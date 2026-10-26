#!/usr/bin/env python3
"""Prechauffe le proxy compact + Ollama avec le prompt EXACT de la tablette. Appelle le PROXY directement (pas HA) : aucun ordre ne peut etre execute. Usage : warmup_proxy.py [URL]"""
import json, time, sys, urllib.request
R = json.load(open("/opt/tinyllm/data/ha_tablet_prompt.json")); url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:11436"
body = {"model": "qwen3-ha-v4c:latest", "stream": False, "messages": [{"role": "system", "content": R["system"]}, {"role": "user", "content": "Combien font un plus un ?"}], "tools": R["tools"]}
for i in range(2):
    t = time.time(); r = json.loads(urllib.request.urlopen(urllib.request.Request(url + "/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}), timeout=600).read())
    m = r["message"]; print("prechauffage proxy essai %d : %.1fs | prompt %s tokens | reponse : %s %s" % (i + 1, time.time() - t, r.get("prompt_eval_count"), (m.get("content") or "")[:50], ("[appel ignore : %s]" % m["tool_calls"][0]["function"]["name"]) if m.get("tool_calls") else ""))
