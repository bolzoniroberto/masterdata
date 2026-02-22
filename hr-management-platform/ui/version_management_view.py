"""
Vista Gestione Versioni - Visualizza e ripristina snapshot database
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
import config
from services.version_manager import VersionManager

def show_version_management_view():
    """
    Mostra interfaccia gestione versioni database.

    Features:
    - Lista tutti gli snapshot disponibili
    - Visualizza dettagli versione
    - Ripristina versione precedente (con conferma)
    - Elimina snapshot vecchi
    - Cleanup automatico
    """
    st.caption("Visualizza, ripristina ed elimina snapshot del database")

    # Inizializza version manager
    db = st.session_state.database_handler
    snapshots_dir = config.DATA_DIR / "snapshots"
    vm = VersionManager(db, snapshots_dir)

    # === INFO SISTEMA ===
    st.markdown("### ℹ️ Sistema Versioni")

    col1, col2, col3 = st.columns(3)

    with col1:
        snapshots = vm.list_snapshots()
        st.metric("📦 Snapshot Disponibili", len(snapshots))

    with col2:
        # Calcola spazio totale
        total_size = sum(vm.get_snapshot_size_mb(s['file_path']) for s in snapshots)
        st.metric("💾 Spazio Totale", f"{total_size:.1f} MB")

    with col3:
        # Versione corrente
        versions = db.get_import_versions(limit=1)
        current_version = versions[0]['id'] if versions else 0
        st.metric("🔢 Versione Corrente", f"#{current_version}")

    # === LISTA SNAPSHOT ===
    st.markdown("### 📋 Snapshot Disponibili")

    if not snapshots:
        st.info("📭 Nessuno snapshot disponibile.")
        st.markdown("""
        **Come creare snapshot:**

        **📦 Snapshot automatici (Import)**
        1. Vai alla sezione di upload file
        2. Carica un file Excel
        3. Conferma l'import
        4. Uno snapshot viene creato automaticamente

        **📸 Snapshot manuali**
        1. Clicca "📸 Crea Snapshot Manuale" nella sidebar
        2. Aggiungi una nota descrittiva
        3. Conferma per salvare lo stato attuale
        """)
        return

    # Prepara tabella snapshots
    snapshots_df = pd.DataFrame(snapshots)
    snapshots_df['timestamp_display'] = pd.to_datetime(snapshots_df['timestamp']).dt.strftime('%d/%m/%Y %H:%M')
    snapshots_df['size_mb'] = snapshots_df['file_path'].apply(lambda x: vm.get_snapshot_size_mb(x))

    # Aggiungi colonna "Tipo" per distinguere snapshot manuali da import
    snapshots_df['tipo'] = snapshots_df['source_filename'].apply(
        lambda x: "📸 Manuale" if x == "MANUAL_SNAPSHOT" else "📦 Import"
    )

    # Display table
    st.dataframe(
        snapshots_df[[
            'import_version_id', 'timestamp_display', 'tipo', 'source_filename',
            'user_note', 'personale_count', 'strutture_count', 'size_mb'
        ]].rename(columns={
            'import_version_id': 'ID Versione',
            'timestamp_display': 'Data/Ora',
            'tipo': 'Tipo',
            'source_filename': 'File Origine',
            'user_note': 'Nota',
            'personale_count': 'Personale',
            'strutture_count': 'Strutture',
            'size_mb': 'Dimensione (MB)'
        }),
        use_container_width=True,
        height=400,
        hide_index=True
    )

    # === AZIONI ===
    st.markdown("### 🔧 Azioni")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 🔄 Ripristina Versione")

        # Selettore versione - usa DataFrame che ha timestamp_display
        snapshot_options = [
            f"#{row['import_version_id']}: {row['timestamp_display']} - {row['source_filename']}"
            for _, row in snapshots_df.iterrows()
        ]

        if snapshot_options:
            selected_snapshot_str = st.selectbox(
                "Seleziona versione da ripristinare",
                snapshot_options,
                help="ATTENZIONE: Ripristinare una versione sovrascriverà i dati attuali!"
            )

            selected_idx = snapshot_options.index(selected_snapshot_str)
            selected_snapshot_row = snapshots_df.iloc[selected_idx]
            selected_snapshot = snapshots[selected_idx]  # Per file_path nel restore

            # Info snapshot selezionato
            with st.expander("ℹ️ Dettagli Snapshot", expanded=True):
                st.markdown(f"""
                **ID Versione:** #{selected_snapshot_row['import_version_id']}
                **Data/Ora:** {selected_snapshot_row['timestamp_display']}
                **Tipo:** {selected_snapshot_row['tipo']}
                **File Origine:** `{selected_snapshot_row['source_filename']}`
                **Nota:** {selected_snapshot_row['user_note'] or '(nessuna)'}
                **Record:** {selected_snapshot_row['personale_count']} personale, {selected_snapshot_row['strutture_count']} strutture
                **Dimensione:** {selected_snapshot_row['size_mb']:.2f} MB
                """)

            # Checkbox conferma
            create_backup = st.checkbox(
                "✅ Crea backup automatico prima del ripristino",
                value=True,
                help="Consigliato: salva lo stato attuale prima di ripristinare"
            )

            confirm = st.checkbox(
                "⚠️ Confermo di voler sovrascrivere i dati attuali",
                value=False,
                help="ATTENZIONE: Questa operazione sovrascriverà tutti i dati attuali nel database!"
            )

            if st.button("🔄 Ripristina Questa Versione", type="primary", disabled=not confirm, use_container_width=True):
                with st.spinner("Ripristino in corso..."):
                    success, message = vm.restore_snapshot(
                        selected_snapshot['file_path'],
                        create_backup=create_backup
                    )

                    if success:
                        st.success(message)
                        st.balloons()

                        # Ricarica dati in session state
                        from app import load_data_from_db
                        load_data_from_db()

                        st.info("🔄 Aggiorna la pagina per vedere i dati ripristinati")
                        st.rerun()
                    else:
                        st.error(message)

    with col2:
        st.markdown("#### 🗑️ Gestione Spazio")

        st.metric("Snapshot Totali", len(snapshots))
        st.metric("Spazio Utilizzato", f"{total_size:.1f} MB")

        # Cleanup old snapshots
        keep_last = st.number_input(
            "Mantieni ultimi N snapshot",
            min_value=5,
            max_value=200,
            value=50,
            step=5,
            help="Elimina gli snapshot più vecchi oltre questo numero"
        )

        if len(snapshots) > keep_last:
            st.warning(f"⚠️ Hai {len(snapshots) - keep_last} snapshot che verranno eliminati")

        if st.button("🗑️ Pulisci Snapshot Vecchi", use_container_width=True):
            with st.spinner("Pulizia in corso..."):
                deleted = vm.cleanup_old_snapshots(keep_last_n=keep_last)
                if deleted > 0:
                    st.success(f"✅ Eliminati {deleted} snapshot vecchi")
                    st.rerun()
                else:
                    st.info("ℹ️ Nessun snapshot da eliminare")

        # Elimina snapshot specifico
        st.markdown("##### 🗑️ Elimina Snapshot Specifico")

        snapshot_to_delete = st.selectbox(
            "Seleziona snapshot da eliminare",
            snapshot_options,
            key="delete_selector"
        )

        delete_idx = snapshot_options.index(snapshot_to_delete)
        delete_snapshot = snapshots[delete_idx]

        if st.button("🗑️ Elimina Snapshot", use_container_width=True, type="secondary"):
            confirm_delete = st.checkbox(
                f"Conferma eliminazione snapshot #{delete_snapshot['import_version_id']}",
                key="confirm_delete"
            )

            if confirm_delete:
                success, message = vm.delete_snapshot(delete_snapshot['file_path'])
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

    # === INFORMAZIONI ===
    with st.expander("ℹ️ Come Funziona il Sistema Versioni"):
        st.markdown("""
        ### 📦 Sistema di Versioning

        **Creazione Automatica Snapshot:**
        - Ogni volta che importi un file Excel, viene creato uno snapshot automatico
        - Lo snapshot contiene tutti i dati (personale + strutture) in quel momento
        - Ogni snapshot ha un ID univoco collegato all'import version

        **Ripristino Versione:**
        - Puoi ripristinare qualsiasi versione precedente
        - Il ripristino sovrascrive i dati attuali nel database
        - **Consigliato:** Crea sempre un backup automatico prima del ripristino

        **Gestione Spazio:**
        - Gli snapshot sono salvati come file JSON in `data/snapshots/`
        - Puoi eliminare snapshot vecchi per liberare spazio
        - Mantieni almeno 10-20 snapshot per avere uno storico utile

        **Sicurezza:**
        - Prima di ogni ripristino, viene creato un backup automatico
        - I backup hanno ID versione -1 e filename "AUTO_BACKUP"
        - Tutti i restore sono tracciati nell'audit log

        **Best Practices:**
        - Aggiungi note descrittive quando importi file Excel
        - Mantieni almeno 30-50 snapshot per uno storico di 1-2 mesi
        - Fai backup manuali prima di operazioni critiche
        """)
