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
    initial_sidebar_state="collapsed"  # Collapsed by default when using ribbon
)

# ── Design system – iniettato UNA SOLA VOLTA all'avvio ──────────────────────
from ui.styles import apply_common_styles
apply_common_styles()

# ── Ribbon Interface ────────────────────────────────────────────────────────
# from ui.ribbon import render_ribbon  # OLD: Custom HTML/JS ribbon (SecurityError issues)
# from ui.ribbon_simple import render_simple_ribbon  # SIMPLE: Bottoni base
from ui.ribbon_sticky import render_sticky_ribbon  # STICKY: Con sottomenu completi
# from ui.ribbon_listener import render_listener  # DISABLED
# from ui.mobile_menu import render_mobile_menu  # Not needed

# ── Handle ribbon navigation via query parameters ──────────────────────────
# Ribbon communicates via URL query params since it runs in an iframe
query_params = st.query_params

# Update current_page from query param (if present)
if 'current_page' in query_params:
    new_page = query_params['current_page']
    if 'current_page' not in st.session_state or st.session_state.current_page != new_page:
        st.session_state.current_page = new_page

# Update active_ribbon_tab from query param (if present)
if 'active_ribbon_tab' in query_params:
    new_tab = query_params['active_ribbon_tab']
    if 'active_ribbon_tab' not in st.session_state or st.session_state.active_ribbon_tab != new_tab:
        st.session_state.active_ribbon_tab = new_tab

# Update dialog flags from query params
if 'show_manual_snapshot_dialog' in query_params:
    st.session_state.show_manual_snapshot_dialog = query_params['show_manual_snapshot_dialog'] == 'true'

if 'show_clear_db_confirm' in query_params:
    st.session_state.show_clear_db_confirm = query_params['show_clear_db_confirm'] == 'true'

# Inizializza session state per UI
if 'sidebar_collapsed' not in st.session_state:
    st.session_state.sidebar_collapsed = False
if 'compare_versions' not in st.session_state:
    st.session_state.compare_versions = False
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Dashboard Home"

# ✅ NOTA: Listener per ribbon ora è DOPO render_ribbon() nel main()

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
        print(f"! Warning: Migration 001 failed: {str(e)}")

    try:
        from migrations.migration_002_add_checkpoint_milestone import migrate as migrate_002
        migrate_002(config.DB_PATH)
    except Exception as e:
        print(f"! Warning: Migration 002 failed: {str(e)}")

    try:
        from migrations.migration_003_add_hierarchy_fields import migrate as migrate_003
        migrate_003(config.DB_PATH)
    except Exception as e:
        print(f"! Warning: Migration 003 failed: {str(e)}")


def load_excel_to_staging(uploaded_file):
    """
    Step 1: Carica file Excel in staging area (NON ancora nel database).
    Supporta sia formato TNS (vecchio) che DB_ORG (nuovo con mappatura colonne).

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

        # === RILEVA FORMATO FILE ===
        xls = pd.ExcelFile(tmp_path)
        available_sheets = xls.sheet_names

        # Controlla se è formato DB_ORG (nuovo)
        if 'DB_ORG' in available_sheets:
            # Formato DB_ORG rilevato - salva file per import
            st.session_state.uploaded_db_org_file = uploaded_file
            st.session_state.db_org_file_ready = True

            # Non fare return - mostra invece un pulsante diretto
            return True, "DB_ORG_DETECTED"

        # Controlla se è formato TNS (vecchio)
        has_tns_personale = 'TNS Personale' in available_sheets or any('personale' in s.lower() for s in available_sheets)
        has_tns_strutture = 'TNS Strutture' in available_sheets or any('strutture' in s.lower() for s in available_sheets)

        if not has_tns_personale or not has_tns_strutture:
            # Formato non riconosciuto
            return False, f"""✗ **Formato file non riconosciuto**

**Fogli trovati nel file:**
{', '.join(available_sheets)}

**Formati supportati:**

1. **DB_ORG** (consigliato):
   - Foglio: "DB_ORG"
   - Sistema di mappatura colonne intelligente
   - Importa posizioni organizzative (vacanti e occupate)

2. **TNS** (legacy):
   - Fogli: "TNS Personale" e "TNS Strutture"
   - Sistema di import tradizionale

💡 **Suggerimento**: Usa il formato DB_ORG per l'import con mappatura colonne.
"""

        # Formato TNS rilevato - procedi con caricamento tradizionale
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
            return False, f"""✗ **Errori validazione Personale**

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
            return False, f"""✗ **Errori validazione Strutture**

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

        return True, f"""✓ **File caricato con successo in memoria!**

• Contenuto:
- {len(personale)} dipendenti (Personale)
- {len(strutture)} strutture organizzative

🔍 **Prossimi passi:**
1. Esplora i dati usando le tab qui sotto
2. Verifica che tutto sia corretto
3. Clicca "Importa nel Database" quando sei pronto
"""

    except Exception as e:
        return False, f"✗ Errore caricamento: {str(e)}"


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
                print(f"! Errore creazione snapshot: {str(e)}")
                import traceback
                traceback.print_exc()
                snapshot_msg = f"\n! Warning: Snapshot non creato - {str(e)}"

            # Reload to session state
            success, msg = load_data_from_db()
            return success, f"✓ {msg}{snapshot_msg}", None

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
            return False, "✗ Nessun dato in staging. Carica prima un file Excel."

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
            print(f"! Errore creazione snapshot: {str(e)}")
            snapshot_msg = f"! Snapshot non creato: {str(e)}"

        # Reload to session state
        success, msg = load_data_from_db()

        # Cleanup staging
        del st.session_state.excel_staging

        return success, f"""✓ **Dati importati nel database con successo!**

• Importati:
- {p_count} dipendenti (Personale)
- {s_count} strutture organizzative

📦 Snapshot creato automaticamente
{snapshot_msg}

• Database pronto! Usa "Crea Snapshot" per salvare modifiche importanti.
"""

    except Exception as e:
        return False, f"✗ Errore import: {str(e)}"


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
            print(f"✓ Snapshot creato: {snapshot_path}")
        except Exception as e:
            print(f"! Errore creazione snapshot: {str(e)}")
            import traceback
            traceback.print_exc()
            snapshot_msg = f"\n! Warning: Snapshot non creato - {str(e)}"

        # Reload to session state
        success, msg = load_data_from_db()

        # Cleanup preview data
        if 'import_preview' in st.session_state:
            del st.session_state.import_preview

        return success, f"""✓ **Dati caricati con successo nel database!**

• Importati:
- {p_count} dipendenti (Personale)
- {s_count} strutture organizzative

📦 Snapshot creato automaticamente per recovery
{snapshot_msg}

• Puoi ora lavorare con i dati. Usa "Crea Snapshot" per salvare modifiche importanti.
"""

    except Exception as e:
        return False, f"Errore conferma import: {str(e)}"


def show_top_toolbar():
    """
    Mostra topbar fissa con stats e pagina corrente.
    CSS gestito centralmente da ui/styles.py → apply_common_styles().
    """
    from ui.styles import render_topbar

    data_loaded = st.session_state.data_loaded
    current_page = st.session_state.get('current_page', 'Dashboard Home')

    if data_loaded:
        p_count = len(st.session_state.personale_df) if st.session_state.personale_df is not None else 0
        s_count = len(st.session_state.strutture_df) if st.session_state.strutture_df is not None else 0
        stats = f"{p_count} dip · {s_count} stru"
    else:
        stats = "Nessun dato"

    render_topbar(page_name=current_page, stats=stats)


def load_data_from_db():
    """
    Carica dati dal database SQLite in session state.

    Supporta sia schema vecchio (personale/strutture) che nuovo (employees/org_units).
    Converte automaticamente dal nuovo schema al formato dataframe per compatibilità UI.

    Viene usato:
    - Dopo upload Excel (che importa nel DB)
    - Quando app si riavvia (carica da DB persistente)
    """
    try:
        db_handler = st.session_state.database_handler
        conn = db_handler.get_connection()
        cursor = conn.cursor()

        # === PROVA PRIMA NUOVO SCHEMA (employees/org_units) ===
        cursor.execute("SELECT COUNT(*) FROM employees")
        employees_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM org_units")
        org_units_count = cursor.fetchone()[0]

        if employees_count > 0 or org_units_count > 0:
            print(f"[AUTO-LOAD] Trovati dati in nuovo schema: {employees_count} employees, {org_units_count} org_units")

            # Query employees directly from database
            # Note: Some fields like CDCCOSTO are in org_units, not employees
            cursor.execute("""
                SELECT
                    tx_cod_fiscale,
                    titolare,
                    codice,
                    cognome,
                    nome,
                    qualifica,
                    area,
                    sede,
                    livello,
                    contratto,
                    ral,
                    data_assunzione,
                    data_cessazione,
                    societa,
                    sottoarea,
                    sesso,
                    email,
                    reports_to_cf,
                    cod_tns,
                    padre_tns,
                    matricola
                FROM employees
                WHERE tx_cod_fiscale IS NOT NULL
                ORDER BY titolare
            """)
            employees_rows = cursor.fetchall()

            if employees_rows:
                personale_data = []
                for row in employees_rows:
                    personale_data.append({
                        'TxCodFiscale': row[0] or '',
                        'Titolare': row[1] or '',
                        'Codice': row[2] or '',
                        'DESCRIZIONE': f"{row[3] or ''} {row[4] or ''}".strip(),
                        'Qualifica': row[5] or '',
                        'Area': row[6] or '',
                        'Sede': row[7] or '',
                        'LIVELLO': row[8] or '',
                        'Contratto': row[9] or '',
                        'RAL': row[10] or 0,
                        'Data Assunzione': str(row[11]) if row[11] else '',
                        'Data Cessazione': str(row[12]) if row[12] else '',
                        'Società': row[13] or '',
                        'SottoArea': row[14] or '',
                        'Sesso': row[15] or '',
                        'Email': row[16] or '',
                        'CF Responsabile Diretto': row[17] or '',  # Hierarchy: HR
                        'Codice TNS': row[18] or '',               # Hierarchy: TNS
                        'Padre TNS': row[19] or '',                # Hierarchy: TNS
                        'Matricola': row[20] or '',
                        # Note: CDCCOSTO would need join with org_units - skip for now
                        'CDCCOSTO': '',
                        'Unità Organizzativa': '',  # Would need org_units join
                    })
                personale = pd.DataFrame(personale_data)
            else:
                personale = pd.DataFrame()

            # Query org units directly
            cursor.execute("""
                SELECT
                    codice,
                    descrizione,
                    unita_org_livello1,
                    unita_org_livello2,
                    cdccosto,
                    livello,
                    cdc_amm,
                    testata_gg
                FROM org_units
                WHERE codice IS NOT NULL
                ORDER BY descrizione
            """)
            org_units_rows = cursor.fetchall()

            if org_units_rows:
                strutture_data = []
                for row in org_units_rows:
                    strutture_data.append({
                        'Codice': row[0] or '',
                        'DESCRIZIONE': row[1] or '',
                        'Unità Organizzativa': row[2] or '',
                        'Unità Organizzativa 2': row[3] or '',
                        'CDCCOSTO': row[4] or '',
                        'LIVELLO': str(row[5]) if row[5] is not None else '',
                        'CdC Amm': row[6] or '',
                        'Testata GG/2': row[7] or '',
                        # Parent relationship would need recursive join - skip for now
                        'UNITA\' OPERATIVA PADRE ': '',
                    })
                strutture = pd.DataFrame(strutture_data)
            else:
                strutture = pd.DataFrame()

            print(f"[AUTO-LOAD] Convertiti a vecchio formato: {len(personale)} personale, {len(strutture)} strutture")

        else:
            # === FALLBACK A VECCHIO SCHEMA (personale/strutture) ===
            print("[AUTO-LOAD] Nuovo schema vuoto, provo vecchio schema...")
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
        import traceback
        traceback.print_exc()
        return False, f"Errore caricamento database: {str(e)}"


def main():
    """Funzione principale applicazione"""

    # === AUTO-LOAD DA DATABASE ===
    # Se database ha dati e session state è vuoto, carica automaticamente
    if not st.session_state.data_loaded and config.DB_PATH.exists():
        try:
            # DEBUG: Log per capire cosa succede
            print(f"[DEBUG] Tentativo auto-load da DB: {config.DB_PATH}")
            print(f"[DEBUG] data_loaded prima: {st.session_state.data_loaded}")

            # Caricamento silenzioso - nessun spinner per non rallentare UX
            success, msg = load_data_from_db()

            print(f"[DEBUG] Auto-load result: success={success}, msg={msg}")

            if success:
                st.session_state.data_loaded = True
                # Nota: Questo è normale ad ogni refresh - carica dati esistenti dal DB
                print(f"✓ Auto-load from DB: {msg}")
                print(f"[DEBUG] data_loaded dopo: {st.session_state.data_loaded}")
            else:
                # Auto-load fallito - salva errore per mostrarlo
                st.session_state.autoload_error = msg
                print(f"• Auto-load skipped: {msg}")
        except Exception as e:
            import traceback
            error_msg = f"Errore auto-load: {str(e)}"
            st.session_state.autoload_error = error_msg
            print(f"! Auto-load error: {str(e)}")
            print(f"[DEBUG] Traceback completo:")
            traceback.print_exc()
    else:
        if st.session_state.data_loaded:
            print(f"[DEBUG] Dati già caricati in session state")
        else:
            print(f"[DEBUG] Database non esiste: {config.DB_PATH}")

    # ═══════════════════════════════════════════════════════════════════════════
    # RIBBON INTERFACE - STICKY CON SOTTOMENU (Nativo Streamlit, no SecurityError)
    # ═══════════════════════════════════════════════════════════════════════════
    if st.session_state.data_loaded:
        render_sticky_ribbon()  # Sticky ribbon con sottomenu completi

        # Note: Ribbon buttons set st.session_state.current_page,
        # then page routing below (line 1318+) handles rendering

    # === TOP TOOLBAR (sempre visibile) ===
    # Rimosso temporaneamente per evitare conflitti con ribbon
    # show_top_toolbar()

    # ═══════════════════════════════════════════════════════════
    # SIDEBAR - Quick Panel with actions and contextual tools
    # ═══════════════════════════════════════════════════════════
    with st.sidebar:
        from ui.sidebar_quick_panel import render_sidebar
        render_sidebar()

    # OLD SIDEBAR NAVIGATION CODE REMOVED - Now using ribbon + quick panel

    # === MANUAL SNAPSHOT DIALOG ===
    if st.session_state.get('show_manual_snapshot_dialog'):
        st.markdown("---")
        st.subheader("Crea Snapshot Manuale")
        st.caption("Salva lo stato attuale del database per poterlo ripristinare in futuro")

        # Info stato attuale
        col1, col2 = st.columns(2)
        with col1:
            pdf = st.session_state.get('personale_df')
            p_count = len(pdf) if pdf is not None else 0
            st.metric("👥 Personale", p_count)
        with col2:
            sdf = st.session_state.get('strutture_df')
            s_count = len(sdf) if sdf is not None else 0
            st.metric("🏗️ Strutture", s_count)

        # Input nota
        snapshot_note = st.text_input(
            "💬 Nota snapshot (obbligatoria)",
            placeholder="es. Prima di riorganizzazione reparto IT",
            help="Descrivi perché stai creando questo snapshot"
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Crea Snapshot", type="primary", use_container_width=True, disabled=not snapshot_note):
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
                        pdf = st.session_state.get('personale_df')
                        sdf = st.session_state.get('strutture_df')
                        p_count = len(pdf) if pdf is not None else 0
                        s_count = len(sdf) if sdf is not None else 0

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

                        st.success(f"✓ Snapshot creato con successo!\n📦 {Path(snapshot_path).name}")
                        st.session_state.show_manual_snapshot_dialog = False
                        st.rerun()

                    except Exception as e:
                        st.error(f"✗ Errore creazione snapshot: {str(e)}")

        with col2:
            if st.button("Annulla", use_container_width=True):
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
            pdf = st.session_state.get('personale_df')
            p_count = len(pdf) if pdf is not None else 0
            st.metric("👥 Personale", p_count)
        with col2:
            sdf = st.session_state.get('strutture_df')
            s_count = len(sdf) if sdf is not None else 0
            st.metric("🏗️ Strutture", s_count)

        # Nota opzionale
        checkpoint_note = st.text_input(
            "💬 Nota (opzionale)",
            placeholder="es. Prima di modifiche batch reparto IT",
            help="Lascia vuoto per auto-generare nota con timestamp"
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✓ Crea Checkpoint", type="primary", use_container_width=True):
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
                        st.error(f"✗ Errore: {str(e)}")

        with col2:
            if st.button("Annulla", use_container_width=True):
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
            pdf = st.session_state.get('personale_df')
            p_count = len(pdf) if pdf is not None else 0
            st.metric("👥 Personale", p_count)
        with col2:
            sdf = st.session_state.get('strutture_df')
            s_count = len(sdf) if sdf is not None else 0
            st.metric("🏗️ Strutture", s_count)

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
            if st.button("✓ Crea Milestone", type="primary", use_container_width=True,
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
                        st.error(f"✗ Errore: {str(e)}")

        with col2:
            if st.button("Annulla", use_container_width=True):
                st.session_state.show_milestone_dialog = False
                st.rerun()

        if not can_create:
            st.warning("! Nota e descrizione sono obbligatorie per le milestone")

        st.stop()

    # === CLEAR DATABASE CONFIRMATION DIALOG ===
    if st.session_state.get('show_clear_db_confirm'):
        st.markdown("---")
        st.error("### 🗑️ Conferma Eliminazione Database")
        st.warning("! **ATTENZIONE**: Questa operazione eliminerà **TUTTI** i dati dal database!")

        st.markdown("**Dati che verranno eliminati:**")
        col1, col2 = st.columns(2)
        with col1:
            pdf = st.session_state.get('personale_df')
            p_count = len(pdf) if pdf is not None else 0
            st.metric("👥 Personale", p_count)
        with col2:
            sdf = st.session_state.get('strutture_df')
            s_count = len(sdf) if sdf is not None else 0
            st.metric("🏗️ Strutture", s_count)

        st.markdown("💡 **Suggerimento**: Crea un checkpoint prima di eliminare")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("Checkpoint Prima", use_container_width=True):
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
                    st.success("✓ Database eliminato")
                    st.rerun()
                except Exception as e:
                    st.error(f"✗ Errore: {str(e)}")

        with col3:
            if st.button("Annulla", use_container_width=True):
                st.session_state.show_clear_db_confirm = False
                st.rerun()

        st.stop()

    # ═══════════════════════════════════════════════════════════
    # MODAL WIZARDS RENDERING (blocking - must be before routing)
    # ═══════════════════════════════════════════════════════════

    # Onboarding Wizard Modal (first-time setup)
    from ui.wizard_state_manager import get_onboarding_wizard
    onboarding_wizard = get_onboarding_wizard()
    if onboarding_wizard.is_active:
        from ui.wizard_onboarding_modal import render_onboarding_wizard
        render_onboarding_wizard()
        st.stop()  # Block all other content rendering

    # Import Wizard Modal
    from ui.wizard_state_manager import get_import_wizard
    import_wizard = get_import_wizard()
    if import_wizard.is_active:
        from ui.wizard_import_modal import render_wizard_import_modal
        render_wizard_import_modal()
        st.stop()  # Block all other content rendering

    # Settings Wizard Modal
    from ui.wizard_state_manager import get_settings_wizard
    settings_wizard = get_settings_wizard()
    if settings_wizard.is_active:
        from ui.wizard_settings_modal import render_wizard_settings_modal
        render_wizard_settings_modal()
        st.stop()  # Block all other content rendering

    # ═══════════════════════════════════════════════════════════
    # CONTINUE WITH NORMAL PAGE ROUTING
    # ═══════════════════════════════════════════════════════════

    # === STAGING EXPLORER (dati Excel caricati ma non ancora nel DB) ===
    if st.session_state.get('excel_staging'):
        staging = st.session_state.excel_staging

        # Handle different formats (DB_ORG vs TNS)
        file_format = staging.get('format', 'TNS')

        if file_format == 'DB_ORG':
            # DB_ORG format - single dataframe
            df = staging.get('data')
            if df is not None:
                personale_df = df[df['TxCodFiscale'].notna()] if 'TxCodFiscale' in df.columns else df
                strutture_df = df[df['TxCodFiscale'].isna()] if 'TxCodFiscale' in df.columns else pd.DataFrame()
            else:
                personale_df = pd.DataFrame()
                strutture_df = pd.DataFrame()
        else:
            # TNS format - separate dataframes
            personale_df = staging.get('personale_df', staging.get('personale', pd.DataFrame()))
            strutture_df = staging.get('strutture_df', staging.get('strutture', pd.DataFrame()))

        st.markdown("---")
        st.title("🔍 Esplora Dati Excel")
        st.caption(f"**File:** {staging.get('filename', 'N/A')} ({staging.get('file_size_mb', 0):.2f} MB)")
        st.info("• **I dati sono caricati in memoria (NON ancora nel database)**. Esplora e verifica tutto prima di importare.")

        # === CONTEGGI ===
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("👥 Dipendenti", len(personale_df))
        with col2:
            st.metric("🏗️ Strutture", len(strutture_df))
        with col3:
            st.metric("• Totale Record", len(personale_df) + len(strutture_df))

        st.markdown("---")

        # === TAB CON TABELLE COMPLETE ===
        tab1, tab2 = st.tabs(["👥 Personale (Dipendenti)", "🏗️ Strutture Organizzative"])

        with tab1:
            st.markdown(f"### Personale - Tutti i {len(personale_df)} dipendenti")
            st.caption("Tabella completa - Scorri per vedere tutti i record")

            # Mostra TUTTA la tabella
            st.dataframe(
                personale_df,
                use_container_width=True,
                height=500,  # Altezza fissa, scrollabile
                hide_index=True
            )

            # Stats aggiuntive
            with st.expander("• Statistiche Personale"):
                st.write(f"- **Totale dipendenti:** {len(personale_df)}")
                st.write(f"- **Codici Fiscali univoci:** {personale_df['TxCodFiscale'].nunique()}")
                st.write(f"- **Unità Organizzative:** {personale_df['Unità Organizzativa'].nunique()}")
                st.write(f"- **Approvatori (SÌ):** {len(personale_df[personale_df['Approvatore'] == 'SÌ'])}")

        with tab2:
            st.markdown(f"### Strutture - Tutte le {len(strutture_df)} strutture")
            st.caption("Tabella completa - Scorri per vedere tutte le strutture")

            # Mostra TUTTA la tabella
            st.dataframe(
                strutture_df,
                use_container_width=True,
                height=500,  # Altezza fissa, scrollabile
                hide_index=True
            )

            # Stats aggiuntive
            with st.expander("• Statistiche Strutture"):
                col_padre = "UNITA' OPERATIVA PADRE "
                st.write(f"- **Totale strutture:** {len(strutture_df)}")
                st.write(f"- **Codici univoci:** {strutture_df['Codice'].nunique()}")
                st.write(f"- **Con padre organizzativo:** {strutture_df[col_padre].notna().sum()}")

        st.markdown("---")

        # === CONFERMA IMPORT ===
        st.markdown("### ✓ Conferma Import nel Database")
        st.warning("! **Attenzione:** L'import nel database sovrascriverà i dati esistenti (se presenti).")

        user_note = st.text_input(
            "💬 Nota descrittiva (opzionale)",
            placeholder="es. Primo import database - dati gennaio 2026",
            help="Aggiungi una nota per identificare questo import negli snapshot"
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✓ Importa nel Database", type="primary", use_container_width=True):
                with st.spinner("Importazione in corso nel database..."):
                    success, msg = confirm_import_from_staging(user_note)

                    if success:
                        st.success(msg)
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(msg)

        with col2:
            if st.button("Annulla e Ricarica", use_container_width=True):
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
                "• Record Totali",
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
        st.markdown("### ✓ Conferma Caricamento")

        user_note = st.text_input(
            "💬 Nota descrittiva (opzionale)",
            placeholder="es. Aggiornamento organigramma Q1 2026",
            help="Nota per identificare questa versione nell'archivio"
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✓ Carica nel Database", type="primary", use_container_width=True):
                with st.spinner("Caricamento in corso..."):
                    success, msg = confirm_import_with_version(preview, user_note)
                    if success:
                        st.success(msg)
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(msg)

        with col2:
            if st.button("Annulla", use_container_width=True):
                del st.session_state.import_preview
                st.rerun()

        st.stop()  # Blocca rendering resto pagina durante preview

    # === CASO SPECIALE: Import DB_ORG accessibile anche senza dati caricati ===
    if st.session_state.current_page == "Import DB_ORG":
        from ui.db_org_import_view import render_db_org_import_view
        render_db_org_import_view()
        st.stop()  # Blocca rendering resto pagina

    # === DEBUG INFO (rimuovere dopo fix) ===
    with st.expander("🔧 DEBUG INFO", expanded=True):
        st.write(f"**data_loaded:** {st.session_state.data_loaded}")
        st.write(f"**DB path:** {config.DB_PATH}")
        st.write(f"**DB exists:** {config.DB_PATH.exists()}")
        if config.DB_PATH.exists():
            import os
            st.write(f"**DB size:** {os.path.getsize(config.DB_PATH) / 1024:.2f} KB")

        if st.session_state.get('personale_df') is not None:
            st.write(f"**personale_df:** {len(st.session_state.personale_df)} records")
        else:
            st.write(f"**personale_df:** None")

        if st.session_state.get('strutture_df') is not None:
            st.write(f"**strutture_df:** {len(st.session_state.strutture_df)} records")
        else:
            st.write(f"**strutture_df:** None")

        # Mostra errore auto-load se presente
        if st.session_state.get('autoload_error'):
            st.error(f"**❌ Errore Auto-load:**\n{st.session_state.autoload_error}")

    # Contenuto principale
    if not st.session_state.data_loaded:
        # ═══════════════════════════════════════════════════════════
        # WELCOME SCREEN - Professional onboarding experience
        # ═══════════════════════════════════════════════════════════

        # Hero section
        st.markdown("""
        <div style="text-align: center; padding: 3rem 1rem;">
            <h1>🎉 Benvenuto in HR Management Platform</h1>
            <p style="font-size: 1.2rem; color: var(--text-color-secondary);">
                Sistema completo per gestione organigrammi e dati HR
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Main actions - centered layout
        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            st.markdown("### Per iniziare, scegli:")

            st.markdown("<br>", unsafe_allow_html=True)

            # PRIMARY: Guided setup
            if st.button(
                "🚀 AVVIA CONFIGURAZIONE GUIDATA",
                type="primary",
                use_container_width=True,
                help="Setup guidato passo-passo (consigliato per nuovi utenti)"
            ):
                from ui.wizard_onboarding_modal import get_onboarding_wizard
                get_onboarding_wizard().activate()
                st.rerun()

            st.markdown("---")

            # ALTERNATIVE: Direct import
            if st.button(
                "📂 Importa File Direttamente",
                use_container_width=True,
                help="Per utenti esperti - salta la guida e importa subito"
            ):
                from ui.wizard_state_manager import get_import_wizard
                get_import_wizard().activate()
                st.rerun()

        st.markdown("<br><br>", unsafe_allow_html=True)

        # Info boxes - expandable
        col1, col2 = st.columns(2)

        with col1:
            with st.expander("💡 Cosa puoi fare con questa piattaforma"):
                st.markdown("""
                - **Gestire organigrammi** multipli (HR, TNS, SGSL)
                - **Importare dati** da Excel con mappatura intelligente
                - **Visualizzare gerarchie** interattive
                - **Tracciare modifiche** con versioning automatico
                - **Generare export** in formato DB_TNS
                - **Validare dati** con controlli automatici
                """)

        with col2:
            with st.expander("📚 Formati file supportati"):
                st.markdown("""
                **DB_ORG** (consigliato):
                - Mappatura colonne automatica
                - 135+ colonne supportate
                - Validazione avanzata

                **TNS** (legacy):
                - Fogli separati per Personale e Strutture
                - Compatibilità con sistema legacy
                """)

        # Additional help
        with st.expander("🆘 Serve aiuto?"):
            st.markdown("""
            **File di esempio**: Puoi usare `data/input/TNS_HR_Data.xls` per testare l'import.

            **Primo import**: Segui la configurazione guidata per un setup passo-passo.

            **Supporto**: Per assistenza, contatta il team IT.
            """)
    
    else:
        # === BREADCRUMB / PAGE INDICATOR ===
        page = st.session_state.current_page

        # Auto-select default pages when ribbon tabs are active
        active_ribbon_tab = st.session_state.get('active_ribbon_tab', 'Home')

        if active_ribbon_tab == 'Organigrammi' and page == "Dashboard Home":
            # User clicked Organigrammi tab but no specific organigramma selected
            # Auto-select HR Hierarchy as default
            page = "HR Hierarchy"
            st.session_state.current_page = "HR Hierarchy"

        elif active_ribbon_tab == 'Gestione Dati' and page == "Dashboard Home":
            # User clicked Gestione Dati tab but no specific page selected
            # Auto-select Gestione Personale as default
            page = "Gestione Personale"
            st.session_state.current_page = "Gestione Personale"

        # Routing pagine - NUOVO MENU
        if page == "Dashboard Home":
            from ui.dashboard import show_dashboard
            show_dashboard()

        elif page == "Dashboard DB_ORG":
            from ui.dashboard_extended import render_dashboard_extended
            render_dashboard_extended()

        elif page == "HR Hierarchy":
            from ui.orgchart_hr_view import render_orgchart_hr_view
            render_orgchart_hr_view()

        elif page == "ORG Hierarchy":
            from ui.orgchart_org_view import render_orgchart_org_view
            render_orgchart_org_view()

        elif page == "TNS Hierarchy":
            from ui.orgchart_tns_structures_view import render_orgchart_tns_structures_view
            render_orgchart_tns_structures_view()

        elif page == "SGSL Safety":
            st.info("🚧 Organigramma SGSL Safety in development")

        elif page == "Unità Organizzative":
            from ui.orgchart_positions_view import render_orgchart_positions_view
            render_orgchart_positions_view()

        elif page == "Gestione Personale":
            from ui.personale_view import show_personale_view
            show_personale_view()

        elif page == "Gestione Strutture":
            from ui.strutture_view import show_strutture_view
            show_strutture_view()

        elif page == "Gestione Posizioni":
            from ui.posizioni_view import show_posizioni_view
            show_posizioni_view()

        elif page == "Gestione Ruoli":
            from ui.ruoli_view import show_ruoli_view
            show_ruoli_view()

        elif page == "Ricerca Intelligente":
            from ui.search_view import show_search_view
            show_search_view()

        elif page == "Confronta Versioni":
            from ui.compare_view import show_compare_view
            show_compare_view()

        elif page == "Log Modifiche":
            from ui.audit_log_view import show_audit_log_view
            show_audit_log_view()

        elif page == "Gestione Versioni":
            from ui.version_management_view import show_version_management_view
            show_version_management_view()

        elif page == "Genera DB_TNS":
            from ui.merger_view import show_merger_view
            show_merger_view()

        elif page == "💾 Salvataggio & Export":
            from ui.save_export_view import show_save_export_view
            show_save_export_view()

        elif page == "Verifica Consistenza":
            from ui.sync_check_view import show_sync_check_view
            show_sync_check_view()

        elif page == "Import DB_ORG":
            from ui.db_org_import_view import render_db_org_import_view
            render_db_org_import_view()

        elif page == "Scheda Dipendente":
            from ui.employee_card_view import render_employee_card_view
            render_employee_card_view()

        elif page == "Scheda Strutture":
            from ui.structure_card_view import render_structure_card_view
            render_structure_card_view()

        elif page == "Vista Tabellare":
            from ui.tabular_view import show_tabular_view
            show_tabular_view()

        elif page == "Impostazioni":
            from ui.settings_view import show_settings_view
            show_settings_view()


if __name__ == "__main__":
    main()
