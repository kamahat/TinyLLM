"""Construit le « pack de connaissance » de la maison : un document par entite (nom, zone, synonymes, exemples de phrases),
utilise (1) pour l index vectoriel (RAG) et (2) pour choisir le sous-ensemble d outils a envoyer au modele."""
import json
D = "/opt/tinyllm/data/"
ents = json.load(open(D + "ha_exposed.json"))
SYN = {"light": ("lumière éclairage lampe", "allume éteins mets la lumière", "Allume {n}. Éteins {n}."),
       "cover": ("volet store volets roulants ouvrir fermer", "ouvre ferme remonte baisse", "Ferme {n}. Ouvre {n}."),
       "script": ("script scénario action", "lance exécute active", "Lance {n}."),
       "todo": ("liste de courses courses acheter", "ajoute retire coche lis", "Ajoute du lait à {n}."),
       "climate": ("climatisation clim chauffage température", "mets règle allume éteins", "Mets {n} à 22 degrés."),
       "sensor": ("capteur température mesure", "quelle est la température", "Quelle est la valeur de {n} ?"),
       "binary_sensor": ("capteur présence état", "y a-t-il quelqu un", "Quel est l état de {n} ?"),
       "weather": ("météo prévision temps", "quel temps fait-il", "Quelle est la météo ?"),
       "input_boolean": ("mode interrupteur virtuel", "active désactive", "Active {n}. Désactive {n}."),
       "automation": ("automatisation", "active désactive", "Désactive {n}."),
       "button": ("bouton", "appuie sur", "Appuie sur {n}.")}
docs = []
for e in ents:
    s = SYN.get(e["domain"], ("", "", ""))
    txt = "%s. Type : %s. %s. %s%s Exemples : %s" % (e["name"], e["domain"], s[0], ("Zone : %s. " % e["area"]) if e["area"] else "", " ".join(e["aliases"]), s[2].format(n=e["name"]))
    docs.append({"id": e["entity_id"], "name": e["name"], "domain": e["domain"], "text": txt})
json.dump(docs, open(D + "knowledge_pack.json", "w"), ensure_ascii=False, indent=1)
print(len(docs), "documents. Exemple :", docs[1]["text"])
