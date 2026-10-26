# 06 — Leçons, incidents et limites

## Incidents qui ont façonné la conception

| Incident | Cause | Règle qui en découle |
|---|---|---|
| **Sept lampes allumées en 45 secondes** pendant un test | Un premier modèle était branché avec un vrai contrôle et testé par l'API de conversation. Après une erreur d'outil, il réessayait sur d'autres appareils. Le banc ne mesurait que le *premier* appel d'outil, et un test qui exécutait réellement des commandes avait été appelé « simulation » | **Ne jamais tester un agent de contrôle en conditions réelles.** Une simulation est un chemin qui ne peut pas exécuter (un proxy qui retire les appels d'outils). Entraîner les *tours d'erreur* (« appareil introuvable » → refuser et s'arrêter). Le framework plafonne les itérations d'outils à 10 |
| Génération sans fin, réponses aléatoires | Le framework n'envoie **ni température ni limite de tokens** ; le serveur prenait par défaut 0,6 et aucune limite | Imposer température 0 et un plafond de 160 tokens dans le proxy |
| « Pas de réponse » aux premières phrases | La tablette envoie un **prompt différent** de celui de l'API (25 outils, ~3 000 tokens) ; à froid, ~63 s, au-delà du délai du client | Capturer la *vraie* requête, préchauffer le cache, réduire le prompt |
| Commandes qui échouent avec un historique de conversation | Le modèle **imitait le tour précédent de l'assistant** (« Allumé », une réponse locale sans appel d'outil) | Entraîner avec 0 à 3 tours d'historique |
| Un « passes » (avec un s) prononcé et non reconnu | La reconnaissance vocale conjugue autrement que les phrases déclencheuses ; un LLM de repli sans outils **affirmait** avoir agi | Un LLM sans outils ne doit jamais pouvoir affirmer une action ; phrases déclencheuses tolérantes |
| Latence de 25 à 37 s sur certaines phrases | Un historique glissant jetait le cache de prompt du LLM ; retirer les outils au tour 2 aussi | Historique court en texte seul ; garder le préfixe du prompt stable |
| 37 % pour le modèle centré sur le français | Tokenizer d'entraînement ≠ tokenizer d'inférence (`arguments` devenait `a`) | Entraîner avec la tokenisation du moteur d'inférence |
| Valeurs inventées (« 0 degré ») sur un capteur indisponible | État jamais vu à l'entraînement | Le rendre « indisponible » **et** ajouter un garde-fou déterministe |
| « 3 100 km », puis « 31 000 km » pour une paire de villes | Extraits web sans chiffre ; un code postal lu comme une distance | Chaque nombre **avec son unité** doit figurer dans les extraits |

## Pièges pratiques

- Le vrai prompt du framework n'est pas celui qui est documenté : noms d'outils préfixés, contexte sans états, noms avec doubles espaces exacts. **Toujours capturer la vraie requête** avant de générer les données d'entraînement.
- Le traitement du prompt domine la latence sur CPU : **un prompt qui change à chaque requête casse le cache**.
- Le serveur ne garde qu'un modèle chargé : tester un autre modèle **évince la production**, qu'il faut réchauffer ensuite.
- Les attentes en arrière-plan du type `while pgrep -f "motif"` lancées par SSH se détectent **elles-mêmes** et ne se terminent jamais ; attendre plutôt un marqueur écrit dans un fichier de log.
- Les moteurs de recherche publics limitent le débit en rafale (HTTP 429) ; mélanger extraits réels et synthétiques pour les données d'entraînement.

## Limites de cette étude

- **Une machine, une maison, une langue.** Les latences sont celles d'un Intel Core i3-6100T sans GPU ; toutes les phrases du banc sont en français.
- **Parole synthétique pour le STT.** Le banc STT utilise de l'audio généré par TTS (propre, puis avec bruit ajouté à 15 dB de rapport signal/bruit), pas de vrais enregistrements au micro avec accents, distance et acoustique de pièce. Les taux d'erreur de mots sont donc **optimistes en valeur absolue** et surtout significatifs **les uns par rapport aux autres**.
- **Le banc est petit** (92 phrases, 46 pour les bancs au prompt de la tablette) et écrit par le même auteur que les générateurs de données d'entraînement : pas de fuite de phrases, mais un style proche. Des écarts d'une ou deux phrases relèvent du bruit.
- **Non mesuré :** Qwen3-4B (latence estimée ×2 à 2,5), quantification sous Q4_K_M, autres langues pour STT/TTS, usage concurrent (l'installation sert une requête à la fois).
- **Les requêtes réelles sur l'outil web** sont peu nombreuses (22) et instables (les moteurs changent) ; les résultats sont indicatifs.
- **La production est un seul foyer** avec quelques dizaines d'appareils ; l'intérêt du RAG à plus grande échelle n'est pas mesuré.

## Pistes ouvertes

- Un **GPU sur l'hôte d'inférence** rendrait un modèle de 4 à 8 Md aussi rapide que le 1,7 Md actuel.
- Enrichir les données d'entraînement du 0,6B avec des phrases de confirmation (2 à 3 époques) et mesurer sur davantage de requêtes web réelles.
- Ollama a récemment ajouté un modèle vocal (**Phonon**, synthèse vocale) : macOS d'abord, Windows/Linux annoncés. À tester contre Piper quand Linux sera supporté (prise en charge du français et vitesse sur CPU inconnues).
