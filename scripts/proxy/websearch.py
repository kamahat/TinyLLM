"""Recherche web pour Jarvis (SearXNG local), anonymisation de la requete, journal a retention courte."""
import collections, json, os, re, threading, time, unicodedata, urllib.parse, urllib.request
NL = chr(10)
SEARX = os.environ.get("SEARX_URL", "http://127.0.0.1:8888")
WEBLOG = os.environ.get("WEB_LOG", "/opt/tinyllm/logs/web_queries.jsonl")
RETENTION_DAYS = float(os.environ.get("LOG_RETENTION_DAYS", "7"))
def _norm(x):
    x = unicodedata.normalize("NFD", x.lower()); return "".join(c for c in x if unicodedata.category(c) != "Mn")
def private_tokens(ents):
    """mots appartenant aux noms d appareils, alias et zones de la maison : ils ne doivent jamais partir sur Internet"""
    t = set()
    for e in ents:
        if e.get("domain") == "weather": continue          # la ville et le mot meteo sont publics et necessaires
        for part in [e["name"]] + list(e.get("aliases", [])) + [e.get("areas", "")]:
            t |= {w for w in re.findall(r"[a-z0-9]+", _norm(part)) if len(w) > 2}
    return t - {"les", "des", "est", "une", "pour", "dans", "sur", "avec", "temperature", "tous", "toutes", "meteo", "prevision", "france", "liste", "courses", "mode", "actif", "exterieur", "exterieurs"}
def sanitize(query, ents):
    priv = private_tokens(ents); keep = [w for w in re.findall(r"[^\s]+", query) if _norm(re.sub(r"[^\w]", "", w)) not in priv]
    return " ".join(keep).strip()
def purge(path, days=RETENTION_DAYS):
    try:
        if not os.path.exists(path): return
        cut = time.time() - days * 86400; keep = []
        for l in open(path):
            try:
                if json.loads(l).get("ts", time.time()) >= cut: keep.append(l)
            except Exception: pass
        open(path, "w").write("".join(keep))
    except Exception: pass
def log_query(rec):
    rec["ts"] = time.time(); open(WEBLOG, "a").write(json.dumps(rec, ensure_ascii=False) + NL)
_CACHE = collections.OrderedDict(); _CLOCK = threading.Lock()
CACHE_TTL = float(os.environ.get("WEB_CACHE_TTL", "600")); CACHE_MAX = int(os.environ.get("WEB_CACHE_MAX", "100"))
def search(query, n=int(os.environ.get("WEB_N", "4")), timeout=8):
    """Cache MEMOIRE uniquement (TTL court, LRU, jamais ecrit sur disque, perdu au redemarrage) devant SearXNG ; les erreurs et resultats vides ne sont pas gardes."""
    key = (re.sub(r"\s+", " ", query.lower().strip()), n); now = time.time()
    with _CLOCK:
        hit = _CACHE.get(key)
        if hit and now - hit[0] < CACHE_TTL: _CACHE.move_to_end(key); return [dict(x) for x in hit[1]]
    out = _search(query, n, timeout)
    if out and CACHE_TTL > 0:
        with _CLOCK:
            _CACHE[key] = (now, [dict(x) for x in out]); _CACHE.move_to_end(key)
            while len(_CACHE) > CACHE_MAX: _CACHE.popitem(last=False)
    return out
def _search(query, n, timeout):
    url = SEARX + "/search?" + urllib.parse.urlencode({"q": query, "format": "json", "language": "fr"})
    r = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "jarvis-proxy"}), timeout=timeout).read())
    out = []
    for x in r.get("results", []):
        c = re.sub(r"\s+", " ", (x.get("content") or "")).strip()
        if len(c) < 30: continue
        out.append({"titre": re.sub(r"\s+", " ", x.get("title") or "")[:90], "extrait": c[:int(os.environ.get("WEB_CHARS", "230"))], "site": urllib.parse.urlparse(x.get("url") or "").netloc.replace("www.", "")})
        if len(out) >= n: break
    return out
def format_results(query, res):
    if not res: return "Aucun résultat trouvé."
    res = [dict(x, extrait=x["extrait"][:int(os.environ.get("WEB_CHARS", "230"))]) for x in res[:int(os.environ.get("WEB_N", "4"))]]
    return ("Résultats web pour « " + query + " » :" + NL + NL.join("%d. %s : %s [%s]" % (i + 1, x["titre"], x["extrait"], x["site"]) for i, x in enumerate(res)))

UNITS = [(r"(?<=\d)\s*(?:kilom[eè]tres?|km)\b", "~km"), (r"(?<=\d)\s*(?:°\s*[cC]?|degr[eé]s?)", "~deg"), (r"(?<=\d)\s*(?:heures?|h)\b", "~h"),
         (r"(?<=\d)\s*(?:minutes?|min)\b", "~min"), (r"(?<=\d)\s*(?:%|pour cent)", "~pct"), (r"(?<=\d)\s*(?:€|euros?)", "~eur"), (r"(?<=\d)\s*mm\b", "~mm")]
def _canon(t):
    t = re.sub(r"(?<=\d)[\s\u202f\u00a0.](?=\d{3}\b)", "", t)
    for pat, rep in UNITS: t = re.sub(pat, rep, t, flags=re.I)
    return t
def grounded(answer, results_text):
    """Chaque nombre de la reponse (avec son unite : km, degres, h, min, %, euros) doit figurer tel quel dans les extraits web : sinon le modele l a invente ou l a confondu (code postal pris pour une distance)."""
    src = _canon(results_text)
    for n, u in re.findall(r"(\d+(?:[.,]\d+)?)(~\w+)?", _canon(answer or "")):
        if not any(re.search(r"(?<![\d.,])" + re.escape(v + u) + r"(?![\d])", src) for v in {n, n.replace(",", "."), n.replace(".", ",")}): return False
    return True
