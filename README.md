# AII — AI as Infrastructure

> An AI agent that monitors your Docker environment, detects incidents, and proposes corrective actions — with a human trust layer before anything executes.

```
    ___    ____   ____
   /   |  /  _/  /  _/
  / /| |  / /    / /
 / ___ |_/ /   _/ /
/_/  |_/___/  /___/

  AI as Infrastructure — DevSecOps Agent
```

---

## What it does

AII runs locally and watches your Docker environment in real time. When something breaks, it detects it, diagnoses it using Claude, and proposes a recovery plan. You decide what to execute.

```
docker-compose.yml        →  source of truth (what to monitor)
python aii/cli.py         →  local control plane (detect + diagnose + act)
ChromaDB memory           →  learns from past incidents
```

**The key idea:** the AI only intervenes when there is a real anomaly. Every other cycle costs zero tokens.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│  LOCAL CONTROL PLANE (python aii/cli.py)        │
│                                                 │
│  watcher.py ──► detect_anomalies() ──► 0 token │
│                      │                          │
│               anomaly found?                    │
│                      │                          │
│              pipeline.py trigger                │
│           ┌──────────┴──────────┐               │
│     detector.py           responder.py          │
│     (classify)            (action plan)         │
│           └──────────┬──────────┘               │
│                 memory.py                       │
│               (ChromaDB)                        │
│                                                 │
│  TRUST LAYER ──► you approve/modify/skip        │
└─────────────────────────────────────────────────┘
              │ Docker SDK
              ▼
┌─────────────────────────────────────────────────┐
│  INFRASTRUCTURE (docker-compose.yml)            │
│                                                 │
│  aii-prometheus   aii-grafana   aii-nginx       │
│  aii-app          aii-node-exporter             │
└─────────────────────────────────────────────────┘
```

---

## Requirements

- Python 3.11+
- Docker Desktop
- Anthropic API key ([console.anthropic.com](https://console.anthropic.com))

---

## Quick Start

**1. Clone and install**

```powershell
git clone https://github.com/Khalil-secure/AII
cd AII
pip install -r requirements.txt
pip install docker pyyaml
```

**2. Configure your API key**

Create a `.env` file at the root:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**3. Start the infrastructure**

```powershell
docker compose up -d
```

**4. Launch AII**

```powershell
python aii/cli.py
```

---

## Usage

When you launch `python aii/cli.py` you get:

```
  [1] Watch Mode     — Continuous monitoring + auto-detect
  [2] Diagnose Mode  — Manual incident analysis
  [3] Memory         — View past incidents (ChromaDB)
  [4] Budget         — API cost tracker
  [0] Exit
```

### Watch Mode

AII scans your containers every 30 seconds. When everything is fine:

```
  [+] 14:32:01  Nominal -- 5/5 up | RAM 45% | CPU 3%
  [+] 14:32:31  Nominal -- 5/5 up | RAM 44% | CPU 2%
```

When something breaks (e.g. a container crashes):

```
  <!> ALERT -- 1 anomaly(ies)
      CRITICAL CONTAINER_DOWN -- aii-app is exited

  ~ AII is analyzing the incident... -- done

  [DETECTOR] Severity: CRITICAL | Category: CONTAINER_CRASH
  [DETECTOR] Known pattern: True (2 similar incidents in memory)

  TRUST LAYER -- ACTION REQUIRED
  Command 1/3:
    $ docker restart aii-app
  [1] Execute  [2] Modify  [3] Skip  [0] Stop
  > 1
  [+] Success

  ~ Waiting 15s to verify resolution...
  [RESOLVED] Danger evaded -- no anomalies detected
```

### Diagnose Mode

Manually describe an incident and get an AI diagnosis + action plan:

```
  Describe the incident:
  > prometheus is not scraping metrics since this morning

  ~ Collecting system data -- done
  ~ Running AII pipeline -- done

  [DETECTOR] Category: SERVICE_DOWN | Root cause: ...
  [RESPONDER] Immediate actions: ...
```

### Manage Script

```powershell
.\manage.ps1 start    # Start infrastructure
.\manage.ps1 stop     # Stop everything
.\manage.ps1 status   # Container status + URLs
.\manage.ps1 logs     # Live watcher logs
.\manage.ps1 restart  # Rebuild + restart
```

---

## Demo — Break it and watch AII react

Open two terminals.

**Terminal 1 — Launch AII:**
```powershell
python aii/cli.py
# Select [1] Watch Mode
```

**Terminal 2 — Create an incident:**
```powershell
# Crash a container
python break_it.py --scenario crash

# Or memory pressure
python break_it.py --scenario oom

# Or disk saturation
python break_it.py --scenario disk
```

Watch Terminal 1 detect, diagnose, and propose a fix within 30 seconds.

---

## Project Structure

```
AII/
├── aii/
│   ├── cli.py          # CLI interface — entry point
│   └── watcher.py      # Local control plane
│
├── agents/
│   ├── detector.py     # Classifies incidents (JSON output)
│   └── responder.py    # Generates DRY-RUN action plan
│
├── app/                # Demo Flask app with /metrics endpoint
├── prometheus/         # Prometheus scrape config
├── nginx/              # Reverse proxy config
│
├── pipeline.py         # LangGraph orchestration
├── memory.py           # ChromaDB vector memory
├── config.py           # Budget guard (0.50 EUR hard stop)
├── roles.py            # Architect / Builder API clients
├── trust.py            # Trust layer + confidence score
│
├── docker-compose.yml  # Infrastructure definition (source of truth)
├── break_it.py         # Incident simulator for demo
├── manage.ps1          # Environment management script
└── requirements.txt
```

---

## How the Trust Layer works

AII never executes commands without your approval.

Every action goes through:

```
AI proposes command
      ↓
[1] Execute          — runs it immediately
[2] Modify           — you edit before running
[3] Skip             — ignore this command
[0] Stop             — cancel all remaining
```

After execution, AII waits 15 seconds and re-checks. If the issue is gone: `[RESOLVED] Danger evaded`. If not: it tells you what is still failing.

The trust score (`trust.py`) tracks your approval rate over time. Future versions will enable auto-execution once the score reaches 80/100 — like promoting a junior to senior.

---

## Memory

Every incident is stored in ChromaDB as a vector. On the next similar incident, AII retrieves the 3 most similar past cases and uses them as context for the diagnosis.

```
Incident #1 — OOM crash         → stored
Incident #2 — similar OOM       → Known pattern: True
Incident #3 — memory pressure   → Known pattern: True (2 similar)
```

This means AII gets better the more incidents it sees.

---

## Budget

AII uses Claude Sonnet via the Anthropic API. The budget guard (`config.py`) enforces a hard stop at **0.50 EUR per session**.

Typical cost per incident: ~0.02 EUR (Detector + Responder).
At 0 anomalies: **0 EUR** — no API calls made.

---

## Services

| Service | URL | Description |
|---------|-----|-------------|
| App Python | http://localhost:5000 | Demo Flask API |
| Prometheus | http://localhost:9090 | Metrics storage |
| Grafana | http://localhost:3000 | Dashboards (admin/aii2026) |
| Nginx | http://localhost:80 | Reverse proxy |
| Node Exporter | http://localhost:9100 | System metrics |

---

## Author

**Khalil Ghiati** — Electronics & Telecoms Engineer (ENSIL-ENSCI 2025)  
Targeting: DevSecOps / Cloud Security  
[portfolio-khalil-secure.vercel.app](https://portfolio-khalil-secure.vercel.app) | [github.com/Khalil-secure](https://github.com/Khalil-secure)
