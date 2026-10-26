import json, random, re, unicodedata, copy
random.seed(7)
D = "/opt/tinyllm/data/"
REAL = json.load(open(D + "ha_real_prompt.json")); SYS = REAL["system"]; TOOLS = REAL["tools"]
TAB = json.load(open(D + "ha_tablet_prompt.json")); TOOLS25 = TAB["tools"]
recette = json.load(open(D + "recette.json"))
def norm(s):
    s = unicodedata.normalize("NFD", str(s).lower()); s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", s).split())
BAN = {norm(r["text"]) for r in recette}
# --- entites du contexte statique reel -------------------------------------------------
head, ctx = SYS.split("Static Context: An overview of the areas and the devices in this smart home:\n")
ctx, tail = ctx.split("\n\nWhen controlling Home Assistant", 1); tail = "\n\nWhen controlling Home Assistant" + tail
BLOCKS = []
for b in re.split(r"(?m)^(?=- names:)", ctx):
    if not b.strip(): continue
    nm = re.search(r"- names: (.*)", b).group(1); dom = re.search(r"domain: (\S+)", b).group(1); ar = re.search(r"areas: (.*)", b)
    BLOCKS.append({"text": b if b.endswith("\n") else b + "\n", "names": [n.strip() for n in nm.split(", ")] if nm != "''" else [], "name0": nm.split(", ")[0] if nm != "''" else "", "domain": dom, "areas": ar.group(1).split(", ") if ar else []})
TIMERLINE = chr(10) + "This device is not able to start timers."
def sysprompt(drop=(), variant=18):
    keep = [b["text"] for b in BLOCKS if b["name0"] not in drop]
    t = tail if variant == 18 else tail.replace(TIMERLINE, "")
    return head + "Static Context: An overview of the areas and the devices in this smart home:" + chr(10) + "".join(keep).rstrip(chr(10)) + t
assert sysprompt() == SYS, "prompt 18 outils : reconstruction differente"
assert sysprompt(variant=25) == TAB["system"], "prompt tablette : reconstruction differente"
assert sysprompt(variant=25) == TAB["system"], "prompt tablette : reconstruction differente"
NM = {norm(b["name0"]): b["name0"] for b in BLOCKS}
def N(x): return NM[norm(x)]          # nom exact (avec ses espaces) tel que dans le contexte
TN = {t["function"]["name"].split("__")[-1]: t["function"]["name"] for t in TOOLS}   # court -> reel
# --- formes parlees ---------------------------------------------------------------------
LIGHTS = {"Lumière Salon": ["la lumière du salon", "la lumière salon", "la lumière de salon"], "Lumière Tapisserie": ["la lumière tapisserie", "la tapisserie", "la lumière de la tapisserie"],
          "Lumière Bureau Alex": ["la lumière du bureau de Alex", "le bureau de Alex", "la lumière du bureau Alex"], "Lumières  Cuisines": ["les lumières de la cuisine", "la lumière de la cuisine", "la cuisine"],
          "Lumière garage": ["la lumière du garage", "le garage", "la lumière garage"], "Lumière Terrasse": ["la lumière de la terrasse", "la terrasse", "la lumière terrasse"],
          "Lumières salon table": ["les lumières de la table du salon", "la table du salon", "les lumières salon table"], "Lumières extérieurs": ["les lumières extérieures", "les lumières de l extérieur", "l éclairage extérieur"],
          "led Opale blanche": ["la led Opale blanche", "la led blanche du salon", "la lampe Opale"], "Lumiere Piscine": ["la lumière de la piscine", "la piscine", "l éclairage de la piscine"]}
COVERS = {"Volets du salon": ["les volets du salon", "les volets roulants du salon", "les stores du salon"], "Volets de la chambre d\x27amis": ["les volets de la chambre d amis", "les volets de la chambre invités", "les volets de la chambre d invités"],
          "Tous les volets": ["tous les volets", "l ensemble des volets", "tous les volets roulants"]}
ZONES = {"Salon": ["salon", "le salon"], "Cuisine": ["cuisine", "la cuisine"], "Bureau Alex": ["bureau de Alex", "le bureau de Alex"], "Terrasse": ["terrasse", "la terrasse"], "Piscine": ["piscine", "la piscine"]}
ON = ["allume", "allumes", "active", "mets", "lance"]; OFF = ["éteins", "éteint", "coupe", "arrête", "désactive"]
OPEN = ["ouvre", "ouvres", "remonte", "lève"]; CLOSE = ["ferme", "fermes", "baisse", "descends"]
PRE = ["", "", "", "Peux-tu ", "Jarvis, ", "S il te plaît, ", "Dis Jarvis, "]; SUF = ["", "", "", " s il te plaît", " maintenant", " tout de suite"]
MIS = {"lumières": ["vumières", "lumiere", "lu mières", "numières"], "vumière": ["lumière"], "éteins": ["éteint", "et teins", "étaient"], "toutes": ["tout", "toute"], "volets": ["voler", "volés", "voleurs", "voler roulants"], "lumière": ["lumiere", "lumières", "lu mière"], "Alex": ["lionnelle", "Lionnel", "Alexle"], "salon": ["salons", "salom"],
       "tapisserie": ["tapis serie", "tapisseries"], "cuisine": ["cuisines"], "ferme": ["fermes", "ferme-les"], "allume": ["allumes", "et allume"], "vide": ["vite", "vides", "vide-moi"], "arrête": ["arrêtes", "arrête-moi", "a raide"]}
def noise(t):
    if random.random() < 0.3:
        for k, v in MIS.items():
            if k in t and random.random() < 0.6: t = t.replace(k, random.choice(v), 1)
    if random.random() < 0.3:
        t = unicodedata.normalize("NFD", t); t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return t
def fin(t):
    t = t.strip(); t = t[0].upper() + t[1:]; return t + random.choice(["", ".", ".", " ?" if t.lower().startswith("peux") else "."])
def wrap(core): return noise(fin(random.choice(PRE) + core + random.choice(SUF)))
OK = ["C est fait.", "D accord, c est fait.", "Voilà, c est fait.", "C est noté.", "Très bien."]
REFUS = ["Je ne trouve pas cet appareil.", "Je n ai pas trouvé cet appareil.", "Je ne connais pas cet appareil."]
ECHEC = ["Désolé, je n ai pas pu faire ça.", "Je n y suis pas arrivé, désolé.", "Ça n a pas marché, désolé."]
def succ(names): return {"speech": {}, "response_type": "action_done", "data": {"targets": [], "success": [{"name": n, "type": "entity", "id": "x.y"} for n in names], "failed": []}}
def err_nomatch(n):
    return random.choice([{"error": "MatchFailedError"}, {"error": "MatchFailedError", "error_text": "No entities matched name"}, {"error": "NoStatesMatchedError"}, {"error": "MatchFailedError", "error_text": "Sorry, I am not aware of any device called " + n}])
def err_fail(): return random.choice([{"error": "IntentHandleError", "error_text": "Service call failed"}, {"error": "IntentHandleError"}, {"error": "HomeAssistantError", "error_text": "Device unavailable"}])
EX = []
def add(user, steps, final, cat, drop=()):
    if norm(user) in BAN: return
    EX.append({"user": user, "steps": steps, "final": final, "cat": cat, "drop": list(drop)})
SCRIPTS = {"cinema_on": ["allume le cinéma", "lance le cinéma", "démarre le cinéma", "mets le cinéma", "active le mode cinéma", "lance la séance cinéma"],
           "cinema_off": ["éteins le cinéma", "coupe le cinéma", "arrête le cinéma", "termine le cinéma", "fin de la séance cinéma"],
           "mode_automatique_volets": ["passe les volets en mode automatique", "active le mode automatique des volets", "remets les volets roulants en automatique", "volets en mode auto", "repasse les volets en automatique", "bascule les volets en auto"],
           "vide_liste_courses": ["vide la liste de courses", "efface la liste des courses", "supprime tout de la liste de courses", "remets la liste de courses à zéro", "nettoie la liste de courses"]}
ITEMS = ["du lait", "des œufs", "du pain", "du beurre", "des pommes", "du fromage", "des pâtes", "du café", "du riz", "des tomates", "de la farine", "du jambon", "des yaourts"]
QA = [("quelle est la capitale de l Espagne", "Madrid."), ("quelle est la capitale du Japon", "Tokyo."), ("combien font six fois sept", "42."), ("combien font neuf fois neuf", "81."), ("qui a peint la Joconde", "Léonard de Vinci."),
      ("quelle est la capitale de l Allemagne", "Berlin."), ("combien y a-t-il de jours dans une semaine", "Sept."), ("quel est le plus grand océan", "L océan Pacifique."), ("raconte-moi une blague", "Pourquoi les plongeurs plongent-ils en arrière ? Parce que sinon ils tomberaient dans le bateau."),
      ("qui a écrit Le Petit Prince", "Antoine de Saint-Exupéry."), ("quelle est la capitale du Portugal", "Lisbonne."), ("combien font quinze plus vingt-sept", "42."), ("quelle est la couleur du ciel", "Bleue."), ("quel est le plus long fleuve de France", "La Loire."), ("quelle est la capitale de l Australie", "Canberra.")]
TRAPS = [("allume le four", "on", "four"), ("ferme le portail", "off", "portail"), ("éteins la télé de la chambre", "off", "télé de la chambre"), ("ouvre la porte du garage", "on", "porte du garage"), ("allume la machine à café", "on", "machine à café"),
         ("lance l aspirateur", "on", "aspirateur"), ("éteins la lumière de la salle de bain", "off", "lumière de la salle de bain"), ("verrouille la porte d entrée", "on", "porte d entrée"), ("allume la lumière de la chambre des enfants", "on", "lumière de la chambre des enfants"),
         ("éteins l ordinateur", "off", "ordinateur"), ("démarre la machine à laver", "on", "machine à laver"), ("baisse le store de la cuisine", "off", "store de la cuisine"), ("allume le ventilateur", "on", "ventilateur"), ("mets de la musique", "on", "musique"),
         ("règle le chauffage de la chambre à 20 degrés", "on", "chauffage de la chambre"), ("allume la lumière du couloir", "on", "lumière du couloir"), ("ferme le garage", "off", "garage")]
AMBIG = ["allume les lumières", "éteins toutes les lumières", "allume tout", "éteins tout", "ferme les volets", "ouvre les volets"]
ZL = {"Salon": "du salon", "Cuisine": "de la cuisine", "Bureau Alex": "du bureau de Alex", "Terrasse": "de la terrasse", "Piscine": "de la piscine"}
ZI = {"Salon": "dans le salon", "Cuisine": "dans la cuisine", "Bureau Alex": "dans le bureau de Alex", "Terrasse": "sur la terrasse", "Piscine": "à la piscine"}
def T(s): return TN[s]
def tc(tool, args, result): return {"tool": tool, "args": args, "result": result}
def live_text(states):
    NL = chr(10); t = "Live Context: An overview of the areas and the devices in this smart home:" + NL
    for b in BLOCKS:
        t += "- names: %s%s  domain: %s%s  state: %s%s" % (b["name0"] or "\x27\x27", NL, b["domain"], NL, "\x27" + str(states.get(b["name0"], "unknown")) + "\x27", NL)
        if b["areas"]: t += "  areas: %s%s" % (", ".join(b["areas"]), NL)
    return t
WD = {"Monday": "lundi", "Tuesday": "mardi", "Wednesday": "mercredi", "Thursday": "jeudi", "Friday": "vendredi", "Saturday": "samedi", "Sunday": "dimanche"}
MO = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
import datetime
for _ in range(4300):
    k = random.random(); P = wrap
    if k < 0.20:
        n = random.choice(list(LIGHTS)); on = random.random() < 0.5; nm = N(n)
        add(P("%s %s" % (random.choice(ON if on else OFF), random.choice(LIGHTS[n]))), [tc(T("HassTurnOn" if on else "HassTurnOff"), {"name": nm}, succ([nm]))], random.choice(OK), "lumiere", [nm])
    elif k < 0.29:
        n = random.choice(list(COVERS)); op = random.random() < 0.5; nm = N(n)
        add(P("%s %s" % (random.choice(OPEN if op else CLOSE), random.choice(COVERS[n]))), [tc(T("HassTurnOn" if op else "HassTurnOff"), {"name": nm}, succ([nm]))], random.choice(OK), "volets", [nm])
    elif k < 0.32:
        n = random.choice(["Volets du salon", "Volets de la chambre d\x27amis"]); p = random.choice([10, 20, 25, 30, 40, 50, 60, 70, 75, 80]); nm = N(n)
        add(P("mets %s à %d pour cent" % (random.choice(COVERS[n]), p)), [tc(T("HassSetPosition"), {"name": nm, "position": p}, succ([nm]))], random.choice(OK), "volets", [nm])
    elif k < 0.38:
        n = random.choice(["Volets du salon", "Volets de la chambre d\x27amis", "Tous les volets"]); nm = N(n)
        add(P("%s %s" % (random.choice(["arrête", "stoppe", "stop", "arrête-toi sur", "interromps"]), random.choice(COVERS[n]))), [tc(T("HassStopMoving"), {"name": nm}, succ([nm]))], random.choice(OK), "stop", [nm])
    elif k < 0.41:
        n = random.choice(list(LIGHTS)[:8]); b = random.choice([10, 20, 30, 40, 50, 60, 70, 80, 90]); nm = N(n)
        add(P("%s %s à %d pour cent" % (random.choice(["mets", "règle", "baisse", "monte"]), random.choice(LIGHTS[n]), b)), [tc(T("HassLightSet"), {"name": nm, "brightness": b}, succ([nm]))], random.choice(OK), "lumiere", [nm])
    elif k < 0.51:
        t = random.choice(list(SCRIPTS)); add(P(random.choice(SCRIPTS[t])), [tc(T(t), {}, {"success": True})], random.choice(OK), "scripts")
    elif k < 0.58:
        it = random.choice(ITEMS); nm = re.sub(r"^(du|des|de la) ", "", it); c = random.random(); L = N("Liste Courses")
        if c < 0.45: add(P("%s %s %s la liste de courses" % (random.choice(["ajoute", "rajoute", "mets", "note"]), it, random.choice(["à", "sur"]))), [tc(T("HassListAddItem"), {"item": nm, "name": L}, {"success": True})], random.choice(OK), "todo", [L])
        elif c < 0.65: add(P("retire %s de la liste de courses" % it), [tc(T("HassListRemoveItem"), {"item": nm, "name": L}, {"success": True})], random.choice(OK), "todo", [L])
        elif c < 0.8: add(P("coche %s sur la liste de courses" % nm), [tc(T("HassListCompleteItem"), {"item": nm, "name": L}, {"success": True})], random.choice(OK), "todo", [L])
        else:
            its = random.sample(["lait", "pain", "œufs", "beurre", "pommes", "café"], random.randint(1, 4))
            add(P(random.choice(["qu est-ce qu il y a sur la liste de courses", "lis-moi la liste de courses", "que dois-je acheter"])), [tc(T("get_items"), {"name": L}, {"success": True, "result": [{"summary": x, "status": "needs_action"} for x in its]})], "Il y a : " + ", ".join(its) + ".", "todo", [L])
    elif k < 0.62:
        c = random.random(); nm = N("Climatisation Salon")
        if c < 0.5:
            t = random.randint(18, 26); add(P("%s la %s à %d degrés" % (random.choice(["mets", "règle", "passe"]), random.choice(["clim du salon", "climatisation du salon"]), t)), [tc(T("HassClimateSetTemperature"), {"name": nm, "temperature": t}, succ([nm]))], random.choice(OK), "clim", [nm])
        else:
            on = c < 0.75; add(P("%s la %s" % (random.choice(ON if on else OFF), random.choice(["clim du salon", "climatisation du salon"]))), [tc(T("HassTurnOn" if on else "HassTurnOff"), {"name": nm}, succ([nm]))], random.choice(OK), "clim", [nm])
    elif k < 0.70:
        z = random.choice(list(ZL)); c = random.random()
        if c < 0.45:
            on = random.random() < 0.5; add(P("%s %s les lumières %s" % (random.choice(ON if on else OFF), random.choice(["toutes", "toutes", ""]), ZL[z])).replace("  ", " "), [tc(T("HassTurnOn" if on else "HassTurnOff"), {"area": z, "domain": ["light"]}, succ([]))], random.choice(OK), "zone")
        elif c < 0.8:
            on = random.random() < 0.5; add(P("%s tout %s" % (random.choice(ON if on else OFF), ZI[z])), [tc(T("HassTurnOn" if on else "HassTurnOff"), {"area": z}, succ([]))], random.choice(OK), "zone")
        elif z == "Salon":
            op = random.random() < 0.5; add(P("%s tous les volets du salon" % random.choice(OPEN if op else CLOSE)), [tc(T("HassTurnOn" if op else "HassTurnOff"), {"area": "Salon", "domain": ["cover"]}, succ([]))], random.choice(OK), "zone")
    elif k < 0.77:
        QI = [("quelle température fait-il dehors", "Température extérieur Sud", "ext"), ("quelle est la température extérieure", "Température extérieur Sud", "ext"), ("quelle température y a-t-il dans la douche", "Température Douche", "dou"), ("quelle est la température de la douche", "Température Douche", "dou")]
        c = random.random(); st = {b["name0"]: random.choice(["on", "off"]) for b in BLOCKS if b["domain"] in ("light", "input_boolean", "binary_sensor")}
        st.update({b["name0"]: random.choice(["open", "closed"]) for b in BLOCKS if b["domain"] == "cover"}); st["Température extérieur Sud"] = str(random.randint(-3, 36)) + ".0"; st["Température Douche"] = str(random.randint(18, 55)) + ".0"
        st["Climatisation Salon"] = "off"; st["Liste Courses"] = "1"; MT = "Prévision Météo France à Montpellier Montpellier"; st[MT] = random.choice(["sunny", "cloudy", "partlycloudy", "rainy", "clear-night"]); PR = "Quelqu\x27un à la maison"; st[PR] = random.choice(["on", "off"])
        wx = {"sunny": "ensoleillé", "cloudy": "nuageux", "partlycloudy": "partiellement nuageux", "rainy": "pluvieux", "clear-night": "dégagé"}; LV = {"result": live_text(st)}
        if c < 0.45:
            q, e, w = random.choice(QI); v = st[e].replace(".0", ""); add(P(q), [tc(T("GetLiveContext"), {}, LV)], ("Il fait %s degrés dehors." if w == "ext" else "La douche est à %s degrés.") % v, "info")
        elif c < 0.6: add(P(random.choice(["y a-t-il quelqu un à la maison", "il y a du monde à la maison", "est-ce qu il y a quelqu un"])), [tc(T("GetLiveContext"), {}, LV)], "Oui, quelqu un est à la maison." if st[PR] == "on" else "Non, il n y a personne.", "info")
        elif c < 0.75: add(P(random.choice(["quelle est la météo", "quel temps fait-il"])), [tc(T("GetLiveContext"), {}, LV)], "Le temps est %s." % wx[st[MT]], "info")
        elif c < 0.9:
            n = random.choice(list(LIGHTS)[:8]); s = st[N(n)]; add(P(random.choice(["est-ce que %s est allumée", "%s est-elle allumée"]) % random.choice(LIGHTS[n])), [tc(T("GetLiveContext"), {}, LV)], "Oui, elle est allumée." if s == "on" else "Non, elle est éteinte.", "info")
        else:
            n = random.choice(["Volets du salon", "Volets de la chambre d\x27amis"]); s = st[N(n)]; add(P("%s sont-ils ouverts" % random.choice(COVERS[n])), [tc(T("GetLiveContext"), {}, LV)], "Oui, ils sont ouverts." if s == "open" else "Non, ils sont fermés.", "info")
    elif k < 0.80:
        d = datetime.datetime(2026, 1, 1) + datetime.timedelta(minutes=random.randint(0, 600000)); r = {"date": d.strftime("%Y-%m-%d"), "time": d.strftime("%H:%M:%S"), "timezone": "CEST", "weekday": d.strftime("%A")}
        if random.random() < 0.5: add(P(random.choice(["quelle heure est-il", "quelle heure il est", "donne-moi l heure"])), [tc(T("GetDateTime"), {}, r)], "Il est %d h %02d." % (d.hour, d.minute), "info")
        else: add(P(random.choice(["quel jour sommes-nous", "on est quel jour", "quelle est la date d aujourd hui"])), [tc(T("GetDateTime"), {}, r)], "Nous sommes %s %d %s %d." % (WD[r["weekday"]], d.day, MO[d.month - 1], d.year), "info")
    elif k < 0.86:
        q, a = random.choice(QA); add(P(q), [], a, "general")
    elif k < 0.93:
        ph, kind, nm = random.choice(TRAPS)
        if random.random() < 0.6: add(P(ph), [], random.choice(REFUS), "piege")
        else: add(P(ph), [tc(T("HassTurnOn" if kind == "on" else "HassTurnOff"), {"name": nm}, err_nomatch(nm))], random.choice(REFUS), "piege-erreur")
    elif k < 0.95: add(P(random.choice(AMBIG)), [], random.choice(["Dans quelle pièce ?", "Dans quelle pièce, s il te plaît ?"]), "ambigu")
    else:
        n = random.choice(list(LIGHTS)[:8]); on = random.random() < 0.5; nm = N(n)
        add(P("%s %s" % (random.choice(ON if on else OFF), random.choice(LIGHTS[n]))), [tc(T("HassTurnOn" if on else "HassTurnOff"), {"name": nm}, err_fail())], random.choice(ECHEC), "echec", [nm])
seen = set(); OUT = []
for x in EX:
    key = (norm(x["user"]), json.dumps(x["steps"], sort_keys=True, ensure_ascii=False)[:200], x["final"])
    if key in seen: continue
    seen.add(key); OUT.append(x)
random.shuffle(OUT)
# --- historiques ---------------------------------------------------------------------------
def commas(t):
    w = t.rstrip(".").split(" ")
    return (", ".join(w[:1]) + ", " + ", ".join(w[1:3]) + (" " + " ".join(w[3:]) if len(w) > 3 else "") if len(w) > 3 and random.random() < 0.5 else t)
def local_turn():
    c = random.random()
    if c < 0.5:
        n = random.choice(list(LIGHTS)[:8]); on = random.random() < 0.5; u = noise(fin(random.choice(ON if on else OFF) + " " + random.choice(LIGHTS[n]))); r = "Allumé" if on else "Éteint"
    elif c < 0.85:
        n = random.choice(list(COVERS)[:3]); op = random.random() < 0.5; u = noise(fin(random.choice(OPEN if op else CLOSE) + " " + random.choice(COVERS[n]))); r = "Ouverture en cours" if op else "Fermeture en cours"
    else:
        n = random.choice(["la lumière du salon", "la lumière tapisserie", "la lumière du bureau de Alex"]); on = random.random() < 0.5; u = fin(random.choice(ON if on else OFF) + " " + n); r = "Allumé" if on else "Éteint"
    if random.random() < 0.35: u = u.replace(" ", ", ", 1) if random.random() < 0.5 else u.replace(" ", ", ", 2)
    return {"user": u, "steps": [], "final": r}
POOL = [x for x in OUT if x["steps"] and x["cat"] in ("lumiere", "volets", "scripts", "todo", "clim", "stop", "zone")]
def tool_turn():
    x = random.choice(POOL); return {"user": x["user"], "steps": x["steps"], "final": x["final"]}
def qa_turn():
    q, a = random.choice(QA); return {"user": wrap(q), "steps": [], "final": a}
def make_hist():
    n = random.choices([0, 1, 2, 3], [40, 30, 20, 10])[0]; h = []
    for _ in range(n):
        c = random.random(); h.append(local_turn() if c < 0.55 else (tool_turn() if c < 0.85 else qa_turn()))
    return h
for x in OUT:
    used = set(x["drop"]); drop = []
    if random.random() < 0.15:
        cands = [b["name0"] for b in BLOCKS if b["name0"] and b["name0"] not in used]; drop = random.sample(cands, random.randint(1, 3))
    x["variant"] = 25 if random.random() < 0.7 else 18; x["hist"] = make_hist(); x["system"] = sysprompt(drop, x["variant"]); x.pop("drop", None)
json.dump(OUT, open(D + "train_v3.json", "w"), ensure_ascii=False)
from collections import Counter
print(len(OUT), "exemples uniques;", dict(Counter(x["cat"] for x in OUT)))
print("variantes :", dict(Counter(x["variant"] for x in OUT)), "| tours d historique :", dict(Counter(len(x["hist"]) for x in OUT)))
print("fuites vers la recette :", len([x for x in OUT if norm(x["user"]) in BAN]))
ex = [x for x in OUT if x["hist"] and x["hist"][0]["steps"] == [] and x["hist"][0]["final"] == "Allumé" and x["steps"]][:2]
for x in ex: print("  ex. historique local :", [(h["user"], h["final"]) for h in x["hist"]], "->", x["user"], "=>", x["steps"][0]["tool"], x["steps"][0]["args"])
