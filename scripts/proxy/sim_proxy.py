#!/usr/bin/env python3
"""Proxy de SIMULATION Ollama pour Home Assistant.
Transmet les requetes a Ollama, enregistre la requete EXACTE de HA (prompt, outils, messages), et SUPPRIME tout tool_call de la reponse :
HA ne peut donc jamais executer d outil. Echec ferme : toute erreur de filtrage => HTTP 500."""
import json, sys, time, threading, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
UP = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:11434"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 11435
LOG = "/opt/tinyllm/logs/proxy_sim.jsonl"
LOCK = threading.Lock()
def log(rec):
    with LOCK:
        open(LOG, "a").write(json.dumps(rec, ensure_ascii=False) + "\n")
class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass
    def _send(self, code, body, ctype="application/json"):
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body))); self.end_headers()
        if self.command != "HEAD": self.wfile.write(body)
    def _forward(self, method, body=None):
        r = urllib.request.Request(UP + self.path, data=body, method=method, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(r, timeout=900) as resp: return resp.status, resp.read()
        except urllib.error.HTTPError as e: return e.code, e.read()
    def do_HEAD(self): c, b = self._forward("HEAD"); self._send(c, b)
    def do_GET(self): c, b = self._forward("GET"); self._send(c, b)
    def do_DELETE(self): self._send(403, b"{}")   # jamais de suppression de modele
    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0); raw = self.rfile.read(n) if n else b""
        if self.path != "/api/chat":
            if self.path in ("/api/pull", "/api/create", "/api/push", "/api/delete", "/api/copy"): return self._send(403, b"{}")
            c, b = self._forward("POST", raw); return self._send(c, b)
        try:
            req = json.loads(raw); want_stream = req.get("stream", True); req["stream"] = False
            t = time.time(); c, b = self._forward("POST", json.dumps(req).encode()); dt = time.time() - t
            res = json.loads(b); msg = res.get("message", {}); calls = msg.get("tool_calls") or []
            if calls:
                desc = "; ".join("%s(%s)" % (x["function"]["name"], json.dumps(x["function"].get("arguments"), ensure_ascii=False)) for x in calls)
                msg.pop("tool_calls", None); msg["content"] = "[SIMULATION] appel d outil non execute : " + desc
            assert "tool_calls" not in res.get("message", {}), "tool_calls encore present"
            log({"t": time.strftime("%H:%M:%S"), "latency": round(dt, 1), "model": req.get("model"), "options": req.get("options"), "keep_alive": req.get("keep_alive"), "think": req.get("think"),
                 "n_tools_defs": len(req.get("tools") or []), "messages": req.get("messages"), "tools": req.get("tools"), "stripped_calls": [x["function"] for x in calls], "reply": msg.get("content", "")[:300]})
            out = json.dumps(res, ensure_ascii=False).encode()
            if want_stream: self._send(200, out + b"\n", "application/x-ndjson")
            else: self._send(200, out)
        except Exception as e:
            log({"t": time.strftime("%H:%M:%S"), "error": repr(e)[:300]}); self._send(500, json.dumps({"error": "proxy simulation : " + repr(e)[:200]}).encode())
ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
