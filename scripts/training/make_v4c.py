"""Convertit les exemples v3 au format COMPACT (memes phrases, memes cibles) : systeme/outils/resultats compacts, tour 2 sans outils."""
import json, sys, random
sys.path.insert(0, "/opt/tinyllm/compact")
from compactlib import *
D = "/opt/tinyllm/data/"; random.seed(11)
rows = json.load(open(D + "train_v3.json")); out = []
def msgs_of(turns):
    m = []
    for h in turns:
        m.append({"role": "user", "content": h["user"]})
        for s in h["steps"]:
            m.append({"role": "assistant", "content": "", "tool_calls": [{"function": {"name": s["tool"], "arguments": s["args"]}}]}); m.append({"role": "tool", "content": compact_result(s["result"])})
        if h.get("final") is not None: m.append({"role": "assistant", "content": h["final"]})
    return m
for ex in rows:
    ents = parse_ha_system(ex["system"])
    cur = {"user": ex["user"], "steps": ex["steps"], "final": None}
    out.append({"cat": ex["cat"], "system": compact_system(ents), "hist": msgs_of(ex["hist"]),
                "user": ex["user"], "steps": [{"tool": s["tool"], "args": s["args"], "result": compact_result(s["result"])} for s in ex["steps"]], "final": ex["final"]})
json.dump(out, open(D + "train_v4c.json", "w"), ensure_ascii=False)
print(len(out), "exemples compacts ; moyenne systeme :", sum(len(x["system"]) for x in out) // len(out), "car.")
x = next(e for e in out if e["steps"] and e["cat"] == "info"); print("exemple info, resultat compact :", x["steps"][0]["result"][:300].replace(chr(10), " | "))
