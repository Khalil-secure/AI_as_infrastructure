"""
AII Demo App — Flask API simple
Expose /metrics pour Prometheus
Expose /health pour les checks
"""

import os
import time
import random
from flask import Flask, jsonify
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from flask import Response

app = Flask(__name__)

# ── Métriques Prometheus ──────────────────────────────────────────────────────
REQUEST_COUNT   = Counter("app_requests_total", "Total requests", ["method", "endpoint"])
REQUEST_LATENCY = Histogram("app_request_latency_seconds", "Request latency")
APP_VERSION     = Gauge("app_version_info", "App version", ["version"])

APP_VERSION.labels(version=os.environ.get("APP_VERSION", "1.0.0")).set(1)

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    REQUEST_COUNT.labels(method="GET", endpoint="/").inc()
    return jsonify({
        "service": "AII Demo App",
        "status":  "running",
        "version": os.environ.get("APP_VERSION", "1.0.0")
    })

@app.route("/health")
def health():
    return jsonify({"status": "healthy", "timestamp": time.time()})

@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

@app.route("/work")
def work():
    """Simule du travail CPU."""
    REQUEST_COUNT.labels(method="GET", endpoint="/work").inc()
    with REQUEST_LATENCY.time():
        result = sum(i * i for i in range(10000))
    return jsonify({"result": result, "status": "done"})

@app.route("/stress")
def stress():
    """Endpoint qui consomme de la mémoire — pour tester AII."""
    REQUEST_COUNT.labels(method="GET", endpoint="/stress").inc()
    # Alloue 50MB temporairement
    data = bytearray(50 * 1024 * 1024)
    time.sleep(1)
    del data
    return jsonify({"status": "stress test done"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
