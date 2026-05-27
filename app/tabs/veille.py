"""
veille.py
Onglet Veille réglementaire — Keepinbot
========================================

Affiche les résultats de la veille quotidienne automatique.
Recherche web via API Tavily + analyse LLM pour détecter
les modifications réglementaires.

Fonctionnement :
- Veille lancée automatiquement tous les jours à 6h (paramétrable)
- Résultats affichés par date avec indicateur de changement
- Historique conservé jusqu'à effacement manuel
- Effacement recommandé après dépôt des nouveaux documents
"""

import streamlit as st
import os
from app.core.veille import (
    load_historique,
    load_sujets,
    save_sujets,
    load_compteur,
    effacer_historique,
    lancer_veille,
    TAVILY_QUOTA_MENSUEL,
    TAVILY_ALERTE_SEUIL,
    VEILLE_SUJETS_DEFAUT
)


def render_veille():
    """
    Rendu de l'onglet Veille réglementaire.
    """
    st.subheader("Veille réglementaire")
    st.caption(
        "Surveillance automatique quotidienne des modifications réglementaires. "
        "Lancée tous les jours à 6h via API Tavily + analyse par IA."
    )

    # ── Quota Tavily ──────────────────────────────────────────────────────────
    compteur = load_compteur()
    requetes = compteur.get("requetes", 0)
    mois = compteur.get("mois", "")
    pct = int(requetes / TAVILY_QUOTA_MENSUEL * 100)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Requêtes ce mois", f"{requetes} / {TAVILY_QUOTA_MENSUEL}")
    with col2:
        st.metric("Quota utilisé", f"{pct}%")
    with col3:
        st.metric("Mois", mois)

    if requetes >= TAVILY_ALERTE_SEUIL:
        st.warning(
            f"⚠️ Quota Tavily à {pct}% — {TAVILY_QUOTA_MENSUEL - requetes} requêtes restantes. "
            "Passez sur un plan payant si nécessaire (app.tavily.com)."
        )

    st.divider()

    # ── Historique des rapports ───────────────────────────────────────────────
    historique = load_historique(nb_jours=30)

    if not historique:
        st.info(
            "Aucun rapport de veille disponible. "
            "La veille se lance automatiquement tous les jours à 6h. "
            "Vérifiez que la clé API Tavily est configurée dans le fichier .env."
        )
    else:
        # Sélecteur de date
        dates = [r["date"] for r in historique]
        date_selectionnee = st.selectbox(
            "Rapport du",
            options=dates,
            format_func=lambda d: f"{d} — "
                + next((f"{r['nb_changements']} changement(s)" for r in historique if r["date"] == d), "")
        )

        # Rapport sélectionné
        rapport = next((r for r in historique if r["date"] == date_selectionnee), None)

        if rapport:
            st.caption(
                f"Veille du {rapport['date']} à {rapport.get('heure', '--')} — "
                f"{rapport['nb_sujets']} sujets — "
                f"{rapport['nb_changements']} changement(s) détecté(s)"
            )

            st.divider()

            # Résultats par sujet
            for r in rapport["resultats"]:
                if r.get("changed"):
                    # Changement détecté — affiché en rouge/gras
                    st.error(
                        f"🔴 **{r['sujet']}**\n\n{r['resume']}"
                    )
                    if r.get("sources"):
                        for url in r["sources"]:
                            if url:
                                st.caption(f"🔗 {url}")
                else:
                    # Pas de changement — affiché normalement
                    st.success(
                        f"🟢 {r['sujet']} — {r.get('resume', 'Pas de modification détectée.')}"
                    )

                    if r.get("error"):
                        st.caption(f"⚠️ Erreur : {r['error']}")

    st.divider()

    # ── Actions ───────────────────────────────────────────────────────────────
    st.markdown("### Actions")

    col1, col2 = st.columns(2)

    with col1:
        st.caption("**Effacer l'historique**")
        st.caption(
            "À utiliser après avoir déposé les nouveaux documents "
            "dans l'onglet Collecte."
        )
        if st.button("Effacer l'historique de veille", type="secondary"):
            effacer_historique()
            st.success("Historique effacé.")
            st.rerun()

    with col2:
        st.caption("**Configuration**")
        st.caption("Sujets de veille configurés :")
        sujets = load_sujets()
        for s in sujets:
            st.caption(f"• {s}")

    st.divider()

    # ── Avertissement fraîcheur ───────────────────────────────────────────────
    st.warning(
        "⚠️ La veille détecte les changements réglementaires mais ne met pas "
        "automatiquement à jour les documents de la base. "
        "En cas de changement détecté, téléchargez les nouveaux textes "
        "et déposez-les dans l'onglet Collecte, puis effacez l'historique."
    )