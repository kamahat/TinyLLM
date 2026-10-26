#!/usr/bin/env python3
"""Micro-banc de VITESSE entre variantes quantifiees d un meme modele, sur l instance Ollama de TEST (port 11435).
Prompt reel du proxy (capture de HA) + un nonce au debut pour neutraliser le cache de prompt : chaque essai mesure le VRAI traitement du prompt (prefill) puis la generation (decodage).
Le modele est decharge apres chaque essai (keep_alive 0) : memoire propre, pas d accumulation de copies de prompt dans le serveur.
Ordre : une passe A B C puis la passe inverse C B A (compense chauffe et derive). Usage : speed_bench.py MODELE_A[@FORMAT] MODELE_B[@FORMAT] [...]   (RUNS = essais par bloc, defaut 3)"""
import json, os, random, statistics, sys, time, urllib.request
os.environ["COMPACT_WEB"] = "1"; sys.path.insert(0, "/opt/tinyllm/compact")
from compactlib import transform, render, stop_token
cap = json.load(open("/opt/tinyllm/data/capture_ha_request.json")); SYS = cap["messages"][0]["content"]; TOOLS = cap["tools"]
URL = "http://localhost:11435/api/generate"; SPEC = [(a.partition("@")[0], a.partition("@")[2] or "qwen") for a in sys.argv[1:]]; MODELS = [m for m, _ in SPEC]; KIND = dict(SPEC); N = int(os.environ.get("RUNS", "3"))   # argument NOM ou NOM@FORMAT (qwen par defaut, gemma)
def run(model):
    msgs, tools, _ = transform([{"role": "system", "content": SYS}, {"role": "user", "content": "Allume la lumière du salon"}], TOOLS)
    msgs[0] = dict(msgs[0], content="[nonce %08x]\n" % random.getrandbits(32) + msgs[0]["content"])
    body = {"model": model, "prompt": render(msgs, tools, True, KIND[model]), "raw": True, "stream": False, "keep_alive": 0, "options": {"temperature": 0, "num_predict": 48, "num_ctx": 4096, "stop": [stop_token(KIND[model])]}}
    t = time.time(); r = json.loads(urllib.request.urlopen(urllib.request.Request(URL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}), timeout=600).read()); tot = time.time() - t
    return {"prefill_tok": r["prompt_eval_count"], "prefill_s": r["prompt_eval_duration"] / 1e9, "gen_tok": r["eval_count"], "gen_s": r["eval_duration"] / 1e9, "total_s": tot}
res = {m: [] for m in MODELS}
for blk, m in enumerate(MODELS + MODELS[::-1]):
    for i in range(N):
        x = run(m); res[m].append(x)
        print("%-26s bloc %d essai %d : prompt %d tok en %.1fs (%.1f tok/s) | generation %d tok en %.1fs (%.1f tok/s) | total %.1fs" % (m, blk + 1, i + 1, x["prefill_tok"], x["prefill_s"], x["prefill_tok"] / x["prefill_s"], x["gen_tok"], x["gen_s"], x["gen_tok"] / max(x["gen_s"], 1e-9), x["total_s"]), flush=True)
print("== medianes (min - max)")
for m in MODELS:
    L = res[m]; pf = [x["prefill_tok"] / x["prefill_s"] for x in L]; dc = [x["gen_tok"] / max(x["gen_s"], 1e-9) for x in L]
    print("%-26s prefill %.1f tok/s (%.1f - %.1f) | decodage %.1f tok/s (%.1f - %.1f) | total d une commande %.1fs | n=%d" % (m, statistics.median(pf), min(pf), max(pf), statistics.median(dc), min(dc), max(dc), statistics.median(x["total_s"] for x in L), len(L)))
json.dump(res, open("/opt/tinyllm/results/speed_" + "_vs_".join(MODELS) + ".json", "w"), indent=1)
