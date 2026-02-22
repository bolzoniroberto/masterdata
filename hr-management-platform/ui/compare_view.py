"""
Vista Confronta Versioni - Confronto side-by-side di 2 snapshot
Mostra diff dettagliato con highlight colori e export report
"""
import streamlit as st
import pandas as pd
import config
from services.version_manager import VersionManager

def show_compare_view():
    """Mostra vista confronta versioni"""
    st.caption("Confronta 2 snapshot side-by-side per vedere differenze")

    # Inizializza VersionManager
    vm = VersionManager(st.session_state.database_handler, config.SNAPSHOTS_DIR)

    # Carica lista snapshot
    snapshots = vm.list_snapshots()

    if len(snapshots) < 2:
        st.warning("⚠️ Servono almeno 2 snapshot per confrontare versioni.")
        st.info("💡 Crea snapshot usando il bottone '💾 Checkpoint' o '🏁 Milestone' in alto")
        return

    # === SELETTORI VERSIONI ===
    st.markdown("### 📂 Seleziona Versioni da Confrontare")

    # Prepara opzioni dropdown
    snapshot_options = {}
    for s in snapshots:
        version_id = s['import_version_id']
        timestamp = pd.to_datetime(s['timestamp']).strftime('%Y-%m-%d %H:%M')
        note = s['user_note'] or s['source_filename']

        # Aggiungi badge certified se milestone
        try:
            with open(s['file_path'], 'r', encoding='utf-8') as f:
                import json
                data = json.load(f)
                is_certified = data['metadata'].get('certified', False)
                badge = " 🏁" if is_certified else ""
        except:
            badge = ""

        label = f"#{version_id}{badge} - {timestamp} - {note}"
        snapshot_options[label] = version_id

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Versione A** (base)")
        version_a_label = st.selectbox(
            "Versione A",
            options=list(snapshot_options.keys()),
            index=0,
            label_visibility="collapsed"
        )
        version_a_id = snapshot_options[version_a_label]

    with col2:
        st.markdown("**Versione B** (confronto)")
        version_b_label = st.selectbox(
            "Versione B",
            options=list(snapshot_options.keys()),
            index=min(1, len(snapshot_options) - 1),
            label_visibility="collapsed"
        )
        version_b_id = snapshot_options[version_b_label]

    # Bottone confronta
    if st.button("⚖️ Confronta Versioni", type="primary", use_container_width=False):
        st.session_state.compare_versions = True
        st.session_state.compare_a = version_a_id
        st.session_state.compare_b = version_b_id
        st.rerun()

    # === MOSTRA DIFF (se confronto attivo) ===
    if st.session_state.get('compare_versions'):
        version_a_id = st.session_state.compare_a
        version_b_id = st.session_state.compare_b

        st.markdown("### 🔍 Risultati Confronto")

        with st.spinner("Generazione diff in corso..."):
            try:
                # Genera diff
                diff_df = vm.compare_versions(version_a_id, version_b_id)

                if len(diff_df) == 0:
                    st.success("✅ Le due versioni sono identiche! Nessuna differenza trovata.")
                    return

                # === FILTRI DIFF ===
                st.markdown("#### 🎯 Filtra Differenze")
                col1, col2, col3 = st.columns(3)

                with col1:
                    tipo_record_filter = st.radio(
                        "Tipo Record",
                        options=["Entrambi", "Personale", "Struttura"],
                        horizontal=True
                    )

                with col2:
                    tipo_cambio_filter = st.multiselect(
                        "Tipo Cambio",
                        options=["Aggiunto", "Modificato", "Eliminato"],
                        default=["Aggiunto", "Modificato", "Eliminato"]
                    )

                with col3:
                    # Campo filter (opzionale)
                    all_campi = sorted(diff_df['campo'].unique().tolist())
                    campo_filter = st.multiselect(
                        "Campo",
                        options=all_campi,
                        help="Filtra per campo specifico (opzionale)"
                    )

                # Applica filtri
                filtered_diff = diff_df.copy()

                if tipo_record_filter != "Entrambi":
                    filtered_diff = filtered_diff[filtered_diff['tipo'] == tipo_record_filter]

                if tipo_cambio_filter:
                    filtered_diff = filtered_diff[filtered_diff['tipo_cambio'].isin(tipo_cambio_filter)]

                if campo_filter:
                    filtered_diff = filtered_diff[filtered_diff['campo'].isin(campo_filter)]

                # === STATISTICHE DIFF ===
                st.markdown("#### 📊 Statistiche Differenze")
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    aggiunti = len(filtered_diff[filtered_diff['tipo_cambio'] == 'Aggiunto'])
                    st.metric("➕ Aggiunti", aggiunti)

                with col2:
                    modificati = len(filtered_diff[filtered_diff['tipo_cambio'] == 'Modificato'])
                    st.metric("✏️ Modificati", modificati)

                with col3:
                    eliminati = len(filtered_diff[filtered_diff['tipo_cambio'] == 'Eliminato'])
                    st.metric("🗑️ Eliminati", eliminati)

                with col4:
                    st.metric("📊 Totale", len(filtered_diff))

                # === TABELLA DIFF ===
                st.markdown("#### 🔍 Dettaglio Differenze")

                if len(filtered_diff) == 0:
                    st.info("Nessuna differenza con i filtri selezionati")
                else:
                    # Colora righe in base a tipo_cambio
                    def highlight_diff(row):
                        if row['tipo_cambio'] == 'Aggiunto':
                            return ['background-color: #d4edda'] * len(row)
                        elif row['tipo_cambio'] == 'Eliminato':
                            return ['background-color: #f8d7da'] * len(row)
                        elif row['tipo_cambio'] == 'Modificato':
                            return ['background-color: #fff3cd'] * len(row)
                        return [''] * len(row)

                    styled_diff = filtered_diff.style.apply(highlight_diff, axis=1)

                    st.dataframe(
                        styled_diff,
                        use_container_width=True,
                        height=400,
                        hide_index=True,
                        column_config={
                            'tipo': st.column_config.TextColumn("Tipo", width="small"),
                            'tipo_cambio': st.column_config.TextColumn(
                                "Cambio",
                                width="small",
                                help="➕ Aggiunto | ✏️ Modificato | 🗑️ Eliminato"
                            ),
                            'record': st.column_config.TextColumn("Record", width="medium"),
                            'campo': st.column_config.TextColumn("Campo", width="medium"),
                            'valore_a': st.column_config.TextColumn(
                                f"Valore A (#{version_a_id})",
                                width="large"
                            ),
                            'valore_b': st.column_config.TextColumn(
                                f"Valore B (#{version_b_id})",
                                width="large"
                            )
                        }
                    )

                # === EXPORT DIFF ===
                st.markdown("#### 📥 Esporta Report Diff")

                col1, col2 = st.columns([3, 1])

                with col1:
                    st.caption(f"Esporta {len(filtered_diff)} differenze in Excel")

                with col2:
                    if st.button("📥 Scarica Report", type="primary", use_container_width=True):
                        try:
                            # Crea Excel
                            output_path = config.OUTPUT_DIR / f"diff_v{version_a_id}_v{version_b_id}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                            config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

                            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                                # Sheet diff
                                filtered_diff.to_excel(writer, sheet_name='Differenze', index=False)

                                # Metadata sheet
                                metadata_df = pd.DataFrame([{
                                    'Versione A': f"#{version_a_id}",
                                    'Versione B': f"#{version_b_id}",
                                    'Data Export': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    'Totale Diff': len(filtered_diff),
                                    'Aggiunti': aggiunti,
                                    'Modificati': modificati,
                                    'Eliminati': eliminati
                                }])
                                metadata_df.to_excel(writer, sheet_name='Info', index=False)

                            st.success(f"✅ Report esportato: `{output_path.name}`")

                            # Download button
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
                st.error(f"❌ Errore confronto versioni: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
