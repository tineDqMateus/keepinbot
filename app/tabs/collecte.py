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
    PUBLIC_FOLDER,
    INDEXED_FOLDER,
    ARCHIVE_FOLDER
)


def render_collecte():
    """
    Rendu de l'onglet Collecte Réglementation.
    """
    st.subheader("Collecte Réglementation")
    st.caption(
        "Déposez vos PDFs réglementaires dans le dossier `data/public/` "
        "puis cliquez sur Indexer pour les intégrer à la base de recherche."
    )
    st.info(
        "💡 **Workflow recommandé :**\n\n"
        "1. Consultez l'onglet **Veille** pour identifier les changements détectés\n"
        "2. Téléchargez les documents depuis les liens officiels fournis\n"
        "3. Déposez les PDFs dans `data/public/`\n"
        "4. Cliquez sur **Indexer** ci-dessous\n"
        "5. Retournez dans **Veille** et effacez l'historique"
    )

    st.caption(
    "💡 Après indexation, les fichiers sont automatiquement déplacés "
    "dans `data/public/indexed/` — ils restent valables jusqu'à remplacement. "
    "Déposez uniquement les documents signalés comme modifiés par la veille, "
    "en conservant le même nom de fichier que la version existante."
    )

    st.divider()

    # ── État ──────────────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    pending = []
    if os.path.exists(PUBLIC_FOLDER):
        pending = [f for f in os.listdir(PUBLIC_FOLDER) if f.endswith(".pdf")]

    indexed = []
    if os.path.exists(INDEXED_FOLDER):
        indexed = os.listdir(INDEXED_FOLDER)

    with col1:
        st.metric("PDFs en attente", len(pending))
    with col2:
        st.metric("Documents indexés", len(indexed))

    st.divider()

    # ── Indexation ────────────────────────────────────────────────────────────
    st.markdown("### Indexer les PDFs")

    if pending:
        st.info(f"{len(pending)} PDF(s) en attente : {', '.join(pending)}")
    else:
        st.caption("Aucun PDF en attente dans `data/public/`.")
        st.caption(
            "Déposez vos PDFs dans ce dossier depuis l'explorateur Windows, "
            "puis cliquez sur Indexer."
        )

    if st.button("Indexer les PDFs en attente", type="primary"):
        if not pending:
            st.warning("Aucun PDF à indexer — déposez d'abord des fichiers dans `data/public/`.")
        else:
            with st.spinner("Indexation en cours..."):
                results = index_folder()
            if results:
                st.success(f"{len(results)} document(s) indexé(s) avec succès.")
                for r in results:
                    st.caption(f"✓ {r['source']} — {r['pages']} page(s)")
                st.rerun()
            else:
                st.error("Aucun document indexé — vérifier les fichiers.")

    st.divider()

    # ── Documents indexés ─────────────────────────────────────────────────────
    st.markdown("### Documents indexés")

    if indexed:
        for filename in sorted(indexed):
            st.caption(f"🟢 {filename}")
    else:
        st.info("Aucun document réglementaire indexé pour le moment.")

    # ── Archive ───────────────────────────────────────────────────────────────
    archive = []
    if os.path.exists(ARCHIVE_FOLDER):
        archive = os.listdir(ARCHIVE_FOLDER)

    if archive:
        st.divider()
        st.markdown("### Archive")
        st.caption(f"{len(archive)} version(s) archivée(s) dans `data/public/archive/`")
        with st.expander("Voir les versions archivées"):
            for filename in sorted(archive, reverse=True):
                st.caption(f"📦 {filename}")

    # ── Avertissement ─────────────────────────────────────────────────────────
    st.divider()
    st.warning(
        "⚠️ La législation française évolue plusieurs fois par an. "
        "Consultez régulièrement l'onglet **Veille** pour détecter "
        "les modifications et mettre à jour vos documents."
    )