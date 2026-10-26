import json
R = []
def add(cat, text, tool=None, args=None, no_tool=False):
    R.append({"id": "%03d" % (len(R) + 1), "cat": cat, "text": text, "tool": tool, "args": args or {}, "no_tool": no_tool})

# A. lumieres (nom complet de l entite)
L = {"Lumière Salon": ["Allume la lumière du salon", "Éteins la lumière du salon", "Peux-tu allumer la lumière du salon ?"],
     "Lumière Tapisserie": ["Allume la lumière tapisserie", "Éteins la lumière tapisserie", "Mets la tapisserie en lumière"],
     "Lumière Bureau Alex": ["Allume la lumière du bureau de Alex", "Éteins la lumière du bureau de Alex"],
     "Lumières Cuisines": ["Éteins les lumières de la cuisine", "Allume la cuisine"],
     "Lumière garage": ["Allume la lumière du garage", "Éteins le garage"],
     "Lumière Terrasse": ["Allume la lumière de la terrasse", "Éteins la terrasse"],
     "Lumières salon table": ["Allume les lumières de la table du salon", "Éteins la table du salon"],
     "Lumières extérieurs": ["Allume les lumières extérieures", "Éteins les lumières extérieures"]}
for name, phrases in L.items():
    for p in phrases:
        on = any(w in p.lower() for w in ("allume", "mets"))
        add("lumiere", p, "HassTurnOn" if on else "HassTurnOff", {"name": name})
add("lumiere", "Mets la lumière du salon à 50 pour cent", "HassLightSet", {"name": "Lumière Salon", "brightness": 50})
add("lumiere", "Baisse la lumière de la cuisine à 30 pour cent", "HassLightSet", {"name": "Lumières Cuisines", "brightness": 30})
add("lumiere", "Allume toutes les lumières du salon", "HassTurnOn", {"area": "Salon", "domain": "light"})
add("lumiere", "Éteins tout dans le salon", "HassTurnOff", {"area": "Salon"})

# B. volets
for p, t, n in [("Ferme les volets du salon", "HassTurnOff", "Volets du salon"), ("Ouvre les volets du salon", "HassTurnOn", "Volets du salon"),
                ("Ferme les volets de la chambre d amis", "HassTurnOff", "Volets de la chambre d'amis"), ("Ouvre les volets de la chambre d amis", "HassTurnOn", "Volets de la chambre d'amis"),
                ("Ferme tous les volets", "HassTurnOff", "Tous les volets"), ("Ouvre tous les volets", "HassTurnOn", "Tous les volets"),
                ("Peux-tu fermer tous les volets ?", "HassTurnOff", "Tous les volets"), ("Baisse l écran de projection", "HassTurnOff", "Écran de projection"),
                ("Remonte l écran de projection", "HassTurnOn", "Écran de projection")]:
    add("volets", p, t, {"name": n})
add("volets", "Mets les volets du salon à moitié", "HassSetPosition", {"name": "Volets du salon", "position": 50})
add("volets", "Ouvre les volets du salon à 30 pour cent", "HassSetPosition", {"name": "Volets du salon", "position": 30})
add("volets", "Arrête les volets du salon", "HassStopMoving", {"name": "Volets du salon"})

# C. scripts
for p, tool in [("Allume le cinéma", "cinema_on"), ("Lance le cinéma", "cinema_on"), ("Mode cinéma", "cinema_on"), ("Éteins le cinéma", "cinema_off"),
                ("Arrête le cinéma", "cinema_off"), ("Fin du cinéma", "cinema_off"),
                ("Passe les volets en mode automatique", "mode_automatique_volets"), ("Active le mode automatique des volets", "mode_automatique_volets"),
                ("Remets les volets roulants en automatique", "mode_automatique_volets"), ("Vide la liste de courses", "vide_liste_courses"),
                ("Efface la liste de courses", "vide_liste_courses"), ("Nettoie la liste des courses", "vide_liste_courses")]:
    add("scripts", p, tool)

# D. liste de courses
add("todo", "Ajoute du lait à la liste de courses", "HassListAddItem", {"item": "lait"})
add("todo", "Ajoute des œufs à la liste de courses", "HassListAddItem", {"item": "œufs"})
add("todo", "Mets du pain sur la liste de courses", "HassListAddItem", {"item": "pain"})
add("todo", "Retire le lait de la liste de courses", "HassListRemoveItem", {"item": "lait"})
add("todo", "Coche le pain sur la liste de courses", "HassListCompleteItem", {"item": "pain"})
add("todo", "Qu est-ce qu il y a sur la liste de courses ?", "get_items")
add("todo", "Lis-moi la liste de courses", "get_items")

# E. climatisation
add("clim", "Mets la clim du salon à 22 degrés", "HassClimateSetTemperature", {"name": "Climatisation Salon", "temperature": 22})
add("clim", "Règle la climatisation du salon sur 24", "HassClimateSetTemperature", {"name": "Climatisation Salon", "temperature": 24})
add("clim", "Allume la climatisation du salon", "HassTurnOn", {"name": "Climatisation Salon"})
add("clim", "Éteins la clim du salon", "HassTurnOff", {"name": "Climatisation Salon"})

# F. etat / info (lecture)
for p in ["Quelle température fait-il dehors ?", "Quelle est la température de la douche ?", "Y a-t-il quelqu un à la maison ?", "Quelle est la météo ?",
          "Est-ce que la lumière du salon est allumée ?", "Les volets du salon sont-ils ouverts ?", "Est-ce que la cuisine est allumée ?"]:
    add("info", p, "GetLiveContext")
add("info", "Quelle heure est-il ?", "GetDateTime")
add("info", "Quel jour sommes-nous ?", "GetDateTime")

# G. culture generale (pas d outil)
for p in ["Quelle est la capitale de l Italie ?", "Combien font sept fois huit ?", "Raconte-moi une blague courte", "Qui a écrit Les Misérables ?",
          "Donne-moi une idée de dessert rapide", "Quelle est la plus haute montagne du monde ?"]:
    add("general", p, no_tool=True)

# H. pieges : appareil inexistant -> aucun outil ne doit etre appele
for p in ["Allume le four", "Ferme le portail", "Éteins la télé du salon", "Mets le chauffage de la chambre à 20 degrés", "Ouvre la porte du garage",
          "Allume la machine à café", "Lance l aspirateur", "Éteins la lumière de la salle de bain", "Verrouille la porte d entrée", "Mets de la musique dans le salon"]:
    add("piege", p, no_tool=True)

# I. bruit de transcription (ce que Whisper a vraiment sorti)
for p, tool, a in [("Fermes voler salon", "HassTurnOff", {"name": "Volets du salon"}), ("Allume lumière bureau lionnelle", "HassTurnOn", {"name": "Lumière Bureau Alex"}),
                   ("Et un lumière tapisserie", "HassTurnOn", {"name": "Lumière Tapisserie"}), ("Allume lumière tapisserie.", "HassTurnOn", {"name": "Lumière Tapisserie"}),
                   ("Passent les volets roulants en mode automatique.", "mode_automatique_volets", {}), ("Ferme les volets du salon.", "HassTurnOff", {"name": "Volets du salon"}),
                   ("Vite la liste de courses", "vide_liste_courses", {}), ("Éteins la lumière, tapisserie.", "HassTurnOff", {"name": "Lumière Tapisserie"}),
                   ("Allume la lumière du bureau lionnel", "HassTurnOn", {"name": "Lumière Bureau Alex"}), ("Ouvre les voleurs de la chambre d amis", "HassTurnOn", {"name": "Volets de la chambre d'amis"})]:
    add("bruit", p, tool, a)
json.dump(R, open("/opt/tinyllm/data/recette.json", "w"), ensure_ascii=False, indent=1)
from collections import Counter
print(len(R), "phrases", dict(Counter(r["cat"] for r in R)))
