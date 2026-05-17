# Keepinbot

> Plutôt que de tout garder à l'esprit, on charge le bot.

Assistant documentaire RAG hybride pour PME/TPE — collecte, structure et interroge
la connaissance de l'entreprise en langage naturel, sans que les données sensibles
ne quittent jamais son infrastructure.

---

## Ce que fait Keepinbot

Une PME accumule de la connaissance dans des endroits éparpillés : mails, comptes-rendus,
présentations, procédures Word, documents réglementaires. Personne ne sait où chercher,
les nouvelles recrues se noient, la veille réglementaire se fait à la main.

Keepinbot centralise, structure et rend interrogeable cette connaissance via un chatbot
qui cite ses sources — déployable en local, sans compétence technique côté client.

---

## Architecture — 3 modules

### Module 1 — Collecte
Pipeline automatisé qui surveille les sources réglementaires publiques (Légifrance, URSSAF,
BODACC), télécharge les nouveaux documents, extrait leur contenu et les indexe dans la base
documentaire. Aucune intervention humaine requise après configuration.

### Module 2 — Génération
À partir d'un corpus hétérogène (mails, PowerPoints, Word, comptes-rendus), produit un
document structuré et cohérent. Signale explicitement les lacunes et contradictions détectées
dans les sources. Aucun document généré n'entre dans la base sans validation humaine.

### Module 3 — Assistant RAG
Chatbot qui répond en langage naturel aux questions sur la documentation indexée, en citant
ses sources. Un routeur hybride oriente chaque requête vers le moteur adapté selon la nature
des documents concernés.

---

## Pourquoi ces choix techniques

### Confidentialité des données
Les données internes d'une entreprise ne peuvent pas transiter sur des serveurs externes.
Keepinbot fonctionne en mode hybride :

- **Données publiques** (réglementaires) → cloud · API Mistral · pgvector
- **Données sensibles** (projets, contrats, RH) → local · Ollama + Mistral 7B · ChromaDB

Le LLM local tourne entièrement sur la machine du client. Zéro appel externe sur les données
sensibles.

### Modularité et coût maîtrisé
L'ensemble de la stack est open source. Le LLM est interchangeable en une ligne de
configuration — API externe pour la démonstration, modèle local pour un déploiement sensible.
Pas de licence, pas de vendor lock-in.

### Déployabilité
L'application est conteneurisée (Docker). Le client installe Docker une fois, double-clique
pour démarrer, interagit uniquement via une interface web. Aucun terminal, aucune dépendance
à gérer côté client.

---

## Cas d'usage possibles

| Secteur | Cas d'usage |
|---|---|
| PME / TPE | Base de connaissance interne, onboarding, procédures |
| Juridique | Interrogation de contrats, CGV, documentation réglementaire |
| RH | Convention collective, règlement intérieur, politique de formation |
| Banque / Assurance | Conformité réglementaire, backtesting documentaire |
| Industrie | Documentation technique, fiches produits, SAV |
| Tout secteur | Veille réglementaire automatisée, capitalisation avant départ |

---

## Stack technique

| Brique | Outil | Rôle |
|---|---|---|
| Orchestration RAG | LangChain 0.3.7 | Chaîne chunking → retrieval → génération |
| LLM local | Ollama + Mistral 7B | Inférence locale — données sensibles |
| LLM cloud | API Mistral | Performance — données publiques |
| Embeddings local | Sentence-Transformers | Vectorisation sans appel externe |
| Vector store local | ChromaDB | Stockage vectoriel fichier local |
| Vector store cloud | pgvector (PostgreSQL) | Stockage vectoriel partagé |
| Parsing documents | PyMuPDF · python-docx · python-pptx | PDF, Word, PowerPoint |
| Interface | Streamlit | Chatbot + upload + administration |
| Conteneurisation | Docker + Compose | Déploiement clé en main |
| Planification | APScheduler | Collecte périodique automatisée |
| Évaluation RAG | RAGAS | Fidélité, pertinence, précision |

100% open source · Python 3.11

---

## Limites

- **Hallucinations** : réduites par le RAG mais non éliminées. Chaque réponse affiche
  ses sources. Si l'information n'est pas dans les documents, le système le signale
  explicitement plutôt que d'inventer.
- **Module 2** : la qualité du document généré est bornée par la qualité des sources.
  Ce qui n'a jamais été écrit ne peut pas être reconstitué. Validation humaine obligatoire
  avant indexation.
- **Module 1** : pipeline déterministe, pas de LLM. Risque limité au parsing de PDFs
  complexes et à la fraîcheur des sources publiques.

---

## Statut

🚧 Projet en cours de développement — dans le cadre d'un titre RNCP niveau 7
« Expert en ingénierie de l'intelligence artificielle »
