"""
AII - Pipeline Principal
Orchestration : Collect → Detect → Respond → Memory

IMPORTANT: Quand appelé depuis le CLI/watcher, context_data est
déjà fourni avec les vraies données. node_collect ne collecte
que si context_data est vide (appel standalone).
"""

import os
import sys
import json
import psutil
import platform
import subprocess
from datetime import datetime
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

import config as budget
from agents.detector import run_detector
from agents.responder import run_responder
import memory as mem

# ── State ─────────────────────────────────────────────────────────────────────

class PipelineState(TypedDict):
    messages:        Annotated[list, add_messages]
    incident:        str
    context_data:    str
    tool_calls:      list
    detector_result: dict
    final_report:    dict

# ── Real MCP Tools ────────────────────────────────────────────────────────────

def tool_docker_status() -> dict:
    """Collecte l'état réel des containers Docker."""
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=aii-", "--format", "{{json .}}"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0 or not result.stdout.strip():
            return {"status": "unavailable", "containers": [], "note": "Docker not accessible"}

        containers = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                try:
                    c = json.loads(line)
                    containers.append({
                        "name":    c.get("Names", ""),
                        "status":  c.get("State", ""),
                        "image":   c.get("Image", ""),
                        "ports":   c.get("Ports", ""),
                        "created": c.get("CreatedAt", ""),
                    })
                except Exception:
                    pass

        return {"status": "ok", "containers": containers, "count": len(containers)}
    except Exception as e:
        return {"status": "error", "message": str(e), "containers": []}


def tool_log_reader(containers: list = None) -> dict:
    """
    Collecte les vrais logs Docker des containers AII.
    Plus de logs simulés — uniquement ce que Docker retourne.
    """
    if not containers:
        # Découvrir les containers AII actifs
        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", "name=aii-", "--format", "{{.Names}}"],
                capture_output=True, text=True, timeout=10
            )
            containers = [n.strip() for n in result.stdout.strip().split("\n") if n.strip()]
        except Exception:
            return {"service": "docker", "logs": [], "note": "Could not list containers"}

    real_logs = []
    for name in containers[:5]:  # max 5 containers
        try:
            result = subprocess.run(
                ["docker", "logs", "--tail", "15", "--timestamps", name],
                capture_output=True, text=True, timeout=10
            )
            output = (result.stdout + result.stderr).strip()
            for line in output.split("\n"):
                if line.strip():
                    real_logs.append(f"[{name}] {line.strip()}")
        except Exception:
            pass

    # Vérifier aussi les containers récemment arrêtés
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=aii-", "--filter", "status=exited",
             "--format", "{{.Names}}:{{.Status}}"],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                real_logs.append(f"[EXITED] {line.strip()}")
    except Exception:
        pass

    return {
        "service":   "docker_real",
        "logs":      real_logs[-60:],  # max 60 lignes
        "count":     len(real_logs),
        "simulated": False
    }


def tool_system_metrics() -> dict:
    """Métriques système réelles."""
    try:
        cpu  = psutil.cpu_percent(interval=1)
        ram  = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        return {
            "cpu_percent":  cpu,
            "ram_percent":  ram.percent,
            "ram_used_gb":  round(ram.used / 1e9, 2),
            "ram_total_gb": round(ram.total / 1e9, 2),
            "disk_percent": disk.percent,
            "platform":     platform.system(),
            "simulated":    False
        }
    except Exception:
        return {"cpu_percent": 0, "ram_percent": 0, "disk_percent": 0, "simulated": True}

# ── Nodes LangGraph ───────────────────────────────────────────────────────────

def node_collect(state: PipelineState) -> PipelineState:
    """
    Si context_data est déjà fourni (appel depuis CLI/watcher) :
      → on utilise les données existantes, on ne réécrit pas
    Si context_data est vide (appel standalone) :
      → on collecte les vraies données
    """
    # Context déjà fourni par le watcher/CLI — on ne l'écrase pas
    if state.get("context_data") and len(state["context_data"]) > 50:
        print("\n[AII] Donnees recues du watcher (contexte reel)")
        return state

    # Appel standalone — collecte réelle
    print("\n[AII] Collecte des donnees en temps reel...")
    tool_calls = []

    print("   -> docker_status")
    docker = tool_docker_status()
    tool_calls.append({"tool": "docker_status", "result": docker})

    # Extraire les noms de containers pour les logs
    container_names = [c["name"] for c in docker.get("containers", [])]

    print("   -> log_reader")
    logs = tool_log_reader(container_names)
    tool_calls.append({"tool": "log_reader", "result": logs})

    print("   -> system_metrics")
    metrics = tool_system_metrics()
    tool_calls.append({"tool": "system_metrics", "result": metrics})

    context_data = json.dumps({
        "docker":  docker,
        "logs":    logs,
        "metrics": metrics
    }, indent=2, ensure_ascii=False)

    return {**state, "tool_calls": tool_calls, "context_data": context_data}


def node_detect(state: PipelineState) -> PipelineState:
    result = run_detector(state["incident"], state["context_data"])
    return {**state, "detector_result": result}


def node_respond(state: PipelineState) -> PipelineState:
    report = run_responder(state["detector_result"], state["context_data"])
    return {**state, "final_report": report}


def node_done(state: PipelineState) -> PipelineState:
    print("\n" + "="*60)
    print("  AII PIPELINE TERMINE")
    print("="*60)
    report = state.get("final_report", {})
    print(f"  Incident ID  : {report.get('incident_id', 'N/A')}")
    print(f"  Severity     : {report.get('severity', 'N/A')}")
    print(f"  Category     : {report.get('category', 'N/A')}")
    print(f"  En memoire   : {report.get('stored_in_memory', False)}")
    stats = mem.get_memory_stats()
    print(f"  Total incidents memorises : {stats['total_incidents']}")
    budget.print_session_summary()
    return state

# ── Build Graph ───────────────────────────────────────────────────────────────

def build_pipeline():
    graph = StateGraph(PipelineState)
    graph.add_node("collect", node_collect)
    graph.add_node("detect",  node_detect)
    graph.add_node("respond", node_respond)
    graph.add_node("done",    node_done)
    graph.set_entry_point("collect")
    graph.add_edge("collect", "detect")
    graph.add_edge("detect",  "respond")
    graph.add_edge("respond", "done")
    graph.add_edge("done",    END)
    return graph.compile()

# ── Main standalone ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("="*60)
    print("  AII Pipeline | Standalone mode")
    print("  Collecte les vraies donnees Docker")
    print("="*60)

    pipeline = build_pipeline()
    try:
        pipeline.invoke({
            "messages":        [],
            "incident":        "Diagnostic complet de l'environnement AII",
            "context_data":    "",
            "tool_calls":      [],
            "detector_result": {},
            "final_report":    {}
        })
    except budget.BudgetExceededError as e:
        print(f"\n{e}")
        budget.print_session_summary()
        sys.exit(1)