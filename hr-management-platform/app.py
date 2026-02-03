"""
HR Management Platform - Applicazione Streamlit principale
Gruppo Il Sole 24 ORE
"""
import streamlit as st
from pathlib import Path
import sys

# Setup path per import moduli
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

import config
from services.excel_handler import ExcelHandler
from services.validator import DataValidator
from services.merger import DBTNSMerger
from services.database import DatabaseHandler

# Configurazione pagina
st.set_page_config(
    page_title=config.PAGE_TITLE,
    page_icon=config.PAGE_ICON,
    layout=config.LAYOUT,
    initial_sidebar_state="expanded"
)

# Inizializzazione session state
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'personale_df' not in st.session_state:
    st.session_state.personale_df = None
if 'strutture_df' not in st.session_state:
    st.session_state.strutture_df = None
if 'db_tns_df' not in st.session_state:
    st.session_state.db_tns_df = None
if 'excel_handler' not in st.session_state:
    st.session_state.excel_handler = None
if 'database_handler' not in st.session_state:
    st.session_state.database_handler = DatabaseHandler()

# Inizializza database se non esiste
if st.session_state.database_handler:
    st.session_state.database_handler.init_db()


def load_data_from_upload(uploaded_file):
    """
    Carica dati da file uploadato e persisti nel database.

    Flow:
    1. Load Excel file
    2. Validate data
    3. Import into SQLite database
    4. Load from database to session state
    """
    try:
        # Salva file temporaneo
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xls') as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = Path(tmp.name)

        # Carica dati da Excel
        handler = ExcelHandler(tmp_path)
        personale, strutture, db_tns = handler.load_data()

        # Valida dati
        validator = DataValidator()
        errors = validator.validate_all(personale, strutture)
        if errors:
            error_list = "\n".join(errors[:5])  # Primi 5 errori
            return False, f"Errori validazione dati:\n{error_list}"

        # Importa nel database
        db_handler = st.session_state.database_handler
        p_count, s_count = db_handler.import_from_dataframe(personale, strutture)

        # Ricarica da database a session state
        return load_data_from_db()

    except Exception as e:
        return False, f"Errore caricamento: {str(e)}"


def load_data_from_db():
    """
    Carica dati dal database SQLite in session state.

    Viene usato:
    - Dopo upload Excel (che importa nel DB)
    - Quando app si riavvia (carica da DB persistente)
    """
    try:
        db_handler = st.session_state.database_handler
        personale, strutture = db_handler.export_to_dataframe()

        # Salva in session state (cache per UI performance)
        st.session_state.personale_df = personale
        st.session_state.strutture_df = strutture
        st.session_state.db_tns_df = None  # Rigenerato al bisogno da merger_view
        st.session_state.data_loaded = True

        return True, f"Dati caricati da database: {len(personale)} personale, {len(strutture)} strutture"

    except Exception as e:
        return False, f"Errore caricamento database: {str(e)}"


def main():
    """Funzione principale applicazione"""

    # === AUTO-LOAD DA DATABASE ===
    # Se database ha dati e session state è vuoto, carica automaticamente
    if not st.session_state.data_loaded and config.DB_PATH.exists():
        try:
            success, msg = load_data_from_db()
            if success:
                st.session_state.data_loaded = True
        except:
            pass  # Database vuoto, continua a chiedere upload

    # Header
    st.title("✈️ Travel & Expense Approval Management")
    st.subheader("Gruppo Il Sole 24 ORE - Gestione Ruoli Approvazione")
    
    # Sidebar per navigazione
    with st.sidebar:
        st.header("📋 Menu")
        
        # Upload file
        st.markdown("### 📁 Carica File Excel")
        uploaded_file = st.file_uploader(
            "Carica file TNS (.xls/.xlsx)",
            type=['xls', 'xlsx'],
            help="File Excel con fogli 'TNS Personale' e 'TNS Strutture'"
        )
        
        if uploaded_file is not None and not st.session_state.data_loaded:
            with st.spinner("Caricamento dati..."):
                success, message = load_data_from_upload(uploaded_file)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

        st.markdown("---")

        # === PULSANTE RESET DATABASE ===
        if st.session_state.data_loaded:
            st.markdown("### 🔄 Database Manager")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📤 Re-import Excel", use_container_width=True):
                    st.session_state.data_loaded = False
                    st.info("Carica di nuovo il file Excel per reimportare i dati nel database")
                    st.rerun()

            with col2:
                if st.button("🗑️ Clear Database", use_container_width=True):
                    try:
                        cursor = st.session_state.database_handler.conn.cursor()
                        cursor.execute("DELETE FROM personale")
                        cursor.execute("DELETE FROM strutture")
                        cursor.execute("DELETE FROM db_tns")
                        st.session_state.database_handler.conn.commit()
                        st.session_state.data_loaded = False
                        st.success("Database azzerato")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore: {str(e)}")

            st.markdown("---")
        
        # Navigazione
        if st.session_state.data_loaded:
            page = st.radio(
                "Sezione",
                [
                    "📊 Dashboard",
                    "🏗️ Gestione Strutture",
                    "👥 Gestione Personale",
                    "🎭 Gestione Ruoli",
                    "🤖 Assistente Bot",
                    "🔄 Genera DB_TNS",
                    "💾 Salvataggio & Export",
                    "🔍 Confronto File"
                ],
                label_visibility="collapsed"
            )
        else:
            # Vista confronto disponibile anche senza file caricato
            page = st.radio(
                "Sezione",
                [
                    "🔍 Confronto File"
                ],
                label_visibility="collapsed"
            )
            st.info("📤 Carica un file Excel per accedere a tutte le funzionalità")
        
        st.markdown("---")
        st.caption(f"v1.0 | {config.PAGE_TITLE}")
    
    # Contenuto principale
    if not st.session_state.data_loaded:
        # Schermata benvenuto
        st.markdown("""
        ## Benvenuto nel Sistema di Gestione Approvazioni

        **Gestisci i ruoli di approvazione per trasferte e note spese**

        Questa applicazione ti permette di:

        - 📊 **Visualizzare** statistiche e anomalie sui ruoli di approvazione
        - ✏️ **Modificare** ruoli dipendenti (Approvatori, Controllori, Cassieri, etc.)
        - 🏗️ **Gestire** struttura organizzativa e gerarchie
        - ✅ **Validare** dati con controlli automatici (CF, riferimenti, cicli)
        - 🔄 **Generare** il foglio DB_TNS per export al sistema trasferte
        - 💾 **Salvare** ed esportare i dati aggiornati con backup automatico

        ### 🚀 Per iniziare:

        1. Carica il file Excel TNS dalla sidebar
        2. Naviga tra le sezioni usando il menu
        3. Modifica ruoli e strutture direttamente nelle tabelle
        4. Genera il DB_TNS aggiornato
        5. Salva o esporta il risultato per l'import

        ### 📋 Struttura file Excel:

        - **TNS Personale**: dipendenti con ruoli approvazione (Viaggiatore, Approvatore, Controllore, Cassiere, etc.)
        - **TNS Strutture**: organigramma aziendale (gerarchia organizzativa)
        - **DB_TNS**: merge generato automaticamente per import IT

        ### ✈️ Ruoli Chiave:

        - **Viaggiatore**: può inserire richieste trasferte/note spese
        - **Approvatore**: approva le richieste
        - **Controllore**: controlla/audita le spese
        - **Cassiere**: gestisce i pagamenti
        - **Segretario**: supporto amministrativo
        - **Assistenti**: deleghe per approvatori/controllori/segretari
        """)
        
        # Esempio struttura
        with st.expander("📖 Struttura dati e campi chiave"):
            st.markdown("""
            **TNS Personale** (dipendenti con ruoli):
            - ✅ TxCodFiscale OBBLIGATORIO (16 caratteri)
            - ✅ Titolare (nome dipendente)
            - ✅ Codice univoco
            - ✅ UNITA' OPERATIVA PADRE (gerarchia)
            - **Ruoli Approvazione Trasferte**:
              - Viaggiatore, Approvatore, Controllore, Cassiere
              - Segretario, Visualizzatori, Amministrazione
              - SegreteriA Red. Ass.ta, SegretariO Ass.to, Controllore Ass.to
              - RuoliAFC, RuoliHR, AltriRuoli
            - Sede_TNS, GruppoSind

            **TNS Strutture** (organigramma):
            - ❌ TxCodFiscale VUOTO (distingue da Personale)
            - ✅ DESCRIZIONE (nome unità organizzativa)
            - ✅ Codice univoco
            - Padre: UNITA' OPERATIVA PADRE (gerarchia)

            **DB_TNS** (generato per export):
            - Merge automatico: Strutture + Personale
            - Ordine critico: prima Strutture, poi Personale
            - Pronto per import nel sistema trasferte/note spese
            """)
    
    else:
        # Routing pagine
        if page == "📊 Dashboard":
            from ui.dashboard import show_dashboard
            show_dashboard()
        
        elif page == "🏗️ Gestione Strutture":
            from ui.strutture_view import show_strutture_view
            show_strutture_view()
        
        elif page == "👥 Gestione Personale":
            from ui.personale_view import show_personale_view
            show_personale_view()

        elif page == "🎭 Gestione Ruoli":
            from ui.ruoli_view import show_ruoli_view
            show_ruoli_view()

        elif page == "🤖 Assistente Bot":
            from ui.chatbot_view import show_chatbot_view
            show_chatbot_view()

        elif page == "🔄 Genera DB_TNS":
            from ui.merger_view import show_merger_view
            show_merger_view()
        
        elif page == "💾 Salvataggio & Export":
            from ui.save_export_view import show_save_export_view
            show_save_export_view()

        elif page == "🔍 Confronto File":
            from ui.diff_view import show_diff_view
            show_diff_view()


if __name__ == "__main__":
    main()
