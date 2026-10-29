#!/usr/bin/env python3
"""train_v6.json = train_v5.json avec des pieges COHERENTS : un appareil absent de la maison -> refus SANS appel d outil, toujours.
Constat v5 : les memes phrases servaient a la fois a 'piege' (pas d appel, 60 %) et 'piege-erreur' (appel puis refus sur erreur, 40 %) : un modele qui choisit l appel dans 40 % des cas
appelle l outil sur les pieges (Gemma 3 1B : 'telé du salon', 'aspirateur'). v6 : (1) les piege-erreur deviennent des refus sans appel, (2) ~450 exemples ajoutes sur ~60 appareils absents.
La phrase d evaluation 'tele du salon' est EXCLUE de l entrainement (piege tenu en reserve). Aucune lecture/ecriture de HA."""
import json, random, re
D = "/opt/tinyllm/data/"; random.seed(66)
tr = json.load(open(D + "train_v5.json"))
REFUS = ["Je ne connais pas cet appareil.", "Je ne trouve pas cet appareil.", "Je n ai pas trouvé cet appareil."]
# --- (1) piege-erreur -> refus sans appel
conv = 0; out = []
for ex in tr:
    if ex["cat"] == "piege-erreur":
        ex = dict(ex, cat="piege", steps=[]); conv += 1
    out.append(ex)
# --- (2) nouveaux appareils absents (verifies contre les noms exposes du prompt de la tablette : aucun n y figure)
APPAREIL = ["le four", "le micro-ondes", "le lave-vaisselle", "le lave-linge", "le sèche-linge", "le réfrigérateur", "le congélateur", "la hotte", "la bouilloire", "le grille-pain", "la cafetière", "le robot de cuisine",
            "l aspirateur robot", "la tondeuse", "le robot tondeuse", "l arrosage du jardin", "le ventilateur", "l humidificateur", "le purificateur d air", "le déshumidificateur", "la chaîne hi-fi", "la radio",
            "la console de jeux", "l ordinateur", "l imprimante", "la box internet", "le barbecue", "le spa", "le chauffe-eau", "la machine à pain", "la friteuse", "le mixeur"]
LUMIERE = ["la lampe de chevet", "la lumière de la salle de bain", "la lumière des toilettes", "la lumière de l escalier", "la lumière de la cave", "la lumière de la chambre parentale", "la lumière de la buanderie",
           "la lumière du couloir", "la lampe du bureau des enfants", "la guirlande du sapin", "la lumière de la chambre des enfants", "la lumière du grenier"]
OUVRANT = ["le portail", "le portillon", "la porte d entrée", "la porte de la cave", "la serrure de la porte", "la porte du garage", "la fenêtre de toit", "la porte du jardin"]
CHAUD = ["le radiateur de la salle de bain", "le sèche-serviettes", "le chauffage de la chambre", "le chauffage du bureau", "le poêle"]
TELE = ["la télé de la chambre", "la télé de la cuisine", "la télé du bureau", "la télé de la chambre d amis", "la télévision de la chambre"]   # PAS 'du salon' (piege tenu en reserve)
V_APP_ON = ["allume", "démarre", "lance", "mets en marche", "active"]; V_APP_OFF = ["éteins", "arrête", "coupe", "stoppe", "désactive"]
V_LUM_ON = ["allume", "mets"]; V_LUM_OFF = ["éteins", "coupe"]; V_OPEN_ON = ["ouvre", "déverrouille"]; V_OPEN_OFF = ["ferme", "verrouille"]
def phrases():
    for lst, von, voff in ((APPAREIL, V_APP_ON, V_APP_OFF), (TELE, V_APP_ON, V_APP_OFF), (LUMIERE, V_LUM_ON, V_LUM_OFF), (OUVRANT, V_OPEN_ON, V_OPEN_OFF)):
        for x in lst:
            for v in random.sample(von, 2) + random.sample(voff, 1): yield "%s %s" % (v, x)
    for x in CHAUD:
        for t in (18, 20, 21): yield "règle %s à %d degrés" % (x, t)
        yield "monte %s" % x; yield "baisse %s" % x
WRAP = ["{}", "{}", "{} s il te plaît", "peux-tu {}", "tu peux {}", "{} tout de suite", "{} maintenant", "jarvis {}", "{} stp", "est-ce que tu peux {}"]
def finish(ph):
    s = random.choice(WRAP).format(ph); s = s[0].upper() + s[1:]
    return s + random.choice(["", "", ".", " ?" if s.lower().startswith(("peux", "tu peux", "est-ce")) else ""])
base = [ex for ex in out if ex["cat"] in ("lumiere", "volets", "scripts", "clim", "info", "todo", "zone", "stop")]
new = []
for ph in list(phrases()) + list(phrases()):
    ex = random.choice(base); h = ex["hist"] if random.random() < 0.35 else []
    new.append({"cat": "piege", "system": ex["system"], "hist": h, "user": finish(ph), "steps": [], "final": random.choice(REFUS)})
assert not any(re.search(r"télé(vision)? du salon", n["user"], re.I) for n in new)
out += new; random.shuffle(out)
json.dump(out, open(D + "train_v6.json", "w"), ensure_ascii=False)
import collections
c = collections.Counter(e["cat"] for e in out)
print(len(out), "exemples ; piege-erreur convertis :", conv, "; ajoutes :", len(new), "; piege total :", c["piege"], "(%.1f %%)" % (100.0 * c["piege"] / len(out)))
print(c.most_common())
