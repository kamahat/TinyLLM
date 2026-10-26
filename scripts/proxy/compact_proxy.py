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
import json, sys, os, re, time, threading, argparse, urllib.request, urllib.error, uuid, datetime, hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compactlib import *
import compactlib
import websearch as W
import meteo as M
ap = argparse.ArgumentParser()
ap.add_argument("--upstream", default=os.environ.get("UPSTREAM", "http://localhost:11434")); ap.add_argument("--port", type=int, default=11436); ap.add_argument("--backend-model", default="")
ap.add_argument("--kind", default="qwen"); ap.add_argument("--ctx", type=int, default=4096); ap.add_argument("--sim", action="store_true"); ap.add_argument("--log", default=os.environ.get("PROXY_LOG", "/opt/tinyllm/logs/compact_proxy.jsonl"))
A = ap.parse_known_args()[0]; LOCK = threading.Lock(); NWRITE = [0]
ANNOUNCE = os.environ.get("ANNOUNCE", "0") == "1"; ANN_RE = re.compile(r"^Je cherche sur Internet : .*?\. Un instant\.\s*", re.S)
def announce_text(user_text, q):
    """Phrase dite AVANT la reponse d une recherche web : reprend la question de l utilisateur (preuve que l IA a compris) et previent qu il faut patienter."""
    s = re.sub(r"\s+", " ", user_text or "").strip().rstrip("?!. ")
    subject = (s[:1].lower() + s[1:]) if 6 <= len(s) <= 100 else q
    return "Je cherche sur Internet : %s. Un instant. " % subject
LAST = os.path.join(os.path.dirname(os.path.abspath(A.log)), "last_ha_request.json"); WARM = {"lock": threading.Lock(), "hash": None, "state": "jamais"}
def log(rec):
    rec["ts"] = time.time()
    with LOCK:
        open(A.log, "a").write(json.dumps(rec, ensure_ascii=False) + NL); NWRITE[0] += 1
        if NWRITE[0] % 200 == 0: W.purge(A.log); W.purge(W.WEBLOG)
def gen_remote(model, prompt, n=160):
    body = {"model": model, "prompt": prompt, "raw": True, "stream": False, "keep_alive": -1, "options": {"temperature": 0, "num_predict": n, "num_ctx": A.ctx, "stop": [stop_token(A.kind)]}}
    r = urllib.request.Request(A.upstream + "/api/generate", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=900) as resp: return json.loads(resp.read())
def handle_chat(req, gen, announce=None):
    """req : requete /api/chat de HA ; gen(prompt)->dict(response, ...) ; renvoie (message, notes, infos)"""
    allowed = {t["function"]["name"] for t in req["tools"]}; notes = []; web_info = None
    if any(m["role"] == "assistant" and ANN_RE.match(m.get("content") or "") for m in req["messages"]):   # l annonce vocale ne doit pas polluer l historique vu par le modele
        req = dict(req, messages=[dict(m, content=ANN_RE.sub("", m.get("content") or "")) if m["role"] == "assistant" and ANN_RE.match(m.get("content") or "") else m for m in req["messages"]])
    users = [i for i, m in enumerate(req["messages"]) if m["role"] == "user"]
    if users:   # corrections STT sur la derniere phrase de l utilisateur (liste rechargee a chaud)
        fixed, fn = apply_stt_fixes(req["messages"][users[-1]].get("content") or "")
        if fn: req = dict(req, messages=[dict(m, content=fixed) if i == users[-1] else m for i, m in enumerate(req["messages"])]); notes += fn
    msgs, tools, round2 = transform(req["messages"], req["tools"])
    fc = fast_confirm(req["messages"]) if round2 else None
    if fc:   # ordre reussi (outil d action, succes complet) : pas de 2e appel LLM, confirmation immediate
        notes.append("confirmation directe : 2e appel LLM evite")
        return {"role": "assistant", "content": fc}, notes, {"round2": True, "tools_sent": len(tools), "msgs": msgs, "res": {}, "calls": [], "stripped": [], "bad": False, "web": None}
    res = gen(render(msgs, tools, True, A.kind))
    content, calls, bad = parse_output(res.get("response", "")); webc = [c for c in calls if c["function"]["name"] == "recherche_web"]; hac = [c for c in calls if c["function"]["name"] != "recherche_web"]
    if compactlib.WEB and webc and not hac and not round2:
        q0 = str(webc[0]["function"]["arguments"].get("query", "")).strip(); ents = parse_ha_system(req["messages"][0]["content"]); q = W.sanitize(q0, ents); t0 = time.time(); results = []; err = None
        meteo_txt = None
        if M.ENABLED and len(q) >= 3:   # questions de METEO : API Open-Meteo (valeurs exactes) a la place des extraits de recherche ; en cas d echec -> recherche web habituelle
            try: meteo_txt = M.answer(q, [m.get("content") or "" for m in req["messages"] if m["role"] == "user"][-1])
            except Exception as e: notes.append("meteo : echec " + repr(e)[:70])
        if announce and not meteo_txt and len(q) >= 3:   # recherche web longue (~15 s) : annonce vocale immediate (streaming)
            try: announce(announce_text([m.get("content") or "" for m in req["messages"] if m["role"] == "user"][-1], q)); notes.append("annonce vocale envoyee")
            except Exception as e: notes.append("annonce impossible : " + repr(e)[:60])
        if meteo_txt: results = [{"titre": "Open-Meteo", "extrait": meteo_txt[0], "site": "open-meteo.com"}]
        elif len(q) < 3: err = "requete vide apres anonymisation"
        else:
            try: results = W.search(q)
            except Exception as e: err = repr(e)[:90]
        web_info = {"q_model": q0, "q_sent": q, "n": len(results), "sites": [x["site"] for x in results], "err": err, "latency": round(time.time() - t0, 1)}; W.log_query(dict(web_info))
        if meteo_txt: content = meteo_txt[0]; calls = []; notes.append("meteo Open-Meteo : " + json.dumps(meteo_txt[1], ensure_ascii=False))
        elif err or not results: content = "Je n ai pas pu consulter Internet." if err else "Je n ai rien trouvé sur Internet."; calls = []; notes.append("recherche web : " + (err or "aucun resultat"))
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
def save_last(req):
    """Memorise la derniere requete REELLE de HA (systeme + outils) pour le prechauffage automatique ; n ecrit que si elle change."""
    try:
        sysm = req["messages"][0]["content"]; h = hashlib.md5((sysm + json.dumps([t["function"]["name"] for t in req["tools"]])).encode()).hexdigest()
        if WARM["hash"] == h: return
        tmp = LAST + ".tmp"; json.dump({"system": sysm, "tools": req["tools"], "saved": time.strftime("%Y-%m-%d %H:%M:%S")}, open(tmp, "w"), ensure_ascii=False); os.replace(tmp, LAST); WARM["hash"] = h
    except Exception as e: log({"t": time.strftime("%H:%M:%S"), "error": "memorisation requete : " + repr(e)[:120]})
def warm(reason):
    """Prechauffe le cache d Ollama avec la derniere requete reelle (mise en forme compacte identique). N appelle jamais HA : aucun ordre possible."""
    if not WARM["lock"].acquire(blocking=False): return "deja en cours"
    try:
        d = json.load(open(LAST)); m = A.backend_model
        if not m: return "pas de modele impose"
        msgs, tools, _ = transform([{"role": "system", "content": d["system"]}, {"role": "user", "content": "Combien font un plus un ?"}], d["tools"])
        t = time.time(); r = gen_remote(m, render(msgs, tools, True, A.kind), 2); dt = time.time() - t
        WARM["state"] = "%s | %s | %.1fs | %s tokens" % (time.strftime("%H:%M:%S"), reason, dt, r.get("prompt_eval_count")); log({"t": time.strftime("%H:%M:%S"), "warm": reason, "latency": round(dt, 1), "prompt_tokens": r.get("prompt_eval_count")}); return WARM["state"]
    except FileNotFoundError: return "aucune requete reelle memorisee"
    except Exception as e: WARM["state"] = "echec : " + repr(e)[:100]; return WARM["state"]
    finally: WARM["lock"].release()
def model_loaded():
    try:
        with urllib.request.urlopen(A.upstream + "/api/ps", timeout=10) as resp: ms = json.loads(resp.read()).get("models", [])
        return any((x.get("name") or "").split(":")[0] == A.backend_model.split(":")[0] for x in ms)
    except Exception: return True   # dans le doute : ne pas prechauffer
def warm_loop():
    time.sleep(5); warm("demarrage du proxy")
    while True:
        time.sleep(120)
        if A.backend_model and not model_loaded(): warm("modele decharge d Ollama")
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
        if self.path == "/health": return self._send(200, json.dumps({"ok": True, "web": compactlib.WEB, "sim": A.sim, "meteo": M.ENABLED, "fast_confirm": compactlib.FAST_CONFIRM, "annonce": ANNOUNCE, "stt_fixes": len(compactlib._fix_rules()), "warm": WARM["state"]}, ensure_ascii=False).encode())
        c, b = self._fwd("GET"); self._send(c, b)
    def do_DELETE(self): self._send(403, b"{}")
    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0); raw = self.rfile.read(n) if n else b""
        if self.path in ("/api/pull", "/api/create", "/api/push", "/api/delete", "/api/copy"): return self._send(403, b"{}")
        if self.path == "/warm": return self._send(200, json.dumps({"warm": warm("demande manuelle")}, ensure_ascii=False).encode())
        if self.path != "/api/chat": c, b = self._fwd("POST", raw); return self._send(c, b)
        sst = {"on": False}
        def chunk(obj):   # reponse en flux NDJSON (Transfer-Encoding: chunked) : le 1er bloc part immediatement, le dernier (done) contient la reponse finale
            data = (json.dumps(obj, ensure_ascii=False) + "\n").encode()
            if not sst["on"]:
                self.send_response(200); self.send_header("Content-Type", "application/x-ndjson"); self.send_header("Transfer-Encoding", "chunked"); self.end_headers(); sst["on"] = True
            self.wfile.write((("%x" + "\r\n") % len(data)).encode() + data + b"\r\n"); self.wfile.flush()
        def end_chunks(): self.wfile.write(b"0\r\n\r\n"); self.wfile.flush()
        try:
            req = json.loads(raw)
            if not req.get("tools"): c, b = self._fwd("POST", raw); return self._send(c, b)
            want_stream = req.get("stream", True); model = A.backend_model or req.get("model"); t = time.time()
            ann = (lambda text: chunk({"model": req.get("model"), "created_at": datetime.datetime.utcnow().isoformat() + "Z", "message": {"role": "assistant", "content": text}, "done": False})) if (want_stream and ANNOUNCE) else None
            msg, notes, info = handle_chat(req, lambda p: gen_remote(model, p), announce=ann); dt = time.time() - t; res = info["res"]
            if not A.sim: save_last(req)
            out = {"model": req.get("model"), "created_at": datetime.datetime.utcnow().isoformat() + "Z", "message": msg, "done": True, "done_reason": "stop", "total_duration": res.get("total_duration"), "prompt_eval_count": res.get("prompt_eval_count"), "eval_count": res.get("eval_count")}
            log({"t": time.strftime("%H:%M:%S"), "latency": round(dt, 1), "model": model, "round2": info["round2"], "tools_sent": info["tools_sent"], "prompt_tokens": res.get("prompt_eval_count"), "gen_tokens": res.get("eval_count"),
                 "user": [m["content"] for m in info["msgs"] if m["role"] == "user"][-1][:120], "calls": info["calls"], "stripped_calls": info["stripped"], "reply": msg["content"][:120], "bad_format": info["bad"], "notes": notes, "web": (info["web"] or {}).get("n")})
            enc = json.dumps(out, ensure_ascii=False).encode()
            if sst["on"]: chunk(out); end_chunks()
            else: self._send(200, enc + b"\n", "application/x-ndjson") if want_stream else self._send(200, enc)
        except Exception as e:
            log({"t": time.strftime("%H:%M:%S"), "error": repr(e)[:300]})
            if sst["on"]:   # l annonce est deja partie : terminer proprement le flux avec un message d erreur parlable
                try: chunk({"model": "proxy", "created_at": datetime.datetime.utcnow().isoformat() + "Z", "message": {"role": "assistant", "content": "Je n ai pas pu terminer la recherche."}, "done": True, "done_reason": "stop"}); end_chunks()
                except Exception: pass
            else: self._send(500, json.dumps({"error": "proxy compact : " + repr(e)[:200]}).encode())
if __name__ == "__main__":
    W.purge(A.log); W.purge(W.WEBLOG)
    if not A.sim and A.backend_model: threading.Thread(target=warm_loop, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", A.port), H).serve_forever()
