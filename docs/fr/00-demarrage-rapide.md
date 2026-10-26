# 00 — Démarrage rapide

Objectif : avoir **toute la chaîne vocale locale qui tourne en une trentaine de minutes**, puis décider d'aller plus loin ou non. Aucun GPU n'est nécessaire pour ce guide.

> **Soyez lucide sur l'étape 3.** Avec un modèle *brut* (sans affinage), l'assistant est facile à démarrer mais peu fiable : il a obtenu **18 %** sur notre banc domotique. C'est l'affinage ([étape 6](#6-le-rendre-fiable--entraîner-son-propre-modèle)) qui le fait fonctionner (**96 %**). Le démarrage rapide vous donne la tuyauterie ; l'entraînement vous donne la qualité.

## Ce qu'il vous faut

| | Minimum | Confortable |
|---|---|---|
| Machine | x86-64, 4 threads CPU, **6 Go de RAM**, 10 Go de disque | l'étude a utilisé un Intel i3-6100T, ~7 Go de RAM |
| Logiciel | Docker + Docker Compose | — |
| Home Assistant | une version récente avec les intégrations **Ollama** et **Wyoming** | + l'application Companion sur une tablette pour un mot d'activation |
| GPU | inutile pour faire tourner | un GPU de 12 Go pour entraîner son propre modèle (~1 h) |

## 1. Récupérer le code

```bash
git clone https://github.com/kamahat/TinyLLM.git
cd TinyLLM/quickstart
```

## 2. Démarrer les services

```bash
# un secret privé pour le moteur de recherche local
sed -i "s/CHANGE_ME/$(openssl rand -hex 32)/" searxng-settings.yml

# optionnel : la ville utilisée pour la météo, et le nom du modèle
export HOME_PLACE="Paris"        # défaut : Paris
export LLM_MODEL="qwen3:1.7b"    # défaut : qwen3:1.7b

docker compose up -d
docker compose ps
```

Cela démarre cinq conteneurs : **Ollama** (LLM), **Whisper** (reconnaissance vocale), **Piper** (synthèse vocale), **SearXNG** (recherche web privée) et le **proxy compact**. Le premier démarrage télécharge les modèles vocaux (quelques centaines de Mo).

| Service | Port | Qui lui parle |
|---|---|---|
| Proxy compact | `11436` | **Home Assistant** (c'est l'adresse à lui donner) |
| Ollama | `11434` | le proxy |
| Whisper | `10300` | Home Assistant (Wyoming) |
| Piper | `10200` | Home Assistant (Wyoming) |
| SearXNG | `127.0.0.1:8888` | le proxy uniquement |

## 3. Télécharger un modèle

```bash
docker compose exec ollama ollama pull qwen3:1.7b
curl -s http://localhost:11436/health        # -> {"ok": true, "web": true, "sim": false}
```

C'est un modèle **brut** : suffisant pour voir la chaîne fonctionner, pas assez bon pour lui confier vos lumières.

## 4. Connecter Home Assistant

1. **Paramètres → Appareils et services → Ajouter une intégration → Ollama.** URL : `http://<votre-machine>:11436` (le **proxy**, pas 11434). Laissez la clé API vide.
2. Ouvrez la nouvelle entrée Ollama → ajoutez un agent de conversation. Activez **Contrôler Home Assistant → Assist** uniquement. Ajoutez aux instructions : *« Réponds toujours en français, en une phrase courte. »*
3. **Ajouter une intégration → Wyoming Protocol**, deux fois : `<votre-machine>:10300` (Whisper) et `<votre-machine>:10200` (Piper).
4. **Paramètres → Assistants vocaux → Ajouter un assistant.** Langue français, agent de conversation = l'agent Ollama, reconnaissance vocale = Whisper, synthèse vocale = Piper. Gardez **Préférer le traitement local des commandes** activé : les phrases simples (« allume la lumière ») sont alors traitées en ~0,1 s sans LLM.
5. Exposez les appareils à contrôler (**Paramètres → Assistants vocaux → Exposer**).

## 5. L'essayer

Dans le chat Assist (écrit ou vocal), essayez :

- une commande qui n'est *pas* une phrase locale simple, par exemple *« Pourrais-tu éteindre toutes les lumières du salon ? »*
- une question sur le monde : *« Quelle est la météo demain ? »* (répondue via la recherche privée ; ~20 s sur un CPU)
- un piège : *« Allume le four »* si vous n'avez pas de four — l'assistant doit refuser, pas choisir un autre appareil.

La première requête après un démarrage prend ~35 s (cache froid) : voir le [dépannage](#dépannage). Les échecs du modèle brut sont attendus ; voir l'étape 6.

## 6. Le rendre fiable : entraîner son propre modèle

Les chiffres publiés viennent d'un Qwen3-1.7B **affiné par LoRA** sur des exemples synthétiques de *votre* liste d'appareils. Les poids affinés ne sont pas publiés (ils encodent les appareils d'une maison), mais la recette complète l'est : [03 — Méthodes](03-methodes.md) explique l'approche et [07 — Le reproduire](07-reproduire.md) donne les commandes (génération des données, un entraînement LoRA d'~1 h sur un GPU de 12 Go, export GGUF, import dans Ollama). Ensuite :

```bash
export LLM_MODEL="mon-modele-v5"     # le nom donné dans Ollama
docker compose up -d proxy
```

Validez **avant** de lui faire confiance : pas de régression sur le banc, zéro boucle, zéro fausse confirmation après une erreur ([07](07-reproduire.md#5-valider-avant-de-brancher-rien-nest-exécuté)).

## 7. Mesurer sa propre machine (optionnel)

Les scripts de l'étude sont dans `scripts/stt_tts/` (client Wyoming, générateur de corpus utilisant votre Piper, banc Whisper). Ce sont des **scripts de recherche** : ils utilisent des chemins absolus sous `/opt/tinyllm` et le banc lance des conteneurs temporaires par SSH ; modifiez les constantes en tête de fichier avant de les lancer (`PIPER_HOST`, `PIPER_PORT`, chemin des données). Comparez vos chiffres avec les [résultats](04-resultats.md) : sur notre machine de référence, Whisper `small` met ~3 s par phrase et Piper ~0,2 s.

## Dépannage

| Symptôme | Cause probable | Que faire |
|---|---|---|
| La première réponse met 30 à 60 s, puis c'est rapide | cache de prompt froid | normal après chaque redémarrage ; envoyer une requête pour préchauffer |
| « Pas de réponse » / délai dépassé aux premières phrases | idem, avec le prompt de 3 000 tokens du framework | pointer Home Assistant sur le **proxy** (11436), pas sur Ollama |
| L'assistant dit « appareil introuvable » pour un appareil que vous avez | non exposé à Assist, ou nom vide | l'exposer et lui donner un alias |
| Les questions web répondent « pas trouvé de réponse fiable » | les extraits ne contenaient aucun chiffre (voulu) | reformuler, ou accepter la réponse honnête |
| Les questions web répondent « impossible de consulter Internet » | SearXNG arrêté ou limité en débit | `docker compose logs searxng` ; attendre et réessayer |
| Il répond en anglais | instructions de l'agent | ajouter « Réponds toujours en français » à l'agent |
| Le modèle brut appelle un mauvais outil ou aucun | pas d'affinage | étape 6 |

## Plan du dépôt

| Chemin | Contenu |
|---|---|
| `quickstart/` | le fichier compose de ce guide et les réglages du moteur de recherche |
| `docs/en`, `docs/fr` | l'étude, en deux langues |
| `results/` | tableaux de résultats (CSV) : STT, TTS, LLM |
| `data/benchmark_fr_92.json` | les 92 phrases du banc en français (noms d'appareils génériques) |
| `scripts/proxy` | le proxy compact (`compact_proxy.py`, `compactlib.py`, `websearch.py`) |
| `scripts/training` | génération des données, entraînement LoRA, import GGUF, expérience RAG |
| `scripts/brain` | sessions de la machine GPU (arrêt du service GPU, entraînement, conversion, relance) |
| `scripts/bench` | bancs LLM, vérifications en simulation, préchauffage |
| `scripts/stt_tts` | bancs Whisper et Piper (client Wyoming) |
| `scripts/ha` | utilitaires Home Assistant (agent, pipeline, capture de prompt) |
| `scripts/deploy` | fichiers compose utilisés en production |

Les commentaires des scripts sont surtout en français ; noms d'hôtes, chemins et noms d'appareils sont des valeurs fictives anonymisées (`*.example.lan`, `/opt/tinyllm`) : adaptez-les.
