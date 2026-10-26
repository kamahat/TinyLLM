"""Test unitaire de la boucle web du proxy avec un faux modele et un faux moteur de recherche : aucune requete reelle, aucun appareil."""
import os, sys, json
os.environ["COMPACT_WEB"] = "1"; os.environ["WEB_LOG"] = "/tmp/_web_test.jsonl"
sys.path.insert(0, "/opt/tinyllm/compact"); sys.argv = ["x"]
import compact_proxy as P, websearch as W
R = json.load(open("/opt/tinyllm/data/ha_tablet_prompt.json")); NLC = chr(10)
req = lambda q, hist=(): {"model": "m", "stream": False, "tools": R["tools"], "messages": [{"role": "system", "content": R["system"]}, *hist, {"role": "user", "content": q}]}
calls_seen = []
W.search = lambda q, n=4, timeout=8: (calls_seen.append(q), [{"titre": "Meteo Montpellier", "extrait": "Demain : ciel nuageux, 16 degres, risque de pluie 40 pour cent en fin de journee.", "site": "meteo.example"}])[1]
def fake(out): 
    seq = iter(out); return lambda prompt: {"response": next(seq), "eval_count": 5, "prompt_eval_count": 1300}
tc = lambda n, a: "<tool_call>" + NLC + json.dumps({"name": n, "arguments": a}) + NLC + "</tool_call>"
msg, notes, info = P.handle_chat(req("Quelle meteo demain a Montpellier ?"), fake([tc("recherche_web", {"query": "meteo demain Montpellier salon"}), "Demain, ciel nuageux, 16 degres."]))
print("1 recherche normale :", msg["content"], "| tool_calls:", "tool_calls" in msg, "| requete envoyee :", calls_seen[-1], "|", notes)
msg, notes, info = P.handle_chat(req("Eteins le salon"), fake([tc("intent__HassTurnOff", {"name": "Lumière Salon"})]))
print("2 ordre HA inchange :", "tool_calls" in msg and msg["tool_calls"][0]["function"]["name"], "|", notes)
msg, notes, info = P.handle_chat(req("quoi de neuf"), fake([tc("recherche_web", {"query": "salon"}), "x"]))
print("3 requete vide apres anonymisation :", msg["content"], "|", notes)
msg, notes, info = P.handle_chat(req("actualites"), fake([tc("recherche_web", {"query": "actualites du jour"}), tc("recherche_web", {"query": "encore"})]))
print("4 le modele reboucle apres la recherche :", msg["content"], "|", notes)
W.search = lambda q, n=4, timeout=8: (_ for _ in ()).throw(RuntimeError("moteur hors ligne"))
msg, notes, info = P.handle_chat(req("actualites"), fake([tc("recherche_web", {"query": "actualites du jour"})]))
print("5 moteur de recherche hors ligne :", msg["content"], "|", notes)
msg, notes, info = P.handle_chat(req("x"), fake([tc("recherche_web", {"query": "a b c"}), "ok"]))
print("6 appel inconnu :", [l for l in open("/tmp/_web_test.jsonl")][-1][:140].strip())
