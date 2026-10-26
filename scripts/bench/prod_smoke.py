#!/usr/bin/env python3
"""Test de fumee du proxy de PRODUCTION (11436) en HTTP direct, sans Home Assistant : le proxy ne fait que RENVOYER des tool_calls, rien n est execute."""
import json, time, urllib.request, sys
R = json.load(open("/opt/tinyllm/data/ha_tablet_prompt.json"))
for q in sys.argv[1:]:
    body = {"model": "x", "stream": False, "tools": R["tools"], "messages": [{"role": "system", "content": R["system"]}, {"role": "user", "content": q}]}
    t = time.time(); r = json.loads(urllib.request.urlopen(urllib.request.Request("http://localhost:11436/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}), timeout=300).read())
    m = r["message"]; print("%-46s %5.1fs | appels=%s | %s" % (q, time.time() - t, json.dumps(m.get("tool_calls") or [], ensure_ascii=False)[:100], (m.get("content") or "")[:90]))
