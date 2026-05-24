"""
tabs/admin.py
Onglet Administration — Keepinbot
===================================
Interface de pilotage des services depuis le navigateur.

Fonctionnalités :
- État des services (Ollama, ChromaDB, mode LLM)
- Démarrage/arrêt du planificateur de collecte
- Statistiques de la base documentaire
- Configuration du mode LLM (local/cloud)
"""

import streamlit as st
import os
import requests
from app.core.config import (
    OLLAMA_BASE_URL, OLLAMA_MODEL, MISTRAL_MODEL,
    LLM_MODE, CHROMA_PATH, CORPUS_PATH
)
from app.core.collector import PUBLIC_FOLDER, INDEXED_FOLDER


def check_ollama() -> dict:
    """
    Vérifie l'état d'Ollama et retourne les informations du modèle chargé.

    Retourne un dict :
    {
      "available" : True si Ollama répond (bool),
      "model"     : nom du modèle chargé (str),
      "error"     : message d'erreur ou None
    }
    """
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_name = models[0]["name"] if models else "Aucun modèle"
            return {"available": True, "model": model_name, "error": None}
        return {"available": False, "model": None, "error": f"Status {response.status_code}"}
    except Exception as e:
        return {"available": False, "model": None, "error": str(e)}


def get_corpus_stats() -> dict:
    """
    Calcule les statistiques de la base documentaire.

    Retourne un dict :
    {
      "corpus_count"  : nombre de documents dans data/corpus/ (int),
      "public_count"  : nombre de PDFs indexés dans data/public/indexed/ (int),
      "pending_count" : nombre de PDFs en attente dans data/public/ (int),
      "chroma_exists" : True si le vectorstore ChromaDB existe (bool)
    }
    """
    corpus_count = len([
        f for f in os.listdir(CORPUS_PATH)
        if os.path.isfile(os.path.join(CORPUS_PATH, f))
    ]) if os.path.exists(CORPUS_PATH) else 0

    public_count = len(os.listdir(INDEXED_FOLDER)) if os.path.exists(INDEXED_FOLDER) else 0

    pending_count = len([
        f for f in os.listdir(PUBLIC_FOLDER)
        if f.endswith(".pdf")
    ]) if os.path.exists(PUBLIC_FOLDER) else 0

    chroma_exists = os.path.exists(CHROMA_PATH) and len(os.listdir(CHROMA_PATH)) > 0

    return {
        "corpus_count": corpus_count,
        "public_count": public_count,
        "pending_count": pending_count,
        "chroma_exists": chroma_exists
    }


def render_admin():
    """
    Rendu de l'onglet Administration.
    """
    st.subheader("Administration")
    st.caption("Pilotage des services et de la base documentaire.")

    # ── État des services ─────────────────────────────────────────────────────
    st.markdown("### État des services")

    col1, col2, col3 = st.columns(3)

    # Ollama
    ollama = check_ollama()
    with col1:
        if ollama["available"]:
            st.success(f"🟢 Ollama — {ollama['model']}")
        else:
            st.error(f"🔴 Ollama — indisponible")
            st.caption(ollama["error"])

    # ChromaDB
    stats = get_corpus_stats()
    with col2:
        if stats["chroma_exists"]:
            st.success("🟢 ChromaDB — opérationnel")
        else:
            st.error("🔴 ChromaDB — vectorstore absent")

    # Mode LLM
    with col3:
        if LLM_MODE == "local":
            st.info(f"🟣 Mode : local ({OLLAMA_MODEL})")
        else:
            st.info(f"🟢 Mode : cloud ({MISTRAL_MODEL})")

    st.divider()

    # ── Statistiques base documentaire ───────────────────────────────────────
    st.markdown("### Base documentaire")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Documents internes", stats["corpus_count"])
    with col2:
        st.metric("Documents publics indexés", stats["public_count"])
    with col3:
        st.metric("PDFs en attente", stats["pending_count"])

    st.divider()

    # ── Documents indexés ─────────────────────────────────────────────────────
    st.markdown("### Documents dans la base")

    col1, col2 = st.columns(2)

    with col1:
        st.caption("**Documents internes** (data/corpus/)")
        if os.path.exists(CORPUS_PATH):
            files = [f for f in os.listdir(CORPUS_PATH) if os.path.isfile(os.path.join(CORPUS_PATH, f))]
            for f in sorted(files):
                icon = "🟢" if f.startswith(("code_", "legal_", "urssaf_")) else "🟣"
                st.caption(f"{icon} {f}")

    with col2:
        st.caption("**Documents publics indexés** (data/public/indexed/)")
        if os.path.exists(INDEXED_FOLDER):
            files = os.listdir(INDEXED_FOLDER)
            for f in sorted(files):
                st.caption(f"🟢 {f}")
        else:
            st.caption("Aucun document public indexé.")

    st.divider()

    # ── Actions de maintenance ────────────────────────────────────────────────
    st.markdown("### Maintenance")

    col1, col2 = st.columns(2)

    with col1:
        st.caption("**Reconstruire le vectorstore**")
        st.caption("À utiliser après ajout manuel de documents dans data/corpus/")
        if st.button("Reconstruire ChromaDB", type="secondary"):
            with st.spinner("Reconstruction en cours..."):
                try:
                    import shutil
                    from app.core.rag import load_documents, chunk_documents, build_vectorstore
                    from app.core.collector import parse_pdf

                    # Suppression et reconstruction
                    if os.path.exists(CHROMA_PATH):
                        shutil.rmtree(CHROMA_PATH)

                    docs = load_documents(CORPUS_PATH)
                    chunks = chunk_documents(docs)
                    build_vectorstore(chunks)

                    # Réindexation des PDFs publics
                    if os.path.exists(INDEXED_FOLDER):
                        for pdf in os.listdir(INDEXED_FOLDER):
                            if pdf.endswith(".pdf"):
                                result = parse_pdf(os.path.join(INDEXED_FOLDER, pdf))
                                if not result["error"]:
                                    chunks = chunk_documents([result])
                                    build_vectorstore(chunks)

                    st.success("Vectorstore reconstruit avec succès.")
                    # Reset du vectorstore en session
                    if "vectorstore" in st.session_state:
                        del st.session_state["vectorstore"]
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")

    with col2:
        st.caption("**Vider l'historique de chat**")
        st.caption("Efface la conversation en cours dans l'onglet Assistant")
        if st.button("Vider le chat", type="secondary"):
            st.session_state.messages = []
            st.success("Historique effacé.")

    st.divider()

    # ── Informations système ──────────────────────────────────────────────────
    st.markdown("### Informations système")
    st.caption(f"CHROMA_PATH : `{CHROMA_PATH}`")
    st.caption(f"CORPUS_PATH : `{CORPUS_PATH}`")
    st.caption(f"PUBLIC_FOLDER : `{PUBLIC_FOLDER}`")
    st.caption(f"OLLAMA_BASE_URL : `{OLLAMA_BASE_URL}`")
    st.caption(f"LLM_MODE : `{LLM_MODE}`")