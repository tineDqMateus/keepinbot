# Keepinbot — Scénario de démo entretien

---

## Le pitch en 30 secondes

*"Keepinbot est un assistant documentaire RAG hybride pour PME.
Plutôt que de tout garder à l'esprit, on charge le bot — il collecte
automatiquement des documents réglementaires, structure la connaissance
interne éparpillée dans des mails et des PPT, et répond aux questions
en langage naturel en citant ses sources. La contrainte centrale c'est
la confidentialité : les données sensibles ne sortent jamais de la machine
du client, le LLM tourne en local via Ollama. Livré comme une application
Docker, sans terminal côté client."*

---

## Avant la démo — checklist

- [ ] Ollama lancé en mode CPU (PowerShell : `$env:OLLAMA_NUM_GPU="0"`)
- [ ] Streamlit lancé (`PYTHONPATH=. streamlit run app/main.py`)
- [ ] Navigateur ouvert sur http://localhost:8501
- [ ] `.env` en mode `local`
- [ ] Les 4 documents de corpus sont bien indexés (vérifier onglet Admin)

---

## Scénario de démo — 10 minutes

### 1. Présentation rapide de l'interface (1 min)

Montrer les 4 onglets :
- *"L'onglet Assistant c'est le chatbot — on interroge les documents."*
- *"Documentation c'est le Module 2 — on génère des docs à partir de
  sources disparates."*
- *"Collecte c'est le Module 1 — on alimente la base automatiquement."*
- *"Administration c'est le panneau de contrôle."*

---

### 2. Démo onglet Assistant (4 min)

**Question 1 — document interne :**
> "Quel est le délai de préavis ?"

Montrer :
- La réponse sourcée (procedure_rh.txt)
- L'indicateur 🟣 Mode : Local
- *"Les données RH restent sur la machine — le LLM local génère la réponse."*

**Question 2 — document public :**
> "Que dit le code du travail sur le télétravail ?"

Montrer :
- La réponse sourcée (code_travail.txt)
- L'indicateur 🟢 Mode : Cloud ou 🟡 Mode : Hybride
- *"Pour les données publiques, on peut utiliser le cloud — plus rapide."*

**Question 3 — hors corpus :**
> "Quel est le chiffre d'affaires de l'entreprise ?"

Montrer :
- *"Je ne trouve pas cette information dans les documents."*
- *"Le système ne fabrique pas de réponse quand l'information est absente —
  c'est la première protection contre les hallucinations."*

**Upload d'un document :**
- Uploader `data/samples/procedure_rh.txt` depuis l'interface
- *"N'importe quel collaborateur peut enrichir la base depuis son navigateur."*

---

### 3. Démo onglet Documentation (3 min)

- Uploader les 3 fichiers de `data/samples/`
  (cr_reunion_alpha.docx, mail_recrutement.eml, presentation_alpha.pptx)
- Titre : "Synthèse projet Alpha"
- Cliquer Générer
- Montrer le document structuré généré
- *"On part de 3 fichiers hétérogènes — compte-rendu Word, mail,
  PowerPoint — et on obtient un document structuré en 30 secondes.
  Les [À COMPLÉTER] signalent les lacunes — on ne fabrique rien."*
- Télécharger en Word
- *"L'utilisateur relit, valide, et seulement alors le document
  entre dans la base interrogeable."*

---

### 4. Onglet Collecte (1 min)

- Montrer les 3 sources (dossier, URL, API Légifrance)
- *"En production, le Module 1 tourne automatiquement toutes les 24h —
  la base réglementaire se met à jour sans intervention humaine."*

---

### 5. Onglet Administration (1 min)

- Montrer l'état des services
- *"Le client voit l'état de tout le système depuis son navigateur —
  sans jamais ouvrir un terminal."*

---

## Questions techniques fréquentes en entretien

**"Comment vous gérez les hallucinations ?"**
*"Trois niveaux : le RAG ancre les réponses dans les documents,
le system prompt interdit de répondre hors contexte, et chaque réponse
affiche ses sources pour permettre la vérification humaine.
On teste aussi le cas hors corpus — le système dit explicitement
qu'il ne sait pas."*

**"Pourquoi Phi-3 Mini plutôt que Mistral ?"**
*"Contrainte de développement — mémoire GPU insuffisante sur ma machine.
L'architecture est modulaire : changer de modèle = une ligne dans config.py.
En production sur serveur dimensionné, on utiliserait Mistral 7B ou LLaMA 3."*

**"C'est quoi le RAG exactement ?"**
*"On ne demande pas au LLM de répondre de mémoire. À chaque question,
on cherche les passages les plus proches sémantiquement dans les documents,
et on les injecte dans le prompt. Le LLM reformule ce qu'on lui a fourni —
il ne génère pas librement. C'est comme donner le dossier complet
à un consultant juste avant la réunion."*

**"Pourquoi local/cloud hybride ?"**
*"Les données sensibles d'une entreprise ne peuvent pas sortir du SI.
Le routeur analyse les documents sources de chaque réponse :
si un document interne est impliqué, la génération reste en local.
Si la question ne porte que sur des données publiques réglementaires,
on peut utiliser le cloud pour la performance."*

**"Comment ça se déploie en entreprise ?"**
*"Docker. Le client installe Docker Desktop une fois, double-clique
sur lancer.sh, et l'application tourne sur leur réseau interne.
En profil production, tous les postes y accèdent depuis leur navigateur
— aucune installation côté client."*

**"Vous avez évalué la qualité des réponses ?"**
*"RAGAS est intégré dans la stack pour mesurer trois métriques :
faithfulness (la réponse est-elle fidèle aux documents ?),
answer relevancy (répond-elle à la question ?),
context precision (a-t-on récupéré les bons chunks ?).
L'évaluation formelle sera faite sur le corpus complet en production."*

---

## Points de différenciation à mettre en avant

1. **Architecture hybride local/cloud** — pas un choix par défaut,
   une réponse pensée aux contraintes RGPD des PME

2. **Validation humaine obligatoire** (Module 2) — pas d'indexation
   automatique, le système est conçu pour assister, pas remplacer

3. **Modularité** — chaque brique est remplaçable : LLM, vector store,
   source de collecte. Pas de vendor lock-in.

4. **Expérience métier** — 20 ans de contexte entreprise permettent
   de concevoir des cas d'usage réalistes et de comprendre pourquoi
   les projets IA échouent en production

5. **Open source et coût maîtrisé** — zéro licence, déployable
   sur l'infrastructure existante
