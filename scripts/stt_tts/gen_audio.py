#!/usr/bin/env python3
"""Genere le corpus audio de test avec le Piper de production (10200) et mesure la synthese.
Corpus : les phrases de la recette (ordres parles) + des reponses typiques de l assistant. Sortie : audio/*.wav + results/piper_medium.json"""
import asyncio, json, os, sys, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wy
HOST, PORT = os.environ.get("PIPER_HOST", "localhost"), int(os.environ.get("PIPER_PORT", "10200"))
RACINE = "/opt/tinyllm"
ordres = [x["text"] for x in json.load(open("/opt/tinyllm/data/benchmark_fr_92.json"))]
reponses = ["La lumière du salon a été allumée.", "C est fait.", "Je n ai pas trouvé cet appareil.", "Demain à Nîmes, les températures varieront entre 9 et 19 degrés.",
            "Je n ai pas de valeur récente pour la température de la piscine : le capteur est indisponible.", "Il est dix-huit heures trente.",
            "Les volets du salon sont en cours de fermeture.", "Je n ai pas trouvé de réponse fiable.", "La capitale de l Italie est Rome.", "Voici la liste de courses : lait, pain et œufs."]
async def main():
    os.makedirs(RACINE + "/audio", exist_ok=True); lignes = []
    await wy.synth(HOST, PORT, "Bonjour.")   # echauffement
    for kind, textes in (("ordre", ordres), ("reponse", reponses)):
        for i, t in enumerate(textes):
            pcm, rate, ttfa, total = await wy.synth(HOST, PORT, t); dur = len(pcm) / 2.0 / rate
            nom = "%s_%03d.wav" % (kind, i); open(RACINE + "/audio/" + nom, "wb").write(wy.wav_bytes(pcm, rate))
            lignes.append({"file": nom, "kind": kind, "text": t, "rate": rate, "audio_s": round(dur, 2), "ttfa_s": round(ttfa, 3), "total_s": round(total, 3), "rtf": round(total / dur, 3) if dur else None})
            print(nom, "%.1fs audio | 1er son %.2fs | total %.2fs | RTF %.2f" % (dur, ttfa, total, total / dur), flush=True)
    json.dump(lignes, open(RACINE + "/results/piper_medium.json", "w"), ensure_ascii=False, indent=1)
    for kind in ("ordre", "reponse"):
        s = [x for x in lignes if x["kind"] == kind]
        print("== %s : n=%d | audio moy %.1fs | 1er son moy %.2fs (max %.2f) | total moy %.2fs | RTF moy %.2f" % (kind, len(s), statistics.mean(x["audio_s"] for x in s), statistics.mean(x["ttfa_s"] for x in s), max(x["ttfa_s"] for x in s), statistics.mean(x["total_s"] for x in s), statistics.mean(x["rtf"] for x in s)))
asyncio.run(main())
