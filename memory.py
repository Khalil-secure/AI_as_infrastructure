"""
AII - Semaine 2 : Mémoire des incidents
ChromaDB local — stocke et retrouve les incidents passés.
L'agent Detector consulte la mémoire avant de diagnostiquer.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

# ChromaDB
import chromadb
from chromadb.config import Settings

CHROMA_PATH = Path(__file__).parent / "memory_store"

# ─── Init ChromaDB ────────────────────────────────────────────────────────────

def _get_collection():
    client = chromadb.PersistentClient(
        path=str(CHROMA_PATH),
        settings=Settings(anonymized_telemetry=False)
    )
    return client.get_or_create_collection(
        name="aii_incidents",
        metadata={"hnsw:space": "cosine"}
    )


# ─── Store incident ───────────────────────────────────────────────────────────

def store_incident(incident: str, diagnosis: str, severity: str, tags: list) -> str:
    """Stocke un incident diagnostiqué en mémoire vectorielle."""
    collection = _get_collection()
    incident_id = f"inc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    document = f"""INCIDENT: {incident}
DIAGNOSIS: {diagnosis}
SEVERITY: {severity}
TAGS: {', '.join(tags)}
DATE: {datetime.now().isoformat()}"""

    metadata = {
        "incident_id": incident_id,
        "severity":    severity,
        "tags":        json.dumps(tags),
        "date":        datetime.now().isoformat(),
        "short":       incident[:100]
    }

    collection.add(
        documents=[document],
        metadatas=[metadata],
        ids=[incident_id]
    )

    print(f"💾 [MEMORY] Incident stocké : {incident_id} | Severity: {severity}")
    return incident_id


def search_similar(query: str, n_results: int = 3) -> list:
    """Retrouve les incidents similaires au query."""
    collection = _get_collection()

    try:
        count = collection.count()
        if count == 0:
            return []

        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, count)
        )

        incidents = []
        for i, doc in enumerate(results["documents"][0]):
            incidents.append({
                "document": doc,
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i]
            })

        return incidents

    except Exception as e:
        print(f"⚠️  [MEMORY] Erreur recherche : {e}")
        return []


def get_memory_stats() -> dict:
    """Stats de la mémoire."""
    try:
        collection = _get_collection()
        count = collection.count()
        return {"total_incidents": count, "db_path": str(CHROMA_PATH)}
    except Exception as e:
        return {"total_incidents": 0, "error": str(e)}


def format_past_incidents(incidents: list) -> str:
    """Formate les incidents passés pour le prompt."""
    if not incidents:
        return "Aucun incident similaire trouvé en mémoire."

    lines = ["📚 INCIDENTS SIMILAIRES EN MÉMOIRE :"]
    for i, inc in enumerate(incidents, 1):
        similarity = round((1 - inc["distance"]) * 100, 1)
        meta = inc["metadata"]
        lines.append(f"\n--- Incident #{i} (similarité: {similarity}%) ---")
        lines.append(f"Sévérité: {meta.get('severity', 'N/A')}")
        lines.append(f"Date: {meta.get('date', 'N/A')[:10]}")
        lines.append(inc["document"][:300] + "...")

    return "\n".join(lines)
