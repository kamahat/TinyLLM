# 04 — Résultats

Matériel : Intel Core i3-6100T (4 threads, AVX2), ~7 Go de RAM, **sans GPU** ; Ollama 0.40.x, GGUF Q4_K_M ; Whisper et Piper via le protocole Wyoming. Les CSV bruts sont dans [`../../results/`](../../results/). Les phrases du banc LLM sont dans [`../../data/benchmark_fr_92.json`](../../data/benchmark_fr_92.json) (noms d'appareils génériques dans la copie publiée ; les chiffres ci-dessous viennent de l'original, aux noms privés).

> **Lire d'abord les limites** ([06](06-lecons-et-limites.md)) : une seule machine, le français uniquement, un banc de petite taille et de la **parole synthétique** pour la reconnaissance vocale.

## 1. Reconnaissance vocale (Whisper, et deux moteurs alternatifs)

92 ordres parlés synthétisés avec Piper (propre) et le même audio avec un bruit blanc ajouté à 15 dB de rapport signal/bruit. `WER` = taux d'erreur de mots. Latence = temps entre la fin de la parole et la transcription (le moteur en streaming reçoit l'audio à la cadence du temps réel, comme depuis un micro). La dernière colonne rejoue 46 phrases du banc dans le LLM de production en utilisant le texte **transcrit** au lieu du texte exact (référence avec le texte exact : 43/46, 93 %).

| Moteur STT | WER, audio propre | WER, audio bruité (15 dB) | Latence après la fin de la parole | Facteur temps réel | Commandes correctes de bout en bout, propre / bruité |
|---|---|---|---|---|---|
| Whisper tiny-int8 + prompt de vocabulaire | 31,2 % | 45,4 % | 0,68 s | 0,38 | 35/46 (76 %) / – |
| Whisper base-int8 + prompt de vocabulaire | 16,0 % | 24,4 % | 1,41 s | 0,79 | 40/46 (87 %) / – |
| **Whisper small-int8 + prompt de vocabulaire (production)** | 6,5 % | 11,5 % | 3,04 s | 1,71 | 44/46 (96 %) / 43/46 (93 %) |
| Whisper small-int8, sans prompt | 9,6 % | 13,5 % | 3,12 s | 1,75 | – / – |
| Parakeet TDT 0,6B v3, int8 (sherpa-onnx) | 9,2 % | 9,0 % | 0,39 s | 0,22 | 42/46 (91 %) / 42/46 (91 %) |
| **Zipformer FR en streaming, Kroko (sherpa-onnx)** | 11,7 % | 12,3 % | 0,12 s | 0,07 | 43/46 (93 %) / 43/46 (93 %) |

**Constats**
- **La latence de Whisper est un coût fixe.** Elle reste autour de 3 s (écart-type 0,1 s) quelle que soit la durée de la phrase (0,9 à 2,8 s), parce que faster-whisper complète chaque phrase à une **fenêtre de 30 secondes** avant l'encodage. Sur ce CPU, `small` met donc ~3 s même pour une commande d'un mot. Les plus petits modèles Whisper sont plus rapides mais pas assez précis (31 % et 16 % de WER).
- **Les moteurs dont le coût suit la durée de l'audio sont bien plus rapides.** Parakeet TDT 0,6B v3 répond en **0,39 s** ; un modèle **en streaming** (Zipformer Kroko, français, seulement 68 Mo) répond **0,12 s après la fin de la parole**, car il transcrit *pendant* que vous parlez.
- **Le taux d'erreur de mots est plus élevé, mais les commandes passent.** Le WER passe de 6,5 % (Whisper small + prompt) à 9,2 % et 11,7 %, pourtant la part de *commandes* correctes reste à une à trois phrases de Whisper small (91–93 % contre 93–96 % ; des écarts de cette taille relèvent du bruit sur 46 phrases). Le LLM a été entraîné avec du bruit de transcription et Home Assistant associe les noms d'appareils de façon souple.
- **Moins sensible au bruit** : Parakeet (9,2 → 9,0 %) et le modèle en streaming (11,7 → 12,3 %) bougent à peine à 15 dB, alors que Whisper small passe de 6,5 à 11,5 %.
- Le **prompt de vocabulaire** aide Whisper `small` (WER 9,6 → 6,5 %, phrases exactes 59 → 68 sur 92) et ne coûte rien ; les moteurs alternatifs n'ont pas d'équivalent.
- **Réserve : c'est de la parole synthétique.** De vrais micros, accents et pièces peuvent pénaliser les nouveaux moteurs plus que Whisper, entraîné sur une énorme quantité de parole réelle. Un **test A/B en direct avec de vraies voix** est la suite indispensable avant de remplacer Whisper.

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
| **Avec le moteur STT en streaming au lieu de Whisper small** | ~0,1 s | inchangé | inchangé | phrase simple **~0,4 s**, commande **~6–7 s**, web **~17–23 s** |

Le prompt natif du framework (3 000 tokens) prenait **63 à 70 s** à traiter à froid, ce qui a d'abord fait croire que l'assistant était « mort » avant le prompt compact et le préchauffage.
