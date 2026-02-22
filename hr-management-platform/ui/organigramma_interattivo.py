"""
Organigramma Interattivo con Modal
Visualizzazione gerarchica con nodi colorati (strutture blu, dipendenti verdi)
e modal dettagli al click
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, List, Optional

def show_interactive_organigramma_view(strutture_df: pd.DataFrame, personale_df: pd.DataFrame):
    """
    Vista organigramma interattivo avanzato con:
    - Nodi strutture (blu) e dipendenti (verdi)
    - Click per aprire modal dettagli
    - Navigazione per livelli
    """
    st.markdown("### 📊 Organigramma Interattivo")
    st.caption("Click su nodi per dettagli • 🔵 Strutture  🟢 Dipendenti")

    # === CONTROLS ===
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        max_depth = calculate_max_depth_full(strutture_df, personale_df)
        level_filter = st.slider(
            "📏 Livelli da mostrare",
            min_value=1,
            max_value=max(3, max_depth),
            value=max(3, max_depth),
            help="Limita profondità albero visualizzato"
        )

    with col2:
        show_employees = st.checkbox("👥 Mostra dipendenti", value=True,
                                     help="Includi dipendenti come nodi verdi")

    with col3:
        show_empty_structures = st.checkbox("📦 Mostra strutture vuote", value=False,
                                           help="Includi strutture senza dipendenti")

    with col4:
        layout_orientation = st.selectbox(
            "Layout",
            ["Top-Down", "Left-Right"],
            help="Orientamento grafico"
        )

    # === GENERA GRAFICO ===
    try:
        fig = create_interactive_orgchart(
            strutture_df,
            personale_df,
            max_level=level_filter,
            show_employees=show_employees,
            show_empty_structures=show_empty_structures,
            orientation=layout_orientation
        )

        # Event handler per click
        selection = st.plotly_chart(
            fig,
            use_container_width=True,
            config={'displayModeBar': True},
            key="org_chart",
            on_select="rerun"
        )

        # Info usage
        st.info("💡 **Click su un nodo** per vedere dettagli completi in modal")

        # Processa selezione (se presente)
        if selection and 'selection' in selection and 'points' in selection['selection']:
            points = selection['selection']['points']
            if points:
                # Prendi primo punto selezionato
                point = points[0]
                if 'customdata' in point:
                    node_id = point['customdata']
                    # Determina tipo: se inizia con "struct_" è struttura, altrimenti dipendente
                    if node_id.startswith('struct_'):
                        st.session_state.selected_node_code = node_id.replace('struct_', '')
                        st.session_state.selected_node_type = 'structure'
                    elif node_id.startswith('emp_'):
                        st.session_state.selected_node_code = node_id.replace('emp_', '')
                        st.session_state.selected_node_type = 'employee'

    except Exception as e:
        st.error(f"❌ Errore generazione organigramma: {str(e)}")
        import traceback
        with st.expander("Debug info"):
            st.code(traceback.format_exc())

    # === MODAL DETTAGLI (se nodo selezionato) ===
    if st.session_state.get('selected_node_code'):
        selected_code = st.session_state.selected_node_code
        selected_type = st.session_state.get('selected_node_type', 'structure')

        with st.expander("📋 Dettagli Nodo Selezionato", expanded=True):
            if selected_type == 'structure':
                show_structure_detail(selected_code, strutture_df, personale_df)
            else:
                show_employee_detail(selected_code, personale_df)

            if st.button("❌ Chiudi Dettagli"):
                del st.session_state.selected_node_code
                if 'selected_node_type' in st.session_state:
                    del st.session_state.selected_node_type
                st.rerun()

def calculate_max_depth_full(strutture_df: pd.DataFrame, personale_df: pd.DataFrame) -> int:
    """Calcola profondità massima includendo dipendenti"""
    max_depth = 0
    root_structures = strutture_df[strutture_df['UNITA\' OPERATIVA PADRE '].isna()]

    for _, root in root_structures.iterrows():
        depth = get_depth_recursive_full(root['Codice'], strutture_df, personale_df, 0)
        max_depth = max(max_depth, depth)

    return max_depth

def get_depth_recursive_full(codice: str, strutture_df: pd.DataFrame,
                             personale_df: pd.DataFrame, current_depth: int) -> int:
    """Calcola profondità ricorsiva includendo dipendenti come foglie"""
    # Figli strutture
    children_struct = strutture_df[strutture_df['UNITA\' OPERATIVA PADRE '] == codice]

    # Dipendenti (se presenti, aggiungono 1 livello)
    has_employees = len(personale_df[personale_df['Unità Organizzativa'] == codice]) > 0

    if len(children_struct) == 0:
        return current_depth + (1 if has_employees else 0)

    max_child_depth = current_depth
    for _, child in children_struct.iterrows():
        child_depth = get_depth_recursive_full(child['Codice'], strutture_df, personale_df, current_depth + 1)
        max_child_depth = max(max_child_depth, child_depth)

    # Considera anche dipendenti diretti
    if has_employees:
        max_child_depth = max(max_child_depth, current_depth + 1)

    return max_child_depth

def create_interactive_orgchart(
    strutture_df: pd.DataFrame,
    personale_df: pd.DataFrame,
    max_level: int = 10,
    show_employees: bool = True,
    show_empty_structures: bool = False,
    orientation: str = "Top-Down"
) -> go.Figure:
    """
    Crea organigramma interattivo con Plotly.
    Nodi strutture: blu, Nodi dipendenti: verdi
    """

    # Build graph data
    nodes_data, edges_data = build_interactive_graph(
        strutture_df,
        personale_df,
        max_level=max_level,
        show_employees=show_employees,
        show_empty_structures=show_empty_structures
    )

    if len(nodes_data) == 0:
        # Empty chart
        fig = go.Figure()
        fig.add_annotation(
            text="Nessun nodo da visualizzare con i filtri correnti",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
        return fig

    # Create figure
    fig = go.Figure()

    # Add edges (collegamenti)
    for edge in edges_data:
        fig.add_trace(go.Scatter(
            x=[edge['x0'], edge['x1']],
            y=[edge['y0'], edge['y1']],
            mode='lines',
            line=dict(color='#95a5a6', width=2),
            hoverinfo='skip',
            showlegend=False
        ))

    # Separa nodi strutture e dipendenti
    structure_nodes = [n for n in nodes_data if n['type'] == 'structure']
    employee_nodes = [n for n in nodes_data if n['type'] == 'employee']

    # Add structure nodes (blu)
    if structure_nodes:
        fig.add_trace(go.Scatter(
            x=[n['x'] for n in structure_nodes],
            y=[n['y'] for n in structure_nodes],
            mode='markers+text',
            marker=dict(
                size=[n['size'] for n in structure_nodes],
                color='#3498db',  # Blu
                line=dict(color='white', width=2)
            ),
            text=[n['label'] for n in structure_nodes],
            textposition='top center',
            textfont=dict(size=10, color='#2c3e50'),
            hovertext=[n['hover'] for n in structure_nodes],
            hoverinfo='text',
            customdata=[n['id'] for n in structure_nodes],
            name='Strutture',
            showlegend=True
        ))

    # Add employee nodes (verdi)
    if employee_nodes:
        fig.add_trace(go.Scatter(
            x=[n['x'] for n in employee_nodes],
            y=[n['y'] for n in employee_nodes],
            mode='markers+text',
            marker=dict(
                size=[n['size'] for n in employee_nodes],
                color='#27ae60',  # Verde
                line=dict(color='white', width=2)
            ),
            text=[n['label'] for n in employee_nodes],
            textposition='top center',
            textfont=dict(size=8, color='#2c3e50'),
            hovertext=[n['hover'] for n in employee_nodes],
            hoverinfo='text',
            customdata=[n['id'] for n in employee_nodes],
            name='Dipendenti',
            showlegend=True
        ))

    # Layout
    fig.update_layout(
        title="Organigramma Aziendale Interattivo",
        showlegend=True,
        legend=dict(x=0.01, y=0.99),
        hovermode='closest',
        margin=dict(b=20, l=5, r=5, t=40),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='rgba(250,250,250,1)',
        height=700,
        clickmode='event+select'
    )

    return fig

def build_interactive_graph(
    strutture_df: pd.DataFrame,
    personale_df: pd.DataFrame,
    max_level: int = 10,
    show_employees: bool = True,
    show_empty_structures: bool = False
) -> tuple:
    """
    Costruisce dati grafo per organigramma interattivo.
    Returns: (nodes_data, edges_data)
    """
    nodes_data = []
    edges_data = []

    root_structures = strutture_df[strutture_df['UNITA\' OPERATIVA PADRE '].isna()]

    x_offset = 0
    x_spacing = 3.0

    for _, root in root_structures.iterrows():
        # Check if should show (empty filter)
        if not show_empty_structures:
            from ui.organigramma_view import has_employees_recursive
            if not has_employees_recursive(root['Codice'], strutture_df, personale_df):
                continue

        build_graph_recursive_interactive(
            root,
            strutture_df,
            personale_df,
            nodes_data,
            edges_data,
            x=x_offset,
            y=0,
            level=0,
            max_level=max_level,
            show_employees=show_employees,
            show_empty_structures=show_empty_structures,
            x_spacing=x_spacing
        )
        x_offset += x_spacing * 5

    return nodes_data, edges_data

def build_graph_recursive_interactive(
    structure: pd.Series,
    strutture_df: pd.DataFrame,
    personale_df: pd.DataFrame,
    nodes_data: List[Dict],
    edges_data: List[Dict],
    x: float,
    y: float,
    level: int,
    max_level: int,
    show_employees: bool,
    show_empty_structures: bool,
    x_spacing: float = 2.0
):
    """Costruisce grafo ricorsivamente con strutture e dipendenti"""

    if level > max_level:
        return

    codice = structure['Codice']
    nome = structure.get('DESCRIZIONE', 'N/A')

    # Count employees
    employees = personale_df[personale_df['Unità Organizzativa'] == codice]
    emp_count = len(employees)

    # Add structure node
    node_id = f"struct_{codice}"
    nodes_data.append({
        'id': node_id,
        'type': 'structure',
        'codice': codice,
        'label': nome[:30],
        'x': x,
        'y': y,
        'size': max(20, min(60, 30 + emp_count * 2)),
        'hover': f"<b>{nome}</b><br>Codice: {codice}<br>Dipendenti: {emp_count}<br>Livello: {level}"
    })

    # Add employee nodes if requested
    if show_employees and emp_count > 0 and level < max_level:
        emp_y = y - 1.0
        emp_x_start = x - (emp_count - 1) * 0.3 / 2

        for i, (_, emp) in enumerate(employees.iterrows()):
            emp_id = f"emp_{emp.get('TxCodFiscale', f'unknown_{i}')}"
            emp_name = emp.get('Titolare', 'N/A')
            emp_x = emp_x_start + i * 0.3

            nodes_data.append({
                'id': emp_id,
                'type': 'employee',
                'codice': emp.get('TxCodFiscale', ''),
                'label': emp_name[:20] if len(employees) < 10 else '',  # Hide labels if too many
                'x': emp_x,
                'y': emp_y,
                'size': 15,
                'hover': f"<b>{emp_name}</b><br>CF: {emp.get('TxCodFiscale', 'N/A')}<br>Ruolo: {emp.get('Approvatore', 'N/A')}"
            })

            # Edge structure -> employee
            edges_data.append({
                'x0': x, 'y0': y,
                'x1': emp_x, 'y1': emp_y
            })

    # Children structures
    children = strutture_df[strutture_df['UNITA\' OPERATIVA PADRE '] == codice]

    # Filter empty if needed
    if not show_empty_structures:
        from ui.organigramma_view import has_employees_recursive
        children_filtered = []
        for _, child in children.iterrows():
            if has_employees_recursive(child['Codice'], strutture_df, personale_df):
                children_filtered.append(child)
        children = pd.DataFrame(children_filtered)

    num_children = len(children)

    if num_children == 0:
        return

    # Position children
    child_y = y - 2.0
    child_x_start = x - (num_children - 1) * x_spacing / 2

    for i, (_, child) in enumerate(children.iterrows()):
        child_x = child_x_start + i * x_spacing

        # Edge parent -> child
        edges_data.append({
            'x0': x, 'y0': y,
            'x1': child_x, 'y1': child_y
        })

        # Recursive
        build_graph_recursive_interactive(
            child,
            strutture_df,
            personale_df,
            nodes_data,
            edges_data,
            x=child_x,
            y=child_y,
            level=level + 1,
            max_level=max_level,
            show_employees=show_employees,
            show_empty_structures=show_empty_structures,
            x_spacing=x_spacing
        )

def show_node_detail_modal(
    node_id: str,
    strutture_df: pd.DataFrame,
    personale_df: pd.DataFrame
):
    """Mostra modal con dettagli nodo selezionato"""

    # Parse node type
    if node_id.startswith('struct_'):
        show_structure_detail(node_id.replace('struct_', ''), strutture_df, personale_df)
    elif node_id.startswith('emp_'):
        show_employee_detail(node_id.replace('emp_', ''), personale_df)
    else:
        st.error(f"Nodo sconosciuto: {node_id}")

    # Close button
    if st.button("❌ Chiudi", use_container_width=True):
        del st.session_state.selected_node_id
        st.rerun()

def show_structure_detail(codice: str, strutture_df: pd.DataFrame, personale_df: pd.DataFrame):
    """Mostra dettagli struttura in modal"""

    structure = strutture_df[strutture_df['Codice'] == codice]

    if len(structure) == 0:
        st.error(f"Struttura {codice} non trovata")
        return

    structure = structure.iloc[0]

    st.caption(f"Codice: {codice}")

    # Tabs
    tab1, tab2, tab3 = st.tabs(["📋 Info Generali", "👥 Dipendenti", "🌳 Gerarchia"])

    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            st.text(f"Codice: {structure.get('Codice', 'N/A')}")
            st.text(f"Descrizione: {structure.get('DESCRIZIONE', 'N/A')}")
            st.text(f"UO: {structure.get('Unità Organizzativa', 'N/A')}")
            st.text(f"CDC: {structure.get('CDCCOSTO', 'N/A')}")

        with col2:
            padre = structure.get('UNITA\' OPERATIVA PADRE ', 'N/A')
            st.text(f"Padre: {padre if padre else 'ROOT'}")
            st.text(f"Livello: {structure.get('LIVELLO', 'N/A')}")

            # Count children
            children_count = len(strutture_df[strutture_df['UNITA\' OPERATIVA PADRE '] == codice])
            st.text(f"Figli: {children_count}")

    with tab2:
        employees = personale_df[personale_df['Unità Organizzativa'] == codice]

        if len(employees) == 0:
            st.info("Nessun dipendente assegnato a questa struttura")
        else:
            st.metric("Totale Dipendenti", len(employees))

            st.dataframe(
                employees[['Titolare', 'TxCodFiscale', 'Approvatore', 'Controllore', 'Viaggiatore']],
                use_container_width=True,
                hide_index=True
            )

    with tab3:

        # Breadcrumb path to root
        path = build_hierarchy_path(codice, strutture_df)
        st.markdown(" → ".join(path))

        # Direct children
        children = strutture_df[strutture_df['UNITA\' OPERATIVA PADRE '] == codice]
        if len(children) > 0:
            for _, child in children.iterrows():
                st.markdown(f"- {child['DESCRIZIONE']} ({child['Codice']})")

def show_employee_detail(cf: str, personale_df: pd.DataFrame):
    """Mostra dettagli dipendente in modal"""

    employee = personale_df[personale_df['TxCodFiscale'] == cf]

    if len(employee) == 0:
        st.error(f"Dipendente {cf} non trovato")
        return

    employee = employee.iloc[0]

    st.caption(f"CF: {cf}")

    # Tabs
    tab1, tab2 = st.tabs(["📋 Dati Anagrafici", "🎭 Ruoli & Permessi"])

    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            st.text(f"Nome: {employee.get('Titolare', 'N/A')}")
            st.text(f"CF: {employee.get('TxCodFiscale', 'N/A')}")
            st.text(f"Codice: {employee.get('Codice', 'N/A')}")

        with col2:
            st.text(f"UO: {employee.get('Unità Organizzativa', 'N/A')}")
            st.text(f"Sede: {employee.get('Sede_TNS', 'N/A')}")
            st.text(f"Gruppo: {employee.get('GruppoSind', 'N/A')}")

    with tab2:

        roles = {
            'Viaggiatore': employee.get('Viaggiatore', ''),
            'Approvatore': employee.get('Approvatore', ''),
            'Controllore': employee.get('Controllore', ''),
            'Cassiere': employee.get('Cassiere', ''),
            'Segretario': employee.get('Segretario', ''),
            'Visualizzatori': employee.get('Visualizzatori', ''),
            'Amministrazione': employee.get('Amministrazione', '')
        }

        for role, value in roles.items():
            icon = "✅" if value == "SÌ" else "❌"
            st.markdown(f"{icon} **{role}**: {value if value else 'NO'}")

def build_hierarchy_path(codice: str, strutture_df: pd.DataFrame) -> List[str]:
    """Costruisce path gerarchico da struttura a root"""
    path = []
    current = codice

    while current:
        structure = strutture_df[strutture_df['Codice'] == current]
        if len(structure) == 0:
            break

        structure = structure.iloc[0]
        path.insert(0, structure.get('DESCRIZIONE', current))

        parent = structure.get('UNITA\' OPERATIVA PADRE ', None)
        if not parent or pd.isna(parent):
            break
        current = parent

    return path if path else [codice]
