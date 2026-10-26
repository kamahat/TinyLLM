#!/usr/bin/env python3
"""Exemples web SYNTHETIQUES : extraits de recherche fabriques (style reel) + reponse calculee par regle a partir des memes valeurs. Distracteurs = vrais extraits d autres requetes."""
import json, random, re, os, sys
sys.path.insert(0, "/opt/tinyllm/compact")
os.environ["COMPACT_WEB"] = "1"
import websearch as W
D = "/opt/tinyllm/data/"; rng = random.Random(99)
Q = json.load(open(D + "web_queries.json")) + json.load(open(D + "web_queries2.json"))
real = [g for f in ("web_gold.json", "web_gold2.json") for g in json.load(open(D + f))]
POOL = []
for g in real:
    for l in g["results_text"].split(chr(10))[1:]:
        m = re.match(r"\d+\. (.*?) : (.*) \[(.*)\]$", l)
        if m: POOL.append({"titre": m.group(1), "extrait": m.group(2), "site": m.group(3)})
VILLES = ["Nîmes", "Montpellier", "Lyon", "Paris", "Marseille", "Alès", "Sommières", "Toulouse", "Lille", "Bordeaux", "Nice", "Avignon", "Strasbourg", "Nantes", "Montpellier"]
CIEL = ["ciel nuageux", "ciel dégagé", "éclaircies", "ciel couvert", "quelques averses", "temps ensoleillé", "pluie faible", "brouillard le matin"]
ADV = ["Lens", "Nice", "Rennes", "Monaco", "Brest", "Lille", "Nantes", "Strasbourg", "Lorient", "Reims"]
JOURS = ["samedi", "dimanche", "mercredi", "vendredi", "mardi"]
def fr(x): return str(x).replace(".", ",")
def pick(d, n): return rng.sample(POOL, n) if len(POOL) >= n else []
def find(phrase, lst, default):
    for x in lst:
        for k in (x if isinstance(x, tuple) else (x,)):
            if k.lower() in phrase.lower().replace("l ", "l").replace("l\x27", "l") or k.lower() in phrase.lower(): return x
    return default
def make(it):
    p = it["phrase"]; q = it["query"]; c = it["cat"]; v = next((x for x in VILLES if x.lower() in p.lower()), "Montpellier"); rel = None; ans = None; exp = []
    if c == "meteo" and "soleil" in p:
        h, m = rng.randint(17, 19), rng.randint(0, 59); rel = ("Coucher du soleil à %s" % v, "Aujourd hui à %s : lever du soleil %d h %02d, coucher du soleil %d h %02d." % (v, 8, rng.randint(0, 59), h, m), "heure.example"); ans = "Le soleil se couche à %d h %02d." % (h, m); exp = ["%d h" % h]
    elif c == "meteo" and "pollen" in p:
        n = rng.choice(["faible", "moyen", "élevé"]); rel = ("Pollens %s" % v, "Risque d allergie aux pollens aujourd hui à %s : niveau %s (graminées, cyprès)." % (v, n), "pollens.example"); ans = "Le risque de pollen est %s aujourd hui à %s." % (n, v); exp = [n]
    elif c == "meteo":
        tmin = rng.randint(-2, 18); tmax = tmin + rng.randint(3, 11); ciel = rng.choice(CIEL); pl = rng.choice([0, 10, 20, 40, 60, 80]); quand = "ce week-end" if "week-end" in p else "demain"
        rel = ("Météo %s %s - prévisions" % (v, quand), "%s à %s : %s, températures de %d°C à %d°C. Probabilité de précipitations %d %%." % (quand.capitalize(), v, ciel, tmin, tmax, pl), "meteo-france.example")
        if "pleuvoir" in p or "neiger" in p: ans = ("Oui, %d pour cent de risque de pluie %s à %s." % (pl, quand, v)) if pl >= 40 else ("Non, peu de risque de pluie %s à %s, %d pour cent." % (quand, v, pl)); exp = [str(pl)]
        elif "degrés" in p: ans = "%s à %s, entre %d et %d degrés." % (quand.capitalize(), v, tmin, tmax); exp = [str(tmin), str(tmax)]
        else: ans = "%s à %s, %s, entre %d et %d degrés." % (quand.capitalize(), v, ciel, tmin, tmax); exp = [str(tmin), str(tmax)]
    elif c == "sport":
        eq = next((x for x in ("PSG", "OM", "OL", "Montpellier", "Nîmes", "Real Madrid", "Barcelone", "Liverpool", "XV de France", "Toulouse") if x.lower() in p.lower()), "PSG"); adv = rng.choice(ADV); a, b = rng.randint(0, 4), rng.randint(0, 3); jour = rng.choice(JOURS); h = rng.choice([17, 19, 20, 21])
        if "Quand joue" in p: rel = ("Prochain match %s" % eq, "Le prochain match de %s : %s à %d h 00 contre %s." % (eq, jour, h, adv), "sport.example"); ans = "%s joue %s à %d h contre %s." % (eq, jour, h, adv); exp = [jour, str(h)]
        elif "classement" in p.lower() or "tête" in p: pts = rng.randint(20, 60); rel = ("Classement Ligue 1", "1. %s %d pts ; 2. %s %d pts ; 3. %s %d pts." % (eq, pts, adv, pts - 3, rng.choice(ADV), pts - 5), "classement.example"); ans = "%s est en tête avec %d points." % (eq, pts); exp = [str(pts)]
        else: rel = ("%s - résultat" % eq, "Dernier match : %s %d - %d %s." % (eq, a, b, adv), "sport.example"); ans = ("%s a gagné %d à %d contre %s." % (eq, a, b, adv)) if a > b else (("%s a perdu %d à %d contre %s." % (eq, a, b, adv)) if a < b else ("%s a fait match nul %d partout contre %s." % (eq, a, adv))); exp = [str(a), str(b)]
    elif c == "prix":
        prod, u, lo, hi = rng.choice([("le gazole", "euros le litre", 1.6, 2.1), ("l essence", "euros le litre", 1.7, 2.2), ("le gaz", "euros le mégawattheure", 30, 60), ("l électricité", "centimes le kilowattheure", 18, 26), ("l or", "euros l once", 2000, 3500), ("le bitcoin", "euros", 50000, 95000)])
        val = round(rng.uniform(lo, hi), 2 if hi < 100 else 0); rel = ("Prix %s aujourd hui" % prod, "Le prix %s est de %s %s aujourd hui." % (prod, fr(val), u), "prix.example"); ans = "%s coûte %s %s." % (prod.capitalize(), fr(val), u); exp = [fr(val).split(",")[0]]
    elif c == "horaires" and ("pharmacie" in p or "mairie" in p):
        h, m = rng.randint(17, 20), rng.choice([0, 30]); n = "pharmacie" if "pharmacie" in p else "mairie"; rel = ("%s de %s - horaires" % (n.capitalize(), v), "%s de %s ouverte du lundi au samedi de 8 h 30 à %d h %02d." % (n.capitalize(), v, h, m), "horaires.example"); ans = "La %s de %s ferme à %d h %02d." % (n, v, h, m); exp = ["%d h" % h]
    elif c == "horaires": h, m = rng.randint(6, 21), rng.randint(0, 59); rel = ("Horaires train %s" % v, "Prochain départ pour %s : %d h %02d, voie %d." % (v, h, m, rng.randint(1, 8)), "sncf.example"); ans = "Le prochain train part à %d h %02d." % (h, m); exp = ["%d h" % h]
    elif c == "trajet": km = rng.randint(20, 650); mn = int(km * rng.uniform(0.8, 1.1)); rel = ("Trajet %s" % q, "Distance : %d km, durée estimée %d h %02d en voiture." % (km, mn // 60, mn % 60), "trajet.example"); ans = "Environ %d kilomètres, %d h %02d de route." % (km, mn // 60, mn % 60); exp = [str(km)]
    else: return None
    items = [{"titre": rel[0], "extrait": rel[1], "site": rel[2]}] + pick(POOL, 3)
    if rng.random() < 0.1: items = pick(POOL, 4); ans = "Je n ai pas trouvé de réponse fiable."; exp = []
    else: rng.shuffle(items)
    return {"id": it["id"], "cat": c, "phrase": p, "query": q, "split": it["split"], "results_text": W.format_results(q, items), "answer": ans, "expect": exp}
out = []
for it in Q:
    for rep in range(4 if it["split"] == "train" else 3):
        x = make(it)
        if x: out.append(x)
json.dump(out, open(D + "web_synth.json", "w"), ensure_ascii=False)
import collections
print(len(out), "exemples synthetiques ;", dict(collections.Counter(x["split"] for x in out)), dict(collections.Counter(x["cat"] for x in out)), "| distracteurs reels :", len(POOL))
x = next(y for y in out if y["cat"] == "meteo"); print(x["phrase"], "->", x["answer"]); print(x["results_text"][:420])
