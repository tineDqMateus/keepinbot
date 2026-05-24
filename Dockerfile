# docker-compose.yml — Keepinbot
# ================================
# Deux profils de déploiement :
# - dev (défaut)  : localhost uniquement, pour le développement
# - prod          : réseau interne entreprise, pour le déploiement
#
# Lancer en développement : docker compose up
# Lancer en production    : docker compose --profile prod up

version: "3.9"

services:

  # ── Application Keepinbot ──────────────────────────────────────────────────
  app:
    build: .
    container_name: keepinbot_app
    # Profil dev : localhost uniquement
    ports:
      - "127.0.0.1:8501:8501"
    environment:
      - PYTHONPATH=/app
      - LLM_MODE=${LLM_MODE:-local}
      - MISTRAL_API_KEY=${MISTRAL_API_KEY}
      - CHROMA_PATH=/app/data/chroma
      - CORPUS_PATH=/app/data/corpus
      - OLLAMA_BASE_URL=http://ollama:11434
    volumes:
      # Les dossiers data/ sont montés comme volumes
      # Les données persistent entre les redémarrages du conteneur
      - ./data/corpus:/app/data/corpus
      - ./data/chroma:/app/data/chroma
      - ./data/public:/app/data/public
      - ./data/samples:/app/data/samples
    depends_on:
      - ollama
    restart: unless-stopped

  # ── Application Keepinbot (profil production) ──────────────────────────────
  app_prod:
    build: .
    container_name: keepinbot_app_prod
    profiles:
      - prod
    # Profil prod : accessible sur tout le réseau interne
    ports:
      - "0.0.0.0:8501:8501"
    environment:
      - PYTHONPATH=/app
      - LLM_MODE=${LLM_MODE:-local}
      - MISTRAL_API_KEY=${MISTRAL_API_KEY}
      - CHROMA_PATH=/app/data/chroma
      - CORPUS_PATH=/app/data/corpus
      - OLLAMA_BASE_URL=http://ollama:11434
    volumes:
      - ./data/corpus:/app/data/corpus
      - ./data/chroma:/app/data/chroma
      - ./data/public:/app/data/public
      - ./data/samples:/app/data/samples
    depends_on:
      - ollama
    restart: unless-stopped

  # ── Ollama — LLM local ─────────────────────────────────────────────────────
  ollama:
    image: ollama/ollama:latest
    container_name: keepinbot_ollama
    ports:
      - "127.0.0.1:11434:11434"
    volumes:
      # Les modèles Ollama sont persistés sur le disque hôte
      # Évite de retélécharger le modèle à chaque redémarrage
      - ollama_models:/root/.ollama
    environment:
      # Force le mode CPU — pas de GPU requis
      - OLLAMA_NUM_GPU=0
    restart: unless-stopped

volumes:
  # Volume nommé pour les modèles Ollama
  ollama_models: