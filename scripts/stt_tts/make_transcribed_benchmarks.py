#!/usr/bin/env python3
"""Cree, pour chaque moteur STT et chaque condition (propre / bruite), une copie du banc de phrases dont le texte est la TRANSCRIPTION du moteur
(au lieu du texte exact). Ces fichiers sont ensuite rejoues dans le LLM avec harness4.py --recette (voir e2e_stt_tests.sh). Entrees : les JSON de bench_stt*.py."""
import json
R = "/opt/tinyllm/results/"; D = "/opt/tinyllm/data/"
base = json.load(open(D + "benchmark_fr_92.json")); src = {}
for f in ("stt_all.json", "stt_alt_all.json"): src.update(json.load(open(R + f)))
cfg = {"small": "small-int8 + prompt (production)", "base": "base-int8 + prompt", "tiny": "tiny-int8 + prompt", "parakeet": "parakeet-tdt-0.6b-v3 int8 (sherpa)", "kroko": "zipformer fr kroko streaming (sherpa)"}
for cid, nom in cfg.items():
    for cond, nomcond in (("propre", "clean"), ("bruite", "noisy")):
        det = src[nom]["details_" + cond]; nouveau = []
        for i, x in enumerate(base[:92]):
            assert det[i]["ref"] == x["text"]; y = dict(x); y["text"] = det[i]["hyp"] or x["text"]; nouveau.append(y)
        json.dump(nouveau, open(D + "benchmark_stt_%s_%s.json" % (cid, nomcond), "w"), ensure_ascii=False)
