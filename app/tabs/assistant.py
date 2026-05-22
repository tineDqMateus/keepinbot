"""
assistant.py
Onglet Assistant — Keepinbot
=============================
Interface de chat RAG avec :
- Zone de saisie de question
- Affichage de la réponse générée
- Sources affichées avec couleur selon le type (public/interne)
- Indicateur de routage (local/cloud/hybrid)
- Upload de nouveaux documents
- Indicateur d'état des services
"""

import streamlit as st
import requests
import os
from app.core.rag import (
    load_vectorstore, retrieve,
    load_documents, chunk_documents, build_vectorstore
)
from app.core.router import route_and_generate
from app.core.config import CORPUS_PATH, OLLAMA_BASE_URL


def check_ollama() -> bool:
    """
    Vérifie qu'Ollama est accessible sur le port 11434.
    Retourne True si disponible, False sinon.
    """
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def render_assistant():
    """
    Rendu de l'onglet Assistant.
    Gère l'état de la conversation via st.session_state
    pour conserver l'historique entre les interactions.
    """

    # ── Initialisation de l'état de session ───────────────────────────────────
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "vectorstore" not in st.session_state:
        with st.spinner("Chargement de la base documentaire..."):
            try:
                st.session_state.vectorstore = load_vectorstore()
                st.success("Base documentaire chargée.", icon="✅")
            except Exception as e:
                st.error(f"Erreur chargement vectorstore : {e}")
                st.session_state.vectorstore = None

    # ── Layout : chat à gauche, infos à droite ────────────────────────────────
    col_chat, col_info = st.columns([3, 1])

    with col_chat:
        st.subheader("Posez votre question")

        # Affichage de l'historique des messages
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                if "sources" in msg and msg["sources"]:
                    st.caption(f"Sources : {', '.join(msg['sources'])}")
                if "route" in msg:
                    route = msg["route"]
                    color = "🟢" if route == "cloud" else "🟣" if route == "local" else "🟡"
                    st.caption(f"{color} Routage : {route}")

        # Zone de saisie
        question = st.chat_input("Votre question...")

        if question and st.session_state.vectorstore:
            st.session_state.messages.append({
                "role": "user",
                "content": question
            })

            with st.chat_message("user"):
                st.write(question)

            with st.chat_message("assistant"):
                with st.spinner("Recherche en cours..."):
                    chunks = retrieve(question, st.session_state.vectorstore)
                    result = route_and_generate(question, chunks)

                st.write(result["response"])

                if result["sources"]:
                    source_display = []
                    for chunk in chunks:
                        if chunk["source"] in result["sources"]:
                            color = "🟢" if chunk["type"] == "public" else "🟣"
                            source_display.append(f"{color} {chunk['source']}")
                    source_display = list(dict.fromkeys(source_display))
                    st.caption(f"Sources : {' · '.join(source_display)}")

                route = result["route"]
                color = "🟢" if route == "cloud" else "🟣" if route == "local" else "🟡"
                st.caption(f"{color} Routage : {route}")

            st.session_state.messages.append({
                "role": "assistant",
                "content": result["response"],
                "sources": result["sources"],
                "route": result["route"]
            })

        elif question and not st.session_state.vectorstore:
            st.error("Base documentaire non disponible.")

    with col_info:
        st.subheader("Documents")

        # ── Upload de nouveaux documents ──────────────────────────────────────
        uploaded = st.file_uploader(
            "Ajouter un document",
            type=["txt", "pdf"],
            help="Formats acceptés : .txt, .pdf"
        )

        if uploaded:
            save_path = f"{CORPUS_PATH}/{uploaded.name}"
            with open(save_path, "wb") as f:
                f.write(uploaded.getbuffer())
            st.success(f"Fichier ajouté : {uploaded.name}")

            with st.spinner("Mise à jour de la base..."):
                docs = load_documents(CORPUS_PATH)
                chunks = chunk_documents(docs)
                st.session_state.vectorstore = build_vectorstore(chunks)
            st.success("Base documentaire mise à jour.", icon="✅")

        # ── Liste des documents indexés ───────────────────────────────────────
        st.divider()
        st.caption("Documents indexés")
        if os.path.exists(CORPUS_PATH):
            files = [f for f in os.listdir(CORPUS_PATH) if f.endswith(".txt")]
            for f in files:
                icon = "🟢" if f.startswith(("code_", "legal_", "urssaf_")) else "🟣"
                st.caption(f"{icon} {f}")

        # ── État des services ─────────────────────────────────────────────────
        st.divider()
        st.caption("État des services")
        ollama_ok = check_ollama()
        st.caption(f"{'🟢' if ollama_ok else '🔴'} LLM local (Ollama)")
        st.caption("🟢 Base vectorielle (ChromaDB)")

    # ── Bouton reset conversation ─────────────────────────────────────────────
    if st.button("Nouvelle conversation"):
        st.session_state.messages = []
        st.rerun()