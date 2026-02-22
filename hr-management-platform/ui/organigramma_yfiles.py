"""
Organigramma Interattivo stile yFiles con Cytoscape.js
Layout gerarchico professionale con nodi styled, zoom, pan, click events
"""
import streamlit as st
import pandas as pd
import json
from typing import List, Dict, Tuple
import streamlit.components.v1 as components

def show_yfiles_organigramma(strutture_df: pd.DataFrame, personale_df: pd.DataFrame):
    """Vista organigramma stile yFiles con Cytoscape.js"""

    st.markdown("### 🎯 Organigramma Interattivo")
    st.caption("Zoom con rotella mouse • Pan con drag • Click su nodi per dettagli • Doppio-click per espandere/collassare")

    # === CONTROLS ===
    col1, col2, col3 = st.columns(3)

    with col1:
        max_depth = st.slider("📏 Livelli da mostrare", 1, 10, 3, key="yfiles_depth")

    with col2:
        show_employees = st.checkbox("👥 Mostra dipendenti", value=True, key="yfiles_employees")

    with col3:
        layout_direction = st.selectbox(
            "Direzione",
            ["Top-Down", "Left-Right"],
            key="yfiles_direction"
        )

    # === BUILD GRAPH DATA ===
    nodes, edges = build_cytoscape_data(
        strutture_df,
        personale_df,
        max_depth=max_depth,
        show_employees=show_employees
    )

    if not nodes:
        st.warning("Nessun nodo da visualizzare con i filtri correnti")
        return

    # === RENDER CYTOSCAPE ===
    render_cytoscape_graph(
        nodes,
        edges,
        layout_direction=layout_direction,
        height=700
    )

    # === DETTAGLI NODO SELEZIONATO ===
    if st.session_state.get('selected_yfiles_node'):
        show_node_details(
            st.session_state.selected_yfiles_node,
            strutture_df,
            personale_df
        )

def build_cytoscape_data(
    strutture_df: pd.DataFrame,
    personale_df: pd.DataFrame,
    max_depth: int = 10,
    show_employees: bool = True
) -> Tuple[List[Dict], List[Dict]]:
    """Costruisce dati per Cytoscape (nodi ed edges)"""

    nodes = []
    edges = []

    # Trova root structures
    root_structures = strutture_df[strutture_df['UNITA\' OPERATIVA PADRE '].isna()]

    for _, root in root_structures.iterrows():
        build_graph_recursive(
            root['Codice'],
            strutture_df,
            personale_df,
            nodes,
            edges,
            level=0,
            max_depth=max_depth,
            show_employees=show_employees
        )

    return nodes, edges

def build_graph_recursive(
    codice: str,
    strutture_df: pd.DataFrame,
    personale_df: pd.DataFrame,
    nodes: List[Dict],
    edges: List[Dict],
    level: int,
    max_depth: int,
    show_employees: bool
):
    """Costruisce grafo ricorsivamente"""

    if level > max_depth:
        return

    # Get structure info
    struct = strutture_df[strutture_df['Codice'] == codice]
    if struct.empty:
        return

    struct = struct.iloc[0]
    nome = struct.get('DESCRIZIONE', 'N/A')

    # Count employees
    employees = personale_df[personale_df['Unità Organizzativa'] == codice]
    emp_count = len(employees)

    # Count children
    children = strutture_df[strutture_df['UNITA\' OPERATIVA PADRE '] == codice]
    children_count = len(children)

    # Add structure node
    nodes.append({
        'data': {
            'id': f'struct_{codice}',
            'label': nome,
            'type': 'structure',
            'codice': codice,
            'emp_count': emp_count,
            'children_count': children_count,
            'level': level
        }
    })

    # Add employees if requested
    if show_employees and emp_count > 0 and level < max_depth:
        for idx, (_, emp) in enumerate(employees.iterrows()):
            cf = emp.get('TxCodFiscale', f'unknown_{idx}')
            nome_emp = emp.get('Titolare', 'N/A')
            ruolo = get_primary_role(emp)

            emp_node_id = f'emp_{cf}'

            nodes.append({
                'data': {
                    'id': emp_node_id,
                    'label': nome_emp,
                    'type': 'employee',
                    'cf': cf,
                    'codice': emp.get('Codice', 'N/A'),
                    'ruolo': ruolo,
                    'level': level + 1
                }
            })

            # Edge structure -> employee
            edges.append({
                'data': {
                    'source': f'struct_{codice}',
                    'target': emp_node_id
                }
            })

    # Recursively add children structures
    for _, child in children.iterrows():
        child_codice = child['Codice']

        # Edge parent -> child
        edges.append({
            'data': {
                'source': f'struct_{codice}',
                'target': f'struct_{child_codice}'
            }
        })

        # Recurse
        build_graph_recursive(
            child_codice,
            strutture_df,
            personale_df,
            nodes,
            edges,
            level + 1,
            max_depth,
            show_employees
        )

def get_primary_role(emp: pd.Series) -> str:
    """Determina ruolo primario dipendente"""
    if emp.get('Approvatore') == 'SÌ':
        return 'Approvatore'
    elif emp.get('Controllore') == 'SÌ':
        return 'Controllore'
    elif emp.get('Cassiere') == 'SÌ':
        return 'Cassiere'
    elif emp.get('Segretario') == 'SÌ':
        return 'Segretario'
    elif emp.get('Viaggiatore') == 'SÌ':
        return 'Viaggiatore'
    else:
        return 'N/A'

def render_cytoscape_graph(
    nodes: List[Dict],
    edges: List[Dict],
    layout_direction: str = "Top-Down",
    height: int = 700
):
    """Render Cytoscape.js graph embedded in Streamlit"""

    # Convert to JSON
    elements_json = json.dumps(nodes + edges)

    # Determine layout direction
    if layout_direction == "Top-Down":
        rankDir = "TB"
    else:
        rankDir = "LR"

    # HTML with Cytoscape.js
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.26.0/cytoscape.min.js"></script>
        <script src="https://unpkg.com/dagre@0.8.5/dist/dagre.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/cytoscape-dagre@2.5.0/cytoscape-dagre.min.js"></script>
        <style>
            body {{
                margin: 0;
                padding: 0;
                overflow: hidden;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }}
            #cy {{
                width: 100%;
                height: {height}px;
                background: #f8f9fa;
            }}
            .info-box {{
                position: absolute;
                bottom: 10px;
                left: 10px;
                background: white;
                padding: 10px 15px;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                font-size: 12px;
                z-index: 1000;
            }}
        </style>
    </head>
    <body>
        <div id="cy"></div>
        <div class="info-box">
            🖱️ Zoom: rotella mouse • Pan: drag background • Click: dettagli nodo
        </div>

        <script>
            const elements = {elements_json};

            const cy = cytoscape({{
                container: document.getElementById('cy'),
                elements: elements,

                style: [
                    // Structure nodes (blue cards)
                    {{
                        selector: 'node[type="structure"]',
                        style: {{
                            'label': 'data(label)',
                            'background-color': '#3498db',
                            'background-opacity': 1,
                            'border-width': 3,
                            'border-color': '#2980b9',
                            'color': '#fff',
                            'text-valign': 'center',
                            'text-halign': 'center',
                            'font-size': '12px',
                            'font-weight': 'bold',
                            'width': 'label',
                            'height': 'label',
                            'padding': '15px',
                            'shape': 'round-rectangle',
                            'text-wrap': 'wrap',
                            'text-max-width': '120px'
                        }}
                    }},

                    // Employee nodes (green cards)
                    {{
                        selector: 'node[type="employee"]',
                        style: {{
                            'label': 'data(label)',
                            'background-color': '#27ae60',
                            'background-opacity': 1,
                            'border-width': 2,
                            'border-color': '#229954',
                            'color': '#fff',
                            'text-valign': 'center',
                            'text-halign': 'center',
                            'font-size': '10px',
                            'width': 'label',
                            'height': 'label',
                            'padding': '10px',
                            'shape': 'round-rectangle',
                            'text-wrap': 'wrap',
                            'text-max-width': '100px'
                        }}
                    }},

                    // Edges
                    {{
                        selector: 'edge',
                        style: {{
                            'width': 2,
                            'line-color': '#95a5a6',
                            'target-arrow-color': '#95a5a6',
                            'target-arrow-shape': 'triangle',
                            'curve-style': 'bezier',
                            'arrow-scale': 1.5
                        }}
                    }},

                    // Hover effects
                    {{
                        selector: 'node:active',
                        style: {{
                            'overlay-color': '#e74c3c',
                            'overlay-padding': 10,
                            'overlay-opacity': 0.25
                        }}
                    }},

                    // Selected node
                    {{
                        selector: 'node:selected',
                        style: {{
                            'border-width': 5,
                            'border-color': '#e74c3c'
                        }}
                    }}
                ],

                layout: {{
                    name: 'dagre',
                    rankDir: '{rankDir}',
                    nodeSep: 80,
                    rankSep: 100,
                    padding: 50,
                    animate: true,
                    animationDuration: 500
                }},

                minZoom: 0.3,
                maxZoom: 3,
                wheelSensitivity: 0.2
            }});

            // Click handler
            cy.on('tap', 'node', function(evt) {{
                const node = evt.target;
                const nodeData = node.data();

                // Send to Streamlit (via window message)
                window.parent.postMessage({{
                    type: 'streamlit:setComponentValue',
                    data: {{
                        nodeId: nodeData.id,
                        nodeType: nodeData.type,
                        nodeData: nodeData
                    }}
                }}, '*');
            }});

            // Fit graph on load
            cy.fit();
            cy.center();

            // Double-click to fit
            cy.on('dbltap', function() {{
                cy.fit();
                cy.center();
            }});
        </script>
    </body>
    </html>
    """

    # Render with components
    result = components.html(html_code, height=height + 50, scrolling=False)

    # Handle node selection (if component returns data)
    if result:
        st.session_state.selected_yfiles_node = result

def show_node_details(
    node_data: Dict,
    strutture_df: pd.DataFrame,
    personale_df: pd.DataFrame
):
    """Mostra dettagli nodo selezionato"""

    with st.expander("📋 Dettagli Nodo Selezionato", expanded=True):
        node_type = node_data.get('nodeType', 'unknown')

        if node_type == 'structure':
            # Structure details
            codice = node_data['nodeData']['codice']
            struct = strutture_df[strutture_df['Codice'] == codice]

            if not struct.empty:
                struct = struct.iloc[0]

                col1, col2 = st.columns(2)

                with col1:
                    st.text(f"Nome: {struct.get('DESCRIZIONE', 'N/A')}")
                    st.text(f"Codice: {struct.get('Codice', 'N/A')}")
                    st.text(f"UO: {struct.get('Unità Organizzativa', 'N/A')}")

                    parent = struct.get('UNITA\' OPERATIVA PADRE ')
                    if pd.notna(parent):
                        st.text(f"Padre: {parent}")
                    else:
                        st.text("Padre: ROOT")

                with col2:
                    emp_count = node_data['nodeData'].get('emp_count', 0)
                    children_count = node_data['nodeData'].get('children_count', 0)

                    st.metric("👥 Dipendenti", emp_count)
                    st.metric("🏢 Sotto-strutture", children_count)

        elif node_type == 'employee':
            # Employee details
            cf = node_data['nodeData'].get('cf', '')
            emp = personale_df[personale_df['TxCodFiscale'] == cf]

            if not emp.empty:
                emp = emp.iloc[0]

                col1, col2 = st.columns(2)

                with col1:
                    st.text(f"Nome: {emp.get('Titolare', 'N/A')}")
                    st.text(f"CF: {emp.get('TxCodFiscale', 'N/A')}")
                    st.text(f"Codice: {emp.get('Codice', 'N/A')}")
                    st.text(f"UO: {emp.get('Unità Organizzativa', 'N/A')}")
                    st.text(f"Sede: {emp.get('Sede_TNS', 'N/A')}")

                with col2:

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

        # Close button
        if st.button("❌ Chiudi Dettagli"):
            del st.session_state.selected_yfiles_node
            st.rerun()
