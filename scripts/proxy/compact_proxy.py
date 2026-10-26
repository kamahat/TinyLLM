#!/usr/bin/env python3
"""Proxy COMPACT Ollama pour Home Assistant (Jarvis), v2 : recherche web interne.
HA -> proxy -> Ollama /api/generate (mode brut). Le proxy :
  - remplace le prompt systeme et les outils de HA par une version compacte (~1,3 k tokens) ;
  - impose temperature 0, 160 tokens maximum, arret sur <|im_end|> ;
  - NE PERMET QU UN TOUR D OUTILS HA par demande (tout nouvel appel au tour 2 est REJETE) ; noms d outils verifies (echec ferme) ;
  - COMPACT_WEB=1 : le modele peut appeler recherche_web ; le proxy l EXECUTE LUI-MEME (SearXNG local, requete anonymisee, 1 recherche max)
    puis relance le modele avec les extraits ; HA ne recoit que la reponse finale ;
  - garde-fou : une reponse chiffree sur un capteur INDISPONIBLE est remplacee ; journaux purges au-dela de 7 jours ;
  - --sim : retire les appels d outils HA (aucune execution possible)."""
import json, sys, os, time, threading, argparse, urllib.request, urllib.error, uuid, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compactlib import *
import compactlib
import websearch as W
ap = argparse.ArgumentParser()
ap.add_argument("--upstream", default=os.environ.get("UPSTREAM", "http://localhost:11434")); ap.add_argument("--port", type=int, default=11436); ap.add_argument("--backend-model", default="")
ap.add_argument("--kind", default="qwen"); ap.add_argument("--ctx", type=int, default=4096); ap.add_argument("--sim", action="store_true"); ap.add_argument("--log", default=os.environ.get("PROXY_LOG", "/opt/tinyllm/logs/compact_proxy.jsonl"))
A = ap.parse_known_args()[0]; LOCK = threading.Lock(); NWRITE = [0]
def log(rec):
    rec["ts"] = time.time()
    with LOCK:
        open(A.log, "a").write(json.dumps(rec, ensure_ascii=False) + NL); NWRITE[0] += 1
        if NWRITE[0] % 200 == 0: W.purge(A.log); W.purge(W.WEBLOG)
def gen_remote(model, prompt):
    body = {"model": model, "prompt": prompt, "raw": True, "stream": False, "keep_alive": -1, "options": {"temperature": 0, "num_predict": 160, "num_ctx": A.ctx, "stop": ["<|im_end|>"]}}
    r = urllib.request.Request(A.upstream + "/api/generate", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=900) as resp: return json.loads(resp.read())
def handle_chat(req, gen):
    """req : requete /api/chat de HA ; gen(prompt)->dict(response, ...) ; renvoie (message, notes, infos)"""
    allowed = {t["function"]["name"] for t in req["tools"]}; notes = []; web_info = None
    msgs, tools, round2 = transform(req["messages"], req["tools"]); res = gen(render(msgs, tools, True, A.kind))
    content, calls, bad = parse_output(res.get("response", "")); webc = [c for c in calls if c["function"]["name"] == "recherche_web"]; hac = [c for c in calls if c["function"]["name"] != "recherche_web"]
    if compactlib.WEB and webc and not hac and not round2:
        q0 = str(webc[0]["function"]["arguments"].get("query", "")).strip(); ents = parse_ha_system(req["messages"][0]["content"]); q = W.sanitize(q0, ents); t0 = time.time(); results = []; err = None
        if len(q) < 3: err = "requete vide apres anonymisation"
        else:
            try: results = W.search(q)
            except Exception as e: err = repr(e)[:90]
        web_info = {"q_model": q0, "q_sent": q, "n": len(results), "sites": [x["site"] for x in results], "err": err, "latency": round(time.time() - t0, 1)}; W.log_query(dict(web_info))
        if err or not results: content = "Je n ai pas pu consulter Internet." if err else "Je n ai rien trouvé sur Internet."; calls = []; notes.append("recherche web : " + (err or "aucun resultat"))
        else:
            m2 = msgs + [{"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "recherche_web", "arguments": {"query": q}}}]}, {"role": "tool", "content": W.format_results(q, results)}]
            r2 = gen(render(m2, tools, True, A.kind)); c2, calls2, _ = parse_output(r2.get("response", "")); res["eval_count"] = (res.get("eval_count") or 0) + (r2.get("eval_count") or 0); res["prompt_eval_count"] = r2.get("prompt_eval_count")
            content = "Je n ai pas trouvé de réponse." if (calls2 or not c2) else c2; calls = []; notes.append("recherche web executee")
            if not (calls2 or not c2) and not W.grounded(c2, W.format_results(q, results)): content = "Je n ai pas trouvé de réponse fiable."; notes.append("nombre non present dans les extraits : reponse ecartee")
    else:
        calls = hac
        if webc and round2: notes.append("recherche_web ignoree au tour 2")
    ok = [x for x in calls if x["function"]["name"] in allowed]
    if len(ok) != len(calls): notes.append("outil inconnu rejete"); content = content or "Je n ai pas compris cette commande."; calls = ok
    if round2 and content and not calls:
        g = guard_unavailable(msgs, content)
        if g != content: notes.append("reponse chiffree remplacee : capteur indisponible"); content = g
        g2 = guard_success(msgs, content)
        if g2 != content: notes.append("refus a tort apres succes remplace"); content = g2
    if round2 and calls: notes.append("nouvel appel d outil REJETE au tour 2"); calls = []; content = "Je n ai pas pu faire ça."
    stripped = [x["function"] for x in calls] if A.sim else []
    if A.sim and calls: content = "[SIMULATION] " + "; ".join("%s(%s)" % (x["function"]["name"], json.dumps(x["function"]["arguments"], ensure_ascii=False)) for x in calls); calls = []
    msg = {"role": "assistant", "content": content}
    if calls: msg["tool_calls"] = [{"id": "call_" + uuid.uuid4().hex[:8], "function": {"index": i, "name": x["function"]["name"], "arguments": x["function"]["arguments"]}} for i, x in enumerate(calls)]
    return msg, notes, {"round2": round2, "tools_sent": len(tools), "msgs": msgs, "res": res, "calls": [x["function"] for x in calls], "stripped": stripped, "bad": bad, "web": web_info}
class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass
    def _send(self, code, body, ctype="application/json"):
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body))); self.end_headers()
        if self.command != "HEAD": self.wfile.write(body)
    def _fwd(self, method, body=None):
        r = urllib.request.Request(A.upstream + self.path, data=body, method=method, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(r, timeout=900) as resp: return resp.status, resp.read()
        except urllib.error.HTTPError as e: return e.code, e.read()
    def do_HEAD(self): c, b = self._fwd("HEAD"); self._send(c, b)
    def do_GET(self):
        if self.path == "/health": return self._send(200, json.dumps({"ok": True, "web": compactlib.WEB, "sim": A.sim}).encode())
        c, b = self._fwd("GET"); self._send(c, b)
    def do_DELETE(self): self._send(403, b"{}")
    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0); raw = self.rfile.read(n) if n else b""
        if self.path in ("/api/pull", "/api/create", "/api/push", "/api/delete", "/api/copy"): return self._send(403, b"{}")
        if self.path != "/api/chat": c, b = self._fwd("POST", raw); return self._send(c, b)
        try:
            req = json.loads(raw)
            if not req.get("tools"): c, b = self._fwd("POST", raw); return self._send(c, b)
            want_stream = req.get("stream", True); model = A.backend_model or req.get("model"); t = time.time()
            msg, notes, info = handle_chat(req, lambda p: gen_remote(model, p)); dt = time.time() - t; res = info["res"]
            out = {"model": req.get("model"), "created_at": datetime.datetime.utcnow().isoformat() + "Z", "message": msg, "done": True, "done_reason": "stop", "total_duration": res.get("total_duration"), "prompt_eval_count": res.get("prompt_eval_count"), "eval_count": res.get("eval_count")}
            log({"t": time.strftime("%H:%M:%S"), "latency": round(dt, 1), "model": model, "round2": info["round2"], "tools_sent": info["tools_sent"], "prompt_tokens": res.get("prompt_eval_count"), "gen_tokens": res.get("eval_count"),
                 "user": [m["content"] for m in info["msgs"] if m["role"] == "user"][-1][:120], "calls": info["calls"], "stripped_calls": info["stripped"], "reply": msg["content"][:120], "bad_format": info["bad"], "notes": notes, "web": (info["web"] or {}).get("n")})
            enc = json.dumps(out, ensure_ascii=False).encode()
            self._send(200, enc + b"\n", "application/x-ndjson") if want_stream else self._send(200, enc)
        except Exception as e:
            log({"t": time.strftime("%H:%M:%S"), "error": repr(e)[:300]}); self._send(500, json.dumps({"error": "proxy compact : " + repr(e)[:200]}).encode())
if __name__ == "__main__":
    W.purge(A.log); W.purge(W.WEBLOG)
    ThreadingHTTPServer(("0.0.0.0", A.port), H).serve_forever()
