"""
run_veille.py
Script autonome de veille réglementaire
========================================
À exécuter via le Planificateur de tâches Windows tous les jours à 6h.
Lance la veille Tavily et sauvegarde les résultats dans data/veille/.

Commande à configurer dans le Planificateur de tâches :
  Programme : C:\chemin\vers\keepinbot\.venv\Scripts\python.exe
  Arguments  : C:\chemin\vers\keepinbot\scripts\run_veille.py
  Démarrer dans : C:\chemin\vers\keepinbot
"""

import sys
import os

# Ajouter la racine du projet au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.core.veille import lancer_veille
from datetime import datetime

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Démarrage de la veille réglementaire...")

rapport = lancer_veille()

if rapport.get("error"):
    print(f"ERREUR : {rapport['error']}")
    sys.exit(1)

print(f"Veille terminée : {rapport['nb_changements']} changement(s) sur {rapport['nb_sujets']} sujets")
print(f"Requêtes Tavily ce mois : {rapport['quota']['requetes']} / 1000")

if rapport['quota'].get('alerte'):
    print("ALERTE : quota Tavily à 80% — vérifier la consommation")