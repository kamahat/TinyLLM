#!/usr/bin/env python3
"""Banc STT : Whisper (faster-whisper, int8, CPU) via Wyoming sur le corpus audio synthetique (ordres parles produits par Piper), propre puis bruite (SNR 15 dB).
Mesure : WER, phrases exactes, latence apres la fin de la parole. Les configurations tiny/base/small sans prompt sont lancees dans des conteneurs TEMPORAIRES
(noms tinyllm-bench-*, supprimes a la fin). La config de production (small-int8 + prompt de vocabulaire, port 10300) est mesuree telle quelle."""
import asyncio, json, os, re, shlex, socket, statistics, subprocess, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wy
R = "/opt/tinyllm"; DK = "root@localhost"; HOST = "localhost"
PROMPT = "Maison connectée. Allume, éteins, ferme, ouvre. Volets, lumière, salon, cuisine, chambre, bureau, tapisserie, cinéma, Jarvis."
CONFIGS = [  # (nom, id court, port, arguments du serveur, temps reel ?)
    ("parakeet-tdt-0.6b-v3 int8 (sherpa)", "parakeet", 10314, "--stt-library sherpa --language fr --model sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8", False),
    ("zipformer fr kroko streaming (sherpa)", "kroko", 10315, "--stt-library sherpa --sherpa-streaming --language fr --model sherpa-onnx-streaming-zipformer-fr-kroko-2025-08-06", True)]
only = set(sys.argv[1:])

def ssh(cmd, check=True): return subprocess.run(["ssh", "-o", "BatchMode=yes", DK, cmd], capture_output=True, text=True, check=check)

def norm(t): return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t.lower().replace("’", " ").replace("'", " "))).strip().split(" ")

def wer(ref, hyp):
    r, h = norm(ref), norm(hyp); d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            cur = d[j]; d[j] = min(d[j] + 1, d[j - 1] + 1, prev + (r[i - 1] != h[j - 1])); prev = cur
    return d[len(h)], len(r)

def pcm16k(path):
    out = subprocess.run(["ffmpeg", "-v", "quiet", "-i", path, "-ar", "16000", "-ac", "1", "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.int16)

def bruit(x, snr_db, seed):
    rng = np.random.default_rng(seed); p = np.mean(x.astype(np.float64) ** 2) + 1e-9
    n = rng.normal(0, np.sqrt(p / (10 ** (snr_db / 10.0))), len(x)); return np.clip(x + n, -32768, 32767).astype(np.int16)

def attendre(port, t=240):
    d = time.time() + t
    while time.time() < d:
        try: socket.create_connection((HOST, port), 2).close(); time.sleep(1.0); return True
        except OSError: time.sleep(2)
    return False

async def mesure(port, items, pace=0.0):
    await wy.transcribe(HOST, port, items[0][1].tobytes(), pace=pace)  # echauffement
    out = []
    for ref, pcm in items:
        txt, lat, tot = await wy.transcribe(HOST, port, pcm.tobytes(), pace=pace); e, n = wer(ref, txt)
        out.append({"ref": ref, "hyp": txt, "err": e, "n": n, "latence_s": round(lat, 3), "total_s": round(tot, 3), "audio_s": round(len(pcm) / 16000.0, 2)})
    return out

def resume(res):
    e = sum(x["err"] for x in res); n = sum(x["n"] for x in res); lat = sorted(x["latence_s"] for x in res)
    return {"n": len(res), "wer_pct": round(100.0 * e / n, 1), "exactes": sum(1 for x in res if x["err"] == 0), "lat_moy": round(statistics.mean(lat), 2), "lat_med": round(statistics.median(lat), 2),
            "lat_p90": round(lat[int(0.9 * len(lat)) - 1], 2), "rtf": round(sum(x["latence_s"] for x in res) / sum(x["audio_s"] for x in res), 2)}

def main():
    corpus = [(x["text"], x["file"]) for x in json.load(open(R + "/results/piper_medium.json")) if x["kind"] == "ordre"]
    propre = [(t, pcm16k(R + "/audio/" + f)) for t, f in corpus]; bruite = [(t, bruit(p, 15, i)) for i, (t, p) in enumerate(propre)]
    tout = {}
    for nom, cid, port, args, realtime in CONFIGS:
        if only and cid not in only: continue
        cname = "tinyllm-bench-stt-" + cid; pace = 2048 / 16000.0 if realtime else 0.0
        try:
            ssh("mkdir -p /opt/tinyllm-bench/stt && docker run -d --name %s --memory 1800m -p %d:10300 -v /opt/tinyllm-bench/stt:/data rhasspy/wyoming-whisper:latest %s" % (cname, port, args))
            if not attendre(port, 600): print("echec demarrage", nom, flush=True); continue
            t0 = time.time(); r_propre = asyncio.run(mesure(port, propre, pace)); r_bruit = asyncio.run(mesure(port, bruite, pace))
            tout[nom] = {"modele": cid, "avec_prompt": False, "propre": resume(r_propre), "bruite": resume(r_bruit), "details_propre": r_propre, "details_bruite": r_bruit}
            print("== %s | propre %s | bruite %s | %.0fs" % (nom, tout[nom]["propre"], tout[nom]["bruite"], time.time() - t0), flush=True)
            json.dump(tout, open(R + "/results/stt_alt_" + ("_".join(sorted(only)) or "all") + ".json", "w"), ensure_ascii=False, indent=1)
        finally:
            lg = ssh("docker logs --tail 6 %s 2>&1" % cname, check=False).stdout; print("-- journal conteneur", cid, ":", lg[-500:].replace(chr(10), " | "), flush=True); ssh("docker rm -f %s >/dev/null 2>&1; true" % cname, check=False)
main()
