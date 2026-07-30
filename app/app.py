import os
import random
import threading
import time

from flask import Flask, Response, jsonify, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest


REQUESTS = Counter(
    "http_requests_total",
    "HTTP requests served",
    ("method", "route", "status_code"),
)
LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ("method", "route"),
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)

_fault_lock = threading.Lock()
_fault = {"error_rate": 0.0, "latency_ms": 0, "unhealthy": False}


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["FAULT_TOKEN"] = os.getenv("FAULT_TOKEN", "local-development-only")
    app.config["FAULT_INJECTION_ENABLED"] = (
        os.getenv("ENABLE_FAULT_INJECTION", "true").lower() == "true"
    )

    @app.before_request
    def start_timer():
        request._started_at = time.monotonic()

    @app.after_request
    def record_request(response):
        route = request.url_rule.rule if request.url_rule else "unmatched"
        if route not in {"/metrics", "/livez", "/readyz"}:
            REQUESTS.labels(request.method, route, str(response.status_code)).inc()
            LATENCY.labels(request.method, route).observe(
                time.monotonic() - request._started_at
            )
        return response

    @app.get("/")
    def index():
        with _fault_lock:
            error_rate = _fault["error_rate"]
            latency_ms = _fault["latency_ms"]
        if latency_ms:
            time.sleep(latency_ms / 1000)
        if random.random() < error_rate:
            return jsonify(error="injected failure"), 503
        return jsonify(
            service="sre-demo-api",
            version=os.getenv("APP_VERSION", "dev"),
            status="ok",
        )

    @app.get("/livez")
    def live():
        return jsonify(status="alive")

    @app.get("/readyz")
    def ready():
        with _fault_lock:
            unhealthy = _fault["unhealthy"]
        if unhealthy:
            return jsonify(status="not-ready"), 503
        return jsonify(status="ready")

    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(), content_type=CONTENT_TYPE_LATEST)

    @app.post("/admin/fault")
    def set_fault():
        if not app.config["FAULT_INJECTION_ENABLED"]:
            return jsonify(error="not found"), 404
        if request.headers.get("X-Fault-Token") != app.config["FAULT_TOKEN"]:
            return jsonify(error="unauthorized"), 401
        payload = request.get_json(silent=True) or {}
        try:
            error_rate = float(payload.get("error_rate", 0))
            latency_ms = int(payload.get("latency_ms", 0))
            unhealthy = bool(payload.get("unhealthy", False))
        except (TypeError, ValueError):
            return jsonify(error="invalid fault configuration"), 400
        if not 0 <= error_rate <= 1 or not 0 <= latency_ms <= 30_000:
            return jsonify(error="values outside permitted range"), 400
        with _fault_lock:
            _fault.update(
                error_rate=error_rate,
                latency_ms=latency_ms,
                unhealthy=unhealthy,
            )
        return jsonify(_fault)

    @app.delete("/admin/fault")
    def clear_fault():
        if not app.config["FAULT_INJECTION_ENABLED"]:
            return jsonify(error="not found"), 404
        if request.headers.get("X-Fault-Token") != app.config["FAULT_TOKEN"]:
            return jsonify(error="unauthorized"), 401
        with _fault_lock:
            _fault.update(error_rate=0.0, latency_ms=0, unhealthy=False)
        return jsonify(_fault)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
