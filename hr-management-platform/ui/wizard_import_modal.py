"""
Import Wizard Modal - 5-step guided import flow for DB_ORG files.

Steps:
1. Upload File
2. Column Mapping (conditional - auto-skip if 100% match)
3. Import Configuration (smart UI based on file content)
4. Confirmation & Execution
5. Results & Transition
"""

import streamlit as st
import pandas as pd
import tempfile
import time
import json
from pathlib import Path
from typing import Dict, Tuple, Optional
from ui.wizard_state_manager import get_import_wizard


def auto_detect_columns(df: pd.DataFrame) -> Tuple[Dict[str, str], float]:
    """
    Auto-detect column mapping with fuzzy matching.

    Args:
        df: DataFrame with Excel columns

    Returns:
        Tuple of (mapping_dict, match_percentage)
    """
    REQUIRED = {
        'ID': ['id', 'codice', 'cod', 'id_posizione'],
        'TxCodFiscale': ['cf', 'codice fiscale', 'cod_fiscale', 'codicefiscale', 'txcodfiscale'],
        'Titolare': ['titolare', 'nome', 'dipendente', 'name'],
        'Unità Organizzativa': ['uo', 'unita org', 'unit', 'unità organizzativa', 'unita organizzativa'],
        'Unità Organizzativa 2': ['uo2', 'unita org 2', 'unità liv 2', 'unità organizzativa 2'],
        'ReportsTo': ['reportsto', 'reports to', 'superiore', 'manager', 'capo'],
        # Hierarchy columns for organigrammi
        'CF Responsabile Diretto': ['cf responsabile', 'responsabile diretto', 'cf superiore', 'parent cf', 'resp diretto'],
        'Codice TNS': ['codice tns', 'cod tns', 'tns code', 'cod_tns', 'codtns'],
        'Padre TNS': ['padre tns', 'parent tns', 'tns parent', 'padre_tns', 'padretns'],
    }

    mapping = {}
    df_cols_lower = {col.lower(): col for col in df.columns}

    for sys_col, aliases in REQUIRED.items():
        # Exact match (case-insensitive)
        sys_col_lower = sys_col.lower()
        if sys_col_lower in df_cols_lower:
            mapping[sys_col] = df_cols_lower[sys_col_lower]
            continue

        # Fuzzy match via aliases
        for alias in aliases:
            matches = [c for c in df.columns if alias in c.lower()]
            if matches:
                mapping[sys_col] = matches[0]
                break

    # Calculate match percentage (only required columns)
    required_cols = ['ID', 'TxCodFiscale', 'Titolare', 'Unità Organizzativa']
    matched_required = sum(1 for col in required_cols if col in mapping)
    match_pct = (matched_required / len(required_cols)) * 100

    return mapping, match_pct


def should_simplify_config_step(df: pd.DataFrame, mapping: Dict[str, str]) -> bool:
    """
    Check if Step 3 should use simplified UI.

    Simplified if:
    - No vacant positions (all rows have Titolare)
    - No TNS role columns

    Args:
        df: DataFrame with data
        mapping: Column mapping

    Returns:
        True if should simplify
    """
    titolare_col = mapping.get('Titolare')
    id_col = mapping.get('ID')

    if not titolare_col or not id_col:
        return False

    # Check vacant positions (rows with ID but no Titolare)
    vacant_count = df[df[titolare_col].isna() & df[id_col].notna()].shape[0]

    # Check TNS columns
    tns_columns = ['Viaggiatore', 'Approvatore', 'Controllore', 'Responsabile SGSL']
    has_tns = any(col in df.columns for col in tns_columns)

    return vacant_count == 0 and not has_tns


def save_column_mapping(mapping: Dict[str, str], config_dir: Path = None):
    """Save column mapping to JSON for future use"""
    if config_dir is None:
        config_dir = Path(__file__).parent.parent / 'config'

    config_dir.mkdir(exist_ok=True)
    mapping_file = config_dir / 'column_mapping.json'

    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)


def load_column_mapping(config_dir: Path = None) -> Dict[str, str]:
    """Load saved column mapping"""
    if config_dir is None:
        config_dir = Path(__file__).parent.parent / 'config'

    mapping_file = config_dir / 'column_mapping.json'

    if mapping_file.exists():
        with open(mapping_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    return {}


# ═══════════════════════════════════════════════════════════
# STEP RENDERERS
# ═══════════════════════════════════════════════════════════

def render_step_1_upload(wizard):
    """Step 1: Upload File"""
    st.markdown("### 📁 Carica File DB_ORG")
    st.markdown("Seleziona il file Excel contenente i dati da importare.")

    uploaded_file = st.file_uploader(
        "Scegli un file",
        type=['xls', 'xlsx', 'xlsm'],
        key="wizard_file_uploader",
        help="File Excel con foglio 'DB_ORG'"
    )

    if uploaded_file:
        # Show file info
        file_size = uploaded_file.size / 1024  # KB
        st.success(f"✅ File caricato: **{uploaded_file.name}** ({file_size:.1f} KB)")

        try:
            # Read Excel file
            df = pd.read_excel(uploaded_file, sheet_name='DB_ORG')
            wizard.set_data('uploaded_file', uploaded_file)
            wizard.set_data('file_df', df)
            wizard.set_data('filename', uploaded_file.name)

            # Show preview
            st.info(f"📊 Righe: {len(df):,} | Colonne: {len(df.columns)}")

            with st.expander("🔍 Anteprima dati (prime 5 righe)"):
                st.dataframe(df.head(), use_container_width=True)

            # Auto-detect column mapping
            mapping, match_pct = auto_detect_columns(df)
            wizard.set_data('column_mapping', mapping)
            wizard.set_data('mapping_auto_detected', match_pct >= 100)
            wizard.set_data('mapping_match_pct', match_pct)

            # Show auto-detect results
            if match_pct >= 100:
                st.success(f"✅ **Mappatura automatica completata al {match_pct:.0f}%**")
                st.info("ℹ️ Verifica le associazioni allo Step 2 prima di procedere")
                wizard.set_skip(step=2, skip=False)  # Never skip - always show for verification
            elif match_pct >= 75:
                st.warning(f"⚠️ Mappatura automatica parziale ({match_pct:.0f}%). Verifica richiesta allo Step 2.")
                wizard.set_skip(step=2, skip=False)
            else:
                st.error(f"❌ Mappatura automatica insufficiente ({match_pct:.0f}%). Configurazione manuale richiesta.")
                wizard.set_skip(step=2, skip=False)

        except Exception as e:
            st.error(f"❌ Errore lettura file: {str(e)}")
            return

    # Navigation
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("✕ Annulla", key="step1_cancel"):
            wizard.deactivate()
            st.rerun()

    with col3:
        disabled = uploaded_file is None
        if st.button("Avanti →", key="step1_next", disabled=disabled, type="primary"):
            wizard.next_step()
            st.rerun()


def column_index_to_letter(index):
    """Convert 0-based column index to Excel letter (A, B, ..., Z, AA, AB, ...)"""
    letter = ''
    while index >= 0:
        letter = chr(index % 26 + 65) + letter
        index = index // 26 - 1
    return letter


def render_step_2_mapping(wizard):
    """Step 2: Column Mapping (conditional)"""
    st.markdown("### 🔗 Mappatura Colonne")
    st.markdown("Collega le colonne del file Excel ai campi del sistema.")

    df = wizard.get_data('file_df')
    mapping = wizard.get_data('column_mapping', {})

    if df is None:
        st.error("❌ Dati file non trovati. Torna allo Step 1.")
        return

    # Define required and optional columns
    REQUIRED_COLS = {
        'ID': 'Identificativo univoco posizione',
        'TxCodFiscale': 'Codice Fiscale dipendente',
        'Titolare': 'Nome dipendente/titolare',
        'Unità Organizzativa': 'Unità organizzativa livello 1'
    }

    OPTIONAL_COLS = {
        'Unità Organizzativa 2': 'Unità organizzativa livello 2',
        'ReportsTo': 'Parent posizione ORG (colonna AC)',
        'Matricola': 'Matricola dipendente',
        'Email': 'Email aziendale'
    }

    # Hierarchy columns for organigrammi
    HIERARCHY_COLS = {
        'CF Responsabile Diretto': '👤 CF del responsabile diretto (col. BF) - per Organigramma HR',
        'Codice TNS': '🔢 Codice TNS dipendente (col. CB) - per Organigramma TNS',
        'Padre TNS': '👆 Codice TNS del parent (col. CC) - per Organigramma TNS'
    }

    # Create dropdown options with format "LETTER - Column Name"
    # Keep a mapping of display text -> actual column name
    display_to_col = {'': ''}
    col_to_display = {'': ''}

    for idx, col_name in enumerate(df.columns):
        letter = column_index_to_letter(idx)
        display_text = f"{letter} - {col_name}"
        display_to_col[display_text] = col_name
        col_to_display[col_name] = display_text

    excel_columns_display = [''] + [col_to_display[col] for col in df.columns]

    st.markdown("#### 🔴 Colonne Obbligatorie")

    # Required columns mapping
    for sys_col, description in REQUIRED_COLS.items():
        col1, col2, col3 = st.columns([2, 3, 4])

        with col1:
            st.markdown(f"**{sys_col}**")

        with col2:
            st.caption(description)

        with col3:
            # Get current mapped column and convert to display format
            current_col = mapping.get(sys_col, '')
            current_display = col_to_display.get(current_col, '')

            selected_display = st.selectbox(
                f"Colonna Excel per {sys_col}",
                options=excel_columns_display,
                index=excel_columns_display.index(current_display) if current_display in excel_columns_display else 0,
                key=f"map_req_{sys_col}",
                label_visibility="collapsed"
            )

            # Convert back from display to actual column name
            if selected_display:
                mapping[sys_col] = display_to_col[selected_display]
            else:
                mapping[sys_col] = ''

    st.markdown("#### ⚪ Colonne Opzionali")

    for sys_col, description in OPTIONAL_COLS.items():
        col1, col2, col3 = st.columns([2, 3, 4])

        with col1:
            st.markdown(f"**{sys_col}**")

        with col2:
            st.caption(description)

        with col3:
            # Get current mapped column and convert to display format
            current_col = mapping.get(sys_col, '')
            current_display = col_to_display.get(current_col, '')

            selected_display = st.selectbox(
                f"Colonna Excel per {sys_col}",
                options=excel_columns_display,
                index=excel_columns_display.index(current_display) if current_display in excel_columns_display else 0,
                key=f"map_opt_{sys_col}",
                label_visibility="collapsed"
            )

            # Convert back from display to actual column name
            if selected_display:
                mapping[sys_col] = display_to_col[selected_display]
            else:
                mapping[sys_col] = ''

    st.markdown("#### 🌳 Colonne Gerarchie Organigrammi (Opzionali)")
    st.info("📌 **Suggerimento**: Queste colonne servono per costruire i 3 organigrammi (HR, ORG, TNS). Puoi saltarle se non hai questi dati.")

    for sys_col, description in HIERARCHY_COLS.items():
        col1, col2, col3 = st.columns([2, 4, 3])

        with col1:
            st.markdown(f"**{sys_col}**")

        with col2:
            st.caption(description)

        with col3:
            # Get current mapped column and convert to display format
            current_col = mapping.get(sys_col, '')
            current_display = col_to_display.get(current_col, '')

            selected_display = st.selectbox(
                f"Colonna Excel per {sys_col}",
                options=excel_columns_display,
                index=excel_columns_display.index(current_display) if current_display in excel_columns_display else 0,
                key=f"map_hier_{sys_col}",
                label_visibility="collapsed"
            )

            # Convert back from display to actual column name
            if selected_display:
                mapping[sys_col] = display_to_col[selected_display]
            else:
                mapping[sys_col] = ''

    # Update mapping in wizard
    wizard.set_data('column_mapping', mapping)

    # Validation
    st.markdown("---")
    missing_required = [col for col in REQUIRED_COLS.keys() if not mapping.get(col)]

    if missing_required:
        st.error(f"❌ Colonne obbligatorie mancanti: {', '.join(missing_required)}")

    # Action buttons
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("💾 Salva Mappatura", key="step2_save"):
            save_column_mapping(mapping)
            st.success("✅ Mappatura salvata!")
            time.sleep(0.5)
            st.rerun()

    # Navigation
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("← Indietro", key="step2_back"):
            wizard.prev_step()
            st.rerun()

    with col2:
        if st.button("✕ Annulla", key="step2_cancel"):
            wizard.deactivate()
            st.rerun()

    with col3:
        disabled = len(missing_required) > 0
        if st.button("Avanti →", key="step2_next", disabled=disabled, type="primary"):
            wizard.next_step()
            st.rerun()


def render_step_3_config(wizard):
    """Step 3: Import Configuration (smart UI)"""
    st.markdown("### ⚙️ Configurazione Import")

    df = wizard.get_data('file_df')
    mapping = wizard.get_data('column_mapping', {})

    if df is None:
        st.error("❌ Dati file non trovati.")
        return

    # Determine if should simplify UI
    simplified = should_simplify_config_step(df, mapping)

    # Count entities
    id_col = mapping.get('ID')
    titolare_col = mapping.get('Titolare')

    total_rows = len(df)
    employees = df[df[titolare_col].notna()].shape[0] if titolare_col else 0
    vacant = df[df[titolare_col].isna() & df[id_col].notna()].shape[0] if titolare_col and id_col else 0

    # Check TNS columns
    tns_columns = ['Viaggiatore', 'Approvatore', 'Controllore', 'Responsabile SGSL']
    has_tns = any(col in df.columns for col in tns_columns)

    if simplified:
        # SIMPLIFIED UI
        st.info(f"📊 File contiene: **{employees:,} dipendenti**")

        st.success("✅ **Configurazione automatica applicata**")
        st.markdown("""
        - **Tipo import**: Solo Dipendenti
        - **Ruoli TNS**: Non rilevati
        """)

        # Set default config
        wizard.set_data('import_type', 'employees_only')
        wizard.set_data('import_tns', False)

    else:
        # STANDARD UI
        st.info(f"📊 **Statistiche file**: {total_rows:,} righe totali | {employees:,} dipendenti | {vacant:,} posizioni vacanti")

        if has_tns:
            st.info("🎭 **Colonne ruoli TNS** rilevate nel file")

        st.markdown("#### Tipo di Import")

        import_type = st.radio(
            "Seleziona cosa importare",
            options=['all', 'positions_only', 'employees_only'],
            format_func=lambda x: {
                'all': '📦 Tutti i dati (Dipendenti + Posizioni Organizzative)',
                'positions_only': '🏢 Solo Posizioni Organizzative (senza titolare)',
                'employees_only': '👥 Solo Dipendenti (con titolare)'
            }[x],
            index=0,
            key="import_type_radio"
        )

        wizard.set_data('import_type', import_type)

        # TNS import option
        if has_tns:
            import_tns = st.checkbox(
                "✓ Importa Ruoli TNS (Approvatore, Viaggiatore, etc.)",
                value=True,
                key="import_tns_checkbox"
            )
            wizard.set_data('import_tns', import_tns)
        else:
            wizard.set_data('import_tns', False)

    # Optional note
    st.markdown("#### Nota (opzionale)")
    user_note = st.text_area(
        "Aggiungi una nota descrittiva per questo import",
        placeholder="es. Import mensile gennaio 2026",
        key="import_note_textarea",
        height=80
    )

    wizard.set_data('user_note', user_note)

    # Navigation
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("← Indietro", key="step3_back"):
            wizard.prev_step()
            st.rerun()

    with col2:
        if st.button("✕ Annulla", key="step3_cancel"):
            wizard.deactivate()
            st.rerun()

    with col3:
        if st.button("Avanti →", key="step3_next", type="primary"):
            wizard.next_step()
            st.rerun()


def render_step_4_execution(wizard):
    """Step 4: Confirmation & Execution"""
    st.markdown("### 🚀 Conferma ed Esecuzione")

    df = wizard.get_data('file_df')
    mapping = wizard.get_data('column_mapping', {})
    filename = wizard.get_data('filename', 'file.xlsx')
    import_type = wizard.get_data('import_type', 'all')
    import_tns = wizard.get_data('import_tns', False)
    user_note = wizard.get_data('user_note', '')

    # Count entities
    titolare_col = mapping.get('Titolare')
    id_col = mapping.get('ID')

    employees = df[df[titolare_col].notna()].shape[0] if titolare_col else 0
    vacant = df[df[titolare_col].isna() & df[id_col].notna()].shape[0] if titolare_col and id_col else 0

    # Summary card
    st.markdown("#### 📋 RIEPILOGO IMPORT")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
        **File**: {filename}
        **Formato**: DB_ORG
        **Righe totali**: {len(df):,}
        """)

    with col2:
        st.markdown(f"""
        **Dipendenti**: {employees:,}
        **Posizioni org.**: {vacant:,}
        **Colonne mappate**: {len([v for v in mapping.values() if v])}/{len(mapping)}
        """)

    st.markdown(f"""
    **Tipo Import**: {
        '📦 Tutti i dati' if import_type == 'all'
        else '🏢 Solo Posizioni' if import_type == 'positions_only'
        else '👥 Solo Dipendenti'
    }
    **Ruoli TNS**: {'✓ Inclusi' if import_tns else '✗ Esclusi'}
    """)

    if user_note:
        st.markdown(f"**Nota**: {user_note}")

    # Execution
    st.markdown("---")

    if not wizard.get_data('import_executed', False):
        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            if st.button("← Indietro", key="step4_back"):
                wizard.prev_step()
                st.rerun()

        with col2:
            if st.button("✕ Annulla", key="step4_cancel"):
                wizard.deactivate()
                st.rerun()

        with col3:
            if st.button("🚀 Avvia Import", key="step4_execute", type="primary"):
                # Execute import
                execute_import(wizard)
                st.rerun()
    else:
        # Already executed, show option to proceed
        st.success("✅ Import già eseguito!")
        if st.button("Avanti ai Risultati →", key="step4_results", type="primary"):
            wizard.next_step()
            st.rerun()


def execute_import(wizard):
    """Execute the import process"""
    df = wizard.get_data('file_df')
    mapping = wizard.get_data('column_mapping', {})
    user_note = wizard.get_data('user_note', '')

    # Prepare renamed DataFrame
    rename_dict = {excel_col: sys_col for sys_col, excel_col in mapping.items() if excel_col}
    df_renamed = df.rename(columns=rename_dict)

    # DEBUG: Show mapping info
    st.info(f"🔍 DEBUG - Colonne mappate: {len(rename_dict)}")
    if 'CF Responsabile Diretto' in df_renamed.columns:
        non_null = df_renamed['CF Responsabile Diretto'].notna().sum()
        st.success(f"✅ Colonna 'CF Responsabile Diretto' trovata con {non_null} valori non-NULL")
    else:
        st.warning(f"⚠️ Colonna 'CF Responsabile Diretto' NON trovata! Colonne presenti: {list(df_renamed.columns[:10])}")

    # Create temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx', mode='wb') as tmp:
        df_renamed.to_excel(tmp.name, sheet_name='DB_ORG', index=False)
        tmp_path = Path(tmp.name)

    try:
        with st.spinner("⏳ Import in corso... Attendere..."):
            # REAL IMPORT using db_org_import_service
            from services.db_org_import_service import DBOrgImportService
            import config

            service = DBOrgImportService(config.DB_PATH)
            results = service.import_db_org_file(tmp_path, 'DB_ORG', user_note)

            if results['success']:
                wizard.set_data('import_results', results)
                wizard.set_data('import_executed', True)
                st.success("✅ Import completato con successo!")

                # Reload data to session state
                st.session_state.data_loaded = False  # Force reload
                st.rerun()
            else:
                st.error(f"❌ Import fallito: {results.get('message', 'Errore sconosciuto')}")
                if results.get('errors'):
                    for error in results['errors'][:5]:
                        st.error(f"  • {error}")
                wizard.set_data('import_results', results)
                wizard.set_data('import_executed', False)

    except Exception as e:
        st.error(f"❌ Errore durante l'import: {str(e)}")
        wizard.set_data('import_results', {'success': False, 'error': str(e)})

    finally:
        # Cleanup temp file
        if tmp_path.exists():
            tmp_path.unlink()


def render_step_5_results(wizard):
    """Step 5: Results & Transition"""
    st.markdown("### ✅ Import Completato!")

    results = wizard.get_data('import_results')

    if not results or not results.get('success'):
        st.error("❌ Import non completato o fallito.")
        if st.button("← Torna Indietro", key="step5_back_error"):
            wizard.goto_step(4)
            st.rerun()
        return

    # Show success with balloons
    st.balloons()

    st.success("🎉 **IMPORT COMPLETATO CON SUCCESSO!**")

    # Statistics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("👥 Dipendenti", f"{results['employees_imported']:,}")

    with col2:
        st.metric("🏢 Strutture", f"{results.get('org_units_imported', 0):,}")

    with col3:
        st.metric("🌳 Gerarchie", f"{results.get('hierarchies_assigned', 0):,}")

    with col4:
        st.metric("🎭 Ruoli", f"{results.get('roles_assigned', 0):,}")

    # Show success message if available
    if results.get('message'):
        st.success(f"✅ {results['message']}")

    st.markdown("---")

    # Action buttons
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🏠 Vai a Dashboard", key="step5_dashboard", type="primary", use_container_width=True):
            wizard.deactivate()
            st.session_state.data_loaded = True
            st.session_state.current_page = "Dashboard DB_ORG"
            st.rerun()

    with col2:
        if st.button("⚙️ Configura Impostazioni", key="step5_settings", use_container_width=True):
            from ui.wizard_state_manager import get_settings_wizard
            wizard.deactivate()
            settings_wizard = get_settings_wizard()
            settings_wizard.activate()
            st.rerun()


# ═══════════════════════════════════════════════════════════
# MAIN MODAL RENDERER WITH @st.dialog
# ═══════════════════════════════════════════════════════════

@st.dialog("🧙‍♂️ Import Wizard DB_ORG", width="large")
def render_wizard_import_dialog():
    """Main dialog renderer for import wizard using Streamlit native dialog"""
    wizard = get_import_wizard()

    # Progress indicator
    current = wizard.current_step
    total = wizard.total_steps

    # Progress bar using columns
    st.caption(f"Step {current}/{total}")
    progress_cols = st.columns(total)
    for i in range(total):
        with progress_cols[i]:
            step_num = i + 1
            if wizard.is_step_skipped(step_num):
                continue
            elif step_num < current:
                st.markdown("🟢", help="Completato")
            elif step_num == current:
                st.markdown("🔵", help="Corrente")
            else:
                st.markdown("⚪", help="Da completare")

    st.markdown("---")

    # Render current step
    if current == 1:
        render_step_1_upload(wizard)
    elif current == 2:
        render_step_2_mapping(wizard)
    elif current == 3:
        render_step_3_config(wizard)
    elif current == 4:
        render_step_4_execution(wizard)
    elif current == 5:
        render_step_5_results(wizard)


def render_wizard_import_modal():
    """Main entry point for import wizard modal"""
    wizard = get_import_wizard()

    if wizard.is_active:
        render_wizard_import_dialog()
