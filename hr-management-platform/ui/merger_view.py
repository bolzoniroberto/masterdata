"""
UI per generazione DB_TNS (merge Personale + Strutture)
"""
import streamlit as st
from services.merger import DBTNSMerger

def show_merger_view():
    """UI per generare DB_TNS"""
    
    st.markdown("""
    Questa sezione genera automaticamente il foglio **DB_TNS** 
    effettuando il merge di:
    - **TNS Strutture** (organigramma)
    - **TNS Personale** (dipendenti)
    
    Il risultato è un unico foglio con tutti i record, pronto per l'import IT.
    """)

    # Get dataframes with safety check
    personale_df = st.session_state.get('personale_df')
    strutture_df = st.session_state.get('strutture_df')

    if personale_df is None or strutture_df is None:
        st.warning("⚠️ Nessun dato disponibile. Importa un file Excel per iniziare.")
        return

    # Info pre-merge
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Strutture", len(strutture_df))
    with col2:
        st.metric("Personale", len(personale_df))
    with col3:
        expected = len(strutture_df) + len(personale_df)
        st.metric("Totale atteso", expected)
    
    # Pulsante genera
    if st.button("🚀 Genera DB_TNS", type="primary", use_container_width=True):
        with st.spinner("Generazione DB_TNS in corso..."):
            
            # Merge
            db_tns, warnings = DBTNSMerger.merge_data(personale_df, strutture_df)
            
            # Valida
            is_valid, errors = DBTNSMerger.validate_db_tns(db_tns)
            
            # Salva in session state
            st.session_state.db_tns_df = db_tns
            
            # Mostra risultati
            if is_valid:
                st.success(f"✅ DB_TNS generato con successo! {len(db_tns)} record totali")
            else:
                st.error("❌ DB_TNS generato ma con errori di validazione")
                for err in errors:
                    st.error(f"- {err}")
            
            # Mostra warnings
            if warnings:
                with st.expander("⚠️ Warning generazione", expanded=False):
                    for warn in warnings:
                        st.warning(warn)
            
            # Statistiche
            stats = DBTNSMerger.get_statistics(db_tns)
            
            st.markdown("### 📊 Statistiche DB_TNS generato")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Record totali", stats['total_records'])
            with col2:
                st.metric("Strutture", stats['strutture_count'])
            with col3:
                st.metric("Personale", stats['personale_count'])
            with col4:
                st.metric("Codici duplicati", stats['duplicate_codes'])
            
            # Anteprima
            st.markdown("### 👀 Anteprima DB_TNS (prime 20 righe)")
            st.dataframe(db_tns.head(20), use_container_width=True, height=400)
    
    # Se già generato, mostra info
    if st.session_state.db_tns_df is not None:
        st.info("ℹ️ DB_TNS già presente in memoria. Rigenera per aggiornare.")
        
        db_tns = st.session_state.db_tns_df
        
        # Stats correnti
        stats = DBTNSMerger.get_statistics(db_tns)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Record in DB_TNS", len(db_tns))
        with col2:
            st.metric("Strutture", stats['strutture_count'])
        with col3:
            st.metric("Personale", stats['personale_count'])
        
        # Anteprima
        if st.checkbox("Mostra anteprima DB_TNS corrente"):
            st.dataframe(db_tns, use_container_width=True, height=400)
