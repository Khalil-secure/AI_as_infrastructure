"""
AII — break_it.py
Crée de vrais problèmes dans l'environnement Docker.
Lance ce script pendant que AII Watcher tourne — regarde-le réagir.

Usage :
  python break_it.py --scenario oom
  python break_it.py --scenario crash
  python break_it.py --scenario disk
  python break_it.py --scenario all
"""

import sys
import time
import argparse
import subprocess

def run(cmd: str):
    print(f"  $ {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(f"    {result.stdout.strip()}")
    if result.returncode != 0 and result.stderr:
        print(f"    ⚠️  {result.stderr.strip()}")
    return result.returncode == 0


def scenario_crash():
    """Tue le container app-python — AII doit détecter CONTAINER_DOWN."""
    print("\n💥 SCENARIO : Container crash")
    print("   → Arrêt forcé de aii-app...")
    run("docker stop aii-app")
    print("   ✅ Container arrêté. AII va détecter dans ~30s.\n")
    print("   Pour rétablir : docker start aii-app")


def scenario_oom():
    """Simule une pression mémoire sur le container app."""
    print("\n💥 SCENARIO : Memory pressure")
    print("   → Envoi de requêtes /stress à l'app...")
    for i in range(5):
        run("curl -s http://localhost:5000/stress > /dev/null")
        print(f"   → Requête {i+1}/5 envoyée")
        time.sleep(1)
    print("   ✅ Pression mémoire simulée. Surveille les métriques Prometheus.\n")


def scenario_disk():
    """Remplit le disque du container nginx."""
    print("\n💥 SCENARIO : Disk pressure")
    print("   → Génération d'un fichier volumineux dans nginx...")
    run("docker exec aii-nginx sh -c 'dd if=/dev/zero of=/tmp/bigfile bs=1M count=200 2>/dev/null'")
    print("   ✅ 200MB générés. AII va détecter si disk > 90%.\n")
    print("   Pour nettoyer : docker exec aii-nginx rm /tmp/bigfile")


def scenario_all():
    """Lance tous les scénarios en séquence."""
    print("\n💥 SCENARIO : ALL — attaque multi-vecteur\n")
    scenario_oom()
    time.sleep(5)
    scenario_crash()
    print("\n⏳ Attends 30s que AII détecte et diagnostique...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AII Break It — Simulation d'incidents")
    parser.add_argument(
        "--scenario",
        choices=["crash", "oom", "disk", "all"],
        default="crash",
        help="Scénario à simuler"
    )
    args = parser.parse_args()

    print("="*55)
    print("  AII — Break It Script")
    print("  Assure-toi que AII Watcher tourne :")
    print("  docker compose up -d && docker logs -f aii-watcher")
    print("="*55)

    scenarios = {
        "crash": scenario_crash,
        "oom":   scenario_oom,
        "disk":  scenario_disk,
        "all":   scenario_all,
    }

    scenarios[args.scenario]()
