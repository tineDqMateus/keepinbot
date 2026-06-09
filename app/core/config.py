"""
config.py — configuration centrale de Keepinbot
=================================================
Point d'entrée unique pour tous les paramètres de l'application.
Toute modification de comportement global se fait ici — pas dans le code métier.

Fonctionnement :
- Les variables sensibles (clé API) sont lues depuis le fichier .env
- Les paramètres techniques sont définis directement ici
- Tous les autres modules importent depuis config.py
"""

import os
from dotenv import load_dotenv

# Charge les variables définies dans le fichier .env
# .env n'est jamais commité sur GitHub (voir .gitignore)
load_dotenv()

# ── Mode LLM ──────────────────────────────────────────────────────────────────
# Détermine quel moteur de génération est utilisé.
# "local"  → Ollama + Phi-3 Mini — données traitées sur la machine du client,
#             zéro appel externe. Obligatoire pour les données sensibles.
# "cloud"  → API Mistral — plus rapide, nécessite une connexion internet
#             et une clé API. Réservé aux données publiques non sensibles.
# Valeur par défaut : "local" — le mode le plus sûr
LLM_MODE = os.getenv("LLM_MODE", "local")

# ── Clé API Mistral ───────────────────────────────────────────────────────────
# Utilisée uniquement en mode "cloud".
# Stockée dans .env, jamais en dur dans le code.
# Obtenir une clé : console.mistral.ai (gratuit jusqu'à 1M tokens/mois)
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# ── Chemins ───────────────────────────────────────────────────────────────────
# CHROMA_PATH : dossier où ChromaDB sauvegarde les vecteurs sur disque.
#   Permet de recharger le vectorstore sans reconstruire les embeddings
#   à chaque démarrage.
CHROMA_PATH = os.getenv("CHROMA_PATH", "./data/chroma")

# CORPUS_PATH : dossier contenant les documents sources à indexer.
#   En production, l'utilisateur uploade ses documents via l'interface
#   Streamlit — ils sont déposés dans ce dossier avant indexation.
CORPUS_PATH = "./data/corpus"

# ── Paramètres RAG ────────────────────────────────────────────────────────────
# CHUNK_SIZE : taille maximale d'un chunk en caractères.
#   500 est un bon compromis pour des documents métier en français.
#   Augmenter si les documents ont des paragraphes très longs.
#   Diminuer si les réponses contiennent trop d'informations non pertinentes.
CHUNK_SIZE = 800

# CHUNK_OVERLAP : chevauchement entre deux chunks consécutifs en caractères.
#   50 caractères évitent de perdre une information à la jonction
#   entre deux chunks sans trop alourdir le stockage.
CHUNK_OVERLAP = 50

# TOP_K : nombre de chunks retournés par le retrieval pour chaque question.
#   3 chunks = contexte suffisant sans surcharger la fenêtre du LLM.
#   Augmenter si les réponses semblent incomplètes.
#   Diminuer si les réponses contiennent des informations hors sujet.
TOP_K = 5

# ── Paramètres LLM local (Ollama) ─────────────────────────────────────────────
# OLLAMA_BASE_URL : adresse du serveur Ollama sur la machine locale.
#   11434 est le port par défaut d'Ollama — ne pas modifier sauf
#   si un autre service occupe ce port.
OLLAMA_BASE_URL = "http://localhost:11434"

# OLLAMA_MODEL : nom du modèle chargé dans Ollama.
#   "phi3:mini" pointe vers Phi-3 Mini (3.8B paramètres, ~2.5 Go).
#   Choix retenu pour fonctionner sur CPU avec RAM limitée.
#   Alternatives : "mistral" (7B, ~4.4 Go — nécessite 8 Go RAM),
#                  "llama3" (8B, ~4.7 Go), "mistral:7b-instruct"
OLLAMA_MODEL = "phi3:mini"

# ── Paramètres LLM cloud (API Mistral) ────────────────────────────────────────
# MISTRAL_MODEL : modèle Mistral utilisé en mode cloud.
#   "mistral-small-latest" : bon équilibre qualité / coût.
#   Alternatives : "mistral-large-latest" (meilleur, plus cher),
#                  "open-mistral-7b" (gratuit, moins performant)
MISTRAL_MODEL = "mistral-small-latest"

# print de debug pour vérifier que la config est bien chargée
#print(f"Config chargée — mode : {LLM_MODE}")