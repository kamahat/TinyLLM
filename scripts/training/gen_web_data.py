#!/usr/bin/env python3
"""Fabrique les exemples « recherche web » : vraie recherche SearXNG (tunnel ssh vers la VM docker) + reponse d or redigee par le Qwen3-8B de Brain (vLLM).
Prerequis : VM brain demarree, vLLM actif. La cle API est lue sur Brain a la volee et n est JAMAIS affichee."""
import json, os, re, subprocess, sys, time, urllib.request, random
os.environ["WEB_LOG"] = "/opt/tinyllm/logs/web_gen_queries.jsonl"; os.environ["SEARX_URL"] = "http://127.0.0.1:18888"
sys.path.insert(0, "/opt/tinyllm/compact")
import websearch as W
D = "/opt/tinyllm/data/"; random.seed(5)
Q = json.load(open(D + os.environ.get("IN", "web_queries.json"))); NL = chr(10)
tun = subprocess.Popen(["ssh", "-N", "-o", "ExitOnForwardFailure=yes", "-L", "18888:127.0.0.1:8888", "localhost"]); time.sleep(3)
key = subprocess.run(["ssh", "brain.example.lan", "grep ^VLLM_API_KEY /etc/vllm/vllm.env | cut -d= -f2-"], capture_output=True, text=True).stdout.strip().strip(chr(34))
SYS = ("Tu es un assistant vocal. Reponds en francais en UNE phrase courte (25 mots maximum), uniquement a partir des extraits web fournis. Donne les chiffres utiles (temperatures, scores, prix, horaires). "
       "Si les extraits ne permettent pas de repondre, reponds exactement : Je n ai pas trouve de reponse fiable. Pas de liste, pas de markdown, pas de source.")
def ask(question, results_text):
    body = {"model": "Qwen/Qwen3-8B-AWQ", "messages": [{"role": "system", "content": SYS}, {"role": "user", "content": "Question : " + question + NL + NL + results_text}], "temperature": 0.2, "max_tokens": 90, "chat_template_kwargs": {"enable_thinking": False}}
    r = urllib.request.Request("http://brain.example.lan:8000/v1/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    return json.loads(urllib.request.urlopen(r, timeout=120).read())["choices"][0]["message"]["content"].strip()
out = []; skipped = 0
try:
    for it in Q:
        try:
            res = W.search(it["query"], n=4, timeout=10)
            if len(res) < 2: skipped += 1; continue
            txt = W.format_results(it["query"], res); ans = ask(it["phrase"], txt)
            ans = re.sub(r"[*_#`]+", "", ans).replace(chr(10), " ").strip()
            if not ans or len(ans) > 220: skipped += 1; continue
            out.append({**it, "results_text": txt, "answer": ans}); print(it["id"], it["phrase"][:46], "->", ans[:90], flush=True)
        except Exception as e: skipped += 1; print(it["id"], "ERREUR", repr(e)[:70], flush=True)
        time.sleep(float(os.environ.get("SLEEP", "1.5")))
finally:
    tun.terminate()
json.dump(out, open(D + os.environ.get("OUT", "web_gold.json"), "w"), ensure_ascii=False, indent=1); print(len(out), "exemples ;", skipped, "ecartes")
