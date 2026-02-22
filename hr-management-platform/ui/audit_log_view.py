"""
Vista Log Modifiche - Mostra audit log con filtri
Traccia tutte le operazioni INSERT/UPDATE/DELETE con before/after values
"""
import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta

def show_audit_log_view():
    """Mostra vista log modifiche"""
    st.caption("Traccia completa di tutte le modifiche al database con before/after values")

    db = st.session_state.database_handler

    # === FILTRI ===
    st.markdown("### 🎯 Filtri")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Data range
        default_from = datetime.now() - timedelta(days=30)
        date_from = st.date_input(
            "Da",
            value=default_from,
            help="Data inizio ricerca"
        )

    with col2:
        date_to = st.date_input(
            "A",
            value=datetime.now(),
            help="Data fine ricerca"
        )

    with col3:
        # Tabella filter
        table_filter = st.selectbox(
            "Tabella",
            options=["Tutte", "personale", "strutture"],
            help="Filtra per tabella specifica"
        )

    with col4:
        # Operation filter
        operation_filter = st.multiselect(
            "Operazione",
            options=["INSERT", "UPDATE", "DELETE"],
            default=["INSERT", "UPDATE", "DELETE"],
            help="Tipo di operazione"
        )

    # Bottone carica
    col1, col2 = st.columns([1, 3])
    with col1:
        load_button = st.button("🔍 Carica Log", type="primary", use_container_width=True)

    with col2:
        limit = st.slider("Max record", min_value=10, max_value=1000, value=100, step=10)

    # === CARICA AUDIT LOG ===
    if load_button or st.session_state.get('audit_log_loaded'):
        st.session_state.audit_log_loaded = True

        with st.spinner("Caricamento log in corso..."):
            try:
                # Carica audit log da database
                cursor = db.conn.cursor()

                # Build query
                query = """
                    SELECT id, timestamp, table_name, operation, record_key,
                           before_values, after_values, user_action
                    FROM audit_log
                    WHERE 1=1
                """
                params = []

                # Filtro data
                if date_from:
                    query += " AND DATE(timestamp) >= ?"
                    params.append(date_from.strftime('%Y-%m-%d'))

                if date_to:
                    query += " AND DATE(timestamp) <= ?"
                    params.append(date_to.strftime('%Y-%m-%d'))

                # Filtro tabella
                if table_filter != "Tutte":
                    query += " AND table_name = ?"
                    params.append(table_filter)

                # Filtro operation
                if operation_filter:
                    placeholders = ','.join(['?'] * len(operation_filter))
                    query += f" AND operation IN ({placeholders})"
                    params.extend(operation_filter)

                # Order e limit
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)

                cursor.execute(query, params)
                rows = cursor.fetchall()
                cursor.close()

                if len(rows) == 0:
                    st.info("📭 Nessun log trovato con questi filtri")
                    return

                # Converti in DataFrame
                logs = []
                for row in rows:
                    log_entry = {
                        'id': row[0],
                        'timestamp': row[1],
                        'table_name': row[2],
                        'operation': row[3],
                        'record_key': row[4],
                        'before_values': row[5],
                        'after_values': row[6],
                        'user_action': row[7] or 'system'
                    }
                    logs.append(log_entry)

                logs_df = pd.DataFrame(logs)

                # === STATISTICHE LOG ===
                st.markdown("### 📊 Statistiche")

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    inserts = len(logs_df[logs_df['operation'] == 'INSERT'])
                    st.metric("➕ INSERT", inserts)

                with col2:
                    updates = len(logs_df[logs_df['operation'] == 'UPDATE'])
                    st.metric("✏️ UPDATE", updates)

                with col3:
                    deletes = len(logs_df[logs_df['operation'] == 'DELETE'])
                    st.metric("🗑️ DELETE", deletes)

                with col4:
                    st.metric("📊 Totale", len(logs_df))

                # === TABELLA LOG ===
                st.markdown("### 📋 Log Dettagliato")

                # Formatta timestamp
                logs_df['timestamp_fmt'] = pd.to_datetime(logs_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')

                # Mostra tabella principale
                display_df = logs_df[[
                    'id', 'timestamp_fmt', 'operation', 'table_name',
                    'record_key', 'user_action'
                ]].rename(columns={
                    'timestamp_fmt': 'Data/Ora',
                    'operation': 'Operazione',
                    'table_name': 'Tabella',
                    'record_key': 'Record',
                    'user_action': 'Utente'
                })

                # Color code operations
                def highlight_operation(row):
                    if row['Operazione'] == 'INSERT':
                        return ['background-color: #d4edda'] * len(row)
                    elif row['Operazione'] == 'DELETE':
                        return ['background-color: #f8d7da'] * len(row)
                    elif row['Operazione'] == 'UPDATE':
                        return ['background-color: #fff3cd'] * len(row)
                    return [''] * len(row)

                styled_logs = display_df.style.apply(highlight_operation, axis=1)

                st.dataframe(
                    styled_logs,
                    use_container_width=True,
                    height=400,
                    hide_index=True,
                    column_config={
                        'id': st.column_config.NumberColumn("ID", width="small"),
                        'Data/Ora': st.column_config.TextColumn("Data/Ora", width="medium"),
                        'Operazione': st.column_config.TextColumn("Op", width="small"),
                        'Tabella': st.column_config.TextColumn("Tabella", width="small"),
                        'Record': st.column_config.TextColumn("Record", width="medium"),
                        'Utente': st.column_config.TextColumn("Utente", width="small")
                    }
                )

                # === DETTAGLIO LOG (Expander per before/after) ===
                st.markdown("### 🔍 Dettaglio Modifiche")
                st.caption("Espandi un log per vedere before/after values")

                # Select log per dettaglio
                selected_log_id = st.selectbox(
                    "Seleziona Log ID",
                    options=logs_df['id'].tolist(),
                    format_func=lambda x: f"#{x} - {logs_df[logs_df['id']==x].iloc[0]['operation']} - {logs_df[logs_df['id']==x].iloc[0]['record_key']}"
                )

                if selected_log_id:
                    selected_log = logs_df[logs_df['id'] == selected_log_id].iloc[0]

                    col1, col2 = st.columns(2)

                    with col1:
                        if selected_log['before_values']:
                            try:
                                before_json = json.loads(selected_log['before_values'])
                                st.json(before_json)
                            except:
                                st.text(selected_log['before_values'])
                        else:
                            st.caption("(vuoto - nuovo record)")

                    with col2:
                        if selected_log['after_values']:
                            try:
                                after_json = json.loads(selected_log['after_values'])
                                st.json(after_json)
                            except:
                                st.text(selected_log['after_values'])
                        else:
                            st.caption("(vuoto - record eliminato)")

                # === EXPORT LOG ===
                st.markdown("### 📥 Esporta Log")

                if st.button("📥 Esporta Log Excel", type="primary"):
                    try:
                        import config
                        output_path = config.OUTPUT_DIR / f"audit_log_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                        config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

                        # Prepara export con before/after parsed
                        export_df = logs_df.copy()

                        # Parse JSON per export leggibile
                        def parse_json_field(val):
                            if val:
                                try:
                                    parsed = json.loads(val)
                                    return json.dumps(parsed, indent=2, ensure_ascii=False)
                                except:
                                    return val
                            return ""

                        export_df['before_values'] = export_df['before_values'].apply(parse_json_field)
                        export_df['after_values'] = export_df['after_values'].apply(parse_json_field)

                        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                            export_df.to_excel(writer, sheet_name='Audit Log', index=False)

                            # Metadata
                            metadata_df = pd.DataFrame([{
                                'Data Export': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'Filtro Da': str(date_from),
                                'Filtro A': str(date_to),
                                'Filtro Tabella': table_filter,
                                'Totale Record': len(logs_df)
                            }])
                            metadata_df.to_excel(writer, sheet_name='Info', index=False)

                        st.success(f"✅ Log esportato: `{output_path.name}`")

                        # Download
                        with open(output_path, 'rb') as f:
                            st.download_button(
                                label="⬇️ Scarica File",
                                data=f.read(),
                                file_name=output_path.name,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )

                    except Exception as e:
                        st.error(f"❌ Errore export: {str(e)}")

            except Exception as e:
                st.error(f"❌ Errore caricamento log: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
