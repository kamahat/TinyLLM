#!/usr/bin/env python3
"""Validation par le vrai chemin de HA : agent de simulation -> proxy (retire les tool_calls). Garde : etat des appareils avant/apres, arret au moindre changement."""
import json, sys, time, urllib.request, urllib.error
sys.path.insert(0, "/opt/tinyllm/ha")
from ws import ws
EID = "CONFIG_ENTRY_ID"; AG = "conversation.simulation_jarvis"; LOG = "/opt/tinyllm/logs/proxy_sim.jsonl"
tok = open("/root/.ha-token").read().strip(); H = "http://homeassistant.example.lan:8123/api/"
def api(method, path, body=None):
    r = urllib.request.Request(H + path, method=method, data=json.dumps(body).encode() if body is not None else None, headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=300).read() or b"null")
ME = ws({"type": "auth/current_user"})["result"]["id"]
DOM = ("light", "cover", "switch", "climate", "input_boolean", "script", "todo", "fan", "lock")
def snap(): return {s["entity_id"]: (s["state"], s["context"].get("user_id")) for s in api("GET", "states") if s["entity_id"].split(".")[0] in DOM}
step = sys.argv[1]
if step == "model":
    subs = ws({"type": "config_entries/subentries/list", "entry_id": EID})["result"]; sid = next(s["subentry_id"] for s in subs if s["subentry_type"] == "conversation")
    f = api("POST", "config/config_entries/subentries/flow", {"handler": [EID, "conversation"], "subentry_id": sid})
    cur = {x["name"]: x.get("description", {}).get("suggested_value") for x in f["data_schema"]}
    cur["model"] = sys.argv[2]; r = api("POST", "config/config_entries/subentries/flow/" + f["flow_id"], {k: (int(v) if isinstance(v, float) else v) for k, v in cur.items()})
    print("modele de l agent de simulation ->", sys.argv[2], "|", r.get("type"), r.get("reason"))
if step == "run":
    R = json.load(open("/opt/tinyllm/data/recette.json"))[:: int(sys.argv[2])]
    R = [r for r in R if r["id"] >= (sys.argv[3] if len(sys.argv) > 3 else "000")]
    PRE = {"HassTurnOn": "intent__", "HassTurnOff": "intent__", "HassSetPosition": "intent__", "HassStopMoving": "intent__", "HassLightSet": "light__", "GetLiveContext": "homeassistant__", "GetDateTime": "llm__", "HassClimateSetTemperature": "climate__", "get_items": "todo__", "HassListAddItem": "todo__", "HassListCompleteItem": "todo__", "HassListRemoveItem": "todo__"}
    import unicodedata, re
    def norm(s):
        s = unicodedata.normalize("NFD", str(s).lower()); s = "".join(c for c in s if unicodedata.category(c) != "Mn"); return " ".join(re.sub(r"[^a-z0-9 ]+", " ", s).split())
    before = snap(); ok = tot = nocall = 0; bad = []
    for r in R:
        n0 = sum(1 for _ in open(LOG)); t = time.time()
        d = api("POST", "conversation/process", {"text": r["text"], "language": "fr", "agent_id": AG}); sp = d["response"]["speech"]["plain"]["speech"]
        recs = [json.loads(l) for l in list(open(LOG))[n0:]]; calls = [c for x in recs for c in x.get("stripped_calls", [])]
        exp = None if r["no_tool"] else PRE.get(r["tool"], "script__") + r["tool"]
        good = (not calls) if r["no_tool"] else bool(calls) and calls[0]["name"] == exp and all(norm(v) in norm(str((calls[0].get("arguments") or {}).get(k, ""))) or norm(str((calls[0].get("arguments") or {}).get(k, ""))) in norm(v) for k, v in r["args"].items() if not isinstance(v, int))
        tot += 1; ok += good
        if calls and "[SIMULATION]" not in sp: print("ALERTE : appel sans marqueur de simulation ->", r["text"], sp[:80]); sys.exit(2)
        if not good: bad.append((r["id"], r["text"], calls[:1], sp[:60]))
        after = snap(); diff = {k: (before[k][0], after.get(k, (None, None))[0], after.get(k, (None, None))[1]) for k in before if before[k][0] != after.get(k, (None, None))[0]}
        mine = {k: v for k, v in diff.items() if v[2] == ME}
        if mine: print("ARRET : changement attribuable a ma session !", mine); sys.exit(3)
        if diff: print("   (note : changement externe, contexte sans utilisateur :", {k: v[:2] for k, v in diff.items()}, ")"); before = after
        print("%s %-8s %s %.1fs | %s" % (r["id"], r["cat"], "OK " if good else "KO ", time.time() - t, (json.dumps(calls[0], ensure_ascii=False)[:90] if calls else "(texte) " + sp[:50])), flush=True)
    print("\nVALIDATION (chemin reel de HA, simulation) : %d/%d | changements attribuables a ma session : 0 (garde active)" % (ok, tot))
    for b in bad: print("  KO", b)
