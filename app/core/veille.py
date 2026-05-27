"""
veille.py
Module de veille réglementaire — Keepinbot
==========================================

Recherche web quotidienne automatique via API Tavily pour détecter
les modifications réglementaires et alerter l'utilisateur.

Fonctionnement :
- Tous les jours à l'heure configurée (défaut : 6h)
- Lance une recherche Tavily pour chaque sujet de veille configuré
- Le LLM analyse les résultats et détecte si quelque chose a changé
- Les résultats sont stockés dans data/veille/YYYY-MM-DD.json
- L'historique est conservé jusqu'à effacement manuel

Quota Tavily :
- 1 requête par sujet par jour
- 10 sujets par défaut = 300 requêtes/mois (quota gratuit : 1 000/mois)
- Alerte automatique à 80% du quota (800 requêtes)

Confidentialité :
- Les recherches portent uniquement sur des sources publiques
- Aucune donnée interne n'est transmise à Tavily
"""

import os
import json
from datetime import datetime
from tavily import TavilyClient
from app.core.config import (
    MISTRAL_API_KEY, MISTRAL_MODEL,
    OLLAMA_BASE_URL, OLLAMA_MODEL,
    LLM_MODE
)
import requests

# ── Configuration veille ──────────────────────────────────────────────────────

# Dossier de stockage des résultats de veille
VEILLE_FOLDER = "./data/veille"

# Sujets de veille par défaut — configurables dans l'interface
VEILLE_SUJETS_DEFAUT = [
    "SMIC revalorisation 2026 France",
    "Code du travail modifications 2026",
    "congés payés réforme France 2026",
    "télétravail réglementation France 2026",
    "convention collective modifications 2026",
    "rupture conventionnelle règles 2026",
    "cotisations sociales employeur 2026",
    "arrêt maladie indemnisation 2026",
    "licenciement procédure France 2026",
    "retraite réforme France 2026",
]
# Sources officielles autorisées pour la veille
# Tavily ne cherchera que sur ces domaines
SOURCES_OFFICIELLES = [
    "legifrance.gouv.fr",
    "travail-emploi.gouv.fr",
    "service-public.gouv.fr",
    "urssaf.fr",
    "ameli.fr",
    "info.gouv.fr",
    "securite-sociale.fr",
    "retraite.cnav.fr",
    "boss.gouv.fr",
    "legislation.cnav.fr",
]

# Fichier de configuration des sujets (modifiable par l'utilisateur)
VEILLE_CONFIG_FILE = "./data/veille/sujets.json"

# Quota Tavily
TAVILY_QUOTA_MENSUEL = 1000
TAVILY_ALERTE_SEUIL = 800  # alerte à 80%
TAVILY_COMPTEUR_FILE = "./data/veille/compteur.json"


# ── Gestion des sujets ────────────────────────────────────────────────────────

def load_sujets() -> list[str]:
    """
    Charge la liste des sujets de veille depuis le fichier de config.
    Si le fichier n'existe pas, retourne les sujets par défaut.

    Retourne :
    - liste de sujets de recherche (str)
    """
    if os.path.exists(VEILLE_CONFIG_FILE):
        with open(VEILLE_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return VEILLE_SUJETS_DEFAUT


def save_sujets(sujets: list[str]) -> None:
    """
    Sauvegarde la liste des sujets de veille dans le fichier de config.

    Paramètre :
    - sujets : liste de sujets de recherche
    """
    os.makedirs(VEILLE_FOLDER, exist_ok=True)
    with open(VEILLE_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(sujets, f, ensure_ascii=False, indent=2)


# ── Gestion du quota ──────────────────────────────────────────────────────────

def load_compteur() -> dict:
    """
    Charge le compteur mensuel de requêtes Tavily.
    Réinitialise si on est dans un nouveau mois.

    Retourne un dict :
    {
      "mois"     : "2026-05" (str),
      "requetes" : nombre de requêtes ce mois (int)
    }
    """
    mois_actuel = datetime.now().strftime("%Y-%m")

    if os.path.exists(TAVILY_COMPTEUR_FILE):
        with open(TAVILY_COMPTEUR_FILE, "r") as f:
            compteur = json.load(f)
        # Réinitialiser si nouveau mois
        if compteur.get("mois") != mois_actuel:
            compteur = {"mois": mois_actuel, "requetes": 0}
    else:
        compteur = {"mois": mois_actuel, "requetes": 0}

    return compteur


def save_compteur(compteur: dict) -> None:
    """Sauvegarde le compteur mensuel."""
    os.makedirs(VEILLE_FOLDER, exist_ok=True)
    with open(TAVILY_COMPTEUR_FILE, "w") as f:
        json.dump(compteur, f)


def increment_compteur(nb: int = 1) -> dict:
    """
    Incrémente le compteur de requêtes et alerte si on approche du quota.

    Paramètre :
    - nb : nombre de requêtes à ajouter (défaut : 1)

    Retourne :
    - dict compteur mis à jour avec un champ "alerte" si seuil dépassé
    """
    compteur = load_compteur()
    compteur["requetes"] += nb
    compteur["alerte"] = compteur["requetes"] >= TAVILY_ALERTE_SEUIL
    save_compteur(compteur)
    return compteur


# ── Recherche et analyse ──────────────────────────────────────────────────────

def rechercher_sujet(sujet: str, api_key: str) -> dict:
    """
    Lance une recherche Tavily sur un sujet et retourne les résultats.

    Paramètre :
    - sujet   : sujet de recherche (ex: "SMIC revalorisation 2026")
    - api_key : clé API Tavily

    Retourne un dict :
    {
      "sujet"    : sujet recherché,
      "resultats": liste de résultats Tavily,
      "error"    : message d'erreur ou None
    }
    """
    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(
            sujet,
            max_results=5,
            include_domains=SOURCES_OFFICIELLES
        )
        return {
            "sujet": sujet,
            "resultats": response.get("results", []),
            "error": None
        }
    except Exception as e:
        return {
            "sujet": sujet,
            "resultats": [],
            "error": str(e)
        }


def analyser_changement(sujet: str, resultats: list[dict]) -> dict:
    """
    Demande au LLM d'analyser les résultats de recherche et de détecter
    si une modification réglementaire significative est signalée.

    Le LLM reçoit les titres et extraits des résultats Tavily et répond :
    - changed : True si un changement récent est détecté, False sinon
    - resume  : résumé court du changement ou "Pas de modification détectée"
    - sources : liste des URLs sources

    Paramètres :
    - sujet     : sujet recherché
    - resultats : liste de résultats Tavily

    Retourne un dict :
    {
      "changed" : bool,
      "resume"  : str,
      "sources" : list[str]
    }
    """
    if not resultats:
        return {
            "changed": False,
            "resume": "Aucun résultat de recherche.",
            "sources": []
        }

    # Assemblage du contexte pour le LLM
    context = "\n\n".join([
        f"Titre : {r.get('title', '')}\n"
        f"Extrait : {r.get('content', '')[:300]}\n"
        f"URL : {r.get('url', '')}"
        for r in resultats
    ])

    prompt = f"""Sujet de veille : {sujet}

Résultats de recherche récents :
{context}

Analyse ces résultats et réponds en JSON strict avec exactement ces champs :
{{
  "changed": true ou false,
  "resume": "résumé en une phrase du changement détecté, ou 'Pas de modification détectée'"
}}

changed = true uniquement si un changement réglementaire RÉCENT et CONCRET est mentionné.
changed = false si les résultats sont anciens, généraux ou sans nouveauté."""

    # Génération via LLM
    response_text = _appeler_llm(prompt)

    # Parse la réponse JSON
    try:
        # Nettoyage des balises markdown éventuelles
        clean = response_text.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        result = json.loads(clean.strip())
        result["sources"] = [r.get("url", "") for r in resultats]
        return result
    except Exception:
        # Fallback si le JSON est mal formé
        changed = "true" in response_text.lower() and "false" not in response_text.lower()
        return {
            "changed": changed,
            "resume": response_text[:200],
            "sources": [r.get("url", "") for r in resultats]
        }


def _appeler_llm(prompt: str) -> str:
    """
    Appelle le LLM selon le mode configuré (local ou cloud).
    Utilisé pour analyser les résultats de veille.

    Paramètre :
    - prompt : texte à envoyer au LLM

    Retourne :
    - réponse du LLM (str)
    """
    # La veille porte sur des données publiques — on utilise toujours
    # le cloud en priorité pour la rapidité (pas de données sensibles)
    if MISTRAL_API_KEY:
        headers = {
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": MISTRAL_MODEL,
            "messages": [{"role": "user", "content": prompt}]
        }
        try:
            r = requests.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
        except Exception:
            pass

    # Fallback local
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }
    try:
        r = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
            timeout=120
        )
        if r.status_code == 200:
            return r.json()["message"]["content"]
    except Exception as e:
        return f'{{"changed": false, "resume": "Erreur LLM : {e}"}}'

    return '{"changed": false, "resume": "LLM indisponible"}'


# ── Pipeline de veille ────────────────────────────────────────────────────────

def lancer_veille() -> dict:
    """
    Lance le pipeline de veille complet sur tous les sujets configurés.

    Workflow :
    1. Charge les sujets de veille
    2. Vérifie le quota Tavily
    3. Pour chaque sujet : recherche Tavily + analyse LLM
    4. Sauvegarde les résultats dans data/veille/YYYY-MM-DD.json
    5. Met à jour le compteur de requêtes

    Retourne un dict :
    {
      "date"          : date du jour (str),
      "nb_sujets"     : nombre de sujets traités (int),
      "nb_changements": nombre de changements détectés (int),
      "resultats"     : liste de résultats par sujet,
      "quota"         : état du compteur Tavily,
      "error"         : message d'erreur global ou None
    }
    """
    os.makedirs(VEILLE_FOLDER, exist_ok=True)
    date_jour = datetime.now().strftime("%Y-%m-%d")
    heure = datetime.now().strftime("%H:%M")

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return {"error": "Clé API Tavily manquante dans .env (TAVILY_API_KEY)"}

    sujets = load_sujets()
    compteur = load_compteur()

    # Vérification quota
    requetes_restantes = TAVILY_QUOTA_MENSUEL - compteur["requetes"]
    if requetes_restantes < len(sujets):
        return {
            "error": f"Quota Tavily insuffisant : {requetes_restantes} requêtes restantes, "
                     f"{len(sujets)} nécessaires. Quota mensuel : {TAVILY_QUOTA_MENSUEL}."
        }

    resultats = []
    nb_changements = 0

    for sujet in sujets:
        print(f"Recherche : {sujet}")

        # Recherche Tavily
        recherche = rechercher_sujet(sujet, api_key)
        increment_compteur(1)

        if recherche["error"]:
            resultats.append({
                "sujet": sujet,
                "changed": False,
                "resume": f"Erreur recherche : {recherche['error']}",
                "sources": [],
                "error": recherche["error"]
            })
            continue

        # Analyse LLM
        analyse = analyser_changement(sujet, recherche["resultats"])
        if analyse.get("changed"):
            nb_changements += 1

        resultats.append({
            "sujet": sujet,
            "changed": analyse.get("changed", False),
            "resume": analyse.get("resume", ""),
            "sources": analyse.get("sources", []),
            "error": None
        })

    # Sauvegarde des résultats
    rapport = {
        "date": date_jour,
        "heure": heure,
        "nb_sujets": len(sujets),
        "nb_changements": nb_changements,
        "resultats": resultats,
        "quota": load_compteur()
    }

    filepath = os.path.join(VEILLE_FOLDER, f"{date_jour}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(rapport, f, ensure_ascii=False, indent=2)

    print(f"Veille terminée : {nb_changements} changement(s) détecté(s) sur {len(sujets)} sujets")
    return rapport


# ── Historique ────────────────────────────────────────────────────────────────

def load_historique(nb_jours: int = 30) -> list[dict]:
    """
    Charge les rapports de veille des derniers jours.

    Paramètre :
    - nb_jours : nombre de jours d'historique à charger (défaut : 30)

    Retourne :
    - liste de rapports triés du plus récent au plus ancien
    """
    if not os.path.exists(VEILLE_FOLDER):
        return []

    rapports = []
    fichiers = sorted([
        f for f in os.listdir(VEILLE_FOLDER)
        if f.endswith(".json") and f != "sujets.json" and f != "compteur.json"
    ], reverse=True)[:nb_jours]

    for fichier in fichiers:
        filepath = os.path.join(VEILLE_FOLDER, fichier)
        with open(filepath, "r", encoding="utf-8") as f:
            rapports.append(json.load(f))

    return rapports


def effacer_historique() -> None:
    """
    Efface tous les rapports de veille.
    À utiliser après avoir déposé les nouveaux fichiers mis à jour.
    Conserve le fichier de configuration des sujets et le compteur.
    """
    if not os.path.exists(VEILLE_FOLDER):
        return

    for fichier in os.listdir(VEILLE_FOLDER):
        if fichier.endswith(".json") and fichier not in ["sujets.json", "compteur.json"]:
            os.remove(os.path.join(VEILLE_FOLDER, fichier))
            print(f"Supprimé : {fichier}")

    print("Historique de veille effacé.")


# ── Planificateur de tâches Windows à configurer─────────────────────────────────────────────────────────────