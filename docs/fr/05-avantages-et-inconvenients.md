# 05 — Avantages et inconvénients

## Tout local contre cloud

| | Tout local (cette étude) | Voix + LLM dans le cloud |
|---|---|---|
| **Confidentialité** | L'audio, le texte et les commandes ne quittent jamais la maison ; les requêtes web sont anonymisées et le journal purgé après 7 jours | La voix et les requêtes sont traitées par un tiers |
| **Disponibilité** | Fonctionne sans Internet pour tout le contrôle de la maison ; seules les questions web ont besoin d'une connexion | Tombe en panne quand la connexion ou le fournisseur tombe |
| **Coût** | Matériel déjà possédé ; aucun tarif par requête ; électricité seulement | Abonnement ou tarif par token |
| **Latence** | Ordres domotiques ~5 à 10 s de bout en bout sur un mini-PC sans GPU ; questions web ~20 s | Typiquement 1 à 3 s |
| **Qualité** | Un modèle de 1,7 Md est excellent sur *une tâche étroite* (appel d'outils sur une liste d'appareils connue), faible en culture générale, calcul et raisonnement multi-étapes | Assistant généraliste bien plus fort |
| **Maîtrise** | Vous maîtrisez le prompt, le modèle, les garde-fous et le comportement en cas d'échec | Le comportement change sans préavis |
| **Effort** | Important : génération de données, entraînement, bancs, un proxy à maintenir | Presque nul |
| **Sûreté** | Les échecs peuvent être rendus **déterministes et sûrs** (garde-fous, simulation, refus sur erreur) | Opaque |

**Verdict.** Le local est le bon choix quand la confidentialité, l'indépendance et la prévisibilité comptent et que les tâches sont *étroites et structurées* (domotique). C'est le mauvais choix si l'objectif est un assistant conversationnel généraliste : un petit modèle sur CPU n'égalera pas un modèle cloud, et ~20 s pour une réponse web est lent.

## Technique par technique

| Technique | Avantages | Inconvénients | Verdict ici |
|---|---|---|---|
| **Sans entraînement** (modèle brut) | Rien à construire | 18 % sur le banc ; écrit le nom de l'outil en texte | Inutilisable |
| **Affinage LoRA** | Fait passer un modèle de 1,7 Md de 18 % à ~96 % sur l'appel d'outils ; petit adaptateur ; ~1 h sur un GPU grand public ; améliore le français et les refus ; peut encoder « s'arrêter après une erreur » | Demande un GPU pour l'entraînement, des données synthétiques et un banc ; à **réentraîner quand les appareils changent** ; risque de surajustement au style des données | **Indispensable** |
| **RAG** (récupérer les appareils pertinents) | S'adapte à des centaines d'appareils ; pas de réentraînement quand les appareils changent | Composant supplémentaire (embedding, index) ; les erreurs de récupération deviennent des erreurs d'outil ; **un prompt qui change jette le cache du LLM** (≈ +25 s par requête sur CPU) | Pas rentable sous ~100 appareils ; à garder pour plus tard |
| **Prompt compact + proxy** | Prompt ÷ 2,3 ; cache stable ; limites strictes sur boucles, longueur et noms d'outils ; permet des tests sûrs | Un service de plus à exploiter ; le modèle est couplé au format du proxy | **Plus gros gain** |
| **Garde-fous déterministes** | Exacts, instantanés, testables ; corrigent des défauts qu'un entraînement supplémentaire ne corrige pas | Ils masquent les faiblesses du modèle au lieu de les supprimer ; chacun est un cas particulier | **Fortement recommandés** |
| **Recherche web locale** | Privée, sans clé d'API | Moteurs à débit limité ; les extraits manquent souvent du chiffre exact ; +12 à 18 s par rapport à un ordre | Utile, avec des réponses « introuvable » honnêtes |
| **Modèle plus petit** (0,6 Md) | ~40 % plus rapide ; fichier de 0,4 Go | Plus de confirmations erronées ; lit moins bien les extraits | Viable si la latence prime |
| **Modèle plus gros** (4 Md, non mesuré) | Probablement meilleur pour lire les extraits web | Latence ×2 à 2,5 sur ce CPU (estimation), fichiers plus gros | Un GPU serait le vrai levier |

## À quoi sert chaque couche

- Le **STT** décide de ce que le système entend, et c'est la **plus grosse latence fixe** (~3 s avec Whisper `small`). Whisper `small` est nettement plus précis que `tiny`/`base`, et un court **prompt de vocabulaire** aide. Un moteur **en streaming** répond en ~0,1 s après la fin de la parole, avec un taux d'erreur de mots plus élevé mais presque la même part de commandes correctes (sur de la parole synthétique) — [04](04-resultats.md).
- Le **LLM** décide de ce qu'il faut faire. L'affinage est ce qui rend un tout petit modèle fiable sur cette tâche unique.
- Les **garde-fous et le proxy** décident de ce qui a le *droit* d'arriver et de ce qui est répondu.
- Le **TTS** est la partie la moins chère : Piper synthétise une phrase en environ 0,2 s sur ce CPU.
