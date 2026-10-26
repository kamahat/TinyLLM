"""Questions externes (a besoin d Internet) en francais parle : (phrase dite, requete de recherche). Separation entrainement/evaluation PAR MODELE de phrase."""
import json, random
random.seed(21)
VILLES = ["Nîmes", "Montpellier", "Lyon", "Paris", "Marseille", "Alès", "Sommières", "Toulouse", "Lille", "Bordeaux", "Nice", "Avignon", "Strasbourg", "Nantes", "Montpellier"]
EQ = ["le PSG", "l OM", "l OL", "Montpellier", "Nîmes Olympique", "le Real Madrid", "le FC Barcelone", "Liverpool", "le XV de France", "Toulouse"]
PROD = ["l essence", "le gazole", "le gaz", "l or", "le bitcoin", "l électricité", "le baril de pétrole"]
T = [  # (modele de phrase dite, modele de requete, categorie)
 ("Quelle est la météo demain à {v} ?", "météo demain {v}", "meteo"), ("Quel temps fait-il demain à {v} ?", "météo demain {v}", "meteo"), ("Est-ce qu il va pleuvoir demain à {v} ?", "pluie demain {v}", "meteo"),
 ("Quelle météo ce week-end à {v} ?", "météo week-end {v}", "meteo"), ("Il fera combien de degrés demain à {v} ?", "température demain {v}", "meteo"), ("Va-t-il neiger cette semaine à {v} ?", "neige cette semaine {v}", "meteo"),
 ("Quelle est la météo demain ?", "météo demain Montpellier", "meteo"), ("Quel temps ce week-end ?", "météo week-end Montpellier", "meteo"), ("Est-ce qu il va pleuvoir demain ?", "pluie demain Montpellier", "meteo"),
 ("Quelles sont les actualités du jour ?", "actualités du jour France", "actu"), ("Quelles sont les dernières infos ?", "dernières infos France", "actu"), ("Que se passe-t-il aujourd hui en France ?", "actualité France aujourd hui", "actu"),
 ("Quelles sont les infos sur {s} ?", "actualité {s}", "actu"),
 ("Qui a gagné le match de {e} ?", "résultat match {e}", "sport"), ("Quel est le score de {e} ?", "score {e}", "sport"), ("Quand joue {e} ?", "prochain match {e}", "sport"), ("Comment s est terminé le dernier match de {e} ?", "dernier match {e} résultat", "sport"),
 ("Quel est le classement de la Ligue 1 ?", "classement Ligue 1", "sport"), ("Qui est en tête du championnat de France ?", "classement Ligue 1", "sport"),
 ("Quel est le prix de {p} aujourd hui ?", "prix {p} aujourd hui", "prix"), ("Combien coûte {p} en ce moment ?", "prix {p}", "prix"), ("Quel est le cours de {p} ?", "cours {p}", "prix"),
 ("Quels sont les horaires de la pharmacie à {v} ?", "horaires pharmacie {v}", "horaires"), ("Quelle pharmacie de garde est ouverte à {v} ?", "pharmacie de garde {v}", "horaires"), ("À quelle heure ferme la mairie de {v} ?", "horaires mairie {v}", "horaires"),
 ("Quels sont les horaires du train pour {v} ?", "horaires train {v}", "horaires"), ("Y a-t-il des perturbations sur le réseau SNCF aujourd hui ?", "perturbations SNCF aujourd hui", "horaires"),
 ("Quel film passe au cinéma ce soir ?", "films au cinéma ce soir", "culture"), ("Qu est-ce qu il y a à la télé ce soir ?", "programme TV ce soir", "culture"), ("Quels sont les films qui sortent cette semaine ?", "sorties cinéma cette semaine", "culture"),
 ("Qui est le président de la République en ce moment ?", "président de la République actuel", "recent"), ("Quelle est la date des prochaines élections ?", "date prochaines élections France", "recent"),
 ("Quel est le dernier album de {a} ?", "dernier album {a}", "recent"), ("Qui a gagné la dernière Coupe du monde de football ?", "vainqueur dernière Coupe du monde football", "recent"),
 ("Combien de temps pour aller de {v} à {w} en voiture ?", "trajet voiture {v} {w} durée", "trajet"), ("Quelle est la distance entre {v} et {w} ?", "distance {v} {w}", "trajet"),
 ("Quel est l indice de pollen aujourd hui à {v} ?", "pollen aujourd hui {v}", "meteo"), ("À quelle heure se couche le soleil aujourd hui ?", "coucher du soleil aujourd hui Montpellier", "meteo"),
]
SUJ = ["la météo", "le sport", "l économie", "la politique", "la santé", "l énergie", "le climat"]; ART = ["Angèle", "Stromae", "Daft Punk", "Indochine", "Gims", "Julien Clerc"]
items = []
for k, (ph, q, cat) in enumerate(T):
    ev = random.random() < 0.18          # ~18 % des modeles de phrase reserves a l evaluation
    for _ in range(9 if "{" in ph else 1):
        v, w = random.sample(VILLES, 2); e = random.choice(EQ); p = random.choice(PROD); s = random.choice(SUJ); a = random.choice(ART)
        fmt = dict(v=v, w=w, e=e, p=p, s=s, a=a)
        items.append({"id": len(items), "cat": cat, "phrase": ph.format(**fmt), "query": q.format(**fmt), "split": "eval" if ev else "train", "modele": k})
seen = set(); out = []
for x in items:
    if (x["phrase"]) in seen: continue
    seen.add(x["phrase"]); out.append(x)
json.dump(out, open("/opt/tinyllm/data/web_queries.json", "w"), ensure_ascii=False, indent=1)
from collections import Counter
print(len(out), "questions externes ;", dict(Counter(x["split"] for x in out)), dict(Counter(x["cat"] for x in out)))
