"""
Ribbon Interface Sticky con Sottomenu
Ribbon moderna stile Office con tab + dropdown groups
"""
import streamlit as st


def render_sticky_ribbon():
    """
    Render ribbon sticky con sottomenu espandibili.

    Features:
    - Position: sticky (rimane in cima allo scroll)
    - Tab navigation con bottoni
    - Sottomenu espandibili per ogni gruppo di funzionalità
    - Organizzazione come da piano originale
    """
    # Inizializza session state
    if 'active_ribbon_tab' not in st.session_state:
        st.session_state.active_ribbon_tab = 'Home'
    if 'ribbon_submenu_open' not in st.session_state:
        st.session_state.ribbon_submenu_open = None

    # Leggi parametro URL se presente
    url_tab = st.query_params.get('active_ribbon_tab')
    if url_tab and url_tab != st.session_state.active_ribbon_tab:
        if url_tab in ["Home", "Gestione Dati", "Organigrammi", "Analisi", "Versioni", "Impostazioni"]:
            st.session_state.active_ribbon_tab = url_tab

    # CSS per ribbon sticky compatto
    st.markdown("""
    <style>
    /* RIMUOVI SPAZIO STREAMLIT DEFAULT */
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 1rem !important;
    }

    header[data-testid="stHeader"] {
        display: none !important;
    }

    /* Assicura che il main container non blocchi lo sticky */
    .main {
        overflow: visible !important;
    }

    section.main > div {
        overflow: visible !important;
    }

    /* Container ribbon sticky - NO SPAZIO SOPRA */
    .ribbon-sticky-container {
        position: sticky !important;
        top: 0 !important;
        z-index: 9999 !important;
        background: #1e293b !important;
        border-bottom: 1px solid #334155;
        padding: 0;
        margin: 0 !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.4) !important;
        width: 100% !important;
    }

    /* Tab bar - COMPATTO */
    .ribbon-tabs {
        display: flex;
        background: #0f172a;
        padding: 0.25rem 0.5rem;
        gap: 0.25rem;
        border-bottom: 1px solid #334155;
    }

    /* Ribbon content area - MOLTO COMPATTO */
    .ribbon-content {
        padding: 0.5rem;
        background: #1e293b;
        min-height: auto;
        max-height: 150px;
        overflow-y: auto;
    }

    /* Stile bottoni tab - COMPATTO */
    div[data-testid="column"] button {
        width: 100%;
        font-size: 0.8rem;
        padding: 0.35rem 0.75rem;
        border-radius: 4px;
        transition: all 0.1s;
    }

    /* Gruppi con bordo invece di expander */
    .ribbon-group {
        border: 1px solid #475569;
        border-radius: 4px;
        padding: 0.4rem;
        background: #0f172a;
        margin-bottom: 0.4rem;
    }

    .ribbon-group-title {
        font-size: 0.75rem;
        font-weight: 600;
        color: #94a3b8;
        margin-bottom: 0.3rem;
        padding-bottom: 0.2rem;
        border-bottom: 1px solid #334155;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Bottoni dentro gruppi - PIÙ COMPATTI */
    .ribbon-group button {
        margin-bottom: 0.25rem !important;
        padding: 0.3rem 0.6rem !important;
        font-size: 0.75rem !important;
    }

    /* Riduci spacing colonne */
    div[data-testid="column"] {
        padding: 0 0.25rem !important;
    }

    /* Riduci spacing expander se usati */
    .streamlit-expanderHeader {
        background: #263348 !important;
        border-radius: 4px;
        font-weight: 500;
        padding: 0.3rem 0.6rem !important;
        font-size: 0.75rem !important;
        min-height: auto !important;
    }

    .streamlit-expanderContent {
        padding: 0.3rem 0 !important;
    }

    /* Riduci spacing globale Streamlit */
    div[data-testid="stVerticalBlock"] > div {
        gap: 0.25rem !important;
    }

    /* Selectbox compatto */
    div[data-baseweb="select"] {
        margin-top: 0 !important;
        margin-bottom: 0 !important;
    }

    div[data-baseweb="select"] > div {
        padding: 0.3rem 0.5rem !important;
        font-size: 0.75rem !important;
    }

    /* Elimina spazi extra sotto ribbon */
    .ribbon-sticky-container + div {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }

    /* Info box più compatti */
    div[data-testid="stAlert"] {
        padding: 0.3rem 0.5rem !important;
        font-size: 0.75rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Container sticky
    with st.container():
        st.markdown('<div class="ribbon-sticky-container">', unsafe_allow_html=True)

        # === TAB BAR ===
        active_tab = st.session_state.active_ribbon_tab

        col1, col2, col3, col4, col5, col6 = st.columns(6)

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

        with col6:
            btn_type = "primary" if active_tab == "Impostazioni" else "secondary"
            if st.button("⚙️ Impostazioni", key="ribbon_settings", type=btn_type, use_container_width=True):
                st.session_state.active_ribbon_tab = "Impostazioni"
                st.query_params['active_ribbon_tab'] = "Impostazioni"
                st.rerun()

        # === SOTTOMENU AREA ===
        st.markdown('<div class="ribbon-content">', unsafe_allow_html=True)

        if active_tab == "Home":
            _render_home_submenu()
        elif active_tab == "Gestione Dati":
            _render_gestione_submenu()
        elif active_tab == "Organigrammi":
            _render_organigrammi_submenu()
        elif active_tab == "Analisi":
            _render_analisi_submenu()
        elif active_tab == "Versioni":
            _render_versioni_submenu()
        elif active_tab == "Impostazioni":
            _render_impostazioni_submenu()

        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# SOTTOMENU PER OGNI TAB
# ═══════════════════════════════════════════════════════════════════════════

def _render_home_submenu():
    """Tab Home: Dashboard, Azioni Rapide, Ricerca"""
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        st.markdown('<div class="ribbon-group"><div class="ribbon-group-title">📊 Dashboard</div>', unsafe_allow_html=True)
        if st.button("📊 Dashboard Home", key="cmd_dashboard_home", use_container_width=True):
            st.session_state.current_page = "Dashboard Home"
            st.rerun()
        if st.button("🗄️ Dashboard DB_ORG", key="cmd_dashboard_db", use_container_width=True):
            st.session_state.current_page = "Dashboard DB_ORG"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="ribbon-group"><div class="ribbon-group-title">⚡ Azioni Rapide</div>', unsafe_allow_html=True)
        subcol1, subcol2 = st.columns(2)
        with subcol1:
            if st.button("👤 Nuovo Dip.", key="cmd_new_emp", use_container_width=True):
                st.session_state.current_page = "Scheda Dipendente"
                st.rerun()
            if st.button("📥 Import Dati", key="cmd_import", use_container_width=True):
                from ui.wizard_state_manager import get_import_wizard
                wizard = get_import_wizard()
                wizard.activate()
                st.rerun()
        with subcol2:
            if st.button("🏢 Nuova Strutt.", key="cmd_new_struct", use_container_width=True):
                st.session_state.current_page = "Gestione Strutture"
                st.rerun()
            if st.button("📤 Export TNS", key="cmd_export_tns", use_container_width=True):
                st.session_state.current_page = "Save & Export"
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="ribbon-group"><div class="ribbon-group-title">🔍 Ricerca</div>', unsafe_allow_html=True)
        if st.button("🔎 Ricerca", key="cmd_search", use_container_width=True):
            st.session_state.current_page = "Ricerca Dati"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


def _render_gestione_submenu():
    """Tab Gestione Dati: Dipendenti, Strutture, Posizioni, Ruoli, Import/Export, Vista Tabellare"""
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        with st.expander("👥 **Dipendenti**", expanded=False):
            if st.button("📋 Gestione Personale", key="cmd_gest_pers", use_container_width=True):
                st.session_state.current_page = "Gestione Personale"
                st.rerun()
            if st.button("🪪 Scheda Dipendente", key="cmd_scheda_dip", use_container_width=True):
                st.session_state.current_page = "Scheda Dipendente"
                st.rerun()
            if st.button("⚡ Modifica Batch", key="cmd_batch", use_container_width=True):
                st.info("Funzione Modifica Batch in sviluppo")

    with col2:
        with st.expander("🏢 **Strutture**", expanded=False):
            if st.button("🏛️ Gestione Strutture", key="cmd_gest_struct", use_container_width=True):
                st.session_state.current_page = "Gestione Strutture"
                st.rerun()
            if st.button("📐 Scheda Strutture", key="cmd_scheda_struct", use_container_width=True):
                st.session_state.current_page = "Gestione Strutture"
                st.rerun()
            if st.button("➕ Nuova Struttura", key="cmd_new_struct2", use_container_width=True):
                st.session_state.current_page = "Gestione Strutture"
                st.rerun()

    with col3:
        with st.expander("📍 **Posizioni**", expanded=False):
            if st.button("📍 Gestione Posizioni", key="cmd_gest_posizioni", use_container_width=True):
                st.session_state.current_page = "Gestione Posizioni"
                st.rerun()
            if st.button("➕ Nuova Posizione", key="cmd_new_posizione", use_container_width=True):
                st.session_state.current_page = "Gestione Posizioni"
                st.session_state.show_new_position_form = True
                st.rerun()
            if st.button("⭕ Posizioni Vacanti", key="cmd_pos_vacanti", use_container_width=True):
                st.session_state.current_page = "Gestione Posizioni"
                st.rerun()

    with col4:
        with st.expander("🎭 **Ruoli**", expanded=False):
            if st.button("🎯 Gestione Ruoli", key="cmd_gest_ruoli", use_container_width=True):
                st.session_state.current_page = "Gestione Ruoli"
                st.rerun()
            if st.button("✅ Assegna Ruolo", key="cmd_assign_role", use_container_width=True):
                st.session_state.current_page = "Gestione Ruoli"
                st.rerun()
            if st.button("📊 Report Ruoli", key="cmd_report_ruoli", use_container_width=True):
                st.info("Report Ruoli in sviluppo")

    with col5:
        with st.expander("📥 **Import/Export**", expanded=False):
            if st.button("📥 Import DB_ORG", key="cmd_import_db", use_container_width=True):
                st.session_state.current_page = "Import DB_ORG"
                st.rerun()
            if st.button("🔄 Merge/Arricchimento", key="cmd_merge_enrichment", use_container_width=True):
                # Apri wizard merge/enrichment
                from ui.wizard_merge_enrichment_modal import show_merge_wizard
                show_merge_wizard()
            if st.button("📄 Import Personale", key="cmd_import_pers", use_container_width=True):
                st.session_state.current_page = "Import DB_ORG"
                st.rerun()
            if st.button("📤 Export Excel", key="cmd_export_excel", use_container_width=True):
                st.session_state.current_page = "Save & Export"
                st.rerun()

    with col6:
        with st.expander("📋 **Vista Dati**", expanded=False):
            if st.button("📋 Vista Tabellare", key="cmd_vista_tabellare", use_container_width=True):
                st.session_state.current_page = "Vista Tabellare"
                st.rerun()
            if st.button("📊 Vista Grafica", key="cmd_vista_grafica", use_container_width=True):
                st.info("Vista grafica in sviluppo")


def _render_organigrammi_submenu():
    """Tab Organigrammi: Viste, Layout, Strumenti"""
    col1, col2, col3 = st.columns([3, 2, 2])

    with col1:
        st.markdown('<div class="ribbon-group"><div class="ribbon-group-title">📊 Viste Organigrammi</div>', unsafe_allow_html=True)
        subcol1, subcol2 = st.columns(2)
        with subcol1:
            if st.button("👥 HR", key="cmd_hr_hier", use_container_width=True):
                st.session_state.current_page = "HR Hierarchy"
                st.rerun()
            if st.button("🧳 ORG", key="cmd_org_hier", use_container_width=True):
                st.session_state.current_page = "ORG Hierarchy"
                st.rerun()
            if st.button("🛡️ SGSL", key="cmd_sgsl", use_container_width=True):
                st.session_state.current_page = "SGSL Safety"
                st.rerun()
        with subcol2:
            if st.button("✅ TNS", key="cmd_struct_tns", use_container_width=True):
                st.session_state.current_page = "TNS Hierarchy"
                st.rerun()
            if st.button("🏛️ Unità", key="cmd_uo", use_container_width=True):
                st.session_state.current_page = "Unità Organizzative"
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="ribbon-group"><div class="ribbon-group-title">🎨 Layout</div>', unsafe_allow_html=True)
        layout_option = st.selectbox(
            "Layout",
            ["🌲 Albero H", "🏛️ Albero V", "☀️ Sunburst", "📦 Treemap", "🗂️ Pannelli", "📋 Card"],
            key="layout_selector",
            label_visibility="collapsed"
        )
        if st.session_state.get('orgchart_layout') != layout_option:
            st.session_state.orgchart_layout = layout_option
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="ribbon-group"><div class="ribbon-group-title">🔧 Strumenti</div>', unsafe_allow_html=True)
        if st.button("🔍 Cerca", key="cmd_search_node", use_container_width=True):
            st.info("Cerca nodo nell'organigramma")
        if st.button("📸 Export", key="cmd_export_png", use_container_width=True):
            st.info("Export PNG in sviluppo")
        st.markdown('</div>', unsafe_allow_html=True)


def _render_analisi_submenu():
    """Tab Analisi: Ricerca, Confronti, Audit Log, Report"""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        with st.expander("🔎 **Ricerca Avanzata**", expanded=False):
            if st.button("🔍 Ricerca Intelligente", key="cmd_smart_search", use_container_width=True):
                st.session_state.current_page = "Ricerca Dati"
                st.rerun()
            if st.button("🎛️ Filtri Multipli", key="cmd_filters", use_container_width=True):
                st.session_state.current_page = "Ricerca Dati"
                st.rerun()

    with col2:
        with st.expander("⚖️ **Confronti**", expanded=False):
            if st.button("⚖️ Confronta Versioni", key="cmd_compare_ver", use_container_width=True):
                st.session_state.current_page = "Confronta Versioni"
                st.rerun()
            if st.button("📊 Audit Comparativo", key="cmd_audit_comp", use_container_width=True):
                st.session_state.current_page = "Audit Comparativo"
                st.rerun()

    with col3:
        with st.expander("📜 **Audit Log**", expanded=False):
            if st.button("📜 Log Modifiche", key="cmd_audit_log", use_container_width=True):
                st.session_state.current_page = "Audit Log"
                st.rerun()
            if st.button("💾 Export Log", key="cmd_export_log", use_container_width=True):
                st.info("Export log in sviluppo")

    with col4:
        with st.expander("📊 **Report**", expanded=False):
            if st.button("📊 Report Standard", key="cmd_report_std", use_container_width=True):
                st.info("Report Standard in sviluppo")
            if st.button("📈 Report Personale", key="cmd_report_pers", use_container_width=True):
                st.info("Report Personale in sviluppo")


def _render_versioni_submenu():
    """Tab Versioni: Snapshot, Gestione Versioni, Sincronizzazione, Operazioni Avanzate"""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        with st.expander("📸 **Snapshot**", expanded=False):
            if st.button("📸 Snapshot Manuale", key="cmd_snapshot", use_container_width=True):
                st.session_state.current_page = "Gestione Versioni"
                st.rerun()
            if st.button("⚡ Checkpoint Rapido", key="cmd_checkpoint", use_container_width=True):
                st.session_state.current_page = "Gestione Versioni"
                st.rerun()
            if st.button("🏆 Milestone", key="cmd_milestone", use_container_width=True):
                st.session_state.current_page = "Gestione Versioni"
                st.rerun()

    with col2:
        with st.expander("📚 **Gestione Versioni**", expanded=False):
            if st.button("📚 Lista Versioni", key="cmd_list_ver", use_container_width=True):
                st.session_state.current_page = "Gestione Versioni"
                st.rerun()
            if st.button("⏪ Ripristina Versione", key="cmd_restore_ver", use_container_width=True):
                st.session_state.current_page = "Gestione Versioni"
                st.rerun()
            if st.button("⚖️ Compare Versioni", key="cmd_comp_ver", use_container_width=True):
                st.session_state.current_page = "Confronta Versioni"
                st.rerun()

    with col3:
        with st.expander("🔄 **Sincronizzazione**", expanded=False):
            if st.button("✅ Verifica Consistenza", key="cmd_verify", use_container_width=True):
                st.session_state.current_page = "Sync Check"
                st.rerun()
            if st.button("🔍 Sync Check View", key="cmd_sync_check", use_container_width=True):
                st.session_state.current_page = "Sync Check"
                st.rerun()

    with col4:
        with st.expander("🛠️ **Operazioni Avanzate**", expanded=False):
            st.error("⚠️ **ATTENZIONE**: Operazioni irreversibili!")

            # Pulsante Svuota Database con conferma robusta
            if st.button("🗑️ Svuota Database", key="cmd_clear_db", use_container_width=True, type="secondary"):
                st.session_state.show_clear_db_confirm = True

            # Mostra dialog di conferma se richiesto
            if st.session_state.get('show_clear_db_confirm', False):
                st.markdown("---")
                st.error("🚨 **CONFERMA SVUOTAMENTO DATABASE**")
                st.warning("""
                Questa operazione eliminerà **TUTTI I DATI** dal database:
                - Tutti i dipendenti
                - Tutte le strutture
                - Tutti i ruoli e assegnamenti
                - Tutte le versioni e snapshot
                - Tutto l'audit log

                **QUESTA OPERAZIONE È IRREVERSIBILE!**
                """)

                confirm_text = st.text_input(
                    "Digita esattamente: **CONFERMA SVUOTAMENTO**",
                    key="clear_db_confirm_text",
                    placeholder="CONFERMA SVUOTAMENTO"
                )

                col_a, col_b = st.columns(2)

                with col_a:
                    if st.button("✅ PROCEDI", key="clear_db_proceed", type="primary", use_container_width=True):
                        if confirm_text == "CONFERMA SVUOTAMENTO":
                            # Esegui svuotamento
                            db = st.session_state.database_handler
                            result = db.clear_all_data(confirmation_text=confirm_text)

                            if result['success']:
                                st.success(f"✅ {result['message']}")
                                st.info(f"🗑️ Tabelle svuotate: {len(result['tables_cleared'])}")

                                # Reset session state
                                st.session_state.data_loaded = False
                                st.session_state.personale_df = None
                                st.session_state.strutture_df = None
                                st.session_state.db_tns_df = None
                                st.session_state.show_clear_db_confirm = False

                                st.rerun()
                            else:
                                st.error(f"❌ {result['message']}")
                        else:
                            st.error("❌ Testo di conferma non corretto")

                with col_b:
                    if st.button("❌ ANNULLA", key="clear_db_cancel", use_container_width=True):
                        st.session_state.show_clear_db_confirm = False
                        st.rerun()

            if st.button("📤 Export Backup", key="cmd_backup", use_container_width=True):
                st.session_state.current_page = "Save & Export"
                st.rerun()

def _render_impostazioni_submenu():
    """Tab Impostazioni: Viste Personalizzate, Configurazioni"""
    col1, col2, col3 = st.columns([2, 2, 2])

    with col1:
        st.markdown('<div class="ribbon-group"><div class="ribbon-group-title">⚙️ Configurazione</div>', unsafe_allow_html=True)
        if st.button("🎨 Gestione Viste", key="cmd_manage_views", use_container_width=True):
            st.session_state.current_page = "Impostazioni"
            st.rerun()
        if st.button("📋 Viste Personalizzate", key="cmd_custom_views", use_container_width=True):
            st.session_state.current_page = "Impostazioni"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="ribbon-group"><div class="ribbon-group-title">🔧 Sistema</div>', unsafe_allow_html=True)
        if st.button("🗄️ Database", key="cmd_db_settings", use_container_width=True):
            st.info("Impostazioni database in sviluppo")
        if st.button("🔐 Permessi", key="cmd_permissions", use_container_width=True):
            st.info("Gestione permessi in sviluppo")
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="ribbon-group"><div class="ribbon-group-title">ℹ️ Informazioni</div>', unsafe_allow_html=True)
        if st.button("📖 Documentazione", key="cmd_docs", use_container_width=True):
            st.info("Documentazione in sviluppo")
        if st.button("ℹ️ Info App", key="cmd_about", use_container_width=True):
            st.info("HR Masterdata Management v1.0")
        st.markdown('</div>', unsafe_allow_html=True)
