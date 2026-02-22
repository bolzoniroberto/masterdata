"""
Organigramma Drill-Down Interattivo
Vista navigabile per esplorare la gerarchia livello per livello
"""
import streamlit as st
import pandas as pd
from typing import Optional, List, Dict

def show_organigramma_drilldown(strutture_df: pd.DataFrame, personale_df: pd.DataFrame):
    """Vista drill-down interattiva con navigazione breadcrumb"""

    st.markdown("### 🔍 Esplora Organigramma")
    st.caption("Clicca su una struttura per esplorare il livello sotto")

    # Inizializza session state per navigazione
    if 'drill_path' not in st.session_state:
        st.session_state.drill_path = []  # Stack di codici strutture

    # === BREADCRUMB NAVIGATION ===
    render_breadcrumb(strutture_df)

    # Determina livello corrente
    current_codice = st.session_state.drill_path[-1] if st.session_state.drill_path else None

    # === MOSTRA STRUTTURE CORRENTE LIVELLO ===
    if current_codice is None:
        # Livello root
        st.markdown("#### 🏛️ Strutture Principali")
        render_root_structures(strutture_df, personale_df)
    else:
        # Livello figlio
        current_struct = strutture_df[strutture_df['Codice'] == current_codice].iloc[0]
        st.markdown(f"#### 🏢 {current_struct['DESCRIZIONE']}")
        render_child_level(current_codice, strutture_df, personale_df)

def render_breadcrumb(strutture_df: pd.DataFrame):
    """Render breadcrumb navigation per tornare indietro"""

    path = st.session_state.drill_path

    if not path:
        st.markdown("📍 **Posizione:** Home (Root)")
        return

    # Costruisci breadcrumb
    breadcrumb_parts = ["🏠 Home"]

    for codice in path:
        struct = strutture_df[strutture_df['Codice'] == codice]
        if not struct.empty:
            nome = struct.iloc[0]['DESCRIZIONE']
            breadcrumb_parts.append(nome[:20])

    st.markdown(f"📍 **Posizione:** {' → '.join(breadcrumb_parts)}")

    # Pulsante "Torna Su"
    col1, col2, col3 = st.columns([1, 1, 4])

    with col1:
        if st.button("⬆️ Livello Su", disabled=len(path) == 0):
            st.session_state.drill_path.pop()
            st.rerun()

    with col2:
        if st.button("🏠 Torna a Root", disabled=len(path) == 0):
            st.session_state.drill_path = []
            st.rerun()

def render_root_structures(strutture_df: pd.DataFrame, personale_df: pd.DataFrame):
    """Render strutture root con possibilità di drill-down"""

    root_structures = strutture_df[strutture_df['UNITA\' OPERATIVA PADRE '].isna()]

    if root_structures.empty:
        st.info("Nessuna struttura root trovata")
        return

    st.caption(f"Trovate {len(root_structures)} strutture root")

    # Opzioni visualizzazione
    col1, col2 = st.columns(2)
    with col1:
        show_empty = st.checkbox("📦 Mostra strutture senza dipendenti", value=True, key="root_show_empty")
    with col2:
        show_counts = st.checkbox("📊 Mostra contatori", value=True, key="root_show_counts")

    # Render ogni struttura root come card
    for idx, (_, struct) in enumerate(root_structures.iterrows()):
        render_structure_card(
            struct,
            strutture_df,
            personale_df,
            show_counts=show_counts,
            show_empty=show_empty,
            key_prefix=f"root_{idx}"
        )

def render_child_level(parent_codice: str, strutture_df: pd.DataFrame, personale_df: pd.DataFrame):
    """Render figli di una struttura (sotto-strutture + dipendenti)"""

    # === STATISTICHE STRUTTURA CORRENTE ===
    col1, col2, col3 = st.columns(3)

    # Conta figli diretti
    children_structs = strutture_df[strutture_df['UNITA\' OPERATIVA PADRE '] == parent_codice]
    direct_employees = personale_df[personale_df['Unità Organizzativa'] == parent_codice]

    with col1:
        st.metric("🏢 Sotto-strutture", len(children_structs))
    with col2:
        st.metric("👥 Dipendenti Diretti", len(direct_employees))
    with col3:
        # Conta ricorsivo tutti dipendenti nel sotto-albero
        total_employees = count_employees_recursive(parent_codice, strutture_df, personale_df)
        st.metric("👥 Dipendenti Totali", total_employees)

    # === OPZIONI ===
    col1, col2 = st.columns(2)
    with col1:
        show_empty = st.checkbox("📦 Mostra sotto-strutture vuote", value=True, key=f"child_{parent_codice}_show_empty")
    with col2:
        show_counts = st.checkbox("📊 Mostra contatori", value=True, key=f"child_{parent_codice}_show_counts")

    # === SOTTO-STRUTTURE ===
    if not children_structs.empty:
        st.markdown("#### 🏢 Sotto-Strutture")

        for idx, (_, struct) in enumerate(children_structs.iterrows()):
            render_structure_card(
                struct,
                strutture_df,
                personale_df,
                show_counts=show_counts,
                show_empty=show_empty,
                key_prefix=f"child_{parent_codice}_{idx}"
            )
    else:
        st.info("📭 Nessuna sotto-struttura")

    # === DIPENDENTI DIRETTI ===
    if not direct_employees.empty:
        st.markdown("#### 👥 Dipendenti")
        render_employees_list(direct_employees)
    else:
        st.info("📭 Nessun dipendente diretto")

def render_structure_card(
    struct: pd.Series,
    strutture_df: pd.DataFrame,
    personale_df: pd.DataFrame,
    show_counts: bool = True,
    show_empty: bool = True,
    key_prefix: str = ""
):
    """Render card per una struttura con possibilità di drill-down"""

    codice = struct['Codice']
    nome = struct['DESCRIZIONE']

    # Conta dipendenti e figli
    employees_count = count_employees_recursive(codice, strutture_df, personale_df)
    children_count = len(strutture_df[strutture_df['UNITA\' OPERATIVA PADRE '] == codice])

    # Skip se vuota e filtro attivo
    if not show_empty and employees_count == 0:
        return

    # === CARD STRUTTURA ===
    with st.container():
        # Border e padding
        st.markdown(f"""
        <div style="
            border: 2px solid #3498db;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 10px;
            background-color: #f8f9fa;
        ">
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            st.markdown(f"**🏢 {nome}**")
            st.caption(f"Codice: `{codice}`")

        with col2:
            if show_counts:
                st.markdown(f"👥 **{employees_count}**")
                st.caption("dipendenti")

        with col3:
            if show_counts:
                st.markdown(f"🏢 **{children_count}**")
                st.caption("sotto-strutture")

        # Pulsante drill-down
        if children_count > 0 or employees_count > 0:
            if st.button(
                f"🔍 Esplora {nome[:30]}",
                key=f"{key_prefix}_drill_{codice}",
                use_container_width=True
            ):
                st.session_state.drill_path.append(codice)
                st.rerun()

def render_employees_list(employees_df: pd.DataFrame):
    """Render lista dipendenti con dettagli espandibili"""

    st.caption(f"Totale: {len(employees_df)} dipendenti")

    # Mostra come tabella compatta o expander dettagliati?
    view_mode = st.radio(
        "Vista dipendenti",
        ["Tabella Compatta", "Dettagli Espandibili"],
        horizontal=True,
        key="emp_view_mode"
    )

    if view_mode == "Tabella Compatta":
        # Tabella semplice
        display_df = employees_df[[
            'Titolare', 'TxCodFiscale', 'Codice',
            'Approvatore', 'Controllore', 'Viaggiatore'
        ]].copy()

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )

    else:
        # Expander per ogni dipendente
        for idx, (_, emp) in enumerate(employees_df.iterrows()):
            with st.expander(f"👤 {emp.get('Titolare', 'N/A')} ({emp.get('Codice', 'N/A')})"):
                render_employee_detail(emp)

def render_employee_detail(emp: pd.Series):
    """Render dettagli completi dipendente"""

    col1, col2 = st.columns(2)

    with col1:
        st.text(f"Nome: {emp.get('Titolare', 'N/A')}")
        st.text(f"CF: {emp.get('TxCodFiscale', 'N/A')}")
        st.text(f"Codice: {emp.get('Codice', 'N/A')}")
        st.text(f"UO: {emp.get('Unità Organizzativa', 'N/A')}")
        st.text(f"Sede: {emp.get('Sede_TNS', 'N/A')}")

    with col2:

        # Ruoli principali
        ruoli = []
        if emp.get('Viaggiatore') == 'SÌ':
            ruoli.append("Viaggiatore")
        if emp.get('Approvatore') == 'SÌ':
            ruoli.append("✅ Approvatore")
        if emp.get('Controllore') == 'SÌ':
            ruoli.append("🔍 Controllore")
        if emp.get('Cassiere') == 'SÌ':
            ruoli.append("💰 Cassiere")
        if emp.get('Segretario') == 'SÌ':
            ruoli.append("📝 Segretario")

        if ruoli:
            for ruolo in ruoli:
                st.text(ruolo)
        else:
            st.text("Nessun ruolo assegnato")

def count_employees_recursive(codice: str, strutture_df: pd.DataFrame, personale_df: pd.DataFrame) -> int:
    """Conta dipendenti ricorsivamente (diretti + in sotto-strutture)"""

    # Dipendenti diretti
    direct_count = len(personale_df[personale_df['Unità Organizzativa'] == codice])

    # Dipendenti in sotto-strutture
    children = strutture_df[strutture_df['UNITA\' OPERATIVA PADRE '] == codice]

    children_count = 0
    for _, child in children.iterrows():
        children_count += count_employees_recursive(child['Codice'], strutture_df, personale_df)

    return direct_count + children_count
