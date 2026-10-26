#!/usr/bin/env python3
"""Assemble train_v5.json = exemples v3 reconvertis en format compact AVEC la consigne web (COMPACT_WEB=1) + exemples recherche web (x3, paraphrases d historique)."""
import json, os, random, sys
os.environ["COMPACT_WEB"] = "1"
sys.path.insert(0, "/opt/tinyllm/compact")
from compactlib import *
D = "/opt/tinyllm/data/"; random.seed(33)
rows = json.load(open(D + "train_v3.json")); gold = [g for g in json.load(open(D + "web_gold.json")) if g["split"] == "train"]
def msgs_of(turns):
    m = []
    for h in turns:
        m.append({"role": "user", "content": h["user"]})
        for s in h["steps"]:
            m.append({"role": "assistant", "content": "", "tool_calls": [{"function": {"name": s["tool"], "arguments": s["args"]}}]}); m.append({"role": "tool", "content": compact_result(s["result"])})
        if h.get("final") is not None: m.append({"role": "assistant", "content": h["final"]})
    return m
out = []
for ex in rows:
    out.append({"cat": ex["cat"], "system": compact_system(parse_ha_system(ex["system"])), "hist": msgs_of(ex["hist"]), "user": ex["user"], "steps": [{"tool": s["tool"], "args": s["args"], "result": compact_result(s["result"])} for s in ex["steps"]], "final": ex["final"]})
base = rows[:]; n_web = 0
real = [g for f in ("web_gold.json", "web_gold2.json") for g in json.load(open(D + f)) if g["split"] == "train"]
good = [g for g in real if "pas trouv" not in g["answer"].lower()]; nf = [g for g in real if "pas trouv" in g["answer"].lower()]
synth = [g for g in json.load(open(D + "web_synth.json")) if g["split"] == "train"]
web = good * 2 + synth + random.sample(nf, min(25, len(nf)))
for g in web:
    ex = random.choice(base); hist = msgs_of(random.choice(base)["hist"]) if random.random() < 0.4 else []
    out.append({"cat": "web", "system": compact_system(parse_ha_system(ex["system"])), "hist": hist, "user": g["phrase"], "steps": [{"tool": "recherche_web", "args": {"query": g["query"]}, "result": g["results_text"]}], "final": g["answer"]}); n_web += 1
random.shuffle(out); json.dump(out, open(D + "train_v5.json", "w"), ensure_ascii=False)
print(len(out), "exemples dont", n_web, "web (reels utiles x2 :", len(good) * 2, "; synthetiques :", len(synth), "; refus honnetes :", min(25, len(nf)), ")")
