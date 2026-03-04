"""
AII - Trust Layer
Stocke les decisions du senior (approve/modify/skip).
L'AI apprend de ces decisions via ChromaDB.
Le score de confiance monte progressivement.
"""

import json
from datetime import datetime
from pathlib import Path

TRUST_FILE = Path(__file__).parent / "memory_store" / "trust_decisions.json"
TRUST_FILE.parent.mkdir(parents=True, exist_ok=True)

# Score de confiance global (0-100)
# Au dela de 80 -> AI peut suggerer des executions automatiques
TRUST_THRESHOLD = 80


def load_decisions() -> list:
    try:
        return json.loads(TRUST_FILE.read_text()) if TRUST_FILE.exists() else []
    except Exception:
        return []


def save_decision(incident_id: str, command: str, status: str, result: dict = None):
    """
    Enregistre une decision du senior.
    status : executed | modified+executed | skipped
    """
    decisions = load_decisions()
    decisions.append({
        "timestamp":   datetime.now().isoformat(),
        "incident_id": incident_id,
        "command":     command,
        "status":      status,
        "result":      result or {},
        "approved":    status in ["executed", "modified+executed"]
    })
    TRUST_FILE.write_text(json.dumps(decisions[-200:], indent=2))


def get_trust_score() -> dict:
    """
    Calcule le score de confiance base sur l'historique.
    Plus le senior approuve les suggestions AI, plus le score monte.
    """
    decisions = load_decisions()
    if not decisions:
        return {"score": 0, "total": 0, "approved": 0, "level": "NONE"}

    total    = len(decisions)
    approved = sum(1 for d in decisions if d.get("approved"))
    score    = int((approved / total) * 100) if total > 0 else 0

    if score >= TRUST_THRESHOLD:
        level = "HIGH"
    elif score >= 50:
        level = "MEDIUM"
    elif score >= 25:
        level = "LOW"
    else:
        level = "NONE"

    return {
        "score":    score,
        "total":    total,
        "approved": approved,
        "skipped":  total - approved,
        "level":    level,
        "auto_exec_enabled": score >= TRUST_THRESHOLD
    }


def get_approved_patterns() -> list:
    """
    Retourne les commandes que le senior a habituellement approuvees.
    Utile pour le Detector qui peut pre-selectionner les commandes.
    """
    decisions = load_decisions()
    approved  = [d["command"] for d in decisions if d.get("approved")]

    # Deduplication et tri par frequence
    freq = {}
    for cmd in approved:
        base = cmd.split()[0] + " " + cmd.split()[1] if len(cmd.split()) > 1 else cmd
        freq[base] = freq.get(base, 0) + 1

    return sorted(freq.items(), key=lambda x: x[1], reverse=True)[:10]


def print_trust_report():
    trust = get_trust_score()
    patterns = get_approved_patterns()

    print("\n" + "=" * 50)
    print("  TRUST LAYER REPORT")
    print("=" * 50)
    print(f"  Score     : {trust['score']}/100 — Level: {trust['level']}")
    print(f"  Total     : {trust['total']} decisions")
    print(f"  Approved  : {trust['approved']}")
    print(f"  Skipped   : {trust['skipped']}")
    print(f"  Auto-exec : {'ENABLED' if trust['auto_exec_enabled'] else 'DISABLED (need 80+)'}")

    if patterns:
        print(f"\n  Most approved command patterns:")
        for pattern, count in patterns[:5]:
            print(f"    [{count}x] {pattern}")
    print("=" * 50)
