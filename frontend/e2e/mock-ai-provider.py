"""Local deterministic OpenAI-compatible provider for Playwright only."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json


class Handler(BaseHTTPRequestHandler):
    def log_message(self, _format, *_args):
        # Request headers and bodies are deliberately not logged.
        return

    def do_GET(self):
        if self.path != "/health":
            self.send_error(404)
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def do_POST(self):
        if self.path != "/v1/chat/completions" or self.headers.get("Authorization") != "Bearer test-only-key":
            self.send_error(401)
            return
        payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        if payload.get("model") != "playwright-mock" or not payload.get("stream"):
            self.send_error(400)
            return
        events = [
            {"choices": [{"delta": {"content": "This is a controlled test response. "}}]},
            {"choices": [{"delta": {"content": "Use saved chart facts as context."}}]},
            {"choices": [], "usage": {"prompt_tokens": 17, "completion_tokens": 11}},
        ]
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        for event in events:
            self.wfile.write(b"data: " + json.dumps(event).encode("utf-8") + b"\n\n")
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
