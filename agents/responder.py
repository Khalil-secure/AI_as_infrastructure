"""
AII - Semaine 2 : Agent Responder
Rôle : recevoir le diagnostic du Detector,
générer un plan de réponse structuré et priorisé.
MODE DRY-RUN : suggestions uniquement, zéro exécution.
"""

from roles import builder_call
import memory as mem


def run_responder(detector_result: dict, context_data: str) -> dict:
    """
    Responder Agent :
    1. Reçoit le diagnostic enrichi du Detector
    2. Génère un plan de réponse priorisé (DRY-RUN)
    3. Stocke l'incident en mémoire ChromaDB
    Retourne le rapport final complet.
    """
    print("\n🛡️  [RESPONDER] Génération du plan de réponse...")

    severity   = detector_result.get("severity", "HIGH")
    category   = detector_result.get("category", "UNKNOWN")
    root_cause = detector_result.get("root_cause", "")
    tags       = detector_result.get("tags", [])
    services   = detector_result.get("affected_services", [])
    incident   = detector_result.get("original_incident", "")
    known      = detector_result.get("is_known_pattern", False)

    # Contexte mémoire
    memory_note = ""
    if known and detector_result.get("past_incidents"):
        memory_note = f"\nNOTE : Pattern connu. {len(detector_result['past_incidents'])} incident(s) similaire(s) en mémoire."

    user_content = f"""Tu es l'agent RESPONDER de AII. MODE DRY-RUN STRICT.

ENVIRONNEMENT : Windows + Docker Desktop. UNIQUEMENT des commandes Docker.
COMMANDES AUTORISÉES : docker restart, docker start, docker stop, docker logs,
docker stats, docker exec, docker update, docker system prune, docker system df.
INTERDIT : free, df, ps, systemctl, kill, top, iptables, journalctl, dmesg.
Si tu veux voir les ressources, utilise : docker stats --no-stream
Si tu veux redémarrer un service, utilise : docker restart <nom-container>

DIAGNOSTIC DU DETECTOR :
- Severity      : {severity}
- Category      : {category}
- Root cause    : {root_cause}
- Services      : {', '.join(services) if services else 'N/A'}
- Tags          : {', '.join(tags)}{memory_note}

DONNÉES SYSTÈME :
{context_data}

INCIDENT ORIGINAL :
{incident}

Ta mission : générer un plan de réponse immédiat.

Format de réponse :

## 🔴 INCIDENT — {severity}
[1 ligne de contexte]

## 🎯 CAUSE RACINE
[root_cause + données qui le prouvent]

## 📋 PLAN D'ACTION (DRY-RUN — ne rien exécuter)

### ⚡ IMMÉDIAT (< 5 min)
- `commande exacte` — pourquoi

### 🔧 COURT TERME (< 1h)
- `commande exacte` — pourquoi

### 🛡️ PRÉVENTION (long terme)
- action — pourquoi

## ✅ RÉSUMÉ EXÉCUTIF
[2 phrases max pour un manager non-tech]
"""

    response = builder_call(
        messages=[{"role": "user", "content": user_content}],
        label="responder_plan",
        max_tokens=1200
    )

    print("\n" + "─"*60)
    print(response)
    print("─"*60)

    # Stocker en mémoire ChromaDB
    print("\n💾 [RESPONDER] Stockage en mémoire...")
    incident_id = mem.store_incident(
        incident=incident,
        diagnosis=f"{root_cause} | {detector_result.get('detector_summary', '')}",
        severity=severity,
        tags=tags
    )

    return {
        "incident_id":    incident_id,
        "severity":       severity,
        "category":       category,
        "root_cause":     root_cause,
        "response_plan":  response,
        "tags":           tags,
        "services":       services,
        "known_pattern":  known,
        "stored_in_memory": True
    }