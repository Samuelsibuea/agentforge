
# Jalan: python -m agent.serve  → http://127.0.0.1:8787
# Endpoint:
#   POST /v1/chat      {"task": "...", "skill": "research"} → SSE stream jawaban
#   GET  /v1/models    list model dari router
#   GET  /health       hidup/mati
# Server tanpa TUI, client attach lewat HTTP, event JSON per chunk.
import json, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from agent.core import Agent

HOST, PORT = "127.0.0.1", 8787


class Handler(BaseHTTPRequestHandler):
    agent = None  # diisi di serve()

    def log_message(self, *a, **kw):  # tenang, log ke file bukan stdout
        pass

    def _send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(body if isinstance(body, bytes) else json.dumps(body).encode())

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"ok": True, "service": "agentforge-serve"})
        elif self.path == "/v1/models":
            self._send(200, {"models": self.agent.model_chain,
                             "router_tools": list(self.agent.router.tools)})
        else:
            self._send(404, {"ok": False, "error": "unknown path"})

    def do_POST(self):
        if self.path != "/v1/chat":
            self._send(404, {"ok": False, "error": "unknown path"})
            return
        n = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            self._send(400, {"ok": False, "error": "bad json"})
            return
        task = req.get("task", "")
        if not task:
            self._send(400, {"ok": False, "error": "task wajib diisi"})
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        # run blocking di thread biar SSE bisa stream per turn
        out = {}

        def work():
            try:
                out["res"] = self.agent.run(task, skill=req.get("skill", "research"),
                                            verbose=False)
            except Exception as e:
                out["res"] = {"ok": False, "error": f"{type(e).__name__}: {e}"}

        th = threading.Thread(target=work, daemon=True)
        th.start()
        th.join()
        res = out.get("res", {})
        chunk = {"event": "final", "ok": res.get("ok"),
                 "answer": res.get("answer") or res.get("error") or "",
                 "artefak": res.get("artefak"), "stats": res.get("stats")}
        self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode())
        self.wfile.flush()


def serve(port=PORT):
    Handler.agent = Agent()
    srv = ThreadingHTTPServer((HOST, port), Handler)
    print(f"agentforge serve on http://{HOST}:{port} (Ctrl+C berhenti)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    serve()
