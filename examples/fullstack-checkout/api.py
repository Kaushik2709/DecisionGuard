"""Loopback-only checkout fixture. The provider is a local function, never a payment API."""

import json
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def provider_amount(amount):
    return int(Decimal(str(amount)) * 100)


class API(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        if self.path != "/checkout":
            self.send_error(404)
            return
        if self.headers.get("Authorization") != "Bearer fixture-token":
            self.send_error(401)
            return
        size = int(self.headers.get("Content-Length", "0"))
        if not 0 < size <= 1024:
            self.send_error(400)
            return
        try:
            body = json.loads(self.rfile.read(size))
            amount = body["amount"]
            if isinstance(amount, bool) or not isinstance(amount, (str, int, float)):
                raise ValueError("Invalid amount")
            result = {"provider_amount": provider_amount(amount), "currency": "INR"}
        except (ValueError, KeyError, TypeError):
            self.send_error(400)
            return
        encoded = json.dumps(result).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 0), API)
    print(server.server_address[1], flush=True)
    server.serve_forever()
