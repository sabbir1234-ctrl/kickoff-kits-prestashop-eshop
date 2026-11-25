"""Local web server for the Kit Assistant demo.  Run:  python server.py  ->  http://localhost:8000"""
import json
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from agent import ORDERS, PRODUCTS, Session, load_config

HERE = Path(__file__).resolve().parent
CFG = load_config()
SESSIONS = {}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            return self._send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
        if self.path == "/api/testdata":
            return self._send(200, {"products": PRODUCTS, "orders": [{"ref": o["ref"], "email": o["email"], "status": o["status"]} for o in ORDERS], "model": CFG["GROQ_MODEL"]})
        self._send(404, {"error": "not found"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        sid = body.get("session") or str(uuid.uuid4())
        if self.path == "/api/reset":
            SESSIONS.pop(sid, None)
            return self._send(200, {"ok": True})
        if self.path == "/api/chat":
            s = SESSIONS.setdefault(sid, Session())
            try:
                r = s.chat(str(body.get("message", ""))[:2000], CFG)
                r["session"] = sid
                return self._send(200, r)
            except Exception as e:  # show API errors to the user instead of crashing
                return self._send(502, {"error": str(e)[:400], "session": sid})
        self._send(404, {"error": "not found"})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print(f"Kit Assistant running on http://localhost:8000  (model {CFG['GROQ_MODEL']})")
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
