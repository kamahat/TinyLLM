"""Format COMPACT pour Jarvis : prompt systeme, outils et resultats d outils reduits ; rendu ChatML ; analyse de la sortie.
Partage par le proxy compact, l entrainement et le banc de test (un seul code = zero ecart)."""
import json, re, os
NL = chr(10)
WEB = os.environ.get("COMPACT_WEB", "0") == "1"
HOME_PLACE = os.environ.get("HOME_PLACE", "Montpellier")
DESC = {"intent__HassTurnOn": "Allume, ouvre ou active un appareil ou une zone.", "intent__HassTurnOff": "Eteint, ferme ou desactive un appareil ou une zone.",
        "intent__HassSetPosition": "Regle la position (0-100) d un volet ou store.", "intent__HassStopMoving": "Arrete un volet ou store en mouvement.",
        "light__HassLightSet": "Regle la luminosite d une lumiere.", "climate__HassClimateSetTemperature": "Regle la temperature de la climatisation.",
        "homeassistant__GetLiveContext": "Lit l etat actuel des appareils.", "llm__GetDateTime": "Donne la date et l heure.",
        "todo__get_items": "Lit une liste de taches.", "todo__HassListAddItem": "Ajoute un element a une liste.",
        "todo__HassListCompleteItem": "Coche un element d une liste.", "todo__HassListRemoveItem": "Retire un element d une liste."}
ALLOWED = ("name", "area", "domain", "position", "brightness", "temperature", "item")
def compact_tools(tools):
    out = []
    for t in tools:
        f = t["function"]; n = f["name"]
        if n in DESC: d = DESC[n]
        elif n.startswith("script__"):
            m = re.search(r"Aliases: \[(.*)\]", f.get("description") or ""); d = ("Script : " + m.group(1).strip("\x27\" ")) if m else "Script."
        else: continue
        p = f.get("parameters") or {}; props = {k: v for k, v in (p.get("properties") or {}).items() if k in ALLOWED}
        for k, v in list(props.items()):
            props[k] = {"type": "array", "items": {"type": "string"}} if v.get("type") == "array" else {"type": v.get("type", "string")}
        par = {"type": "object"}
        req = [r for r in (p.get("required") or []) if r in props]
        if req: par["required"] = req
        par["properties"] = props
        out.append({"type": "function", "function": {"name": n, "description": d, "parameters": par}})
    if WEB: out.append({"type": "function", "function": {"name": "recherche_web", "description": "Cherche sur Internet une information recente ou exterieure a la maison.", "parameters": {"type": "object", "required": ["query"], "properties": {"query": {"type": "string"}}}}})
    return out
def parse_ha_system(s):
    ctx = s.split("Static Context: An overview of the areas and the devices in this smart home:" + NL, 1)[-1]
    ctx = ctx.split(NL + NL + "When controlling Home Assistant", 1)[0]; ents = []
    for b in re.split(r"(?m)^(?=- names:)", ctx):
        m = re.search(r"- names: (.*)", b)
        if not m or m.group(1).strip() in ("\x27\x27", ""): continue
        names = [x.strip() for x in m.group(1).split(", ")]; d = re.search(r"domain: (\S+)", b); a = re.search(r"areas: (.*)", b)
        ents.append({"name": names[0], "aliases": names[1:], "domain": d.group(1) if d else "", "areas": a.group(1) if a else ""})
    return ents
def compact_system(ents):
    t = ("Tu es Jarvis, l assistant vocal de la maison. Réponds en français, en une phrase courte. Pour agir sur un appareil ou lire son état, appelle un outil ; "
         "ne dis jamais avoir agi sans appel d outil. Si la demande est ambiguë, demande la pièce. " + (("Lieu de la maison : " + HOME_PLACE + ". Pour une information récente ou extérieure à la maison (météo, actualités, sport, horaires, prix), appelle recherche_web ; pour une connaissance générale, réponds directement. ") if WEB else "") + "Appareils (nom | type | zone) :" + NL)
    for e in ents: t += e["name"] + "".join(" ~ " + a for a in e["aliases"]) + " | " + e["domain"] + (" | " + e["areas"] if e["areas"] else "") + NL
    return t.rstrip(NL)
def compact_live(text):
    out = []
    for b in re.split(r"(?m)^(?=- names:)", text):
        m = re.search(r"- names: (.*)", b)
        if not m or m.group(1).strip() in ("\x27\x27", ""): continue
        st = re.search(r"state: \x27?(.*?)\x27?$", b, re.M); a = re.search(r"areas: (.*)", b)
        val = st.group(1) if st else "?"
        if val in ("unavailable", "unknown"): val = os.environ.get("COMPACT_UNAVAIL", "indisponible (aucune valeur récente)")
        out.append("- " + m.group(1).split(", ")[0] + ": " + val + ((" (" + a.group(1) + ")") if a else ""))
    return "Etat actuel :" + NL + NL.join(out)
def compact_result(res):
    """res : dict (ou chaine JSON) renvoye par un outil HA -> chaine courte"""
    if isinstance(res, str):
        try: res = json.loads(res)
        except Exception: return res
    if isinstance(res, dict):
        if "result" in res and isinstance(res["result"], str) and res["result"].startswith("Live Context"): return compact_live(res["result"])
        if "response_type" in res:
            tg = [x.get("name") for x in (res.get("data") or {}).get("success", []) if x.get("name")]
            return json.dumps({"ok": res["response_type"] == "action_done", "cibles": tg}, ensure_ascii=False, separators=(",", ":"))
    return json.dumps(res, ensure_ascii=False, separators=(",", ":"))
TOOLHEAD = ("# Tools" + NL + NL + "You may call one or more functions to assist with the user query." + NL + NL + "You are provided with function signatures within <tools></tools> XML tags:" + NL + "<tools>" + NL)
TOOLTAIL = (NL + "</tools>" + NL + NL + "For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:" + NL + "<tool_call>" + NL +
            "{" + chr(34) + "name" + chr(34) + ": <function-name>, " + chr(34) + "arguments" + chr(34) + ": <args-json-object>}" + NL + "</tool_call>")
def call_text(name, args): return "<tool_call>" + NL + json.dumps({"name": name, "arguments": args}, ensure_ascii=False) + NL + "</tool_call>"
STOP_TOKEN = {"qwen": "<|im_end|>", "croissant": "<|im_end|>", "gemma": "<end_of_turn>"}
def stop_token(kind): return STOP_TOKEN.get(kind, "<|im_end|>")
def render_gemma(messages, tools, gen=True):
    """Format Gemma 3 : pas de role systeme ni outil -> le systeme et les outils sont fusionnes dans le PREMIER tour utilisateur (prefixe stable = cache), les resultats d outils sont un tour utilisateur
    <tool_response>, les appels d outil du modele restent <tool_call>. Pas de BOS dans le texte : il est ajoute par le tokeniseur / llama.cpp."""
    sysm = messages[0]["content"]
    if tools: sysm += NL + NL + TOOLHEAD + NL.join(json.dumps(t, ensure_ascii=False, separators=(",", ":")) for t in tools) + TOOLTAIL
    o = ""; first = True; E = "<end_of_turn>" + NL
    for m in messages[1:]:
        r = m["role"]
        if r == "user":
            o += "<start_of_turn>user" + NL + ((sysm + NL + NL) if first else "") + m["content"] + E; first = False
        else:
            if first: o += "<start_of_turn>user" + NL + sysm + E; first = False
            if r == "assistant":
                body = NL.join(call_text(c["function"]["name"], c["function"]["arguments"]) for c in m.get("tool_calls") or [])
                o += "<start_of_turn>model" + NL + (m.get("content") or "") + ((NL if m.get("content") else "") + body if body else "") + E
            elif r == "tool": o += "<start_of_turn>user" + NL + "<tool_response>" + NL + m["content"] + NL + "</tool_response>" + E
    if first: o += "<start_of_turn>user" + NL + sysm + E
    if gen: o += "<start_of_turn>model" + NL
    return o
def render(messages, tools, gen=True, kind="qwen"):
    """messages : [{role: system|user|assistant|tool, content, tool_calls?}] ; tools : liste compacte ou None"""
    if kind == "gemma": return render_gemma(messages, tools, gen)
    sysm = messages[0]["content"]; o = "<|im_start|>system" + NL + sysm
    if tools: o += NL + NL + TOOLHEAD + NL.join(json.dumps(t, ensure_ascii=False, separators=(",", ":")) for t in tools) + TOOLTAIL
    o += "<|im_end|>" + NL
    for m in messages[1:]:
        r = m["role"]
        if r == "user": o += "<|im_start|>user" + NL + m["content"] + "<|im_end|>" + NL
        elif r == "assistant":
            body = NL.join(call_text(c["function"]["name"], c["function"]["arguments"]) for c in m.get("tool_calls") or [])
            o += "<|im_start|>assistant" + NL + (m.get("content") or "") + ((NL if m.get("content") else "") + body if body else "") + "<|im_end|>" + NL
        elif r == "tool": o += "<|im_start|>user" + NL + "<tool_response>" + NL + m["content"] + NL + "</tool_response><|im_end|>" + NL
    if gen: o += "<|im_start|>assistant" + NL + (("<think>" + NL + NL + "</think>" + NL + NL) if kind == "qwen" else "")
    return o
def parse_output(text):
    calls = []; head = text.split("<tool_call>", 1)[0].strip()
    for m in re.finditer(r"<tool_call>\s*(.*?)\s*</tool_call>", text, re.S):
        try:
            d = json.loads(m.group(1)); calls.append({"function": {"name": d["name"], "arguments": d.get("arguments") or {}}})
        except Exception: return "Je n ai pas compris cette commande.", [], True
    if "<tool_call>" in text and not calls: return "Je n ai pas compris cette commande.", [], True
    return head, calls, False
def transform(ha_messages, ha_tools, max_rounds=2):
    """requete HA (messages + outils) -> (messages compacts, outils compacts, round2). Les outils restent TOUJOURS dans le prompt (cache d Ollama conserve) ; round2=True : le proxy rejette tout nouvel appel."""
    ents = parse_ha_system(ha_messages[0]["content"]); msgs = [{"role": "system", "content": compact_system(ents)}]; rest = ha_messages[1:]
    users = [i for i, m in enumerate(rest) if m["role"] == "user"]
    if len(users) > max_rounds: rest = rest[users[-max_rounds]:]
    lu = max(k for k, m in enumerate(rest) if m["role"] == "user")
    rest = [m for k, m in enumerate(rest) if not (k < lu and (m["role"] == "tool" or m.get("tool_calls")))]   # historique : texte seul (garde le cache court)
    for m in rest:
        if m["role"] == "tool": msgs.append({"role": "tool", "content": compact_result(m["content"])})
        else: msgs.append({"role": m["role"], "content": m.get("content") or "", **({"tool_calls": m["tool_calls"]} if m.get("tool_calls") else {})})
    last_user = max(i for i, m in enumerate(msgs) if m["role"] == "user")
    round2 = any(m["role"] == "tool" for m in msgs[last_user:])
    return msgs, compact_tools(ha_tools), round2

import unicodedata
STOP = {"de", "la", "le", "les", "du", "des", "une", "est", "quelle", "quel", "quels", "quelles", "temperature", "valeur", "etat", "combien", "fait", "dans", "sur", "mon", "ton", "ma", "eau"}
def _toks(x):
    x = unicodedata.normalize("NFD", x.lower()); x = "".join(c for c in x if unicodedata.category(c) != "Mn")
    return {w for w in re.findall(r"[a-z0-9]+", x) if len(w) > 2 and w not in STOP}
def guard_unavailable(msgs, text):
    """Si la reponse contient un chiffre alors que l appareil vise par la question est INDISPONIBLE (resultat d outil), on remplace par un message honnete."""
    if not re.search(r"\d", text or ""): return text
    tools = [m["content"] for m in msgs if m["role"] == "tool"]
    if not tools: return text
    unav = re.findall(r"(?m)^- (.*?): indisponible", tools[-1])
    if not unav: return text
    qraw = [m["content"] for m in msgs if m["role"] == "user"][-1].lower(); q = _toks(qraw); best = None
    want_value = bool(re.search(r"temp|degr|combien|humid|niveau|mesure|valeur", qraw))
    for line in msgs[0]["content"].split(chr(10)):
        parts = line.split(" | "); names = parts[0].split(" ~ ")
        if want_value and len(parts) > 1 and parts[1] not in ("sensor", "weather", "binary_sensor", "climate", "number"): continue
        if names and names[0] in unav:
            for n in names:
                ov = len(_toks(n) & q)
                if ov and (best is None or ov > best[0] or (ov == best[0] and not re.search(r"\d", n) and re.search(r"\d", best[1]))): best = (ov, n)
    if not best: return text
    return "Je n ai pas de valeur récente pour " + best[1][0].lower() + best[1][1:] + " : le capteur est indisponible."
REFUS_RE = re.compile(r"(pas trouv|ne trouve pas|ne connais pas|pas pu|introuvable|désolé)", re.I)
def guard_success(msgs, text):
    """L outil HA a repondu SUCCES mais le modele annonce un refus : on remplace par une confirmation honnete."""
    tools = [m for m in msgs if m["role"] == "tool"]
    if not tools or not REFUS_RE.search(text or ""): return text
    try: r = json.loads(tools[-1]["content"])
    except Exception: return text
    if isinstance(r, dict) and (r.get("ok") is True or (r.get("success") is True and "result" not in r)): return "C est fait."
    return text

# ---- confirmation directe (pas de 2e appel LLM apres un ordre reussi) ---------------------------------
FAST_CONFIRM = os.environ.get("FAST_CONFIRM", "0") == "1"
FAST_PHRASE = os.environ.get("FAST_CONFIRM_PHRASE", "C est fait.")
ACTION_TOOLS = {"intent__HassTurnOn", "intent__HassTurnOff", "intent__HassSetPosition", "intent__HassStopMoving", "light__HassLightSet", "climate__HassClimateSetTemperature"}
def fast_confirm(ha_messages):
    """Messages HA bruts. Renvoie la phrase de confirmation si TOUS les appels du tour sont des outils d ACTION et que HA a repondu SUCCES complet
    (response_type action_done, aucune cible en echec, au moins une cible reussie) ; sinon None (le LLM redige la reponse : lecture de liste, erreur, script, etc.)."""
    if not FAST_CONFIRM: return None
    users = [i for i, m in enumerate(ha_messages) if m["role"] == "user"]
    if not users: return None
    seg = ha_messages[users[-1] + 1:]
    calls = [c for m in seg if m["role"] == "assistant" for c in (m.get("tool_calls") or [])]
    tools = [m for m in seg if m["role"] == "tool"]
    if not calls or len(calls) != len(tools): return None
    if any(c["function"]["name"] not in ACTION_TOOLS for c in calls): return None
    for t in tools:
        try: r = json.loads(t["content"]) if isinstance(t["content"], str) else t["content"]
        except Exception: return None
        if not isinstance(r, dict) or r.get("response_type") != "action_done": return None
        d = r.get("data") or {}
        if d.get("failed") or not d.get("success"): return None
    return FAST_PHRASE


# ---- corrections STT : mots ou groupes de mots souvent mal entendus -> forme correcte ----------------------
import unicodedata
STT_FIXES_ENV = os.environ.get("STT_FIXES", "")            # "mal entendu=correct;autre=correct2"
STT_FIXES_FILE = os.environ.get("STT_FIXES_FILE", "")      # JSON {"mal entendu": "correct"} : recharge a chaud (pas de redemarrage)
_FIX = {"mtime": "?", "rules": []}
def _tok_norm(w): return "".join(c for c in unicodedata.normalize("NFD", w.lower()) if unicodedata.category(c) != "Mn")
def _tokens(text): return [(m.start(), m.end(), _tok_norm(m.group())) for m in re.finditer(r"[^\W_]+", text)]
def _fix_rules():
    mt = os.path.getmtime(STT_FIXES_FILE) if STT_FIXES_FILE and os.path.exists(STT_FIXES_FILE) else None
    if _FIX["mtime"] == mt: return _FIX["rules"]          # rien n a change depuis la derniere lecture
    rules = {}
    for part in STT_FIXES_ENV.split(";"):
        if "=" in part: a, b = part.split("=", 1); rules[a.strip()] = b.strip()
    if mt is not None:
        try: rules.update({k: v for k, v in json.load(open(STT_FIXES_FILE, encoding="utf-8")).items() if not k.startswith("_")})
        except Exception: pass
    comp = []
    for k, v in rules.items():
        kt = tuple(t for _, _, t in _tokens(k))
        if kt and kt != tuple(t for _, _, t in _tokens(v)): comp.append((kt, v, k))
    comp.sort(key=lambda x: -len(x[0])); _FIX["mtime"] = mt; _FIX["rules"] = comp
    return comp
def apply_stt_fixes(text):
    """-> (texte corrige, notes). Insensible a la casse, aux accents et a la ponctuation ; le plus long motif gagne."""
    rules = _fix_rules()
    if not rules or not text: return text, []
    toks = _tokens(text); out = []; notes = []; i = 0; last = 0
    while i < len(toks):
        hit = next(((n, v, k) for kt, v, k in rules for n in [len(kt)] if tuple(t for _, _, t in toks[i:i + n]) == kt), None)
        if hit:
            n, v, k = hit; out.append(text[last:toks[i][0]]); out.append(v); last = toks[i + n - 1][1]; notes.append("correction STT : « %s » -> « %s »" % (text[toks[i][0]:last].strip(), v)); i += n
        else: i += 1
    out.append(text[last:])
    return "".join(out), notes
