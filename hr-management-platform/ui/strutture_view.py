"""
UI per gestione TNS Strutture con Master-Detail pattern.
Layout: Master table (40%) + Detail panel (60%) per UX migliorata.
Tab ridotti da 5 a 3 per ridurre cognitive overload.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from services.validator import DataValidator
from ui.styles import render_filter_badge

def show_strutture_view():
    """UI per gestione strutture organizzative con master-detail pattern"""

    st.caption("Gestisci organigramma aziendale e relazioni gerarchiche")

    # Get dataframes with safety check
    strutture_df = st.session_state.get('strutture_df')
    personale_df = st.session_state.get('personale_df')

    if strutture_df is None or personale_df is None:
        st.warning("⚠️ Nessun dato disponibile. Importa un file Excel per iniziare.")
        return

    # Statistiche rapide
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Totale strutture", len(strutture_df))
    with col2:
        complete = DataValidator.find_incomplete_records_strutture(strutture_df)
        complete_count = len(strutture_df) - len(complete)
        st.metric("Record completi", complete_count)
    with col3:
        orphans = DataValidator.find_orphan_structures(strutture_df, personale_df)
        st.metric("Strutture orfane", len(orphans), delta_color="inverse")
    with col4:
        roots = strutture_df['UNITA\' OPERATIVA PADRE '].isna().sum()
        st.metric("Root", roots)

    # === 3 TAB INVECE DI 5 ===
    tab1, tab2, tab3 = st.tabs([
        "📋 Gestione",
        "➕ Aggiungi Nuova",
        "🌳 Gerarchia Albero"
    ])

    # === TAB 1: GESTIONE (Master-Detail) ===
    with tab1:
        show_gestione_tab(strutture_df, personale_df)

    # === TAB 2: AGGIUNGI NUOVA ===
    with tab2:
        show_add_tab(strutture_df)

    # === TAB 3: GERARCHIA ALBERO ===
    with tab3:
        show_hierarchy_tab(strutture_df, personale_df)

def show_gestione_tab(strutture_df: pd.DataFrame, personale_df: pd.DataFrame):
    """Tab Gestione con master-detail layout"""

    # === STICKY FILTERS BAR ===
    st.markdown('<div class="sticky-filters">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    with col1:
        search_text = st.text_input("🔍 Cerca (Descrizione, Codice)", key="search_strutture")

    with col2:
        show_only = st.selectbox(
            "Filtro Tipo",
            ["Tutte", "Solo root", "Solo orfane"],
            key="filter_type_strutture"
        )

    with col3:
        # Filtro per presenza dipendenti
        filter_deps = st.selectbox(
            "Dipendenti",
            ["Tutte", "Con dipendenti", "Senza dipendenti"],
            key="filter_deps_strutture"
        )

    st.markdown('</div>', unsafe_allow_html=True)

    # Applica filtri
    filtered_df = strutture_df.copy()

    if search_text:
        mask = (
            filtered_df['DESCRIZIONE'].str.contains(search_text, case=False, na=False) |
            filtered_df['Codice'].str.contains(search_text, case=False, na=False)
        )
        filtered_df = filtered_df[mask]

    if show_only == "Solo root":
        filtered_df = filtered_df[filtered_df['UNITA\' OPERATIVA PADRE '].isna()]
    elif show_only == "Solo orfane":
        orphan_codes = DataValidator.find_orphan_structures(strutture_df, personale_df)['Codice'].tolist()
        filtered_df = filtered_df[filtered_df['Codice'].isin(orphan_codes)]

    if filter_deps == "Con dipendenti":
        # Filtra solo strutture che hanno dipendenti
        structs_with_deps = personale_df['UNITA\' OPERATIVA PADRE '].dropna().unique()
        filtered_df = filtered_df[filtered_df['Codice'].isin(structs_with_deps)]
    elif filter_deps == "Senza dipendenti":
        structs_with_deps = personale_df['UNITA\' OPERATIVA PADRE '].dropna().unique()
        filtered_df = filtered_df[~filtered_df['Codice'].isin(structs_with_deps)]

    render_filter_badge(len(filtered_df), len(strutture_df))

    # === MASTER-DETAIL LAYOUT ===
    col_master, col_detail = st.columns([0.4, 0.6])

    # === MASTER TABLE (left 40%) ===
    with col_master:
        st.markdown("### 📋 Lista Strutture")

        if len(filtered_df) > 0:
            # Crea tabella compatta con 3 colonne chiave
            master_df = filtered_df[['Codice', 'DESCRIZIONE', 'UNITA\' OPERATIVA PADRE ']].copy()
            master_df = master_df.reset_index(drop=True)

            # Mostra tabella con on_select
            selection = st.dataframe(
                master_df,
                use_container_width=True,
                height=500,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                column_config={
                    'Codice': st.column_config.TextColumn('Codice', width='small'),
                    'DESCRIZIONE': st.column_config.TextColumn('Descrizione', width='large'),
                    'UNITA\' OPERATIVA PADRE ': st.column_config.TextColumn('Padre', width='small'),
                }
            )

            # Gestisci selezione
            if selection and selection.selection and selection.selection.rows:
                selected_idx = selection.selection.rows[0]
                selected_codice = master_df.iloc[selected_idx]['Codice']
                st.session_state.selected_structure_id = selected_codice

        else:
            st.info("Nessuna struttura trovata con i filtri applicati")

    # === DETAIL PANEL (right 60%) ===
    with col_detail:
        if st.session_state.get('selected_structure_id'):
            show_structure_detail_panel(strutture_df, personale_df, filtered_df)
        else:
            st.info("👈 Seleziona una struttura dalla tabella per visualizzare i dettagli")

def show_structure_detail_panel(strutture_df: pd.DataFrame, personale_df: pd.DataFrame, filtered_df: pd.DataFrame):
    """Mostra detail panel per struttura selezionata"""

    selected_codice = st.session_state.selected_structure_id

    # Trova record
    record = strutture_df[strutture_df['Codice'] == selected_codice]

    if len(record) == 0:
        st.error(f"Struttura con codice {selected_codice} non trovata")
        st.session_state.selected_structure_id = None
        return

    record = record.iloc[0]

    st.markdown('<div class="detail-panel">', unsafe_allow_html=True)
    st.markdown(f"### ✏️ Dettagli: {record['DESCRIZIONE']}")
    st.caption(f"Codice: `{record['Codice']}`")

    # Conta dipendenti associati
    num_dipendenti = len(personale_df[personale_df['UNITA\' OPERATIVA PADRE '] == selected_codice])
    num_sotto_strutture = len(strutture_df[strutture_df['UNITA\' OPERATIVA PADRE '] == selected_codice])

    col1, col2 = st.columns(2)
    with col1:
        st.metric("👥 Dipendenti Diretti", num_dipendenti)
    with col2:
        st.metric("🏗️ Sotto-Strutture", num_sotto_strutture)

    # === SEZIONE 1: DATI ESSENZIALI ===
    st.markdown("#### 📋 Dati Essenziali")

    col1, col2 = st.columns(2)

    with col1:
        new_descrizione = st.text_input("Descrizione *", value=record['DESCRIZIONE'] or "", key="edit_desc_strut")
        new_codice = st.text_input("Codice *", value=record['Codice'] or "", key="edit_cod_strut", disabled=True)

    with col2:
        new_padre = st.text_input("Unità Operativa Padre", value=record['UNITA\' OPERATIVA PADRE '] or "", key="edit_padre_strut")
        new_livello = st.text_input("Livello", value=record['LIVELLO'] or "", key="edit_livello_strut")

    # === SEZIONE 2: ORGANIZZAZIONE (expander) ===
    with st.expander("🏢 Organizzazione e Costi", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            new_cdc = st.text_input("Centro di Costo (CDCCOSTO)", value=record['CDCCOSTO'] or "", key="edit_cdc_strut")
            new_societa = st.text_input("Società Esercente", value=record['SocietaEsercente'] or "", key="edit_soc_strut")
            new_tipo_sede = st.text_input("Tipo Sede", value=record['TIPO SEDE'] or "", key="edit_tipo_sede_strut")

        with col2:
            new_uff_amm = st.text_input("Uff. Amm. Appartenenza", value=record['UFF.AMM.APPARTENENZA'] or "", key="edit_uff_strut")
            new_tipo_struttura = st.text_input("Tipo Struttura", value=record['TIPO STRUTTURA'] or "", key="edit_tipo_strut_strut")
            new_stato_amm = st.text_input("Stato Amministrativo", value=record['STATOAMMINISTRATIVO'] or "", key="edit_stato_strut")

    # === SEZIONE 3: RUOLI E PERMESSI (expander) ===
    with st.expander("🔐 Ruoli e Permessi", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            new_visibilita = st.text_input("Visibilità", value=record['VISIBILITA'] or "", key="edit_vis_strut")
            new_tipo_nodo = st.text_input("Tipo Nodo Interno", value=record['TipoNodoInterno'] or "", key="edit_nodo_strut")
            new_nodo_org_ruolo = st.text_input("Nodo Organigramma Ruolo", value=record['NdoOrganigrammaRuolo'] or "", key="edit_org_ruolo_strut")
            new_nodo_org_fun = st.text_input("Nodo Organigramma Funzione", value=record['NdoOrganigrammaFunzione'] or "", key="edit_org_fun_strut")

        with col2:
            new_campo10 = st.text_input("Campo 10", value=record['Campo10'] or "", key="edit_c10_strut")
            new_campo13 = st.text_input("Campo 13", value=record['Campo13'] or "", key="edit_c13_strut")
            new_campo14 = st.text_input("Campo 14", value=record['Campo14'] or "", key="edit_c14_strut")
            new_campo17 = st.text_input("Campo 17", value=record['Campo17'] or "", key="edit_c17_strut")

    # === SEZIONE 4: ALTRI CAMPI (expander) ===
    with st.expander("📦 Altri Campi", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            new_sede_tns = st.text_input("Sede TNS", value=record['Sede_TNS'] or "", key="edit_sede_strut")
            new_gruppo_sind = st.text_input("Gruppo Sindacale", value=record['GruppoSind'] or "", key="edit_gruppo_strut")
            new_costo_orario = st.text_input("Costo Orario", value=record['CostoOrario'] or "", key="edit_costo_strut")

        with col2:
            new_campo20 = st.text_input("Campo 20", value=record['Campo20'] or "", key="edit_c20_strut")
            new_campo21 = st.text_input("Campo 21", value=record['Campo21'] or "", key="edit_c21_strut")
            new_campo22 = st.text_input("Campo 22", value=record['Campo22'] or "", key="edit_c22_strut")

    # === BOTTONI AZIONE ===
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        if st.button("💾 Salva Modifiche", type="primary", use_container_width=True):
            if not all([new_descrizione, new_codice]):
                st.error("❌ Descrizione e Codice sono obbligatori")
            else:
                # Verifica cicli se padre è cambiato
                if new_padre and new_padre != record['UNITA\' OPERATIVA PADRE ']:
                    # Verifica che il nuovo padre non crei cicli
                    if would_create_cycle(strutture_df, selected_codice, new_padre):
                        st.error("❌ Questa modifica creerebbe un ciclo gerarchico! Operazione annullata.")
                        return

                # Applica modifiche
                idx = strutture_df[strutture_df['Codice'] == selected_codice].index[0]

                strutture_df.at[idx, 'DESCRIZIONE'] = new_descrizione
                strutture_df.at[idx, 'UNITA\' OPERATIVA PADRE '] = new_padre if new_padre else None
                strutture_df.at[idx, 'LIVELLO'] = new_livello if new_livello else None
                strutture_df.at[idx, 'CDCCOSTO'] = new_cdc if new_cdc else None
                strutture_df.at[idx, 'SocietaEsercente'] = new_societa if new_societa else None
                strutture_df.at[idx, 'TIPO SEDE'] = new_tipo_sede if new_tipo_sede else None
                strutture_df.at[idx, 'UFF.AMM.APPARTENENZA'] = new_uff_amm if new_uff_amm else None
                strutture_df.at[idx, 'TIPO STRUTTURA'] = new_tipo_struttura if new_tipo_struttura else None
                strutture_df.at[idx, 'STATOAMMINISTRATIVO'] = new_stato_amm if new_stato_amm else None
                strutture_df.at[idx, 'VISIBILITA'] = new_visibilita if new_visibilita else None
                strutture_df.at[idx, 'TipoNodoInterno'] = new_tipo_nodo if new_tipo_nodo else None
                strutture_df.at[idx, 'NdoOrganigrammaRuolo'] = new_nodo_org_ruolo if new_nodo_org_ruolo else None
                strutture_df.at[idx, 'NdoOrganigrammaFunzione'] = new_nodo_org_fun if new_nodo_org_fun else None
                strutture_df.at[idx, 'Campo10'] = new_campo10 if new_campo10 else None
                strutture_df.at[idx, 'Campo13'] = new_campo13 if new_campo13 else None
                strutture_df.at[idx, 'Campo14'] = new_campo14 if new_campo14 else None
                strutture_df.at[idx, 'Campo17'] = new_campo17 if new_campo17 else None
                strutture_df.at[idx, 'Sede_TNS'] = new_sede_tns if new_sede_tns else None
                strutture_df.at[idx, 'GruppoSind'] = new_gruppo_sind if new_gruppo_sind else None
                strutture_df.at[idx, 'CostoOrario'] = new_costo_orario if new_costo_orario else None
                strutture_df.at[idx, 'Campo20'] = new_campo20 if new_campo20 else None
                strutture_df.at[idx, 'Campo21'] = new_campo21 if new_campo21 else None
                strutture_df.at[idx, 'Campo22'] = new_campo22 if new_campo22 else None

                # === PERSISTI NEL DATABASE ===
                try:
                    db_handler = st.session_state.database_handler
                    updates = {
                        'DESCRIZIONE': new_descrizione,
                        'UNITA\' OPERATIVA PADRE ': new_padre if new_padre else None,
                        'LIVELLO': new_livello if new_livello else None,
                        'CDCCOSTO': new_cdc if new_cdc else None,
                        'SocietaEsercente': new_societa if new_societa else None,
                        'TIPO SEDE': new_tipo_sede if new_tipo_sede else None,
                        'UFF.AMM.APPARTENENZA': new_uff_amm if new_uff_amm else None,
                        'TIPO STRUTTURA': new_tipo_struttura if new_tipo_struttura else None,
                        'STATOAMMINISTRATIVO': new_stato_amm if new_stato_amm else None,
                        'VISIBILITA': new_visibilita if new_visibilita else None,
                        'TipoNodoInterno': new_tipo_nodo if new_tipo_nodo else None,
                        'NdoOrganigrammaRuolo': new_nodo_org_ruolo if new_nodo_org_ruolo else None,
                        'NdoOrganigrammaFunzione': new_nodo_org_fun if new_nodo_org_fun else None,
                        'Campo10': new_campo10 if new_campo10 else None,
                        'Campo13': new_campo13 if new_campo13 else None,
                        'Campo14': new_campo14 if new_campo14 else None,
                        'Campo17': new_campo17 if new_campo17 else None,
                        'Sede_TNS': new_sede_tns if new_sede_tns else None,
                        'GruppoSind': new_gruppo_sind if new_gruppo_sind else None,
                        'CostoOrario': new_costo_orario if new_costo_orario else None,
                        'Campo20': new_campo20 if new_campo20 else None,
                        'Campo21': new_campo21 if new_campo21 else None,
                        'Campo22': new_campo22 if new_campo22 else None,
                    }
                    db_handler.update_struttura(selected_codice, updates)
                except Exception as e:
                    st.warning(f"⚠️ Errore persistenza database: {str(e)}")

                st.session_state.strutture_df = strutture_df
                st.session_state.show_feedback = True
                st.rerun()

    with col2:
        if st.button("🔄 Annulla", use_container_width=True):
            st.session_state.selected_structure_id = None
            st.rerun()

    with col3:
        if st.button("🗑️ Elimina", type="secondary", use_container_width=True):
            st.session_state.delete_confirm_structure_id = selected_codice
            st.rerun()

    # Dialog conferma eliminazione
    if st.session_state.get('delete_confirm_structure_id') == selected_codice:
        # Verifica se è referenziata
        all_parents_strut = set(strutture_df['UNITA\' OPERATIVA PADRE '].dropna().unique())
        all_parents_pers = set(personale_df['UNITA\' OPERATIVA PADRE '].dropna().unique())

        if selected_codice in all_parents_strut or selected_codice in all_parents_pers:
            st.error(f"❌ Impossibile eliminare! La struttura **{record['DESCRIZIONE']}** è referenziata da altre strutture o dipendenti.")

            if st.button("❌ Chiudi", use_container_width=True):
                st.session_state.delete_confirm_structure_id = None
                st.rerun()
        else:
            st.warning(f"⚠️ Confermi eliminazione di **{record['DESCRIZIONE']}** (Codice: {record['Codice']})?")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Sì, elimina", type="secondary", use_container_width=True):
                    # === ELIMINA DAL DATABASE ===
                    try:
                        db_handler = st.session_state.database_handler
                        db_handler.delete_struttura(selected_codice)
                    except Exception as e:
                        st.warning(f"⚠️ Errore eliminazione database: {str(e)}")

                    strutture_df = strutture_df[strutture_df['Codice'] != selected_codice]
                    st.session_state.strutture_df = strutture_df
                    st.session_state.selected_structure_id = None
                    st.session_state.delete_confirm_structure_id = None
                    st.success(f"✅ Struttura {record['DESCRIZIONE']} eliminata")
                    st.rerun()

            with col2:
                if st.button("❌ Annulla", use_container_width=True):
                    st.session_state.delete_confirm_structure_id = None
                    st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

def would_create_cycle(strutture_df: pd.DataFrame, codice: str, new_padre: str) -> bool:
    """
    Verifica se impostare new_padre come padre di codice creerebbe un ciclo.

    Returns:
        True se creerebbe un ciclo, False altrimenti
    """
    if not new_padre:
        return False

    visited = set()
    current = new_padre

    # Risali la catena dal nuovo padre fino a root
    while current and current not in visited:
        if current == codice:
            # Ciclo trovato!
            return True

        visited.add(current)

        # Trova il padre di current
        parent_row = strutture_df[strutture_df['Codice'] == current]
        if len(parent_row) == 0:
            break

        current = parent_row.iloc[0]['UNITA\' OPERATIVA PADRE ']
        if pd.isna(current):
            break

    return False

def show_add_tab(strutture_df: pd.DataFrame):
    """Tab per aggiungere nuova struttura"""

    st.markdown("### ➕ Aggiungi Nuova Struttura")

    with st.form("add_struttura_form"):
        st.markdown("#### Dati Essenziali")

        col1, col2 = st.columns(2)

        with col1:
            new_codice = st.text_input("Codice *", help="Codice univoco struttura")
            new_desc = st.text_input("Descrizione *", help="Nome unità organizzativa")

        with col2:
            new_padre = st.text_input("Padre (UNITA' OPERATIVA PADRE)", help="Lascia vuoto per root")
            new_livello = st.text_input("Livello")

        st.markdown("#### Dati Opzionali")

        col1, col2 = st.columns(2)

        with col1:
            new_cdc = st.text_input("Centro di Costo (CDCCOSTO)")
            new_societa = st.text_input("Società Esercente")

        with col2:
            new_tipo_sede = st.text_input("Tipo Sede")
            new_tipo_struttura = st.text_input("Tipo Struttura")

        submitted = st.form_submit_button("➕ Aggiungi Struttura", type="primary", use_container_width=True)

        if submitted:
            if not all([new_codice, new_desc]):
                st.error("❌ Codice e Descrizione sono obbligatori")
            elif new_codice in strutture_df['Codice'].values:
                st.error(f"❌ Codice '{new_codice}' già esistente!")
            else:
                # Crea nuovo record con tutte le colonne
                new_record = pd.Series({col: None for col in strutture_df.columns})
                new_record['Codice'] = new_codice.strip()
                new_record['DESCRIZIONE'] = new_desc.strip()
                new_record['UNITA\' OPERATIVA PADRE '] = new_padre.strip() if new_padre else None
                new_record['LIVELLO'] = new_livello.strip() if new_livello else None
                new_record['CDCCOSTO'] = new_cdc.strip() if new_cdc else None
                new_record['SocietaEsercente'] = new_societa.strip() if new_societa else None
                new_record['TIPO SEDE'] = new_tipo_sede.strip() if new_tipo_sede else None
                new_record['TIPO STRUTTURA'] = new_tipo_struttura.strip() if new_tipo_struttura else None
                new_record['TxCodFiscale'] = None  # Importante: strutture NON hanno CF

                # === INSERISCI NEL DATABASE ===
                try:
                    db_handler = st.session_state.database_handler
                    record_dict = new_record.to_dict()
                    db_handler.insert_struttura(record_dict)
                except Exception as e:
                    st.warning(f"⚠️ Errore inserimento database: {str(e)}")

                # Aggiungi
                strutture_df = pd.concat([strutture_df, new_record.to_frame().T], ignore_index=True)
                st.session_state.strutture_df = strutture_df

                st.success(f"✅ Struttura {new_desc} aggiunta")
                st.session_state.show_feedback = True
                st.rerun()

def show_hierarchy_tab(strutture_df: pd.DataFrame, personale_df: pd.DataFrame):
    """Tab visualizzazione gerarchia (mantiene logica esistente)"""

    st.markdown("### 🌳 Visualizzazione Gerarchia")

    # Selettore modalità
    view_mode = st.radio(
        "Modalità visualizzazione",
        ["Vista Accordion", "Percorso Singolo"],
        horizontal=True
    )

    if view_mode == "Vista Accordion":
        st.markdown("#### Vista Accordion")

        # Filtri
        col_filter1, col_filter2 = st.columns([1, 2])
        with col_filter1:
            hide_empty = st.checkbox(
                "Nascondi strutture senza dipendenti",
                value=False
            )
        with col_filter2:
            search_text = st.text_input(
                "Cerca struttura",
                placeholder="Cerca per nome o codice...",
                label_visibility="collapsed"
            )

        # Root structures
        root_structures = strutture_df[strutture_df['UNITA\' OPERATIVA PADRE '].isna()]

        if len(root_structures) == 0:
            st.warning("Nessuna struttura root trovata")
        else:
            filtered_roots = root_structures.copy()

            if search_text:
                mask = (
                    filtered_roots['DESCRIZIONE'].str.contains(search_text, case=False, na=False) |
                    filtered_roots['Codice'].str.contains(search_text, case=False, na=False)
                )
                filtered_roots = filtered_roots[mask]

            for idx, root in filtered_roots.iterrows():
                show_accordion_compact(
                    root,
                    strutture_df,
                    personale_df,
                    level=0,
                    unique_key=f"root_{idx}",
                    hide_empty=hide_empty,
                    search_text=search_text
                )

    else:  # Percorso Singolo
        st.info("Seleziona una struttura per vedere il suo percorso gerarchico")

        selected_code = st.selectbox(
            "Struttura",
            options=strutture_df['Codice'].tolist(),
            format_func=lambda c: f"{c} - {strutture_df[strutture_df['Codice']==c]['DESCRIZIONE'].iloc[0]}"
        )

        if selected_code:
            path = get_hierarchy_path(strutture_df, selected_code)

            st.markdown("#### Percorso gerarchico (da root):")
            for i, (code, desc) in enumerate(path):
                indent = "  " * i
                st.text(f"{indent}{'└─' if i > 0 else '▪'} [{code}] {desc}")

            # Figli diretti
            children = strutture_df[strutture_df['UNITA\' OPERATIVA PADRE '] == selected_code]
            if len(children) > 0:
                st.markdown("#### Figli diretti:")
                st.dataframe(
                    children[['Codice', 'DESCRIZIONE']],
                    use_container_width=True,
                    hide_index=True
                )

            # Dipendenti associati
            dipendenti = personale_df[personale_df['UNITA\' OPERATIVA PADRE '] == selected_code]
            if len(dipendenti) > 0:
                st.markdown(f"#### 👥 Dipendenti ({len(dipendenti)}):")
                st.dataframe(
                    dipendenti[['TxCodFiscale', 'Titolare', 'Codice']],
                    use_container_width=True,
                    hide_index=True
                )

# === FUNZIONI HELPER PER GERARCHIA (mantenute dall'originale) ===

def get_hierarchy_path(strutture_df: pd.DataFrame, codice: str) -> list:
    """Costruisce percorso gerarchico da root a codice dato"""
    path = []
    current = codice
    visited = set()

    while current and current not in visited:
        visited.add(current)

        row = strutture_df[strutture_df['Codice'] == current]
        if len(row) == 0:
            break

        desc = row.iloc[0]['DESCRIZIONE']
        path.insert(0, (current, desc))

        padre = row.iloc[0]['UNITA\' OPERATIVA PADRE ']
        if pd.isna(padre):
            break

        current = padre

    return path

def show_accordion_compact(
    structure_row,
    strutture_df: pd.DataFrame,
    personale_df: pd.DataFrame,
    level: int = 0,
    unique_key: str = "",
    hide_empty: bool = False,
    search_text: str = ""
):
    """Vista accordion compatta (mantenuta dall'originale)"""
    code = structure_row['Codice']
    desc = structure_row['DESCRIZIONE']

    children_structs = strutture_df[strutture_df['UNITA\' OPERATIVA PADRE '] == code]
    dipendenti = personale_df[personale_df['UNITA\' OPERATIVA PADRE '] == code]

    if hide_empty and len(dipendenti) == 0:
        return

    if search_text and level == 0:
        if not (search_text.lower() in desc.lower() or search_text.lower() in code.lower()):
            return

    if level == 0:
        with st.expander(
            f"**{desc}** ({code}) - {len(children_structs)} strutture, {len(dipendenti)} dipendenti",
            expanded=False
        ):
            render_compact_content(
                code, desc, children_structs, dipendenti,
                strutture_df, personale_df, level, unique_key,
                hide_empty
            )
    else:
        render_compact_content(
            code, desc, children_structs, dipendenti,
            strutture_df, personale_df, level, unique_key,
            hide_empty
        )

def render_compact_content(
    code: str,
    desc: str,
    children_structs: pd.DataFrame,
    dipendenti: pd.DataFrame,
    strutture_df: pd.DataFrame,
    personale_df: pd.DataFrame,
    level: int,
    unique_key: str,
    hide_empty: bool = False
):
    """Renderizza contenuto accordion compatto"""
    st.caption(f"Codice: {code} | Strutture: {len(children_structs)} | Dipendenti: {len(dipendenti)}")

    # Dipendenti
    if len(dipendenti) > 0:
        expand_deps_key = f"deps_{unique_key}_{code}"

        if expand_deps_key not in st.session_state:
            st.session_state[expand_deps_key] = False

        arrow = "▼" if st.session_state[expand_deps_key] else "▶"
        if st.button(f"{arrow} Dipendenti ({len(dipendenti)})", key=f"btn_{expand_deps_key}"):
            st.session_state[expand_deps_key] = not st.session_state[expand_deps_key]

        if st.session_state[expand_deps_key]:
            for _, dip in dipendenti.iterrows():
                st.text(f"  • {dip['Titolare']} - {dip['TxCodFiscale']}")

    # Sotto-strutture
    if len(children_structs) > 0:
        expand_children_key = f"children_{unique_key}_{code}"

        if expand_children_key not in st.session_state:
            st.session_state[expand_children_key] = False

        arrow = "▼" if st.session_state[expand_children_key] else "▶"
        if st.button(f"{arrow} Sotto-strutture ({len(children_structs)})", key=f"btn_{expand_children_key}"):
            st.session_state[expand_children_key] = not st.session_state[expand_children_key]

        if st.session_state[expand_children_key]:
            for idx, (_, child) in enumerate(children_structs.iterrows()):
                child_code = child['Codice']
                child_desc = child['DESCRIZIONE']

                child_children = len(strutture_df[strutture_df['UNITA\' OPERATIVA PADRE '] == child_code])
                child_deps = len(personale_df[personale_df['UNITA\' OPERATIVA PADRE '] == child_code])

                if hide_empty and child_deps == 0:
                    continue

                indent = "  " * (level + 1)

                expand_child_key = f"expand_{unique_key}_{idx}_{child_code}"

                if expand_child_key not in st.session_state:
                    st.session_state[expand_child_key] = False

                arrow_child = "▼" if st.session_state[expand_child_key] else "▶"

                st.markdown(f"{indent}**{child_desc}** ({child_code})")

                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button(
                        f"{arrow_child}",
                        key=f"btn_{expand_child_key}",
                        help="Espandi/Comprimi"
                    ):
                        st.session_state[expand_child_key] = not st.session_state[expand_child_key]
                with col2:
                    st.caption(f"{child_children} strutture, {child_deps} dipendenti")

                if st.session_state[expand_child_key]:
                    with st.container():
                        show_accordion_compact(
                            child,
                            strutture_df,
                            personale_df,
                            level + 1,
                            unique_key=f"{unique_key}_c{idx}",
                            hide_empty=hide_empty
                        )
