# Journal de développement — Keepinbot

---

## J2 — Construire la base documentaire

**Objectif :** préparer les documents, les découper et les stocker sous une forme
qui permet de retrouver rapidement les passages pertinents pour une question donnée.

---

### Étape 1 — Créer les documents de test

Généré 3 documents texte simulant des documents internes d'une PME fictive
(Artisan Plus SARL) :
- `procedure_rh.txt` — congés, télétravail, formation, préavis, mutuelle
- `fiche_produit.txt` — description produit, garantie, retours, SAV
- `faq_support.txt` — suivi commande, facturation, paiement, modifications

Ces documents servent de corpus de démonstration — ils sont représentatifs
de ce qu'une vraie PME chargerait dans le système.

**Fichier :** `data/corpus/`

---

### Étape 2 — Centraliser la configuration

Créé un fichier de configuration unique qui regroupe tous les réglages
de l'application : chemins des dossiers, clé API, choix du moteur IA,
taille des fragments de texte.

L'intérêt : modifier un paramètre à un seul endroit plutôt que de chercher
dans tout le code.

**Fichier :** `app/core/config.py`

---

### Étape 3 — Découper les documents en fragments

Découpé chaque document en petits blocs de texte appelés *chunks*.

Pourquoi : un assistant IA ne peut pas lire 50 pages d'un coup — on lui
envoie uniquement les passages qui répondent à la question posée.
Chaque bloc fait environ 500 caractères, avec un léger chevauchement
entre deux blocs consécutifs pour ne pas couper une information en deux.

**Résultat :** 3 documents → 7 fragments

**Fichier :** `app/core/rag.py` — fonction `chunk_documents()`

---

### Étape 4 — Transformer les fragments en vecteurs et les stocker

Converti chaque fragment de texte en une représentation numérique
(appelée *vecteur* ou *embedding*) qui capture le sens du texte.

Pourquoi : deux textes qui parlent de la même chose ont des vecteurs proches,
même s'ils n'utilisent pas les mêmes mots. C'est ce qui permet de retrouver
le passage sur le "préavis" quand on pose une question sur le "délai de départ".

Les vecteurs sont stockés sur disque dans une base locale (ChromaDB).
Aucune donnée ne sort de la machine.

**Résultat :** 7 fragments vectorisés et stockés localement

**Fichier :** `app/core/rag.py` — fonctions `build_vectorstore()`, `load_vectorstore()`

---

### Étape 5 — Retrouver les fragments pertinents pour une question

Testé la recherche : pour une question donnée, le système retrouve
les 3 fragments dont le sens est le plus proche de la question.

La proximité est mesurée par un score — plus le score est bas,
plus le fragment est pertinent.

**Résultat validé :**
- Question : *"Quel est le délai de préavis ?"*
- Fragment retourné en premier (score 0.601) : section préavis du document RH ✓

**Fichier :** `app/core/rag.py` — fonction `retrieve()`

---

## J3 — Brancher l'assistant et valider les réponses

**Objectif :** connecter le moteur IA (Mistral) au pipeline de recherche
et vérifier que les réponses sont correctes, sourcées et honnêtes.

---

### Étape 1 — Connecter le moteur IA local (Ollama + Mistral)

Branché Mistral 7B — le modèle de langage qui tourne en local — sur le pipeline
de recherche. Le moteur reçoit la question et les fragments pertinents,
et produit une réponse en français.

Tout tourne sur la machine, aucune donnée ne sort.

**Problème rencontré :** Mistral essayait d'utiliser la carte graphique (GPU)
mais la mémoire était insuffisante. Résolu en forçant le fonctionnement
sur le processeur central (CPU).

**Fichier :** `scripts/test_rag.py` — fonction `generate_response()`

---

### Étape 2 — Écrire les instructions permanentes du chatbot (system prompt)

Rédigé le texte d'instruction qui définit le comportement du chatbot
à chaque réponse :
- Répondre uniquement à partir des documents fournis
- Citer le document source dans chaque réponse
- Dire explicitement quand l'information est absente plutôt qu'inventer
- Rester concis et précis

Ces instructions sont la principale protection contre les réponses inventées.

**Fichier :** `scripts/test_rag.py` — constante `SYSTEM_PROMPT`

---

### Étape 3 — Tester la chaîne complète sur trois questions

Validé le pipeline de bout en bout :
question → recherche des fragments → envoi au moteur IA → réponse sourcée.

**Résultats :**

| Question | Réponse | Source citée |
|---|---|---|
| Quel est le délai de préavis ? | 1 mois employés, 2 mois cadres | procedure_rh.txt ✓ |
| Comment retourner un produit ? | 14 jours, emballage d'origine | fiche_produit.txt ✓ |
| Quelle est la politique de télétravail ? | 2 jours/semaine, 6 mois ancienneté | procedure_rh.txt ✓ |

**Fichier :** `scripts/test_rag.py` — fonction `ask()`

---

### Étape 4 — Tester le comportement quand l'information est absente

Posé une question hors sujet pour vérifier que le chatbot ne répond pas
en inventant une information.

**Question testée :** *"Quel est le chiffre d'affaires de l'entreprise ?"*

**Résultat :** le chatbot répond explicitement qu'il ne trouve pas cette
information dans les documents — sans rien inventer. ✓

Observation utile : le score de recherche sur cette question (1.0 à 1.2)
est nettement plus élevé que sur les questions pertinentes (0.6).
Ce seuil pourra servir à afficher un avertissement automatique
dans l'interface quand la réponse est peu fiable.

---

## État du projet après J2 et J3

✓ Base documentaire vectorielle construite et stockée en local
✓ Recherche sémantique fonctionnelle — le bon fragment arrive en premier
✓ Moteur IA connecté et opérationnel en local (CPU)
✓ Réponses correctes, sourcées et ancrées dans les documents
✓ Comportement honnête en cas d'absence d'information
✓ Code commenté et poussé sur GitHub

**Prochaine étape — J4 :** mettre en place le routeur hybride
qui oriente chaque question vers le moteur local (données sensibles)
ou le cloud (données publiques) selon la nature des documents concernés.
