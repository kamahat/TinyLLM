"""Meteo exacte via Open-Meteo (API publique gratuite, sans cle) pour les questions de meteo du proxy.
Le modele continue d appeler recherche_web (comme a l entrainement) : le proxy detourne les requetes de METEO vers cette API et repond par une phrase
deterministe en francais (valeurs exactes, ~0,5 s) au lieu d extraits de moteur de recherche sans chiffres. Echec ou lieu introuvable : retour None -> recherche web habituelle.
Confidentialite : pour la maison, seules des coordonnees ARRONDIES (2 decimales, ~1 km) sont envoyees ; pour une autre ville, son nom (geocodage). Aucune autre donnee."""
import json, os, re, time, unicodedata, urllib.parse, urllib.request, datetime, threading
from compactlib import HOME_PLACE
ENABLED = os.environ.get("METEO", "0") == "1"
HOME_LAT = os.environ.get("HOME_LAT", ""); HOME_LON = os.environ.get("HOME_LON", "")
COUNTRY = os.environ.get("WEATHER_COUNTRY", "FR")
TIMEOUT = float(os.environ.get("METEO_TIMEOUT", "5")); TTL = float(os.environ.get("METEO_CACHE_TTL", "600"))
_CACHE = {}; _LOCK = threading.Lock()
DAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
WMO = {0: "ciel dégagé", 1: "plutôt dégagé", 2: "partiellement nuageux", 3: "ciel couvert", 45: "brouillard", 48: "brouillard givrant", 51: "bruine légère", 53: "bruine", 55: "bruine forte",
       56: "bruine verglaçante", 57: "bruine verglaçante", 61: "pluie faible", 63: "pluie", 65: "forte pluie", 66: "pluie verglaçante", 67: "pluie verglaçante", 71: "faible neige", 73: "neige",
       75: "forte neige", 77: "grains de neige", 80: "averses", 81: "averses", 82: "fortes averses", 85: "averses de neige", 86: "fortes averses de neige", 95: "orage", 96: "orage avec grêle", 99: "orage avec grêle"}
def _n(t): return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn")).strip()
WEATHER_RE = re.compile(r"\b(meteo|pluie|pleuvoir|pleut|pleuvra|parapluie|averse|vent|neige|neiger|orage|soleil|ensoleille|temperature|degres|prevision|previsions|nuageux|brouillard|canicule|gelee|quel temps|temps fait)\b")
EXCLUDE_RE = re.compile(r"\b(trajet|distance|itineraire|duree|train|sncf|vol|avion|horaire|horaires|bus|tram|route|km|kilometres|embouteillage|trafic)\b")
def is_weather(text):
    n = _n(text); return bool(WEATHER_RE.search(n)) and not EXCLUDE_RE.search(n)
def parse_day(text, today_weekday):
    """-> (decalage en jours, libelle)"""
    n = _n(text)
    if "apres demain" in n: return 2, "Après-demain"
    if re.search(r"\bdemain\b", n): return 1, "Demain"
    if re.search(r"\b(aujourd hui|ce matin|cet apres midi|ce soir|cette nuit|maintenant|actuellement)\b", n): return 0, "Aujourd'hui"
    if "week end" in n: return (5 - today_weekday) % 7, "Ce week-end (samedi)"
    for i, d in enumerate(DAYS):
        if re.search(r"\b" + d + r"\b", n): return (i - today_weekday) % 7, d.capitalize()
    return 0, "Aujourd'hui"
STOP = set(("meteo la le les de du des d l a au aux en pour sur dans demain apres aujourd hui aujourdhui ce cet cette matin soir midi nuit week end semaine prochain prochaine prevision previsions pluie pleuvoir "
            "pleut pleuvra parapluie averse vent neige orage soleil temperature degres temps quel quelle quels quelles fait il va t y combien prevue prevues prevu heure heures jour actuellement maintenant "
            "est sera fera et ou sa ses mon ma mes ici chez moi jarvis dis").split()) | set(DAYS)
def parse_place(query):
    toks = []
    for w in re.findall(r"[^\W_]+", query or ""):
        if _n(w) not in STOP and not w.isdigit() and _n(w) not in [_n(t) for t in toks]: toks.append(w)
    return " ".join(toks)
def user_place(text):
    """Lieu nomme par l UTILISATEUR : mots a majuscule hors debut de phrase (les noms de villes). Sert a corriger un modele qui remplace le lieu demande par celui de la maison."""
    toks = re.findall(r"[^\W_]+", text or "")
    return " ".join(w for i, w in enumerate(toks) if i > 0 and w[0].isupper() and _n(w) not in STOP)
def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "jarvis-proxy"}), timeout=TIMEOUT) as r: return json.loads(r.read())
def geocode(name):
    key = ("geo", _n(name))
    with _LOCK:
        if key in _CACHE: return _CACHE[key]
    res = None
    for country in ([COUNTRY, ""] if COUNTRY else [""]):
        u = "https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode({"name": name, "count": 3, "language": "fr", "format": "json", **({"countryCode": country} if country else {})})
        r = (_get(u).get("results") or [])
        if r: res = (round(r[0]["latitude"], 2), round(r[0]["longitude"], 2), r[0]["name"]); break
    with _LOCK: _CACHE[key] = res
    return res
def forecast(lat, lon):
    key = ("fc", lat, lon)
    with _LOCK:
        c = _CACHE.get(key)
        if c and time.time() - c[0] < TTL: return c[1]
    u = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode({"latitude": lat, "longitude": lon, "timezone": "auto", "forecast_days": 8, "current": "temperature_2m,weather_code,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,wind_speed_10m_max"})
    d = _get(u)
    with _LOCK: _CACHE[key] = (time.time(), d)
    return d
def _r(x): return int(round(x))
def rain_phrase(pop, mm, detail=False):
    if pop is None: return None
    if pop < 10 and (mm or 0) < 0.5: return "pas de pluie prévue"
    if pop < 30: return "faible risque de pluie, %d %%" % pop
    if pop < 60: return "risque de pluie de %d %%" % pop
    return "pluie probable, %d %%" % pop + (", environ %d millimètres" % _r(mm) if detail and (mm or 0) >= 1 else "")
def answer(query, user_text=""):
    """-> (phrase, infos) ou None (desactive, lieu introuvable, jour hors de la periode, erreur reseau : le proxy retombe sur la recherche web)."""
    if not ENABLED or not is_weather(query) or EXCLUDE_RE.search(_n(user_text)): return None
    place = parse_place(query); strict = False; up = user_place(user_text)
    if up and _n(up) not in _n(place) and not (_n(HOME_PLACE) and _n(HOME_PLACE) in _n(up)): place = up; strict = True   # le lieu dit par l utilisateur prime sur celui de la requete du modele
    if not place or (_n(HOME_PLACE) and _n(HOME_PLACE) in _n(place)):   # lieu vide ou commune de la maison : coordonnees de la maison (evite l ambiguite des homonymes)
        if not (HOME_LAT and HOME_LON): return None
        lat, lon, name = round(float(HOME_LAT), 2), round(float(HOME_LON), 2), HOME_PLACE
    else:
        g = geocode(place)
        if not g and not strict and len(place.split()) > 1:   # lieu complet introuvable (mots parasites) : essayer les mots un par un, du dernier au premier
            for w in reversed(place.split()):
                if len(w) >= 3 and (g := geocode(w)): break
        if not g: return None
        lat, lon, name = g
    d = forecast(lat, lon); dl = d["daily"]; cur = d.get("current") or {}
    now_local = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=d.get("utc_offset_seconds", 0))
    off, label = parse_day(user_text + " " + query, now_local.weekday())
    if off >= len(dl["time"]): return None
    n = _n(user_text + " " + query)
    code = dl["weather_code"][off]; tmax, tmin = dl["temperature_2m_max"][off], dl["temperature_2m_min"][off]; pop = dl["precipitation_probability_max"][off]; mm = dl["precipitation_sum"][off]; wind = dl["wind_speed_10m_max"][off]
    cond = WMO.get(code, "temps variable")
    if (code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99)) and (pop or 0) < 30 and (mm or 0) < 1: cond = "ciel nuageux"   # code pluie mais probabilite et cumul quasi nuls : evite « pluie faible » puis « pas de pluie prévue »
    temp = "de %d à %d degrés" % (_r(tmin), _r(tmax))
    if re.search(r"\b(pluie|pleuvoir|pleut|pleuvra|parapluie|averse)\b", n): parts = [rain_phrase(pop, mm, True), cond, temp]
    elif re.search(r"\bvent\b", n): parts = ["vent jusqu'à %d kilomètres par heure" % _r(wind), cond, temp]
    else: parts = [cond, temp, rain_phrase(pop, mm)]
    if off == 0 and cur.get("temperature_2m") is not None: parts.insert(0, "il fait actuellement %d degrés" % _r(cur["temperature_2m"]))
    text = "%s à %s, %s." % (label, name, ", ".join(p for p in parts if p))
    return text, {"lieu": name, "lat": lat, "lon": lon, "decalage_jours": off, "api": "open-meteo"}
