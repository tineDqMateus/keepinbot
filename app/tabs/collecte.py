"""
collecte.py
Onglet Collecte — Keepinbot
=============================
Interface du Module 1 — Collecte automatique de documents publics.

Trois modes de collecte :
- Source A : dépôt manuel de PDFs dans data/public/
- Source B : téléchargement depuis une URL directe
- Source C : API Légifrance (nécessite une clé API)

Affiche également l'état de la collecte :
- Documents déjà indexés
- Prochaine exécution planifiée
"""

import streamlit as st
import os
from app.core.collector import (
    index_folder,
    index_from_url,
    index_from_legifrance,
    PUBLIC_FOLDER,
    INDEXED_FOLDER
)


def render_collecte():
    """
    Rendu de l'onglet Collecte.
    """
    st.subheader("Collecte de documents réglementaires")
    st.caption("Indexez automatiquement des documents publics dans la base RAG.")

    # ── État de la collecte ───────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        # Documents en attente d'indexation
        pending = []
        if os.path.exists(PUBLIC_FOLDER):
            pending = [f for f in os.listdir(PUBLIC_FOLDER) if f.endswith(".pdf")]
        st.metric("PDFs en attente", len(pending))

    with col2:
        # Documents déjà indexés
        indexed = []
        if os.path.exists(INDEXED_FOLDER):
            indexed = os.listdir(INDEXED_FOLDER)
        st.metric("Documents indexés", len(indexed))

    st.divider()

    # ── Source A — Dossier surveillé ──────────────────────────────────────────
    st.markdown("### Source A — Dépôt de PDFs")
    st.caption(f"Déposez vos PDFs dans `{PUBLIC_FOLDER}` puis cliquez sur Indexer.")

    if pending:
        st.info(f"{len(pending)} PDF(s) en attente : {', '.join(pending)}")
        if st.button("Indexer les PDFs en attente", type="primary"):
            with st.spinner("Indexation en cours..."):
                results = index_folder()
            if results:
                st.success(f"{len(results)} document(s) indexé(s) avec succès.")
                for r in results:
                    st.caption(f"✓ {r['source']} — {r['pages']} page(s)")
                st.rerun()
            else:
                st.error("Aucun document indexé — vérifier les fichiers.")
    else:
        st.info(f"Aucun PDF en attente dans `{PUBLIC_FOLDER}`.")

    st.divider()

    # ── Source B — URL directe ────────────────────────────────────────────────
    st.markdown("### Source B — Téléchargement depuis une URL")
    st.caption("Entrez l'URL directe d'un PDF public accessible.")

    url_input = st.text_input(
        "URL du PDF",
        placeholder="https://exemple.gouv.fr/document.pdf"
    )
    filename_input = st.text_input(
        "Nom du fichier (optionnel)",
        placeholder="document_public.pdf"
    )

    if url_input:
        if st.button("Télécharger et indexer", type="primary"):
            with st.spinner(f"Téléchargement de {url_input}..."):
                result = index_from_url(
                    url_input,
                    filename_input if filename_input else None
                )
            if result.get("error"):
                st.error(f"Erreur : {result['error']}")
                st.info("Conseil : si l'URL est bloquée, téléchargez le PDF manuellement et utilisez la Source A.")
            else:
                st.success(f"Indexé : {result['source']} — {result['pages']} page(s)")
                st.rerun()

    st.divider()

    # ── Source C — API Légifrance ─────────────────────────────────────────────
    st.markdown("### Source C — API Légifrance")
    st.caption("Recherchez des textes réglementaires via l'API officielle Légifrance.")

    legifrance_key = os.getenv("LEGIFRANCE_API_KEY")

    if not legifrance_key:
        st.warning(
            "Clé API Légifrance non configurée. "
            "Inscription gratuite sur [piste.gouv.fr](https://piste.gouv.fr). "
        )
    else:
        search_input = st.text_input(
            "Terme de recherche",
            placeholder="Ex : contrat de travail, préavis, congés payés..."
        )
        if search_input:
            if st.button("Rechercher et indexer", type="primary"):
                with st.spinner(f"Recherche Légifrance : {search_input}..."):
                    results = index_from_legifrance(search_input, legifrance_key)
                errors = [r for r in results if r.get("error")]
                success = [r for r in results if not r.get("error")]
                if success:
                    st.success(f"{len(success)} texte(s) indexé(s) depuis Légifrance.")
                if errors:
                    for e in errors:
                        st.error(e["error"])

    st.divider()

    # ── Liste des documents indexés ───────────────────────────────────────────
    st.markdown("### Documents publics indexés")

    if indexed:
        for filename in sorted(indexed):
            st.caption(f"🟢 {filename}")
    else:
        st.info("Aucun document public indexé pour le moment.")