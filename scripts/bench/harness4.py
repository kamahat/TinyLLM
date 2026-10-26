#!/usr/bin/env python3
"""Banc COMPACT : requete HA (prompt tablette + historique) -> compactlib.transform -> Ollama /api/generate brut -> analyse. Simule le tour 2 (succes/erreur/etat reel). N execute rien."""
import argparse, json, re, sys, time, unicodedata, urllib.request, statistics, os
sys.path.insert(0, "/opt/tinyllm/compact")
from compactlib import *
D = "/opt/tinyllm/data/"
ap = argparse.ArgumentParser()
ap.add_argument("--host", default="http://localhost:11434"); ap.add_argument("--model", required=True); ap.add_argument("--kind", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--ctx", type=int, default=4096); ap.add_argument("--every", type=int, default=1); ap.add_argument("--cats", default=""); ap.add_argument("--hist", default="none")
ap.add_argument("--force-error", action="store_true"); ap.add_argument("--adv", action="store_true"); ap.add_argument("--real", default=D + "ha_tablet_prompt.json"); ap.add_argument("--recette", default=D + "recette.json")
a = ap.parse_args(); R = json.load(open(a.recette)); REAL = json.load(open(a.real)); SYSTEM = REAL["system"]; TOOLS = REAL["tools"]
def norm(s):
    s = unicodedata.normalize("NFD", str(s).lower()); s = "".join(c for c in s if unicodedata.category(c) != "Mn"); return " ".join(re.sub(r"[^a-z0-9 ]+", " ", s).split())
PRE = {"HassTurnOn": "intent__", "HassTurnOff": "intent__", "HassSetPosition": "intent__", "HassStopMoving": "intent__", "HassLightSet": "light__", "GetLiveContext": "homeassistant__", "GetDateTime": "llm__", "HassClimateSetTemperature": "climate__", "get_items": "todo__", "HassListAddItem": "todo__", "HassListCompleteItem": "todo__", "HassListRemoveItem": "todo__"}
real = lambda t: None if t is None else PRE.get(t, "script__") + t
pass  # R charge plus haut (--recette)
ADV = [("Allume la led Opale blanche", "HassTurnOn", {"name": "led Opale blanche"}), ("Éteins la lumière de la piscine", "HassTurnOff", {"name": "Lumiere Piscine"}), ("Allume la lumière de la piscine", "HassTurnOn", {"name": "Lumiere Piscine"}),
       ("Allume la led blanche du salon", "HassTurnOn", {"name": "led Opale blanche"}), ("Mets la lampe Opale", "HassTurnOn", {"name": "led Opale blanche"}), ("Éteins la piscine", "HassTurnOff", {"name": "Lumiere Piscine"})]
if a.adv: R = [{"id": "9%02d" % i, "cat": "adv", "text": t, "tool": tl, "args": ar, "no_tool": False} for i, (t, tl, ar) in enumerate(ADV)]
if a.cats: R = [r for r in R if r["cat"] in a.cats.split(",")]
if a.every > 1: R = R[:: a.every]
def U(t): return {"role": "user", "content": t}
def A_(t): return {"role": "assistant", "content": t}
HISTS = [[U("Allume, lumière, salon."), A_("Allumé")], [U("Ferme les volets du salon."), A_("Fermeture en cours")], [U("Éteins la lumière tapisserie."), A_("Éteint")],
         [U("Allume la lumière du bureau de Alex."), A_("Allumé"), U("Éteins la cuisine."), A_("Éteint")], [U("Quelle est la capitale de l Italie ?"), A_("Rome.")], [U("Ouvre les volets de la chambre d amis."), A_("Ouverture en cours")],
         [U("Allume le cinéma"), {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "script__cinema_on", "arguments": {}}}]}, {"role": "tool", "content": json.dumps({"success": True})}, A_("C est fait.")]]
hist_for = lambda r: [] if a.hist == "none" else HISTS[int(r["id"]) % len(HISTS)]
EN = {e["name"]: e["state"] for e in json.load(open(D + "ha_exposed.json"))}
def live_text():
    t = "Live Context: An overview of the areas and the devices in this smart home:" + NL
    for e in parse_ha_system(SYSTEM): t += "- names: %s%s  domain: %s%s  state: %s%s" % (e["name"], NL, e["domain"], NL, "\x27" + str(EN.get(e["name"], "unknown")) + "\x27", NL) + (("  areas: " + e["areas"] + NL) if e["areas"] else "")
    return t
INFO = {"dehors": ["22"], "douche": ["51"], "quelqu": ["oui", "quelqu"], "météo": ["nuageux"], "lumière du salon est": ["non", "éteint"], "volets du salon sont": ["oui", "ouvert"], "cuisine est allumée": ["oui", "allum"]}
REFUS = re.compile(r"(pas|ne .{0,20}trouve|désolé|impossible|échou|n.ai pas|ne connais|erreur)", re.I)
def gen(msgs, tools):
    p = render(msgs, tools, True, a.kind); body = {"model": a.model, "prompt": p, "raw": True, "stream": False, "keep_alive": -1, "options": {"temperature": 0, "num_predict": 160, "num_ctx": a.ctx, "stop": [stop_token(a.kind)]}}
    t = time.time(); r = json.loads(urllib.request.urlopen(urllib.request.Request(a.host + "/api/generate", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}), timeout=900).read())
    return r, time.time() - t
def val_ok(exp, act):
    if isinstance(act, list): act = act[0] if act else ""
    if isinstance(exp, (int, float)):
        try: return float(act) == float(exp)
        except Exception: return False
    e, c = norm(exp), norm(act); return bool(e) and bool(c) and (e in c or c in e)
res = []
for i, r in enumerate(R):
    exp = real(r["tool"]); ha = [{"role": "system", "content": SYSTEM}] + hist_for(r) + [U(r["text"])]
    try:
        m1, t1, _ = transform(ha, TOOLS); out, dt = gen(m1, t1)
    except Exception as ex: res.append({**r, "pass": False, "error": repr(ex)[:150]}); print(r["id"], "ERREUR", repr(ex)[:90], flush=True); continue
    txt, calls, bad = parse_output(out.get("response", "")); allowed = {t["function"]["name"] for t in TOOLS}; calls = [c for c in calls if c["function"]["name"] in allowed]; first = calls[0]["function"] if calls else None
    ok = (first is None) if r["no_tool"] else (bool(first) and first["name"] == exp and all(val_ok(v, (first.get("arguments") or {}).get(k)) for k, v in r["args"].items()))
    rec = {**r, "pass": ok, "got": first, "reply": txt[:140], "latency": round(dt, 2), "prompt_tokens": out.get("prompt_eval_count"), "bad_format": bad}
    if first:
        errmode = a.force_error or a.adv or not ok
        if errmode: result = {"error": "MatchFailedError"} if int(r["id"]) % 2 else {"error": "IntentHandleError", "error_text": "Service call failed"}
        elif first["name"] == "homeassistant__GetLiveContext": result = {"result": live_text()}
        elif first["name"] == "llm__GetDateTime": result = {"date": "2026-10-25", "time": "10:27:00", "timezone": "CEST", "weekday": "Sunday"}
        else: result = {"speech": {}, "response_type": "action_done", "data": {"targets": [], "success": [{"name": str(r["args"].get("name", "x")), "type": "entity", "id": "x.y"}], "failed": []}}
        m2, t2, r2 = transform(ha + [{"role": "assistant", "content": "", "tool_calls": [{"function": first}]}, {"role": "tool", "content": json.dumps(result, ensure_ascii=False)}], TOOLS)
        assert r2, "tour 2 non detecte"
        o2, _ = gen(m2, t2); f2, c2, _ = parse_output(o2.get("response", "")); rec["extra_calls"] = len(c2)
        if c2: f2 = "Je n ai pas pu faire ça."          # le proxy rejette un nouvel appel au tour 2
        rec["final"] = f2[:140]
        if errmode: rec["false_success"] = not REFUS.search(f2)
        else:
            rec["false_refusal"] = bool(REFUS.search(f2))
            for k, w in INFO.items():
                if first["name"] == "homeassistant__GetLiveContext" and k in r["text"].lower(): rec["info_ok"] = any(x in f2.lower() for x in w)
    res.append(rec)
    print("%s %-8s %s %5.1fs | %s | %s" % (r["id"], r["cat"], "OK " if ok else "KO ", dt, json.dumps(first, ensure_ascii=False)[:80] if first else "(texte) " + txt[:40], ("final: " + rec.get("final", "")[:50]) if first else ""), flush=True)
os.makedirs(os.path.dirname(a.out), exist_ok=True); json.dump({"model": a.model, "args": vars(a), "results": res}, open(a.out, "w"), ensure_ascii=False, indent=1)
act = [x for x in res if not x["no_tool"]]; ok = [x for x in res if x.get("pass")]; lat = [x["latency"] for x in res if "latency" in x]
print(NL + "== %s (format compact, kind=%s, hist=%s) ==" % (a.model, a.kind, a.hist)); print("reussite : %d/%d (%.0f%%) | ordres : %d/%d" % (len(ok), len(res), 100 * len(ok) / max(1, len(res)), sum(1 for x in act if x.get("pass")), len(act)))
for c in sorted(set(x["cat"] for x in res)): g = [x for x in res if x["cat"] == c]; print("  %-8s %d/%d" % (c, sum(1 for x in g if x.get("pass")), len(g)))
txt = [x for x in act if not x.get("got") and x.get("reply")]; print("ORDRES SANS APPEL D OUTIL (texte seul) : %d/%d" % (len(txt), len(act)))
for x in txt[:6]: print("   ", x["id"], x["text"], "->", x["reply"][:60])
tr = [x for x in res if x["no_tool"]]; print("pieges avec appel d outil : %d/%d | formats casses : %d | appels apres tour 2 : %d" % (sum(1 for x in tr if x.get("got")), len(tr), sum(1 for x in res if x.get("bad_format")), sum(x.get("extra_calls", 0) for x in res)))
fs = [x for x in res if "false_success" in x]; fr = [x for x in res if "false_refusal" in x]; ii = [x for x in res if "info_ok" in x]
if fs: print("apres ERREUR : fausses confirmations %d/%d" % (sum(x["false_success"] for x in fs), len(fs)))
if fr: print("apres SUCCES : refus a tort %d/%d" % (sum(x["false_refusal"] for x in fr), len(fr)))
if ii: print("questions d etat (valeur correcte dans la reponse) : %d/%d" % (sum(x["info_ok"] for x in ii), len(ii)))
if lat: print("latence generation : moyenne %.1fs | mediane %.1fs | tokens prompt ~%s" % (statistics.mean(lat), statistics.median(lat), res[0].get("prompt_tokens")))
