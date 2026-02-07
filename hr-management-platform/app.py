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
        print(f"⚠️ Warning: Migration failed: {str(e)}")


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
        errors = validator.validate_all(personale, strutture)
        if errors:
            error_list = "\n".join(errors[:5])
            return False, f"❌ Errori validazione dati:\n{error_list}"

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

    # Header
    st.title("✈️ Travel & Expense Approval Management")
    st.subheader("Gruppo Il Sole 24 ORE - Gestione Ruoli Approvazione")
    
    # Sidebar per navigazione
    with st.sidebar:
        st.header("📋 Menu")

        # Upload file
        if not st.session_state.data_loaded:
            st.markdown("### 📁 Primo Import")
            st.info("👋 **Database vuoto**\n\nCarica un file Excel per iniziare")
        else:
            st.markdown("### 📁 Carica File Excel")

        # Toggle preview
        show_preview = st.checkbox(
            "🔍 Mostra anteprima file",
            value=True,
            help="Visualizza contenuto file prima di caricare nel database"
        )

        uploaded_file = st.file_uploader(
            "Carica file TNS (.xls/.xlsx)",
            type=['xls', 'xlsx'],
            help="File Excel con fogli 'TNS Personale' e 'TNS Strutture'"
        )

        # Helper per primo import
        if not st.session_state.data_loaded and uploaded_file is None:
            with st.expander("💡 File di esempio", expanded=False):
                st.caption("Puoi usare il file di test:")
                st.code("data/input/TNS_HR_Data.xls", language=None)
                st.caption("Trascinalo nel box sopra ⬆️")

        if uploaded_file is not None:
            # Mostra info file immediatamente
            st.caption(f"📄 **{uploaded_file.name}**")
            file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
            st.caption(f"💾 Dimensione: {file_size_mb:.2f} MB")

        if uploaded_file is not None and not st.session_state.data_loaded:
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

        # === PULSANTE RESET DATABASE ===
        if st.session_state.data_loaded:
            st.markdown("### 🔄 Database Manager")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📤 Re-import Excel", use_container_width=True):
                    # Pulisci tutti gli stati
                    st.session_state.data_loaded = False
                    if 'excel_staging' in st.session_state:
                        del st.session_state.excel_staging
                    if 'import_preview' in st.session_state:
                        del st.session_state.import_preview
                    if 'personale_df' in st.session_state:
                        del st.session_state.personale_df
                    if 'strutture_df' in st.session_state:
                        del st.session_state.strutture_df
                    st.info("✅ Database resettato. Carica un nuovo file Excel dalla sidebar.")
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

            # === SNAPSHOT MANUALI ===
            st.markdown("### 📸 Snapshot")
            if st.button("📸 Crea Snapshot Manuale", use_container_width=True, help="Salva stato attuale per recovery futuro"):
                # Mostra dialog per nota snapshot
                st.session_state.show_manual_snapshot_dialog = True
                st.rerun()

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
                    "📦 Gestione Versioni",
                    "🔍 Confronto & Storico"
                ],
                label_visibility="collapsed"
            )
        else:
            # Vista confronto disponibile anche senza file caricato
            page = st.radio(
                "Sezione",
                [
                    "🔍 Confronto & Storico"
                ],
                label_visibility="collapsed"
            )
            st.info("📤 Carica un file Excel per accedere a tutte le funzionalità")
        
        st.markdown("---")
        st.caption(f"v1.0 | {config.PAGE_TITLE}")

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

        elif page == "📦 Gestione Versioni":
            from ui.version_management_view import show_version_management_view
            show_version_management_view()

        elif page == "🔍 Confronto & Storico":
            from ui.comparison_audit_view import show_comparison_audit_view
            show_comparison_audit_view()


if __name__ == "__main__":
    main()
