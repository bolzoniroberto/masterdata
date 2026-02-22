"""
UI per gestione TNS Personale con Master-Detail pattern.
Layout: Master table (40%) + Detail panel (60%) per UX migliorata.
"""
import streamlit as st
import pandas as pd
from services.validator import DataValidator
from ui.styles import render_filter_badge
from services.database import DatabaseHandler


def save_changes_to_db(original_df, edited_df, full_df):
    """Save edited dataframe changes to database"""
    db = DatabaseHandler()
    conn = db.get_connection()
    cursor = conn.cursor()

    try:
        # Find changed rows by comparing dataframes
        changes_count = 0
        for idx in edited_df.index:
            if idx >= len(original_df):
                # New row added
                continue  # TODO: Handle new rows

            # Check if row was modified
            original_row = original_df.iloc[idx]
            edited_row = edited_df.iloc[idx]

            if not original_row.equals(edited_row):
                # Row was modified - get the ID
                if 'TxCodFiscale' in edited_row:
                    cf = edited_row['TxCodFiscale']

                    # Build UPDATE query dynamically based on changed columns
                    updates = []
                    params = []

                    # Map display column names to database column names
                    column_mapping = {
                        'Titolare': 'titolare',
                        'Qualifica': 'qualifica',
                        'Area': 'area',
                        'Sede': 'sede',
                        'Email': 'email',
                        'Matricola': 'matricola',
                        'CF Responsabile Diretto': 'reports_to_cf',
                        'Codice TNS': 'cod_tns',
                        'Padre TNS': 'padre_tns',
                        'Società': 'societa',
                        'SottoArea': 'sottoarea',
                        'Contratto': 'contratto',
                        'RAL': 'ral',
                        'Sesso': 'sesso',
                    }

                    for col in edited_row.index:
                        if col in column_mapping and str(original_row[col]) != str(edited_row[col]):
                            db_col = column_mapping[col]
                            updates.append(f"{db_col} = ?")
                            params.append(edited_row[col] if edited_row[col] != '' else None)

                    if updates:
                        params.append(cf)  # For WHERE clause
                        query = f"UPDATE employees SET {', '.join(updates)} WHERE tx_cod_fiscale = ?"
                        cursor.execute(query, params)
                        changes_count += 1

        conn.commit()
        return changes_count

    except Exception as e:
        conn.rollback()
        st.error(f"❌ Errore durante il salvataggio: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return 0


def show_personale_view():
    """UI per gestione dipendenti con master-detail pattern"""

    st.caption("Seleziona un record dalla tabella per visualizzare e modificare i dettagli")

    # Get personale dataframe with safety check
    personale_df = st.session_state.get('personale_df')

    if personale_df is None:
        st.warning("⚠️ Nessun dato disponibile. Importa un file Excel per iniziare.")
        return

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
        # Use 'Sede' column (loaded from employees.sede)
        sedi = personale_df['Sede'].nunique() if 'Sede' in personale_df.columns else 0
        st.metric("Sedi", sedi)

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
        # Use 'Sede' column instead of 'Sede'
        sede_options = sorted(personale_df['Sede'].dropna().unique()) if 'Sede' in personale_df.columns else []
        filter_sede = st.multiselect(
            "Sede",
            options=sede_options,
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
        filtered_df = filtered_df[filtered_df['Sede'].isin(filter_sede)]

    render_filter_badge(len(filtered_df), len(personale_df))

    # === COLUMN SELECTOR ===
    with st.expander("🎛️ Seleziona Colonne da Visualizzare", expanded=False):
        st.markdown("**Personalizza la vista selezionando le colonne:**")

        # Get all available columns
        all_columns = list(personale_df.columns)

        # Default columns (most important)
        default_columns = ['Codice', 'TxCodFiscale', 'Titolare', 'Qualifica', 'Unità Organizzativa', 'Sede']
        # Keep only defaults that exist in dataframe
        default_columns = [col for col in default_columns if col in all_columns]

        # Get saved selection from session state or use defaults
        if 'personale_selected_columns' not in st.session_state:
            st.session_state.personale_selected_columns = default_columns

        # Column selector
        col1, col2, col3 = st.columns([4, 1, 1])

        with col1:
            selected_columns = st.multiselect(
                "Colonne da visualizzare nella lista",
                options=all_columns,
                default=st.session_state.personale_selected_columns,
                key="column_selector",
                help="Seleziona le colonne da mostrare nella tabella"
            )

        with col2:
            if st.button("↻ Reset", use_container_width=True, help="Ripristina colonne predefinite"):
                st.session_state.personale_selected_columns = default_columns
                st.rerun()

        with col3:
            if st.button("☑ Tutte", use_container_width=True, help="Seleziona tutte le colonne"):
                st.session_state.personale_selected_columns = all_columns
                st.rerun()

        # Save selection
        if selected_columns:
            st.session_state.personale_selected_columns = selected_columns

        st.caption(f"📊 {len(selected_columns or default_columns)} colonne selezionate su {len(all_columns)} disponibili")

    # Use selected columns or fall back to defaults
    columns_to_show = st.session_state.personale_selected_columns if st.session_state.personale_selected_columns else default_columns

    # === FULL-WIDTH TABLE ===
    st.markdown("### 📋 Lista Dipendenti")

    if len(filtered_df) > 0:
        # Create dynamic dataframe with selected columns
        display_df = filtered_df[columns_to_show].copy()
        display_df = display_df.reset_index(drop=True)

        # Build dynamic column config with editability
        column_config = {}
        disabled_columns = ['Codice']  # ID columns that should not be edited

        for col in columns_to_show:
            # Determine width based on column type/name
            if col in ['Codice', 'Sede', 'Sesso', 'Matricola']:
                width = 'small'
            elif col in ['TxCodFiscale', 'Qualifica', 'Area', 'CF Responsabile Diretto', 'Codice TNS', 'Padre TNS']:
                width = 'medium'
            elif col in ['Titolare', 'Unità Organizzativa', 'Email']:
                width = 'large'
            else:
                width = 'medium'

            # Number columns
            if col in ['RAL', 'FTE']:
                column_config[col] = st.column_config.NumberColumn(
                    col,
                    width=width,
                    disabled=(col in disabled_columns)
                )
            # Date columns
            elif col in ['Data Assunzione', 'Data Cessazione']:
                column_config[col] = st.column_config.DateColumn(
                    col,
                    width=width,
                    format="DD/MM/YYYY"
                )
            # Text columns
            else:
                column_config[col] = st.column_config.TextColumn(
                    col,
                    width=width,
                    disabled=(col in disabled_columns)
                )

        # Mostra tabella EDITABILE (tipo Excel!)
        edited_df = st.data_editor(
            display_df,
            use_container_width=True,
            height=600,
            hide_index=True,
            column_config=column_config,
            num_rows="dynamic",  # Allow adding/deleting rows
            key="employee_editor"
        )

        # Detect changes and show save button
        # DEBUG: Show if DataFrames are different
        are_different = not edited_df.equals(display_df)

        # More robust change detection (handle NaN and type differences)
        changes_detected = False
        try:
            # Reset index to ensure alignment
            ed = edited_df.reset_index(drop=True)
            di = display_df.reset_index(drop=True)

            # Check shape first
            if ed.shape != di.shape:
                changes_detected = True
            else:
                # Compare values with fillna to handle NaN
                for col in ed.columns:
                    if col in di.columns:
                        # Convert to string and compare to handle type differences
                        ed_col = ed[col].fillna('').astype(str)
                        di_col = di[col].fillna('').astype(str)
                        if not ed_col.equals(di_col):
                            changes_detected = True
                            break
        except Exception as e:
            st.error(f"Errore nel rilevare modifiche: {e}")
            changes_detected = are_different

        # DEBUG INFO
        with st.expander("🔍 Debug Info", expanded=False):
            st.write(f"equals() result: {not are_different}")
            st.write(f"Custom detection: {changes_detected}")
            st.write(f"Original shape: {display_df.shape}")
            st.write(f"Edited shape: {edited_df.shape}")

        if changes_detected:
            st.warning(f"⚠️ **Hai modifiche non salvate!** Clicca 'Salva Modifiche' per applicarle al database.")

            col1, col2, col3 = st.columns([1, 1, 4])

            with col1:
                if st.button("💾 Salva Modifiche", type="primary", use_container_width=True):
                    with st.spinner("Salvataggio in corso..."):
                        changes_count = save_changes_to_db(display_df, edited_df, personale_df)
                        if changes_count > 0:
                            st.success(f"✅ {changes_count} record aggiornati nel database!")
                            # Force reload data from DB
                            st.session_state.data_loaded = False
                            st.rerun()
                        else:
                            st.warning("⚠️ Nessuna modifica rilevata da salvare")

            with col2:
                if st.button("✕ Annulla", use_container_width=True):
                    st.rerun()
        else:
            st.info("✓ Nessuna modifica pendente. Modifica le celle nella tabella sopra per vedere il pulsante Salva.")

    else:
        st.info("Nessun record trovato con i filtri applicati")

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
    st.markdown(f"### ✏️ Dettagli: {record.get('Titolare', 'N/A')}")
    st.caption(f"Codice Fiscale: `{record.get('TxCodFiscale', 'N/A')}`")

    # === SEZIONE 1: DATI ESSENZIALI (sempre aperta) ===
    st.markdown("#### 📋 Dati Essenziali")

    col1, col2 = st.columns(2)

    with col1:
        new_titolare = st.text_input("Nome Dipendente *", value=record.get('Titolare', '') or "", key="edit_titolare")
        new_codice = st.text_input("Codice *", value=record.get('Codice', '') or "", key="edit_codice")

    with col2:
        new_uo = st.text_input("Unità Organizzativa *", value=record.get('Unità Organizzativa', '') or "", key="edit_uo")
        new_padre = st.text_input("Unità Operativa Padre", value=record.get('UNITA\' OPERATIVA PADRE ', '') or "", key="edit_padre")

    # === SEZIONE 2: SEDE E ORGANIZZAZIONE (expander) ===
    with st.expander("🏢 Sede e Organizzazione", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            new_sede = st.text_input("Sede TNS", value=record.get('Sede', '') or "", key="edit_sede")
            new_cdc = st.text_input("Centro di Costo (CDCCOSTO)", value=record.get('CDCCOSTO', '') or "", key="edit_cdc")
            new_societa = st.text_input("Società Esercente", value=record.get('SocietaEsercente', '') or "", key="edit_societa")
            new_tipo_sede = st.text_input("Tipo Sede", value=record.get('TIPO SEDE', '') or "", key="edit_tipo_sede")

        with col2:
            new_uff_amm = st.text_input("Uff. Amm. Appartenenza", value=record.get('UFF.AMM.APPARTENENZA', '') or "", key="edit_uff_amm")
            new_tipo_struttura = st.text_input("Tipo Struttura", value=record.get('TIPO STRUTTURA', '') or "", key="edit_tipo_struttura")
            new_stato_amm = st.text_input("Stato Amministrativo", value=record.get('STATOAMMINISTRATIVO', '') or "", key="edit_stato_amm")
            new_gruppo_sind = st.text_input("Gruppo Sindacale", value=record.get('GruppoSind', '') or "", key="edit_gruppo_sind")

    # === SEZIONE 3: RUOLI E PERMESSI (expander) ===
    with st.expander("🔐 Ruoli e Permessi", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            new_visibilita = st.text_input("Visibilità", value=record.get('VISIBILITA', '') or "", key="edit_visibilita")
            new_tipo_nodo = st.text_input("Tipo Nodo Interno", value=record.get('TipoNodoInterno', '') or "", key="edit_tipo_nodo")
            new_nodo_org_ruolo = st.text_input("Nodo Organigramma Ruolo", value=record.get('NdoOrganigrammaRuolo', '') or "", key="edit_nodo_org_ruolo")
            new_nodo_org_fun = st.text_input("Nodo Organigramma Funzione", value=record.get('NdoOrganigrammaFunzione', '') or "", key="edit_nodo_org_fun")

        with col2:
            new_campo10 = st.text_input("Campo 10", value=record.get('Campo10', '') or "", key="edit_campo10")
            new_campo13 = st.text_input("Campo 13", value=record.get('Campo13', '') or "", key="edit_campo13")
            new_campo14 = st.text_input("Campo 14", value=record.get('Campo14', '') or "", key="edit_campo14")
            new_campo17 = st.text_input("Campo 17", value=record.get('Campo17', '') or "", key="edit_campo17")

    # === SEZIONE 4: ALTRI CAMPI (expander) ===
    with st.expander("📦 Altri Campi", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            new_costo_orario = st.text_input("Costo Orario", value=record.get('CostoOrario', '') or "", key="edit_costo_orario")
            new_campo20 = st.text_input("Campo 20", value=record.get('Campo20', '') or "", key="edit_campo20")
            new_campo21 = st.text_input("Campo 21", value=record.get('Campo21', '') or "", key="edit_campo21")

        with col2:
            new_campo22 = st.text_input("Campo 22", value=record.get('Campo22', '') or "", key="edit_campo22")
            new_campo23 = st.text_input("Campo 23", value=record.get('Campo23', '') or "", key="edit_campo23")
            new_campo24 = st.text_input("Campo 24", value=record.get('Campo24', '') or "", key="edit_campo24")

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
                cf_record = personale_df.at[idx, 'TxCodFiscale'] if 'TxCodFiscale' in personale_df.columns else None

                # Helper function per settare solo colonne esistenti
                def set_if_exists(col, val):
                    if col in personale_df.columns:
                        personale_df.at[idx, col] = val

                set_if_exists('Titolare', new_titolare)
                set_if_exists('Codice', new_codice)
                set_if_exists('Unità Organizzativa', new_uo)
                set_if_exists('UNITA\' OPERATIVA PADRE ', new_padre if new_padre else None)
                set_if_exists('Sede', new_sede if new_sede else None)
                set_if_exists('CDCCOSTO', new_cdc if new_cdc else None)
                set_if_exists('SocietaEsercente', new_societa if new_societa else None)
                set_if_exists('TIPO SEDE', new_tipo_sede if new_tipo_sede else None)
                set_if_exists('UFF.AMM.APPARTENENZA', new_uff_amm if new_uff_amm else None)
                set_if_exists('TIPO STRUTTURA', new_tipo_struttura if new_tipo_struttura else None)
                set_if_exists('STATOAMMINISTRATIVO', new_stato_amm if new_stato_amm else None)
                set_if_exists('GruppoSind', new_gruppo_sind if new_gruppo_sind else None)
                set_if_exists('VISIBILITA', new_visibilita if new_visibilita else None)
                set_if_exists('TipoNodoInterno', new_tipo_nodo if new_tipo_nodo else None)
                set_if_exists('NdoOrganigrammaRuolo', new_nodo_org_ruolo if new_nodo_org_ruolo else None)
                set_if_exists('NdoOrganigrammaFunzione', new_nodo_org_fun if new_nodo_org_fun else None)
                set_if_exists('Campo10', new_campo10 if new_campo10 else None)
                set_if_exists('Campo13', new_campo13 if new_campo13 else None)
                set_if_exists('Campo14', new_campo14 if new_campo14 else None)
                set_if_exists('Campo17', new_campo17 if new_campo17 else None)
                set_if_exists('CostoOrario', new_costo_orario if new_costo_orario else None)
                set_if_exists('Campo20', new_campo20 if new_campo20 else None)
                set_if_exists('Campo21', new_campo21 if new_campo21 else None)
                set_if_exists('Campo22', new_campo22 if new_campo22 else None)
                set_if_exists('Campo23', new_campo23 if new_campo23 else None)
                set_if_exists('Campo24', new_campo24 if new_campo24 else None)

                # === PERSISTI NEL DATABASE ===
                try:
                    db_handler = st.session_state.database_handler

                    # Costruisci updates solo per colonne esistenti
                    all_updates = {
                        'Titolare': new_titolare,
                        'Codice': new_codice,
                        'Unità Organizzativa': new_uo,
                        'UNITA\' OPERATIVA PADRE ': new_padre if new_padre else None,
                        'Sede': new_sede if new_sede else None,
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

                    # Filtra solo colonne esistenti nel DataFrame
                    updates = {k: v for k, v in all_updates.items() if k in personale_df.columns}
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
                new_record['Sede'] = new_sede.strip() if new_sede else None
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
