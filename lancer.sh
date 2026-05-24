#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# lancer.sh — Script de démarrage Keepinbot
# Double-cliquer sur ce fichier pour lancer l'application
# ─────────────────────────────────────────────────────────────────────────────

echo "Démarrage de Keepinbot..."

# Vérification que Docker est disponible
if ! command -v docker &> /dev/null; then
    echo "ERREUR : Docker n'est pas installé."
    echo "Téléchargez Docker Desktop sur https://www.docker.com/products/docker-desktop"
    read -p "Appuyez sur Entrée pour fermer..."
    exit 1
fi

# Vérification que Docker tourne
if ! docker info &> /dev/null; then
    echo "ERREUR : Docker n'est pas démarré."
    echo "Lancez Docker Desktop et réessayez."
    read -p "Appuyez sur Entrée pour fermer..."
    exit 1
fi

# Démarrage des services
echo "Lancement des services..."
docker compose up -d

# Attente que l'application soit prête
echo "Attente du démarrage (30 secondes)..."
sleep 30

# Ouverture du navigateur
echo "Ouverture de Keepinbot dans le navigateur..."
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:8501
elif command -v open &> /dev/null; then
    open http://localhost:8501
else
    start http://localhost:8501
fi

echo "Keepinbot est disponible sur http://localhost:8501"