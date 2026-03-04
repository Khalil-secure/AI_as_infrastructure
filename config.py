"""
AII - Layer 0 : Budget Guard
Hard stop à 0.50€ par session.
Chaque appel API passe par ce module.
"""

import json
import os
from datetime import datetime
from pathlib import Path

# ─── Pricing Anthropic (claude-sonnet-4) ──────────────────────────────────────
# Prix en USD pour 1M tokens
PRICE_INPUT_PER_M  = 3.00   # $3.00 / 1M input tokens
PRICE_OUTPUT_PER_M = 15.00  # $15.00 / 1M output tokens
USD_TO_EUR         = 0.92   # taux approximatif

# ─── Limites ──────────────────────────────────────────────────────────────────
BUDGET_HARD_STOP_EUR = 0.50  # Hard stop session
BUDGET_WARNING_EUR   = 0.40  # Warning avant stop
SESSION_LOG_FILE     = Path(__file__).parent / "session_costs.json"

# ─── Session State ────────────────────────────────────────────────────────────
_session = {
    "started_at":    datetime.now().isoformat(),
    "total_eur":     0.0,
    "calls":         [],
    "stopped":       False
}


def _tokens_to_eur(input_tokens: int, output_tokens: int) -> float:
    cost_usd = (input_tokens / 1_000_000 * PRICE_INPUT_PER_M +
                output_tokens / 1_000_000 * PRICE_OUTPUT_PER_M)
    return round(cost_usd * USD_TO_EUR, 6)


def check_budget(role: str = "builder") -> None:
    """Vérifie le budget avant chaque call. Lève une exception si dépassé."""
    if _session["stopped"]:
        raise BudgetExceededError(
            f"🛑 SESSION STOPPÉE — Budget 0.50€ atteint. "
            f"Dépensé: {_session['total_eur']:.4f}€"
        )
    if _session["total_eur"] >= BUDGET_WARNING_EUR:
        remaining = BUDGET_HARD_STOP_EUR - _session["total_eur"]
        print(f"⚠️  [BUDGET] Attention : {_session['total_eur']:.4f}€ / 0.50€ "
              f"— Reste {remaining:.4f}€")


def record_call(role: str, input_tokens: int, output_tokens: int, label: str = "") -> float:
    """Enregistre le coût d'un call API. Retourne le coût en EUR."""
    cost = _tokens_to_eur(input_tokens, output_tokens)
    _session["total_eur"] = round(_session["total_eur"] + cost, 6)

    entry = {
        "timestamp":      datetime.now().isoformat(),
        "role":           role,
        "label":          label,
        "input_tokens":   input_tokens,
        "output_tokens":  output_tokens,
        "cost_eur":       cost,
        "running_total":  _session["total_eur"]
    }
    _session["calls"].append(entry)

    # Check hard stop
    if _session["total_eur"] >= BUDGET_HARD_STOP_EUR:
        _session["stopped"] = True
        _save_session()
        raise BudgetExceededError(
            f"🛑 HARD STOP — Budget 0.50€ atteint ! "
            f"Total session: {_session['total_eur']:.4f}€"
        )

    status = "⚠️ " if _session["total_eur"] >= BUDGET_WARNING_EUR else "💰"
    print(f"{status} [BUDGET] {role.upper()} | {label} | "
          f"+{cost:.4f}€ | Total: {_session['total_eur']:.4f}€ / 0.50€")
    return cost


def get_session_summary() -> dict:
    return {
        "total_eur":    _session["total_eur"],
        "calls_count":  len(_session["calls"]),
        "remaining":    round(BUDGET_HARD_STOP_EUR - _session["total_eur"], 4),
        "stopped":      _session["stopped"],
        "by_role": {
            "architect": sum(c["cost_eur"] for c in _session["calls"] if c["role"] == "architect"),
            "builder":   sum(c["cost_eur"] for c in _session["calls"] if c["role"] == "builder"),
        }
    }


def print_session_summary():
    s = get_session_summary()
    print("\n" + "="*50)
    print("  💰 BILAN SESSION AII")
    print("="*50)
    print(f"  Total dépensé : {s['total_eur']:.4f}€ / 0.50€")
    print(f"  Reste         : {s['remaining']:.4f}€")
    print(f"  Calls API     : {s['calls_count']}")
    print(f"  → Architect   : {s['by_role']['architect']:.4f}€")
    print(f"  → Builder     : {s['by_role']['builder']:.4f}€")
    print("="*50)


def _save_session():
    try:
        SESSION_LOG_FILE.write_text(
            json.dumps(_session, indent=2, ensure_ascii=False)
        )
    except Exception:
        pass


class BudgetExceededError(Exception):
    pass
