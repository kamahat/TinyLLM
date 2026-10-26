#!/usr/bin/env python3
"""Banc de recette : envoie chaque phrase a un modele Ollama avec le prompt + les outils Assist de HA,
et compare le PREMIER appel d outil a l attendu. N execute AUCUNE action sur HA."""
import argparse, json, re, time, unicodedata, urllib.request, statistics, sys, os
D = "/opt/tinyllm/data/"
ap = argparse.ArgumentParser()
ap.add_argument("--host", default="http://localhost:11434")
ap.add_argument("--model", default="qwen3:1.7b")
ap.add_argument("--out", required=True)
ap.add_argument("--cats", default="")
ap.add_argument("--limit", type=int, default=0)
ap.add_argument("--every", type=int, default=1)
ap.add_argument("--num-ctx", type=int, default=6144)
ap.add_argument("--extra-context", default="", help="fichier texte ajoute au prompt (RAG / connaissance)")
ap.add_argument("--timeout", type=int, default=600)
ap.add_argument("--no-tools", action="store_true")
ap.add_argument("--rag", default="", help="rag_topk.json : contexte reduit aux k entites les plus proches")
ap.add_argument("--k", type=int, default=5)
ap.add_argument("--rag-user", action="store_true", help="contexte (entites proches) dans le message utilisateur : systeme+outils constants = cache")
a = ap.parse_args()

def norm(s):
    s = unicodedata.normalize("NFD", str(s).lower()); s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]+", " ", s).split().__str__().replace("[", "").replace("]", "").replace("'", "").replace(",", "")

tools_raw = json.load(open(D + "ha_tools.json"))
tools = [{"type": "function", "function": {"name": t["name"].split("__")[-1], "description": t.get("description", ""), "parameters": t["inputSchema"]}} for t in tools_raw]
ents = json.load(open(D + "ha_exposed.json"))
ctx = "Static Context: An overview of the areas and the devices in this smart home:\n"
for e in ents:
    ctx += "- names: %s\n  domain: %s\n  state: %s\n" % (e["name"], e["domain"], json.dumps(str(e["state"])).replace("\"", "\x27"))
    if e["area"]: ctx += "  areas: %s\n" % e["area"]
SYSTEM = ("You are a voice assistant for Home Assistant.\nAnswer questions about the world truthfully.\nAnswer in plain text. Keep it simple and to the point.\n"
          "Réponds toujours en français, en une phrase courte.\n"
          "When controlling Home Assistant always call the intent tools. Use HassTurnOn to lock and HassTurnOff to unlock a lock. "
          "When controlling a device, prefer passing just name and domain. When controlling an area, prefer passing just area name and domain.\n"
          "When a user asks to turn on all devices of a specific type, ask user to specify an area, unless there is only one device of that type.\n"
          "This device is not able to start timers.\n" + ctx)
if a.extra_context: SYSTEM += "\n" + open(a.extra_context).read()


DOM_TOOLS = {"light": ["HassTurnOn", "HassTurnOff", "HassLightSet"], "cover": ["HassTurnOn", "HassTurnOff", "HassSetPosition", "HassStopMoving"],
             "todo": ["get_items", "HassListAddItem", "HassListCompleteItem", "HassListRemoveItem"], "climate": ["HassClimateSetTemperature", "HassTurnOn", "HassTurnOff"],
             "input_boolean": ["HassTurnOn", "HassTurnOff"], "automation": ["HassTurnOn", "HassTurnOff"], "button": ["HassTurnOn", "HassTurnOff"]}
RAG = json.load(open(a.rag)) if a.rag else None
BYID = {e["entity_id"]: e for e in ents}
def rag_prompt(text):
    ids = RAG.get(text, [])[: a.k]; es = [BYID[i] for i in ids if i in BYID]
    names = {"GetLiveContext", "GetDateTime"}
    for e in es:
        names |= set(DOM_TOOLS.get(e["domain"], []))
        if e["domain"] == "script": names.add(e["entity_id"].split(".", 1)[1])
    c = "Static Context: An overview of the areas and the devices in this smart home:\n"
    for e in es:
        c += "- names: %s\n  domain: %s\n  state: %s\n" % (e["name"], e["domain"], "'" + str(e["state"]) + "'")
        if e["area"]: c += "  areas: %s\n" % e["area"]
    head = SYSTEM.split("Static Context:")[0]
    return head + c, [t for t in tools if t["function"]["name"] in names]

R = json.load(open(D + "recette.json"))
if a.cats: R = [r for r in R if r["cat"] in a.cats.split(",")]
if a.every > 1: R = R[:: a.every]
if a.limit: R = R[: a.limit]

def chat(text):
    sysmsg, tl = (rag_prompt(text) if RAG else (SYSTEM, tools))
    if RAG and a.rag_user:
        ids = RAG.get(text, [])[: a.k]; es = [BYID[i] for i in ids if i in BYID]
        ctxu = '\n'.join('- %s (%s%s, etat %s)' % (e['name'], e['domain'], (', ' + e['area']) if e['area'] else '', e['state']) for e in es)
        sysmsg = SYSTEM.split('Static Context:')[0]; tl = tools
        text = 'Appareils pertinents :' + '\n' + ctxu + '\n\n' + 'Demande : ' + text
    body = {"model": a.model, "stream": False, "think": False,
            "messages": [{"role": "system", "content": sysmsg}, {"role": "user", "content": text}],
            "options": {"temperature": 0, "num_ctx": a.num_ctx, "num_predict": 200}}
    if not a.no_tools: body["tools"] = tl
    t = time.time()
    r = json.loads(urllib.request.urlopen(urllib.request.Request(a.host + "/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}), timeout=a.timeout).read())
    return r, time.time() - t

def val_ok(exp, act):
    if isinstance(act, list): act = act[0] if act else ""
    if isinstance(exp, (int, float)):
        try: return float(act) == float(exp)
        except Exception: return False
    e, c = norm(exp), norm(act)
    return bool(e) and (e in c or c in e) and bool(c)

res = []
for i, r in enumerate(R):
    try: resp, dt = chat(r["text"])
    except Exception as ex:
        res.append({**r, "error": repr(ex)[:200], "pass": False}); print(i + 1, len(R), r["id"], "ERREUR", repr(ex)[:80], flush=True); continue
    m = resp.get("message", {}); calls = [c["function"] for c in m.get("tool_calls", [])]
    first = calls[0] if calls else None
    if r["no_tool"]: tool_ok = args_ok = (first is None)
    else:
        tool_ok = bool(first) and first["name"] == r["tool"]
        args_ok = tool_ok and all(val_ok(v, (first.get("arguments") or {}).get(k)) for k, v in r["args"].items())
    ok = tool_ok and args_ok
    res.append({**r, "pass": ok, "tool_ok": tool_ok, "args_ok": args_ok, "got": first, "n_calls": len(calls), "reply": (m.get("content") or "")[:160],
                "latency": round(dt, 2), "prompt_tokens": resp.get("prompt_eval_count"), "gen_tokens": resp.get("eval_count"),
                "eval_s": round(resp.get("eval_duration", 0) / 1e9, 2), "prompt_s": round(resp.get("prompt_eval_duration", 0) / 1e9, 2)})
    print("%d/%d %s %-8s %s %5.1fs | %s | attendu=%s%s" % (i + 1, len(R), r["id"], r["cat"], "OK " if ok else "KO ", dt, json.dumps(first, ensure_ascii=False)[:90] if first else "(aucun outil) " + (m.get("content") or "")[:50].replace("\n", " "), "-" if r["no_tool"] else r["tool"], ""), flush=True)
os.makedirs(os.path.dirname(a.out), exist_ok=True)
json.dump({"model": a.model, "host": a.host, "args": vars(a), "results": res}, open(a.out, "w"), ensure_ascii=False, indent=1)
ok = [x for x in res if x.get("pass")]; lat = [x["latency"] for x in res if "latency" in x]
print("\n== %s | %s ==" % (a.model, a.out)); print("reussite globale: %d/%d (%.0f%%)" % (len(ok), len(res), 100 * len(ok) / max(1, len(res))))
for c in sorted(set(x["cat"] for x in res)):
    g = [x for x in res if x["cat"] == c]; print("  %-8s %d/%d" % (c, sum(1 for x in g if x.get("pass")), len(g)))
if lat: print("latence : moyenne %.1fs | mediane %.1fs | max %.1fs | tokens prompt ~%s" % (statistics.mean(lat), statistics.median(lat), max(lat), res[0].get("prompt_tokens")))
