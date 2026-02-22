"""
Vista Streamlit: Confronto File Excel + Storico Modifiche.
View consolidata con due tabs:
1. Confronto File: upload manuale 2 file e confronta
2. Storico Modifiche: visualizza audit log database
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import tempfile
from datetime import datetime
from services.excel_handler import ExcelHandler
from services.file_differ import FileDiffer, DiffResult
from services.change_report_generator import ChangeReportGenerator

def show_comparison_audit_view():
    """
    View consolidata: Confronto File + Storico Modifiche.

    Tabs:
    1. Confronto File: Upload 2 file Excel e confronta manualmente
    2. Storico Modifiche: Visualizza audit log database con filtri e report
    """
    st.caption("Analizza differenze tra file e visualizza storico modifiche database")

    # Tabs per funzionalità separate
    tab1, tab2 = st.tabs(["📂 Confronto File", "📖 Storico Modifiche"])

    with tab1:
        show_file_comparison_tab()

    with tab2:
        show_audit_history_tab()

def show_file_comparison_tab():
    """
    Mostra interfaccia confronto file Excel.

    Workflow:
    1. Upload due file (Originale vs Modificato)
    2. Confronta Personale e Strutture
    3. Mostra statistiche differenze
    4. Visualizza dettagli: aggiunti, eliminati, modificati
    5. Export report differenze
    """
    # CSS personalizzato per evidenziare valori nuovi
    st.markdown("""
    <style>
    /* Evidenziazione valori nuovi */
    div[data-testid="stDataFrame"] td:nth-child(3) {
        background-color: #d4edda !important;
        font-weight: 600;
    }
    /* Stile per info box diff */
    .diff-highlight {
        background: linear-gradient(90deg, #fff3cd 0%, #d4edda 100%);
        padding: 8px 12px;
        border-radius: 4px;
        border-left: 4px solid #28a745;
        margin: 8px 0;
    }
    </style>
    """, unsafe_allow_html=True)

    # === UPLOAD FILE ===

    col1, col2 = st.columns(2)

    with col1:
        file_old = st.file_uploader(
            "Carica file Excel originale",
            type=['xls', 'xlsx'],
            key='file_old',
            help="File TNS versione precedente"
        )

    with col2:
        file_new = st.file_uploader(
            "Carica file Excel modificato",
            type=['xls', 'xlsx'],
            key='file_new',
            help="File TNS con modifiche da confrontare"
        )

    if not file_old or not file_new:
        st.info("📤 Carica entrambi i file per iniziare il confronto")

        with st.expander("ℹ️ Come Usare"):
            st.markdown("""
            **Casi d'Uso:**
            - ✅ Validare modifiche prima di applicarle
            - ✅ Audit trail: tracciare cambiamenti nel tempo
            - ✅ Verificare backup: confrontare file corrente con backup precedente
            - ✅ Merge review: controllare modifiche proposte da altri

            **Cosa Viene Confrontato:**
            - **TNS Personale**: Dipendenti (chiave: Codice Fiscale)
            - **TNS Strutture**: Organigramma (chiave: Codice)

            **Output:**
            - 🟢 Record aggiunti
            - 🔴 Record eliminati
            - 🟠 Record modificati (con dettaglio campi)
            - ⚪ Record invariati (solo conteggio)
            """)
        return

    # === CARICA E CONFRONTA ===

    if st.button("🔄 Esegui Confronto", type="primary", use_container_width=True):
        with st.spinner("📊 Analisi differenze in corso..."):
            try:
                # Salva file temporanei
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xls') as tmp_old:
                    tmp_old.write(file_old.getvalue())
                    tmp_old_path = Path(tmp_old.name)

                with tempfile.NamedTemporaryFile(delete=False, suffix='.xls') as tmp_new:
                    tmp_new.write(file_new.getvalue())
                    tmp_new_path = Path(tmp_new.name)

                # Carica dati
                handler_old = ExcelHandler(tmp_old_path)
                handler_new = ExcelHandler(tmp_new_path)

                personale_old, strutture_old, _ = handler_old.load_data()
                personale_new, strutture_new, _ = handler_new.load_data()

                # Confronta
                personale_diff, strutture_diff = FileDiffer.compare_full_files(
                    personale_old,
                    strutture_old,
                    personale_new,
                    strutture_new
                )

                # Salva in session state
                st.session_state.personale_diff = personale_diff
                st.session_state.strutture_diff = strutture_diff
                st.session_state.diff_completed = True

                st.success("✅ Confronto completato!")

            except Exception as e:
                st.error(f"❌ Errore durante confronto: {str(e)}")
                return

    # === MOSTRA RISULTATI ===
    if st.session_state.get('diff_completed', False):

        personale_diff = st.session_state.personale_diff
        strutture_diff = st.session_state.strutture_diff

        # Statistiche generali
        col1, col2, col3, col4 = st.columns(4)

        total_added = personale_diff.added_count + strutture_diff.added_count
        total_deleted = personale_diff.deleted_count + strutture_diff.deleted_count
        total_modified = personale_diff.modified_count + strutture_diff.modified_count
        total_unchanged = personale_diff.unchanged_count + strutture_diff.unchanged_count

        with col1:
            st.metric("🟢 Aggiunti", total_added)
        with col2:
            st.metric("🔴 Eliminati", total_deleted)
        with col3:
            st.metric("🟠 Modificati", total_modified)
        with col4:
            st.metric("⚪ Invariati", total_unchanged)

        # Dettagli per tipo
        tab1, tab2 = st.tabs(["👥 Personale", "🏗️ Strutture"])

        with tab1:
            show_diff_details(personale_diff, "Personale", "TxCodFiscale")

        with tab2:
            show_diff_details(strutture_diff, "Strutture", "Codice")

        # Export report

        if st.button("📄 Genera Report Excel", use_container_width=True):
            with st.spinner("Generazione report..."):
                try:
                    report_df = FileDiffer.export_diff_report(
                        personale_diff,
                        strutture_diff
                    )

                    # Converti in Excel per download
                    output = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
                    report_df.to_excel(output.name, index=False)

                    with open(output.name, 'rb') as f:
                        st.download_button(
                            label="⬇️ Scarica Report Differenze",
                            data=f,
                            file_name=f"diff_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )

                    st.success("✅ Report generato! Clicca per scaricare.")

                except Exception as e:
                    st.error(f"Errore generazione report: {str(e)}")

def show_diff_details(diff_result: DiffResult, record_type: str, key_field: str):
    """
    Mostra dettagli differenze per un tipo di record.

    Args:
        diff_result: DiffResult da visualizzare
        record_type: Tipo record (Personale/Strutture)
        key_field: Nome campo chiave
    """
    st.markdown(f"#### Riepilogo {record_type}")
    st.caption(diff_result.get_summary())

    if not diff_result.has_changes():
        st.success(f"✅ Nessuna differenza trovata in {record_type}")
        return

    # === RECORD AGGIUNTI ===
    if diff_result.added_count > 0:
        with st.expander(f"🟢 Record Aggiunti ({diff_result.added_count})", expanded=True):
            for item in diff_result.added_records:
                st.markdown(f"**Chiave:** `{item['key']}` 🆕")

                # Mostra SOLO campi con valore (non None/vuoti)
                data = item['data']
                filled_fields = {k: v for k, v in data.items() if v is not None and v != ''}

                # Conta campi compilati
                st.caption(f"✨ {len(filled_fields)} campi compilati su {len(data)} totali")

                # Mostra in formato tabellare compatto con evidenziazione
                if filled_fields:
                    field_data = [{'Campo': k, 'Valore': f"✨ {str(v)}"} for k, v in filled_fields.items()]
                    field_df = pd.DataFrame(field_data)
                    st.dataframe(
                        field_df,
                        use_container_width=True,
                        hide_index=True,
                        height=min(300, len(field_df) * 35 + 38),
                        column_config={
                            'Valore': st.column_config.TextColumn('🟢 Valore Nuovo', width='large')
                        }
                    )
                else:
                    st.info("Tutti i campi sono vuoti")

    # === RECORD ELIMINATI ===
    if diff_result.deleted_count > 0:
        with st.expander(f"🔴 Record Eliminati ({diff_result.deleted_count})", expanded=False):
            for item in diff_result.deleted_records:
                st.markdown(f"**Chiave:** `{item['key']}`")

                # Mostra SOLO campi con valore (non None/vuoti)
                data = item['data']
                filled_fields = {k: v for k, v in data.items() if v is not None and v != ''}

                # Conta campi compilati
                st.caption(f"{len(filled_fields)} campi compilati")

                # Mostra in formato tabellare compatto
                if filled_fields:
                    field_data = [{'Campo': k, 'Valore': str(v)} for k, v in filled_fields.items()]
                    field_df = pd.DataFrame(field_data)
                    st.dataframe(
                        field_df,
                        use_container_width=True,
                        hide_index=True,
                        height=min(300, len(field_df) * 35 + 38)
                    )
                else:
                    st.info("Record vuoto")

    # === RECORD MODIFICATI ===
    if diff_result.modified_count > 0:
        with st.expander(f"🟠 Record Modificati ({diff_result.modified_count})", expanded=True):
            for item in diff_result.modified_records:
                st.markdown(f"**Chiave:** `{item['key']}`")

                # Mostra solo i campi modificati
                if len(item['changes']) == 1:
                    st.caption(f"1 campo modificato")
                else:
                    st.caption(f"{len(item['changes'])} campi modificati")

                # Tabella compatta: solo campi che sono cambiati
                changes_data = []
                for change in item['changes']:
                    # Formatta valori per migliore leggibilità
                    old_val = change['old_value']
                    new_val = change['new_value']

                    # Gestione None/NULL
                    old_display = str(old_val) if old_val is not None else '(vuoto)'
                    new_display = str(new_val) if new_val is not None else '(vuoto)'

                    # Tronca valori molto lunghi
                    if len(old_display) > 50:
                        old_display = old_display[:47] + "..."
                    if len(new_display) > 50:
                        new_display = new_display[:47] + "..."

                    changes_data.append({
                        'Campo': change['field'],
                        'Prima': old_display,
                        'Dopo': f"✨ {new_display}"  # Evidenziazione valore nuovo con emoji
                    })

                changes_df = pd.DataFrame(changes_data)

                # Usa colori per evidenziare differenze
                st.dataframe(
                    changes_df,
                    use_container_width=True,
                    hide_index=True,
                    height=min(300, len(changes_df) * 35 + 38),
                    column_config={
                        'Campo': st.column_config.TextColumn('Campo Modificato', width='medium'),
                        'Prima': st.column_config.TextColumn('⚪ Precedente', width='large'),
                        'Dopo': st.column_config.TextColumn('🟢 Nuovo', width='large')
                    }
                )

                # Mostra diff visivo alternativo per singole modifiche
                if len(item['changes']) == 1:
                    change = item['changes'][0]
                    old_val = change['old_value'] if change['old_value'] is not None else '(vuoto)'
                    new_val = change['new_value'] if change['new_value'] is not None else '(vuoto)'
                    st.markdown(
                        f'<div class="diff-highlight">📝 <strong>{change["field"]}</strong>: '
                        f'<code>{old_val}</code> → <code style="background: #d4edda; padding: 2px 6px; border-radius: 3px; font-weight: 600;">{new_val}</code></div>',
                        unsafe_allow_html=True
                    )

def show_audit_history_tab():
    """
    Tab Storico Modifiche: visualizza audit log con filtri.

    Features:
    - Filtro per import version
    - Filtro per severity (CRITICAL/HIGH/MEDIUM/LOW)
    - Filtro per tabella (personale/strutture)
    - Metrics severity count
    - Tabella report con descrizioni italiane
    - Export Excel opzionale
    """
    db = st.session_state.database_handler

    # === FILTERS ===
    st.markdown("### 🔎 Filtri")

    col1, col2, col3 = st.columns(3)

    # Import Version selector
    with col1:
        try:
            versions = db.get_import_versions(limit=50)
            if versions:
                version_options = ["Tutte le versioni"] + [
                    f"#{v['id']}: {v['timestamp'][:16]} - {v['source_filename']}"
                    for v in versions
                ]
                selected_version_str = st.selectbox("📦 Versione Import", version_options)

                if selected_version_str == "Tutte le versioni":
                    selected_version = None
                else:
                    selected_version = int(selected_version_str.split(':')[0].replace('#', ''))
            else:
                st.info("Nessuna versione import trovata")
                selected_version = None
        except Exception as e:
            st.warning(f"Errore caricamento versioni: {str(e)}")
            selected_version = None

    # Severity filter
    with col2:
        severity_filter = st.multiselect(
            "⚠️ Gravità",
            ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'],
            default=['CRITICAL', 'HIGH']
        )

    # Table filter
    with col3:
        table_filter = st.multiselect(
            "📋 Tabella",
            ['personale', 'strutture'],
            default=['personale', 'strutture']
        )

    # === LOAD & GENERATE REPORT ===
    try:
        report_gen = ChangeReportGenerator(db)

        if selected_version:
            # Report per singolo import
            report_df = report_gen.generate_import_report(selected_version)
            st.caption(f"📊 Visualizzazione modifiche import version #{selected_version}")
        else:
            # Summary ultimi 90 giorni
            report_df = report_gen.generate_summary_report(days=90)
            st.caption("📊 Visualizzazione modifiche ultimi 90 giorni")

        # Apply filters
        if not report_df.empty and severity_filter:
            report_df = report_df[report_df['Gravità'].isin(severity_filter)]

        if not report_df.empty and table_filter:
            report_df = report_df[report_df['Tipo'].isin(table_filter)]

        # === METRICS ===
        st.markdown("### 📊 Riepilogo")

        if not report_df.empty:
            col1, col2, col3, col4 = st.columns(4)

            critical_count = len(report_df[report_df['Gravità'] == 'CRITICAL'])
            high_count = len(report_df[report_df['Gravità'] == 'HIGH'])
            medium_count = len(report_df[report_df['Gravità'] == 'MEDIUM'])
            low_count = len(report_df[report_df['Gravità'] == 'LOW'])

            with col1:
                st.metric("🔴 CRITICAL", critical_count)
            with col2:
                st.metric("🟠 HIGH", high_count)
            with col3:
                st.metric("🟡 MEDIUM", medium_count)
            with col4:
                st.metric("⚪ LOW", low_count)
        else:
            st.info("✅ Nessuna modifica trovata con i filtri selezionati")

        # === DATA TABLE ===
        if not report_df.empty:
            st.markdown("### 📋 Dettaglio Modifiche")

            # Sort by timestamp descending
            report_df = report_df.sort_values('Timestamp', ascending=False)

            st.dataframe(
                report_df,
                use_container_width=True,
                height=600,
                column_config={
                    'Timestamp': st.column_config.DatetimeColumn(
                        'Data/Ora',
                        format='DD/MM/YYYY HH:mm'
                    ),
                    'Gravità': st.column_config.TextColumn('Gravità', width='small'),
                    'Tipo': st.column_config.TextColumn('Tipo', width='small'),
                    'Operazione': st.column_config.TextColumn('Op.', width='small'),
                    'Chiave': st.column_config.TextColumn('Chiave', width='medium'),
                    'Campo': st.column_config.TextColumn('Campo', width='medium'),
                    'Descrizione': st.column_config.TextColumn('Descrizione', width='large')
                },
                hide_index=True
            )

            # === EXPORT (opzionale) ===
            if st.button("📄 Esporta Report Excel", use_container_width=True):
                try:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    output = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')

                    report_gen.export_to_excel(report_df, output.name)

                    with open(output.name, 'rb') as f:
                        st.download_button(
                            label="⬇️ Scarica Report",
                            data=f,
                            file_name=f"audit_report_{timestamp}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )

                    st.success("✅ Report generato! Clicca per scaricare.")

                except Exception as e:
                    st.error(f"Errore export: {str(e)}")

    except Exception as e:
        st.error(f"❌ Errore caricamento storico: {str(e)}")
