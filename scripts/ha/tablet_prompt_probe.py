import sys, json, ssl, asyncio, websockets
sys.path.insert(0, "/opt/tinyllm/ha")
from ws import ws
tok = open("/root/.ha-token").read().strip(); ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
DEV = "YOUR_TABLET_DEVICE_ID"
base = next(p for p in ws({"type": "assist_pipeline/pipeline/list"})["result"]["pipelines"] if p["name"] == "Jarvis local")
new = {k: v for k, v in base.items() if k != "id"}; new["name"] = "SIM tablette (temporaire)"; new["conversation_engine"] = "conversation.simulation_jarvis"
r = ws({"type": "assist_pipeline/pipeline/create", **new}); pid = r["result"]["id"]; print("pipeline temporaire cree :", pid)
async def run():
    async with websockets.connect("wss://homeassistant.example.lan/api/websocket", ssl=ctx, max_size=None) as w:
        await w.recv(); await w.send(json.dumps({"type": "auth", "access_token": tok})); await w.recv()
        await w.send(json.dumps({"id": 1, "type": "assist_pipeline/run", "start_stage": "intent", "end_stage": "intent", "input": {"text": "Combien font sept fois huit ?"}, "pipeline": pid, "device_id": DEV}))
        while True:
            m = json.loads(await asyncio.wait_for(w.recv(), 300)); ev = m.get("event", {})
            if ev.get("type") == "intent-end": return ev["data"]["intent_output"]["response"]["speech"]["plain"]["speech"]
            if ev.get("type") in ("error", "run-end"): return ev
try:
    res = asyncio.run(run()); print("reponse :", str(res)[:140])
finally:
    print("suppression du pipeline temporaire :", ws({"type": "assist_pipeline/pipeline/delete", "pipeline_id": pid}).get("success"))
