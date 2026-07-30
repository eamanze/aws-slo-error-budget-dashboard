import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


ARTIFACT = Path(os.getenv("INCIDENT_LOG", "/artifacts/alert-events.jsonl"))


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/healthz":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
            return
        self.send_error(404)

    def do_POST(self):
        if self.path != "/alerts":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            record = {
                "received_at": datetime.now(timezone.utc).isoformat(),
                "payload": payload,
            }
            ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
            with ARTIFACT.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, separators=(",", ":")) + "\n")
        except (ValueError, json.JSONDecodeError) as exc:
            self.send_error(400, str(exc))
            return
        self.send_response(204)
        self.end_headers()

    def log_message(self, format, *args):
        print("%s - %s" % (self.address_string(), format % args), flush=True)


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 8081), Handler).serve_forever()

