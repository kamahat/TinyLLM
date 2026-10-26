# 04 — Résultats

Matériel : Intel Core i3-6100T (4 threads, AVX2), ~7 Go de RAM, **sans GPU** ; Ollama 0.40.x, GGUF Q4_K_M ; Whisper et Piper via le protocole Wyoming. Les CSV bruts sont dans [`../../results/`](../../results/). Les phrases du banc LLM sont dans [`../../data/benchmark_fr_92.json`](../../data/benchmark_fr_92.json) (noms d'appareils génériques dans la copie publiée ; les chiffres ci-dessous viennent de l'original, aux noms privés).

> **Lire d'abord les limites** ([06](06-lecons-et-limites.md)) : une seule machine, le français uniquement, un banc de petite taille et de la **parole synthétique** pour la reconnaissance vocale.

## 1. Reconnaissance vocale (Whisper, faster-whisper, int8, CPU)

92 ordres parlés synthétisés avec Piper (propre), et le même audio avec un bruit blanc ajouté à 15 dB de rapport signal/bruit. `WER` = taux d'erreur de mots ; latence = temps entre la fin de la parole et la transcription.

| Configuration Whisper | WER, audio propre | Phrases exactes (sur 92) | WER, audio bruité (15 dB) | Phrases exactes (sur 92) | Latence après la fin de la parole | Facteur temps réel |
|---|---|---|---|---|---|---|
| tiny-int8 + prompt de vocabulaire | 31,2 % | 26 | 45,4 % | 11 | 0,68 s | 0,38 |
| base-int8 + prompt de vocabulaire | 16,0 % | 41 | 24,4 % | 26 | 1,41 s | 0,79 |
| **small-int8 + prompt de vocabulaire (production)** | 6,5 % | 68 | 11,5 % | 57 | 3,04 s | 1,71 |
| small-int8, sans prompt | 9,6 % | 59 | 13,5 % | 49 | 3,12 s | 1,75 |

**Constats**
- **Whisper `small` est la seule taille utilisable** pour des commandes : 6,5 % de WER sur audio propre contre 16 % (`base`) et 31 % (`tiny`). Un mot mal entendu fait en général échouer la commande.
- Le **prompt de vocabulaire** (une phrase de mots du domaine : « Maison connectée. Allume, éteins, ferme, ouvre. Volets, lumière, salon… ») fait passer le WER de `small` de 9,6 % à 6,5 % (propre) et de 13,5 % à 11,5 % (bruité), et les phrases exactes de 59 à 68 sur 92. Il ne coûte rien.
- **La vitesse est le prix** : `small` met **~3 s** pour une phrase de ~1,8 s (facteur temps réel 1,7). C'est le **plus gros coût fixe** de toute la chaîne sur ce CPU. `tiny` et `base` répondent en 0,7 s et 1,4 s mais ne sont pas assez précis.
- Un bruit à 15 dB multiplie le WER par 1,4 à 1,8 pour toutes les tailles ; le classement relatif ne change pas.

## 2. Synthèse vocale (Piper, `fr_FR-siwis-medium`)

| Texte | n | Audio produit | Premier son | Synthèse totale | Facteur temps réel |
|---|---|---|---|---|---|
| Phrases d'ordre | 92 | 1,8 s | 0,18 s (max 0,34 s) | 0,19 s | 0,11 |
| Réponses de l'assistant | 10 | 2,7 s | 0,27 s (max 0,55 s) | 0,29 s | 0,11 |

La synthèse est l'étape la moins chère : une réponse est prête en **moins de 0,6 s**. Les autres voix et modèles de TTS n'ont **pas été mesurés**.

## 3. LLM : du modèle brut au modèle de production

Banc français, premier appel d'outil (92 phrases), prompts de 2 500 tokens :

| Étape | Résultat | Ordres sans appel d'outil | Latence moyenne | Tokens de prompt |
|---|---|---|---|---|
| Qwen3-1.7B d origine (Q4_K_M) | 17/92 (18 %) | 72/76 | 5,8 s | 2540 |
| v1 LoRA, prompt complet | 88/92 (96 %) | 0/76 | 7,2 s | 2537 |
| v1 LoRA + RAG dans le message utilisateur (31 phrases) | 26/31 (84 %) | 0/25 | 7,5 s | 1896 |
| v1, requête exacte du framework | 86/92 (93 %) | 2/76 | 6,9 s | 2528 |
| v2, requête exacte du framework | 87/92 (95 %) | 2/76 | 7,1 s | 2528 |

L'affinage fait passer un modèle de 1,7 Md de paramètres de **18 % à 96 %**. « Requête exacte du framework » est la vraie requête capturée dans Home Assistant (le banc précédent utilisait une approximation et flattait le modèle).

### Modèles et formats de prompt comparés

Banc au prompt de la tablette (46 phrases ; avec historique = tours précédents rejoués ; adverses = capteurs indisponibles et appareils inexistants ; fausse confirmation = le modèle dit « fait » alors que l'outil a renvoyé une erreur) :

| Modèle / format | Sans historique | Avec historique | Ordres sans appel (historique) | Adverses | Fausses confirmations après erreur | Latence moyenne | Taille du fichier |
|---|---|---|---|---|---|---|---|
| Qwen3-1.7B v2 (prompt du framework, ~3 000 tokens) | 43/46 (93 %) | 36/46 (78 %) | 7/38 | 6/6 (100 %) | n/a (boucles : 0) | 7,1 s | 1,1 Go |
| Qwen3-1.7B v3 (prompt du framework, ~3 000 tokens) | 43/46 (93 %) | 39/46 (85 %) | 2/38 | 6/6 (100 %) | n/a (boucles : 0) | 7,8 s | 1,1 Go |
| Qwen3-1.7B v4c (compact, ~1 330 tokens) | 44/46 (96 %) | 42/46 (91 %) | 1/38 | 6/6 (100 %) | 0/33 | 5,0 s | 1,1 Go |
| CroissantLLM 1,3B v4c (tokenisation HF, INVALIDE) | 17/46 (37 %) | 17/46 (37 %) | 0/38 | 0/6 (0 %) | 0/30 | 5,0 s | 0,87 Go |
| CroissantLLM 1,3B v4d (tokenisation llama.cpp) | 42/46 (91 %) | 39/46 (85 %) | 1/38 | 6/6 (100 %) | 0/34 | 4,9 s | 0,87 Go |
| **Qwen3-1.7B v5 (compact + web) — en production** | 43/46 (93 %) | 44/46 (96 %) | 1/38 | 6/6 (100 %) | 0/33 | 4,8 s | 1,1 Go |
| Qwen3-0.6B v5 (compact + web) | 43/46 (93 %) | 42/46 (91 %) | 1/38 | 6/6 (100 %) | 0/33 | 2,9 s | 0,40 Go |

**Constats**
- Le **prompt compact + proxy** est le gain principal : le même Qwen3-1.7B passe de 93 %/85 % (prompt du framework, v3) à **96 %/91 %** (v4c), avec un prompt 2,3 fois plus petit et une réponse plus rapide (5,0 s au lieu de 7,8 s).
- La **v5** ajoute la recherche web sans dégrader les ordres (**96 % avec historique**) ; elle a été retenue pour la production.
- **CroissantLLM 1,3B** est un honorable second (91 %/85 %), plus léger (0,87 Go), mais derrière Qwen3 ; sa première version était **invalide à cause d'un écart de tokenisation** (37 %).
- **Qwen3-0.6B** égale le 1,7B sur le choix de l'outil sans historique (93 %) et est **~40 % plus rapide** (2,9 s contre 4,8 s), mais perd 5 points avec historique. Voir ci-dessous.

### Qwen3-0.6B contre Qwen3-1.7B (même recette, v5)

| Mesure | Qwen3-1.7B v5 | Qwen3-0.6B v5 |
|---|---|---|
| Appel d'outil correct, sans / avec historique | 93 % / 96 % | 93 % / 91 % |
| Adverses, erreur forcée | 6/6, 32/34 | 6/6, 32/34 |
| Phrases pièges ayant déclenché un appel d'outil | 0/5 | 1/5 (un appareil inexistant : le framework a renvoyé une erreur) |
| **Refus à tort après un ordre réussi** (avant garde-fou) | 2/35 (sans historique), 5/36 (historique) | **22/36**, **21/35** |
| … corrigés par le garde-fou `guard_success` | 2/2 et 3/5 | 21/22 et 21/21 |
| Génération d'un ordre | 4,8 s | **2,9 s** |
| Question web (deux générations + recherche) | 16,5 s | **9,0 s** |
| Réponses web, requêtes réelles | 15/22 | 10/22 |
| Taille du fichier / mémoire chargée | 1,1 Go / 1,6 Go | 0,4 Go / 0,9 Go |

Le 0,6B choisit le bon outil mais **formule mal la confirmation** (il dit « appareil introuvable » après un succès dans 61 % des ordres) ; seul un garde-fou déterministe le masque. C'est un **choix viable si la latence prime**, pas le choix par défaut.

## 4. Recherche web (Qwen3-1.7B v5, SearXNG local)

| Modèle, réglage des extraits | Routage | Faux déclenchements | Justesse : météo / trajet / horaires | Requêtes réelles | Latence |
|---|---|---|---|---|---|
| **1,7B, 4 résultats x 230 caractères (production)** | 105/105 | 0/10 général, 0/8 maison | 38/38, 22/22, 19/23 | 15/22 | 16,5 s |
| 1,7B, 3 résultats x 170 caractères | 105/105 | 0/10, 0/8 | 29/38, 19/22, 15/23 | 13/22 | 13,7 s |
| 0,6B, 4 x 230 | 105/105 | 0/10, 0/8 | 38/38, 22/22, 19/23 | 10/22 | 9,0 s |

Des extraits plus courts vont plus vite mais sont nettement moins justes : non retenu. Un chiffre absent des extraits n'est **jamais** énoncé : une version initiale répondait « 3 100 km » pour une paire de villes (les extraits n'avaient pas de distance) puis « 31 000 km » (un code postal lu comme une distance) ; le garde-fou `grounded` répond désormais « Je n'ai pas trouvé de réponse fiable. »

## 5. Budget de latence de bout en bout (cache chaud)

| Chemin | STT (small) | LLM | TTS | Total |
|---|---|---|---|---|
| Phrase simple traitée par les intentions locales intégrées | ~3,0 s | 0 (pas de LLM, ~0,1 s) | ~0,2 s | **~3,3 s** |
| Ordre domotique via le LLM | ~3,0 s | ~4,8 s au premier appel, +1 à 2 s au second tour (estimation) | ~0,2 s | **~9–10 s** |
| Question répondue depuis le web | ~3,0 s | 16,5–23 s | ~0,3 s | **~20–26 s** |
| Première requête après un redémarrage (cache froid) | | + ~33–35 s | | ajouter ~35 s ; préchauffer après chaque redémarrage |

Le prompt natif du framework (3 000 tokens) prenait **63 à 70 s** à traiter à froid, ce qui a d'abord fait croire que l'assistant était « mort » avant le prompt compact et le préchauffage.
