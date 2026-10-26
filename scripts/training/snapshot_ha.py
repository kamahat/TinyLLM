import sys, json, ssl, urllib.request
sys.path.insert(0, "/opt/tinyllm/ha")
from ws import ws
D = "/opt/tinyllm/data/"
exp = ws({"type": "homeassistant/expose_entity/list"})["result"]["exposed_entities"]
st = {s["entity_id"]: s for s in ws({"type": "get_states"})["result"]}
reg = {e["entity_id"]: e for e in ws({"type": "config/entity_registry/list"})["result"]}
dev = {d["id"]: d for d in ws({"type": "config/device_registry/list"})["result"]}
areas = {a["area_id"]: a["name"] for a in ws({"type": "config/area_registry/list"})["result"]}
out = []
for eid, v in sorted(exp.items()):
    if not v.get("conversation") or eid not in st: continue
    r = reg.get(eid, {}); s = st[eid]
    area = areas.get(r.get("area_id") or dev.get(r.get("device_id"), {}).get("area_id"))
    out.append({"entity_id": eid, "name": s["attributes"].get("friendly_name"), "area": area,
                "aliases": [a for a in (r.get("aliases") or []) if a], "domain": eid.split(".")[0], "state": s["state"]})
json.dump(out, open(D + "ha_exposed.json", "w"), ensure_ascii=False, indent=1)
print("entites exposees (existantes):", len(out))
from collections import Counter
print(dict(Counter(o["domain"] for o in out)))
# outils (API Assist) via le serveur MCP de HA
tok = open("/root/.ha-token").read().strip()
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
def rpc(body, sid=None):
    h = {"Authorization": "Bearer " + tok, "Content-Type": "application/json", "Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2025-06-18"}
    if sid: h["Mcp-Session-Id"] = sid
    r = urllib.request.urlopen(urllib.request.Request("https://homeassistant.example.lan/api/mcp", data=json.dumps(body).encode(), headers=h), context=ctx, timeout=30)
    raw = r.read().decode(); sid = r.headers.get("Mcp-Session-Id") or sid
    for line in raw.splitlines():
        if line.startswith("data:"): raw = line[5:].strip(); break
    return (json.loads(raw) if raw.strip() else None), sid
try:
    init, sid = rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "eval", "version": "1"}}})
    rpc({"jsonrpc": "2.0", "method": "notifications/initialized"}, sid)
    tools, _ = rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, sid)
    t = tools["result"]["tools"]
    json.dump(t, open(D + "ha_tools.json", "w"), ensure_ascii=False, indent=1)
    print("outils MCP/Assist:", len(t), [x["name"] for x in t])
except Exception as e:
    print("MCP KO:", repr(e)[:300])
