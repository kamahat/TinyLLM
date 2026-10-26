# 07 — Le reproduire

Guide condensé. Les chemins et noms d'hôtes sont des paramètres fictifs : les scripts utilisent `/opt/tinyllm` et `*.example.lan` ; adaptez-les (ou renseignez les variables correspondantes) à votre installation.

## 1. Services sur l'hôte d'inférence

1. **Ollama** (`OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_NUM_PARALLEL=1`). Un seul modèle reste chargé ; prévoyez assez de RAM.
2. **Whisper** avec le protocole Wyoming (`rhasspy/wyoming-whisper`) : `--model small-int8 --language fr --beam-size 1 --initial-prompt "<une phrase de mots de votre domaine>"`.
3. **Piper** avec le protocole Wyoming (`rhasspy/wyoming-piper`) : `--voice fr_FR-siwis-medium`.
4. **SearXNG** lié à `127.0.0.1`, sortie JSON activée, générez votre propre `secret_key` (`scripts/deploy/searxng.settings.yml`).
5. **Proxy compact** : `scripts/proxy/{compact_proxy.py,compactlib.py,websearch.py}` dans un petit conteneur, avec les variables d'environnement ci-dessous. Gardez toujours une copie du dossier d'application et du fichier compose précédents pour revenir en arrière.

Variables du proxy : `COMPACT_WEB` (0/1), `SEARX_URL`, `WEB_LOG`, `LOG_RETENTION_DAYS` (7), `WEB_N` (4), `WEB_CHARS` (230), `WEB_CACHE_TTL` (600), `WEB_CACHE_MAX` (100), `UPSTREAM`, `PROXY_LOG`.

## 2. Home Assistant

Ajoutez l'intégration Ollama pointant sur le **proxy** (pas sur Ollama), créez un agent de conversation avec le contrôle *Assist* seul, créez un pipeline (Whisper + Piper + cet agent) et exposez les appareils voulus. Réglez le mot d'activation dans l'application Companion.

## 3. Capturer d'abord la vraie requête

Utilisez le proxy de simulation (`compact_proxy.py --sim`) et un pipeline temporaire lié à l'identifiant d'appareil de votre tablette pour capturer le prompt et les outils *exacts* envoyés par le framework. Tout le reste (données d'entraînement, banc) est généré à partir de cette capture.

## 4. Entraîner (machine GPU, optionnel)

```bash
# données : make_train_v3.py -> make_v4c.py -> make_v5.py  (scripts/training/)
# entraînement : scripts/brain/session_v5.sh   (arrête le service GPU, LoRA r=32, convertit en GGUF Q4_K_M, relance le service)
# import sous un NOUVEAU nom, sans jamais écraser le modèle de production :
bash scripts/training/import_ollama.sh /chemin/vers/q4_k_m.gguf mon-modele-v5
```

## 5. Valider avant de brancher (rien n'est exécuté)

```bash
python3 scripts/bench/harness4.py --model mon-modele-v5 --kind qwen --every 2 --out results/none.json
python3 scripts/bench/harness4.py --model mon-modele-v5 --kind qwen --every 2 --hist mix --out results/hist.json
python3 scripts/bench/harness4.py --model mon-modele-v5 --kind qwen --adv --out results/adv.json
python3 scripts/bench/harness5_web.py mon-modele-v5         # routage et justesse du web
python3 scripts/stt_tts/bench_stt.py                         # modèles STT, audio propre et bruité
```

Ne basculez la production qu'après : pas de régression sur le banc, **zéro boucle**, **zéro fausse confirmation après une erreur d'outil**, tous les cas adverses réussis, aucun chiffre inventé. Puis préchauffez le cache (`scripts/bench/warmup_proxy.py`) et gardez l'ancien modèle et l'ancien proxy pour un retour arrière immédiat.

## 6. Quantifier autrement (optionnel)

```bash
# texte de calibration au format du proxy, puis matrice d'importance, puis modèle 2 bits
python3 scripts/training/make_calib.py
llama-imatrix -m f16.gguf -f calib.txt -o imatrix.dat -c 1536 -t 8 -ngl 0
llama-quantize --imatrix imatrix.dat f16.gguf q2_k_im.gguf Q2_K
llama-quantize f16.gguf q8_0.gguf Q8_0        # référence 8 bits
```

Importez chaque variante dans une **instance Ollama de test séparée** (autre port) et lancez `scripts/bench/quant_tests.sh MODELE ETIQUETTE`, pour ne jamais évincer le modèle de production.

## Règles à conserver

1. Un agent de développement **n'exécute jamais de vraies commandes** ; utilisez le proxy de simulation ou appelez directement le proxy en HTTP.
2. Les phrases de test sont prononcées par un humain.
3. Ne jamais publier de jetons, de secrets de moteur de recherche ni de journaux contenant des phrases prononcées.
