# 03 — Méthodes comparées

Le LLM est la partie difficile. Cinq approches ont été essayées, dans l'ordre ci-dessous ; chacune corrigeait ce que la précédente avait révélé.

## 0. Référence : un petit LLM brut

Qwen3-1.7B (Q4_K_M) avec le prompt et les outils du framework domotique, sans entraînement. Résultat sur le banc de 92 phrases en français : **17/92 (18 %)** — et seulement **2/76 sur les vraies commandes** : le modèle écrit le nom de l'outil en texte brut (« HassTurnOn light.salon ») au lieu d'émettre un appel d'outil.

## 1. Affinage LoRA

**Quoi :** apprendre au modèle le *format* et le *comportement* : quand appeler un outil, avec quels arguments, en français, et quand **ne pas** en appeler.

| Paramètre | Valeur |
|---|---|
| Modèle de base | `Qwen/Qwen3-1.7B` (bf16) |
| Méthode | LoRA, rang 32, taux d'apprentissage 2e-4, accumulation de gradient 8, longueur max 2 000 tokens |
| Perte | **uniquement sur les tokens de la réponse** (sinon les longs prompts saturent la mémoire GPU et le modèle gaspille sa capacité à apprendre le prompt) |
| Matériel | une RTX 5070 (12 Go) ; ~1 h pour la première version, 19 min pour un modèle de 0,6 Md |
| Export | fusion → GGUF (f16) → `llama-quantize` **Q4_K_M** (~1,1 Go pour 1,7 Md) → Ollama |
| Données | synthétiques, générées par des scripts, **sans fuite** vers le banc (mêmes appareils, phrases différentes) |

Itérations :

| Version | Données d'entraînement | Ce qui a été corrigé |
|---|---|---|
| v1 | 2 124 exemples à un tour, prompt complet | appel d'outils : 18 % → 96 % au premier appel. Mais le modèle **rappelle l'outil** après le résultat |
| v2 | 3 844 exemples multi-tours : succès → « C'est fait », erreur → refus et **arrêt** ; ordres par zone | plus de boucle ; refus propres après une erreur forcée |
| v3 | le prompt réellement envoyé par la tablette (25 outils) 70 % + prompt à 18 outils 30 % ; 0 à 3 tours d'historique (dont les réponses locales « Allumé ») ; bruit de reconnaissance vocale (« lumières » → « vumières ») ; température 0 | le modèle n'*imite* plus le tour précédent de l'assistant |
| v4c | exemples v3 convertis au format **compact** | prompt plus petit, meilleur modèle avant la recherche web |
| v5 | v4c + consigne de recherche web + exemples de recherche (x3) + **extraits synthétiques** (3 895 échantillons) | recherche web ; modèle en production |

## 2. RAG : testé, non retenu

**Hypothèse :** ne pas envoyer tous les appareils ; récupérer les *k* plus pertinents avec un modèle d'embedding et n'envoyer que ceux-là.

- Scripts : pack de connaissance (un document par appareil : nom, zone, synonymes, phrases d'exemple), récupération avec `multilingual-e5-base`, évaluation de la récupération.
- **La qualité de la récupération est bonne** : hit@1 = 94 % sur le banc.
- Mais les **résultats de bout en bout sont moins bons** : le RAG dans le message utilisateur a donné 26/31 (84 %) contre 96 % avec la liste complète des appareils.
- Et le RAG dans le prompt *système* est un piège de latence : le prompt change à chaque requête, donc le **cache de prompt du LLM est jeté**. À ~46 tokens/s de traitement du prompt, cela coûte ~25 s par requête.
- Avec quelques dizaines à ~100 appareils exposés, une **liste compacte fixe** (préfixe stable, cache toujours valide) bat la récupération. Le RAG deviendrait rentable avec plusieurs centaines d'appareils ou un contexte bien plus grand.

## 3. Prompt compact et proxy

Décrit en [02](02-architecture.md). Ce fut le **plus gros gain**, supérieur à tout changement de modèle : prompt ÷ 2,3, un seul tour d'outils, noms d'outils validés, paramètres de décodage imposés, cache stable.

## 4. Garde-fous déterministes

Trois petits morceaux de code corrigent trois défauts plus sûrement qu'un entraînement supplémentaire : valeurs inventées sur capteurs indisponibles, refus à tort après un appel d'outil réussi, et nombres non étayés dans les réponses web ([02](02-architecture.md)).

## 5. Recherche web privée

Un outil `web_search` exécuté par le proxy contre une instance SearXNG locale. Choix de conception :

- Les requêtes sont **anonymisées** (noms d'appareils, de pièces et alias retirés, sauf les mots de météo et les mots génériques) et journalisées **7 jours** seulement.
- Les extraits sont limités à 4 résultats x 230 caractères ; des extraits plus courts étaient plus rapides (−3 s) mais nettement moins justes.
- Un cache **en mémoire** (10 min, 100 entrées, jamais écrit sur disque) évite de répéter les recherches identiques.
- Les moteurs de recherche publics limitent le débit en rafale (HTTP 429) : les données d'entraînement de cet outil sont donc surtout **synthétiques** (extraits fabriqués dans le style des vrais, réponses calculées par règle, vrais extraits d'autres requêtes utilisés comme distracteurs).

## 6. Autres modèles

- **CroissantLLM 1,3B** (architecture Llama centrée sur le français, contexte de 2 048 tokens) : entraîné avec la même recette. La première version a obtenu 37 % parce qu'elle avait été entraînée avec un **tokenizer** (HF) différent de celui de l'inférence (llama.cpp) : la clé JSON `arguments` devenait `a`. Un réentraînement avec la tokenisation de llama.cpp l'a corrigé.
- **Qwen3-0.6B** : mêmes données et même recette que le 1,7B, pour mesurer le compromis vitesse/qualité.

## Comment fonctionne le banc

- **92 phrases en français** (data/benchmark_fr_92.json) : lumières, volets, clim, scripts, listes, informations, culture générale, **pièges** (appareils inexistants), **transcriptions bruitées**, et cas **adverses** (capteurs indisponibles).
- **Bancs** : premier appel d'outil ; requête exacte du framework + résultats d'outils simulés (succès ou erreur forcée) pour détecter boucles et fausses confirmations ; pipeline compact ; routage et justesse du web ; rejeux sous contrainte.
- **Tests sûrs** : un *proxy de simulation* retire tous les appels d'outils, et un agent séparé rattaché à aucun pipeline permet de rejouer la requête exacte du framework **sans rien exécuter**.
