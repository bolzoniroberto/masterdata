"""
UI per gestione TNS Personale con Master-Detail pattern.
Layout: Master table (40%) + Detail panel (60%) per UX migliorata.
"""
import streamlit as st
import pandas as pd
from services.validator import DataValidator
from ui.styles import apply_common_styles, render_filter_badge


def show_personale_view():
    """UI per gestione dipendenti con master-detail pattern"""

    apply_common_styles()

    st.header("👥 Gestione Personale")
    st.caption("Seleziona un record dalla tabella per visualizzare e modificare i dettagli")

    personale_df = st.session_state.personale_df

    # Statistiche rapide
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Totale dipendenti", len(personale_df))
    with col2:
        complete = DataValidator.find_incomplete_records_personale(personale_df)
        complete_count = len(personale_df) - len(complete)
        st.metric("Record completi", complete_count)
    with col3:
        has_dup, dups = DataValidator.check_duplicate_keys(personale_df, 'TxCodFiscale')
        dup_count = len(dups) if has_dup else 0
        st.metric("CF duplicati", dup_count, delta_color="inverse")
    with col4:
        sedi = personale_df['Sede_TNS'].nunique()
        st.metric("Sedi", sedi)

    st.markdown("---")

    # === STICKY FILTERS BAR ===
    st.markdown('<div class="sticky-filters">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    with col1:
        search_text = st.text_input("🔍 Cerca (Titolare, CF, Codice)", key="search_personale")

    with col2:
        filter_uo = st.multiselect(
            "Unità Organizzativa",
            options=sorted(personale_df['Unità Organizzativa'].dropna().unique()),
            key="filter_uo_personale"
        )

    with col3:
        filter_sede = st.multiselect(
            "Sede",
            options=sorted(personale_df['Sede_TNS'].dropna().unique()),
            key="filter_sede_personale"
        )

    st.markdown('</div>', unsafe_allow_html=True)

    # Applica filtri
    filtered_df = personale_df.copy()

    if search_text:
        mask = (
            filtered_df['Titolare'].str.contains(search_text, case=False, na=False) |
            filtered_df['TxCodFiscale'].str.contains(search_text, case=False, na=False) |
            filtered_df['Codice'].str.contains(search_text, case=False, na=False)
        )
        filtered_df = filtered_df[mask]

    if filter_uo:
        filtered_df = filtered_df[filtered_df['Unità Organizzativa'].isin(filter_uo)]

    if filter_sede:
        filtered_df = filtered_df[filtered_df['Sede_TNS'].isin(filter_sede)]

    render_filter_badge(len(filtered_df), len(personale_df))

    # === MASTER-DETAIL LAYOUT ===
    col_master, col_detail = st.columns([0.4, 0.6])

    # === MASTER TABLE (left 40%) ===
    with col_master:
        st.markdown("### 📋 Lista Dipendenti")

        if len(filtered_df) > 0:
            # Crea tabella compatta con 4 colonne chiave
            master_df = filtered_df[['Codice', 'Titolare', 'Unità Organizzativa', 'Sede_TNS']].copy()
            master_df = master_df.reset_index(drop=True)

            # Mostra tabella con on_select per catturare selezione
            selection = st.dataframe(
                master_df,
                use_container_width=True,
                height=500,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                column_config={
                    'Codice': st.column_config.TextColumn('Codice', width='small'),
                    'Titolare': st.column_config.TextColumn('Nome', width='large'),
                    'Unità Organizzativa': st.column_config.TextColumn('Unità Org.', width='medium'),
                    'Sede_TNS': st.column_config.TextColumn('Sede', width='small'),
                }
            )

            # Gestisci selezione
            if selection and selection.selection and selection.selection.rows:
                selected_idx = selection.selection.rows[0]
                # Ottieni il codice del record selezionato
                selected_codice = master_df.iloc[selected_idx]['Codice']
                st.session_state.selected_record_id = selected_codice

        else:
            st.info("Nessun record trovato con i filtri applicati")

    # === DETAIL PANEL (right 60%) ===
    with col_detail:
        if st.session_state.get('selected_record_id'):
            show_detail_panel(personale_df, filtered_df)
        else:
            st.info("👈 Seleziona un dipendente dalla tabella per visualizzare i dettagli")

            # Mostra form aggiungi nuovo se nessuna selezione
            with st.expander("➕ Aggiungi Nuovo Dipendente", expanded=False):
                show_add_form(personale_df)


def show_detail_panel(personale_df: pd.DataFrame, filtered_df: pd.DataFrame):
    """
    Mostra detail panel con form editabile per record selezionato.
    Organizza i 26 campi in 4 sezioni con progressive disclosure.
    """
    selected_codice = st.session_state.selected_record_id

    # Trova record nel dataframe completo
    record = personale_df[personale_df['Codice'] == selected_codice]

    if len(record) == 0:
        st.error(f"Record con codice {selected_codice} non trovato")
        st.session_state.selected_record_id = None
        return

    record = record.iloc[0]

    st.markdown('<div class="detail-panel">', unsafe_allow_html=True)
    st.markdown(f"### ✏️ Dettagli: {record['Titolare']}")
    st.caption(f"Codice Fiscale: `{record['TxCodFiscale']}`")

    # === SEZIONE 1: DATI ESSENZIALI (sempre aperta) ===
    st.markdown("#### 📋 Dati Essenziali")

    col1, col2 = st.columns(2)

    with col1:
        new_titolare = st.text_input("Nome Dipendente *", value=record['Titolare'] or "", key="edit_titolare")
        new_codice = st.text_input("Codice *", value=record['Codice'] or "", key="edit_codice")

    with col2:
        new_uo = st.text_input("Unità Organizzativa *", value=record['Unità Organizzativa'] or "", key="edit_uo")
        new_padre = st.text_input("Unità Operativa Padre", value=record['UNITA\' OPERATIVA PADRE '] or "", key="edit_padre")

    # === SEZIONE 2: SEDE E ORGANIZZAZIONE (expander) ===
    with st.expander("🏢 Sede e Organizzazione", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            new_sede = st.text_input("Sede TNS", value=record['Sede_TNS'] or "", key="edit_sede")
            new_cdc = st.text_input("Centro di Costo (CDCCOSTO)", value=record['CDCCOSTO'] or "", key="edit_cdc")
            new_societa = st.text_input("Società Esercente", value=record['SocietaEsercente'] or "", key="edit_societa")
            new_tipo_sede = st.text_input("Tipo Sede", value=record['TIPO SEDE'] or "", key="edit_tipo_sede")

        with col2:
            new_uff_amm = st.text_input("Uff. Amm. Appartenenza", value=record['UFF.AMM.APPARTENENZA'] or "", key="edit_uff_amm")
            new_tipo_struttura = st.text_input("Tipo Struttura", value=record['TIPO STRUTTURA'] or "", key="edit_tipo_struttura")
            new_stato_amm = st.text_input("Stato Amministrativo", value=record['STATOAMMINISTRATIVO'] or "", key="edit_stato_amm")
            new_gruppo_sind = st.text_input("Gruppo Sindacale", value=record['GruppoSind'] or "", key="edit_gruppo_sind")

    # === SEZIONE 3: RUOLI E PERMESSI (expander) ===
    with st.expander("🔐 Ruoli e Permessi", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            new_visibilita = st.text_input("Visibilità", value=record['VISIBILITA'] or "", key="edit_visibilita")
            new_tipo_nodo = st.text_input("Tipo Nodo Interno", value=record['TipoNodoInterno'] or "", key="edit_tipo_nodo")
            new_nodo_org_ruolo = st.text_input("Nodo Organigramma Ruolo", value=record['NdoOrganigrammaRuolo'] or "", key="edit_nodo_org_ruolo")
            new_nodo_org_fun = st.text_input("Nodo Organigramma Funzione", value=record['NdoOrganigrammaFunzione'] or "", key="edit_nodo_org_fun")

        with col2:
            new_campo10 = st.text_input("Campo 10", value=record['Campo10'] or "", key="edit_campo10")
            new_campo13 = st.text_input("Campo 13", value=record['Campo13'] or "", key="edit_campo13")
            new_campo14 = st.text_input("Campo 14", value=record['Campo14'] or "", key="edit_campo14")
            new_campo17 = st.text_input("Campo 17", value=record['Campo17'] or "", key="edit_campo17")

    # === SEZIONE 4: ALTRI CAMPI (expander) ===
    with st.expander("📦 Altri Campi", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            new_costo_orario = st.text_input("Costo Orario", value=record['CostoOrario'] or "", key="edit_costo_orario")
            new_campo20 = st.text_input("Campo 20", value=record['Campo20'] or "", key="edit_campo20")
            new_campo21 = st.text_input("Campo 21", value=record['Campo21'] or "", key="edit_campo21")

        with col2:
            new_campo22 = st.text_input("Campo 22", value=record['Campo22'] or "", key="edit_campo22")
            new_campo23 = st.text_input("Campo 23", value=record['Campo23'] or "", key="edit_campo23")
            new_campo24 = st.text_input("Campo 24", value=record['Campo24'] or "", key="edit_campo24")

    st.markdown("---")

    # === BOTTONI AZIONE ===
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        if st.button("💾 Salva Modifiche", type="primary", use_container_width=True):
            # Valida campi obbligatori
            if not all([new_titolare, new_codice, new_uo]):
                st.error("❌ I campi Titolare, Codice e Unità Organizzativa sono obbligatori")
            else:
                # Applica modifiche al dataframe
                idx = personale_df[personale_df['Codice'] == selected_codice].index[0]
                cf_record = personale_df.at[idx, 'TxCodFiscale']

                personale_df.at[idx, 'Titolare'] = new_titolare
                personale_df.at[idx, 'Codice'] = new_codice
                personale_df.at[idx, 'Unità Organizzativa'] = new_uo
                personale_df.at[idx, 'UNITA\' OPERATIVA PADRE '] = new_padre if new_padre else None
                personale_df.at[idx, 'Sede_TNS'] = new_sede if new_sede else None
                personale_df.at[idx, 'CDCCOSTO'] = new_cdc if new_cdc else None
                personale_df.at[idx, 'SocietaEsercente'] = new_societa if new_societa else None
                personale_df.at[idx, 'TIPO SEDE'] = new_tipo_sede if new_tipo_sede else None
                personale_df.at[idx, 'UFF.AMM.APPARTENENZA'] = new_uff_amm if new_uff_amm else None
                personale_df.at[idx, 'TIPO STRUTTURA'] = new_tipo_struttura if new_tipo_struttura else None
                personale_df.at[idx, 'STATOAMMINISTRATIVO'] = new_stato_amm if new_stato_amm else None
                personale_df.at[idx, 'GruppoSind'] = new_gruppo_sind if new_gruppo_sind else None
                personale_df.at[idx, 'VISIBILITA'] = new_visibilita if new_visibilita else None
                personale_df.at[idx, 'TipoNodoInterno'] = new_tipo_nodo if new_tipo_nodo else None
                personale_df.at[idx, 'NdoOrganigrammaRuolo'] = new_nodo_org_ruolo if new_nodo_org_ruolo else None
                personale_df.at[idx, 'NdoOrganigrammaFunzione'] = new_nodo_org_fun if new_nodo_org_fun else None
                personale_df.at[idx, 'Campo10'] = new_campo10 if new_campo10 else None
                personale_df.at[idx, 'Campo13'] = new_campo13 if new_campo13 else None
                personale_df.at[idx, 'Campo14'] = new_campo14 if new_campo14 else None
                personale_df.at[idx, 'Campo17'] = new_campo17 if new_campo17 else None
                personale_df.at[idx, 'CostoOrario'] = new_costo_orario if new_costo_orario else None
                personale_df.at[idx, 'Campo20'] = new_campo20 if new_campo20 else None
                personale_df.at[idx, 'Campo21'] = new_campo21 if new_campo21 else None
                personale_df.at[idx, 'Campo22'] = new_campo22 if new_campo22 else None
                personale_df.at[idx, 'Campo23'] = new_campo23 if new_campo23 else None
                personale_df.at[idx, 'Campo24'] = new_campo24 if new_campo24 else None

                # === PERSISTI NEL DATABASE ===
                try:
                    db_handler = st.session_state.database_handler
                    updates = {
                        'Titolare': new_titolare,
                        'Codice': new_codice,
                        'Unità Organizzativa': new_uo,
                        'UNITA\' OPERATIVA PADRE ': new_padre if new_padre else None,
                        'Sede_TNS': new_sede if new_sede else None,
                        'CDCCOSTO': new_cdc if new_cdc else None,
                        'SocietaEsercente': new_societa if new_societa else None,
                        'TIPO SEDE': new_tipo_sede if new_tipo_sede else None,
                        'UFF.AMM.APPARTENENZA': new_uff_amm if new_uff_amm else None,
                        'TIPO STRUTTURA': new_tipo_struttura if new_tipo_struttura else None,
                        'STATOAMMINISTRATIVO': new_stato_amm if new_stato_amm else None,
                        'GruppoSind': new_gruppo_sind if new_gruppo_sind else None,
                        'VISIBILITA': new_visibilita if new_visibilita else None,
                        'TipoNodoInterno': new_tipo_nodo if new_tipo_nodo else None,
                        'NdoOrganigrammaRuolo': new_nodo_org_ruolo if new_nodo_org_ruolo else None,
                        'NdoOrganigrammaFunzione': new_nodo_org_fun if new_nodo_org_fun else None,
                        'Campo10': new_campo10 if new_campo10 else None,
                        'Campo13': new_campo13 if new_campo13 else None,
                        'Campo14': new_campo14 if new_campo14 else None,
                        'Campo17': new_campo17 if new_campo17 else None,
                        'CostoOrario': new_costo_orario if new_costo_orario else None,
                        'Campo20': new_campo20 if new_campo20 else None,
                        'Campo21': new_campo21 if new_campo21 else None,
                        'Campo22': new_campo22 if new_campo22 else None,
                        'Campo23': new_campo23 if new_campo23 else None,
                        'Campo24': new_campo24 if new_campo24 else None,
                    }
                    db_handler.update_personale(cf_record, updates)
                except Exception as e:
                    st.warning(f"⚠️ Errore persistenza database: {str(e)}")

                st.session_state.personale_df = personale_df
                st.session_state.show_feedback = True
                st.rerun()

    with col2:
        if st.button("🔄 Annulla", use_container_width=True):
            st.session_state.selected_record_id = None
            st.rerun()

    with col3:
        if st.button("🗑️ Elimina", type="secondary", use_container_width=True):
            st.session_state.delete_confirm_id = selected_codice
            st.rerun()

    # Dialog conferma eliminazione
    if st.session_state.get('delete_confirm_id') == selected_codice:
        st.warning(f"⚠️ Confermi eliminazione di **{record['Titolare']}** (CF: {record['TxCodFiscale']})?")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Sì, elimina", type="secondary", use_container_width=True):
                # === ELIMINA DAL DATABASE ===
                try:
                    db_handler = st.session_state.database_handler
                    db_handler.delete_personale(record['TxCodFiscale'])
                except Exception as e:
                    st.warning(f"⚠️ Errore eliminazione database: {str(e)}")

                # Elimina dal dataframe
                personale_df = personale_df[personale_df['Codice'] != selected_codice]
                st.session_state.personale_df = personale_df
                st.session_state.selected_record_id = None
                st.session_state.delete_confirm_id = None
                st.success(f"✅ Dipendente {record['Titolare']} eliminato")
                st.rerun()

        with col2:
            if st.button("❌ Annulla", use_container_width=True):
                st.session_state.delete_confirm_id = None
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


def show_add_form(personale_df: pd.DataFrame):
    """Form per aggiungere nuovo dipendente"""

    with st.form("add_personale_form"):
        st.markdown("#### Dati Essenziali")

        col1, col2 = st.columns(2)

        with col1:
            new_cf = st.text_input("Codice Fiscale *", max_chars=16)
            new_titolare = st.text_input("Nome Dipendente *")

        with col2:
            new_codice = st.text_input("Codice *")
            new_uo = st.text_input("Unità Organizzativa *")

        st.markdown("#### Dati Opzionali")

        col1, col2 = st.columns(2)

        with col1:
            new_padre = st.text_input("Unità Operativa Padre")
            new_sede = st.text_input("Sede TNS")

        with col2:
            new_cdc = st.text_input("Centro di Costo")
            new_gruppo = st.text_input("Gruppo Sindacale")

        submitted = st.form_submit_button("➕ Aggiungi Dipendente", type="primary", use_container_width=True)

        if submitted:
            if not all([new_cf, new_titolare, new_codice, new_uo]):
                st.error("❌ Compila tutti i campi obbligatori (*)")
            else:
                # Crea nuovo record con tutte le colonne
                new_record = pd.Series({col: None for col in personale_df.columns})
                new_record['TxCodFiscale'] = new_cf.strip().upper()
                new_record['Titolare'] = new_titolare.strip()
                new_record['Codice'] = new_codice.strip()
                new_record['Unità Organizzativa'] = new_uo.strip()
                new_record['UNITA\' OPERATIVA PADRE '] = new_padre.strip() if new_padre else None
                new_record['Sede_TNS'] = new_sede.strip() if new_sede else None
                new_record['CDCCOSTO'] = new_cdc.strip() if new_cdc else None
                new_record['GruppoSind'] = new_gruppo.strip() if new_gruppo else None

                # === INSERISCI NEL DATABASE ===
                try:
                    db_handler = st.session_state.database_handler
                    record_dict = new_record.to_dict()
                    db_handler.insert_personale(record_dict)
                except Exception as e:
                    st.warning(f"⚠️ Errore inserimento database: {str(e)}")

                # Aggiungi al dataframe
                personale_df = pd.concat([personale_df, new_record.to_frame().T], ignore_index=True)
                st.session_state.personale_df = personale_df

                st.success(f"✅ Dipendente {new_titolare} aggiunto")
                st.session_state.show_feedback = True
                st.rerun()


# === FEEDBACK ACTIONABLE (mostra dopo salvataggio) ===
# Viene mostrato nell'app.py principale o nella view stessa dopo modifiche
def show_feedback_banner():
    """Mostra banner con azioni successive dopo modifiche"""
    if st.session_state.get('show_feedback'):
        st.success("✅ Modifiche applicate al Personale")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🔄 Rigenera DB_TNS", use_container_width=True):
                # Navigation alla vista merger
                st.session_state.show_feedback = False
                st.switch_page("pages/5_🔄_Genera_DB_TNS.py")  # Se usando pagine Streamlit

        with col2:
            if st.button("💾 Salva su File", use_container_width=True):
                st.session_state.show_feedback = False
                st.switch_page("pages/6_💾_Salvataggio_Export.py")

        with col3:
            if st.button("➕ Aggiungi Altro", use_container_width=True):
                st.session_state.show_feedback = False
                st.session_state.selected_record_id = None
                st.rerun()
