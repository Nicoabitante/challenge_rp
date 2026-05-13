import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


PROVIDER_COUNTRY = os.getenv("PROVIDER_COUNTRY", "AR").upper()
PROVIDER_CODE = os.getenv("PROVIDER_CODE", f"provider_{PROVIDER_COUNTRY.lower()}")
MOCK_MODE = os.getenv("MOCK_MODE", "success")
PORT = int(os.getenv("PORT", "8080"))
RESPONSE_DELAY_SECONDS = float(os.getenv("RESPONSE_DELAY_SECONDS", "0"))


class ProviderMockHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "provider": PROVIDER_CODE})
            return
        self._send_json(404, {"detail": "Not found"})

    def do_POST(self):
        if self.path != "/invoices":
            self._send_json(404, {"detail": "Not found"})
            return

        payload = self._read_json()
        if RESPONSE_DELAY_SECONDS:
            time.sleep(RESPONSE_DELAY_SECONDS)

        if MOCK_MODE == "timeout":
            time.sleep(60)
        if MOCK_MODE == "transient":
            self._send_json(503, {"detail": "Temporary provider failure", "provider": PROVIDER_CODE})
            return
        if MOCK_MODE == "permanent":
            self._send_json(422, {"detail": "Invoice rejected", "provider": PROVIDER_CODE})
            return

        if PROVIDER_COUNTRY == "BR":
            self._send_json(201, _build_br_response(payload))
            return

        self._send_json(201, _build_ar_response(payload))

    def log_message(self, format, *args):
        return

    def _read_json(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length == 0:
            return {}
        return json.loads(self.rfile.read(content_length).decode("utf-8"))

    def _send_json(self, status_code, body):
        raw_body = json.dumps(body).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw_body)))
        self.end_headers()
        self.wfile.write(raw_body)


def _build_ar_response(payload):
    reference = f"AR-{payload['request_id'][:12]}"
    return {
        "cae": reference,
        "result": "approved",
        "provider": PROVIDER_CODE,
    }


def _build_br_response(payload):
    reference = f"BR-{payload['correlationId'][:12]}"
    return {
        "notaFiscalId": reference,
        "status": "authorized",
        "provider": PROVIDER_CODE,
    }


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), ProviderMockHandler)
    server.serve_forever()
