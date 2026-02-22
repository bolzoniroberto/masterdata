"""
Onboarding Wizard - Guided setup for first-time users.

Steps:
1. Welcome & Introduction
2. File Upload
3. Preview & Confirmation
4. Auto-trigger Import Wizard (existing)
"""

import streamlit as st
import pandas as pd
import tempfile
from pathlib import Path
from ui.wizard_state_manager import WizardStateManager, get_import_wizard


class OnboardingWizard(WizardStateManager):
    """Onboarding wizard with 4-step flow"""

    def __init__(self):
        super().__init__(wizard_id='onboarding', total_steps=4)


# Singleton instance
_onboarding_wizard = None


def get_onboarding_wizard() -> OnboardingWizard:
    """Get onboarding wizard instance (singleton)"""
    global _onboarding_wizard
    if _onboarding_wizard is None:
        _onboarding_wizard = OnboardingWizard()
    return _onboarding_wizard


@st.dialog("🚀 Configurazione Guidata", width="large")
def render_onboarding_wizard():
    """Render onboarding wizard modal"""
    wizard = get_onboarding_wizard()

    # Render appropriate step
    if wizard.current_step == 1:
        render_step_1_welcome(wizard)
    elif wizard.current_step == 2:
        render_step_2_upload(wizard)
    elif wizard.current_step == 3:
        render_step_3_preview(wizard)
    elif wizard.current_step == 4:
        # Auto-trigger import wizard
        wizard.deactivate()
        get_import_wizard().activate()
        st.rerun()


def render_step_1_welcome(wizard: OnboardingWizard):
    """Step 1: Welcome & Introduction"""

    st.markdown("""
    <div style="text-align: center; padding: 2rem 1rem;">
        <h1>🎉 Benvenuto in HR Management Platform</h1>
        <p style="font-size: 1.1rem; color: var(--c-text-2);">
            Questo wizard ti guiderà nella configurazione iniziale del sistema.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # What we'll do
    st.markdown("### Cosa faremo:")

    col1, col2 = st.columns([1, 3])

    with col1:
        st.markdown("✅")
    with col2:
        st.markdown("**Importare i dati del personale**")

    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown("✅")
    with col2:
        st.markdown("**Configurare le gerarchie organizzative**")

    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown("✅")
    with col2:
        st.markdown("**Impostare le preferenze iniziali**")

    st.markdown("---")

    # Time estimate
    st.info("⏱️ Tempo stimato: ~5 minuti")

    st.markdown("<br>", unsafe_allow_html=True)

    # Navigation buttons
    col1, col2, col3 = st.columns([2, 1, 1])

    with col2:
        if st.button("Salta", use_container_width=True):
            wizard.deactivate()
            st.rerun()

    with col3:
        if st.button("Inizia →", type="primary", use_container_width=True):
            wizard.next_step()
            st.rerun()


def render_step_2_upload(wizard: OnboardingWizard):
    """Step 2: File Upload"""

    # Progress indicator
    st.caption("Passo 2 di 4")
    st.progress(0.5)

    st.markdown("---")

    st.markdown("### 📂 Carica File Dati")

    st.info("""
    Carica un file Excel contenente i dati del personale e delle strutture organizzative.
    Il sistema riconoscerà automaticamente il formato.
    """)

    # File uploader
    uploaded_file = st.file_uploader(
        "Trascina qui il file Excel o clicca per selezionare",
        type=['xls', 'xlsx'],
        help="Formati supportati: DB_ORG (consigliato), TNS (legacy)",
        key="onboarding_file_upload"
    )

    st.markdown("---")

    # Supported formats
    with st.expander("📋 Formati supportati", expanded=False):
        st.markdown("""
        **DB_ORG** (consigliato):
        - Mappatura colonne automatica
        - Validazione avanzata
        - 135+ colonne supportate

        **TNS** (legacy):
        - Fogli separati: "TNS Personale" e "TNS Strutture"
        - Compatibilità con sistema legacy
        """)

    # Template download
    with st.expander("💡 Non hai un file?", expanded=False):
        st.markdown("""
        Puoi scaricare un template di esempio:
        - [Template DB_ORG](placeholder)
        - [Template TNS](placeholder)

        Oppure usa il file di test: `data/input/TNS_HR_Data.xls`
        """)

    st.markdown("---")

    # Store file in wizard data
    if uploaded_file is not None:
        wizard.set_data('uploaded_file', uploaded_file)
        wizard.set_data('file_name', uploaded_file.name)

    # Navigation buttons
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.button("← Indietro", use_container_width=True):
            wizard.prev_step()
            st.rerun()

    with col3:
        # Can only proceed if file uploaded
        if uploaded_file is not None:
            if st.button("Avanti →", type="primary", use_container_width=True):
                wizard.next_step()
                st.rerun()
        else:
            st.button("Avanti →", use_container_width=True, disabled=True,
                     help="Carica un file per continuare")


def render_step_3_preview(wizard: OnboardingWizard):
    """Step 3: Preview & Confirmation"""

    # Progress indicator
    st.caption("Passo 3 di 4")
    st.progress(0.75)

    st.markdown("---")

    st.markdown("### 👀 Verifica Dati")

    uploaded_file = wizard.get_data('uploaded_file')
    file_name = wizard.get_data('file_name', 'file.xlsx')

    if uploaded_file is None:
        st.error("File non trovato. Torna indietro e carica un file.")
        if st.button("← Torna indietro", type="primary"):
            wizard.prev_step()
            st.rerun()
        return

    # Load file to staging area if not already done
    if not st.session_state.get('excel_staging'):
        with st.spinner("Analisi file in corso..."):
            try:
                # Save temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = Path(tmp.name)

                # Detect file format
                xls = pd.ExcelFile(tmp_path)
                available_sheets = xls.sheet_names

                # Check for DB_ORG format
                if 'DB_ORG' in available_sheets:
                    # DB_ORG format detected
                    df = pd.read_excel(tmp_path, sheet_name='DB_ORG')

                    st.session_state.excel_staging = {
                        'format': 'DB_ORG',
                        'data': df,
                        'filename': uploaded_file.name,
                        'file_size_mb': len(uploaded_file.getvalue()) / (1024 * 1024)
                    }

                    # Also store for import wizard
                    st.session_state.uploaded_db_org_file = uploaded_file
                    st.session_state.db_org_file_ready = True

                # Check for TNS format
                elif 'TNS Personale' in available_sheets and 'TNS Strutture' in available_sheets:
                    personale_df = pd.read_excel(tmp_path, sheet_name='TNS Personale')
                    strutture_df = pd.read_excel(tmp_path, sheet_name='TNS Strutture')

                    st.session_state.excel_staging = {
                        'format': 'TNS',
                        'personale': personale_df,
                        'strutture': strutture_df,
                        'personale_df': personale_df,
                        'strutture_df': strutture_df,
                        'filename': uploaded_file.name,
                        'file_size_mb': len(uploaded_file.getvalue()) / (1024 * 1024)
                    }
                else:
                    # Unsupported format
                    st.error(f"""❌ Formato file non riconosciuto

**Fogli trovati:** {', '.join(available_sheets)}

**Formati supportati:**
- DB_ORG (consigliato)
- TNS Personale + TNS Strutture
                    """)
                    if st.button("← Torna indietro", type="primary"):
                        wizard.prev_step()
                        st.rerun()
                    return

                # Cleanup temp file
                tmp_path.unlink(missing_ok=True)

            except Exception as e:
                st.error(f"❌ Errore durante l'analisi del file: {str(e)}")
                if st.button("← Torna indietro", type="primary"):
                    wizard.prev_step()
                    st.rerun()
                return

    # Get staging data
    staging = st.session_state.get('excel_staging', {})
    is_db_org = staging.get('format') == 'DB_ORG'

    # Show file info
    col1, col2 = st.columns(2)

    with col1:
        st.metric("📄 File", file_name)

    with col2:
        format_label = "DB_ORG ✅" if is_db_org else "TNS"
        st.metric("📋 Formato", format_label)

    st.markdown("---")

    # Show detected data
    st.markdown("### Dati rilevati:")

    if is_db_org:
        # DB_ORG format
        df = staging.get('data')
        if df is not None and not df.empty:
            # Count employees (rows with CF)
            employees = df[df['TxCodFiscale'].notna()].shape[0]
            # Count structures (rows without CF)
            structures = df[df['TxCodFiscale'].isna()].shape[0]
            # Count columns
            columns = df.shape[1]

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("👥 Dipendenti", f"{employees:,}")

            with col2:
                st.metric("🏢 Strutture", f"{structures:,}")

            with col3:
                st.metric("📊 Colonne", f"{columns}")

            st.success("✅ File validato con successo!")

    else:
        # TNS format
        personale_df = staging.get('personale')
        strutture_df = staging.get('strutture')

        col1, col2 = st.columns(2)

        with col1:
            if personale_df is not None:
                st.metric("👥 Dipendenti", f"{len(personale_df):,}")
            else:
                st.metric("👥 Dipendenti", "0")

        with col2:
            if strutture_df is not None:
                st.metric("🏢 Strutture", f"{len(strutture_df):,}")
            else:
                st.metric("🏢 Strutture", "0")

        st.success("✅ File validato con successo!")

    st.markdown("---")

    # Preview expander
    with st.expander("🔍 Mostra Anteprima Dati", expanded=False):
        if is_db_org:
            df = staging.get('data')
            if df is not None:
                st.dataframe(df.head(10), use_container_width=True)
        else:
            if personale_df is not None:
                st.markdown("**TNS Personale:**")
                st.dataframe(personale_df.head(5), use_container_width=True)

            if strutture_df is not None:
                st.markdown("**TNS Strutture:**")
                st.dataframe(strutture_df.head(5), use_container_width=True)

    st.markdown("---")

    # Navigation buttons
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.button("← Indietro", use_container_width=True):
            wizard.prev_step()
            st.rerun()

    with col3:
        if st.button("Importa →", type="primary", use_container_width=True,
                    help="Procedi con l'importazione guidata"):
            wizard.next_step()
            st.rerun()
