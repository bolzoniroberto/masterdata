"""
Wizard per import merge/arricchimento differenziale.

Supporta 4 use cases:
1. Salary Review - Aggiorna solo RAL post salary review
2. TNS Reorganization - Modifica strutture TNS coinvolte in reorg
3. Cessati/Assunti Detection - Rileva gap/nuovi con alert critici
4. Banding/Grading - Arricchisce con nuove colonne

Wizard flow (6 steps):
1. Upload file & auto-detection tipo import
2. Import type selection & matching key
3. Column mapping (riusa fuzzy matching esistente)
4. Gap analysis & matching preview
5. Merge preview with conflict resolution
6. Confirmation & apply
"""

import streamlit as st
import pandas as pd
import json
from typing import Dict, Optional, List, Any
from datetime import datetime

from models.merge_models import ImportType, MergeStrategy
from services.merge_engine import MergeEngine
from services.database import DatabaseHandler


# ==================== MAIN WIZARD ====================

@st.dialog("🔄 Import Arricchimento/Merge", width="large")
def show_merge_wizard():
    """
    Main wizard entry point.

    Gestisce wizard state e routing tra steps.
    """
    # Initialize wizard state
    if 'merge_state' not in st.session_state:
        st.session_state.merge_state = {
            'step': 1,
            'file_df': None,
            'import_type': None,
            'key_column': None,
            'column_mapping': {},
            'match_result': None,
            'gap_analysis': None,
            'merge_preview': None,
            'file_name': None
        }

    state = st.session_state.merge_state

    # Progress indicator
    _show_progress_indicator(state['step'])

    # Route to appropriate step
    if state['step'] == 1:
        _step_1_upload_file(state)
    elif state['step'] == 2:
        _step_2_import_type_selection(state)
    elif state['step'] == 3:
        _step_3_column_mapping(state)
    elif state['step'] == 4:
        _step_4_gap_analysis(state)
    elif state['step'] == 5:
        _step_5_merge_preview(state)
    elif state['step'] == 6:
        _step_6_confirmation_apply(state)


def _show_progress_indicator(current_step: int):
    """Mostra indicatore progress wizard."""
    steps = [
        "📂 Upload",
        "📋 Tipo",
        "🗂️ Mapping",
        "🔍 Gap",
        "📊 Preview",
        "✅ Conferma"
    ]

    cols = st.columns(6)
    for idx, (col, step_name) in enumerate(zip(cols, steps), 1):
        with col:
            if idx < current_step:
                st.success(f"✓ {step_name}")
            elif idx == current_step:
                st.info(f"**→ {step_name}**")
            else:
                st.write(step_name)


# ==================== STEP 1: UPLOAD FILE ====================

def _step_1_upload_file(state: Dict[str, Any]):
    """
    Step 1: Upload file Excel & auto-detection tipo import.

    Auto-rileva tipo import basandosi su colonne presenti nel file.
    """
    st.markdown("### Step 1: Carica File Excel")

    st.info("""
        📥 **Carica file Excel con dati parziali da mergiare**

        Il wizard supporta:
        - Salary Review (solo dipendenti con aumenti RAL)
        - TNS Reorganization (solo strutture modificate)
        - Cessati/Assunti Detection (file completo da sistema esterno)
        - Banding/Grading (arricchimento con nuove colonne)
    """)

    uploaded_file = st.file_uploader(
        "📂 Seleziona file Excel",
        type=['xlsx', 'xls'],
        help="File con dati parziali da mergiare con database",
        key="merge_file_uploader"
    )

    if uploaded_file:
        try:
            # Load file
            with st.spinner("📖 Caricamento file..."):
                df = pd.read_excel(uploaded_file)

            state['file_df'] = df
            state['file_name'] = uploaded_file.name

            # Auto-detection tipo import
            detected_type = _detect_import_type(df)

            # Display info
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                st.success(f"✅ **{len(df)}** righe caricate")

            with col2:
                st.info(f"🔍 Tipo rilevato: **{detected_type}**")

            with col3:
                st.metric("Colonne", len(df.columns))

            # Preview dati
            with st.expander("📋 Preview Dati", expanded=True):
                st.dataframe(df.head(10), use_container_width=True)

            # Next button
            st.markdown("---")
            if st.button("➡️ Avanti: Conferma Tipo Import", type="primary", use_container_width=True):
                state['step'] = 2
                st.rerun()

        except Exception as e:
            st.error(f"❌ Errore caricamento file: {e}")


def _detect_import_type(df: pd.DataFrame) -> str:
    """
    Auto-rileva tipo import basandosi su colonne presenti.

    Logic:
    - Ha colonne salary (ral, monthly_gross)? → salary_review
    - Ha cod_tns, padre_tns? → tns_reorg
    - Ha solo CF + pochi campi? → banding (enrichment)
    - Default: custom

    Args:
        df: DataFrame caricato

    Returns:
        ImportType.value
    """
    cols = set(df.columns.str.lower())

    # Salary review detection
    if {'ral', 'monthly_gross'}.intersection(cols) or \
       {'ral', 'retribuzione'}.intersection(cols):
        return ImportType.SALARY_REVIEW.value

    # TNS reorg detection
    if {'cod_tns', 'padre_tns'}.intersection(cols) or \
       {'codice_tns', 'padre'}.intersection(cols):
        return ImportType.TNS_REORG.value

    # Banding detection (poche colonne + CF)
    if len(cols) < 10 and any(c in cols for c in ['codice_fiscale', 'cf', 'tx_cod_fiscale']):
        return ImportType.BANDING.value

    # Cessati/Assunti detection (molte colonne, probabile full export)
    if len(cols) > 15 and any(c in cols for c in ['codice_fiscale', 'cf', 'tx_cod_fiscale']):
        return ImportType.CESSATI_ASSUNTI.value

    return ImportType.CUSTOM.value


# ==================== STEP 2: IMPORT TYPE SELECTION ====================

def _step_2_import_type_selection(state: Dict[str, Any]):
    """
    Step 2: Selezione tipo import & chiave matching.

    User può confermare auto-detection o cambiare tipo.
    Seleziona chiave matching (CF, cod_tns, position_id).
    """
    st.markdown("### Step 2: Tipo Import e Chiave Matching")

    df = state['file_df']
    detected_type = _detect_import_type(df)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📋 Tipo Import")
        import_type = st.selectbox(
            "Tipo Import",
            options=[e.value for e in ImportType],
            index=[e.value for e in ImportType].index(detected_type),
            help="Tipo import determina le strategie di merge",
            label_visibility="collapsed",
            key="import_type_select"
        )

    with col2:
        st.markdown("#### 🔑 Chiave Matching")

        # Default key column basato su tipo
        default_keys = {
            ImportType.SALARY_REVIEW.value: _find_column_fuzzy(df.columns, ['tx_cod_fiscale', 'codice_fiscale', 'cf']),
            ImportType.TNS_REORG.value: _find_column_fuzzy(df.columns, ['cod_tns', 'codice_tns']),
            ImportType.BANDING.value: _find_column_fuzzy(df.columns, ['tx_cod_fiscale', 'codice_fiscale', 'cf']),
            ImportType.CESSATI_ASSUNTI.value: _find_column_fuzzy(df.columns, ['tx_cod_fiscale', 'codice_fiscale', 'cf'])
        }

        default_key = default_keys.get(import_type, df.columns[0])

        try:
            default_index = df.columns.tolist().index(default_key) if default_key in df.columns else 0
        except:
            default_index = 0

        key_column = st.selectbox(
            "Colonna chiave per matching",
            options=df.columns.tolist(),
            index=default_index,
            help="Colonna usata per match file-DB (deve essere univoca)",
            label_visibility="collapsed",
            key="key_column_select"
        )

    # Info tipo import
    st.markdown("---")
    st.markdown("#### ℹ️ Info Tipo Import")
    st.info(_get_import_type_info(import_type))

    # Validation warning
    if key_column:
        # Check uniqueness
        duplicates = df[key_column].duplicated().sum()
        if duplicates > 0:
            st.warning(f"⚠️ Attenzione: {duplicates} valori duplicati nella chiave '{key_column}'")

    # Navigation
    st.markdown("---")
    col_back, col_next = st.columns([1, 2])

    with col_back:
        if st.button("⬅️ Indietro", use_container_width=True):
            state['step'] = 1
            st.rerun()

    with col_next:
        if st.button("➡️ Avanti: Mapping Colonne", type="primary", use_container_width=True):
            state['import_type'] = import_type
            state['key_column'] = key_column
            state['step'] = 3
            st.rerun()


def _find_column_fuzzy(columns: pd.Index, candidates: List[str]) -> Optional[str]:
    """
    Trova colonna da lista candidates con fuzzy matching.

    Args:
        columns: Colonne disponibili nel DataFrame
        candidates: Lista nomi candidati

    Returns:
        Nome colonna trovata o None
    """
    cols_lower = {c.lower(): c for c in columns}

    for candidate in candidates:
        candidate_lower = candidate.lower()
        if candidate_lower in cols_lower:
            return cols_lower[candidate_lower]

        # Fuzzy: check se candidate è substring
        for col_lower, col_original in cols_lower.items():
            if candidate_lower in col_lower or col_lower in candidate_lower:
                return col_original

    return None


def _get_import_type_info(import_type: str) -> str:
    """Descrizione strategia merge per tipo import."""
    info = {
        ImportType.SALARY_REVIEW.value: """
            **Salary Review**: Aggiorna solo campi retributivi.
            - **Strategia**: OVERWRITE su ral, monthly_gross, componenti salary
            - **Campi anagrafici**: KEEP_TARGET (mantiene DB, ignora file)
            - **Gap**: Record DB non nel file = dipendenti senza variazione RAL (normale)
        """,
        ImportType.TNS_REORG.value: """
            **TNS Reorganization**: Aggiorna struttura gerarchica TNS.
            - **Strategia**: OVERWRITE su cod_tns, padre_tns, responsabile_tns, approvatore_tns
            - **Altri campi**: KEEP_TARGET (mantiene DB)
            - **Gap**: Strutture TNS non nel file = strutture non coinvolte in reorg
        """,
        ImportType.BANDING.value: """
            **Banding/Enrichment**: Arricchisci con nuove colonne.
            - **Strategia**: FILL_EMPTY (aggiorna solo se campo DB vuoto)
            - **Comportamento**: Non sovrascrive dati esistenti
            - **Gap**: Record DB non nel file = da completare manualmente in futuro
        """,
        ImportType.CESSATI_ASSUNTI.value: """
            **Cessati/Assunti Detection**: Rileva variazioni organico.
            - **Gap analysis**: DB non nel file = **potenziali cessati**
            - **New records**: File non in DB = **potenziali assunti**
            - **Alert**: Avviso automatico se gap include manager o approvatori critici
        """,
        ImportType.CUSTOM.value: """
            **Import Personalizzato**: Configurazione manuale strategie.
            - **Strategia**: ASK_USER (richiede risoluzione manuale conflitti)
            - **Flessibilità**: Massima libertà, minima automazione
        """
    }

    return info.get(import_type, "Tipo import non riconosciuto")


# ==================== STEP 3: COLUMN MAPPING ====================

def _step_3_column_mapping(state: Dict[str, Any]):
    """
    Step 3: Mapping colonne file → schema DB.

    Riutilizza fuzzy matching dal wizard import esistente.
    """
    st.markdown("### Step 3: Mapping Colonne")

    df = state['file_df']
    import_type = state['import_type']

    st.info(f"""
        📝 **Mappa colonne del file alle colonne database**

        Tipo import: **{import_type}**
        File: **{state.get('file_name', 'unknown.xlsx')}**
    """)

    # Get target schema basato su import type
    target_schema = _get_target_schema(import_type)

    # Auto-mapping (fuzzy)
    if 'column_mapping' not in state or not state['column_mapping']:
        state['column_mapping'] = _fuzzy_match_columns(
            file_columns=df.columns.tolist(),
            target_schema=target_schema
        )

    # Show mapping UI
    mapping = state['column_mapping']

    st.markdown("#### 🗂️ Mappatura Colonne")
    st.markdown("*Verifica o modifica il mapping automatico*")

    # Editable table
    mapping_data = []
    for file_col, db_col in mapping.items():
        mapping_data.append({
            'Colonna File': file_col,
            'Colonna DB': db_col,
            'Match': '✓' if db_col else '✗'
        })

    mapping_df = pd.DataFrame(mapping_data)

    # Show unmapped columns
    unmapped = [c for c in df.columns if c not in mapping]
    if unmapped:
        st.warning(f"⚠️ {len(unmapped)} colonne non mappate: {', '.join(unmapped[:5])}")

    st.dataframe(mapping_df, use_container_width=True, hide_index=True)

    # Allow manual override
    with st.expander("🔧 Override Manuale Mapping"):
        st.markdown("*Per modifiche avanzate*")

        col_file = st.selectbox(
            "Colonna File",
            options=df.columns.tolist(),
            key="manual_file_col"
        )

        col_db = st.selectbox(
            "Colonna DB Target",
            options=[""] + list(target_schema.keys()),
            key="manual_db_col"
        )

        if st.button("Applica Override"):
            if col_db:
                state['column_mapping'][col_file] = col_db
                st.success(f"✅ Mapping aggiornato: {col_file} → {col_db}")
                st.rerun()
            else:
                if col_file in state['column_mapping']:
                    del state['column_mapping'][col_file]
                    st.success(f"✅ Rimosso mapping per: {col_file}")
                    st.rerun()

    # Navigation
    st.markdown("---")
    col_back, col_next = st.columns([1, 2])

    with col_back:
        if st.button("⬅️ Indietro", use_container_width=True, key="back_step3"):
            state['step'] = 2
            st.rerun()

    with col_next:
        if st.button("➡️ Avanti: Gap Analysis", type="primary", use_container_width=True, key="next_step3"):
            state['step'] = 4
            st.rerun()


def _get_target_schema(import_type: str) -> Dict[str, str]:
    """
    Return target schema (colonne DB) per tipo import.

    Returns:
        Dict[db_column_name, description]
    """
    # Schema base dipendenti
    schema_personale = {
        'tx_cod_fiscale': 'Codice Fiscale (chiave)',
        'titolare': 'Nome completo',
        'codice': 'Codice dipendente',
        'reports_to_cf': 'CF Responsabile Diretto',
        'area': 'Area aziendale',
        'sede': 'Sede lavoro',
        'qualifica': 'Qualifica',
        'societa': 'Società',
        'email': 'Email aziendale',
        'matricola': 'Matricola',
        'data_assunzione': 'Data assunzione',
        'contratto': 'Tipo contratto'
    }

    # Schema salary
    schema_salary = {
        'tx_cod_fiscale': 'Codice Fiscale (chiave)',
        'ral': 'RAL annua',
        'monthly_gross': 'Lordo mensile',
        'gross_annual': 'Lordo annuo',
        'base_salary': 'Stipendio base',
        'variable_component': 'Componente variabile'
    }

    # Schema TNS
    schema_tns = {
        'cod_tns': 'Codice TNS (chiave)',
        'padre_tns': 'Codice TNS padre',
        'responsabile_tns_cf': 'CF Responsabile TNS',
        'approvatore_tns_cf': 'CF Approvatore TNS',
        'nome_struttura': 'Nome struttura'
    }

    if import_type == ImportType.SALARY_REVIEW.value:
        return {**schema_personale, **schema_salary}
    elif import_type == ImportType.TNS_REORG.value:
        return schema_tns
    elif import_type == ImportType.CESSATI_ASSUNTI.value:
        return schema_personale
    elif import_type == ImportType.BANDING.value:
        return {
            **schema_personale,
            'job_family': 'Job Family',
            'band': 'Band',
            'grade': 'Grade'
        }
    else:
        return schema_personale


def _fuzzy_match_columns(
    file_columns: List[str],
    target_schema: Dict[str, str]
) -> Dict[str, str]:
    """
    Fuzzy match colonne file → colonne DB.

    Args:
        file_columns: Lista colonne nel file
        target_schema: Schema target DB

    Returns:
        Dict[file_col, db_col]
    """
    from rapidfuzz import fuzz, process

    mapping = {}

    for file_col in file_columns:
        # Exact match
        if file_col.lower() in [k.lower() for k in target_schema.keys()]:
            db_col = [k for k in target_schema.keys() if k.lower() == file_col.lower()][0]
            mapping[file_col] = db_col
            continue

        # Fuzzy match
        match = process.extractOne(
            file_col.lower(),
            [k.lower() for k in target_schema.keys()],
            scorer=fuzz.token_sort_ratio,
            score_cutoff=70
        )

        if match:
            # Find original case
            db_col = [k for k in target_schema.keys() if k.lower() == match[0]][0]
            mapping[file_col] = db_col

    return mapping


# ==================== STEP 4: GAP ANALYSIS ====================

def _step_4_gap_analysis(state: Dict[str, Any]):
    """
    Step 4: Gap Analysis & Matching Preview.

    Esegue matching file-DB e mostra:
    - Matched: record presenti in entrambi
    - New: record solo nel file (da inserire)
    - Gap: record solo in DB (non aggiornati)
    """
    st.markdown("### Step 4: Gap Analysis & Matching")

    # Execute matching se non già fatto
    if not state.get('match_result'):
        with st.spinner("🔍 Matching records in corso..."):
            _execute_matching(state)

    match_result = state['match_result']
    gap_analysis = state['gap_analysis']

    # Display metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "✅ Matched",
            len(match_result.matched_pairs),
            help="Record presenti sia in file che in DB"
        )

    with col2:
        st.metric(
            "🆕 Nuovi",
            len(match_result.unmatched_source),
            help="Record nel file ma non in DB (da inserire)"
        )

    with col3:
        st.metric(
            "⚠️ Gap",
            len(match_result.unmatched_target),
            help="Record in DB ma non nel file (non saranno aggiornati)"
        )

    # Critical gaps alert
    if gap_analysis and gap_analysis.critical_gaps > 0:
        st.error(f"""
            🚨 **{gap_analysis.critical_gaps} gap critici** rilevati!

            Gap su ruoli chiave (manager, approvatori).
            Per import tipo '{state['import_type']}' potrebbe indicare cessazioni di figure critiche.
        """)

        with st.expander("📋 Dettagli Gap Critici", expanded=True):
            critical_gap_records = [
                g for g in gap_analysis.gap_records if g.is_critical
            ]

            critical_df = pd.DataFrame([
                {
                    'ID': g.record_id,
                    'Criticità': g.criticality_reason,
                    **g.record_data
                }
                for g in critical_gap_records
            ])

            st.dataframe(critical_df, use_container_width=True, hide_index=True)

    # Recommendations
    if gap_analysis and gap_analysis.recommendations:
        st.info("💡 **Raccomandazioni:**\n\n" + "\n".join([f"- {r}" for r in gap_analysis.recommendations]))

    # Tabs: Matched / Gap / New
    tab1, tab2, tab3 = st.tabs(["✅ Matched", "⚠️ Gap (DB non in file)", "🆕 Nuovi (File non in DB)"])

    with tab1:
        st.caption(f"**{len(match_result.matched_pairs)} record matched** - Saranno aggiornati secondo strategie merge")

        if match_result.matched_pairs:
            matched_df = pd.DataFrame([
                m.target_data for m in match_result.matched_pairs[:100]  # Limit 100 for performance
            ])
            st.dataframe(matched_df, use_container_width=True, hide_index=True)

            if len(match_result.matched_pairs) > 100:
                st.caption(f"*Mostrati primi 100 di {len(match_result.matched_pairs)}*")

    with tab2:
        st.caption(f"**{len(match_result.unmatched_target)} record in DB ma non nel file** - Non saranno aggiornati")

        if state['import_type'] == ImportType.CESSATI_ASSUNTI.value:
            st.warning("⚠️ Per import tipo 'cessati_assunti', questi record potrebbero essere **cessati**")

        if match_result.unmatched_target:
            gap_df = pd.DataFrame(match_result.unmatched_target[:100])
            st.dataframe(gap_df, use_container_width=True, hide_index=True)

            if len(match_result.unmatched_target) > 100:
                st.caption(f"*Mostrati primi 100 di {len(match_result.unmatched_target)}*")

            # Export button
            if st.button("📥 Esporta Gap CSV", key="export_gap"):
                _export_gap_csv(match_result.unmatched_target, state)

    with tab3:
        st.caption(f"**{len(match_result.unmatched_source)} record nel file ma non in DB** - Da inserire manualmente")

        if state['import_type'] == ImportType.CESSATI_ASSUNTI.value:
            st.info("🆕 Per import tipo 'cessati_assunti', questi record potrebbero essere **assunti**")

        if match_result.unmatched_source:
            new_df = pd.DataFrame(match_result.unmatched_source[:100])
            st.dataframe(new_df, use_container_width=True, hide_index=True)

            if len(match_result.unmatched_source) > 100:
                st.caption(f"*Mostrati primi 100 di {len(match_result.unmatched_source)}*")

    # Navigation
    st.markdown("---")
    col_back, col_next = st.columns([1, 2])

    with col_back:
        if st.button("⬅️ Indietro", use_container_width=True, key="back_step4"):
            state['step'] = 3
            st.rerun()

    with col_next:
        if len(match_result.matched_pairs) > 0:
            if st.button("➡️ Avanti: Merge Preview", type="primary", use_container_width=True, key="next_step4"):
                state['step'] = 5
                st.rerun()
        else:
            st.warning("⚠️ Nessun record matched - impossibile procedere con merge")


def _execute_matching(state: Dict[str, Any]):
    """Esegue matching file-DB."""
    try:
        # Applica column mapping
        file_df = state['file_df']
        mapping = state['column_mapping']

        mapped_df = file_df.rename(columns=mapping)

        # Get DB data
        target_df = _get_target_data_for_import_type(state['import_type'])

        # Execute matching
        merge_engine = MergeEngine()

        match_result = merge_engine.match_records(
            source_df=mapped_df,
            target_df=target_df,
            key_column=state['key_column'],
            import_type=state['import_type']
        )

        state['match_result'] = match_result

        # Gap analysis
        gap_analysis = merge_engine.analyze_gaps(
            match_result=match_result,
            import_type=state['import_type'],
            target_df=target_df
        )

        state['gap_analysis'] = gap_analysis

    except Exception as e:
        st.error(f"❌ Errore durante matching: {e}")
        raise


def _get_target_data_for_import_type(import_type: str) -> pd.DataFrame:
    """Carica dati DB per tipo import."""
    db = DatabaseHandler()

    if import_type in [ImportType.SALARY_REVIEW.value, ImportType.CESSATI_ASSUNTI.value, ImportType.BANDING.value]:
        # Query employees table
        query = "SELECT * FROM employees"
    elif import_type == ImportType.TNS_REORG.value:
        # Query TNS structures
        query = "SELECT * FROM org_units WHERE cod_tns IS NOT NULL"
    else:
        # Default: employees
        query = "SELECT * FROM employees"

    df = pd.read_sql_query(query, db.get_connection())
    return df


def _export_gap_csv(gap_records: List[Dict[str, Any]], state: Dict[str, Any]):
    """Esporta gap records come CSV."""
    gap_df = pd.DataFrame(gap_records)

    csv = gap_df.to_csv(index=False)
    filename = f"gap_{state['import_type']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    st.download_button(
        label="💾 Download CSV Gap",
        data=csv,
        file_name=filename,
        mime="text/csv",
        key="download_gap_csv"
    )


# ==================== STEP 5: MERGE PREVIEW ====================

def _step_5_merge_preview(state: Dict[str, Any]):
    """
    Step 5: Merge Preview con conflict resolution.

    Genera preview before/after e permette risoluzione conflitti.
    """
    st.markdown("### Step 5: Merge Preview & Risoluzione Conflitti")

    # Generate preview se non già fatto
    if not state.get('merge_preview'):
        with st.spinner("🔄 Generando preview merge..."):
            _generate_merge_preview(state)

    merge_preview = state['merge_preview']

    # Stats
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "📝 Record con modifiche",
            merge_preview.records_with_changes
        )

    with col2:
        st.metric(
            "📊 Record totali",
            merge_preview.total_records
        )

    with col3:
        st.metric(
            "⚠️ Conflitti",
            merge_preview.total_conflicts
        )

    if merge_preview.total_conflicts > 0:
        st.warning(f"⚠️ {merge_preview.total_conflicts} conflitti rilevati - richiede risoluzione")

    # Preview modifiche
    st.markdown("#### 🔍 Preview Modifiche")

    # Build preview data
    preview_data = []
    for rec in merge_preview.merge_records:
        if not rec.changed_fields:
            continue

        row = {
            'ID': rec.record_id,
            'Campi Modificati': ', '.join(rec.changed_fields),
            'Conflitti': len(rec.conflicts)
        }

        # Sample before/after per primi 3 campi
        for idx, field in enumerate(rec.changed_fields[:3]):
            row[f'{field}_BEFORE'] = str(rec.before.get(field, ''))[:50]
            row[f'{field}_AFTER'] = str(rec.after.get(field, ''))[:50]

        preview_data.append(row)

    if preview_data:
        preview_df = pd.DataFrame(preview_data)
        st.dataframe(preview_df, use_container_width=True, hide_index=True)

        st.caption(f"*Mostra top {len(preview_data)} record con modifiche*")

    # Conflict resolution UI
    if merge_preview.total_conflicts > 0:
        st.markdown("---")
        st.markdown("#### ⚙️ Risoluzione Conflitti")

        conflicts_by_record = {}
        for rec in merge_preview.merge_records:
            if rec.conflicts:
                conflicts_by_record[rec.record_id] = rec.conflicts

        # Limit to first 10 records with conflicts
        for idx, (record_id, conflicts) in enumerate(list(conflicts_by_record.items())[:10]):
            with st.expander(f"🔧 {record_id} - {len(conflicts)} conflitti"):
                for conflict in conflicts:
                    col1, col2, col3 = st.columns([2, 2, 1])

                    with col1:
                        st.caption(f"**{conflict.field_name}**")
                        st.text(f"DB: {conflict.db_value}")

                    with col2:
                        st.text(f"File: {conflict.file_value}")

                    with col3:
                        resolution = st.radio(
                            "Usa",
                            options=["File", "DB"],
                            index=0 if conflict.suggested_strategy == MergeStrategy.OVERWRITE else 1,
                            key=f"conflict_{record_id}_{conflict.field_name}_{idx}",
                            label_visibility="collapsed",
                            horizontal=True
                        )

                        if resolution == "File":
                            conflict.user_resolution = conflict.file_value
                        else:
                            conflict.user_resolution = conflict.db_value

        if len(conflicts_by_record) > 10:
            st.info(f"ℹ️ Mostrati primi 10 record. Altri {len(conflicts_by_record) - 10} con conflitti da risolvere.")

    # Navigation
    st.markdown("---")
    col_back, col_next = st.columns([1, 2])

    with col_back:
        if st.button("⬅️ Indietro", use_container_width=True, key="back_step5"):
            state['step'] = 4
            st.rerun()

    with col_next:
        if st.button("➡️ Avanti: Conferma & Applica", type="primary", use_container_width=True, key="next_step5"):
            state['step'] = 6
            st.rerun()


def _generate_merge_preview(state: Dict[str, Any]):
    """Genera merge preview."""
    try:
        merge_engine = MergeEngine()

        # Get merge strategies per import type
        strategies = _get_merge_strategies_for_type(state['import_type'])

        merge_preview = merge_engine.preview_merge(
            matched_pairs=state['match_result'].matched_pairs,
            merge_strategy=strategies['default'],
            per_field_strategies=strategies['per_field']
        )

        state['merge_preview'] = merge_preview

    except Exception as e:
        st.error(f"❌ Errore generazione preview: {e}")
        raise


def _get_merge_strategies_for_type(import_type: str) -> Dict[str, Any]:
    """
    Configurazione strategie merge per tipo import.

    Returns:
        {
            'default': MergeStrategy,
            'per_field': Dict[field_name, MergeStrategy]
        }
    """
    if import_type == ImportType.SALARY_REVIEW.value:
        return {
            'default': MergeStrategy.KEEP_TARGET,
            'per_field': {
                'ral': MergeStrategy.OVERWRITE,
                'monthly_gross': MergeStrategy.OVERWRITE,
                'gross_annual': MergeStrategy.OVERWRITE,
                'base_salary': MergeStrategy.OVERWRITE,
                'variable_component': MergeStrategy.OVERWRITE
            }
        }

    elif import_type == ImportType.TNS_REORG.value:
        return {
            'default': MergeStrategy.KEEP_TARGET,
            'per_field': {
                'cod_tns': MergeStrategy.OVERWRITE,
                'padre_tns': MergeStrategy.OVERWRITE,
                'responsabile_tns_cf': MergeStrategy.OVERWRITE,
                'approvatore_tns_cf': MergeStrategy.OVERWRITE
            }
        }

    elif import_type == ImportType.BANDING.value:
        return {
            'default': MergeStrategy.FILL_EMPTY,
            'per_field': {}
        }

    elif import_type == ImportType.CESSATI_ASSUNTI.value:
        return {
            'default': MergeStrategy.OVERWRITE,
            'per_field': {}
        }

    else:  # CUSTOM
        return {
            'default': MergeStrategy.ASK_USER,
            'per_field': {}
        }


# ==================== STEP 6: CONFIRMATION & APPLY ====================

def _step_6_confirmation_apply(state: Dict[str, Any]):
    """
    Step 6: Conferma e applica merge.

    Mostra summary e permette applicazione finale.
    """
    st.markdown("### Step 6: Conferma & Applica Merge")

    merge_preview = state['merge_preview']
    match_result = state['match_result']

    # Summary
    st.info(f"""
        📋 **Riepilogo Import {state['import_type']}**

        - 🔑 Chiave matching: `{state['key_column']}`
        - ✅ Record da aggiornare: **{merge_preview.records_with_changes}**
        - 🆕 Nuovi record: **{len(match_result.unmatched_source)}** *(non gestiti in questo wizard)*
        - ⚠️ Gap (non aggiornati): **{len(match_result.unmatched_target)}**
        - ⚙️ Conflitti risolti: **{merge_preview.total_conflicts}**
    """)

    # Options
    col1, col2 = st.columns(2)

    with col1:
        create_snapshot = st.checkbox(
            "📸 Crea snapshot prima dell'import",
            value=True,
            help="Raccomandato per poter ripristinare in caso di problemi",
            key="create_snapshot_option"
        )

    with col2:
        validate_after = st.checkbox(
            "✅ Valida dati dopo import",
            value=True,
            help="Esegui DataValidator post-merge per verificare integrità",
            key="validate_after_option"
        )

    # Apply button
    st.markdown("---")
    col_cancel, col_apply = st.columns([1, 2])

    with col_cancel:
        if st.button("❌ Annulla", use_container_width=True, key="cancel_wizard"):
            if st.session_state.get('merge_state'):
                del st.session_state.merge_state
            st.rerun()

    with col_apply:
        if st.button("✅ APPLICA MERGE", type="primary", use_container_width=True, key="apply_merge_btn"):
            _apply_merge(state, create_snapshot, validate_after)


def _apply_merge(state: Dict[str, Any], create_snapshot: bool, validate_after: bool):
    """Esegue merge finale."""
    try:
        with st.spinner("🔄 Applicando merge..."):
            # Snapshot
            snapshot_path = None
            if create_snapshot:
                from services.version_manager import VersionManager
                vm = VersionManager()
                snapshot_path = vm.create_snapshot(
                    note=f"Pre-merge {state['import_type']} - {state.get('file_name', 'unknown')}",
                    version_type="merge"
                )
                st.info(f"📸 Snapshot creato: {snapshot_path}")

            # Apply merge
            merge_engine = MergeEngine()

            # Get selected record IDs (tutti per ora)
            selected_ids = [rec.record_id for rec in state['merge_preview'].merge_records]

            result = merge_engine.apply_merge(
                preview=state['merge_preview'],
                selected_record_ids=selected_ids,
                validate=validate_after,
                record_type="personale"  # TODO: dynamic based on import_type
            )

            # Log to audit
            _log_merge_to_audit(state, result, snapshot_path)

            if result.success:
                st.success(f"""
                    ✅ **Merge completato con successo!**

                    - ✅ **{result.applied_count}** record aggiornati
                    - ⏭️ **{result.skipped_count}** record saltati
                    - ❌ **{result.error_count}** errori

                    {f'📸 Snapshot: `{snapshot_path}`' if snapshot_path else ''}
                """)

                # Reset wizard
                if st.button("🏁 Chiudi Wizard"):
                    if 'merge_state' in st.session_state:
                        del st.session_state.merge_state
                    st.rerun()

            else:
                st.error(f"""
                    ❌ **Merge fallito**

                    Errori: {', '.join(result.errors)}
                """)

    except Exception as e:
        st.error(f"❌ Errore durante applicazione merge: {e}")


def _log_merge_to_audit(state: Dict[str, Any], result: Any, snapshot_path: Optional[str]):
    """Log merge to audit_merge_imports table."""
    try:
        db = DatabaseHandler()
        cursor = db.get_connection().cursor()

        match_result = state['match_result']
        merge_preview = state['merge_preview']

        coverage = (
            len(match_result.matched_pairs) /
            (len(match_result.matched_pairs) + len(match_result.unmatched_target)) * 100
            if (len(match_result.matched_pairs) + len(match_result.unmatched_target)) > 0
            else 0
        )

        cursor.execute("""
            INSERT INTO audit_merge_imports (
                import_type, key_column, file_name,
                matched_count, new_count, gap_count,
                applied_count, skipped_count, error_count,
                critical_gaps, coverage_percentage,
                snapshot_path, validation_passed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            state['import_type'],
            state['key_column'],
            state.get('file_name'),
            len(match_result.matched_pairs),
            len(match_result.unmatched_source),
            len(match_result.unmatched_target),
            result.applied_count,
            result.skipped_count,
            result.error_count,
            state['gap_analysis'].critical_gaps if state.get('gap_analysis') else 0,
            coverage,
            snapshot_path,
            result.success
        ))

        db.get_connection().commit()

    except Exception as e:
        st.warning(f"⚠️ Impossibile salvare audit log: {e}")
