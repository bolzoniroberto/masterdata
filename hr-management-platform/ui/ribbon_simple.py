"""
Ribbon Interface Semplificato - Solo Streamlit Nativo
Nessun JavaScript, nessun iframe, nessun SecurityError
"""
import streamlit as st


def render_simple_ribbon():
    """
    Render ribbon usando solo componenti nativi Streamlit (st.button).

    Vantaggi:
    - Nessun SecurityError
    - Nessun iframe
    - Più veloce
    - Più manutenibile
    - Mobile-friendly nativo
    """
    # Inizializza session state se non esiste
    if 'active_ribbon_tab' not in st.session_state:
        st.session_state.active_ribbon_tab = 'Home'

    # Leggi parametro URL se presente (per link diretti)
    url_tab = st.query_params.get('active_ribbon_tab')
    if url_tab and url_tab != st.session_state.active_ribbon_tab:
        if url_tab in ["Home", "Gestione Dati", "Organigrammi", "Analisi", "Versioni"]:
            st.session_state.active_ribbon_tab = url_tab

    # Crea il ribbon con bottoni nativi
    st.markdown("""
    <style>
    /* Ribbon container */
    .ribbon-container {
        background: #1e293b;
        padding: 0.5rem 1rem;
        border-bottom: 2px solid #334155;
        margin-bottom: 1rem;
    }

    /* Nascondi label dei bottoni */
    div[data-testid="column"] > div > div > div > button {
        width: 100%;
        background: transparent;
        border: 1px solid transparent;
        color: #f1f5f9;
        padding: 0.75rem 1rem;
        font-size: 0.875rem;
        font-weight: 500;
        border-radius: 6px;
        transition: all 0.15s;
    }

    div[data-testid="column"] > div > div > div > button:hover {
        background: #334155;
        border-color: #475569;
    }

    /* Tab attivo */
    div[data-testid="column"] > div > div > div > button[kind="primary"] {
        background: #3b82f6 !important;
        color: white !important;
        border-color: #3b82f6 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Crea colonne per i tab
    col1, col2, col3, col4, col5 = st.columns(5)

    active_tab = st.session_state.active_ribbon_tab

    with col1:
        btn_type = "primary" if active_tab == "Home" else "secondary"
        if st.button("🏠 Home", key="ribbon_home", type=btn_type, use_container_width=True):
            st.session_state.active_ribbon_tab = "Home"
            st.query_params['active_ribbon_tab'] = "Home"
            st.rerun()

    with col2:
        btn_type = "primary" if active_tab == "Gestione Dati" else "secondary"
        if st.button("📊 Gestione Dati", key="ribbon_gestione", type=btn_type, use_container_width=True):
            st.session_state.active_ribbon_tab = "Gestione Dati"
            st.query_params['active_ribbon_tab'] = "Gestione Dati"
            st.rerun()

    with col3:
        btn_type = "primary" if active_tab == "Organigrammi" else "secondary"
        if st.button("🌳 Organigrammi", key="ribbon_org", type=btn_type, use_container_width=True):
            st.session_state.active_ribbon_tab = "Organigrammi"
            st.query_params['active_ribbon_tab'] = "Organigrammi"
            st.rerun()

    with col4:
        btn_type = "primary" if active_tab == "Analisi" else "secondary"
        if st.button("🔍 Analisi", key="ribbon_analisi", type=btn_type, use_container_width=True):
            st.session_state.active_ribbon_tab = "Analisi"
            st.query_params['active_ribbon_tab'] = "Analisi"
            st.rerun()

    with col5:
        btn_type = "primary" if active_tab == "Versioni" else "secondary"
        if st.button("📋 Versioni", key="ribbon_versioni", type=btn_type, use_container_width=True):
            st.session_state.active_ribbon_tab = "Versioni"
            st.query_params['active_ribbon_tab'] = "Versioni"
            st.rerun()

    # Divider
    st.markdown("---")
