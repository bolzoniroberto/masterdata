"""
UI per gestione Ruoli di Approvazione Trasferte/Note Spese.
Layout: 3 tab principali per gestire i 16 campi ruoli di approvazione.
"""
import streamlit as st
import pandas as pd
import numpy as np
from ui.styles import apply_common_styles, render_filter_badge
import config


# Costanti
ROLE_FIELDS = [
    "RUOLI OltreV",
    "RUOLI",
    "Viaggiatore",
    "Segr_Redaz",
    "Approvatore",
    "Cassiere",
    "Visualizzatori",
    "Segretario",
    "Controllore",
    "Amministrazione",
    "SegreteriA Red. Ass.ta",
    "SegretariO Ass.to",
    "Controllore Ass.to",
    "RuoliAFC",
    "RuoliHR",
    "AltriRuoli"
]

# Organizzazione ruoli per sezioni
ROLE_SECTIONS = {
    "📌 Ruoli Principali": [
        "Viaggiatore",
        "Approvatore",
        "Controllore",
        "Cassiere",
        "Segretario"
    ],
    "👁️ Visualizzatori & Admin": [
        "Visualizzatori",
        "Amministrazione"
    ],
    "🎯 Ruoli Assistiti": [
        "SegreteriA Red. Ass.ta",
        "SegretariO Ass.to",
        "Controllore Ass.to"
    ],
    "🔧 Ruoli Specializzati": [
        "RUOLI OltreV",
        "RUOLI",
        "RuoliAFC",
        "RuoliHR",
        "Segr_Redaz",
        "AltriRuoli"
    ]
}


def show_ruoli_view():
    """Entry point principale per gestione ruoli"""

    apply_common_styles()

    st.header("🎭 Gestione Ruoli Approvazione")
    st.caption("Gestisci i 16 campi ruoli di approvazione per trasferte e note spese")

    personale_df = st.session_state.personale_df

    # === METRICHE RAPIDE ===
    show_role_metrics(personale_df)

    st.markdown("---")

    # === TAB PRINCIPALE ===
    tab1, tab2, tab3 = st.tabs(["✏️ Tabella Editabile", "🔢 Matrice Ruoli", "📊 Report Aggregato"])

    with tab1:
        show_editable_table_view(personale_df)

    with tab2:
        show_role_matrix_view(personale_df)

    with tab3:
        show_aggregate_report_view(personale_df)


def show_role_metrics(personale_df: pd.DataFrame):
    """Mostra metriche dashboard per ruoli"""

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        total_employees = len(personale_df)
        st.metric("👥 Dipendenti", total_employees)

    with col2:
        employees_with_roles = 0
        for role_col in ROLE_FIELDS:
            if role_col in personale_df.columns:
                has_role = personale_df[role_col].notna() & (personale_df[role_col] != "")
                employees_with_roles = max(employees_with_roles, has_role.sum())
        st.metric("✅ Con Ruoli", employees_with_roles)

    with col3:
        coverage = (employees_with_roles / total_employees * 100) if total_employees > 0 else 0
        st.metric("📊 Copertura %", f"{coverage:.1f}%")

    with col4:
        sedi = personale_df['Sede_TNS'].nunique()
        st.metric("🏢 Sedi", sedi)

    with col5:
        uos = personale_df['Unità Organizzativa'].nunique()
        st.metric("🏗️ UO", uos)


def show_editable_table_view(personale_df: pd.DataFrame):
    """Tab 1: Tabella editabile con master-detail"""

    st.markdown("### ✏️ Modifica Ruoli - Vista Master-Detail")
    st.caption("Seleziona un dipendente dalla tabella per modificare i suoi ruoli")

    # === FILTRI ===
    st.markdown('<div class="sticky-filters">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    with col1:
        search_text = st.text_input("🔍 Cerca (Nome, CF, Codice)", key="search_ruoli")

    with col2:
        filter_uo = st.multiselect(
            "Unità Organizzativa",
            options=sorted(personale_df['Unità Organizzativa'].dropna().unique()),
            key="filter_uo_ruoli"
        )

    with col3:
        filter_role = st.selectbox(
            "Filtra per Ruolo",
            options=["Tutti"] + ROLE_FIELDS,
            key="filter_role_ruoli"
        )

    st.markdown('</div>', unsafe_allow_html=True)

    # === APPLICA FILTRI ===
    filtered_df = apply_filters_editable(personale_df, search_text, filter_uo, filter_role)
    render_filter_badge(len(filtered_df), len(personale_df))

    # === MASTER-DETAIL LAYOUT ===
    col_master, col_detail = st.columns([0.4, 0.6])

    with col_master:
        st.markdown("#### 📋 Lista Dipendenti")

        if len(filtered_df) > 0:
            master_df = filtered_df[['Codice', 'Titolare', 'Unità Organizzativa']].copy()
            master_df = master_df.reset_index(drop=True)

            selection = st.dataframe(
                master_df,
                use_container_width=True,
                height=500,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                column_config={
                    'Codice': st.column_config.TextColumn('Codice', width='small'),
                    'Titolare': st.column_config.TextColumn('Nome', width='large'),
                    'Unità Organizzativa': st.column_config.TextColumn('UO', width='medium'),
                }
            )

            if selection and selection.selection and selection.selection.rows:
                selected_idx = selection.selection.rows[0]
                selected_codice = master_df.iloc[selected_idx]['Codice']
                st.session_state.selected_role_employee = selected_codice
        else:
            st.info("Nessun record trovato")

    with col_detail:
        if st.session_state.get('selected_role_employee'):
            show_role_detail_panel(personale_df, filtered_df)
        else:
            st.info("👈 Seleziona un dipendente dalla tabella")


def show_role_detail_panel(personale_df: pd.DataFrame, filtered_df: pd.DataFrame):
    """Mostra panel dettagli ruoli editabile"""

    selected_codice = st.session_state.selected_role_employee
    record = personale_df[personale_df['Codice'] == selected_codice]

    if len(record) == 0:
        st.error(f"Record non trovato")
        st.session_state.selected_role_employee = None
        return

    record = record.iloc[0]
    idx = personale_df[personale_df['Codice'] == selected_codice].index[0]

    st.markdown(f"#### ✏️ Ruoli: {record['Titolare']}")
    st.caption(f"Codice Fiscale: `{record['TxCodFiscale']}`")

    # === SEZIONI RUOLI ===
    for section_name, section_roles in ROLE_SECTIONS.items():
        with st.expander(section_name, expanded=(section_name == "📌 Ruoli Principali")):
            for role_col in section_roles:
                if role_col in personale_df.columns:
                    current_value = record.get(role_col, "") or ""
                    new_value = st.text_area(
                        role_col,
                        value=current_value,
                        height=60,
                        key=f"role_{role_col}_{selected_codice}",
                        help=f"Inserisci i dati per il ruolo {role_col}"
                    )

                    # Salva in tempo reale (session state + database)
                    if new_value != current_value:
                        personale_df.at[idx, role_col] = new_value if new_value else None
                        st.session_state.personale_df = personale_df

                        # === PERSISTI NEL DATABASE ===
                        try:
                            db_handler = st.session_state.database_handler
                            updates = {role_col: new_value if new_value else None}
                            db_handler.update_personale(record['TxCodFiscale'], updates)
                        except Exception as e:
                            st.warning(f"⚠️ Errore persistenza database: {str(e)}")

    st.markdown("---")

    # === BOTTONI AZIONE ===
    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 Salva & Rigenera DB_TNS", type="primary", use_container_width=True):
            st.session_state.personale_df = personale_df
            st.success("✅ Modifiche salvate!")
            st.session_state.show_feedback = True
            st.rerun()

    with col2:
        if st.button("🔄 Deseleziona", use_container_width=True):
            st.session_state.selected_role_employee = None
            st.rerun()


def show_role_matrix_view(personale_df: pd.DataFrame):
    """Tab 2: Matrice ruoli (righe=ruoli, colonne=dipendenti)"""

    st.markdown("### 🔢 Matrice Ruoli")
    st.caption("Visualizza l'assegnazione di ruoli ai dipendenti in formato matrice")

    # === FILTRI ===
    col1, col2, col3 = st.columns(3)

    with col1:
        filter_matrix_uo = st.multiselect(
            "Unità Organizzativa",
            options=sorted(personale_df['Unità Organizzativa'].dropna().unique()),
            key="filter_matrix_uo"
        )

    with col2:
        only_assigned = st.checkbox("Solo ruoli assegnati", value=False, key="matrix_only_assigned")

    with col3:
        max_employees = st.slider("Max dipendenti", min_value=10, max_value=100, value=50, step=10)

    # === APPLICA FILTRI ===
    filtered_df = personale_df.copy()

    if filter_matrix_uo:
        filtered_df = filtered_df[filtered_df['Unità Organizzativa'].isin(filter_matrix_uo)]

    if len(filtered_df) > max_employees:
        st.warning(f"⚠️ Troppi dipendenti ({len(filtered_df)}). Mostrando i primi {max_employees}. Usa i filtri UO per ridurre.")
        filtered_df = filtered_df.head(max_employees)

    # === COSTRUISCI MATRICE ===
    matrix_df = build_role_matrix(filtered_df)

    if matrix_df is not None and len(matrix_df) > 0:
        st.dataframe(
            matrix_df,
            use_container_width=True,
            height=500,
            column_config={col: st.column_config.TextColumn(col, width='small') for col in matrix_df.columns}
        )

        st.caption(f"📊 Matrice: {len(matrix_df)} ruoli × {len(matrix_df.columns)} dipendenti")
    else:
        st.info("Nessun dato disponibile con i filtri applicati")


def show_aggregate_report_view(personale_df: pd.DataFrame):
    """Tab 3: Report aggregato con statistiche per ruolo"""

    st.markdown("### 📊 Report Aggregato Ruoli")
    st.caption("Visualizza statistiche e copertura per ogni ruolo")

    # === FILTRI ===
    col1, col2 = st.columns(2)

    with col1:
        sort_by = st.selectbox(
            "Ordina per",
            options=["Count (alto → basso)", "Count (basso → alto)", "Nome ruolo"],
            key="report_sort"
        )

    with col2:
        min_count = st.slider("Min dipendenti", min_value=0, max_value=20, value=0, step=1)

    # === COSTRUISCI REPORT ===
    report_data = build_aggregate_report(personale_df, min_count, sort_by)

    if len(report_data) > 0:
        for idx, row in report_data.iterrows():
            role_name = row['Ruolo']
            count = row['Dipendenti']
            coverage = row['Copertura %']
            employees = row['Dipendenti List']

            # === HEADER RUOLO ===
            with st.expander(
                f"**{role_name}** | 👥 {count} dipendenti | 📊 {coverage:.1f}% copertura",
                expanded=False
            ):
                st.metric("Dipendenti assegnati", count)
                st.metric("Copertura unità org", f"{coverage:.1f}%")

                if employees:
                    st.markdown("#### 👥 Dipendenti assegnati:")
                    for emp in employees:
                        st.markdown(f"- {emp}")
    else:
        st.info("Nessun ruolo con i filtri applicati")


# === FUNZIONI HELPER ===

def apply_filters_editable(df: pd.DataFrame, search_text: str, filter_uo: list, filter_role: str) -> pd.DataFrame:
    """Applica filtri alla tabella editabile"""

    filtered_df = df.copy()

    if search_text:
        mask = (
            filtered_df['Titolare'].str.contains(search_text, case=False, na=False) |
            filtered_df['TxCodFiscale'].str.contains(search_text, case=False, na=False) |
            filtered_df['Codice'].str.contains(search_text, case=False, na=False)
        )
        filtered_df = filtered_df[mask]

    if filter_uo:
        filtered_df = filtered_df[filtered_df['Unità Organizzativa'].isin(filter_uo)]

    if filter_role != "Tutti" and filter_role in df.columns:
        # Mostra solo dipendenti che hanno il ruolo assegnato
        mask = filtered_df[filter_role].notna() & (filtered_df[filter_role] != "")
        filtered_df = filtered_df[mask]

    return filtered_df


def parse_role_values(role_str: str) -> list:
    """Parsa valori ruolo separati da ,|; in lista"""

    if not role_str or pd.isna(role_str):
        return []

    # Normalizza separatori
    role_str = str(role_str).strip()
    for sep in ['|', ';']:
        role_str = role_str.replace(sep, ',')

    # Dividi e pulisci
    values = [v.strip() for v in role_str.split(',') if v.strip()]
    return values


def has_role(role_str: str) -> bool:
    """Controlla se il ruolo è valorizzato"""
    return role_str is not None and str(role_str).strip() != "" and not pd.isna(role_str)


def build_role_matrix(personale_df: pd.DataFrame) -> pd.DataFrame:
    """Costruisce matrice ruoli (righe=ruoli, colonne=dipendenti)"""

    if len(personale_df) == 0:
        return None

    # Crea colonna di intestazione dipendente
    personale_df = personale_df.copy()
    personale_df['_emp_label'] = personale_df['Codice'] + " " + personale_df['Titolare'].str[:10]

    # Costruisci matrice
    matrix_data = {}

    for idx, row in personale_df.iterrows():
        emp_label = row['_emp_label']
        matrix_data[emp_label] = {}

        for role_col in ROLE_FIELDS:
            if role_col in personale_df.columns:
                role_value = row.get(role_col, "")

                if has_role(role_value):
                    # Abbrevia il valore se troppo lungo
                    display_value = str(role_value)[:15]
                    if len(str(role_value)) > 15:
                        display_value += "..."
                    matrix_data[emp_label][role_col] = display_value
                else:
                    matrix_data[emp_label][role_col] = ""

    # Converti in DataFrame
    matrix_df = pd.DataFrame(matrix_data).T
    matrix_df = matrix_df[[col for col in ROLE_FIELDS if col in matrix_df.columns]]

    return matrix_df


def build_aggregate_report(personale_df: pd.DataFrame, min_count: int = 0, sort_by: str = "Count (alto → basso)") -> pd.DataFrame:
    """Costruisce report aggregato con statistiche per ruolo"""

    report_rows = []
    total_uos = personale_df['Unità Organizzativa'].nunique()

    for role_col in ROLE_FIELDS:
        if role_col not in personale_df.columns:
            continue

        # Conta dipendenti con questo ruolo
        has_role_mask = personale_df[role_col].notna() & (personale_df[role_col] != "")
        count = has_role_mask.sum()

        if count < min_count:
            continue

        # Calcola copertura UO
        uos_with_role = personale_df[has_role_mask]['Unità Organizzativa'].nunique()
        coverage_pct = (uos_with_role / total_uos * 100) if total_uos > 0 else 0

        # Lista dipendenti
        employees_list = personale_df[has_role_mask]['Titolare'].tolist()

        report_rows.append({
            'Ruolo': role_col,
            'Dipendenti': count,
            'Copertura %': coverage_pct,
            'Dipendenti List': employees_list
        })

    report_df = pd.DataFrame(report_rows)

    if len(report_df) == 0:
        return report_df

    # Applica sorting
    if sort_by == "Count (alto → basso)":
        report_df = report_df.sort_values('Dipendenti', ascending=False)
    elif sort_by == "Count (basso → alto)":
        report_df = report_df.sort_values('Dipendenti', ascending=True)
    else:  # Nome ruolo
        report_df = report_df.sort_values('Ruolo', ascending=True)

    return report_df.reset_index(drop=True)
