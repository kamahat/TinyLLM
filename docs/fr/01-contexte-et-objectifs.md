# 01 — Contexte et objectifs

## La question

Peut-on faire tourner ensemble, **localement et sans cloud, un modèle de reconnaissance vocale (speech-to-text, STT), un grand modèle de langage (LLM) et un modèle de synthèse vocale (text-to-speech, TTS) sur une petite machine bon marché** — et obtenir un résultat assez bon pour piloter une maison connectée à la voix ?

« Petite » signifie ici un mini-PC **Intel Core i3-6100T (2 cœurs / 4 threads, AVX2), environ 7 Go de RAM et aucun GPU**. « Sans cloud » signifie que l'audio, le texte et les commandes ne quittent jamais la maison : ni API vocale hébergée, ni LLM hébergé, ni voix hébergée.

Le cas d'usage est [Home Assistant](https://www.home-assistant.io/) *Assist* : une tablette murale écoute le mot d'activation « hey Jarvis », la phrase est transcrite, un petit LLM choisit quel **outil** de Home Assistant appeler (allumer une lampe, fermer un volet, lancer un script, lire un capteur), Home Assistant l'exécute et une voix synthétique confirme. L'assistant doit aussi répondre à quelques questions sur le monde extérieur : une recherche web privée a donc été ajoutée.

## Pourquoi c'est difficile sur un petit matériel

| Contrainte | Conséquence |
|---|---|
| Pas de GPU, 4 threads CPU | Le traitement du prompt tourne à environ **46 tokens/s** et la génération à environ **8 tokens/s** pour un modèle de 1,7 Md de paramètres (Q4_K_M). Un prompt de 3 000 tokens prend plus d'une minute à froid |
| ~7 Go de RAM partagés entre STT, TTS, LLM et le système | Un seul LLM reste chargé ; petits modèles seulement |
| Les petits LLM sont mauvais en appel d'outils | Un modèle de 1,7 Md de paramètres brut obtient **18 %** sur un banc domotique en français : il écrit le nom de l'outil en texte au lieu de l'appeler |
| Le framework domotique envoie un **long prompt** (25 outils, ~3 000 tokens) | La latence est dominée par la *lecture* du prompt, pas par la génération de la réponse |
| Un assistant vocal agit sur le monde physique | Un mauvais appel d'outil a des conséquences réelles : les échecs doivent être sûrs, pas seulement rares |

## Ce que contient cette étude

- L'**architecture** d'une chaîne complète, fonctionnelle et 100 % locale (STT + LLM + TTS + recherche web privée) — [02](02-architecture.md).
- Les **techniques comparées** : un petit LLM brut, l'**affinage LoRA**, le **RAG** (récupération des appareils pertinents), un **prompt compact** avec garde-fous déterministes, et un outil de **recherche web** privé — [03](03-methodes.md).
- Les **modèles comparés** — Qwen3-1.7B (cinq itérations d'entraînement), Qwen3-0.6B et CroissantLLM 1,3B pour le LLM ; Whisper tiny, base et small pour le STT ; Piper pour le TTS — avec un banc en français et des latences mesurées — [04](04-resultats.md).
- Les **avantages et inconvénients** de l'approche locale et de chaque technique — [05](05-avantages-et-inconvenients.md).
- Les **leçons, incidents et limites** — [06](06-lecons-et-limites.md) — et un **guide de reproduction** condensé — [07](07-reproduire.md).

## Ce qui n'a *pas* été fait

Dit d'emblée pour que les résultats ne soient pas sur-interprétés : le modèle Qwen3-4B et les autres niveaux de quantification (Q1–Q3) n'ont **pas été mesurés** ; les modèles vocaux ont été évalués sur de la **parole synthétique** (pas de vrais enregistrements au micro) ; toutes les phrases du banc sont en **français** et les chiffres proviennent d'**une seule machine et d'une seule maison**. Voir [06](06-lecons-et-limites.md).
