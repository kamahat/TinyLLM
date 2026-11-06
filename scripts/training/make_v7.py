#!/usr/bin/env python3
"""train_v7.json = train_v5.json + pieges COHERENTS (un seul comportement : appareil absent -> refus SANS appel, ~8 % des donnees)
+ paires CONTRASTEES sur les scripts voisins (v6 : 'Lis-moi la liste de courses' -> vide_liste_courses, 'Mode cinema' -> cinema_off).
'telé du salon' reste EXCLUE de l entrainement (piege tenu en reserve). Aucune lecture/ecriture de HA : clones d exemples existants avec une autre phrase."""
import json, random, re, collections
D = "/opt/tinyllm/data/"; random.seed(77)
def norm(t): return re.sub(r"[^a-zàâçéèêëîïôûùüÿœ0-9 ]", "", t.lower()).strip()
EVAL = {norm(x["text"]) for x in json.load(open("/opt/tinyllm/results/c_gemma3v6_none.json"))["results"]}   # phrases du banc : JAMAIS dans l entrainement (formes exactes)

tr = json.load(open(D + "train_v5.json"))
REFUS = ["Je ne connais pas cet appareil.", "Je ne trouve pas cet appareil.", "Je n ai pas trouvé cet appareil."]
out = []; conv = 0
for ex in tr:                                   # (1) piege-erreur -> refus sans appel
    if ex["cat"] == "piege-erreur": ex = dict(ex, cat="piege", steps=[]); conv += 1
    out.append(ex)
# (2) pieges supplementaires : appareils absents (aucun n est dans les noms exposes a Assist)
APPAREIL = ["le four", "le micro-ondes", "le lave-vaisselle", "le lave-linge", "le sèche-linge", "le réfrigérateur", "le congélateur", "la hotte", "la bouilloire", "le grille-pain", "la cafetière", "le robot de cuisine",
            "l aspirateur robot", "la tondeuse", "le robot tondeuse", "l arrosage du jardin", "le ventilateur", "l humidificateur", "le purificateur d air", "le déshumidificateur", "la chaîne hi-fi", "la radio",
            "la console de jeux", "l ordinateur", "l imprimante", "la box internet", "le barbecue", "le spa", "le chauffe-eau", "la machine à pain", "la friteuse", "le mixeur"]
LUMIERE = ["la lampe de chevet", "la lumière de la salle de bain", "la lumière des toilettes", "la lumière de l escalier", "la lumière de la cave", "la lumière de la chambre parentale", "la lumière de la buanderie",
           "la lumière du couloir", "la lampe du bureau des enfants", "la guirlande du sapin", "la lumière de la chambre des enfants", "la lumière du grenier"]
OUVRANT = ["le portail", "le portillon", "la porte d entrée", "la porte de la cave", "la serrure de la porte", "la porte du garage", "la fenêtre de toit", "la porte du jardin"]
CHAUD = ["le radiateur de la salle de bain", "le sèche-serviettes", "le chauffage de la chambre", "le chauffage du bureau", "le poêle"]
TELE = ["la télé de la chambre", "la télé de la cuisine", "la télé du bureau", "la télé de la chambre d amis", "la télévision de la chambre"]   # PAS 'du salon'
V = {"app": (["allume", "démarre", "lance", "mets en marche", "active"], ["éteins", "arrête", "coupe", "stoppe", "désactive"]), "lum": (["allume", "mets"], ["éteins", "coupe"]), "ouv": (["ouvre", "déverrouille"], ["ferme", "verrouille"])}
def phrases():
    for lst, k in ((APPAREIL, "app"), (TELE, "app"), (LUMIERE, "lum"), (OUVRANT, "ouv")):
        for x in lst:
            for v in random.sample(V[k][0], 2) + random.sample(V[k][1], 1): yield "%s %s" % (v, x)
    for x in CHAUD:
        for t in (18, 20, 21): yield "règle %s à %d degrés" % (x, t)
        yield "monte %s" % x; yield "baisse %s" % x
WRAP = ["{}", "{}", "{} s il te plaît", "peux-tu {}", "tu peux {}", "{} tout de suite", "{} maintenant", "jarvis {}", "{} stp", "est-ce que tu peux {}"]
def finish(ph):
    s = random.choice(WRAP).format(ph); s = s[0].upper() + s[1:]
    return s + random.choice(["", "", ".", " ?" if s.lower().startswith(("peux", "tu peux", "est-ce")) else ""])
base = [ex for ex in out if ex["cat"] in ("lumiere", "volets", "scripts", "clim", "info", "todo", "zone", "stop")]
allp = list(phrases()); random.shuffle(allp)
new = []
for ph in allp:
    if len(new) >= 140: break
    ex = random.choice(base); h = ex["hist"] if random.random() < 0.35 else []; u = finish(ph)
    if norm(u) in EVAL: continue
    new.append({"cat": "piege", "system": ex["system"], "hist": h, "user": u, "steps": [], "final": random.choice(REFUS)})
assert not any(re.search(r"télé(vision)? du salon", n["user"], re.I) for n in new)
# (3) paires contrastees : on clone des exemples existants (memes steps/final) avec de nouvelles formulations
def clones(tool, phrases_, per, tag):
    src = [e for e in out if e["steps"] and e["steps"][0]["tool"] == tool and not e["hist"]]
    assert src, tool; res = []
    for ph in phrases_:
        for _ in range(per):
            e = random.choice(src); u = finish(ph) if random.random() < 0.6 else ph[0].upper() + ph[1:]
            if norm(u) in EVAL: u = finish("peux-tu " + ph) 
            if norm(u) in EVAL: continue
            res.append(dict(e, cat=tag, user=u))
    return res
CIN_ON = ["mode cinéma", "cinéma", "le cinéma", "lance le cinéma", "mets le mode cinéma", "démarre le cinéma", "active le cinéma", "séance cinéma", "on se fait un film", "allume le cinéma"]
CIN_OFF = ["arrête le cinéma", "coupe le mode cinéma", "fin du cinéma", "éteins le cinéma", "stoppe le cinéma", "désactive le mode cinéma", "termine le cinéma", "c est fini le cinéma", "ferme le cinéma"]
LIRE = ["lis-moi la liste de courses", "lis la liste de courses", "qu est-ce qu il y a dans la liste de courses", "dis-moi ce qu il y a sur la liste de courses", "quels sont les articles de la liste de courses",
        "qu est-ce que je dois acheter", "la liste de courses", "montre-moi la liste de courses", "qu est-ce qu il y a sur la liste", "lis-moi ma liste de courses"]
VIDER = ["vide la liste de courses", "efface toute la liste de courses", "nettoie la liste de courses", "supprime tout de la liste de courses", "remets la liste de courses à zéro", "vide la liste", "efface la liste de courses entière", "supprime toute la liste de courses"]
new += clones("script__cinema_on", CIN_ON, 3, "scripts") + clones("script__cinema_off", CIN_OFF, 3, "scripts")
new += clones("todo__get_items", LIRE, 4, "todo") + clones("script__vide_liste_courses", VIDER, 3, "scripts")
out += new; random.shuffle(out)
json.dump(out, open(D + "train_v7.json", "w"), ensure_ascii=False)
c = collections.Counter(e["cat"] for e in out)
print(len(out), "exemples ; piege-erreur convertis :", conv, "; ajoutes :", len(new), "; pieges :", c["piege"], "(%.1f %%)" % (100.0 * c["piege"] / len(out)))
print(c.most_common())

assert not [e for e in out[len(tr):] if norm(e["user"]) in EVAL] and not [e for e in new if norm(e["user"]) in EVAL]
print("phrases du banc exclues de l entrainement :", len(EVAL))
