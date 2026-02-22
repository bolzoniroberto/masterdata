"""
Vista Organigramma - Visualizzazione alto livello della struttura organizzativa
Due modalità: Vista Albero (testuale) e Vista Grafico (visuale interattivo)
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, List, Tuple

def show_organigramma_view():
    """Vista dedicata all'organigramma aziendale"""

    st.caption("Visualizza la struttura organizzativa in modalità albero o grafico interattivo")

    if not st.session_state.data_loaded:
        st.warning("⚠️ Carica dati per visualizzare l'organigramma")
        return

    # Get dataframes with safety check
    strutture_df = st.session_state.get('strutture_df')
    personale_df = st.session_state.get('personale_df')

    if strutture_df is None or personale_df is None:
        st.warning("⚠️ Nessun dato disponibile. Importa un file Excel per iniziare.")
        return

    # === STATISTICHE RAPIDE ===
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("📊 Totale Strutture", len(strutture_df))

    with col2:
        roots = strutture_df['UNITA\' OPERATIVA PADRE '].isna().sum()
        st.metric("🌳 Strutture Root", roots)

    with col3:
        # Conta dipendenti per struttura
        if 'Unità Organizzativa' in personale_df.columns:
            total_deps = len(personale_df)
            st.metric("👥 Totale Dipendenti", total_deps)
        else:
            st.metric("👥 Totale Dipendenti", 0)

    with col4:
        # Profondità massima albero
        max_depth = calculate_max_depth(strutture_df)
        st.metric("📏 Livelli Gerarchia", max_depth)

    # === TAB: VISTA ALBERO VS DRILL-DOWN VS YFILES-STYLE ===
    tab1, tab2, tab3 = st.tabs([
        "🌳 Vista Albero Completa",
        "🔍 Esplora Interattivo",
        "🎯 Organigramma Grafico"
    ])

    with tab1:
        show_tree_view(strutture_df, personale_df)

    with tab2:
        show_drilldown_view(strutture_df, personale_df)

    with tab3:
        show_yfiles_view(strutture_df, personale_df)

def show_tree_view(strutture_df: pd.DataFrame, personale_df: pd.DataFrame):
    """Vista albero testuale con indent gerarchico"""

    st.markdown("### 🌳 Vista Albero Gerarchica")
    st.caption("Struttura organizzativa con indentazione per livelli gerarchici")

    # === OPZIONI VISUALIZZAZIONE ===
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        show_counts = st.checkbox("📊 Mostra contatori dipendenti", value=True)

    with col2:
        show_codes = st.checkbox("🔢 Mostra codici", value=False)

    with col3:
        compact_mode = st.checkbox("📦 Modalità compatta", value=False)

    with col4:
        hide_empty = st.checkbox("🚫 Nascondi senza dipendenti", value=False,
                                 help="Nascondi strutture che non hanno dipendenti associati")

    # === RICERCA ===
    search_text = st.text_input(
        "🔍 Cerca struttura",
        placeholder="Cerca per nome o codice...",
        help="Filtra strutture per nome o codice"
    )

    # === COSTRUISCI ALBERO ===
    root_structures = strutture_df[strutture_df['UNITA\' OPERATIVA PADRE '].isna()]

    if len(root_structures) == 0:
        st.warning("⚠️ Nessuna struttura root trovata nel database")
        return

    # Container per albero
    tree_container = st.container()

    with tree_container:
        for idx, root in root_structures.iterrows():
            # Filtra se c'è ricerca
            if search_text:
                if not matches_search(root, search_text):
                    continue

            # Filtra se hide_empty e nessun dipendente (ricorsivo)
            if hide_empty and not has_employees_recursive(root['Codice'], strutture_df, personale_df):
                continue

            render_tree_node(
                root,
                strutture_df,
                personale_df,
                level=0,
                show_counts=show_counts,
                show_codes=show_codes,
                compact_mode=compact_mode,
                search_text=search_text,
                hide_empty=hide_empty
            )

def show_drilldown_view(strutture_df: pd.DataFrame, personale_df: pd.DataFrame):
    """Vista drill-down interattiva per esplorare livello per livello"""
    from ui.organigramma_drilldown import show_organigramma_drilldown

    # Delega alla vista drill-down
    show_organigramma_drilldown(strutture_df, personale_df)

def show_yfiles_view(strutture_df: pd.DataFrame, personale_df: pd.DataFrame):
    """Vista organigramma stile yFiles con Cytoscape.js"""
    from ui.organigramma_yfiles import show_yfiles_organigramma

    # Delega alla vista yFiles-style
    show_yfiles_organigramma(strutture_df, personale_df)

def show_chart_view(strutture_df: pd.DataFrame, personale_df: pd.DataFrame):
    """Vista grafico interattivo (org chart)"""

    st.markdown("### 📊 Organigramma Interattivo")
    st.caption("Grafico gerarchico con nodi cliccabili")

    # === OPZIONI CHART ===
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        layout_type = st.selectbox(
            "Layout",
            ["Verticale", "Orizzontale", "Radiale"],
            help="Orientamento del grafico"
        )

    with col2:
        show_labels = st.checkbox("🏷️ Mostra etichette", value=True)

    with col3:
        color_by = st.selectbox(
            "Colora per",
            ["Livello", "Dipendenti", "Uniforme"],
            help="Schema colori nodi"
        )

    with col4:
        hide_empty_chart = st.checkbox("🚫 Nascondi senza dipendenti", value=False,
                                       help="Nascondi strutture senza dipendenti dal grafico")

    # === GENERA GRAFICO ===
    try:
        fig = create_org_chart(
            strutture_df,
            personale_df,
            layout=layout_type,
            show_labels=show_labels,
            color_by=color_by,
            hide_empty=hide_empty_chart
        )

        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True})

        # Info interattività
        st.info("💡 **Interattività**: Hover sui nodi per dettagli, zoom con scroll, pan con drag")

    except Exception as e:
        st.error(f"❌ Errore generazione grafico: {str(e)}")
        st.code(str(e))

# === FUNZIONI HELPER ===

def calculate_max_depth(strutture_df: pd.DataFrame) -> int:
    """Calcola profondità massima albero gerarchico"""
    max_depth = 0
    root_structures = strutture_df[strutture_df['UNITA\' OPERATIVA PADRE '].isna()]

    for _, root in root_structures.iterrows():
        depth = get_depth_recursive(root['Codice'], strutture_df, 0)
        max_depth = max(max_depth, depth)

    return max_depth

def get_depth_recursive(codice: str, strutture_df: pd.DataFrame, current_depth: int) -> int:
    """Calcola profondità ricorsiva di un nodo"""
    children = strutture_df[strutture_df['UNITA\' OPERATIVA PADRE '] == codice]

    if len(children) == 0:
        return current_depth

    max_child_depth = current_depth
    for _, child in children.iterrows():
        child_depth = get_depth_recursive(child['Codice'], strutture_df, current_depth + 1)
        max_child_depth = max(max_child_depth, child_depth)

    return max_child_depth

def matches_search(structure: pd.Series, search_text: str) -> bool:
    """Verifica se struttura matcha ricerca"""
    search_lower = search_text.lower()
    descrizione = str(structure.get('DESCRIZIONE', '')).lower()
    codice = str(structure.get('Codice', '')).lower()

    return search_lower in descrizione or search_lower in codice

def count_employees(struttura_codice: str, personale_df: pd.DataFrame) -> int:
    """Conta dipendenti in una struttura"""
    if 'Unità Organizzativa' not in personale_df.columns:
        return 0

    return len(personale_df[personale_df['Unità Organizzativa'] == struttura_codice])

def has_employees_recursive(struttura_codice: str, strutture_df: pd.DataFrame, personale_df: pd.DataFrame) -> bool:
    """
    Verifica se una struttura ha dipendenti (direttamente o nei figli).
    Ricorsivo per includere tutta la gerarchia sotto.
    """
    # Check diretto
    if count_employees(struttura_codice, personale_df) > 0:
        return True

    # Check figli ricorsivamente
    children = strutture_df[strutture_df['UNITA\' OPERATIVA PADRE '] == struttura_codice]
    for _, child in children.iterrows():
        if has_employees_recursive(child['Codice'], strutture_df, personale_df):
            return True

    return False

def render_tree_node(
    structure: pd.Series,
    strutture_df: pd.DataFrame,
    personale_df: pd.DataFrame,
    level: int = 0,
    show_counts: bool = True,
    show_codes: bool = False,
    compact_mode: bool = False,
    search_text: str = "",
    hide_empty: bool = False
):
    """Renderizza un nodo dell'albero con indentazione"""

    # Indentazione per livello
    indent = "    " * level
    icon = "📁" if level == 0 else "📂"

    # Nome struttura
    nome = structure.get('DESCRIZIONE', 'N/A')
    codice = structure.get('Codice', 'N/A')

    # Contatore dipendenti
    emp_count = count_employees(codice, personale_df) if show_counts else 0

    # Costruisci label
    label_parts = [f"{icon} **{nome}**"]

    if show_codes:
        label_parts.append(f"`{codice}`")

    if show_counts:
        if emp_count > 0:
            label_parts.append(f"👥 {emp_count}")

    label = " · ".join(label_parts)

    # Highlight se match ricerca
    if search_text and matches_search(structure, search_text):
        label = f"🔍 {label}"

    # Renderizza nodo
    if compact_mode:
        st.markdown(f"{indent}{label}")
    else:
        with st.container():
            st.markdown(f"{indent}{label}")

    # Figli ricorsivi
    children = strutture_df[strutture_df['UNITA\' OPERATIVA PADRE '] == codice]

    for _, child in children.iterrows():
        # Filtra figli senza dipendenti se hide_empty attivo
        if hide_empty and not has_employees_recursive(child['Codice'], strutture_df, personale_df):
            continue

        render_tree_node(
            child,
            strutture_df,
            personale_df,
            level=level + 1,
            show_counts=show_counts,
            show_codes=show_codes,
            compact_mode=compact_mode,
            search_text=search_text,
            hide_empty=hide_empty
        )

def create_org_chart(
    strutture_df: pd.DataFrame,
    personale_df: pd.DataFrame,
    layout: str = "Verticale",
    show_labels: bool = True,
    color_by: str = "Livello",
    hide_empty: bool = False
) -> go.Figure:
    """Crea grafico organigramma con Plotly"""

    # Costruisci struttura grafo
    nodes_data = build_graph_data(strutture_df, personale_df, color_by, hide_empty)

    # Crea figure
    fig = go.Figure()

    # Aggiungi edges (collegamenti)
    edge_traces = create_edge_traces(nodes_data, layout)
    for trace in edge_traces:
        fig.add_trace(trace)

    # Aggiungi nodes
    node_trace = create_node_trace(nodes_data, layout, show_labels, color_by)
    fig.add_trace(node_trace)

    # Layout
    fig.update_layout(
        title="Organigramma Aziendale",
        showlegend=False,
        hovermode='closest',
        margin=dict(b=20, l=5, r=5, t=40),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='rgba(0,0,0,0)',
        height=600
    )

    return fig

def build_graph_data(
    strutture_df: pd.DataFrame,
    personale_df: pd.DataFrame,
    color_by: str,
    hide_empty: bool = False
) -> List[Dict]:
    """Costruisce dati grafo con posizioni e attributi"""

    nodes_data = []
    root_structures = strutture_df[strutture_df['UNITA\' OPERATIVA PADRE '].isna()]

    # Posizionamento: layout ad albero semplificato
    x_spacing = 1.5
    y_spacing = 1.0

    for root_idx, root in root_structures.iterrows():
        # Filtra root senza dipendenti se hide_empty
        if hide_empty and not has_employees_recursive(root['Codice'], strutture_df, personale_df):
            continue

        x_offset = root_idx * x_spacing * 3
        build_graph_recursive(
            root,
            strutture_df,
            personale_df,
            nodes_data,
            x=x_offset,
            y=0,
            level=0,
            color_by=color_by,
            x_spacing=x_spacing,
            y_spacing=y_spacing,
            hide_empty=hide_empty
        )

    return nodes_data

def build_graph_recursive(
    structure: pd.Series,
    strutture_df: pd.DataFrame,
    personale_df: pd.DataFrame,
    nodes_data: List[Dict],
    x: float,
    y: float,
    level: int,
    color_by: str,
    x_spacing: float,
    y_spacing: float,
    hide_empty: bool = False
):
    """Costruisce grafo ricorsivamente"""

    codice = structure['Codice']
    nome = structure.get('DESCRIZIONE', 'N/A')
    emp_count = count_employees(codice, personale_df)

    # Determina colore
    if color_by == "Livello":
        color_value = level
    elif color_by == "Dipendenti":
        color_value = emp_count
    else:
        color_value = 0

    # Aggiungi nodo
    node = {
        'codice': codice,
        'nome': nome,
        'emp_count': emp_count,
        'x': x,
        'y': y,
        'level': level,
        'color_value': color_value,
        'parent': structure.get('UNITA\' OPERATIVA PADRE ', None)
    }
    nodes_data.append(node)

    # Figli (filtra se hide_empty)
    children = strutture_df[strutture_df['UNITA\' OPERATIVA PADRE '] == codice]

    # Filtra figli senza dipendenti se hide_empty
    if hide_empty:
        children_filtered = []
        for _, child in children.iterrows():
            if has_employees_recursive(child['Codice'], strutture_df, personale_df):
                children_filtered.append(child)
        children = pd.DataFrame(children_filtered)

    num_children = len(children)

    if num_children == 0:
        return

    # Posiziona figli in orizzontale
    child_x_start = x - (num_children - 1) * x_spacing / 2

    for i, (_, child) in enumerate(children.iterrows()):
        child_x = child_x_start + i * x_spacing
        child_y = y - y_spacing

        build_graph_recursive(
            child,
            strutture_df,
            personale_df,
            nodes_data,
            x=child_x,
            y=child_y,
            level=level + 1,
            color_by=color_by,
            x_spacing=x_spacing,
            y_spacing=y_spacing,
            hide_empty=hide_empty
        )

def create_edge_traces(nodes_data: List[Dict], layout: str) -> List[go.Scatter]:
    """Crea tracce per collegamenti tra nodi"""

    edge_traces = []

    # Mappa codice -> nodo
    node_map = {node['codice']: node for node in nodes_data}

    for node in nodes_data:
        if node['parent'] and node['parent'] in node_map:
            parent = node_map[node['parent']]

            # Coordinate edge
            x_coords = [parent['x'], node['x'], None]
            y_coords = [parent['y'], node['y'], None]

            edge_trace = go.Scatter(
                x=x_coords,
                y=y_coords,
                mode='lines',
                line=dict(width=1, color='#888'),
                hoverinfo='none',
                showlegend=False
            )
            edge_traces.append(edge_trace)

    return edge_traces

def create_node_trace(
    nodes_data: List[Dict],
    layout: str,
    show_labels: bool,
    color_by: str
) -> go.Scatter:
    """Crea traccia per nodi"""

    x_coords = [node['x'] for node in nodes_data]
    y_coords = [node['y'] for node in nodes_data]

    # Hover text
    hover_texts = [
        f"<b>{node['nome']}</b><br>" +
        f"Codice: {node['codice']}<br>" +
        f"Dipendenti: {node['emp_count']}<br>" +
        f"Livello: {node['level']}"
        for node in nodes_data
    ]

    # Dimensione nodi basata su dipendenti
    marker_sizes = [max(10, min(50, node['emp_count'] * 2 + 10)) for node in nodes_data]

    # Colori
    if color_by == "Livello":
        colors = [node['level'] for node in nodes_data]
        colorscale = 'Viridis'
    elif color_by == "Dipendenti":
        colors = [node['emp_count'] for node in nodes_data]
        colorscale = 'Blues'
    else:
        colors = ['lightblue'] * len(nodes_data)
        colorscale = None

    # Testo labels
    text_labels = [node['nome'][:20] for node in nodes_data] if show_labels else None

    node_trace = go.Scatter(
        x=x_coords,
        y=y_coords,
        mode='markers+text' if show_labels else 'markers',
        text=text_labels,
        textposition="top center",
        textfont=dict(size=8),
        hovertext=hover_texts,
        hoverinfo='text',
        marker=dict(
            size=marker_sizes,
            color=colors,
            colorscale=colorscale,
            showscale=color_by != "Uniforme",
            colorbar=dict(
                title="Livello" if color_by == "Livello" else "Dipendenti",
                thickness=15,
                len=0.7
            ),
            line=dict(width=2, color='white')
        ),
        showlegend=False
    )

    return node_trace
