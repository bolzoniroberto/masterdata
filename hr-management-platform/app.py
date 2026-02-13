"""
HR Management Platform - Applicazione Streamlit principale
Gruppo Il Sole 24 ORE
"""
import streamlit as st
from pathlib import Path
import sys
import pandas as pd

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

# Inizializza session state per UI
if 'sidebar_collapsed' not in st.session_state:
    st.session_state.sidebar_collapsed = False
if 'compare_versions' not in st.session_state:
    st.session_state.compare_versions = False
if 'current_page' not in st.session_state:
    st.session_state.current_page = "📊 Dashboard Home"

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

    # Esegui migrations se necessario
    try:
        from migrations.migration_001_add_import_versioning import migrate
        migrate(config.DB_PATH)
    except Exception as e:
        print(f"⚠️ Warning: Migration 001 failed: {str(e)}")

    try:
        from migrations.migration_002_add_checkpoint_milestone import migrate as migrate_002
        migrate_002(config.DB_PATH)
    except Exception as e:
        print(f"⚠️ Warning: Migration 002 failed: {str(e)}")


def load_excel_to_staging(uploaded_file):
    """
    Step 1: Carica file Excel in staging area (NON ancora nel database).
    L'utente potrà esplorare tutti i dati prima di decidere se importarli.

    Args:
        uploaded_file: File Excel uploadato

    Returns:
        Tuple (success, message)
    """
    try:
        import tempfile
        import pandas as pd

        # Salva file temporaneo
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xls') as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = Path(tmp.name)

        # Carica dati da Excel
        handler = ExcelHandler(tmp_path)
        personale, strutture, db_tns = handler.load_data()

        # Valida dati
        validator = DataValidator()

        # Valida personale
        personale_result = validator.validate_personale(personale)
        if not personale_result.is_valid():
            error_summary = personale_result.get_summary()
            # Mostra primi 10 errori dettagliati
            first_errors = personale_result.errors[:10]
            error_details = "\n".join([
                f"- Riga {e['row']}, campo '{e['field']}': {e['message']}"
                for e in first_errors
            ])
            more_msg = f"\n... e altri {len(personale_result.errors) - 10} errori" if len(personale_result.errors) > 10 else ""
            return False, f"""❌ **Errori validazione Personale**

{error_summary}

**Primi errori:**
{error_details}{more_msg}

**Suggerimento:** Verifica il file Excel per questi problemi comuni:
- Codici Fiscali mancanti o formato errato (16 caratteri alfanumerici)
- Campi obbligatori vuoti (Titolare, Codice, Unità Organizzativa)
- Caratteri speciali o formati non validi
"""

        # Valida strutture
        strutture_result = validator.validate_strutture(strutture)
        if not strutture_result.is_valid():
            error_summary = strutture_result.get_summary()
            # Mostra primi 10 errori dettagliati
            first_errors = strutture_result.errors[:10]
            error_details = "\n".join([
                f"- Riga {e['row']}, campo '{e['field']}': {e['message']}"
                for e in first_errors
            ])
            more_msg = f"\n... e altri {len(strutture_result.errors) - 10} errori" if len(strutture_result.errors) > 10 else ""
            return False, f"""❌ **Errori validazione Strutture**

{error_summary}

**Primi errori:**
{error_details}{more_msg}

**Suggerimento:** Verifica il file Excel per questi problemi comuni:
- Codici struttura mancanti o duplicati
- Descrizioni mancanti
- Riferimenti a strutture padre inesistenti
"""

        # Salva in STAGING (non ancora nel database!)
        st.session_state.excel_staging = {
            'personale_df': personale,
            'strutture_df': strutture,
            'filename': uploaded_file.name,
            'file_size_mb': len(uploaded_file.getvalue()) / (1024 * 1024),
        }

        return True, f"""✅ **File caricato con successo in memoria!**

📊 Contenuto:
- {len(personale)} dipendenti (Personale)
- {len(strutture)} strutture organizzative

🔍 **Prossimi passi:**
1. Esplora i dati usando le tab qui sotto
2. Verifica che tutto sia corretto
3. Clicca "Importa nel Database" quando sei pronto
"""

    except Exception as e:
        return False, f"❌ Errore caricamento: {str(e)}"


def preview_import_from_upload(uploaded_file, show_preview: bool = True):
    """
    DEPRECATO: Mantenuto per compatibilità.
    Ora usiamo load_excel_to_staging() + confirm_import_from_staging()
    """
    try:
        import tempfile
        import pandas as pd

        # Salva file temporaneo
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
            error_list = "\n".join(errors[:5])
            return False, f"Errori validazione dati:\n{error_list}", None

        # SE preview disabilitata: import diretto
        if not show_preview:
            import json
            from services.version_manager import VersionManager

            db_handler = st.session_state.database_handler

            # Begin import version
            version_id = db_handler.begin_import_version(
                source_filename=uploaded_file.name,
                user_note="Import diretto (senza preview)"
            )

            # Import data
            p_count, s_count = db_handler.import_from_dataframe(personale, strutture)

            # Complete version
            db_handler.complete_import_version(
                version_id, p_count, s_count,
                json.dumps({'note': 'Import diretto senza preview'})
            )

            # Create snapshot
            try:
                vm = VersionManager(db_handler, config.SNAPSHOTS_DIR)
                snapshot_path = vm.create_snapshot(
                    import_version_id=version_id,
                    source_filename=uploaded_file.name,
                    user_note="Import diretto (senza preview)"
                )
                snapshot_msg = f"\n📦 Snapshot creato per recovery: {Path(snapshot_path).name}"
            except Exception as e:
                print(f"⚠️ Errore creazione snapshot: {str(e)}")
                import traceback
                traceback.print_exc()
                snapshot_msg = f"\n⚠️ Warning: Snapshot non creato - {str(e)}"

            # Reload to session state
            success, msg = load_data_from_db()
            return success, f"✅ {msg}{snapshot_msg}", None

        # SE preview abilitata: genera preview semplice con stats file
        else:
            # Genera preview semplice con stats file
            preview_data = {
                'personale_df': personale,
                'strutture_df': strutture,
                'filename': uploaded_file.name,
                'file_size_mb': len(uploaded_file.getvalue()) / (1024 * 1024),
                'stats': {
                    'personale_count': len(personale),
                    'strutture_count': len(strutture),
                    'personale_sample': personale.head(5).to_dict('records'),
                    'strutture_sample': strutture.head(5).to_dict('records')
                }
            }

            return True, "Preview generata", preview_data

    except Exception as e:
        return False, f"Errore caricamento: {str(e)}", None


def confirm_import_from_staging(user_note: str = ""):
    """
    Step 2: Importa dati da staging area nel database.
    Chiamato dopo che l'utente ha esplorato e verificato i dati.

    Args:
        user_note: Nota opzionale utente

    Returns:
        Tuple (success, message)
    """
    try:
        import json
        from services.version_manager import VersionManager

        if 'excel_staging' not in st.session_state:
            return False, "❌ Nessun dato in staging. Carica prima un file Excel."

        staging = st.session_state.excel_staging
        db_handler = st.session_state.database_handler

        # Begin import version
        version_id = db_handler.begin_import_version(
            source_filename=staging['filename'],
            user_note=user_note or None
        )

        # Import data
        personale = staging['personale_df']
        strutture = staging['strutture_df']
        p_count, s_count = db_handler.import_from_dataframe(personale, strutture)

        # Complete import version
        changes_summary = json.dumps({
            'type': 'upload_import',
            'personale_imported': p_count,
            'strutture_imported': s_count
        })
        db_handler.complete_import_version(version_id, p_count, s_count, changes_summary)

        # Create snapshot
        try:
            vm = VersionManager(db_handler, config.SNAPSHOTS_DIR)
            snapshot_path = vm.create_snapshot(
                import_version_id=version_id,
                source_filename=staging['filename'],
                user_note=user_note
            )
            snapshot_msg = f"📦 Snapshot #{version_id}: {Path(snapshot_path).name}"
        except Exception as e:
            print(f"⚠️ Errore creazione snapshot: {str(e)}")
            snapshot_msg = f"⚠️ Snapshot non creato: {str(e)}"

        # Reload to session state
        success, msg = load_data_from_db()

        # Cleanup staging
        del st.session_state.excel_staging

        return success, f"""✅ **Dati importati nel database con successo!**

📊 Importati:
- {p_count} dipendenti (Personale)
- {s_count} strutture organizzative

📦 Snapshot creato automaticamente
{snapshot_msg}

🎉 Database pronto! Usa "📸 Crea Snapshot" per salvare modifiche importanti.
"""

    except Exception as e:
        return False, f"❌ Errore import: {str(e)}"


def confirm_import_with_version(preview_data: dict, user_note: str = ""):
    """
    Step 2: Conferma import dopo preview utente.

    Args:
        preview_data: Dati preview salvati in session state
        user_note: Nota opzionale utente
    """
    try:
        import json
        from services.version_manager import VersionManager

        db_handler = st.session_state.database_handler

        # Begin import version
        version_id = db_handler.begin_import_version(
            source_filename=preview_data['filename'],
            user_note=user_note or None
        )

        # Import data with version tracking
        # Nota: import_version_id viene gestito internamente da _log_audit
        personale = preview_data['personale_df']
        strutture = preview_data['strutture_df']

        p_count, s_count = db_handler.import_from_dataframe(personale, strutture)

        # Generate summary for version completion
        changes_summary = json.dumps({
            'type': 'upload_import',
            'personale_imported': p_count,
            'strutture_imported': s_count
        })

        # Complete import version
        db_handler.complete_import_version(version_id, p_count, s_count, changes_summary)

        # **NEW: Create snapshot for version recovery**
        try:
            vm = VersionManager(db_handler, config.SNAPSHOTS_DIR)
            snapshot_path = vm.create_snapshot(
                import_version_id=version_id,
                source_filename=preview_data['filename'],
                user_note=user_note
            )
            snapshot_msg = f"\n📦 Snapshot creato per recovery: {Path(snapshot_path).name}"
            print(f"✅ Snapshot creato: {snapshot_path}")
        except Exception as e:
            print(f"⚠️ Errore creazione snapshot: {str(e)}")
            import traceback
            traceback.print_exc()
            snapshot_msg = f"\n⚠️ Warning: Snapshot non creato - {str(e)}"

        # Reload to session state
        success, msg = load_data_from_db()

        # Cleanup preview data
        if 'import_preview' in st.session_state:
            del st.session_state.import_preview

        return success, f"""✅ **Dati caricati con successo nel database!**

📊 Importati:
- {p_count} dipendenti (Personale)
- {s_count} strutture organizzative

📦 Snapshot creato automaticamente per recovery
{snapshot_msg}

🎉 Puoi ora lavorare con i dati. Usa "📸 Crea Snapshot" per salvare modifiche importanti.
"""

    except Exception as e:
        return False, f"Errore conferma import: {str(e)}"


def show_top_toolbar():
    """
    Mostra toolbar superiore con bottoni Checkpoint e Milestone.
    Sempre visibile, ma bottoni disabilitati se dati non caricati.
    """
    # CSS per header fisso e miglioramenti UI
    st.markdown("""
    <style>
    /* Header fisso in alto */
    .main-header {
        position: sticky;
        top: 0;
        z-index: 999;
        background: linear-gradient(180deg, var(--background-color) 0%, var(--background-color) 90%, transparent 100%);
        padding: 1rem 0 1.5rem 0;
        border-bottom: 2px solid var(--primary-color);
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    /* Toolbar sempre visibile */
    .toolbar-container {
        background: linear-gradient(135deg, var(--secondary-background-color) 0%, var(--secondary-background-color) 100%);
        padding: 0.75rem 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid rgba(128,128,128,0.2);
    }

    /* Breadcrumb style */
    .breadcrumb {
        font-size: 0.9rem;
        color: var(--text-color);
        opacity: 0.8;
        margin-bottom: 0.5rem;
        padding: 0.5rem 0;
        font-weight: 500;
    }

    .breadcrumb b {
        color: var(--primary-color);
    }

    /* Migliora spacing generale */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* Stile bottoni migliorato */
    .stButton button {
        transition: all 0.2s ease;
    }

    .stButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }

    /* Sidebar migliorata */
    section[data-testid="stSidebar"] {
        background-color: var(--secondary-background-color);
        border-right: 2px solid var(--primary-color);
    }

    /* Menu sections headers */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        font-size: 0.9rem;
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
        opacity: 0.8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Menu buttons spacing */
    section[data-testid="stSidebar"] .stButton {
        margin-bottom: 0.25rem;
    }

    /* Section headers in sidebar */
    section[data-testid="stSidebar"] p strong {
        display: block;
        font-size: 0.75rem;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
        color: var(--text-color);
        opacity: 0.6;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Expander in sidebar (Operazioni Avanzate) */
    section[data-testid="stSidebar"] .streamlit-expanderHeader {
        font-size: 0.85rem;
        font-weight: 500;
        background-color: rgba(128, 128, 128, 0.1);
        border-radius: 0.3rem;
        padding: 0.4rem 0.6rem;
    }

    section[data-testid="stSidebar"] .streamlit-expanderContent {
        padding: 0.5rem 0;
        border-left: 2px solid rgba(128, 128, 128, 0.2);
        margin-left: 0.5rem;
        padding-left: 0.5rem;
    }

    /* Caption styling in sidebar */
    section[data-testid="stSidebar"] .caption {
        font-size: 0.7rem;
        opacity: 0.5;
        margin-bottom: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)

    data_loaded = st.session_state.data_loaded

    # Container toolbar con sfondo
    st.markdown('<div class="toolbar-container">', unsafe_allow_html=True)

    col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 2])

    with col1:
        if data_loaded:
            p_count = len(st.session_state.personale_df) if st.session_state.personale_df is not None else 0
            s_count = len(st.session_state.strutture_df) if st.session_state.strutture_df is not None else 0
            st.markdown(f"**📊 Dati:** {p_count} personale · {s_count} strutture")
        else:
            st.markdown("**📊 Azioni Rapide**")

    with col2:
        if st.button("💾 Checkpoint", use_container_width=True,
                     disabled=not data_loaded,
                     help="Salvataggio veloce stato attuale" if data_loaded else "Carica dati prima"):
            st.session_state.show_checkpoint_dialog = True
            st.rerun()

    with col3:
        if st.button("🏁 Milestone", use_container_width=True,
                     disabled=not data_loaded,
                     help="Milestone certificata con nota" if data_loaded else "Carica dati prima"):
            st.session_state.show_milestone_dialog = True
            st.rerun()

    with col4:
        if st.button("🔍 Ricerca", use_container_width=True,
                     disabled=not data_loaded,
                     help="Ricerca intelligente" if data_loaded else "Carica dati prima"):
            st.session_state.current_page = "🔍 Ricerca Intelligente"
            st.rerun()

    with col5:
        # Info utente/sessione
        if data_loaded:
            st.markdown("**✅ Database attivo**")
        else:
            st.markdown("**⚠️ Carica dati**")

    st.markdown('</div>', unsafe_allow_html=True)


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

        # Verifica che ci siano effettivamente dati
        if len(personale) == 0 and len(strutture) == 0:
            return False, "Database vuoto - nessun dato da caricare"

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
                print(f"✅ Auto-load from DB: {msg}")
            else:
                print(f"ℹ️ Auto-load skipped: {msg}")
        except Exception as e:
            print(f"⚠️ Auto-load error: {str(e)}")
            pass  # Database vuoto o errore, continua a chiedere upload

    # === TOP TOOLBAR (sempre visibile) ===
    show_top_toolbar()

    # Header principale (fisso)
    st.markdown('<div class="main-header">', unsafe_allow_html=True)
    st.title("✈️ Travel & Expense Approval Management")
    st.caption("Gruppo Il Sole 24 ORE - Gestione Ruoli Approvazione")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Sidebar per navigazione
    with st.sidebar:
        st.header("📋 Menu")

        # === PRIMO IMPORT (solo se DB vuoto) ===
        if not st.session_state.data_loaded:
            st.markdown("### 📁 Primo Import")
            st.info("👋 **Database vuoto**\n\nCarica un file Excel per iniziare")

            uploaded_file = st.file_uploader(
                "Carica file TNS (.xls/.xlsx)",
                type=['xls', 'xlsx'],
                help="File Excel con fogli 'TNS Personale' e 'TNS Strutture'"
            )

            # Helper per primo import
            if uploaded_file is None:
                with st.expander("💡 File di esempio", expanded=False):
                    st.caption("Puoi usare il file di test:")
                    st.code("data/input/TNS_HR_Data.xls", language=None)
                    st.caption("Trascinalo nel box sopra ⬆️")

            if uploaded_file is not None:
                # Mostra info file immediatamente
                st.caption(f"📄 **{uploaded_file.name}**")
                file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
                st.caption(f"💾 Dimensione: {file_size_mb:.2f} MB")

                # Check if already in staging mode
                if not st.session_state.get('excel_staging'):
                    # Load Excel to staging area (NOT yet in database)
                    with st.spinner("Caricamento file Excel in memoria..."):
                        success, message = load_excel_to_staging(uploaded_file)

                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)

            st.markdown("---")

        # Navigazione - MENU STRUTTURATO PULITO
        if st.session_state.data_loaded:
            st.markdown("### 🧭 Navigazione")

            # === DASHBOARD ===
            if st.button("📊 Dashboard Home", use_container_width=True,
                         type="primary" if st.session_state.current_page == "📊 Dashboard Home" else "secondary"):
                st.session_state.current_page = "📊 Dashboard Home"
                st.rerun()

            if st.button("🌳 Organigramma", use_container_width=True,
                         type="primary" if st.session_state.current_page == "🌳 Organigramma" else "secondary",
                         help="Vista albero e grafico dell'organigramma aziendale"):
                st.session_state.current_page = "🌳 Organigramma"
                st.rerun()

            st.markdown("**Gestione Dati**")

            # === GESTIONE ===
            if st.button("👥 Gestione Personale", use_container_width=True,
                         type="primary" if st.session_state.current_page == "👥 Gestione Personale" else "secondary"):
                st.session_state.current_page = "👥 Gestione Personale"
                st.rerun()

            if st.button("🏗️ Gestione Strutture", use_container_width=True,
                         type="primary" if st.session_state.current_page == "🏗️ Gestione Strutture" else "secondary"):
                st.session_state.current_page = "🏗️ Gestione Strutture"
                st.rerun()

            if st.button("🎭 Gestione Ruoli", use_container_width=True,
                         type="primary" if st.session_state.current_page == "🎭 Gestione Ruoli" else "secondary"):
                st.session_state.current_page = "🎭 Gestione Ruoli"
                st.rerun()

            st.markdown("**Ricerca & Analisi**")

            # === RICERCA & ANALISI ===
            if st.button("🔍 Ricerca Intelligente", use_container_width=True,
                         type="primary" if st.session_state.current_page == "🔍 Ricerca Intelligente" else "secondary"):
                st.session_state.current_page = "🔍 Ricerca Intelligente"
                st.rerun()

            if st.button("⚖️ Confronta Versioni", use_container_width=True,
                         type="primary" if st.session_state.current_page == "⚖️ Confronta Versioni" else "secondary"):
                st.session_state.current_page = "⚖️ Confronta Versioni"
                st.rerun()

            if st.button("📖 Log Modifiche", use_container_width=True,
                         type="primary" if st.session_state.current_page == "📖 Log Modifiche" else "secondary"):
                st.session_state.current_page = "📖 Log Modifiche"
                st.rerun()

            # === OPERAZIONI AVANZATE (collassate) ===
            st.markdown("---")
            with st.expander("🔧 Operazioni Avanzate", expanded=False):
                st.caption("Operazioni occasionali e amministrazione")

                # Database Management
                st.markdown("**Gestione Database**")

                uploaded_file_adv = st.file_uploader(
                    "📤 Re-import Excel",
                    type=['xls', 'xlsx'],
                    help="Carica nuovo file per sostituire dati esistenti",
                    key="upload_advanced"
                )

                if uploaded_file_adv is not None:
                    st.warning("⚠️ **Attenzione**: Re-import sovrascrive tutti i dati!")
                    if st.button("✅ Conferma Re-import", type="primary", use_container_width=True):
                        # Reset e reload
                        st.session_state.data_loaded = False
                        if 'excel_staging' in st.session_state:
                            del st.session_state.excel_staging
                        st.rerun()

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📸 Snapshot Manuale", use_container_width=True, key="adv_snapshot",
                                help="Crea snapshot manuale dello stato attuale"):
                        st.session_state.show_manual_snapshot_dialog = True
                        st.rerun()

                with col2:
                    if st.button("🗑️ Svuota DB", use_container_width=True, key="adv_clear",
                                help="Elimina tutti i dati dal database"):
                        st.session_state.show_clear_db_confirm = True
                        st.rerun()

                st.markdown("---")
                st.markdown("**Export & Versioning**")

                if st.button("📦 Gestione Versioni", use_container_width=True, key="adv_versions",
                             type="primary" if st.session_state.current_page == "📦 Gestione Versioni" else "secondary"):
                    st.session_state.current_page = "📦 Gestione Versioni"
                    st.rerun()

                if st.button("🔄 Genera DB_TNS", use_container_width=True, key="adv_dbtns",
                             type="primary" if st.session_state.current_page == "🔄 Genera DB_TNS" else "secondary"):
                    st.session_state.current_page = "🔄 Genera DB_TNS"
                    st.rerun()

                if st.button("💾 Export File", use_container_width=True, key="adv_export",
                             type="primary" if st.session_state.current_page == "💾 Salvataggio & Export" else "secondary"):
                    st.session_state.current_page = "💾 Salvataggio & Export"
                    st.rerun()

                st.markdown("---")
                st.markdown("**Verifica & Debug**")

                if st.button("🔍 Verifica Consistenza", use_container_width=True, key="adv_sync_check",
                             type="primary" if st.session_state.current_page == "🔍 Verifica Consistenza" else "secondary",
                             help="Verifica consistenza DB-Excel per responsabili e approvatori"):
                    st.session_state.current_page = "🔍 Verifica Consistenza"
                    st.rerun()

            page = st.session_state.current_page
        else:
            # Vista disponibile anche senza file caricato
            st.markdown("### 🧭 Navigazione")

            st.caption("Funzioni disponibili senza dati:")

            if st.button("⚖️ Confronta Versioni", use_container_width=True,
                         type="primary" if st.session_state.current_page == "⚖️ Confronta Versioni" else "secondary"):
                st.session_state.current_page = "⚖️ Confronta Versioni"
                st.rerun()

            with st.expander("🔧 Operazioni Avanzate", expanded=False):
                if st.button("📦 Gestione Versioni", use_container_width=True, key="nodb_versions",
                             type="primary" if st.session_state.current_page == "📦 Gestione Versioni" else "secondary"):
                    st.session_state.current_page = "📦 Gestione Versioni"
                    st.rerun()

            st.info("📤 Carica un file Excel per accedere a tutte le funzionalità")

            page = st.session_state.current_page
        
        st.markdown("---")

        # === INFO SIDEBAR FOOTER ===
        if st.session_state.data_loaded:
            with st.expander("ℹ️ Info Database", expanded=False):
                try:
                    # Ottieni ultima modifica
                    cursor = st.session_state.database_handler.conn.cursor()
                    cursor.execute("SELECT MAX(timestamp) FROM audit_log")
                    last_mod = cursor.fetchone()[0]
                    cursor.close()

                    if last_mod:
                        st.caption(f"**Ultima modifica:** {last_mod[:19]}")
                    else:
                        st.caption("**Nessuna modifica** registrata")

                    # Conta versioni
                    cursor = st.session_state.database_handler.conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM import_versions WHERE completed = 1")
                    version_count = cursor.fetchone()[0]
                    cursor.execute("SELECT COUNT(*) FROM import_versions WHERE completed = 1 AND certified = 1")
                    milestone_count = cursor.fetchone()[0]
                    cursor.close()

                    st.caption(f"**Versioni:** {version_count} ({milestone_count} milestone)")

                except Exception as e:
                    st.caption(f"Info non disponibile")

        st.markdown("---")
        st.caption(f"**v2.0** | UX Redesign")
        st.caption(f"{config.PAGE_TITLE[:30]}...")

    # === MANUAL SNAPSHOT DIALOG ===
    if st.session_state.get('show_manual_snapshot_dialog'):
        st.markdown("---")
        st.subheader("📸 Crea Snapshot Manuale")
        st.caption("Salva lo stato attuale del database per poterlo ripristinare in futuro")

        # Info stato attuale
        col1, col2 = st.columns(2)
        with col1:
            st.metric("👥 Personale", len(st.session_state.personale_df))
        with col2:
            st.metric("🏗️ Strutture", len(st.session_state.strutture_df))

        # Input nota
        snapshot_note = st.text_input(
            "💬 Nota snapshot (obbligatoria)",
            placeholder="es. Prima di riorganizzazione reparto IT",
            help="Descrivi perché stai creando questo snapshot"
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Crea Snapshot", type="primary", use_container_width=True, disabled=not snapshot_note):
                with st.spinner("Creazione snapshot in corso..."):
                    try:
                        from services.version_manager import VersionManager
                        import json

                        db = st.session_state.database_handler

                        # Crea import_version entry per snapshot manuale
                        version_id = db.begin_import_version(
                            source_filename="MANUAL_SNAPSHOT",
                            user_note=snapshot_note
                        )

                        # Complete version (no actual import, just snapshot)
                        p_count = len(st.session_state.personale_df)
                        s_count = len(st.session_state.strutture_df)

                        db.complete_import_version(
                            version_id, p_count, s_count,
                            json.dumps({'type': 'manual_snapshot'})
                        )

                        # Crea snapshot
                        vm = VersionManager(db, config.SNAPSHOTS_DIR)
                        snapshot_path = vm.create_snapshot(
                            import_version_id=version_id,
                            source_filename="MANUAL_SNAPSHOT",
                            user_note=snapshot_note
                        )

                        st.success(f"✅ Snapshot creato con successo!\n📦 {Path(snapshot_path).name}")
                        st.session_state.show_manual_snapshot_dialog = False
                        st.rerun()

                    except Exception as e:
                        st.error(f"❌ Errore creazione snapshot: {str(e)}")

        with col2:
            if st.button("❌ Annulla", use_container_width=True):
                st.session_state.show_manual_snapshot_dialog = False
                st.rerun()

        st.stop()

    # === CHECKPOINT DIALOG ===
    if st.session_state.get('show_checkpoint_dialog'):
        st.markdown("---")
        st.subheader("💾 Crea Checkpoint Veloce")
        st.caption("Salvataggio rapido dello stato attuale per backup/recovery")

        # Info stato
        col1, col2 = st.columns(2)
        with col1:
            st.metric("👥 Personale", len(st.session_state.personale_df))
        with col2:
            st.metric("🏗️ Strutture", len(st.session_state.strutture_df))

        # Nota opzionale
        checkpoint_note = st.text_input(
            "💬 Nota (opzionale)",
            placeholder="es. Prima di modifiche batch reparto IT",
            help="Lascia vuoto per auto-generare nota con timestamp"
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Crea Checkpoint", type="primary", use_container_width=True):
                with st.spinner("Creazione checkpoint..."):
                    try:
                        from services.version_manager import VersionManager
                        vm = VersionManager(st.session_state.database_handler, config.SNAPSHOTS_DIR)

                        success, message, snapshot_path = vm.create_checkpoint(checkpoint_note)

                        if success:
                            st.success(message)
                            st.session_state.show_checkpoint_dialog = False
                            st.rerun()
                        else:
                            st.error(message)

                    except Exception as e:
                        st.error(f"❌ Errore: {str(e)}")

        with col2:
            if st.button("❌ Annulla", use_container_width=True):
                st.session_state.show_checkpoint_dialog = False
                st.rerun()

        st.stop()

    # === MILESTONE DIALOG ===
    if st.session_state.get('show_milestone_dialog'):
        st.markdown("---")
        st.subheader("🏁 Crea Milestone Certificata")
        st.caption("Versione ufficiale con descrizione dettagliata dei cambiamenti")

        # Info stato
        col1, col2 = st.columns(2)
        with col1:
            st.metric("👥 Personale", len(st.session_state.personale_df))
        with col2:
            st.metric("🏗️ Strutture", len(st.session_state.strutture_df))

        # Nota obbligatoria
        milestone_note = st.text_input(
            "💬 Titolo Milestone (obbligatorio) *",
            placeholder="es. Riorganizzazione Q1 2026",
            help="Titolo breve e descrittivo della milestone"
        )

        # Descrizione obbligatoria
        milestone_description = st.text_area(
            "📝 Descrizione Cambiamenti (obbligatoria) *",
            placeholder="Descrivi dettagliatamente i cambiamenti:\n- Nuovo organigramma IT\n- Assegnazione approvatori\n- Aggiornamento strutture regionali",
            height=150,
            help="Descrizione completa dei cambiamenti inclusi in questa milestone"
        )

        col1, col2 = st.columns(2)

        with col1:
            can_create = bool(milestone_note and milestone_description)
            if st.button("✅ Crea Milestone", type="primary", use_container_width=True,
                         disabled=not can_create):
                with st.spinner("Creazione milestone certificata..."):
                    try:
                        from services.version_manager import VersionManager
                        vm = VersionManager(st.session_state.database_handler, config.SNAPSHOTS_DIR)

                        success, message, snapshot_path = vm.create_milestone(
                            milestone_note, milestone_description
                        )

                        if success:
                            st.success(message)
                            st.balloons()
                            st.session_state.show_milestone_dialog = False
                            st.rerun()
                        else:
                            st.error(message)

                    except Exception as e:
                        st.error(f"❌ Errore: {str(e)}")

        with col2:
            if st.button("❌ Annulla", use_container_width=True):
                st.session_state.show_milestone_dialog = False
                st.rerun()

        if not can_create:
            st.warning("⚠️ Nota e descrizione sono obbligatorie per le milestone")

        st.stop()

    # === CLEAR DATABASE CONFIRMATION DIALOG ===
    if st.session_state.get('show_clear_db_confirm'):
        st.markdown("---")
        st.error("### 🗑️ Conferma Eliminazione Database")
        st.warning("⚠️ **ATTENZIONE**: Questa operazione eliminerà **TUTTI** i dati dal database!")

        st.markdown("**Dati che verranno eliminati:**")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("👥 Personale", len(st.session_state.personale_df))
        with col2:
            st.metric("🏗️ Strutture", len(st.session_state.strutture_df))

        st.markdown("💡 **Suggerimento**: Crea un checkpoint prima di eliminare")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("💾 Checkpoint Prima", use_container_width=True):
                st.session_state.show_checkpoint_dialog = True
                st.session_state.show_clear_db_confirm = False
                st.rerun()

        with col2:
            confirm_text = st.text_input("Scrivi ELIMINA per confermare", key="confirm_clear")
            if st.button("🗑️ ELIMINA DATABASE", type="primary", use_container_width=True,
                        disabled=(confirm_text != "ELIMINA")):
                try:
                    cursor = st.session_state.database_handler.conn.cursor()
                    cursor.execute("DELETE FROM personale")
                    cursor.execute("DELETE FROM strutture")
                    cursor.execute("DELETE FROM db_tns")
                    st.session_state.database_handler.conn.commit()
                    st.session_state.data_loaded = False
                    st.session_state.show_clear_db_confirm = False
                    st.success("✅ Database eliminato")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Errore: {str(e)}")

        with col3:
            if st.button("❌ Annulla", use_container_width=True):
                st.session_state.show_clear_db_confirm = False
                st.rerun()

        st.stop()

    # === STAGING EXPLORER (dati Excel caricati ma non ancora nel DB) ===
    if st.session_state.get('excel_staging'):
        staging = st.session_state.excel_staging
        personale_df = staging['personale_df']
        strutture_df = staging['strutture_df']

        st.markdown("---")
        st.title("🔍 Esplora Dati Excel")
        st.caption(f"**File:** {staging['filename']} ({staging['file_size_mb']:.2f} MB)")
        st.info("📋 **I dati sono caricati in memoria (NON ancora nel database)**. Esplora e verifica tutto prima di importare.")

        # === CONTEGGI ===
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("👥 Dipendenti", len(personale_df))
        with col2:
            st.metric("🏗️ Strutture", len(strutture_df))
        with col3:
            st.metric("📊 Totale Record", len(personale_df) + len(strutture_df))

        st.markdown("---")

        # === TAB CON TABELLE COMPLETE ===
        tab1, tab2 = st.tabs(["👥 Personale (Dipendenti)", "🏗️ Strutture Organizzative"])

        with tab1:
            st.markdown(f"### 👥 Personale - Tutti i {len(personale_df)} dipendenti")
            st.caption("Tabella completa - Scorri per vedere tutti i record")

            # Mostra TUTTA la tabella
            st.dataframe(
                personale_df,
                use_container_width=True,
                height=500,  # Altezza fissa, scrollabile
                hide_index=True
            )

            # Stats aggiuntive
            with st.expander("📊 Statistiche Personale"):
                st.write(f"- **Totale dipendenti:** {len(personale_df)}")
                st.write(f"- **Codici Fiscali univoci:** {personale_df['TxCodFiscale'].nunique()}")
                st.write(f"- **Unità Organizzative:** {personale_df['Unità Organizzativa'].nunique()}")
                st.write(f"- **Approvatori (SÌ):** {len(personale_df[personale_df['Approvatore'] == 'SÌ'])}")

        with tab2:
            st.markdown(f"### 🏗️ Strutture - Tutte le {len(strutture_df)} strutture")
            st.caption("Tabella completa - Scorri per vedere tutte le strutture")

            # Mostra TUTTA la tabella
            st.dataframe(
                strutture_df,
                use_container_width=True,
                height=500,  # Altezza fissa, scrollabile
                hide_index=True
            )

            # Stats aggiuntive
            with st.expander("📊 Statistiche Strutture"):
                col_padre = "UNITA' OPERATIVA PADRE "
                st.write(f"- **Totale strutture:** {len(strutture_df)}")
                st.write(f"- **Codici univoci:** {strutture_df['Codice'].nunique()}")
                st.write(f"- **Con padre organizzativo:** {strutture_df[col_padre].notna().sum()}")

        st.markdown("---")

        # === CONFERMA IMPORT ===
        st.markdown("### ✅ Conferma Import nel Database")
        st.warning("⚠️ **Attenzione:** L'import nel database sovrascriverà i dati esistenti (se presenti).")

        user_note = st.text_input(
            "💬 Nota descrittiva (opzionale)",
            placeholder="es. Primo import database - dati gennaio 2026",
            help="Aggiungi una nota per identificare questo import negli snapshot"
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Importa nel Database", type="primary", use_container_width=True):
                with st.spinner("Importazione in corso nel database..."):
                    success, msg = confirm_import_from_staging(user_note)

                    if success:
                        st.success(msg)
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(msg)

        with col2:
            if st.button("❌ Annulla e Ricarica", use_container_width=True):
                del st.session_state.excel_staging
                st.info("🗑️ Dati rimossi da memoria. Carica un nuovo file.")
                st.rerun()

        st.stop()  # Blocca rendering resto pagina mentre in staging mode

    # === PREVIEW MODAL (se in attesa di conferma) ===
    if st.session_state.get('import_preview'):
        preview = st.session_state.import_preview
        stats = preview['stats']

        st.markdown("---")
        st.subheader("📄 Anteprima File Excel")
        st.caption(f"File: **{preview['filename']}** ({preview['file_size_mb']:.2f} MB)")

        # === CONTEGGI PRINCIPALI ===
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "👥 Dipendenti (Personale)",
                stats['personale_count'],
                help="Numero totale record in TNS Personale"
            )

        with col2:
            st.metric(
                "🏗️ Strutture Organizzative",
                stats['strutture_count'],
                help="Numero totale strutture organigramma"
            )

        with col3:
            total = stats['personale_count'] + stats['strutture_count']
            st.metric(
                "📊 Record Totali",
                total,
                help="Totale record che verranno importati"
            )

        # === ANTEPRIMA DATI (prime righe) ===
        st.markdown("---")
        st.markdown("### 🔍 Anteprima Dati (prime 5 righe)")

        tab1, tab2 = st.tabs(["👥 Personale", "🏗️ Strutture"])

        with tab1:
            if stats['personale_count'] > 0:
                personale_preview_df = pd.DataFrame(stats['personale_sample'])
                st.dataframe(
                    personale_preview_df,
                    use_container_width=True,
                    hide_index=True,
                    height=250
                )
                if stats['personale_count'] > 5:
                    st.caption(f"... e altri {stats['personale_count'] - 5} record")
            else:
                st.info("Nessun record personale nel file")

        with tab2:
            if stats['strutture_count'] > 0:
                strutture_preview_df = pd.DataFrame(stats['strutture_sample'])
                st.dataframe(
                    strutture_preview_df,
                    use_container_width=True,
                    hide_index=True,
                    height=250
                )
                if stats['strutture_count'] > 5:
                    st.caption(f"... e altre {stats['strutture_count'] - 5} strutture")
            else:
                st.info("Nessuna struttura nel file")

        # === CONFERMA CARICAMENTO ===
        st.markdown("---")
        st.markdown("### ✅ Conferma Caricamento")

        user_note = st.text_input(
            "💬 Nota descrittiva (opzionale)",
            placeholder="es. Aggiornamento organigramma Q1 2026",
            help="Nota per identificare questa versione nell'archivio"
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Carica nel Database", type="primary", use_container_width=True):
                with st.spinner("Caricamento in corso..."):
                    success, msg = confirm_import_with_version(preview, user_note)
                    if success:
                        st.success(msg)
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(msg)

        with col2:
            if st.button("❌ Annulla", use_container_width=True):
                del st.session_state.import_preview
                st.rerun()

        st.stop()  # Blocca rendering resto pagina durante preview

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

        ### 🚀 Primo Import - Come iniziare:

        1. **📁 Carica file Excel** dalla sidebar (in alto a sinistra)
           - File di esempio disponibile: `data/input/TNS_HR_Data.xls`
           - Oppure usa il tuo file Excel con fogli "TNS Personale" e "TNS Strutture"

        2. **🔍 Anteprima file** (se attivata):
           - Vedi conteggi: dipendenti, strutture, totale
           - Verifica prime 5 righe di ogni tipo
           - Aggiungi nota descrittiva (opzionale): es. "Primo import database"

        3. **✅ Conferma caricamento**:
           - Clicca "Carica nel Database"
           - Attendi il messaggio di successo
           - Uno snapshot viene creato automaticamente per recovery

        4. **🎉 Database pronto!**:
           - Naviga tra le sezioni usando il menu
           - Modifica ruoli e strutture
           - Usa "📸 Crea Snapshot Manuale" prima di modifiche importanti

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
        # === BREADCRUMB / PAGE INDICATOR ===
        page = st.session_state.current_page

        # Mostra breadcrumb
        st.markdown(f'<div class="breadcrumb">📍 Sei qui: <b>{page}</b></div>', unsafe_allow_html=True)
        st.markdown("---")

        # Routing pagine - NUOVO MENU
        if page == "📊 Dashboard Home":
            from ui.dashboard import show_dashboard
            show_dashboard()

        elif page == "🌳 Organigramma":
            from ui.organigramma_view import show_organigramma_view
            show_organigramma_view()

        elif page == "👥 Gestione Personale":
            from ui.personale_view import show_personale_view
            show_personale_view()

        elif page == "🏗️ Gestione Strutture":
            from ui.strutture_view import show_strutture_view
            show_strutture_view()

        elif page == "🎭 Gestione Ruoli":
            from ui.ruoli_view import show_ruoli_view
            show_ruoli_view()

        elif page == "🔍 Ricerca Intelligente":
            from ui.search_view import show_search_view
            show_search_view()

        elif page == "⚖️ Confronta Versioni":
            from ui.compare_view import show_compare_view
            show_compare_view()

        elif page == "📖 Log Modifiche":
            from ui.audit_log_view import show_audit_log_view
            show_audit_log_view()

        elif page == "📦 Gestione Versioni":
            from ui.version_management_view import show_version_management_view
            show_version_management_view()

        elif page == "🔄 Genera DB_TNS":
            from ui.merger_view import show_merger_view
            show_merger_view()

        elif page == "💾 Salvataggio & Export":
            from ui.save_export_view import show_save_export_view
            show_save_export_view()

        elif page == "🔍 Verifica Consistenza":
            from ui.sync_check_view import show_sync_check_view
            show_sync_check_view()


if __name__ == "__main__":
    main()
