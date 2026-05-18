"""
Routeur hybride de Keepinbot
============================
Analyse les chunks récupérés par le retrieval et décide
quel moteur LLM utiliser pour générer la réponse :
- Chunks publics uniquement  → cloud (API Mistral)
- Chunks internes uniquement → local (Ollama + Phi3)
- Chunks mixtes              → les deux retrievals, génération en local

Principe de sécurité : dès qu'un chunk interne est impliqué,
la génération reste en local — les données sensibles
ne sortent jamais de la machine.
"""

import requests
from app.core.config import (
    LLM_MODE,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    MISTRAL_API_KEY,
    MISTRAL_MODEL
)

# ── System prompt ─────────────────────────────────────────────────────────────
# Instructions permanentes envoyées au LLM à chaque appel.
# Version renforcée pour contraindre les modèles plus petits (Phi3)
# à rester dans les documents sans dériver.
SYSTEM_PROMPT = """Tu es un assistant documentaire pour une PME.
Règles strictes :
1. Réponds UNIQUEMENT avec les informations présentes dans le contexte fourni.
2. Si l'information n'est pas dans le contexte, réponds exactement : "Je ne trouve pas cette information dans les documents."
3. Ne fais aucune supposition, aucune recommandation générale, aucun ajout.
4. Cite le nom du document source entre parenthèses à la fin de ta réponse.
5. Maximum 3 phrases. Pas de liste à puces."""


def detect_route(chunks: list[dict]) -> str:
    """
    Analyse les types des chunks récupérés et détermine le mode de routage.

    Paramètre :
    - chunks : liste de dicts retournée par retrieve()
               chaque dict contient un champ "type" : "public" ou "interne"

    Retourne une chaîne parmi :
    - "local"  : tous les chunks sont internes → Ollama
    - "cloud"  : tous les chunks sont publics → API Mistral
    - "hybrid" : chunks mixtes → fusion, génération en local

    Règle de sécurité :
    Si LLM_MODE est forcé à "local" dans config.py (ex: développement),
    on ignore le routage et on envoie tout en local.
    """
    # Si le mode est forcé en local, on n'envoie rien sur le cloud
    if LLM_MODE == "local":
        return "local"

    types = set(c["type"] for c in chunks)

    if types == {"public"}:
        return "cloud"
    elif types == {"interne"}:
        return "local"
    else:
        # Mélange public + interne → hybride, génération locale par sécurité
        return "hybrid"


def build_context(chunks: list[dict]) -> str:
    """
    Assemble les chunks en un bloc de contexte lisible pour le LLM.
    Chaque chunk est présenté avec sa source et son type.

    Paramètre :
    - chunks : liste de dicts avec "content", "source", "type"

    Retourne :
    - chaîne de caractères prête à être injectée dans le prompt
    """
    return "\n\n".join([
        f"[Source : {c['source']} — {c['type']}]\n{c['content']}"
        for c in chunks
    ])


def generate_local(question: str, chunks: list[dict]) -> str:
    """
    Génère une réponse via Ollama (LLM local).
    Utilisé pour les données internes et les cas hybrides.
    Zéro appel externe — les données restent sur la machine.

    Paramètres :
    - question : question de l'utilisateur
    - chunks   : chunks récupérés par le retrieval

    Retourne :
    - réponse générée (str) ou message d'erreur
    """
    context = build_context(chunks)
    prompt = f"Contexte :\n{context}\n\nQuestion : {question}\n\nRéponds en français."

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
            timeout=120  # 2 minutes max — génération CPU peut être lente
        )
        if response.status_code == 200:
            return response.json()["message"]["content"]
        else:
            return f"Erreur Ollama : {response.status_code}"
    except requests.exceptions.ConnectionError:
        return "Erreur : Ollama n'est pas disponible. Lance Ollama et réessaie."
    except requests.exceptions.Timeout:
        return "Erreur : délai dépassé. Ollama met trop de temps à répondre."


def generate_cloud(question: str, chunks: list[dict]) -> str:
    """
    Génère une réponse via l'API Mistral (cloud).
    Utilisé uniquement pour les données publiques (réglementaires).
    Nécessite une clé API dans le fichier .env.

    Paramètres :
    - question : question de l'utilisateur
    - chunks   : chunks récupérés par le retrieval (type "public" uniquement)

    Retourne :
    - réponse générée (str) ou message d'erreur
    """
    if not MISTRAL_API_KEY:
        return "Erreur : clé API Mistral manquante dans le fichier .env"

    context = build_context(chunks)
    prompt = f"Contexte :\n{context}\n\nQuestion : {question}\n\nRéponds en français."

    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MISTRAL_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"Erreur API Mistral : {response.status_code}"
    except requests.exceptions.Timeout:
        return "Erreur : délai dépassé sur l'API Mistral."


def route_and_generate(question: str, chunks: list[dict]) -> dict:
    """
    Fonction principale du routeur.
    Détermine le mode, génère la réponse et retourne le tout.

    Paramètres :
    - question : question de l'utilisateur
    - chunks   : chunks récupérés par retrieve()

    Retourne un dict :
    {
      "response" : réponse générée (str),
      "route"    : mode utilisé ("local", "cloud", "hybrid"),
      "sources"  : liste des sources utilisées
    }
    """
    route = detect_route(chunks)
    print(f"  Routeur → {route}")

    if route == "cloud":
        response = generate_cloud(question, chunks)
    else:
        # local ou hybrid → génération locale par sécurité
        response = generate_local(question, chunks)

    sources = list(set(c["source"] for c in chunks))

    return {
        "response": response,
        "route": route,
        "sources": sources
    }