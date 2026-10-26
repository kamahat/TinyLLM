# 04 — Résultats

Quantification : tous les LLM ci-dessous sont des GGUF quantifiés avec llama.cpp ; la colonne **Quantification** donne le format (Q4_K_M sauf mention contraire). Les modèles vocaux ont la précision indiquée dans leur propre tableau.

Matériel : Intel Core i3-6100T (4 threads, AVX2), ~7 Go de RAM, **sans GPU** ; Ollama 0.40.x, GGUF Q4_K_M ; Whisper et Piper via le protocole Wyoming. Les CSV bruts sont dans [`../../results/`](../../results/). Les phrases du banc LLM sont dans [`../../data/benchmark_fr_92.json`](../../data/benchmark_fr_92.json) (noms d'appareils génériques dans la copie publiée ; les chiffres ci-dessous viennent de l'original, aux noms privés).

> **Lire d'abord les limites** ([06](06-lecons-et-limites.md)) : une seule machine, le français uniquement, un banc de petite taille et de la **parole synthétique** pour la reconnaissance vocale.

## 1. Reconnaissance vocale (Whisper, et deux moteurs alternatifs)

92 ordres parlés synthétisés avec Piper (propre) et le même audio avec un bruit blanc ajouté à 15 dB de rapport signal/bruit. `WER` = taux d'erreur de mots. Latence = temps entre la fin de la parole et la transcription (le moteur en streaming reçoit l'audio à la cadence du temps réel, comme depuis un micro). La dernière colonne rejoue 46 phrases du banc dans le LLM de production en utilisant le texte **transcrit** au lieu du texte exact (référence avec le texte exact : 43/46, 93 %).

| Moteur STT | Quantification | WER, audio propre | WER, audio bruité (15 dB) | Latence après la fin de la parole | Facteur temps réel | Commandes correctes de bout en bout, propre / bruité |
|---|---|---|---|---|---|---|
| Whisper tiny-int8 + prompt de vocabulaire | int8 (CTranslate2) | 31,2 % | 45,4 % | 0,68 s | 0,38 | 35/46 (76 %) / – |
| Whisper base-int8 + prompt de vocabulaire | int8 (CTranslate2) | 16,0 % | 24,4 % | 1,41 s | 0,79 | 40/46 (87 %) / – |
| **Whisper small-int8 + prompt de vocabulaire (production)** | int8 (CTranslate2) | 6,5 % | 11,5 % | 3,04 s | 1,71 | 44/46 (96 %) / 43/46 (93 %) |
| Whisper small-int8, sans prompt | int8 (CTranslate2) | 9,6 % | 13,5 % | 3,12 s | 1,75 | – / – |
| Parakeet TDT 0,6B v3, int8 (sherpa-onnx) | int8 (ONNX) | 9,2 % | 9,0 % | 0,39 s | 0,22 | 42/46 (91 %) / 42/46 (91 %) |
| **Zipformer FR en streaming, Kroko (sherpa-onnx)** | non précisée (ONNX) | 11,7 % | 12,3 % | 0,12 s | 0,07 | 43/46 (93 %) / 43/46 (93 %) |

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

| Étape | Quantification | Résultat | Ordres sans appel d'outil | Latence moyenne | Tokens de prompt |
|---|---|---|---|---|---|
| Qwen3-1.7B d origine (Q4_K_M) | Q4_K_M | 17/92 (18 %) | 72/76 | 5,8 s | 2540 |
| v1 LoRA, prompt complet | Q4_K_M | 88/92 (96 %) | 0/76 | 7,2 s | 2537 |
| v1 LoRA + RAG dans le message utilisateur (31 phrases) | Q4_K_M | 26/31 (84 %) | 0/25 | 7,5 s | 1896 |
| v1, requête exacte du framework | Q4_K_M | 86/92 (93 %) | 2/76 | 6,9 s | 2528 |
| v2, requête exacte du framework | Q4_K_M | 87/92 (95 %) | 2/76 | 7,1 s | 2528 |

L'affinage fait passer un modèle de 1,7 Md de paramètres de **18 % à 96 %**. « Requête exacte du framework » est la vraie requête capturée dans Home Assistant (le banc précédent utilisait une approximation et flattait le modèle).

### Modèles et formats de prompt comparés

Banc au prompt de la tablette (46 phrases ; avec historique = tours précédents rejoués ; adverses = capteurs indisponibles et appareils inexistants ; fausse confirmation = le modèle dit « fait » alors que l'outil a renvoyé une erreur) :

| Modèle / format | Quantification | Sans historique | Avec historique | Ordres sans appel (historique) | Adverses | Fausses confirmations après erreur | Latence moyenne | Taille du fichier |
|---|---|---|---|---|---|---|---|---|
| Qwen3-1.7B v2 (prompt du framework, ~3 000 tokens) | Q4_K_M | 43/46 (93 %) | 36/46 (78 %) | 7/38 | 6/6 (100 %) | n/a (boucles : 0) | 7,1 s | 1,1 Go |
| Qwen3-1.7B v3 (prompt du framework, ~3 000 tokens) | Q4_K_M | 43/46 (93 %) | 39/46 (85 %) | 2/38 | 6/6 (100 %) | n/a (boucles : 0) | 7,8 s | 1,1 Go |
| Qwen3-1.7B v4c (compact, ~1 330 tokens) | Q4_K_M | 44/46 (96 %) | 42/46 (91 %) | 1/38 | 6/6 (100 %) | 0/33 | 5,0 s | 1,1 Go |
| CroissantLLM 1,3B v4c (tokenisation HF, INVALIDE) | Q4_K_M | 17/46 (37 %) | 17/46 (37 %) | 0/38 | 0/6 (0 %) | 0/30 | 5,0 s | 0,87 Go |
| CroissantLLM 1,3B v4d (tokenisation llama.cpp) | Q4_K_M | 42/46 (91 %) | 39/46 (85 %) | 1/38 | 6/6 (100 %) | 0/34 | 4,9 s | 0,87 Go |
| **Qwen3-1.7B v5 (compact + web) — en production** | Q4_K_M | 43/46 (93 %) | 44/46 (96 %) | 1/38 | 6/6 (100 %) | 0/33 | 4,8 s | 1,1 Go |
| Qwen3-0.6B v5 (compact + web) | Q4_K_M | 43/46 (93 %) | 42/46 (91 %) | 1/38 | 6/6 (100 %) | 0/33 | 2,9 s | 0,40 Go |
| Qwen3-1.7B v5 (compact + web) | Q2_K | 8/46 (17 %) | 9/46 (20 %) | 24/38 | 0/6 (0 %) | n/a (boucles : 0) | 6,1 s | 0,78 Go |
| Qwen3-1.7B v5 (compact + web) | Q2_K (imatrix) | 37/46 (80 %) | 31/46 (67 %) | 1/38 | 5/6 (83 %) | 0/33 | 4,5 s | 0,78 Go |
| Qwen3-0.6B v5 (compact + web) | Q8_0 | 43/46 (93 %) | 42/46 (91 %) | 1/38 | 6/6 (100 %) | 0/33 | 3,3 s | 0,64 Go |
| Qwen3-1.7B v5 (compact + web) | Q4_K_M (imatrix) | 45/46 (98 %) | 43/46 (93 %) | 1/38 | 6/6 (100 %) | 0/33 | 4,9 s | 1,1 Go |
| Qwen3-1.7B v5 (compact + web) | IQ4_XS (imatrix) | 44/46 (96 %) | 42/46 (91 %) | 1/38 | 6/6 (100 %) | 0/33 | 4,9 s | 1,0 Go |

**Constats**
- Le **prompt compact + proxy** est le gain principal : le même Qwen3-1.7B passe de 93 %/85 % (prompt du framework, v3) à **96 %/91 %** (v4c), avec un prompt 2,3 fois plus petit et une réponse plus rapide (5,0 s au lieu de 7,8 s).
- La **v5** ajoute la recherche web sans dégrader les ordres (**96 % avec historique**) ; elle a été retenue pour la production.
- **CroissantLLM 1,3B** est un honorable second (91 %/85 %), plus léger (0,87 Go), mais derrière Qwen3 ; sa première version était **invalide à cause d'un écart de tokenisation** (37 %).
- **Qwen3-0.6B** égale le 1,7B sur le choix de l'outil sans historique (93 %) et est **~40 % plus rapide** (2,9 s contre 4,8 s), mais perd 5 points avec historique. Voir ci-dessous.

### Qwen3-0.6B contre Qwen3-1.7B (même recette, v5)

| Mesure | Qwen3-1.7B v5 | Qwen3-0.6B v5 |
|---|---|---|
| **Quantification** | Q4_K_M | Q4_K_M |
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

| Modèle, réglage des extraits | Quantification | Routage | Faux déclenchements | Justesse : météo / trajet / horaires | Requêtes réelles | Latence |
|---|---|---|---|---|---|---|
| **1,7B, 4 résultats x 230 caractères (production)** | Q4_K_M | 105/105 | 0/10 général, 0/8 maison | 38/38, 22/22, 19/23 | 15/22 | 16,5 s |
| 1,7B, 3 résultats x 170 caractères | Q4_K_M | 105/105 | 0/10, 0/8 | 29/38, 19/22, 15/23 | 13/22 | 13,7 s |
| 0,6B, 4 x 230 | Q4_K_M | 105/105 | 0/10, 0/8 | 38/38, 22/22, 19/23 | 10/22 | 9,0 s |

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

## 6. Quantification : jusqu'où descendre (et monter) ?

Chaque modèle affiné a été exporté en GGUF f16 puis quantifié avec llama.cpp (`llama-quantize`), et passé dans les **mêmes bancs** que les versions Q4_K_M, sur une instance Ollama isolée de la même machine. Les variantes à 2 bits ont aussi été essayées **avec une matrice d'importance (imatrix)** : calibration sur 48 exemples rendus exactement comme le proxy les présente au modèle (24 premiers tours, 24 tours avec résultats d'outils ; 49 blocs de 1 536 tokens). Une seule exécution par variante : des écarts d'une ou deux phrases relèvent du bruit.

| Modèle | Quantification | Fichier | Commandes correctes, sans / avec historique | Phrases pièges ayant déclenché un appel d'outil, sans / avec historique (sur 5) | Génération d'une commande | Routage web / requêtes réelles | Latence web |
|---|---|---|---|---|---|---|---|
| Qwen3-1,7B v5 | **Q4_K_M (production)** | 1,1 Go | 93 % / 96 % | 0 / 0 | 4,8 s | 105/105 / 15/22 | 16,5 s |
| Qwen3-1,7B v5 | Q2_K | 0,78 Go | 17 % / 20 % | 0 / 0 (répond en texte) | 6,1 s | 0/105 | n/m |
| Qwen3-1,7B v5 | Q2_K + imatrix | 0,78 Go | 80 % / 67 % | 1 / 3 | 4,5 s | 105/105 / 15/22 | 16,0 s |
| Qwen3-0,6B v5 | Q4_K_M | 0,40 Go | 93 % / 91 % | 1 / 1 | 2,9 s | 105/105 / 10/22 | 9,0 s |
| Qwen3-0,6B v5 | Q8_0 | 0,64 Go | 93 % / 91 % | 1 / 1 | 3,3 s | 105/105 / 9/22 | 10,5 s |

**Constats**
- **Le 2 bits sans calibration casse le modèle** : 13 réponses sur 46 ont un format d'appel d'outil cassé, 0 commande sur 38 est correcte, et l'outil web n'est jamais appelé.
- **La matrice d'importance répare l'essentiel** (17 % → 80 %, plus aucun format cassé) sans entraînement supplémentaire, ce qui donne une **borne basse** utile. Mais on reste 13 à 29 points sous le Q4_K_M, et avec historique **3 pièges sur 5 déclenchent un appel d'outil** : pas sûr pour un assistant vocal qui agit sur la maison.
- **Plus petit n'est pas beaucoup plus rapide** : le fichier à 2 bits est 30 % plus léger, mais une commande prend 4,5 s au lieu de 4,8 s. Sur ce CPU, le traitement du prompt et la déquantification coûtent autant que la lecture des poids.
- **Le 8 bits n'apporte rien** : sur le 0,6B, le Q8_0 a la même justesse que le Q4_K_M (93 % / 91 %), un fichier 60 % plus gros et une génération ~14 % plus lente : une **borne haute** sans bénéfice.
- **Le 4 bits est le bon compromis** pour cette tâche (Q4_K_M, ou IQ4_XS : voir ci-dessous) : quasi sans perte, léger, rapide.
- **Non mesuré** : Q3_K_M, Q5_K_M, Q6_K (attendus entre les deux bornes), quantifications IQ1/IQ2/IQ3, un jeu de calibration plus grand, l'affinage conscient de la quantification.

### Formats 4 bits comparés : Q4_K_M, Q4_K_M + imatrix, IQ4_XS + imatrix

Mêmes poids f16 (Qwen3-1,7B v5). Les deux variantes « imatrix » utilisent **la même** matrice d'importance (48 exemples de calibration) : le tableau sépare donc l'effet de la **calibration** (Q4_K_M contre Q4_K_M + imatrix) de l'effet du **format** (Q4_K_M + imatrix contre IQ4_XS + imatrix). Justesse : banc de 46 phrases. Vitesse : micro-banc avec le vrai prompt de 1 500 tokens, cache de prompt désactivé à chaque essai, 12 essais en blocs alternés, médianes.

| Variante | Fichier | Commandes correctes, sans / avec historique | Erreur forcée | Pièges ayant déclenché un appel d'outil (sur 8) | Refus à tort après un succès (sans / avec historique) | Génération d'une commande | Web : requêtes réelles / latence | Traitement du prompt | Décodage |
|---|---|---|---|---|---|---|---|---|---|
| Q4_K_M (production) | 1 107 Mo | 93 % / 96 % | 32/34 | 0 | 2/35 · 5/36 | 4,8 s | 15/22 / 16,5 s | 44,9 tok/s | 6,9 tok/s |
| Q4_K_M + imatrix | 1 107 Mo | **98 %** / 93 % | 33/34 | 0 | 2/37 · 3/35 | 4,9 s | 15/22 / 16,9 s | non mesuré (mêmes types de tenseurs) | non mesuré |
| IQ4_XS + imatrix | **1 010 Mo** | 96 % / 91 % | 33/34 | 1 | **0/37 · 0/35** | 4,9 s | 16/22 / 16,3 s | **46,9 tok/s** | 7,1 tok/s |

**Constats**
- **Justesse : les trois variantes sont indiscernables** (93–98 % sans historique, 91–96 % avec) : l'écart est d'une à trois phrases sur 46, ce qui est du bruit pour une seule exécution.
- **La matrice d'importance n'a pas d'effet net à 4 bits** (+1 phrase sans historique, −1 avec). Elle compte beaucoup plus à 2 bits, où elle était décisive (17 % → 80 %).
- **L'IQ4_XS n'est pas plus lent sur ce CPU**, contrairement à ce qu'on attend d'ordinaire des quantifications à dictionnaire : **9 % plus léger**, traitement du prompt **+4 %**, décodage égal dans le bruit.
- **Une phrase piège** (« Éteins la télé du salon ») fait appeler un outil par l'IQ4_XS sur un appareil inexistant ; le framework répond par une erreur sans toucher d'autre appareil (même comportement que le 0,6B). Les deux variantes Q4_K_M ne le font pas.
- **Verdict** : l'IQ4_XS peut remplacer le Q4_K_M sans réserve : un peu plus léger et plus rapide, même justesse. Le gain est faible (environ 100 Mo et ~1,5 s sur un prompt froid de 1 500 tokens) : **cela ne justifie pas à lui seul de changer la production**.
