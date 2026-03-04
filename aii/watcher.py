"""
AII Watcher — Control Plane (tourne en LOCAL uniquement)
Architecture enterprise : externe a l'infrastructure surveillee.

docker-compose.yml = source de verite (quels containers surveiller)
CLI local = seul point de controle (surveille + execute)

JAMAIS dans un container Docker.
"""

import os
import sys
import json
import time
import yaml
import psutil
import requests
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Config ────────────────────────────────────────────────────────────────────
WATCH_INTERVAL = int(os.environ.get("WATCH_INTERVAL", "30"))
DRY_RUN        = os.environ.get("DRY_RUN", "true").lower() == "true"
COMPOSE_FILE   = Path(__file__).parent.parent / "docker-compose.yml"

# ── Docker client ─────────────────────────────────────────────────────────────
try:
    import docker
    docker_client    = docker.from_env()
    DOCKER_AVAILABLE = True
except Exception as e:
    DOCKER_AVAILABLE = False
    print(f"[WATCHER] Docker SDK unavailable: {e}")
    print("[WATCHER] Run: pip install docker")

# ── Source of Truth — docker-compose.yml ─────────────────────────────────────

def load_expected_services() -> dict:
    """
    Lit docker-compose.yml pour savoir quels containers surveiller.
    C'est la seule source de verite — pas de liste hardcodee.
    """
    health_urls = {
        "aii-app":          "http://localhost:5000/health",
        "aii-prometheus":   "http://localhost:9090/-/ready",
        "aii-grafana":      "http://localhost:3000/api/health",
        "aii-nginx":        "http://localhost:80/health",
        "aii-node-exporter":"http://localhost:9100/metrics",
    }

    try:
        with open(COMPOSE_FILE) as f:
            compose = yaml.safe_load(f)

        services = {}
        for svc_name, svc_config in compose.get("services", {}).items():
            container_name = svc_config.get("container_name", f"aii-{svc_name}")
            services[container_name] = health_urls.get(container_name)
        return services

    except Exception as e:
        print(f"[WATCHER] Cannot read docker-compose.yml: {e}")
        return {}

EXPECTED = load_expected_services()
print(f"[WATCHER] Monitoring {len(EXPECTED)} services from docker-compose.yml:")
for name in sorted(EXPECTED.keys()):
    print(f"  - {name}")

# ── Data Collection (0 token) ─────────────────────────────────────────────────

def collect_containers() -> list:
    """Collecte uniquement les containers definis dans docker-compose.yml."""
    if not DOCKER_AVAILABLE:
        return []
    results = []
    try:
        for container in docker_client.containers.list(all=True):
            if container.name not in EXPECTED:
                continue

            stats = {}
            if container.status == "running":
                try:
                    raw          = container.stats(stream=False)
                    cpu_delta    = (raw["cpu_stats"]["cpu_usage"]["total_usage"] -
                                    raw["precpu_stats"]["cpu_usage"]["total_usage"])
                    system_delta = (raw["cpu_stats"]["system_cpu_usage"] -
                                    raw["precpu_stats"]["system_cpu_usage"])
                    cpu_pct      = (cpu_delta / system_delta * 100) if system_delta > 0 else 0
                    mem_usage    = raw["memory_stats"].get("usage", 0)
                    mem_limit    = raw["memory_stats"].get("limit", 1)
                    stats = {
                        "cpu_percent": round(cpu_pct, 2),
                        "mem_percent": round((mem_usage / mem_limit) * 100, 2),
                        "mem_mb":      round(mem_usage / 1e6, 1),
                    }
                except Exception:
                    stats = {"cpu_percent": 0, "mem_percent": 0, "mem_mb": 0}

            results.append({
                "name":   container.name,
                "status": container.status,
                "image":  container.image.tags[0] if container.image.tags else "unknown",
                "stats":  stats,
            })

        # Ajoute les containers attendus mais absents
        found_names = {c["name"] for c in results}
        for expected_name in EXPECTED:
            if expected_name not in found_names:
                results.append({
                    "name":   expected_name,
                    "status": "missing",
                    "image":  "unknown",
                    "stats":  {},
                })

    except Exception as e:
        print(f"[WATCHER] Docker error: {e}")
    return results


def collect_real_logs(containers: list) -> list:
    """Collecte les vrais logs Docker."""
    if not DOCKER_AVAILABLE:
        return []
    logs = []
    for c in containers:
        if c.get("status") not in ["running", "exited"]:
            continue
        try:
            container = docker_client.containers.get(c["name"])
            raw = container.logs(tail=15, timestamps=True).decode("utf-8", errors="replace")
            for line in raw.strip().split("\n"):
                if line.strip():
                    logs.append(f"[{c['name']}] {line.strip()}")
        except Exception:
            pass
    return logs[-50:]


def collect_system() -> dict:
    ram  = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return {
        "cpu_percent":  psutil.cpu_percent(interval=1),
        "ram_percent":  ram.percent,
        "ram_used_gb":  round(ram.used / 1e9, 2),
        "ram_total_gb": round(ram.total / 1e9, 2),
        "disk_percent": disk.percent,
    }


def check_services() -> dict:
    """Health checks uniquement sur les services avec une URL definie."""
    results = {}
    for name, url in EXPECTED.items():
        if not url:
            continue
        try:
            r = requests.get(url, timeout=3)
            results[name] = {"up": r.status_code < 400, "code": r.status_code}
        except Exception as e:
            results[name] = {"up": False, "error": str(e)}
    return results

# ── Anomaly Detection (0 token) ───────────────────────────────────────────────

def detect_anomalies(containers: list, system: dict, services: dict) -> list:
    anomalies = []

    for c in containers:
        if c.get("status") in ["exited", "missing"]:
            anomalies.append({
                "type":     "CONTAINER_DOWN",
                "severity": "CRITICAL",
                "target":   c["name"],
                "detail":   f"{c['name']} is {c['status']}"
            })
        elif c.get("status") == "running":
            stats = c.get("stats", {})
            if stats.get("mem_percent", 0) > 85:
                anomalies.append({
                    "type":     "HIGH_MEMORY",
                    "severity": "HIGH",
                    "target":   c["name"],
                    "detail":   f"{c['name']} RAM at {stats['mem_percent']}%"
                })
            if stats.get("cpu_percent", 0) > 90:
                anomalies.append({
                    "type":     "HIGH_CPU",
                    "severity": "HIGH",
                    "target":   c["name"],
                    "detail":   f"{c['name']} CPU at {stats['cpu_percent']}%"
                })

    if system.get("ram_percent", 0) > 95:
        anomalies.append({
            "type":     "SYSTEM_OOM_RISK",
            "severity": "CRITICAL",
            "target":   "host",
            "detail":   f"Host RAM at {system['ram_percent']}%"
        })

    if system.get("disk_percent", 0) > 95:
        anomalies.append({
            "type":     "DISK_FULL",
            "severity": "HIGH",
            "target":   "host",
            "detail":   f"Disk at {system['disk_percent']}%"
        })

    for name, result in services.items():
        if not result.get("up"):
            # Verifier si le container est up avant d'alerter sur le service
            container_up = any(
                c["name"] == name and c["status"] == "running"
                for c in containers
            )
            if container_up:
                anomalies.append({
                    "type":     "SERVICE_UNREACHABLE",
                    "severity": "HIGH",
                    "target":   name,
                    "detail":   f"{name} container running but HTTP unreachable"
                })

    return anomalies


def trigger_pipeline(anomalies, containers, system, services, real_logs):
    import config as budget
    from pipeline import build_pipeline

    context_data = json.dumps({
        "docker":   {"containers": containers},
        "logs":     {"service": "watcher_local", "logs": real_logs},
        "metrics":  system,
        "services": services,
        "expected_services": list(EXPECTED.keys()),
    }, indent=2, ensure_ascii=False)

    incident = f"ALERT — {len(anomalies)} anomaly(ies) in AII environment:\n"
    incident += "\n".join([f"- [{a['severity']}] {a['type']}: {a['detail']}" for a in anomalies])

    try:
        pipeline    = build_pipeline()
        final_state = pipeline.invoke({
            "messages": [], "incident": incident,
            "context_data": context_data, "tool_calls": [],
            "detector_result": {}, "final_report": {}
        })
        return final_state.get("final_report", {})
    except budget.BudgetExceededError as e:
        print(f"\n{e}")
        return {}
    except Exception as e:
        print(f"\n[WATCHER] Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        return {}


def watch():
    print("=" * 60)
    print("  AII Control Plane — Local Monitor")
    print(f"  Interval : {WATCH_INTERVAL}s | DRY-RUN : {DRY_RUN}")
    print(f"  Source   : {COMPOSE_FILE.name}")
    print("=" * 60)

    cycle         = 0
    last_incident = None

    while True:
        cycle += 1
        now = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{now}] Cycle #{cycle}")

        containers = collect_containers()
        system     = collect_system()
        services   = check_services()
        anomalies  = detect_anomalies(containers, system, services)

        up    = sum(1 for c in containers if c.get("status") == "running")
        total = len(EXPECTED)

        if not anomalies:
            print(f"OK - {up}/{total} up | RAM {system['ram_percent']}% | CPU {system['cpu_percent']}%")
            last_incident = None
        else:
            key = sorted([a["type"] + a["target"] for a in anomalies])
            if key != last_incident:
                print(f"ALERT: {len(anomalies)} anomaly(ies)")
                for a in anomalies:
                    print(f"  [{a['severity']}] {a['type']} — {a['detail']}")
                report = trigger_pipeline(anomalies, containers, system, services, collect_real_logs(containers))
                last_incident = key

        time.sleep(WATCH_INTERVAL)


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set")
        sys.exit(1)
    watch()