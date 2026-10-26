#!/usr/bin/env python3
"""Banc v2 : requete IDENTIQUE a celle de HA (prompt + outils captures par le proxy de simulation) + suite de conversation SIMULEE
(resultat d outil succes/erreur) pour mesurer si le modele s arrete ou boucle. Appelle directement Ollama : n execute rien dans HA."""
import argparse, json, re, time, unicodedata, urllib.request, statistics, os
D = "/opt/tinyllm/data/"
ap = argparse.ArgumentParser()
ap.add_argument("--host", default="http://localhost:11434"); ap.add_argument("--model", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--every", type=int, default=1); ap.add_argument("--limit", type=int, default=0); ap.add_argument("--cats", default="")
ap.add_argument("--num-ctx", type=int, default=6144); ap.add_argument("--timeout", type=int, default=900); ap.add_argument("--max-iter", type=int, default=4)
ap.add_argument("--no-loop", action="store_true"); ap.add_argument("--force-error", action="store_true"); ap.add_argument("--adv", action="store_true"); ap.add_argument("--real", default=D + "ha_real_prompt.json"); ap.add_argument("--hist", default="none")
a = ap.parse_args()
REAL = json.load(open(a.real)); SYSTEM = REAL["system"]; TOOLS = REAL["tools"]
def norm(s):
    s = unicodedata.normalize("NFD", str(s).lower()); s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", s).split())
PRE = {"HassTurnOn": "intent__", "HassTurnOff": "intent__", "HassSetPosition": "intent__", "HassStopMoving": "intent__", "HassLightSet": "light__", "GetLiveContext": "homeassistant__",
       "GetDateTime": "llm__", "HassClimateSetTemperature": "climate__", "get_items": "todo__", "HassListAddItem": "todo__", "HassListCompleteItem": "todo__", "HassListRemoveItem": "todo__"}
def real(t):
    if t is None: return None
    return PRE.get(t, "script__") + t
R = json.load(open(D + "recette.json"))
if a.cats: R = [r for r in R if r["cat"] in a.cats.split(",")]
if a.every > 1: R = R[:: a.every]
if a.limit: R = R[: a.limit]
ADV = [("Allume la led Opale blanche", "HassTurnOn", {"name": "led Opale blanche"}), ("Éteins la lumière de la piscine", "HassTurnOff", {"name": "Lumiere Piscine"}), ("Allume la lumière de la piscine", "HassTurnOn", {"name": "Lumiere Piscine"}),
       ("Allume la led blanche du salon", "HassTurnOn", {"name": "led Opale blanche"}), ("Mets la lampe Opale", "HassTurnOn", {"name": "led Opale blanche"}), ("Éteins la piscine", "HassTurnOff", {"name": "Lumiere Piscine"})]
if a.adv: R = [{"id": "9%02d" % i, "cat": "adv", "text": t, "tool": tl, "args": ar, "no_tool": False} for i, (t, tl, ar) in enumerate(ADV)]
def U(t): return {"role": "user", "content": t}
def A(t): return {"role": "assistant", "content": t}
HISTS = [[U("Allume, lumière, salon."), A("Allumé")], [U("Ferme les volets du salon."), A("Fermeture en cours")], [U("Éteins la lumière tapisserie."), A("Éteint")],
         [U("Allume la lumière du bureau de Alex."), A("Allumé"), U("Éteins la cuisine."), A("Éteint")], [U("Quelle est la capitale de l Italie ?"), A("Rome.")],
         [U("Ouvre les volets de la chambre d amis."), A("Ouverture en cours")], [U("Allume le cinéma"), {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "script__cinema_on", "arguments": {}}}]}, {"role": "tool", "tool_name": "script__cinema_on", "content": "{" + chr(34) + "success" + chr(34) + ": true}"}, A("C est fait.")]]
def hist_for(r): return [] if a.hist == "none" else HISTS[int(r["id"]) % len(HISTS)]
def chat(messages):
    body = {"model": a.model, "stream": False, "think": False, "messages": messages, "tools": TOOLS, "options": {"temperature": 0, "num_ctx": a.num_ctx, "num_predict": 200}}
    t = time.time(); r = json.loads(urllib.request.urlopen(urllib.request.Request(a.host + "/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}), timeout=a.timeout).read())
    return r, time.time() - t
def val_ok(exp, act):
    if isinstance(act, list): act = act[0] if act else ""
    if isinstance(exp, (int, float)):
        try: return float(act) == float(exp)
        except Exception: return False
    e, c = norm(exp), norm(act); return bool(e) and bool(c) and (e in c or c in e)
SUCCESS = lambda n: {"speech": {}, "response_type": "action_done", "data": {"targets": [], "success": [{"name": n, "type": "entity", "id": "x.y"}], "failed": []}}
ERRORS = [{"error": "MatchFailedError"}, {"error": "MatchFailedError", "error_text": "No entities matched name"}, {"error": "NoStatesMatchedError"}, {"error": "IntentHandleError", "error_text": "Service call failed"}]
res = []
for i, r in enumerate(R):
    exp = real(r["tool"]); msgs = [{"role": "system", "content": SYSTEM}] + hist_for(r) + [{"role": "user", "content": r["text"]}]
    try: resp, dt = chat(msgs)
    except Exception as ex: res.append({**r, "pass": False, "error": repr(ex)[:200]}); print(i + 1, len(R), r["id"], "ERREUR", repr(ex)[:80], flush=True); continue
    m = resp["message"]; calls = [c["function"] for c in m.get("tool_calls", [])]; first = calls[0] if calls else None
    if r["no_tool"]: ok = first is None
    else: ok = bool(first) and first["name"] == exp and all(val_ok(v, (first.get("arguments") or {}).get(k)) for k, v in r["args"].items())
    rec = {**r, "tool_real": exp, "pass": ok, "got": first, "reply": (m.get("content") or "")[:140], "latency": round(dt, 2), "prompt_tokens": resp.get("prompt_eval_count"), "gen_tokens": resp.get("eval_count")}
    # suite simulee : succes si l appel est le bon, erreur sinon (ou si la phrase ne devait appeler aucun outil)
    if first and not a.no_loop:
        depth = 1; cur = msgs; call = first; final = ""; names = [first["name"]]
        while depth <= a.max_iter and call:
            result = SUCCESS(r["args"].get("name", "x")) if ok and depth == 1 and not (a.force_error or a.adv) else ERRORS[(int(r["id"]) + depth) % len(ERRORS)]
            cur = cur + [{"role": "assistant", "content": "", "tool_calls": [{"function": call}]}, {"role": "tool", "tool_name": call["name"], "content": json.dumps(result, ensure_ascii=False)}]
            try: resp2, _ = chat(cur)
            except Exception as ex: final = "ERREUR " + repr(ex)[:60]; break
            m2 = resp2["message"]; c2 = [c["function"] for c in m2.get("tool_calls", [])]
            if not c2: final = (m2.get("content") or "")[:140]; call = None; break
            call = c2[0]; names.append(call["name"]); depth += 1
        rec.update({"loop_calls": len(names), "loop_names": names, "loop_final": final, "loop_ended": call is None})
    res.append(rec)
    print("%d/%d %s %-8s %s %5.1fs | %s | suite: %s" % (i + 1, len(R), r["id"], r["cat"], "OK " if ok else "KO ", dt, json.dumps(first, ensure_ascii=False)[:80] if first else "(aucun outil) " + (m.get("content") or "")[:40].replace(chr(10), " "),
          ("%d appel(s), fin=%s" % (rec["loop_calls"], rec["loop_final"][:40].replace(chr(10), " ")) if "loop_calls" in rec else "-")), flush=True)
os.makedirs(os.path.dirname(a.out), exist_ok=True)
json.dump({"model": a.model, "args": vars(a), "results": res}, open(a.out, "w"), ensure_ascii=False, indent=1)
ok = [x for x in res if x.get("pass")]; act = [x for x in res if not x["no_tool"]]; lat = [x["latency"] for x in res if "latency" in x]
print("\n== %s (requete HA exacte) ==" % a.model); print("reussite : %d/%d (%.0f%%) | ordres : %d/%d" % (len(ok), len(res), 100 * len(ok) / max(1, len(res)), sum(1 for x in act if x.get("pass")), len(act)))
for c in sorted(set(x["cat"] for x in res)):
    g = [x for x in res if x["cat"] == c]; print("  %-8s %d/%d" % (c, sum(1 for x in g if x.get("pass")), len(g)))
txt = [x for x in act if not x.get("got") and x.get("reply")]
print("ORDRES SANS APPEL D OUTIL (texte seul) : %d/%d" % (len(txt), len(act)))
for x in txt[:8]: print("   ", x["id"], x["text"], "->", x["reply"][:60])
lp = [x for x in res if "loop_calls" in x]
if lp:
    bad = [x for x in lp if x["loop_calls"] > 2 or not x["loop_ended"]]
    print("BOUCLES : %d requetes avec appel d outil ; %d avec plus de 2 appels ou sans fin ; profondeur max %d" % (len(lp), len(bad), max(x["loop_calls"] for x in lp)))
    traps = [x for x in res if x["no_tool"]]; print("pieges : %d/%d ont appele un outil (devrait etre 0) ; apres erreur, arret propre : %d" % (sum(1 for x in traps if x.get("got")), len(traps), sum(1 for x in traps if x.get("got") and x.get("loop_ended") and x["loop_calls"] == 1)))
if lat: print("latence : moyenne %.1fs | mediane %.1fs | tokens prompt ~%s" % (statistics.mean(lat), statistics.median(lat), res[0].get("prompt_tokens")))
