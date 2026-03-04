"""
AII - Layer 0 : Two-Instance Pattern
Architect  → décisions haut niveau, planning, debug thinking
Builder    → code, exécution semaine par semaine
"""

from anthropic import Anthropic
import config as budget

MODEL = "claude-sonnet-4-20250514"

_client = Anthropic()

# ─── Prompts système par rôle ─────────────────────────────────────────────────

ARCHITECT_SYSTEM = """Tu es l'Architecte de AII (AI as Infrastructure).

Ton rôle : décisions de haut niveau, cohérence de l'architecture, anticipation des problèmes.

Règles absolues :
- Tu ne génères pas de code directement — tu décris des interfaces et des contrats
- Tu penses en termes de semaines, pas de lignes
- Tu poses des questions avant de valider une direction
- Tu protèges le budget API : si une approche coûte cher en tokens, tu dis pourquoi et proposes une alternative
- Tu maintiens la vision DRY-RUN : rien n'est exécuté sans validation humaine

Tu travailles sur AII : un agent DevSecOps multi-agent (LangGraph + Claude + MCP + ChromaDB) 
déployé sur GCP Cloud Run, stack Zero Trust, CI/CD sécurisé.
"""

BUILDER_SYSTEM = """Tu es le Builder de AII (AI as Infrastructure).

Ton rôle : implémenter, coder, livrer semaine par semaine.

Règles absolues :
- MODE DRY-RUN : les agents suggèrent des actions, ils n'exécutent JAMAIS
- Tu suis le plan semaine par semaine, tu ne sautes pas d'étapes
- Chaque fichier que tu produis est immédiatement utilisable (imports corrects, pas de TODO cachés)
- Tu commentes les sections critiques de sécurité
- Si tu détectes un risque (boucle infinie, commande dangereuse, coût API explosif), tu STOP et tu signales

Stack : Python 3.11, LangGraph, Anthropic API, ChromaDB, psutil, Docker, GCP.
"""

# ─── Clients ──────────────────────────────────────────────────────────────────

def architect_call(messages: list, label: str = "arch") -> str:
    """Call API en mode Architecte. Budget plus généreux (réflexion)."""
    budget.check_budget("architect")

    response = _client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=ARCHITECT_SYSTEM,
        messages=messages
    )

    text = response.content[0].text
    budget.record_call(
        role="architect",
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        label=label
    )
    return text


def builder_call(messages: list, label: str = "build", max_tokens: int = 1200) -> str:
    """Call API en mode Builder. Budget serré, orienté exécution."""
    budget.check_budget("builder")

    response = _client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=BUILDER_SYSTEM,
        messages=messages
    )

    text = response.content[0].text
    budget.record_call(
        role="builder",
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        label=label
    )
    return text
