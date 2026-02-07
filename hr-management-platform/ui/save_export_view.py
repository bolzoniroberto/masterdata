"""
UI per salvataggio ed export dei dati
"""
import streamlit as st
from pathlib import Path
import config


def show_save_export_view():
    """UI per salvare ed esportare dati"""

    st.header("💾 Salvataggio & Export")

    personale_df = st.session_state.personale_df
    strutture_df = st.session_state.strutture_df
    db_tns_df = st.session_state.db_tns_df
    excel_handler = st.session_state.get('excel_handler', None)

    # Messaggio se excel_handler non disponibile
    if not excel_handler:
        st.warning("""
        ⚠️ **Funzionalità di salvataggio Excel non disponibile**

        Con il nuovo flusso basato su database, usa invece:
        - **📦 Gestione Versioni** → Crea snapshot per salvare versioni
        - **📸 Crea Snapshot Manuale** (sidebar) → Salva stato corrente

        Per esportare dati in Excel, contattare l'amministratore.
        """)
        return

    # Tab per diverse opzioni
    tab1, tab2, tab3 = st.tabs(["💾 Salva modifiche", "📤 Esporta", "🕐 Backup"])

    with tab1:
        st.markdown("""
        ### Salva modifiche sul file originale
        
        Questa operazione:
        - Sovrascrive il file originale con i dati modificati
        - Crea automaticamente un backup con timestamp
        - Include i tre fogli: TNS Personale, TNS Strutture, DB_TNS
        """)
        
        if st.button("💾 Salva modifiche", type="primary", use_container_width=True):
            with st.spinner("Salvataggio in corso..."):
                try:
                    # Salva con backup automatico
                    saved_path = excel_handler.save_data(
                        personale_df,
                        strutture_df,
                        db_tns_df,
                        create_backup=True
                    )
                    
                    st.success(f"✅ File salvato con successo!")
                    st.info(f"📁 Path: {saved_path}")
                    
                    # Mostra info backup
                    backups = excel_handler.get_backup_list()
                    if backups:
                        st.success(f"🔒 Backup creato: {backups[0]['name']}")
                
                except Exception as e:
                    st.error(f"❌ Errore durante salvataggio: {str(e)}")
    
    with tab2:
        st.markdown("""
        ### Esporta in nuovo file
        
        Crea un nuovo file Excel con timestamp, senza modificare l'originale.
        """)
        
        export_prefix = st.text_input(
            "Prefisso nome file",
            value="TNS_HR_Export",
            help="Verrà aggiunto timestamp automaticamente"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            include_db_tns = st.checkbox(
                "Includi DB_TNS",
                value=True if db_tns_df is not None else False,
                disabled=db_tns_df is None
            )
        
        with col2:
            if db_tns_df is None:
                st.warning("⚠️ DB_TNS non ancora generato")
        
        if st.button("📤 Esporta", type="primary", use_container_width=True):
            with st.spinner("Export in corso..."):
                try:
                    db_to_export = db_tns_df if include_db_tns else None
                    
                    export_path = excel_handler.export_to_output(
                        personale_df,
                        strutture_df,
                        db_to_export,
                        prefix=export_prefix
                    )
                    
                    st.success(f"✅ File esportato con successo!")
                    st.info(f"📁 Path: {export_path}")
                    
                    # Offri download
                    with open(export_path, 'rb') as f:
                        st.download_button(
                            label="⬇️ Scarica file esportato",
                            data=f,
                            file_name=export_path.name,
                            mime="application/vnd.ms-excel"
                        )
                
                except Exception as e:
                    st.error(f"❌ Errore durante export: {str(e)}")
    
    with tab3:
        st.markdown("""
        ### Gestione Backup
        
        Visualizza e ripristina backup precedenti.
        """)

        # Lista backup
        backups = excel_handler.get_backup_list()

        if not backups:
            st.info("Nessun backup disponibile")
        else:
            st.markdown(f"**{len(backups)} backup disponibili** (max {config.MAX_BACKUPS})")
            
            # Tabella backup
            import pandas as pd
            backup_table = pd.DataFrame([
                {
                    'Nome': b['name'],
                    'Data': b['date'].strftime('%Y-%m-%d %H:%M:%S'),
                    'Dimensione (MB)': f"{b['size_mb']:.2f}"
                }
                for b in backups
            ])
            
            st.dataframe(backup_table, use_container_width=True, height=300)
            
            # Selezione backup da ripristinare
            st.markdown("---")
            st.markdown("#### Ripristina backup")
            
            selected_backup = st.selectbox(
                "Seleziona backup",
                options=[b['name'] for b in backups],
                help="Attenzione: ripristinare sovrascriverà i dati correnti"
            )
            
            col1, col2 = st.columns([3, 1])
            
            with col2:
                if st.button("🔄 Ripristina", type="secondary"):
                    if st.checkbox("⚠️ Conferma ripristino (operazione irreversibile)"):
                        backup_path = next(b['path'] for b in backups if b['name'] == selected_backup)
                        
                        with st.spinner("Ripristino in corso..."):
                            try:
                                # Carica da backup
                                personale, strutture, db_tns = excel_handler.restore_backup(backup_path)
                                
                                # Aggiorna session state
                                st.session_state.personale_df = personale
                                st.session_state.strutture_df = strutture
                                st.session_state.db_tns_df = db_tns
                                
                                st.success(f"✅ Backup ripristinato: {selected_backup}")
                                st.info("♻️ Ricarica la pagina per vedere i dati ripristinati")
                            
                            except Exception as e:
                                st.error(f"❌ Errore ripristino: {str(e)}")
