#!/usr/bin/env python3
"""Banc WEB : coeur du proxy (handle_chat) + faux moteur de recherche (extraits de l exemple) + Ollama brut. Mesure routage, justesse des reponses, faux declenchements. Aucun acces Internet reel, aucun ordre HA. Usage : harness5_web.py MODELE"""
import os, sys, json, time, urllib.request, collections, statistics
os.environ["COMPACT_WEB"] = "1"; os.environ["WEB_LOG"] = "/tmp/_h5_web.jsonl"
sys.path.insert(0, "/opt/tinyllm/compact"); model = sys.argv[1]; sys.argv = ["x", "--kind", "qwen"]
import compact_proxy as P, websearch as W
D = "/opt/tinyllm/data/"; R = json.load(open(D + "ha_tablet_prompt.json"))
def gen(prompt):
    body = {"model": model, "prompt": prompt, "raw": True, "stream": False, "keep_alive": -1, "options": {"temperature": 0, "num_predict": 160, "num_ctx": 4096, "stop": ["<|im_end|>"]}}
    return json.loads(urllib.request.urlopen(urllib.request.Request("http://localhost:11434/api/generate", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}), timeout=900).read())
CUR = {}
def fake_search(q, n=4, timeout=8):
    CUR["q"] = q; return [{"titre": t, "extrait": e, "site": s} for (t, e, s) in CUR["res"]]
W.search = fake_search
import re
def parse_results(txt):
    out = []
    for l in txt.split(chr(10))[1:]:
        m = re.match(r"\d+\. (.*?) : (.*) \[(.*)\]$", l)
        if m: out.append((m.group(1), m.group(2), m.group(3)))
    return out
def run(phrase, results):
    CUR["res"] = results; CUR.pop("q", None); t = time.time()
    msg, notes, info = P.handle_chat({"model": model, "stream": False, "tools": R["tools"], "messages": [{"role": "system", "content": R["system"]}, {"role": "user", "content": phrase}]}, gen)
    return msg, notes, info, time.time() - t
web = [x for x in json.load(open(D + "web_synth.json")) if x["split"] == "eval"]
real = [g for f in ("web_gold.json", "web_gold2.json") for g in json.load(open(D + f)) if g["split"] == "eval" and "pas trouv" not in g["answer"].lower()]
STATIC = ["Quelle est la capitale de l Italie ?", "Combien font sept fois huit ?", "Raconte-moi une blague courte", "Qui a écrit Les Misérables ?", "Quelle est la plus haute montagne du monde ?", "Qui a peint la Joconde ?", "Combien y a-t-il de jours dans une année ?", "Donne-moi une idée de dessert rapide",
          "Quelle est la capitale de l Espagne ?", "Quel est le plus grand océan ?"]
HA = ["Allume la lumière du salon", "Ferme les volets du salon", "Quelle est la température de la douche ?", "Y a-t-il quelqu un à la maison ?", "Quelle heure est-il ?", "Éteins la clim du salon", "Ajoute du lait à la liste de courses", "Lance le cinéma"]
stats = collections.defaultdict(list); lat = []; rows = []
for x in web[::2]:        # un exemple synthetique sur deux (duree)
    msg, notes, info, dt = run(x["phrase"], parse_results(x["results_text"])); routed = info["web"] is not None; a = msg["content"]
    ok = routed and ((not x["expect"] and "pas trouv" in a.lower()) or (x["expect"] and all(e.lower() in a.lower() for e in x["expect"]))); stats["web_" + x["cat"]].append((routed, ok)); lat.append(dt)
    rows.append((x["cat"], x["phrase"], routed, ok, a[:70]))
for g in real:
    msg, notes, info, dt = run(g["phrase"], parse_results(g["results_text"])); routed = info["web"] is not None; stats["reel"].append((routed, routed and "pas trouv" not in msg["content"].lower())); rows.append(("reel", g["phrase"], routed, routed, msg["content"][:70]))
for nm, lst in (("statique", STATIC), ("maison", HA)):
    for ph in lst:
        CUR["res"] = [("x", "x" * 40, "x")]; msg, notes, info, dt = run(ph, [("x", "x" * 40, "x")]); stats[nm].append((info["web"] is not None, False)); rows.append((nm, ph, info["web"] is not None, False, (msg["content"] or str(info["calls"]))[:50]))
print("== " + model + " : banc WEB ==")
for k in sorted(stats):
    v = stats[k]
    if k in ("statique", "maison"): print("  %-14s : recherches declenchees a tort : %d/%d" % (k, sum(r for r, _ in v), len(v)))
    else: print("  %-14s : routage %d/%d | reponse correcte %d/%d" % (k, sum(r for r, _ in v), len(v), sum(o for _, o in v), len(v)))
print("latence moyenne (2 generations) : %.1f s" % statistics.mean(lat))
for r in rows:
    if (r[0] in ("statique", "maison") and r[2]) or (r[0] not in ("statique", "maison") and not r[3]): print("  KO", r[0], "|", r[1][:48], "| route:", r[2], "|", r[4])
