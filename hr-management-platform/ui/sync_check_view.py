"""
Vista Streamlit per la verifica di consistenza DB-Excel.
"""
import streamlit as st
import pandas as pd
from pathlib import Path
from typing import List
import io

from models.sync_models import PersonMismatch, SyncCheckResult
from services.sync_checker import SyncChecker
import config

def show_sync_check_view():
    """Vista principale per la verifica di consistenza DB-Excel."""

    st.markdown("""
    Questa funzionalità verifica la consistenza tra i dati presenti nel **database SQLite**
    e un **file Excel di riferimento**.

    **Verifiche eseguite:**
    1. 📋 **Completezza Persone**: Tutte le persone dell'Excel sono presenti nel DB?
    2. 👤 **Coerenza Responsabili**: Ogni responsabile assegnato esiste ed è abilitato come Approvatore?

    ---
    """)

    # 1️⃣ Selezione file Excel

    excel_files = _get_available_excel_files()

    if not excel_files:
        st.warning("⚠️ Nessun file Excel trovato nella cartella `data/input/`.")
        st.info("Carica un file Excel (.xls o .xlsx) in `data/input/` e riprova.")
        return

    selected_file = st.selectbox(
        "File Excel da verificare:",
        options=excel_files,
        help="Seleziona il file Excel di riferimento da confrontare con il database"
    )

    # Opzioni avanzate
    with st.expander("⚙️ Opzioni Avanzate", expanded=False):
        sheet_name = st.text_input(
            "Nome foglio Excel",
            value="TNS Personale",
            help="Nome del foglio contenente i dati Personale"
        )

    # 2️⃣ Esegui verifica

    if st.button("🚀 Avvia Verifica", type="primary", use_container_width=True):
        with st.spinner("🔍 Verifica in corso..."):
            try:
                # Ottieni database handler da session state
                if 'database_handler' not in st.session_state:
                    st.error("❌ DatabaseHandler non inizializzato. Riavvia l'applicazione.")
                    return

                db_handler = st.session_state.database_handler

                # Crea checker ed esegui verifica
                checker = SyncChecker(db_handler)
                excel_path = config.INPUT_DIR / selected_file

                result = checker.check_consistency(
                    excel_path=str(excel_path),
                    excel_sheet_name=sheet_name
                )

                # Salva risultato in session state
                st.session_state.sync_check_result = result

                st.success("✅ Verifica completata!")
                st.rerun()

            except FileNotFoundError as e:
                st.error(f"❌ File non trovato: {e}")
            except ValueError as e:
                st.error(f"❌ Errore nella verifica: {e}")
            except Exception as e:
                st.error(f"❌ Errore imprevisto: {e}")
                st.exception(e)

    # Mostra risultati se presenti
    if 'sync_check_result' in st.session_state:
        _show_results(st.session_state.sync_check_result)

def _get_available_excel_files() -> List[str]:
    """
    Trova tutti i file Excel (.xls, .xlsx) nella cartella input.

    Returns:
        Lista di nomi file Excel disponibili
    """
    excel_files = []

    if config.INPUT_DIR.exists():
        for file_path in config.INPUT_DIR.iterdir():
            if file_path.suffix.lower() in ['.xls', '.xlsx']:
                excel_files.append(file_path.name)

    return sorted(excel_files)

def _show_results(result: SyncCheckResult):
    """
    Mostra i risultati della verifica di consistenza.

    Args:
        result: Oggetto SyncCheckResult con i dati della verifica
    """

    # Timestamp e file
    st.caption(f"📅 Verifica eseguita: {result.timestamp.strftime('%d/%m/%Y %H:%M:%S')}")
    st.caption(f"📄 File Excel: `{result.excel_file}`")

    # Panoramica - 4 metriche
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="📊 Record Excel",
            value=result.excel_row_count,
            help="Numero di dipendenti nel file Excel"
        )

    with col2:
        st.metric(
            label="💾 Record DB",
            value=result.db_row_count,
            help="Numero di dipendenti nel database"
        )

    with col3:
        st.metric(
            label="✅ Consistenza",
            value=f"{result.consistency_percentage:.1f}%",
            delta=None if result.consistency_percentage == 100 else f"-{100 - result.consistency_percentage:.1f}%",
            delta_color="normal",
            help="Percentuale di dipendenti Excel consistenti con il DB"
        )

    with col4:
        st.metric(
            label="⚠️ Problemi",
            value=result.total_issues,
            delta=None if result.total_issues == 0 else f"+{result.total_issues}",
            delta_color="inverse",
            help="Numero totale di inconsistenze rilevate"
        )

    # Status generale
    if not result.has_issues:
        st.success("✅ **Perfetta consistenza!** Nessun problema rilevato.")
    else:
        st.warning(f"⚠️ **Rilevati {result.total_issues} problemi di consistenza.**")

    # Dettaglio categorie - 3 metriche

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="🔴 Mancanti in DB",
            value=result.missing_in_db_count,
            help="Dipendenti presenti in Excel ma non nel database"
        )

    with col2:
        st.metric(
            label="🟡 Mancanti in Excel",
            value=result.missing_in_excel_count,
            help="Dipendenti presenti nel database ma non in Excel (info)"
        )

    with col3:
        st.metric(
            label="🟠 Incoerenze Responsabili",
            value=result.responsabile_issues_count,
            help="Responsabili inesistenti o senza flag Approvatore"
        )

    # Dettagli problemi - 4 tabs
    if result.has_issues:

        tab1, tab2, tab3, tab4 = st.tabs([
            f"🔴 Mancanti DB ({result.missing_in_db_count})",
            f"🟡 Mancanti Excel ({result.missing_in_excel_count})",
            f"🔴 Resp. Inesistenti ({len(result.responsabile_missing)})",
            f"🟠 Resp. Non Approvatori ({len(result.responsabile_not_approver)})"
        ])

        with tab1:
            if result.missing_in_db:
                _show_mismatch_table(
                    result.missing_in_db,
                    title="Dipendenti presenti in Excel ma **non trovati nel database**",
                    show_responsabile=False,
                    show_flag=False
                )
            else:
                st.info("✅ Nessun dipendente mancante nel database.")

        with tab2:
            if result.missing_in_excel:
                _show_mismatch_table(
                    result.missing_in_excel,
                    title="Dipendenti presenti nel database ma **non trovati in Excel**",
                    show_responsabile=False,
                    show_flag=False
                )
            else:
                st.info("✅ Tutti i dipendenti del database sono presenti in Excel.")

        with tab3:
            if result.responsabile_missing:
                _show_mismatch_table(
                    result.responsabile_missing,
                    title="Dipendenti con responsabile **inesistente nel database**",
                    show_responsabile=True,
                    show_flag=False
                )
            else:
                st.info("✅ Tutti i responsabili assegnati esistono nel database.")

        with tab4:
            if result.responsabile_not_approver:
                _show_mismatch_table(
                    result.responsabile_not_approver,
                    title="Dipendenti con responsabile **senza flag Approvatore=SÌ**",
                    show_responsabile=True,
                    show_flag=True
                )
            else:
                st.info("✅ Tutti i responsabili hanno il flag Approvatore corretto.")
    else:
        st.success("✅ Nessun problema da visualizzare.")

def _show_mismatch_table(
    mismatches: List[PersonMismatch],
    title: str,
    show_responsabile: bool = False,
    show_flag: bool = False
):
    """
    Mostra una tabella con i dettagli delle inconsistenze.

    Args:
        mismatches: Lista di PersonMismatch da visualizzare
        title: Titolo della tabella
        show_responsabile: Se True, mostra colonne responsabile
        show_flag: Se True, mostra colonna flag Approvatore
    """
    if not mismatches:
        return

    st.markdown(f"**{title}**")

    # Costruisci DataFrame per visualizzazione
    data = []
    for m in mismatches:
        row = {
            'Codice Fiscale': m.codice_fiscale,
            'Codice': m.codice or 'N/D',
            'Nome': m.titolare,
            'Unità Organizzativa': m.unita_organizzativa or 'N/D',
            'Dettagli': m.details
        }

        if show_responsabile:
            row['Resp. Codice'] = m.responsabile_codice or 'N/D'
            row['Resp. Nome'] = m.responsabile_nome or 'N/D'

        if show_flag:
            row['Flag Approvatore'] = m.responsabile_approvatore_flag or 'N/D'

        data.append(row)

    df = pd.DataFrame(data)

    # Filtro ricerca (solo se >10 righe)
    if len(df) > 10:
        search = st.text_input(
            "🔎 Cerca (Nome o CF)",
            key=f"search_{title[:20]}",
            help="Filtra la tabella per nome o codice fiscale"
        )

        if search:
            mask = (
                df['Nome'].str.contains(search, case=False, na=False) |
                df['Codice Fiscale'].str.contains(search, case=False, na=False)
            )
            df = df[mask]

    # Mostra tabella
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

    # Download CSV
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
    csv_data = csv_buffer.getvalue()

    st.download_button(
        label="📥 Scarica CSV",
        data=csv_data,
        file_name=f"inconsistenze_{title[:30].replace(' ', '_')}.csv",
        mime="text/csv",
        help="Scarica questa tabella in formato CSV"
    )
