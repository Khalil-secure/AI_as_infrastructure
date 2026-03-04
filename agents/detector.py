"""
AII - Semaine 2 : Agent Detector
Rôle : analyser les données brutes, classifier l'incident,
consulter la mémoire, passer le contexte enrichi au Responder.
"""

import json
from roles import builder_call
import memory as mem

# ─── Severity levels ──────────────────────────────────────────────────────────
SEVERITY_LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

CATEGORIES = {
    "OOM":            "RAM exhaustion, OOM killer triggered, exit code 137",
    "CONTAINER_CRASH":"Container stopped/exited for non-OOM reason (manual stop, config error, app crash)",
    "NETWORK":        "Service unreachable, DNS failure, port not responding",
    "DISK_FULL":      "Disk usage > 90%, no space left",
    "SERVICE_DOWN":   "HTTP health check failing, process not running",
    "PERFORMANCE":    "High CPU, high latency, slow response",
    "SECURITY":       "SSH brute force, unauthorized access, suspicious traffic",
    "UNKNOWN":        "Cannot determine root cause from available data",
}


def run_detector(incident: str, context_data: str) -> dict:
    """
    Detector Agent :
    1. Consulte la mémoire pour des incidents similaires
    2. Analyse les données brutes
    3. Classifie : severity + tags + résumé structuré
    Retourne un dict enrichi pour le Responder.
    """
    print("\n🔎 [DETECTOR] Analyse de l'incident...")

    # 1. Recherche mémoire
    past_incidents = mem.search_similar(incident, n_results=3)
    memory_context = mem.format_past_incidents(past_incidents)
    print(f"   → Mémoire consultée : {len(past_incidents)} incident(s) similaire(s) trouvé(s)")

    # 2. Prompt Detector
    user_content = f"""Tu es l'agent DETECTOR de AII.

INCIDENT SIGNALÉ :
{incident}

DONNÉES SYSTÈME (MCP Tools) :
{context_data}

{memory_context}

Ta mission : analyser et classifier cet incident.
Réponds UNIQUEMENT en JSON valide, sans markdown, sans explication :

{{
  "severity": "CRITICAL|HIGH|MEDIUM|LOW",
  "category": "OOM|CONTAINER_CRASH|NETWORK|DISK_FULL|SERVICE_DOWN|PERFORMANCE|SECURITY|UNKNOWN",
  // IMPORTANT: Use CONTAINER_CRASH not OOM unless you see exit code 137 OR explicit oom-killer in logs
  // Use NETWORK if containers are running but HTTP checks fail
  // Use SERVICE_DOWN if app is running but not responding correctly
  "tags": ["tag1", "tag2", "tag3"],
  "root_cause": "cause racine en une phrase",
  "affected_services": ["service1", "service2"],
  "is_known_pattern": true|false,
  "similar_past_incident": "id ou null",
  "detector_summary": "résumé technique en 2 phrases max"
}}"""

    response = builder_call(
        messages=[{"role": "user", "content": user_content}],
        label="detector_classify"
    )

    # 3. Parse JSON
    try:
        # Nettoyer si markdown présent
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        result = json.loads(clean.strip())
    except json.JSONDecodeError:
        print("⚠️  [DETECTOR] JSON invalide, fallback...")
        result = {
            "severity":             "HIGH",
            "category":             "UNKNOWN",
            "tags":                 ["parse_error"],
            "root_cause":           "Erreur parsing réponse Detector",
            "affected_services":    [],
            "is_known_pattern":     False,
            "similar_past_incident": None,
            "detector_summary":     response[:200]
        }

    # 4. Affichage
    print(f"   → Severity   : {result.get('severity', '?')}")
    print(f"   → Category   : {result.get('category', '?')}")
    print(f"   → Tags       : {result.get('tags', [])}")
    print(f"   → Root cause : {result.get('root_cause', '?')}")
    print(f"   → Known pattern : {result.get('is_known_pattern', False)}")

    # Ajouter le contexte mémoire au résultat
    result["past_incidents"]  = past_incidents
    result["memory_context"]  = memory_context
    result["original_incident"] = incident

    return result