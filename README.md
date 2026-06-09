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
qui cite ses sources — déployable en local sur le réseau interne, sans compétence
technique côté client.

---

## Architecture — 3 modules

### Module 1 — Collecte Réglementation

Indexe les documents réglementaires publics déposés manuellement.

**Workflow :**
1. L'onglet **Veille** détecte quotidiennement les changements réglementaires
   via API Tavily sur les sources officielles (Légifrance, URSSAF, service-public.fr...)
2. En cas de changement 🔴, télécharger le document depuis le lien officiel fourni
3. Déposer le PDF dans `data/public/` en conservant le même nom de fichier
   que la version existante
4. Cliquer sur **Indexer** dans l'onglet Collecte Réglementation
5. L'ancienne version est automatiquement archivée dans `data/public/archive/`
   et remplacée dans la base de recherche
6. Effacer l'historique de veille dans l'onglet Veille

**Gestion des versions :**
- `data/public/` — zone de dépôt temporaire (vidée après indexation)
- `data/public/indexed/` — documents en vigueur dans la base
- `data/public/archive/` — versions remplacées conservées avec horodatage

**État actuel :**
Le dépôt manuel et l'indexation automatique sont opérationnels et testés.
Le téléchargement depuis des URLs publiques est disponible dans l'interface
mais non opérationnel sur les sites gouvernementaux français
(Cloudflare, protections anti-bot).

**Veille réglementaire :**
Recherche quotidienne via API Tavily filtrée sur les sources officielles.
Compare les résultats avec le contenu déjà indexé dans ChromaDB —
signale uniquement les changements absents de la base.
Planifiable via le Planificateur de tâches Windows (voir ci-dessous).


### Module 2 — Génération
À partir d'un corpus hétérogène (mails, PowerPoints, Word, comptes-rendus), produit un
document structuré et cohérent en Markdown, exportable en Word. Signale explicitement
les lacunes et contradictions détectées dans les sources. Aucun document généré n'entre
dans la base sans validation humaine explicite.

### Module 3 — Assistant RAG
Chatbot qui répond en langage naturel en citant ses sources. 
Un routeur hybride en local oriente chaque requête vers le moteur adapté selon la nature
des documents concernés.
Pour les documents publics uniquement, la génération est déléguée à l'API Mistral (cloud).

---

## Pourquoi ces choix techniques

### Confidentialité des données
Les données internes d'une entreprise ne peuvent pas transiter sur des serveurs externes.
Keepinbot fonctionne en mode hybride :

- **Données publiques** (réglementaires) → cloud · API Mistral · pgvector
- **Données sensibles** (projets, contrats, RH) → local · Ollama + Phi-3 Mini · ChromaDB

Le LLM local tourne entièrement sur la machine du client. Zéro appel externe sur les données
sensibles. Dès qu'un chunk interne est impliqué dans une réponse, la génération reste locale.

### Modularité et coût maîtrisé
L'ensemble de la stack est open source. Le LLM est interchangeable en une ligne de
configuration — API externe pour la démonstration, modèle local pour un déploiement sensible.
Pas de licence, pas de vendor lock-in.

### Déployabilité
L'application est conteneurisée (Docker). Le client installe Docker une fois,
double-clique sur `lancer.sh` pour démarrer, interagit uniquement via une
interface web. Aucun terminal, aucune dépendance à gérer côté client.

En profil production (`docker compose --profile prod up`), l'application est
accessible depuis tous les postes du réseau interne de l'entreprise.

**Option A — PC Windows dans les locaux**
Docker Desktop + `lancer.sh`. Si le PC se met en veille, configurer le
Planificateur de tâches Windows pour le réveiller à 5h55 (avant le cron
de veille à 6h). Docker Desktop doit être configuré pour démarrer
automatiquement avec Windows.

**Option B — Serveur Linux dans les locaux (recommandé)**
Solution optimale pour la production — données sur site, veille automatique
24h/24 sans contrainte de mise en veille. Un mini-serveur suffit (NUC Intel,
ancien PC, NAS compatible Docker) avec 16 Go RAM.
Docker Engine (version serveur, plus légère que Desktop) + systemd pour
le démarrage automatique. Même `docker-compose.yml` que sur Windows —
aucune configuration supplémentaire pour la veille.

**Option C — VPS chez un hébergeur**
Veille automatique 24h/24 mais les données internes transitent hors site.
À réserver aux documents publics uniquement si la confidentialité est une
contrainte forte.

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
| LLM local | Ollama + Phi-3 Mini (3.8B) | Inférence locale — données sensibles |
| LLM cloud | API Mistral | Performance — données publiques |
| Embeddings local | Sentence-Transformers | Vectorisation sans appel externe |
| Vector store local | ChromaDB | Stockage vectoriel fichier local |
| Parsing documents | PyMuPDF · python-docx · python-pptx | PDF, Word, PowerPoint |
| Interface | Streamlit | Chatbot + upload + administration |
| Conteneurisation | Docker + Compose | Déploiement clé en main |
| Planification | APScheduler | Collecte périodique automatisée |
| Évaluation RAG | RAGAS | Fidélité, pertinence, précision |

100% open source · Python 3.11

---

## Démarrage rapide

### Prérequis
- Docker Desktop installé et démarré
- Git

### Installation
```bash
git clone https://github.com/tineDqMateus/keepinbot.git
cd keepinbot
cp .env.example .env  # configurer la clé API Mistral
```

### Lancement
```bash
# Double-clic sur lancer.sh
# ou depuis le terminal :
docker compose up
```

L'application est disponible sur http://localhost:8501

### Déploiement réseau interne
```bash
docker compose --profile prod up
```

L'application est accessible depuis tous les postes sur http://IP_SERVEUR:8501


### Veille réglementaire automatique

La veille se lance manuellement depuis l'onglet Veille ou automatiquement
via le Planificateur de tâches Windows.

**Configuration du Planificateur de tâches Windows :**

1. Touche Windows → **Planificateur de tâches**
2. **Créer une tâche de base**
3. Nom : `Keepinbot — Veille réglementaire`
4. Déclencheur : **Tous les jours** → heure souhaitée (ex : 6h00)
5. Action : **Démarrer un programme**
   - Programme : `C:\chemin\vers\keepinbot\.venv\Scripts\python.exe`
   - Arguments : `scripts\run_veille.py`
   - Démarrer dans : `C:\chemin\vers\keepinbot`
6. **Terminer**

Les résultats sont disponibles dans l'onglet **Veille** de l'interface.
En cas de changement détecté, téléchargez les nouveaux documents
depuis les sources officielles et déposez-les dans l'onglet **Collecte Réglementation**.


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
- **Génération locale** : la génération de documents longs (Module 2) dépasse le timeout
  CPU sur machines modestes. Mode cloud recommandé pour ce module en production sur
  infrastructure légère.

---

## Statut

✅ Projet complet — développé dans le cadre d'un titre RNCP niveau 7
« Expert en ingénierie de l'intelligence artificielle »