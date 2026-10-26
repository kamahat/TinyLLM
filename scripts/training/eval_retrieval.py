"""Compare des modeles d embedding : la bonne entite est-elle dans le top-k pour chaque phrase de la recette ?"""
import json, sys, time, numpy as np
from sentence_transformers import SentenceTransformer
D = "/var/lib/tinyllm/data/"
docs = json.load(open(D + "knowledge_pack.json")); R = json.load(open(D + "recette.json"))
SC = {"cinema_on": "Allume Cinéma", "cinema_off": "Eteint Cinéma", "mode_automatique_volets": "Mode automatique des volets", "vide_liste_courses": "Vide Liste Courses"}
Q = []
for r in R:
    exp = r["args"].get("name") or SC.get(r["tool"]) or ("Liste Courses" if (r["tool"] or "").startswith(("HassList", "get_items")) else None)
    if exp: Q.append((r["text"], exp.replace("\x27", "’").lower()))
def key(n): return n.replace("\x27", "’").lower()
names = [key(d["name"]) for d in docs]
for model in sys.argv[1:]:
    t = time.time(); m = SentenceTransformer(model, device="cpu", trust_remote_code=True); lt = time.time() - t
    qp = "query: " if "e5" in model else ""; dp = "passage: " if "e5" in model else ""
    de = m.encode([dp + d["text"] for d in docs], normalize_embeddings=True)
    t = time.time(); qe = m.encode([qp + q for q, _ in Q], normalize_embeddings=True, batch_size=1); per = (time.time() - t) / len(Q)
    S = qe @ de.T; hits = {1: 0, 3: 0, 5: 0}
    for i, (_, exp) in enumerate(Q):
        order = np.argsort(-S[i])
        for k in hits:
            if any(names[j] == exp or exp in names[j] or names[j] in exp for j in order[:k]): hits[k] += 1
    print("%-40s hit@1 %.0f%% | hit@3 %.0f%% | hit@5 %.0f%% | %.0f ms/requete (CPU 8 coeurs) | %d requetes" % (model, *(100 * hits[k] / len(Q) for k in (1, 3, 5)), per * 1000, len(Q)), flush=True)
