"""
Vista Ricerca Intelligente - Sostituisce il Bot conversazionale
Permette ricerche cross-table, filtri, query predefinite, export risultati
"""
import streamlit as st
import pandas as pd
from pathlib import Path
import config

def show_search_view():
    """Mostra vista ricerca intelligente"""
    st.caption("Cerca dipendenti e strutture, filtra per ruolo, UO, sede. Esporta risultati.")

    # Check data loaded
    if not st.session_state.data_loaded:
        st.warning("⚠️ Dati non caricati. Carica un file Excel prima di usare la ricerca.")
        return

    personale_df = st.session_state.personale_df
    strutture_df = st.session_state.strutture_df

    # === SEARCH BAR GLOBALE ===
    st.markdown("### 🔎 Ricerca Globale")
    query = st.text_input(
        "Cerca per nome, CF, codice, descrizione...",
        placeholder="es. Mario Rossi, RSSMRA80A01H501Z, P001",
        help="Cerca in tutti i campi chiave di personale e strutture"
    )

    # === FILTRI RAPIDI ===
    st.markdown("### 🎯 Filtri Rapidi")
    col1, col2, col3 = st.columns(3)

    with col1:
        # UO filter
        all_uo = sorted(list(set(
            list(personale_df['Unità Organizzativa'].dropna().unique()) +
            list(strutture_df['Unità Organizzativa'].dropna().unique())
        )))
        uo_filter = st.multiselect(
            "Unità Organizzativa",
            options=all_uo,
            help="Filtra per unità organizzativa"
        )

    with col2:
        # Ruolo filter (solo personale)
        ruoli = ["Tutti", "Approvatore", "Controllore", "Cassiere", "Viaggiatore",
                 "Segretario", "Visualizzatori", "Amministrazione"]
        ruolo_filter = st.selectbox("Ruolo", options=ruoli)

    with col3:
        # Sede filter
        all_sedi = sorted(personale_df['Sede_TNS'].dropna().unique().tolist())
        sede_filter = st.multiselect(
            "Sede",
            options=all_sedi,
            help="Filtra per sede"
        )

    # === QUERY PREDEFINITE ===
    st.markdown("### ⚡ Query Rapide")
    col1, col2, col3, col4 = st.columns(4)

    query_type = None

    with col1:
        if st.button("🔍 Trova Orfani", use_container_width=True,
                     help="Dipendenti senza struttura padre valida"):
            query_type = "orfani"

    with col2:
        if st.button("🔍 Senza Approvatore", use_container_width=True,
                     help="Dipendenti che non hanno approvatore assegnato"):
            query_type = "no_approvatore"

    with col3:
        if st.button("🔍 Cicli Gerarchici", use_container_width=True,
                     help="Strutture con riferimenti circolari"):
            query_type = "cicli"

    with col4:
        if st.button("🔍 Duplicati CF", use_container_width=True,
                     help="Codici fiscali duplicati"):
            query_type = "duplicati_cf"

    # === ESEGUI RICERCA ===
    results_personale = personale_df.copy()
    results_strutture = strutture_df.copy()
    query_description = ""

    # Applica query globale
    if query:
        query_lower = query.lower()

        # Personale: cerca in Titolare, TxCodFiscale, Codice
        mask_p = (
            personale_df['Titolare'].fillna('').str.lower().str.contains(query_lower) |
            personale_df['TxCodFiscale'].fillna('').str.lower().str.contains(query_lower) |
            personale_df['Codice'].fillna('').str.lower().str.contains(query_lower)
        )
        results_personale = personale_df[mask_p]

        # Strutture: cerca in DESCRIZIONE, Codice
        mask_s = (
            strutture_df['DESCRIZIONE'].fillna('').str.lower().str.contains(query_lower) |
            strutture_df['Codice'].fillna('').str.lower().str.contains(query_lower)
        )
        results_strutture = strutture_df[mask_s]

        query_description = f"Query: '{query}'"

    # Applica filtri
    if uo_filter:
        results_personale = results_personale[results_personale['Unità Organizzativa'].isin(uo_filter)]
        results_strutture = results_strutture[results_strutture['Unità Organizzativa'].isin(uo_filter)]
        query_description += f" | UO: {', '.join(uo_filter)}"

    if ruolo_filter and ruolo_filter != "Tutti":
        results_personale = results_personale[results_personale[ruolo_filter] == 'SÌ']
        query_description += f" | Ruolo: {ruolo_filter}"

    if sede_filter:
        results_personale = results_personale[results_personale['Sede_TNS'].isin(sede_filter)]
        query_description += f" | Sede: {', '.join(sede_filter)}"

    # Applica query predefinite
    if query_type == "orfani":
        # Dipendenti con padre non esistente
        all_codici = set(strutture_df['Codice'].dropna().unique())
        mask = ~results_personale['UNITA\' OPERATIVA PADRE '].fillna('').isin(all_codici) & \
               (results_personale['UNITA\' OPERATIVA PADRE '].fillna('') != '')
        results_personale = results_personale[mask]
        results_strutture = pd.DataFrame()  # Solo personale
        query_description = "Query: Orfani (padre inesistente)"

    elif query_type == "no_approvatore":
        mask = results_personale['Approvatore'].fillna('') != 'SÌ'
        results_personale = results_personale[mask]
        results_strutture = pd.DataFrame()
        query_description = "Query: Senza Approvatore"

    elif query_type == "cicli":
        # Rileva cicli nelle strutture
        from models.strutture import detect_cycles
        cycles = detect_cycles(strutture_df)
        if cycles:
            cicli_codici = [item for cycle in cycles for item in cycle]
            results_strutture = strutture_df[strutture_df['Codice'].isin(cicli_codici)]
            results_personale = pd.DataFrame()
            query_description = f"Query: Cicli Gerarchici ({len(cycles)} trovati)"
        else:
            st.info("✅ Nessun ciclo gerarchico trovato!")
            results_strutture = pd.DataFrame()
            results_personale = pd.DataFrame()

    elif query_type == "duplicati_cf":
        # CF duplicati
        duplicati = personale_df['TxCodFiscale'].value_counts()
        duplicati_cf = duplicati[duplicati > 1].index.tolist()
        if duplicati_cf:
            results_personale = personale_df[personale_df['TxCodFiscale'].isin(duplicati_cf)]
            results_strutture = pd.DataFrame()
            query_description = f"Query: CF Duplicati ({len(duplicati_cf)} CF con duplicati)"
        else:
            st.info("✅ Nessun CF duplicato trovato!")
            results_personale = pd.DataFrame()
            results_strutture = pd.DataFrame()

    # === RISULTATI ===
    st.markdown("### 📊 Risultati")

    if query_description:
        st.caption(query_description)

    total_results = len(results_personale) + len(results_strutture)

    if total_results == 0:
        st.info("🔍 Nessun risultato trovato. Modifica query o filtri.")
        return

    # KPI results
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("👥 Personale", len(results_personale))
    with col2:
        st.metric("🏗️ Strutture", len(results_strutture))
    with col3:
        st.metric("📊 Totale", total_results)

    # Tabs risultati
    tab1, tab2 = st.tabs(["👥 Personale", "🏗️ Strutture"])

    with tab1:
        if len(results_personale) > 0:
            st.dataframe(
                results_personale,
                use_container_width=True,
                height=400,
                hide_index=True
            )
        else:
            st.info("Nessun dipendente trovato con questi criteri")

    with tab2:
        if len(results_strutture) > 0:
            st.dataframe(
                results_strutture,
                use_container_width=True,
                height=400,
                hide_index=True
            )
        else:
            st.info("Nessuna struttura trovata con questi criteri")

    # === EXPORT RISULTATI ===
    st.markdown("### 📤 Esporta Risultati")

    col1, col2 = st.columns([3, 1])

    with col1:
        st.caption(f"Esporta {total_results} risultati in un file Excel")

    with col2:
        if st.button("📥 Esporta Excel", type="primary", use_container_width=True):
            try:
                # Crea Excel con risultati
                from services.excel_handler import ExcelHandler
                import tempfile

                # Crea file temporaneo
                output_path = config.OUTPUT_DIR / f"ricerca_risultati_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

                # Scrivi Excel
                with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                    if len(results_personale) > 0:
                        results_personale.to_excel(writer, sheet_name='Personale', index=False)
                    if len(results_strutture) > 0:
                        results_strutture.to_excel(writer, sheet_name='Strutture', index=False)

                    # Metadata sheet
                    metadata_df = pd.DataFrame([{
                        'Query': query_description,
                        'Data Export': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'Record Personale': len(results_personale),
                        'Record Strutture': len(results_strutture),
                        'Totale': total_results
                    }])
                    metadata_df.to_excel(writer, sheet_name='Info', index=False)

                st.success(f"✅ File esportato: `{output_path.name}`")

                # Download button
                with open(output_path, 'rb') as f:
                    st.download_button(
                        label="⬇️ Scarica File",
                        data=f.read(),
                        file_name=output_path.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

            except Exception as e:
                st.error(f"❌ Errore export: {str(e)}")
