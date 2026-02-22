"""
Vista Gestione Posizioni Organizzative
Gestisce le posizioni organizzative (ID) con associazione opzionale a dipendente
"""
import streamlit as st
import pandas as pd
from services.database import DatabaseHandler


def show_posizioni_view():
    """
    Vista principale per gestione posizioni organizzative

    Campi chiave:
    - ID (chiave primaria)
    - Titolo unità organizzativa (DESCRIZIONE o nome posizione)
    - Associazione dipendente (se presente): TxCodFiscale, Titolare
    """
    st.markdown("## 📍 Gestione Posizioni Organizzative")
    st.caption("Gestisci le posizioni organizzative, sia vacanti che occupate da dipendenti")

    # Get personale dataframe with safety check
    personale_df = st.session_state.get('personale_df')

    if personale_df is None:
        st.warning("⚠️ Nessun dato disponibile. Importa un file Excel per iniziare.")
        return

    db = st.session_state.database_handler
    personale_df = personale_df.copy()

    # Mappa delle colonne dal file DB_ORG
    # Cerca la colonna ID (dopo import viene rinominata in 'codice')
    id_col = None

    # Priorità: cerca prima 'codice' (nome dopo import), poi 'ID' (nome originale)
    id_candidates = ['codice', 'ID', 'Id', 'id', 'ID ', ' ID']

    for candidate in id_candidates:
        if candidate in personale_df.columns:
            id_col = candidate
            break

    if id_col is None:
        st.error("❌ Colonna 'ID' non trovata nel dataset.")
        st.warning("⚠️ La colonna ID (colonna AB del file DB_ORG) è necessaria per gestire le posizioni organizzative.")
        st.info("💡 Importa un file DB_ORG completo dalla sezione 'Import DB_ORG'")

        with st.expander("🔍 Colonne disponibili"):
            st.dataframe(pd.DataFrame({'Colonna': personale_df.columns}), use_container_width=True)

        return

    # Trova le colonne da usare
    # Nota: L'import DB_ORG rinomina alcune colonne:
    # ID → codice, TxCodFiscale → tx_cod_fiscale, ReportsTo → reports_to_codice
    columns_map = {
        'id': id_col,  # Colonna AB: 'codice' (dopo import) o 'ID' (originale)
        'org_level1': None,  # Colonna B
        'org_level2': None,  # Colonna C
        'reports_to': None,  # Colonna AC
        'cf': None,  # Codice Fiscale
        'titolare': None,  # Titolare
        'cognome': None,  # Cognome
        'nome': None  # Nome
    }

    # Cerca CF (può essere TxCodFiscale o tx_cod_fiscale dopo import)
    for cf_var in ['tx_cod_fiscale', 'TxCodFiscale', 'txcodfiscale']:
        if cf_var in personale_df.columns:
            columns_map['cf'] = cf_var
            break

    # Cerca Titolare
    for tit_var in ['titolare', 'Titolare']:
        if tit_var in personale_df.columns:
            columns_map['titolare'] = tit_var
            break

    # Cerca Cognome/Nome
    for cog_var in ['cognome', 'Cognome']:
        if cog_var in personale_df.columns:
            columns_map['cognome'] = cog_var
            break

    for nom_var in ['nome', 'Nome']:
        if nom_var in personale_df.columns:
            columns_map['nome'] = nom_var
            break

    # Identifica colonne B e C (primi livelli organizzativi)
    # Dopo import: 'Unità Organizzativa' → 'unita_org_livello1', 'Unità Organizzativa 2' → 'unita_org_livello2'

    # Cerca con nomi post-import
    for level1_var in ['unita_org_livello1', 'Unità Organizzativa', 'unita_organizzativa']:
        if level1_var in personale_df.columns:
            columns_map['org_level1'] = level1_var
            break

    for level2_var in ['unita_org_livello2', 'Unità Organizzativa 2', 'unita_organizzativa_2']:
        if level2_var in personale_df.columns:
            columns_map['org_level2'] = level2_var
            break

    # Se non trovate, cerca con pattern generici
    if columns_map['org_level1'] is None:
        for col in personale_df.columns:
            col_lower = col.lower()
            if ('livello' in col_lower and '1' in col_lower) or ('level' in col_lower and '1' in col_lower):
                columns_map['org_level1'] = col
                break

    if columns_map['org_level2'] is None:
        for col in personale_df.columns:
            col_lower = col.lower()
            if ('livello' in col_lower and '2' in col_lower) or ('level' in col_lower and '2' in col_lower):
                columns_map['org_level2'] = col
                break

    # Cerca Reports To (dopo import: 'ReportsTo' → 'reports_to_codice')
    for reports_var in ['reports_to_codice', 'ReportsTo', 'reports_to', 'reportsto']:
        if reports_var in personale_df.columns:
            columns_map['reports_to'] = reports_var
            break

    # Se non trovato con nomi specifici, cerca pattern
    if columns_map['reports_to'] is None:
        for col in personale_df.columns:
            col_lower = col.lower()
            if 'reports' in col_lower or 'riporta' in col_lower:
                columns_map['reports_to'] = col
                break

    # Filtra solo righe con ID presente (posizioni organizzative)
    posizioni_df = personale_df[personale_df[id_col].notna()].copy()

    if len(posizioni_df) == 0:
        st.warning("⚠️ Nessuna posizione organizzativa trovata nel database.")
        st.info(f"Le posizioni organizzative sono righe con la colonna '{id_col}' valorizzata.")
        return

    # === STATISTICHE ===
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "📍 Posizioni Totali",
            len(posizioni_df),
            help="Tutte le posizioni organizzative (vacanti + occupate)"
        )

    with col2:
        # Posizioni occupate (con CF e Titolare)
        if columns_map['cf']:
            occupate = posizioni_df[columns_map['cf']].notna().sum()
        else:
            occupate = 0

        st.metric(
            "👤 Occupate",
            occupate,
            help="Posizioni con dipendente assegnato (con Codice Fiscale)"
        )

    with col3:
        # Posizioni vacanti (senza CF)
        vacanti = len(posizioni_df) - occupate
        st.metric(
            "⭕ Vacanti",
            vacanti,
            help="Posizioni senza dipendente assegnato"
        )

    with col4:
        # Percentuale occupazione
        if len(posizioni_df) > 0:
            perc_occupazione = (occupate / len(posizioni_df)) * 100
        else:
            perc_occupazione = 0

        st.metric(
            "📊 Tasso Occupazione",
            f"{perc_occupazione:.1f}%",
            help="Percentuale posizioni occupate"
        )

    st.markdown("---")

    # === FILTRI ===
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        filtro_tipo = st.radio(
            "Mostra",
            options=["Tutte", "Solo Occupate", "Solo Vacanti"],
            horizontal=True,
            label_visibility="collapsed"
        )

    with col2:
        search_term = st.text_input(
            "🔍 Cerca",
            placeholder="Cerca per ID, titolo, nome dipendente...",
            label_visibility="collapsed"
        )

    with col3:
        st.markdown("&nbsp;")  # Spacer
        if st.button("🔄 Aggiorna", use_container_width=True):
            st.rerun()

    # Applica filtri
    filtered_df = posizioni_df.copy()

    if filtro_tipo == "Solo Occupate":
        if columns_map['cf']:
            filtered_df = filtered_df[filtered_df[columns_map['cf']].notna()]
    elif filtro_tipo == "Solo Vacanti":
        if columns_map['cf']:
            filtered_df = filtered_df[filtered_df[columns_map['cf']].isna()]

    if search_term:
        # Cerca nelle colonne disponibili
        search_cols = [columns_map['id']]  # ID sempre presente

        # Aggiungi altre colonne se disponibili
        if columns_map['org_level1']:
            search_cols.append(columns_map['org_level1'])
        if columns_map['org_level2']:
            search_cols.append(columns_map['org_level2'])
        if columns_map['titolare']:
            search_cols.append(columns_map['titolare'])
        if columns_map['cf']:
            search_cols.append(columns_map['cf'])
        if columns_map['cognome']:
            search_cols.append(columns_map['cognome'])
        if columns_map['nome']:
            search_cols.append(columns_map['nome'])

        mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
        for col in search_cols:
            mask |= filtered_df[col].astype(str).str.contains(search_term, case=False, na=False)

        filtered_df = filtered_df[mask]

    st.caption(f"Visualizzate {len(filtered_df)} posizioni su {len(posizioni_df)} totali")

    # === TABELLA POSIZIONI ===

    # Prepara colonne da visualizzare secondo la specifica dell'utente:
    # - ID (colonna AB) - chiave primaria
    # - Unità organizzativa livello 1 (colonna B)
    # - Unità organizzativa livello 2 (colonna C)
    # - Se presente dipendente: CF, Nome, Cognome
    # - Reports To (colonna AC)

    display_cols = [columns_map['id']]  # ID sempre visibile

    # Aggiungi colonne nell'ordine specificato
    if columns_map['org_level1']:
        display_cols.append(columns_map['org_level1'])

    if columns_map['org_level2']:
        display_cols.append(columns_map['org_level2'])

    if columns_map['cf']:
        display_cols.append(columns_map['cf'])

    if columns_map['titolare']:
        display_cols.append(columns_map['titolare'])
    elif columns_map['cognome'] and columns_map['nome']:
        # Se non c'è Titolare, usa Cognome e Nome separati
        display_cols.append(columns_map['cognome'])
        display_cols.append(columns_map['nome'])

    if columns_map['reports_to']:
        display_cols.append(columns_map['reports_to'])

    # Aggiungi altre colonne utili se presenti
    optional_extra_cols = ['Area', 'Sede_TNS', 'Qualifica', 'DESCRIZIONE']
    for col in optional_extra_cols:
        if col in filtered_df.columns and col not in display_cols:
            display_cols.append(col)

    # Configura editor con i nomi effettivi delle colonne
    column_config = {
        columns_map['id']: st.column_config.TextColumn(
            "ID Posizione",
            help="Identificativo univoco posizione organizzativa (colonna AB)",
            width="medium",
            disabled=True  # ID non modificabile
        )
    }

    # Aggiungi config per le colonne presenti
    if columns_map['org_level1']:
        column_config[columns_map['org_level1']] = st.column_config.TextColumn(
            "Unità Org. Livello 1",
            help="Unità organizzativa primo livello (colonna B)",
            width="large"
        )

    if columns_map['org_level2']:
        column_config[columns_map['org_level2']] = st.column_config.TextColumn(
            "Unità Org. Livello 2",
            help="Unità organizzativa secondo livello (colonna C)",
            width="large"
        )

    if columns_map['cf']:
        column_config[columns_map['cf']] = st.column_config.TextColumn(
            "Codice Fiscale",
            help="CF dipendente assegnato alla posizione",
            width="medium"
        )

    if columns_map['titolare']:
        column_config[columns_map['titolare']] = st.column_config.TextColumn(
            "Titolare Posizione",
            help="Nome dipendente assegnato",
            width="large"
        )

    if columns_map['reports_to']:
        column_config[columns_map['reports_to']] = st.column_config.TextColumn(
            "Reports To",
            help="Riferimento gerarchico superiore (colonna AC)",
            width="medium"
        )

    # Data editor
    edited_df = st.data_editor(
        filtered_df[display_cols],
        use_container_width=True,
        height=600,
        column_config=column_config,
        num_rows="fixed",  # Non permettere aggiunta/rimozione righe qui
        key="posizioni_editor"
    )

    # === AZIONI ===
    st.markdown("---")

    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

    with col1:
        if st.button("💾 Salva Modifiche", type="primary", use_container_width=True):
            if save_positions_changes(edited_df, filtered_df, personale_df):
                st.success("✅ Modifiche salvate con successo!")
                st.rerun()
            else:
                st.error("❌ Errore durante il salvataggio")

    with col2:
        if st.button("➕ Nuova Posizione", use_container_width=True):
            st.session_state.show_new_position_form = True
            st.rerun()

    with col3:
        if st.button("📋 Esporta Posizioni", use_container_width=True):
            # Export filtrato
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                "⬇️ Download CSV",
                csv,
                "posizioni_organizzative.csv",
                "text/csv",
                use_container_width=True
            )

    with col4:
        if st.button("🔄 Reset Filtri", use_container_width=True):
            st.rerun()

    # === FORM NUOVA POSIZIONE ===
    if st.session_state.get('show_new_position_form', False):
        show_new_position_form()


def show_new_position_form():
    """Form per creare una nuova posizione organizzativa"""
    st.markdown("---")
    st.markdown("### ➕ Nuova Posizione Organizzativa")

    with st.form("new_position_form"):
        col1, col2 = st.columns(2)

        with col1:
            new_id = st.text_input(
                "ID Posizione *",
                placeholder="Es: POS001",
                help="Identificativo univoco della posizione"
            )

            new_descrizione = st.text_input(
                "Titolo/Descrizione *",
                placeholder="Es: Responsabile Area Marketing",
                help="Titolo o descrizione della posizione"
            )

        with col2:
            # Opzionale: assegna dipendente esistente
            personale_df = st.session_state.personale_df
            dipendenti_list = ["-- Nessuno (posizione vacante) --"]

            if 'Titolare' in personale_df.columns and 'TxCodFiscale' in personale_df.columns:
                dipendenti_disponibili = personale_df[
                    personale_df['TxCodFiscale'].notna()
                ][['TxCodFiscale', 'Titolare']].drop_duplicates()

                dipendenti_list.extend([
                    f"{row['Titolare']} ({row['TxCodFiscale']})"
                    for _, row in dipendenti_disponibili.iterrows()
                ])

            dipendente_assegnato = st.selectbox(
                "Assegna Dipendente",
                options=dipendenti_list,
                help="Opzionale: assegna un dipendente esistente"
            )

            padre = st.text_input(
                "Unità Operativa Padre",
                placeholder="Codice unità padre (opzionale)",
                help="Gerarchia organizzativa"
            )

        col1, col2 = st.columns(2)

        with col1:
            submitted = st.form_submit_button(
                "💾 Crea Posizione",
                type="primary",
                use_container_width=True
            )

        with col2:
            cancelled = st.form_submit_button(
                "❌ Annulla",
                use_container_width=True
            )

        if submitted:
            # Validazione
            if not new_id or not new_descrizione:
                st.error("❌ ID e Descrizione sono obbligatori")
            else:
                # Crea nuova posizione
                if create_new_position(new_id, new_descrizione, dipendente_assegnato, padre):
                    st.success(f"✅ Posizione '{new_descrizione}' creata!")
                    st.session_state.show_new_position_form = False
                    st.rerun()
                else:
                    st.error("❌ Errore durante la creazione")

        if cancelled:
            st.session_state.show_new_position_form = False
            st.rerun()


def save_positions_changes(edited_df, original_filtered_df, full_personale_df):
    """Salva le modifiche alle posizioni nel database"""
    try:
        db = st.session_state.database_handler

        # Trova le righe modificate confrontando i dataframe
        # Aggiorna solo i campi modificabili (non ID)

        for idx in edited_df.index:
            if idx in original_filtered_df.index:
                # Controlla se ci sono state modifiche
                original_row = original_filtered_df.loc[idx]
                edited_row = edited_df.loc[idx]

                # Campi che possono essere modificati
                modifiable_fields = ['DESCRIZIONE', 'TxCodFiscale', 'Titolare', 'Cognome', 'Nome', 'Area', 'Sede_TNS', 'Qualifica']

                changes = {}
                for field in modifiable_fields:
                    if field in edited_row.index and field in original_row.index:
                        if pd.notna(edited_row[field]) and edited_row[field] != original_row[field]:
                            changes[field] = edited_row[field]

                if changes:
                    # Aggiorna nel dataframe principale
                    for field, value in changes.items():
                        if field in full_personale_df.columns:
                            full_personale_df.at[idx, field] = value

                    # Salva nel database
                    position_id = original_row['ID']
                    # Usa la tabella appropriata (DB_ORG o simile)
                    # Per ora aggiorniamo il session state
                    st.session_state.personale_df = full_personale_df

        return True

    except Exception as e:
        st.error(f"Errore durante il salvataggio: {str(e)}")
        return False


def create_new_position(position_id, descrizione, dipendente_assegnato, padre=None):
    """Crea una nuova posizione organizzativa"""
    try:
        db = st.session_state.database_handler
        personale_df = st.session_state.personale_df

        # Verifica che ID non esista già
        if 'ID' in personale_df.columns:
            if position_id in personale_df['ID'].values:
                st.error(f"❌ ID '{position_id}' già esistente")
                return False

        # Prepara nuova riga
        new_row = {'ID': position_id, 'DESCRIZIONE': descrizione}

        # Aggiungi padre se specificato
        if padre:
            new_row['UNITA\' OPERATIVA PADRE '] = padre

        # Se dipendente assegnato, estrai CF
        if dipendente_assegnato and dipendente_assegnato != "-- Nessuno (posizione vacante) --":
            # Estrai CF dalla stringa "Nome (CF)"
            import re
            cf_match = re.search(r'\(([A-Z0-9]{16})\)', dipendente_assegnato)
            if cf_match:
                cf = cf_match.group(1)
                # Trova dipendente e copia i suoi dati
                dipendente_row = personale_df[personale_df['TxCodFiscale'] == cf]
                if not dipendente_row.empty:
                    for col in dipendente_row.columns:
                        if col != 'ID':  # Non copiare ID
                            new_row[col] = dipendente_row.iloc[0][col]

        # Aggiungi al dataframe
        new_row_df = pd.DataFrame([new_row])
        st.session_state.personale_df = pd.concat([personale_df, new_row_df], ignore_index=True)

        return True

    except Exception as e:
        st.error(f"Errore durante la creazione: {str(e)}")
        return False
