#!/usr/bin/env python3
"""Rejoue des phrases comme la tablette (device_id) via un pipeline TEMPORAIRE branche sur l agent de SIMULATION (proxy --sim : aucun appel d outil execute). Usage : sim_phrases.py "phrase 1" "phrase 2" ..."""
import sys, json, ssl, asyncio, time, websockets
sys.path.insert(0, "/opt/tinyllm/ha")
from ws import ws
tok = open("/root/.ha-token").read().strip(); ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
DEV = "YOUR_TABLET_DEVICE_ID"; LOG = "/opt/tinyllm/logs/proxy_sim.jsonl"
base = next(p for p in ws({"type": "assist_pipeline/pipeline/list"})["result"]["pipelines"] if p["name"] == "Jarvis local")
new = {k: v for k, v in base.items() if k != "id"}; new["name"] = "SIM tablette (temporaire)"; new["conversation_engine"] = "conversation.simulation_jarvis"; new["prefer_local_intents"] = False
pid = ws({"type": "assist_pipeline/pipeline/create", **new})["result"]["id"]
async def run(text):
    async with websockets.connect("wss://homeassistant.example.lan/api/websocket", ssl=ctx, max_size=None) as w:
        await w.recv(); await w.send(json.dumps({"type": "auth", "access_token": tok})); await w.recv()
        await w.send(json.dumps({"id": 1, "type": "assist_pipeline/run", "start_stage": "intent", "end_stage": "intent", "input": {"text": text}, "pipeline": pid, "device_id": DEV}))
        while True:
            m = json.loads(await asyncio.wait_for(w.recv(), 300)); ev = m.get("event", {})
            if ev.get("type") == "intent-end": return ev["data"]["intent_output"]["response"]["speech"]["plain"]["speech"]
            if ev.get("type") in ("error", "run-end"): return str(ev)[:120]
try:
    for text in sys.argv[1:]:
        n = sum(1 for _ in open(LOG)); t = time.time(); rep = asyncio.run(run(text))
        recs = [json.loads(l) for l in list(open(LOG))[n:]]
        calls = [c for r in recs for c in (r.get("stripped_calls") or [])]
        print("%-44s %4.1fs | %s | reponse : %s" % (text, time.time() - t, json.dumps(calls[0], ensure_ascii=False)[:110] if calls else "(aucun appel)", rep[:60]))
finally:
    print("pipeline temporaire supprime :", ws({"type": "assist_pipeline/pipeline/delete", "pipeline_id": pid}).get("success"))
