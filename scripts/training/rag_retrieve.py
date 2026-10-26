"""Pre-calcule, pour chaque phrase de la recette, les k entites les plus proches (e5). Sortie : data/rag_topk.json"""
import json, sys, numpy as np
from sentence_transformers import SentenceTransformer
D = "/var/lib/tinyllm/data/"
docs = json.load(open(D + "knowledge_pack.json")); R = json.load(open(D + "recette.json"))
m = SentenceTransformer("intfloat/multilingual-e5-base", device="cpu")
de = m.encode(["passage: " + d["text"] for d in docs], normalize_embeddings=True)
qe = m.encode(["query: " + r["text"] for r in R], normalize_embeddings=True)
S = qe @ de.T; out = {}
for i, r in enumerate(R): out[r["text"]] = [docs[j]["id"] for j in np.argsort(-S[i])[:8]]
json.dump(out, open(D + "rag_topk.json", "w"), ensure_ascii=False)
print(len(out), "requetes indexees")
