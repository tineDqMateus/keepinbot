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


## J4 — Routeur hybride et gestion local/cloud

**Objectif :** faire en sorte que le système sache automatiquement si une question
porte sur des données publiques ou internes, et envoie chaque requête vers le bon
moteur — cloud ou local.

---

### Étape 1 — Résoudre le problème mémoire

Mistral 7B nécessite environ 8 Go de RAM pour tourner sur CPU — insuffisant sur
cette machine. Remplacé par Phi-3 Mini (Microsoft, 3.8B paramètres, ~2.2 Go) qui
offre un bon compromis qualité/ressources pour un usage RAG.

Leçon : dans Keepinbot, le LLM est interchangeable en une ligne de configuration
— c'est exactement l'architecture modulaire prévue.

**Fichier modifié :** `app/core/config.py` — paramètre `OLLAMA_MODEL`

---

### Étape 2 — Renforcer le system prompt

Phi-3 Mini, plus petit que Mistral, a tendance à ajouter des informations non
demandées et à ne pas s'arrêter. Le system prompt a été renforcé avec des règles
numérotées et explicites : rester dans les documents, maximum 3 phrases, citer
la source, ne jamais supposer.

**Fichier modifié :** `scripts/test_rag.py` — constante `SYSTEM_PROMPT`

---

### Étape 3 — Ajouter un document public au corpus

Ajouté un extrait du Code du travail (articles L1234-1 et L1222-9) pour avoir
les deux types de documents dans la base — public et interne.

Les documents sont taggés automatiquement à l'ingestion selon leur nom de fichier :
préfixe `code_`, `legal_`, `urssaf_` → type `public`, tous les autres → type `interne`.

Ce tag est stocké dans les métadonnées de chaque chunk dans ChromaDB.

**Fichiers modifiés :** `data/corpus/code_travail.txt` (nouveau),
`app/core/rag.py` — fonction `load_documents()`

---

### Étape 4 — Écrire et tester le routeur hybride

Créé `app/core/router.py` — le composant qui décide quel moteur utiliser
pour chaque question :

| Types des chunks récupérés | Route | Moteur utilisé |
|---|---|---|
| Publics uniquement | cloud | API Mistral |
| Internes uniquement | local | Ollama + Phi3 |
| Mixtes | hybrid | Ollama + Phi3 (par sécurité) |

Règle de sécurité fondamentale : dès qu'un chunk interne est impliqué,
la génération reste en local — les données sensibles ne quittent jamais
la machine.

**Résultats validés :**
- Question interne → route `local` ✓
- Question mixte → route `hybrid`, génération locale ✓
- Route `cloud` pur : fonction



## J5 — Interface Streamlit — onglet Assistant

**Objectif :** rendre Keepinbot utilisable — transformer le pipeline
technique en une vraie application accessible depuis un navigateur.

---

### Étape 1 — Créer le point d'entrée de l'application

Créé `app/main.py` qui organise l'application en quatre onglets :
Assistant, Documentation, Collecte, Administration.
Les trois derniers affichent un message "disponible prochainement"
— ils seront implémentés en J6, J7 et J8.

**Fichier créé :** `app/main.py`

---

### Étape 2 — Construire l'onglet Assistant

Créé l'interface de chat avec :
- Une zone de conversation qui conserve l'historique
- Les sources affichées en couleur : 🟣 document interne, 🟢 document public
- Un indicateur de routage : 🟣 local · 🟢 cloud · 🟡 hybrid
- Un upload de nouveaux documents avec mise à jour automatique de la base
- La liste des documents indexés
- L'état des services (Ollama disponible ou non)

**Fichier créé :** `app/tabs/assistant.py`

---

### Étape 3 — Itérer sur le system prompt

Le modèle Phi-3 Mini avait tendance à ajouter des informations
non demandées et à poser des questions spontanément.
Le system prompt a été renforcé en trois itérations :
- Ajout d'une règle "ne pose jamais de question"
- Limite à une seule phrase de réponse
- Interdiction d'ajouter des informations connexes

**Résultats validés :**
- Question avec réponse dans les documents → réponse courte et sourcée ✓
- Question hors corpus → "Je ne trouve pas cette information dans les documents." ✓

**Fichier modifié :** `app/core/router.py` — constante `SYSTEM_PROMPT`

---

### Étape 4 — Mise à jour du README

Remplacement de Mistral 7B par Phi-3 Mini dans la documentation
suite au changement effectué en J4.

**Fichier modifié :** `README.md`

---

## État du projet après J5

✓ Application Streamlit opérationnelle et accessible depuis le navigateur
✓ Chat RAG fonctionnel avec historique, sources colorées et indicateur de routage
✓ Upload de documents avec mise à jour automatique de la base
✓ System prompt stabilisé — réponses concises, sourcées, sans dérive
✓ README et journal mis à jour

**Prochaine étape — J6 :** Module 2 — parsers multi-format
(Word, PowerPoint, mails) et pipeline de génération de documentation
à partir de sources hétérogènes.


## J6 — Module 2 : parsers multi-format et génération documentaire

**Objectif :** lire des fichiers hétérogènes (Word, PowerPoint, mails)
et générer un document structuré à partir de ces sources disparates.

---

### Étape 1 — Créer les fichiers de test

Généré 3 fichiers fictifs simulant des documents internes d'une PME
sur un projet fictif (projet Alpha) :
- Un compte-rendu de réunion Word
- Une présentation PowerPoint de lancement
- Un mail d'échange sur le recrutement

Ces fichiers couvrent les formats les plus courants en entreprise
et permettent de tester le pipeline sur des données réalistes.

**Fichiers créés :**
- `data/samples/cr_reunion_alpha.docx`
- `data/samples/presentation_alpha.pptx`
- `data/samples/mail_recrutement.eml`
- `scripts/create_samples.py` — script de génération des fichiers de test

---

### Étape 2 — Implémenter les parsers multi-format

Écrit un parser dédié pour chaque format :
- Word (.docx) : extraction des paragraphes dans l'ordre
- PowerPoint (.pptx) : extraction diapositive par diapositive
- Mail (.eml) : extraction des en-têtes et du corps du message
- Texte brut (.txt) : lecture directe

Un router de parsing détecte automatiquement le format selon
l'extension du fichier et appelle le bon parser.

**Résultat validé :**
- cr_reunion_alpha.docx → 639 caractères extraits ✓
- mail_recrutement.eml → 896 caractères extraits ✓
- presentation_alpha.pptx → 569 caractères extraits ✓

**Fichier complété :** `app/core/generator.py` — fonctions `parse_txt()`,
`parse_docx()`, `parse_pptx()`, `parse_eml()`, `parse_file()`, `parse_folder()`

---

### Étape 3 — Générer un document structuré via le LLM

Écrit le prompt de structuration qui instruit le LLM à :
- Fusionner les informations des différentes sources
- Structurer en Markdown avec titres et sections
- Signaler les lacunes avec [À COMPLÉTER]
- Signaler les contradictions entre sources
- Citer les sources en fin de document

Test effectué en mode cloud (API Mistral) — la génération locale
dépasse le timeout sur CPU avec Phi3 pour des documents longs.
En production sur un serveur dimensionné, le mode local fonctionnerait.

**Résultat validé :** document Markdown complet généré à partir des
3 fichiers — planning, équipe, budget, décisions, points ouverts,
sources citées. Les [À COMPLÉTER] apparaissent correctement. ✓

**Fichier complété :** `app/core/generator.py` — fonctions
`generate_document()`, `_generate_local()`, `_generate_cloud()`

---

## État du projet après J6

✓ Parsers opérationnels pour Word, PowerPoint, mail et texte brut
✓ Génération de document structuré Markdown à partir de sources hétérogènes
✓ Lacunes et contradictions signalées automatiquement
✓ Sources citées en fin de document généré
✓ Architecture locale/cloud selon les ressources disponibles

**Note technique :** la génération de documents longs nécessite
le mode cloud sur cette machine de développement (timeout CPU).
En déploiement production sur serveur dimensionné, le mode local
est viable avec Mistral 7B ou LLaMA 3.

**Prochaine étape — J7 :** interface Streamlit pour le Module 2
— upload multi-fichiers, bouton générer, aperçu du document,
téléchargement Word, validation avant indexation dans la base RAG.

## J7 — Onglet Documentation dans Streamlit

**Objectif :** rendre le Module 2 utilisable depuis le navigateur —
upload de fichiers, génération, téléchargement et validation avant indexation.

---

### Étape 1 — Construire l'interface de génération

Créé l'onglet Documentation avec un workflow en 2 étapes :
- Étape 1 : upload de plusieurs fichiers simultanément + saisie du titre
- Étape 2 : aperçu du document généré, téléchargement Word, validation ou rejet

**Fichier complété :** `app/tabs/documentation.py`

---

### Étape 2 — Convertir le document Markdown en Word

Écrit la fonction `save_as_docx()` qui convertit le Markdown généré
par le LLM en fichier Word téléchargeable.
Deux corrections apportées :
- Suppression des balises ```markdown``` que le LLM ajoute parfois
- Déduplication du titre (présent dans le Markdown ET ajouté par Word)

**Fichier complété :** `app/tabs/documentation.py` — fonction `save_as_docx()`

---

### Étape 3 — Valider et indexer dans la base RAG

Implémenté le bouton "Valider et indexer" qui sauvegarde le document
dans `data/corpus/` avec le préfixe `generated_` et reconstruit
le vectorstore ChromaDB.

Principe de validation humaine respecté : le document n'est jamais
indexé automatiquement — l'utilisateur relit et valide explicitement.

**Fichier complété :** `app/tabs/documentation.py` — fonction `index_document()`

---

### Étape 4 — Valider le pipeline bout en bout

Test complet réalisé avec les 3 fichiers du corpus de démonstration :
- Upload des 3 fichiers (Word, PPT, mail) ✓
- Génération du document "Synthèse projet Alpha" en mode cloud ✓
- Téléchargement Word sans doublon de titre ✓
- Validation et indexation dans la base RAG ✓
- Question posée dans l'onglet Assistant :
  "Quand démarre le projet Alpha ?"
  → "Le projet Alpha débute le 1er avril 2024.
  (Source: generated_synthèse_projet_alpha.txt — interne)" ✓

---

## État du projet après J7

✓ Onglet Documentation opérationnel dans le navigateur
✓ Upload multi-fichiers (Word, PPT, mail, texte)
✓ Génération de document structuré Markdown via API Mistral
✓ Téléchargement en Word propre sans artefacts Markdown
✓ Validation humaine obligatoire avant indexation
✓ Document indexé et interrogeable depuis l'onglet Assistant

**Note :** la génération est effectuée en mode cloud (API Mistral)
sur cette machine de développement — le mode local dépasse le timeout
CPU pour des documents longs. En production sur serveur dimensionné,
le mode local est viable.

**Prochaine étape — J8 :** Module 1 — collecte automatique de documents
réglementaires publics (Légifrance, URSSAF) via scraping,
parsing PDF et indexation dans la base RAG.