import json, random, re, unicodedata
random.seed(42)
D = "/opt/tinyllm/data/"
ents = json.load(open(D + "ha_exposed.json")); recette = json.load(open(D + "recette.json"))
def norm(s):
    s = unicodedata.normalize("NFD", s.lower()); s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", s).split())
BAN = {norm(r["text"]) for r in recette}
byid = {e["entity_id"]: e for e in ents}
N = lambda i: byid[i]["name"]
LIGHTS = {
 "light.lumiere_salon": ["la lumière du salon", "la lumière salon", "le salon", "la lumière de salon"],
 "light.lumiere_tapisserie": ["la lumière tapisserie", "la tapisserie", "la lumière de la tapisserie"],
 "light.bureau_alex_sw_lumiere_bureau_alex": ["la lumière du bureau de Alex", "le bureau de Alex", "la lumière du bureau Alex"],
 "light.lumieres_cuisines": ["les lumières de la cuisine", "la lumière de la cuisine", "la cuisine"],
 "light.sw_lumiere_garage": ["la lumière du garage", "le garage", "la lumière garage"],
 "light.lumiere_terrasse": ["la lumière de la terrasse", "la terrasse", "la lumière terrasse"],
 "light.salon_lumieres_salon_table": ["les lumières de la table du salon", "la table du salon", "les lumières salon table"],
 "light.lumieres_exterieurs": ["les lumières extérieures", "les lumières de l extérieur", "l éclairage extérieur"],
 "light.led_opale_blanche": ["la led Opale blanche", "la led blanche du salon", "la lampe Opale"],
 "light.lumiere_piscine": ["la lumière de la piscine", "la piscine", "l éclairage de la piscine"]}
COVERS = {
 "cover.volets_salon_store_du_groupe": ["les volets du salon", "les volets roulants du salon", "les stores du salon"],
 "cover.vr_chambre_invites_store_du_groupe": ["les volets de la chambre d amis", "les volets de la chambre invités", "les volets de la chambre d invités"],
 "cover.tous_les_volets": ["tous les volets", "l ensemble des volets", "tous les volets roulants"],
 "cover.salon_ecran_de_projection_ecran_de_projection": ["l écran de projection", "l écran du salon", "l écran de cinéma"]}
ON = ["allume", "allumes", "active", "mets", "lance"]; OFF = ["éteins", "éteint", "coupe", "arrête", "désactive"]
OPEN = ["ouvre", "ouvres", "remonte", "lève"]; CLOSE = ["ferme", "fermes", "baisse", "descends"]
PRE = ["", "", "", "Peux-tu ", "Jarvis, ", "S il te plaît, ", "Dis Jarvis, "]; SUF = ["", "", "", " s il te plaît", " maintenant", " tout de suite"]
MIS = {"volets": ["voler", "volés", "voleurs", "voler roulants"], "lumière": ["lumiere", "lumières", "lu mière"], "Alex": ["lionnelle", "Lionnel", "Alexle"],
       "salon": ["salons", "salom"], "tapisserie": ["tapis serie", "tapisseries"], "cuisine": ["cuisines"], "ferme": ["fermes", "ferme-les"], "allume": ["allumes", "et allume"]}
def noise(t):
    if random.random() < 0.25:
        for k, v in MIS.items():
            if k in t and random.random() < 0.6: t = t.replace(k, random.choice(v), 1)
    if random.random() < 0.3:
        t = unicodedata.normalize("NFD", t); t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return t
def fin(t):
    t = t.strip(); t = t[0].upper() + t[1:]
    return t + random.choice(["", ".", ".", " ?" if t.lower().startswith("peux") else "."])
def wrap(core): return noise(fin(random.choice(PRE) + core + random.choice(SUF)))
EX = []
def add(user, tool=None, args=None, text=None, cat="x"):
    if norm(user) in BAN: return
    EX.append({"user": user, "tool": tool, "args": args or {}, "text": text, "cat": cat})
S = {"cinema_on": ["allume le cinéma", "lance le cinéma", "démarre le cinéma", "mets le cinéma", "active le mode cinéma", "lance la séance cinéma"],
     "cinema_off": ["éteins le cinéma", "coupe le cinéma", "arrête le cinéma", "termine le cinéma", "fin de la séance cinéma"],
     "mode_automatique_volets": ["passe les volets en mode automatique", "active le mode automatique des volets", "remets les volets roulants en automatique", "volets en mode auto", "repasse les volets en automatique", "bascule les volets en auto"],
     "vide_liste_courses": ["vide la liste de courses", "efface la liste des courses", "supprime tout de la liste de courses", "remets la liste de courses à zéro", "nettoie la liste de courses"]}
ITEMS = ["du lait", "des œufs", "du pain", "du beurre", "des pommes", "du fromage", "des pâtes", "du café", "du riz", "des tomates", "de la farine", "du jambon", "des yaourts"]
INFO = ["quelle température fait-il dehors", "quelle est la température extérieure", "quelle température y a-t-il dans la douche", "y a-t-il quelqu un à la maison", "il y a du monde à la maison", "quel temps fait-il",
        "est-ce que la lumière de la cuisine est allumée", "est-ce que le garage est allumé", "les volets de la chambre d amis sont-ils fermés", "est-ce que l écran de projection est descendu"]
DT = ["quelle heure est-il", "quelle heure il est", "quel jour sommes-nous", "on est quel jour", "quelle est la date d aujourd hui"]
QA = [("quelle est la capitale de l Espagne", "Madrid."), ("quelle est la capitale du Japon", "Tokyo."), ("combien font six fois sept", "42."), ("combien font neuf fois neuf", "81."),
      ("qui a peint la Joconde", "Léonard de Vinci."), ("quelle est la capitale de l Allemagne", "Berlin."), ("combien y a-t-il de jours dans une semaine", "Sept."), ("quel est le plus grand océan", "L océan Pacifique."),
      ("raconte-moi une blague", "Pourquoi les plongeurs plongent-ils en arrière ? Parce que sinon ils tomberaient dans le bateau."), ("qui a écrit Le Petit Prince", "Antoine de Saint-Exupéry."),
      ("quelle est la capitale du Portugal", "Lisbonne."), ("combien font quinze plus vingt-sept", "42."), ("quelle est la couleur du ciel", "Bleue."), ("donne-moi une idée de repas rapide", "Des pâtes à l ail et à l huile d olive."),
      ("quel est le plus long fleuve de France", "La Loire."), ("quelle est la capitale de l Australie", "Canberra.")]
TR = ["allume le four", "ferme le portail", "éteins la télé de la chambre", "mets le chauffage du salon à 21 degrés", "ouvre la porte du garage", "allume la machine à café", "lance l aspirateur", "éteins la lumière de la salle de bain",
      "verrouille la porte d entrée", "mets de la musique", "allume la lumière de la chambre des enfants", "ouvre le portillon", "éteins l ordinateur", "démarre la machine à laver", "baisse le store de la cuisine", "allume le ventilateur"]
REF = ["Je ne trouve pas cet appareil.", "Je n ai pas compris cette commande.", "Cet appareil n est pas disponible."]
TODO = N("todo.maison_montpellier")
for _ in range(2600):
    k = random.random()
    if k < 0.30:
        e = random.choice(list(LIGHTS)); on = random.random() < 0.5
        add(wrap("%s %s" % (random.choice(ON if on else OFF), random.choice(LIGHTS[e]))), "HassTurnOn" if on else "HassTurnOff", {"name": N(e)}, cat="lumiere")
    elif k < 0.45:
        e = random.choice(list(COVERS)); op = random.random() < 0.5
        add(wrap("%s %s" % (random.choice(OPEN if op else CLOSE), random.choice(COVERS[e]))), "HassTurnOn" if op else "HassTurnOff", {"name": N(e)}, cat="volets")
    elif k < 0.50:
        e = random.choice(["cover.volets_salon_store_du_groupe", "cover.vr_chambre_invites_store_du_groupe"]); p = random.choice([10, 20, 25, 30, 40, 50, 60, 70, 75, 80])
        add(wrap("mets %s à %d pour cent" % (random.choice(COVERS[e]), p)), "HassSetPosition", {"name": N(e), "position": p}, cat="volets")
    elif k < 0.53:
        add(wrap("%s les volets du salon" % random.choice(["arrête", "stoppe"])), "HassStopMoving", {"name": N("cover.volets_salon_store_du_groupe")}, cat="volets")
    elif k < 0.58:
        e = random.choice(list(LIGHTS)[:8]); b = random.choice([10, 20, 30, 40, 50, 60, 70, 80, 90])
        add(wrap("%s %s à %d pour cent" % (random.choice(["mets", "règle", "baisse", "monte"]), random.choice(LIGHTS[e]), b)), "HassLightSet", {"name": N(e), "brightness": b}, cat="lumiere")
    elif k < 0.70:
        t = random.choice(list(S)); add(wrap(random.choice(S[t])), t, {}, cat="scripts")
    elif k < 0.78:
        it = random.choice(ITEMS); nm = re.sub(r"^(du|des|de la) ", "", it); c = random.random()
        if c < 0.5: add(wrap("%s %s %s la liste de courses" % (random.choice(["ajoute", "rajoute", "mets", "note"]), it, random.choice(["à", "sur"]))), "HassListAddItem", {"item": nm, "name": TODO}, cat="todo")
        elif c < 0.7: add(wrap("retire %s de la liste de courses" % it), "HassListRemoveItem", {"item": nm, "name": TODO}, cat="todo")
        elif c < 0.85: add(wrap("coche %s sur la liste de courses" % nm), "HassListCompleteItem", {"item": nm, "name": TODO}, cat="todo")
        else: add(wrap(random.choice(["qu est-ce qu il y a sur la liste de courses", "lis-moi la liste de courses", "que dois-je acheter"])), "get_items", {"name": TODO}, cat="todo")
    elif k < 0.82:
        c = random.random(); n = "Climatisation Salon"
        if c < 0.5: add(wrap("%s la %s à %d degrés" % (random.choice(["mets", "règle", "passe"]), random.choice(["clim du salon", "climatisation du salon"]), random.randint(18, 26))), "HassClimateSetTemperature", {"name": n, "temperature": 0}, cat="clim")
        else:
            on = c < 0.75; add(wrap("%s la %s" % (random.choice(ON if on else OFF), random.choice(["clim du salon", "climatisation du salon"]))), "HassTurnOn" if on else "HassTurnOff", {"name": n}, cat="clim")
    elif k < 0.87: add(wrap(random.choice(INFO)), "GetLiveContext", {}, cat="info")
    elif k < 0.89: add(wrap(random.choice(DT)), "GetDateTime", {}, cat="info")
    elif k < 0.95:
        q, a = random.choice(QA); add(wrap(q), None, None, a, cat="general")
    else: add(wrap(random.choice(TR)), None, None, random.choice(REF), cat="piege")
# la temperature cible doit suivre la phrase : on la relit dans le texte
for x in EX:
    if x["tool"] == "HassClimateSetTemperature":
        x["args"]["temperature"] = int(re.search(r"(\d+) degr", x["user"]).group(1))
seen = set(); OUT = []
for x in EX:
    key = (norm(x["user"]), x["tool"], json.dumps(x["args"], sort_keys=True))
    if key in seen: continue
    seen.add(key); OUT.append(x)
random.shuffle(OUT)
json.dump(OUT, open(D + "train_raw.json", "w"), ensure_ascii=False, indent=1)
from collections import Counter
print(len(OUT), "exemples uniques;", dict(Counter(x["cat"] for x in OUT)))
leak = [x for x in OUT if norm(x["user"]) in BAN]; print("fuites vers la recette :", len(leak))
for x in OUT[:6]: print(" -", x["user"], "->", x["tool"], x["args"], x["text"])
