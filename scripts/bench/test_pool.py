"""Test hors ligne : capteur de piscine present mais sans valeur recente. Prompt tablette + bloc du capteur ajoute ; resultat d outil simule ; AUCUNE execution."""
import json, sys, re, urllib.request
sys.path.insert(0, "/opt/tinyllm/compact")
from compactlib import *
R = json.load(open("/opt/tinyllm/data/ha_tablet_prompt.json")); EN = {e["name"]: e["state"] for e in json.load(open("/opt/tinyllm/data/ha_exposed.json"))}
NLS = chr(10); blk = "- names: piscine-233 Temperature, Température de la piscine, Température de l" + chr(39) + "eau de la piscine" + NLS + "  domain: sensor" + NLS + "  areas: Piscine" + NLS
SYSTEM = R["system"].replace(NLS + "- names: Prévision Météo", NLS + blk.rstrip(NLS) + NLS + "- names: Prévision Météo", 1) if "- names: Prévision Météo" in R["system"] else R["system"]
assert "piscine-233" in SYSTEM, "bloc non insere"
def live(state):
    t = "Live Context: An overview of the areas and the devices in this smart home:" + NLS
    for e in parse_ha_system(SYSTEM):
        v = state if e["name"].startswith("piscine-233") else ("51.0" if e["name"] == "Température Douche" else EN.get(e["name"], "unknown"))
        t += "- names: %s%s  domain: %s%s  state: %s%s" % (e["name"], NLS, e["domain"], NLS, chr(39) + str(v) + chr(39), NLS) + (("  areas: " + e["areas"] + NLS) if e["areas"] else "")
    return t
def gen(msgs, tools):
    body = {"model": "qwen3-ha-v4c", "prompt": render(msgs, tools, True, "qwen"), "raw": True, "stream": False, "keep_alive": -1, "options": {"temperature": 0, "num_predict": 160, "num_ctx": 4096, "stop": ["<|im_end|>"]}}
    return json.loads(urllib.request.urlopen(urllib.request.Request("http://localhost:11434/api/generate", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}), timeout=600).read())["response"]
for q in ["Quelle est la température de la piscine ?", "Quelle température fait l eau de la piscine ?", "Il fait combien dans la piscine ?", "Quelle est la température de la douche ?"]:
    for state in (["unknown", "unavailable"] if "piscine" in q else ["unknown"]):
        ha = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": q}]
        m1, t1, _ = transform(ha, R["tools"]); txt, calls, _ = parse_output(gen(m1, t1)); first = calls[0]["function"] if calls else None
        if not first: print("%-46s -> (aucun appel) %s" % (q, txt)); continue
        m2, t2, _ = transform(ha + [{"role": "assistant", "content": "", "tool_calls": [{"function": first}]}, {"role": "tool", "content": json.dumps({"result": live(state)}, ensure_ascii=False)}], R["tools"])
        f2, c2, _ = parse_output(gen(m2, t2)); f2 = guard_unavailable(m2, f2); print("%-46s [%-11s] appel=%s -> %s" % (q, state, first["name"].split("__")[-1] + json.dumps(first["arguments"], ensure_ascii=False), f2 if not c2 else "(nouvel appel rejete)"))
