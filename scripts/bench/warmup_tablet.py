#!/usr/bin/env python3
"""Prechauffe le cache d Ollama avec le prompt EXACT envoye par la tablette (25 outils). Appelle Ollama directement : n atteint pas HA, aucun ordre."""
import json, time, sys, urllib.request
R = json.load(open("/opt/tinyllm/data/ha_tablet_prompt.json"))
model = sys.argv[1] if len(sys.argv) > 1 else "qwen3-ha-v2:latest"
body = {"model": model, "stream": False, "think": False, "keep_alive": -1, "options": R["options"],
        "messages": [{"role": "system", "content": R["system"]}, {"role": "user", "content": "Combien font un plus un ?"}], "tools": R["tools"]}
t = time.time(); r = json.loads(urllib.request.urlopen(urllib.request.Request("http://localhost:11434/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}), timeout=400).read())
print("prechauffage %s : %.1fs | prompt %s tokens | reponse : %s" % (model, time.time() - t, r.get("prompt_eval_count"), (r["message"].get("content") or str(r["message"].get("tool_calls")))[:60]))
