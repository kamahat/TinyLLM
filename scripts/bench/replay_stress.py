"""Rejoue des phrases mal transcrites avec/sans historique, en streaming, prompt tablette, directement sur Ollama (aucun ordre). Usage : replay_stress.py MODELE"""
import json, time, urllib.request, collections, sys
R = json.load(open("/opt/tinyllm/data/ha_tablet_prompt.json")); model = sys.argv[1]
H1 = [{"role": "user", "content": "Allume, lumière, salon."}, {"role": "assistant", "content": "Allumé"}]
PH = ["Éteins toutes les vumières du salon.", "Éteins toutes les lumières du salon.", "Éteins le salon.", "Allume la vumière du salon.", "Ferme les voler du salon."]
cnt = collections.Counter(); ex = []
for rep in range(2):
    for p in PH:
        for hist in ([], H1):
            body = {"model": model, "stream": True, "think": False, "keep_alive": -1, "options": R["options"], "tools": R["tools"], "messages": [{"role": "system", "content": R["system"]}] + hist + [{"role": "user", "content": p}]}
            resp = urllib.request.urlopen(urllib.request.Request("http://localhost:11434/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}), timeout=300)
            ch = [json.loads(l) for l in resp.read().decode().splitlines() if l.strip()]
            calls = [c["function"] for x in ch for c in (x.get("message", {}).get("tool_calls") or [])]; txt = "".join(x.get("message", {}).get("content") or "" for x in ch)
            kind = "appel" if calls else ("texte" if txt.strip() else "VIDE"); cnt[kind] += 1
            if kind != "appel": ex.append((p, bool(hist), kind, txt[:70]))
print(model, ": classement de 20 requetes :", dict(cnt))
for e in ex: print("  hors appel :", e)
