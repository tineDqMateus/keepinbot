"""
main.py
Keepinbot — Point d'entrée de l'application Streamlit
======================================================
Lance l'interface avec : streamlit run app/main.py
Quatre onglets :
- Assistant    : chatbot RAG avec citations sources
- Documentation: génération de documents (Module 2 — J6-J7)
- Collecte     : veille réglementaire automatisée (Module 1 — J8)
- Administration: pilotage des services Docker (J9)
"""

import streamlit as st

# Configuration de la page — doit être le premier appel Streamlit
st.set_page_config(
    page_title="Keepinbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Import des onglets
from app.tabs.assistant import render_assistant
from app.tabs.documentation import render_documentation
from app.tabs.collecte import render_collecte
from app.tabs.admin import render_admin

# ── En-tête ───────────────────────────────────────────────────────────────────
st.title("Keepinbot")
st.caption("Plutôt que de tout garder à l'esprit, on charge le bot.")
st.divider()

# ── Navigation par onglets ────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "Assistant",
    "Documentation",
    "Collecte",
    "Administration"
])

with tab1:
    render_assistant()

with tab2:
    render_documentation()

with tab3:
    render_collecte()

with tab4:
    render_admin()