"""
collecte.py
Onglet Collecte — Keepinbot
=============================

Interface du Module 1 — Indexation de documents publics dans la base RAG.

─── Source A — Dépôt manuel (seule source validée) ───────────────────

L'utilisateur télécharge les PDFs depuis son navigateur et les dépose
dans data/public/. Cliquez sur "Indexer les PDFs en attente" pour les intégrer à la base.

─── Source B — URL directe (expérimentale) ───────────────────────────

Tente de télécharger un PDF depuis une URL saisie manuellement.
Non opérationnelle sur les sites gouvernementaux français (Cloudflare,
protections anti-bot). Peut fonctionner sur des serveurs sans protection :
intranets d'entreprise, serveurs internes, sites partenaires.
En cas d'échec, télécharger le PDF manuellement et utiliser la Source A.

─── Affichage ────────────────────────────────────────────────────────

- Nombre de PDFs en attente d'indexation
- Nombre de documents publics indexés
- Liste des documents indexés

─── Avertissement ────────────────────────────────────────────────────

La législation française (Code du travail, SMIC, conventions collectives)
évolue plusieurs fois par an. La fraîcheur des documents est de la
responsabilité de l'utilisateur. Une mise à jour manuelle du corpus
est recommandée au minimum tous les 3 mois.
"""

import streamlit as st
import os
from app.core.collector import (
    index_folder,
    index_from_url,
    PUBLIC_FOLDER,
    INDEXED_FOLDER
)


def render_collecte():
    """
    Rendu de l'onglet Collecte.
    """
    st.subheader("Collecte de documents réglementaires")
    st.caption("Déposez vos PDFs dans le dossier de collecte et indexez-les manuellement.")

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
    st.caption(
        "⚠️ **Limitations connues** : les sites gouvernementaux français "
        "(Légifrance, URSSAF, service-public.fr) bloquent les requêtes "
        "automatiques. Cette source fonctionne uniquement sur des URLs "
        "sans protection anti-bot (intranets, serveurs internes, sites partenaires)."
    )

    url_input = st.text_input(
        "URL du PDF",
        placeholder="https://votre-serveur-interne/document.pdf"
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
                st.info(
                    "Le téléchargement a échoué — probablement bloqué par le serveur. "
                    "Téléchargez le PDF manuellement depuis votre navigateur "
                    "et déposez-le dans le dossier via la Source A."
                )
            else:
                st.success(f"Indexé : {result['source']} — {result['pages']} page(s)")
                st.rerun()

    st.divider()


    # ── Liste des documents indexés ───────────────────────────────────────────
    st.markdown("### Documents publics indexés")

    if indexed:
        for filename in sorted(indexed):
            st.caption(f"🟢 {filename}")
    else:
        st.info("Aucun document public indexé pour le moment.")