"""Jeu de calibration pour llama-imatrix : 48 exemples du jeu d entrainement v5 rendus EXACTEMENT comme le proxy les presente au modele (systeme compact, outils, historique, appels et resultats d outils) + la reponse attendue."""
import json, os, random, sys
os.environ["COMPACT_WEB"] = "1"; sys.path.insert(0, "/var/lib/tinyllm/work")
from compactlib import *
random.seed(11)
D = "/var/lib/tinyllm/data/"; rows = json.load(open(D + "train_v5.json")); T = compact_tools(json.load(open(D + "ha_tablet_prompt.json"))["tools"])
def base(ex): return [{"role": "system", "content": ex["system"]}] + ex["hist"] + [{"role": "user", "content": ex["user"]}]
def p1(ex): return render(base(ex), T, True, "qwen") + ((call_text(ex["steps"][0]["tool"], ex["steps"][0]["args"]) if ex["steps"] else ex["final"]) + "<|im_end|>")
def p2(ex):
    m = base(ex)
    for s in ex["steps"]: m.append({"role": "assistant", "content": "", "tool_calls": [{"function": {"name": s["tool"], "arguments": s["args"]}}]}); m.append({"role": "tool", "content": s["result"]})
    return render(m, T, True, "qwen") + ex["final"] + "<|im_end|>"
multi = [e for e in rows if e["steps"]]; random.shuffle(rows); random.shuffle(multi)
txt = [p1(e) for e in rows[:24]] + [p2(e) for e in multi[:24]]
open("/var/lib/tinyllm/work/calib.txt", "w").write("\n\n".join(txt)); print(len(txt), "exemples,", sum(len(t) for t in txt), "caracteres")
