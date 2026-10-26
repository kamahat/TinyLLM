#!/usr/bin/env python3
"""Agent Ollama de prod (sous-entree CONFIG_ENTRY_ID) : backup | v2 | rollback. Ne lance AUCUN ordre."""
import sys, json, urllib.request
tok = open("/root/.ha-token").read().strip(); H = "http://homeassistant.example.lan:8123/api/"
EID, SID = "CONFIG_ENTRY_ID", "CONFIG_ENTRY_ID"; BK = "/opt/tinyllm/ha/backup_ollama_avant_v2.json"
def api(method, path, body=None):
    r = urllib.request.Request(H + path, method=method, data=json.dumps(body).encode() if body is not None else None, headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=120).read() or b"null")
def current():
    f = api("POST", "config/config_entries/subentries/flow", {"handler": [EID, "conversation"], "subentry_id": SID})
    cur = {x["name"]: x.get("description", {}).get("suggested_value") for x in f.get("data_schema", [])}
    try: api("DELETE", "config/config_entries/subentries/flow/" + f["flow_id"])
    except Exception: pass
    return cur
def apply(cfg):
    f = api("POST", "config/config_entries/subentries/flow", {"handler": [EID, "conversation"], "subentry_id": SID})
    body = {"model": cfg["model"], "prompt": cfg["prompt"], "llm_hass_api": cfg["llm_hass_api"], "num_ctx": int(cfg["num_ctx"]), "max_history": int(cfg["max_history"]), "keep_alive": int(cfg["keep_alive"]), "think": bool(cfg["think"])}
    r = api("POST", "config/config_entries/subentries/flow/" + f["flow_id"], body); return r.get("type"), r.get("reason"), r.get("errors")
def show(c): return {k: (v if k != "prompt" else v[:50].replace(chr(10), " ") + "...") for k, v in c.items()}
step = sys.argv[1]
if step == "backup": c = current(); json.dump(c, open(BK, "w"), ensure_ascii=False, indent=1); print("sauvegarde :", show(c))
if step == "rollback": print("retour arriere :", apply(json.load(open(BK)))); print("etat :", show(current()))
if step == "v2":
    NL = chr(10); c = json.load(open(BK)); c["model"] = "qwen3-ha-v2:latest"; c["llm_hass_api"] = ["assist"]; c["num_ctx"] = 6144
    c["prompt"] = "You are a voice assistant for Home Assistant." + NL + "Answer questions about the world truthfully." + NL + "Answer in plain text. Keep it simple and to the point." + NL + "Réponds toujours en français, en une phrase courte."
    print("application v2 :", apply(c)); print("etat :", show(current()))
