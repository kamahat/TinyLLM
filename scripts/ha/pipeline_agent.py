#!/usr/bin/env python3
"""Agent « Jarvis compact » (entree Ollama -> proxy compact) et bascule du pipeline « Jarvis local ».
  create    : cree l entree Ollama (URL du proxy) + l agent de conversation (n affecte aucun pipeline)
  switch    : pipeline Jarvis local -> conversation.jarvis_compact (sauvegarde l etat avant dans backup_pipeline_avant_proxy.json)
  rollback  : pipeline Jarvis local -> conversation.ollama_conversation (agent v2 direct, intact) + prechauffage de la v2
  status    : etat des pipelines et agents
Aucune commande n execute d ordre sur la maison."""
import sys, json, urllib.request, subprocess
sys.path.insert(0, "/opt/tinyllm/ha")
from ws import ws
tok = open("/root/.ha-token").read().strip(); H = "http://homeassistant.example.lan:8123/api/"
PROXY_URL = "http://localhost:11436"; BK = "/opt/tinyllm/ha/backup_pipeline_avant_proxy.json"; PROD_AGENT = "conversation.ollama_conversation"
def api(method, path, body=None):
    r = urllib.request.Request(H + path, method=method, data=json.dumps(body).encode() if body is not None else None, headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=120).read() or b"null")
def pipelines(): return ws({"type": "assist_pipeline/pipeline/list"})["result"]["pipelines"]
def set_engine(engine):
    p = next(x for x in pipelines() if x["name"] == "Jarvis local"); upd = {k: v for k, v in p.items() if k != "id"}; upd["conversation_engine"] = engine
    r = ws({"type": "assist_pipeline/pipeline/update", "pipeline_id": p["id"], **upd}); return r.get("success"), r.get("error")
def new_agent_id():
    ids = [s["entity_id"] for s in ws({"type": "get_states"})["result"] if s["entity_id"].startswith("conversation.") and "compact" in s["entity_id"]]
    return ids[0] if ids else None
step = sys.argv[1]
if step == "create":
    f = api("POST", "config/config_entries/flow", {"handler": "ollama", "show_advanced_options": False}); r = api("POST", "config/config_entries/flow/" + f["flow_id"], {"url": PROXY_URL})
    eid = r["result"]["entry_id"]; print("entree Ollama (proxy) :", eid, r["result"]["state"])
    NL = chr(10); prompt = "You are a voice assistant for Home Assistant." + NL + "Réponds toujours en français, en une phrase courte."
    f = api("POST", "config/config_entries/subentries/flow", {"handler": [eid, "conversation"]})
    r = api("POST", "config/config_entries/subentries/flow/" + f["flow_id"], {"name": "Jarvis compact", "model": "qwen3-ha-v4c:latest", "prompt": prompt, "llm_hass_api": ["assist"], "num_ctx": 4096, "max_history": 3, "keep_alive": -1, "think": False})
    print("agent :", r.get("type"), r.get("title"), "->", new_agent_id())
if step == "switch":
    aid = new_agent_id(); assert aid, "agent compact introuvable"
    json.dump([{k: v for k, v in p.items()} for p in pipelines()], open(BK, "w"), ensure_ascii=False, indent=1)
    print("bascule du pipeline Jarvis local ->", aid, set_engine(aid))
if step == "rollback":
    print("retour arriere : pipeline Jarvis local ->", PROD_AGENT, set_engine(PROD_AGENT))
    print(subprocess.run(["python3", "/opt/tinyllm/scripts/warmup_tablet.py", "qwen3-ha-v2:latest"], capture_output=True, text=True, timeout=600).stdout.strip())
if step in ("status", "create", "switch", "rollback"):
    print("pipelines :", [(p["name"], p["conversation_engine"], p["stt_engine"].split(".")[-1], p["tts_engine"].split(".")[-1]) for p in pipelines()])
    print("agents :", [s["entity_id"] for s in ws({"type": "get_states"})["result"] if s["entity_id"].startswith("conversation.")])
