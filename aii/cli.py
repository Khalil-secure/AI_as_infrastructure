"""
AII - CLI Interface
Style hacking tool au lancement, DevOps pro pendant l'operation.
"""

import os
import sys
import time
import subprocess
import json
import re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

# Colors
RED     = "\033[91m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
CYAN    = "\033[96m"
WHITE   = "\033[97m"
GRAY    = "\033[90m"
BOLD    = "\033[1m"
RESET   = "\033[0m"

def col(color, text):
    return color + str(text) + RESET

LOGO = """
    ___    ____   ____
   /   |  /  _/  /  _/
  / /| |  / /    / /
 / ___ |_/ /   _/ /
/_/  |_/___/  /___/
"""

SEP = col(CYAN, "-" * 55)

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def slow_print(text, delay=0.03):
    for char in text:
        print(char, end="", flush=True)
        time.sleep(delay)
    print()

def info(msg):  print("  " + col(CYAN,   "[*]") + " " + msg)
def ok(msg):    print("  " + col(GREEN,  "[+]") + " " + msg)
def warn(msg):  print("  " + col(YELLOW, "[!]") + " " + msg)
def err(msg):   print("  " + col(RED,    "[-]") + " " + msg)
def action(msg):print("  " + col(CYAN,   "[>]") + " " + msg)

def spinner(msg, duration=1.0):
    frames = ["|", "/", "-", "\\"]
    end = time.time() + duration
    i = 0
    while time.time() < end:
        print("\r  " + col(CYAN, frames[i % 4]) + " " + msg, end="", flush=True)
        time.sleep(0.1)
        i += 1
    print("\r  " + col(GREEN, "+") + " " + msg + " -- done")

# Boot sequence
def boot_sequence():
    clear()
    print(col(CYAN + BOLD, LOGO))
    print(col(GRAY, "  AI as Infrastructure -- DevSecOps Agent"))
    print(col(GRAY, "  by Khalil Ghiati | github.com/Khalil-secure"))
    print()
    time.sleep(0.3)
    print(SEP)
    slow_print(col(CYAN, "  Initializing AII systems..."))
    print(SEP)
    print()
    spinner("Loading LangGraph pipeline", 1.0)
    spinner("Connecting to ChromaDB memory", 0.8)
    spinner("Checking Docker environment", 0.8)
    spinner("Loading budget guard", 0.5)
    print()
    ok("All systems operational")
    print()

# API Key setup
def setup_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key and key.startswith("sk-ant-"):
        ok("API key detected: " + key[:12] + "..." + key[-4:])
        return key

    print()
    print(SEP)
    print(col(YELLOW, "  API KEY REQUIRED"))
    print(SEP)
    print()
    print(col(GRAY, "  Get your key at: console.anthropic.com"))
    print()

    while True:
        key = input(col(CYAN, "  Enter Anthropic API key: ")).strip()
        if key.startswith("sk-ant-") and len(key) > 20:
            os.environ["ANTHROPIC_API_KEY"] = key
            ok("API key accepted")
            return key
        err("Invalid key (must start with sk-ant-)")

# Main menu
def main_menu():
    print()
    print(SEP)
    print(col(BOLD + WHITE, "  MAIN MENU"))
    print(SEP)
    print()
    print("  " + col(CYAN, "[1]") + " " + col(WHITE, "Watch Mode    ") + " -- Continuous monitoring + auto-detect")
    print("  " + col(CYAN, "[2]") + " " + col(WHITE, "Diagnose Mode ") + " -- Manual incident analysis")
    print("  " + col(CYAN, "[3]") + " " + col(WHITE, "Memory        ") + " -- View past incidents (ChromaDB)")
    print("  " + col(CYAN, "[4]") + " " + col(WHITE, "Budget        ") + " -- API cost tracker")
    print("  " + col(RED,  "[0]") + " " + col(GRAY,  "Exit"))
    print()

    while True:
        choice = input(col(CYAN, "  AII> ")).strip()
        if choice in ["0", "1", "2", "3", "4"]:
            return choice
        err("Invalid choice")

# Trust Layer
def prompt_action(commands, incident_id):
    if not commands:
        warn("No actionable commands found in plan")
        return []

    print()
    print(SEP)
    print(col(BOLD + YELLOW, "  TRUST LAYER -- ACTION REQUIRED"))
    print(col(GRAY, "  Incident: " + incident_id))
    print(SEP)
    print()

    approved = []

    for i, cmd in enumerate(commands[:5], 1):
        print("  " + col(YELLOW, "Command " + str(i) + "/" + str(min(len(commands), 5)) + ":"))
        print("  " + col(BOLD + WHITE, "  $ " + cmd))
        print()
        print("  " + col(GREEN,  "[1]") + " Execute")
        print("  " + col(YELLOW, "[2]") + " Modify before execute")
        print("  " + col(RED,    "[3]") + " Skip")
        print("  " + col(GRAY,   "[0]") + " Stop all")
        print()

        while True:
            choice = input(col(CYAN, "  > ")).strip()

            if choice == "1":
                print()
                action("Executing: " + cmd)
                result = execute_command(cmd)
                if result["success"]:
                    ok("Success")
                    if result["output"]:
                        print(col(GRAY, "    " + result["output"][:200]))
                else:
                    err("Failed: " + result["error"])
                approved.append({"cmd": cmd, "status": "executed", "result": result})
                break

            elif choice == "2":
                print()
                modified = input(col(YELLOW, "  New command: ")).strip()
                if modified:
                    action("Executing: " + modified)
                    result = execute_command(modified)
                    if result["success"]:
                        ok("Success")
                    else:
                        err("Failed: " + result["error"])
                    approved.append({"cmd": modified, "status": "modified", "result": result})
                break

            elif choice == "3":
                warn("Skipped")
                approved.append({"cmd": cmd, "status": "skipped"})
                break

            elif choice == "0":
                warn("Stopping action sequence")
                return approved
            else:
                err("Invalid choice")
        print()

    return approved


def execute_command(cmd):
    SAFE = [
        "docker restart",
        "docker start",
        "docker stop",
        "docker stats",
        "docker logs",
        "docker ps",
        "docker system prune",
        "docker system df",
        "docker exec",
        "docker update",
        "docker inspect",
        "docker compose",
        "docker network",
    ]
    if not any(cmd.strip().startswith(p) for p in SAFE):
        return {"success": False, "error": "Not in whitelist", "output": ""}
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return {"success": r.returncode == 0, "output": r.stdout.strip(), "error": r.stderr.strip()}
    except Exception as e:
        return {"success": False, "error": str(e), "output": ""}


def trigger_pipeline_cli(anomalies, containers, system, services, real_logs):
    import config as budget
    from pipeline import build_pipeline

    context_data = json.dumps({
        "docker":   {"containers": containers},
        "logs":     {"service": "cli", "logs": real_logs},
        "metrics":  system,
        "services": services,
    }, indent=2, ensure_ascii=False)

    incident = "ALERT -- " + str(len(anomalies)) + " anomaly(ies):\n"
    incident += "\n".join(["- [" + a["severity"] + "] " + a["type"] + ": " + a["detail"] for a in anomalies])

    try:
        pipeline    = build_pipeline()
        final_state = pipeline.invoke({
            "messages": [], "incident": incident,
            "context_data": context_data, "tool_calls": [],
            "detector_result": {}, "final_report": {}
        })
        return final_state.get("final_report", {})
    except budget.BudgetExceededError as e:
        err(str(e))
        return {}
    except Exception as e:
        err("Pipeline error: " + str(e))
        return {}


def extract_commands(plan):
    commands = re.findall(r'`([^`]+)`', plan)
    safe_starts = ["docker", "free", "df", "dmesg", "systemctl", "find", "iptables", "fail2ban"]
    return [c for c in commands if any(c.startswith(p) for p in safe_starts)][:5]


# Watch Mode
def watch_mode():
    clear()
    print(col(CYAN + BOLD, LOGO))
    print(SEP)
    print(col(BOLD + GREEN, "  WATCH MODE -- Continuous Monitoring"))
    print(SEP)
    print()
    info("Monitoring AII containers only (prefix: aii-)")
    info("AI called ONLY when anomaly detected")
    warn("Press Ctrl+C to return to menu")
    print()

    from aii.watcher import (
        collect_containers, collect_system, check_services,
        detect_anomalies, collect_real_logs
    )

    cycle          = 0
    last_incident  = None
    was_in_alert   = False

    try:
        while True:
            cycle += 1
            now        = datetime.now().strftime("%H:%M:%S")

            # Scanning indicator
            print("  " + col(CYAN, "~") + " " + col(GRAY, "[" + now + "] Scanning..."), end="", flush=True)

            containers = collect_containers()
            system     = collect_system()
            services   = check_services()
            anomalies  = detect_anomalies(containers, system, services)

            aii_up    = sum(1 for c in containers if c.get("status") == "running")
            aii_total = len(containers)
            ram       = str(system["ram_percent"]) + "%"
            cpu       = str(system["cpu_percent"]) + "%"

            if not anomalies:
                # Clear the scanning line
                print("\r", end="")
                if was_in_alert:
                    # Just recovered from an incident
                    print()
                    print("  " + col(GREEN, "[RESOLVED]") + " " + col(BOLD + GREEN, "Danger evaded -- no anomalies detected"))
                    print("  " + col(GRAY, now) + " All systems back to normal")
                    print()
                    was_in_alert  = False
                    last_incident = None
                else:
                    print("  " + col(GREEN, "[+]") + " " + col(GRAY, now) +
                          " Nominal -- " + col(WHITE, str(aii_up) + "/" + str(aii_total)) +
                          " up | RAM " + col(WHITE, ram) + " | CPU " + col(WHITE, cpu))
                    last_incident = None
            else:
                print("\r", end="")
                incident_key = sorted([a["type"] + a["target"] for a in anomalies])
                if incident_key != last_incident:
                    print()
                    print("  " + col(RED, "<!>") + " " + col(BOLD + RED, "ALERT -- " + str(len(anomalies)) + " anomaly(ies)"))
                    for a in anomalies:
                        sev_col = RED if a["severity"] == "CRITICAL" else YELLOW
                        print("      " + col(sev_col, a["severity"]) + " " + a["type"] + " -- " + a["detail"])
                    print()
                    spinner("AII is analyzing the incident...", 1.0)

                    real_logs = collect_real_logs(containers)
                    report    = trigger_pipeline_cli(anomalies, containers, system, services, real_logs)

                    if report:
                        commands = extract_commands(report.get("response_plan", ""))
                        approved = prompt_action(commands, report.get("incident_id", "N/A"))

                        # Post-action verification
                        if any(a.get("status") in ["executed", "modified"] for a in approved):
                            print()
                            print("  " + col(CYAN, "[~]") + " Waiting 15s to verify resolution...")
                            time.sleep(15)
                            recheck     = detect_anomalies(collect_containers(), collect_system(), check_services())
                            same_issues = [a for a in recheck if any(
                                a["type"] == orig["type"] and a["target"] == orig["target"]
                                for orig in anomalies
                            )]
                            if not same_issues:
                                print("  " + col(GREEN, "[RESOLVED]") + " " + col(BOLD + GREEN, "Actions worked -- incident resolved"))
                            else:
                                print("  " + col(YELLOW, "[!]") + " " + str(len(same_issues)) + " issue(s) still present after actions")
                                for s in same_issues:
                                    print("      " + col(YELLOW, s["type"]) + " -- " + s["detail"])

                    was_in_alert  = True
                    last_incident = incident_key
                else:
                    print("  " + col(YELLOW, "[~]") + " " + col(GRAY, now) +
                          " Incident ongoing -- waiting for resolution...")

            time.sleep(30)

    except KeyboardInterrupt:
        print()
        warn("Watch mode stopped")
        time.sleep(1)


# Diagnose Mode
def diagnose_mode():
    clear()
    print(col(CYAN + BOLD, LOGO))
    print(SEP)
    print(col(BOLD + CYAN, "  DIAGNOSE MODE -- Manual Analysis"))
    print(SEP)
    print()

    incident = input(col(CYAN, "  Describe the incident:\n  > ")).strip()
    if not incident:
        err("No incident provided")
        return

    from aii.watcher import collect_containers, collect_system, check_services, collect_real_logs
    print()
    spinner("Collecting system data", 1.0)

    containers = collect_containers()
    system     = collect_system()
    services   = check_services()
    real_logs  = collect_real_logs(containers)
    anomalies  = [{"type": "MANUAL", "severity": "HIGH", "target": "manual", "detail": incident}]

    spinner("Running AII pipeline", 1.5)
    report = trigger_pipeline_cli(anomalies, containers, system, services, real_logs)

    if report:
        commands = extract_commands(report.get("response_plan", ""))
        prompt_action(commands, report.get("incident_id", "N/A"))

    input(col(GRAY, "\n  Press Enter to return..."))


# Memory View
def memory_view():
    clear()
    print(col(CYAN + BOLD, LOGO))
    print(SEP)
    print(col(BOLD + CYAN, "  MEMORY -- Past Incidents (ChromaDB)"))
    print(SEP)
    print()

    import memory as mem
    stats = mem.get_memory_stats()
    info("Total incidents stored: " + str(stats["total_incidents"]))
    print()

    if stats["total_incidents"] == 0:
        warn("No incidents in memory yet")
    else:
        query = input(col(CYAN, "  Search (or Enter for recent):\n  > ")).strip() or "incident"
        results = mem.search_similar(query, n_results=5)
        print()
        for i, inc in enumerate(results, 1):
            meta      = inc["metadata"]
            sim       = str(round((1 - inc["distance"]) * 100, 1)) + "%"
            sev_col   = RED if meta.get("severity") == "CRITICAL" else YELLOW
            print("  " + col(CYAN, "[" + str(i) + "]") + " " +
                  col(sev_col, meta.get("severity", "?")) +
                  " -- " + col(GRAY, meta.get("date", "")[:16]))
            print("      " + col(WHITE, meta.get("short", "")[:80]))
            print("      " + col(GRAY, "Similarity: " + sim))
            print()

    input(col(GRAY, "  Press Enter to return..."))


# Budget View
def budget_view():
    clear()
    print(col(CYAN + BOLD, LOGO))
    print(SEP)
    print(col(BOLD + YELLOW, "  BUDGET -- API Cost Tracker"))
    print(SEP)
    print()

    import config as budget
    s   = budget.get_session_summary()
    pct = int((s["total_eur"] / 0.50) * 100)
    bar = int(pct / 5)
    bar_str = col(GREEN, "#" * bar) + col(GRAY, "." * (20 - bar))

    total_str = str(round(s["total_eur"], 4)) + " EUR"
    print("  [" + bar_str + "]  " + col(WHITE, total_str) + " / 0.50 EUR")
    print()
    ok("Remaining  : " + str(s["remaining"]) + " EUR")
    info("API calls  : " + str(s["calls_count"]))
    info("Architect  : " + str(round(s["by_role"]["architect"], 4)) + " EUR")
    info("Builder    : " + str(round(s["by_role"]["builder"], 4)) + " EUR")
    print()

    input(col(GRAY, "  Press Enter to return..."))


# Main
def main():
    boot_sequence()
    setup_api_key()

    while True:
        choice = main_menu()
        if choice == "1":
            watch_mode()
        elif choice == "2":
            diagnose_mode()
        elif choice == "3":
            memory_view()
        elif choice == "4":
            budget_view()
        elif choice == "0":
            clear()
            print(col(CYAN + BOLD, LOGO))
            slow_print(col(CYAN, "  Shutting down AII..."))
            time.sleep(0.5)
            ok("All systems stopped. No API calls running.")
            print()
            sys.exit(0)


if __name__ == "__main__":
    main()