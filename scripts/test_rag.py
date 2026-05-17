"""
test_rag.py — Test du pipeline RAG complet de Keepinbot
=======================================================
Ce script valide la chaîne complète :
  question → retrieval → génération LLM → réponse sourcée

Rôle dans le projet :
Script de développement — pas utilisé en production.
Permet de tester et d'itérer sur le prompt système et les paramètres RAG
sans passer par l'interface Streamlit.

Utilisation :
  PYTHONPATH=. python scripts/test_rag.py
"""

import requests
import json
from app.core.rag import load_vectorstore, retrieve
from app.core.config import OLLAMA_BASE_URL, OLLAMA_MODEL


# ── System prompt ─────────────────────────────────────────────────────────────
# Le system prompt est l'instruction permanente donnée au LLM.
# Il définit son rôle, ses contraintes et son comportement par défaut.
# C'est un livrable à part entière — il se teste et s'itère comme du code.
#
# Choix de conception :
# - "Réponds uniquement à partir des documents fournis" → réduit les hallucinations
# - "Si la réponse ne se trouve pas dans les documents, dis-le" → transparence
# - "Cite toujours le document source" → traçabilité pour l'utilisateur
# - "Sois concis et précis" → évite les réponses verbeuses du LLM
SYSTEM_PROMPT = """Tu es un assistant documentaire pour une PME.
Réponds uniquement à partir des documents fournis dans le contexte.
Si la réponse ne se trouve pas dans les documents, dis-le explicitement.
Cite toujours le document source dans ta réponse.
Sois concis et précis."""


def generate_response(question: str, chunks: list[dict]) -> str:
    """
    Envoie la question et le contexte extrait à Ollama et retourne la réponse.

    Principe du RAG :
    On ne demande pas au LLM de répondre de mémoire.
    On lui fournit les passages pertinents extraits des documents
    et on lui demande de construire sa réponse à partir de ces passages.
    C'est comme donner à un consultant le dossier complet juste avant
    la réunion — il répond sur le cas précis sans avoir été formé dessus.

    Construction du prompt utilisateur :
    Le contexte est injecté avant la question sous la forme :
      [Source : nom_du_fichier]
      contenu du chunk
    Cette structure permet au LLM d'identifier et de citer ses sources.

    Paramètres :
    - question : question posée par l'utilisateur en langage naturel
    - chunks   : liste de dicts retournée par retrieve()
                 chaque dict contient "content" et "source"

    Retourne :
    - réponse générée par le LLM (str)
    - message d'erreur si Ollama ne répond pas
    """
    # Assemblage du contexte : on concatène les chunks avec leur source
    # Ce contexte sera injecté dans le prompt envoyé au LLM
    context = "\n\n".join([
        f"[Source : {c['source']}]\n{c['content']}"
        for c in chunks
    ])

    # Prompt utilisateur : contexte + question
    # La séparation claire entre contexte et question aide le LLM
    # à distinguer ce qu'il doit lire de ce qu'il doit répondre
    prompt = f"""Contexte extrait des documents :
{context}

Question : {question}

Réponds en français à partir du contexte fourni."""

    # Format de la requête Ollama (API /api/chat)
    # "stream": False → on attend la réponse complète avant de l'afficher
    # En production (interface Streamlit), on utilisera stream=True
    # pour afficher la réponse mot par mot comme un vrai chatbot
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }

    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json=payload
    )

    if response.status_code == 200:
        return response.json()["message"]["content"]
    else:
        return f"Erreur Ollama : {response.status_code}"


def ask(question: str) -> None:
    """
    Fonction principale du pipeline RAG.
    Orchestre les étapes : chargement vectorstore → retrieval → génération.

    Étapes :
    1. Charge le vectorstore ChromaDB depuis le disque
    2. Retrouve les TOP_K chunks les plus pertinents pour la question
    3. Envoie question + chunks au LLM pour générer la réponse
    4. Affiche la réponse et les sources utilisées

    Paramètre :
    - question : question en langage naturel posée par l'utilisateur

    Note sur les sources affichées :
    On affiche les sources avec leur score de similarité pour permettre
    de diagnostiquer la qualité du retrieval — un score élevé (> 1.5)
    sur le premier chunk indique que la question ne correspond
    à aucun document du corpus.
    """
    print(f"\nQuestion : {question}")
    print("-" * 50)

    # Étape 1 — Chargement du vectorstore
    vectorstore = load_vectorstore()

    # Étape 2 — Retrieval : les chunks pertinents sont affichés
    # dans la console avec leur score (voir retrieve() dans rag.py)
    chunks = retrieve(question, vectorstore)

    print(f"\nChunks récupérés : {len(chunks)}")
    print("Génération de la réponse...")

    # Étape 3 — Génération : le LLM reçoit question + contexte
    response = generate_response(question, chunks)

    # Étape 4 — Affichage
    print(f"\nRéponse :\n{response}")
    print("\nSources utilisées :")
    for c in chunks:
        print(f"  - {c['source']} (score : {c['score']})")


# ── Questions de test ─────────────────────────────────────────────────────────
# Trois questions couvrant les trois documents du corpus synthétique :
# - procedure_rh.txt   → préavis, télétravail, congés, formation, mutuelle
# - fiche_produit.txt  → retours, garantie, SAV, livraison
# - faq_support.txt    → commandes, factures, paiement, modifications
if __name__ == "__main__":
    ask("Quel est le délai de préavis ?")
    ask("Comment retourner un produit ?")
    ask("Quelle est la politique de télétravail ?")