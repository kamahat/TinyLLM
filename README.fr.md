# TinyLLM — un assistant vocal 100 % local sur une petite machine sans GPU

**Petits LLM pour piloter Home Assistant à la voix — reconnaissance vocale, LLM et synthèse vocale, tout en local (sans cloud) sur un mini-PC sans GPU.**

🇬🇧 English version: [README.md](README.md) · [docs/en](docs/en/)

## Contexte

Peut-on faire tourner ensemble, **localement et sans cloud, un modèle de reconnaissance vocale, un grand modèle de langage et un modèle de synthèse vocale sur une petite machine** — et obtenir un résultat assez bon pour piloter une maison connectée à la voix ? Ce dépôt documente une réponse fonctionnelle et la mesure :

- **Matériel** : Intel Core i3-6100T (4 threads, AVX2), ~7 Go de RAM, **sans GPU**. Une machine GPU séparée (RTX 5070) sert à l'entraînement uniquement.
- **Chaîne** : mot d'activation sur une tablette Android → **Whisper** (STT) → **Qwen3 affiné par LoRA** servi par **Ollama**, derrière un **proxy compact** → Home Assistant exécute l'outil → **Piper** (TTS). Une **recherche web** privée (SearXNG) répond aux questions sur le monde extérieur.
- **Comparé** : LLM brut, **LoRA**, **RAG**, prompt compact + garde-fous ; Qwen3-1.7B / Qwen3-0.6B / CroissantLLM 1,3B ; Whisper tiny / base / small ; Piper.

## Résultats principaux (banc en français, CPU seul)

| Étape | Choix | Résultat |
|---|---|---|
| **LLM** | Qwen3-1.7B brut | **18 %** — écrit les noms d'outils en texte au lieu de les appeler |
| | + affinage LoRA | **96 %** au premier appel d'outil |
| | + prompt compact, proxy et garde-fous (v5, en production) | **93 % / 96 %** sans / avec historique, 0 fausse confirmation après erreur, ~5 s par commande |
| | Qwen3-0.6B (même recette) | mêmes 93 % sans historique, **~40 % plus rapide** (2,9 s), mais confirmations fragiles |
| | CroissantLLM 1,3B | 91 % / 85 %, plus léger, derrière Qwen3 |
| **STT** | Whisper `small` + prompt de vocabulaire | **6,5 % de WER** (propre), 11,5 % (bruité), ~3 s par phrase |
| | Whisper `base` / `tiny` | 16 % / 31 % de WER, 1,4 s / 0,7 s |
| **TTS** | Piper `fr_FR-siwis-medium` | une réponse en **~0,2 à 0,3 s** (facteur temps réel 0,11) |
| **RAG** | récupération `multilingual-e5-base` | bonne récupération (94 % hit@1) mais **moins bon de bout en bout** et il casse le cache de prompt — non retenu sous ~100 appareils |
| **Bout en bout** | | intentions locales ~3 s · commande via LLM ~9–10 s · question web ~20–26 s |

> Les modèles vocaux ont été testés sur de la **parole synthétique**, le banc est petit et en français uniquement, et les chiffres viennent d'une seule machine. Lisez les [limites](docs/fr/06-lecons-et-limites.md) avant de conclure.

## Lire l'étude

| | English | Français |
|---|---|---|
| Contexte et objectifs | [docs/en/01](docs/en/01-context-and-goals.md) | [docs/fr/01](docs/fr/01-contexte-et-objectifs.md) |
| Architecture et schémas | [docs/en/02](docs/en/02-architecture.md) | [docs/fr/02](docs/fr/02-architecture.md) |
| Méthodes : LoRA, RAG, proxy compact, recherche web | [docs/en/03](docs/en/03-methods.md) | [docs/fr/03](docs/fr/03-methodes.md) |
| **Résultats** (STT, LLM, TTS, web, latence) | [docs/en/04](docs/en/04-results.md) | [docs/fr/04](docs/fr/04-resultats.md) |
| **Avantages et inconvénients** | [docs/en/05](docs/en/05-pros-and-cons.md) | [docs/fr/05](docs/fr/05-avantages-et-inconvenients.md) |
| Leçons, incidents, limites | [docs/en/06](docs/en/06-lessons-and-limits.md) | [docs/fr/06](docs/fr/06-lecons-et-limites.md) |
| Le reproduire | [docs/en/07](docs/en/07-reproduce.md) | [docs/fr/07](docs/fr/07-reproduire.md) |

## Organisation du dépôt

| Chemin | Contenu |
|---|---|
| `docs/en`, `docs/fr` | l'étude, en deux langues |
| `results/` | tableaux de résultats en CSV : `stt_whisper.csv`, `tts_piper.csv`, `llm_models.csv`, `llm_stages.csv` |
| `data/benchmark_fr_92.json` | les 92 phrases du banc en français (noms d'appareils génériques) |
| `scripts/proxy` | le proxy compact (`compact_proxy.py`, `compactlib.py`, `websearch.py`) |
| `scripts/training` | génération des données, entraînement LoRA, import GGUF, expérience RAG |
| `scripts/brain` | sessions de la machine GPU (arrêt du service GPU, entraînement, conversion, relance) |
| `scripts/bench` | bancs LLM, vérifications en simulation, préchauffage |
| `scripts/stt_tts` | bancs Whisper et Piper (client Wyoming) |
| `scripts/ha` | utilitaires Home Assistant (agent, pipeline, capture de prompt) |
| `scripts/deploy` | fichiers compose du proxy et de SearXNG |

Les commentaires et docstrings des scripts sont surtout en français. Les noms d'hôtes, chemins et noms d'appareils ont été anonymisés (`*.example.lan`, `/opt/tinyllm`, noms d'appareils génériques) : adaptez-les à votre installation. Les sorties brutes des bancs ne sont pas publiées (elles contiennent des noms d'appareils privés) ; les tableaux le sont.

## Principes de sécurité tenus tout au long

- **Aucun test avec exécution réelle** par un agent de développement : un proxy de simulation retire tous les appels d'outils.
- **La production ne dépend jamais de la machine GPU**, qui peut rester éteinte.
- Les requêtes web sont **anonymisées**, journalisées 7 jours, avec un cache **en mémoire** uniquement.
- Aucun secret dans ce dépôt.

## Licence

Apache-2.0 — voir [LICENSE](LICENSE).
