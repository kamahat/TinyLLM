import csv, json, os, statistics, shutil
R = "/opt/tinyllm/results"; OUT = "/opt/tinyllm/repo/results"; os.makedirs(OUT, exist_ok=True)
stt = json.load(open(R + "/stt_all.json"))
with open(OUT + "/stt_whisper.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["config", "model", "vocab_prompt", "condition", "n", "wer_pct", "exact_sentences", "latency_mean_s", "latency_p90_s", "rtf"])
    for nom, d in stt.items():
        for cond in ("propre", "bruite"):
            s = d[cond]; w.writerow([nom, d["modele"], d["avec_prompt"], "clean" if cond == "propre" else "noisy_15dB", s["n"], s["wer_pct"], s["exactes"], s["lat_moy"], s["lat_p90"], s["rtf"]])
p = json.load(open(R + "/piper_medium.json"))
with open(OUT + "/tts_piper.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["voice", "kind", "n", "audio_mean_s", "first_audio_mean_s", "first_audio_max_s", "total_mean_s", "rtf_mean"])
    for kind, nom in (("ordre", "command_sentences"), ("reponse", "assistant_replies")):
        s = [x for x in p if x["kind"] == kind]
        w.writerow(["fr_FR-siwis-medium", nom, len(s), round(statistics.mean(x["audio_s"] for x in s), 2), round(statistics.mean(x["ttfa_s"] for x in s), 2), max(x["ttfa_s"] for x in s), round(statistics.mean(x["total_s"] for x in s), 2), round(statistics.mean(x["rtf"] for x in s), 2)])
for src, dst in (("tableau-etapes.csv", "llm_stages.csv"), ("tableau-compact.csv", "llm_models.csv")):
    shutil.copy("/opt/vllm-yoyo/repo/Jarvis/resultats/" + src, OUT + "/" + dst)
print(open(OUT + "/stt_whisper.csv").read()); print(open(OUT + "/tts_piper.csv").read())
