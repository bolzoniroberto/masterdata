"""
Orgchart HR Hierarchy View - Multi-Layout

Interactive organizational chart showing HR hierarchy.
Supports 6 JS-side layouts (no Streamlit rerun):
  H - Albero Orizzontale (LR tree)
  V - Albero Verticale   (top-down tree)
  S - Sunburst           (radial partition)
  T - Treemap            (squarified rectangles)
  P - Pannelli           (Finder-style columns)
  C - Card Grid          (OrgVue-style cards)
"""
import streamlit as st
import streamlit.components.v1 as components
import json
from typing import Optional

from services.orgchart_data_service import get_orgchart_data_service
from services.lookup_service import get_lookup_service


def render_orgchart_hr_view():
    """Render HR Hierarchy orgchart view with multi-layout switcher"""

    orgchart_service = get_orgchart_data_service()
    lookup_service = get_lookup_service()

    # ========== FILTERS & SEARCH ==========
    col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])

    with col1:
        search_query = st.text_input(
            "🔍 Cerca struttura",
            placeholder="Nome struttura…",
            key="org_hr_search"
        )

    with col2:
        companies = lookup_service.get_company_names()
        company_filter = st.selectbox(
            "Società", options=["Tutte"] + companies, key="org_hr_company"
        )

    with col3:
        areas = lookup_service.get_areas()
        area_filter = st.selectbox(
            "Area", options=["Tutte"] + areas, key="org_hr_area"
        )

    with col4:
        show_orphans_only = st.checkbox(
            "👤 Solo Orfani",
            value=False,
            key="org_hr_orphans",
            help="Mostra solo nodi senza responsabile (orfani)"
        )

    with col5:
        st.button("📥 Export PNG", use_container_width=True, disabled=True,
                  help="Disponibile nel layout Albero con tasto destro → Salva immagine")

    # Advanced filters in expander
    with st.expander("🔧 Filtri Avanzati", expanded=False):
        fcol1, fcol2, fcol3 = st.columns(3)

        with fcol1:
            min_employees = st.number_input(
                "Min. dipendenti",
                min_value=0,
                value=0,
                key="org_hr_min_emp",
                help="Mostra solo nodi con almeno N dipendenti"
            )

        with fcol2:
            has_responsible_filter = st.selectbox(
                "Ha responsabile",
                options=["Tutti", "Sì", "No"],
                key="org_hr_has_resp"
            )

        with fcol3:
            node_depth_filter = st.selectbox(
                "Livello gerarchico",
                options=["Tutti"] + [f"Livello {i}" for i in range(1, 6)],
                key="org_hr_depth"
            )

    # ========== LOAD DATA ==========
    with st.spinner("Caricamento organigramma…"):
        try:
            hierarchy_data = orgchart_service.get_hr_hierarchy_tree(
                company_id=None,
                area_filter=None if area_filter == "Tutte" else area_filter
            )

            nodes = hierarchy_data.get('nodes', [])
            if not nodes:
                st.warning("Nessun dato disponibile per l'organigramma HR")
                st.info("Verifica che siano state importate strutture nel database.")
                return

            # Enrich nodes with additional info for tooltips
            for node in nodes:
                # Get full employee details for this node
                emp_details = orgchart_service._query("""
                    SELECT
                        titolare, tx_cod_fiscale, area, sede, qualifica,
                        societa, email, data_assunzione, contratto
                    FROM employees
                    WHERE tx_cod_fiscale = ?
                """, (node['id'],))

                if emp_details:
                    emp = emp_details[0]
                    node['full_name'] = emp['titolare'] or node['name']
                    node['cf'] = emp['tx_cod_fiscale'] or ''
                    node['area'] = emp['area'] or 'N/D'
                    node['sede'] = emp['sede'] or 'N/D'
                    node['qualifica'] = emp['qualifica'] or 'N/D'
                    node['societa'] = emp['societa'] or 'N/D'
                    node['email'] = emp['email'] or 'N/D'
                    node['data_assunzione'] = emp['data_assunzione'] or 'N/D'
                    node['contratto'] = emp['contratto'] or 'N/D'
                else:
                    # Virtual ROOT or no details
                    node['full_name'] = node['name']
                    node['cf'] = node['id'] if node['id'] != 'ROOT' else ''
                    node['area'] = 'N/D'
                    node['sede'] = 'N/D'
                    node['qualifica'] = 'N/D'
                    node['societa'] = 'N/D'
                    node['email'] = 'N/D'
                    node['data_assunzione'] = 'N/D'
                    node['contratto'] = 'N/D'

            # Count orphans (nodes with parentId='ROOT' but not ROOT itself)
            orphans = [n for n in nodes if n.get('parentId') == 'ROOT' and n['id'] != 'ROOT']
            orphans_count = len(orphans)

            # Apply filters
            filtered_nodes = nodes
            if show_orphans_only:
                # Orphans are nodes where parentId is 'ROOT' but id is not 'ROOT'
                filtered_nodes = orphans

            if has_responsible_filter != "Tutti":
                if has_responsible_filter == "Sì":
                    filtered_nodes = [n for n in filtered_nodes if n.get('has_responsible')]
                else:
                    filtered_nodes = [n for n in filtered_nodes if not n.get('has_responsible')]

            if min_employees > 0:
                filtered_nodes = [n for n in filtered_nodes if n.get('employee_count', 0) >= min_employees]

            hierarchy_json = json.dumps(filtered_nodes if show_orphans_only or min_employees > 0 or has_responsible_filter != "Tutti" else nodes, ensure_ascii=False)

            # Create filters config for JavaScript
            filters_config = {
                'showOrphansOnly': show_orphans_only,
                'minEmployees': min_employees,
                'hasResponsible': has_responsible_filter,
                'depthLevel': -1 if node_depth_filter == "Tutti" else int(node_depth_filter.split()[-1]) if node_depth_filter != "Tutti" else -1
            }
            filters_json = json.dumps(filters_config)

            # Show orphans alert if any found
            if orphans_count > 0:
                st.warning(f"⚠️ **{orphans_count} nodi orfani** rilevati (senza responsabile diretto)", icon="👤")

                # Show orphans list in expander
                with st.expander(f"📋 Dettagli {orphans_count} Orfani", expanded=False):
                    orphans_df_data = []
                    for orphan in orphans[:20]:  # Limit to first 20 for performance
                        orphans_df_data.append({
                            'Nome': orphan.get('full_name', orphan.get('name')),
                            'CF': orphan.get('cf', orphan.get('id')),
                            'Area': orphan.get('area', 'N/D'),
                            'Sede': orphan.get('sede', 'N/D'),
                            'Dipendenti': orphan.get('employee_count', 0)
                        })
                    if orphans_df_data:
                        import pandas as pd
                        orphans_df = pd.DataFrame(orphans_df_data)
                        st.dataframe(orphans_df, use_container_width=True, hide_index=True)
                        if orphans_count > 20:
                            st.caption(f"Mostrati primi 20 di {orphans_count} orfani totali")

            # Employees grouped by manager (for modal detail popup)
            # Group employees by their reports_to_cf (manager CF)
            emp_rows = orgchart_service._query("""
                SELECT tx_cod_fiscale, titolare, reports_to_cf
                FROM employees
                WHERE reports_to_cf IS NOT NULL AND reports_to_cf != ''
                ORDER BY titolare
            """)
            emp_by_struttura = {}
            for e in emp_rows:
                manager_cf = e['reports_to_cf']
                if manager_cf not in emp_by_struttura:
                    emp_by_struttura[manager_cf] = []
                emp_by_struttura[manager_cf].append({
                    'cf':    e['tx_cod_fiscale'],
                    'name':  e['titolare'] or e['tx_cod_fiscale'],
                    'roles': []  # Roles not imported yet
                })
            emp_json = json.dumps(emp_by_struttura, ensure_ascii=False)
            node_count = len(nodes)

            # ── HTML Template ──────────────────────────────────────────
            html_content = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:100%;height:100%;overflow:hidden;
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  background:#0f172a;color:#f1f5f9}}
#main{{display:flex;flex-direction:column;height:100vh}}

/* ── layout switcher ── */
#ls-bar{{background:#0a1120;padding:4px 10px;display:flex;gap:4px;
  align-items:center;border-bottom:1px solid #1e293b;flex-shrink:0;height:36px}}
.ls-btn{{background:#1e293b;border:1px solid #334155;color:#94a3b8;
  padding:2px 9px;border-radius:5px;font-size:11px;cursor:pointer;
  transition:all .15s;white-space:nowrap}}
.ls-btn:hover{{background:#334155;color:#e2e8f0}}
.ls-btn.active{{background:#1d4ed8;border-color:#1d4ed8;color:#fff}}

/* ── toolbar ── */
#toolbar{{background:#0f172a;padding:4px 10px;display:flex;gap:5px;
  align-items:center;border-bottom:1px solid #1e293b;flex-shrink:0;height:34px}}
#search-input{{background:#1e293b;border:1px solid #334155;color:#f1f5f9;
  padding:2px 7px;border-radius:4px;font-size:11px;width:180px;outline:none}}
#search-input:focus{{border-color:#3b82f6}}
.btn{{background:#1e293b;border:1px solid #334155;color:#cbd5e1;
  padding:2px 8px;border-radius:4px;font-size:11px;cursor:pointer;
  white-space:nowrap;transition:all .15s}}
.btn:hover{{background:#3b82f6;border-color:#3b82f6;color:#fff}}
.sep{{width:1px;background:#334155;height:18px;flex-shrink:0}}
#legend{{display:flex;gap:8px;font-size:10px;color:#64748b;align-items:center}}
.ld{{width:8px;height:8px;border-radius:2px;border:2px solid;display:inline-block;vertical-align:middle;margin-right:2px}}
#info{{font-size:10px;color:#475569;margin-left:auto}}

/* ── svg canvas ── */
#svg-area{{flex:1;overflow:hidden;cursor:grab}}
#svg-area:active{{cursor:grabbing}}
svg{{width:100%;height:100%}}

/* ── tree nodes ── */
.node-g{{cursor:pointer}}
.node-box{{fill:#1e293b;stroke:#334155;stroke-width:1.5}}
.node-g:hover .node-box{{stroke:#3b82f6;fill:#1a2e4a}}
.node-box.has-resp{{stroke:#22c55e}}
.node-box.no-resp{{stroke:#334155}}
.node-box.collapsed{{stroke:#f59e0b}}
.node-box.hl{{stroke:#f59e0b;stroke-width:2.5;fill:#2a2000}}
.nd-name{{fill:#e2e8f0;font-size:11px;font-weight:600;pointer-events:none}}
.nd-resp{{fill:#64748b;font-size:9.5px;pointer-events:none}}
.nd-cnt{{fill:#3b82f6;font-size:9.5px;pointer-events:none}}
.tog-c{{fill:#1d4ed8;stroke:#0f172a;stroke-width:1;cursor:pointer}}
.tog-c:hover{{fill:#3b82f6}}
.tog-t{{fill:#fff;font-size:8.5px;text-anchor:middle;dominant-baseline:central;pointer-events:none}}
.link{{fill:none;stroke:#1e3a5f;stroke-width:1.5}}

/* ── sunburst ── */
.sb-arc{{cursor:pointer}}
.sb-label{{pointer-events:none;dominant-baseline:central}}

/* ── treemap ── */
.tm-node{{cursor:pointer}}
.tm-rect{{stroke:#0f172a;stroke-width:0.5}}
.tm-label{{pointer-events:none;dominant-baseline:hanging}}

/* ── panels (Finder) ── */
#panels-container{{flex:1;display:none;overflow-x:auto;overflow-y:hidden;flex-direction:row}}
.panel-col{{min-width:220px;border-right:1px solid #334155;overflow-y:auto;flex-shrink:0;background:#1e293b}}
.panel-item{{padding:7px 10px;cursor:pointer;display:flex;justify-content:space-between;
  align-items:center;border-bottom:1px solid #1a2535}}
.panel-item:hover{{background:#263348}}
.panel-item.selected{{background:#1d4ed8}}
.pi-name{{font-size:12px;color:#e2e8f0;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-right:6px}}
.pi-count{{font-size:10px;color:#64748b;white-space:nowrap}}
.pi-arrow{{color:#64748b;font-size:16px;margin-left:3px;line-height:1}}
.panel-item.selected .pi-name{{color:#fff}}
.panel-item.selected .pi-count,.panel-item.selected .pi-arrow{{color:#93c5fd}}

/* ── card grid (OrgVue) ── */
#card-grid-container{{flex:1;display:none;overflow:auto;padding:10px;background:#0f172a}}
.orgcard{{background:#1e293b;border:1px solid #334155;border-radius:6px;
  padding:9px;cursor:pointer;transition:border-color 150ms}}
.orgcard:hover{{border-color:#3b82f6}}
.orgcard-manager{{border-left:3px solid #1d4ed8}}
.oc-header{{margin-bottom:6px;border-bottom:1px solid #1a2535;padding-bottom:5px}}
.oc-name{{font-weight:600;font-size:12px;color:#e2e8f0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.oc-role{{font-size:10px;color:#64748b;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.oc-body{{display:flex;flex-direction:column;gap:2px}}
.oc-row{{display:flex;justify-content:space-between;font-size:10px;color:#94a3b8}}
.oc-row span:first-child{{color:#64748b}}

/* ── tooltip ── */
#tooltip{{display:none;position:fixed;background:#1e293b;border:1px solid #475569;
  border-radius:4px;padding:4px 8px;font-size:11px;color:#e2e8f0;pointer-events:none;z-index:200;max-width:220px}}

/* ── modal ── */
#ov{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:99}}
#modal{{display:none;position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);
  background:#1e293b;border:1px solid #334155;border-radius:8px;
  width:400px;max-height:78vh;flex-direction:column;overflow:hidden;z-index:100}}
#mh{{padding:10px 14px;border-bottom:1px solid #334155;display:flex;align-items:flex-start;
  gap:8px;background:#0f172a}}
#mt{{font-size:12px;font-weight:700;color:#e2e8f0;flex:1;line-height:1.3}}
#mc{{font-size:9px;color:#475569}}
#mx{{background:none;border:none;color:#64748b;cursor:pointer;font-size:16px;padding:0}}
#mx:hover{{color:#ef4444}}
#ms{{padding:6px 14px;background:#0f172a;border-bottom:1px solid #1e293b;
  display:flex;gap:14px;font-size:10px;color:#64748b;flex-shrink:0}}
#ms b{{color:#e2e8f0}}
#msi{{padding:6px 14px;border-bottom:1px solid #1e293b;flex-shrink:0}}
#msi input{{width:100%;background:#0f172a;border:1px solid #334155;color:#f1f5f9;
  padding:3px 7px;border-radius:4px;font-size:11px;outline:none}}
#ml{{overflow-y:auto;flex:1}}
.me{{padding:5px 14px;display:flex;align-items:center;gap:6px;border-bottom:1px solid #0f172a}}
.me:hover{{background:#0f172a}}
.mn{{font-size:11px;color:#e2e8f0;flex:1}}
.mr{{display:flex;gap:3px}}
.rt{{padding:1px 4px;border-radius:3px;font-size:8.5px;font-weight:600;color:#fff}}
.rt.App{{background:#2563eb}}.rt.Viag{{background:#16a34a}}
.rt.Contr{{background:#d97706}}.rt.Cass{{background:#dc2626}}
.noemp{{padding:18px;text-align:center;color:#475569;font-size:11px}}
</style>
</head>
<body>
<div id="main">

  <!-- Layout switcher -->
  <div id="ls-bar">
    <button onclick="setLayout('h')" id="btn-h" class="ls-btn active">🌲 Albero H</button>
    <button onclick="setLayout('v')" id="btn-v" class="ls-btn">🏛️ Albero V</button>
    <button onclick="setLayout('s')" id="btn-s" class="ls-btn">☀️ Sunburst</button>
    <button onclick="setLayout('t')" id="btn-t" class="ls-btn">📦 Treemap</button>
    <button onclick="setLayout('p')" id="btn-p" class="ls-btn">🗂️ Pannelli</button>
    <button onclick="setLayout('c')" id="btn-c" class="ls-btn">📋 Card Grid</button>
  </div>

  <!-- Standard toolbar -->
  <div id="toolbar">
    <input id="search-input" placeholder="Cerca struttura…" oninput="doSearch(this.value)"/>
    <div class="sep"></div>
    <button class="btn" id="btn-reset" onclick="resetView()">&#8635; Reset</button>
    <button class="btn" id="btn-expand" onclick="expandOne()">+1 Livello</button>
    <button class="btn" id="btn-collapse" onclick="collapseAll()">Chiudi tutti</button>
    <button class="btn" onclick="goFullscreen()">&#x26F6; Fullscreen</button>
    <div class="sep"></div>
    <div id="legend">
      <span><i class="ld" style="border-color:#22c55e"></i>Ha resp.</span>
      <span><i class="ld" style="border-color:#334155"></i>No resp.</span>
      <span><i class="ld" style="border-color:#f59e0b"></i>Collassato</span>
    </div>
    <span id="info">{node_count} strutture &nbsp;·&nbsp; click=espandi &nbsp;·&nbsp; dbl-click=lista dip.</span>
  </div>

  <!-- Content areas (one visible at a time) -->
  <div id="svg-area"><svg id="svg"><g id="rg"></g></svg></div>
  <div id="panels-container"></div>
  <div id="card-grid-container"></div>

</div><!-- #main -->

<!-- Tooltip -->
<div id="tooltip"></div>

<!-- Overlay + Modal -->
<div id="ov" onclick="closeModal()"></div>
<div id="modal">
  <div id="mh">
    <div style="flex:1"><div id="mt"></div><div id="mc"></div></div>
    <button id="mx" onclick="closeModal()">&#x2715;</button>
  </div>
  <div id="ms">Dip: <b id="m-d">0</b> &nbsp; Appr: <b id="m-a">0</b> &nbsp; Viag: <b id="m-v">0</b></div>
  <div id="msi"><input placeholder="Filtra…" oninput="filterM(this.value)"/></div>
  <div id="ml"></div>
</div>

<script>
const RAW  = {hierarchy_json};
const EMP  = {emp_json};
const FILTERS = {filters_json};

// ── Stratify flat data ──────────────────────────────────────────────────
const stratify = d3.stratify().id(d=>d.id).parentId(d=>d.parentId);
let root;
try {{ root = stratify(RAW); }}
catch(e) {{
  document.body.innerHTML='<div style="padding:20px;color:#ef4444">Errore gerarchia: '+e.message+'</div>';
  throw e;
}}
// Start tree collapsed (depth>=1)
root.each(d=>{{ if(d.depth>=1&&d.children){{ d._ch=d.children; d.children=null; }} }});

// ── Enhanced Tooltip Function ────────────────────────────────────────────
function showEnhancedTooltip(event, d) {{
  const node = d.data;
  const tooltip = document.getElementById('tooltip');

  // Build detailed tooltip content
  let tooltipHTML = `
    <div style="padding:4px">
      <div style="font-weight:700;margin-bottom:6px;border-bottom:1px solid #475569;padding-bottom:4px">
        ${{node.full_name || node.name}}
      </div>
      <div style="font-size:9px;color:#94a3b8;line-height:1.5">
        ${{node.cf ? '<div><b>CF:</b> ' + node.cf + '</div>' : ''}}
        ${{node.qualifica && node.qualifica !== 'N/D' ? '<div><b>Qualifica:</b> ' + node.qualifica + '</div>' : ''}}
        ${{node.area && node.area !== 'N/D' ? '<div><b>Area:</b> ' + node.area + '</div>' : ''}}
        ${{node.sede && node.sede !== 'N/D' ? '<div><b>Sede:</b> ' + node.sede + '</div>' : ''}}
        ${{node.societa && node.societa !== 'N/D' ? '<div><b>Società:</b> ' + node.societa + '</div>' : ''}}
        <div><b>Dipendenti:</b> ${{node.employee_count || 0}}</div>
        ${{node.email && node.email !== 'N/D' ? '<div><b>Email:</b> ' + node.email + '</div>' : ''}}
        ${{node.contratto && node.contratto !== 'N/D' ? '<div><b>Contratto:</b> ' + node.contratto + '</div>' : ''}}
      </div>
    </div>
  `;

  tooltip.innerHTML = tooltipHTML;
  tooltip.style.left = (event.clientX + 12) + 'px';
  tooltip.style.top = (event.clientY - 8) + 'px';
  tooltip.style.display = 'block';
  tooltip.style.maxWidth = '280px';
}}

function hideTooltip() {{
  document.getElementById('tooltip').style.display = 'none';
}}

// ── SVG & zoom ──────────────────────────────────────────────────────────
const ROW_H=42, COL_W=210, NW=190, NH=36;
const svg  = d3.select('#svg');
const g    = d3.select('#rg');
const zoom = d3.zoom().scaleExtent([0.02,5]).on('zoom',e=>g.attr('transform',e.transform));
svg.call(zoom);

// Click on SVG background to reset focus
svg.on('click', function(event) {{
  // Only if clicking directly on SVG (not on nodes)
  if (event.target.tagName === 'svg') {{
    focusedNode = null;
    g.selectAll('*').remove();
    if(currentLayout==='h') drawHorizontal();
    else if(currentLayout==='v') drawVertical();
    setTimeout(autoFit, 100);
  }}
}});

// Auto-fit helper function
function autoFit() {{
  const el=document.getElementById('svg-area');
  const w=el.clientWidth, h=el.clientHeight;

  try {{
    const bbox = g.node().getBBox();
    if (bbox.width === 0 || bbox.height === 0) return;

    const fullWidth = bbox.width;
    const fullHeight = bbox.height;

    // Calculate scale to fit with padding
    const scale = Math.min(
      (w - 60) / fullWidth,
      (h - 60) / fullHeight,
      1.5  // Max zoom in
    );

    // Center the tree
    const centerX = w / 2 - (bbox.x + fullWidth / 2) * scale;
    const centerY = h / 2 - (bbox.y + fullHeight / 2) * scale;

    svg.transition().duration(300).call(zoom.transform,
      d3.zoomIdentity.translate(centerX, centerY).scale(scale));
  }} catch(e) {{
    console.error('AutoFit error:', e);
  }}
}}

let curEmp=[], currentLayout='h';

// ── LAYOUT SWITCHER ─────────────────────────────────────────────────────
function setLayout(type) {{
  document.querySelectorAll('.ls-btn').forEach(b=>b.classList.remove('active'));
  document.getElementById('btn-'+type).classList.add('active');
  currentLayout=type;

  const svgArea=document.getElementById('svg-area');
  const panelsEl=document.getElementById('panels-container');
  const cardsEl=document.getElementById('card-grid-container');

  // Hide everything
  svgArea.style.display='none';
  panelsEl.style.display='none';
  cardsEl.style.display='none';

  // Clear SVG content
  g.selectAll('*').remove();
  g.attr('transform','');

  // Tree-only toolbar buttons
  const treeOnly = type==='h'||type==='v';
  document.getElementById('btn-expand').style.display=treeOnly?'':'none';
  document.getElementById('btn-collapse').style.display=treeOnly?'':'none';
  document.getElementById('btn-reset').style.display=(type==='h'||type==='v')?'':'none';

  // Re-enable or disable zoom
  if(treeOnly) {{
    svg.call(zoom);
  }} else {{
    svg.on('.zoom',null);
  }}

  // Show right container
  if(['h','v','s','t'].includes(type)) {{
    svgArea.style.cssText='flex:1;overflow:hidden;cursor:'+(treeOnly?'grab':'default');
  }} else if(type==='p') {{
    panelsEl.style.cssText='flex:1;display:flex;overflow-x:auto;overflow-y:hidden';
  }} else if(type==='c') {{
    cardsEl.style.cssText='flex:1;display:block;overflow:auto;padding:10px;background:#0f172a';
  }}

  ({{h:drawHorizontal,v:drawVertical,s:drawSunburst,t:drawTreemap,p:drawPanels,c:drawCardGrid}}[type])();

  if(treeOnly) setTimeout(resetView,80);
}}

// ── Helpers ──────────────────────────────────────────────────────────────
function cc(d) {{ return d._ch?d._ch.length:(d.children?d.children.length:0)||''; }}
function cut(s,m) {{ if(!s)return''; s=String(s); return s.length>m?s.slice(0,m-1)+'…':s; }}

// Global variable to track selected/focused node
let focusedNode = null;

// Get all ancestor nodes (path to root)
function getAncestors(node) {{
  const ancestors = [];
  let current = node;
  while(current.parent) {{
    ancestors.push(current.parent);
    current = current.parent;
  }}
  return ancestors;
}}

// Get all descendant nodes
function getDescendants(node) {{
  const descendants = [];
  function traverse(n) {{
    const children = n.children || n._ch || [];
    children.forEach(child => {{
      descendants.push(child);
      traverse(child);
    }});
  }}
  traverse(node);
  return descendants;
}}

// Check if a node should be visible based on focused node
function shouldShowNode(node) {{
  if (!focusedNode) return true; // No focus = show all

  // Always show the focused node
  if (node === focusedNode) return true;

  // Show all ancestors (path to root)
  const ancestors = getAncestors(focusedNode);
  if (ancestors.includes(node)) return true;

  // Show ONLY direct children (not all descendants) - this is the drill-down
  if (node.parent === focusedNode) return true;

  // Hide everything else (siblings, descendants of children, etc.)
  return false;
}}

function toggle(d) {{
  if(d.children){{
    // Collapsing - collapse this node
    d._ch=d.children;
    d.children=null;
    // Keep focus on parent or clear if at root level
    if (d.depth > 1) {{
      focusedNode = d.parent;
    }} else {{
      focusedNode = null;
    }}
  }}
  else if(d._ch){{
    // Expanding - set this node as focused to show only its children
    focusedNode = d;
    d.children=d._ch;
    d._ch=null;
  }}
  g.selectAll('*').remove();
  if(currentLayout==='h') drawHorizontal();
  else if(currentLayout==='v') drawVertical();

  // Auto-fit after toggle
  setTimeout(autoFit, 100);
}}

function nodeClass(d) {{
  if(d.data._hl)        return 'node-box hl';
  if(d._ch)             return 'node-box collapsed';
  if(d.data.has_responsible) return 'node-box has-resp';
  return 'node-box no-resp';
}}

// ── LAYOUT H: Horizontal Tree ───────────────────────────────────────────
function drawHorizontal() {{
  const tree=d3.tree().nodeSize([ROW_H,COL_W]);
  tree(root);

  // Filter nodes/links based on focused node (drill-down)
  const allNodes = root.descendants();
  const allLinks = root.links();
  const nodes = allNodes.filter(shouldShowNode);
  const links = allLinks.filter(link =>
    shouldShowNode(link.source) && shouldShowNode(link.target)
  );

  const lk=g.selectAll('.link').data(links,d=>d.source.id+'>'+d.target.id);
  lk.enter().insert('path','.node-g').attr('class','link')
    .merge(lk).transition().duration(200)
    .attr('d',d=>{{
      const sx=d.source.y+NW, sy=d.source.x+NH/2;
      const tx=d.target.y,    ty=d.target.x+NH/2;
      const mx=(sx+tx)/2;
      return `M${{sx}},${{sy}} L${{mx}},${{sy}} L${{mx}},${{ty}} L${{tx}},${{ty}}`;
    }});
  lk.exit().remove();

  const nd=g.selectAll('.node-g').data(nodes,d=>d.id);
  const ne=nd.enter().append('g').attr('class','node-g')
    .attr('transform',d=>`translate(${{d.y}},${{d.x}})`)
    .on('click',  (ev,d)=>{{ev.stopPropagation();toggle(d);}})
    .on('dblclick',(ev,d)=>{{ev.stopPropagation();openModal(d);}})
    .on('mouseover', (ev,d)=>showEnhancedTooltip(ev,d))
    .on('mouseout', hideTooltip);

  ne.append('rect').attr('class','node-box').attr('width',NW).attr('height',NH).attr('rx',4);
  ne.append('text').attr('class','nd-name').attr('x',7).attr('y',14).text(d=>cut(d.data.name,24));
  ne.append('text').attr('class','nd-resp').attr('x',7).attr('y',26).text(d=>cut(d.data.title||'',28));
  ne.append('text').attr('class','nd-cnt') .attr('x',7).attr('y',34).text(d=>d.data.employee_count>0?d.data.employee_count+' dip.':'');

  const bg=ne.append('g').attr('class','bg').attr('transform',`translate(${{NW}},${{NH/2}})`);
  bg.append('circle').attr('class','tog-c').attr('r',8).on('click',(ev,d)=>{{ev.stopPropagation();toggle(d);}});
  bg.append('text').attr('class','tog-t').text(d=>cc(d));

  const nu=ne.merge(nd);
  nu.transition().duration(200).attr('transform',d=>`translate(${{d.y}},${{d.x}})`);
  nu.select('.node-box').attr('class',nodeClass);
  nu.select('.nd-name').text(d=>cut(d.data.name,24));
  nu.select('.nd-resp').text(d=>cut(d.data.title||'',28));
  nu.select('.nd-cnt') .text(d=>d.data.employee_count>0?d.data.employee_count+' dip.':'');
  nu.select('.bg').style('display',d=>(d.children||d._ch)?'block':'none');
  nu.select('.tog-t').text(d=>cc(d));
  nd.exit().remove();
}}

// ── LAYOUT V: Vertical Tree (con wrapping automatico) ────────────────────
function drawVertical() {{
  const VNW=150, VNH=42, VGY=90;

  // Calcola larghezza disponibile
  const el=document.getElementById('svg-area');
  const availableWidth = (el.clientWidth || 1200) - 100; // Margini laterali
  const VGX = 170; // Spacing orizzontale tra nodi
  const maxNodesPerRow = Math.max(1, Math.floor(availableWidth / VGX));

  // Applica layout tree base
  const tree=d3.tree().nodeSize([VGX,VGY]);
  tree(root);

  // Filtra nodi visibili in base al focus
  const allNodes = root.descendants();
  const visibleNodes = allNodes.filter(shouldShowNode);

  // Riorganizza nodi per livello con wrapping (solo nodi visibili)
  const nodesByLevel = {{}};
  visibleNodes.forEach(d => {{
    if (!nodesByLevel[d.depth]) nodesByLevel[d.depth] = [];
    nodesByLevel[d.depth].push(d);
  }});

  // Riposiziona nodi con wrapping per livello
  Object.keys(nodesByLevel).forEach(depth => {{
    const levelNodes = nodesByLevel[depth];
    const numRows = Math.ceil(levelNodes.length / maxNodesPerRow);

    levelNodes.forEach((d, i) => {{
      const row = Math.floor(i / maxNodesPerRow);
      const colInRow = i % maxNodesPerRow;
      const nodesInThisRow = Math.min(maxNodesPerRow, levelNodes.length - row * maxNodesPerRow);

      // Centra la riga
      const rowWidth = nodesInThisRow * VGX;
      const rowStartX = -rowWidth / 2;

      d.x = rowStartX + colInRow * VGX + VGX / 2;
      d.y = parseInt(depth) * VGY + row * (VGY + 20); // Spazio extra tra righe
    }});
  }});

  // Filtra anche i links per mostrare solo quelli tra nodi visibili
  const allLinks = root.links();
  const visibleLinks = allLinks.filter(link =>
    shouldShowNode(link.source) && shouldShowNode(link.target)
  );

  const nodes=visibleNodes, links=visibleLinks;

  const lk=g.selectAll('.link').data(links,d=>d.source.id+'>'+d.target.id);
  lk.enter().insert('path','.node-g').attr('class','link')
    .merge(lk).transition().duration(200)
    .attr('d',d=>{{
      const sx=d.source.x, sy=d.source.y+VNH;
      const tx=d.target.x, ty=d.target.y;
      const my=(sy+ty)/2;
      return `M${{sx}},${{sy}} C${{sx}},${{my}} ${{tx}},${{my}} ${{tx}},${{ty}}`;
    }});
  lk.exit().remove();

  const nd=g.selectAll('.node-g').data(nodes,d=>d.id);
  const ne=nd.enter().append('g').attr('class','node-g')
    .attr('transform',d=>`translate(${{d.x-VNW/2}},${{d.y}})`)
    .on('click',  (ev,d)=>{{ev.stopPropagation();toggle(d);}})
    .on('dblclick',(ev,d)=>{{ev.stopPropagation();openModal(d);}})
    .on('mouseover', (ev,d)=>showEnhancedTooltip(ev,d))
    .on('mouseout', hideTooltip);

  ne.append('rect').attr('class','node-box').attr('width',VNW).attr('height',VNH).attr('rx',4);
  ne.append('text').attr('class','nd-name').attr('x',6).attr('y',14).text(d=>cut(d.data.name,19));
  ne.append('text').attr('class','nd-resp').attr('x',6).attr('y',25).text(d=>cut(d.data.title||'',21));
  ne.append('text').attr('class','nd-cnt') .attr('x',6).attr('y',36).text(d=>d.data.employee_count>0?d.data.employee_count+' dip.':'');

  // Toggle badge at bottom center
  const bg=ne.append('g').attr('class','bg').attr('transform',`translate(${{VNW/2}},${{VNH}})`);
  bg.append('circle').attr('class','tog-c').attr('r',8).on('click',(ev,d)=>{{ev.stopPropagation();toggle(d);}});
  bg.append('text').attr('class','tog-t').text(d=>cc(d));

  const nu=ne.merge(nd);
  nu.transition().duration(200).attr('transform',d=>`translate(${{d.x-VNW/2}},${{d.y}})`);
  nu.select('.node-box').attr('class',nodeClass);
  nu.select('.nd-name').text(d=>cut(d.data.name,19));
  nu.select('.nd-resp').text(d=>cut(d.data.title||'',21));
  nu.select('.nd-cnt') .text(d=>d.data.employee_count>0?d.data.employee_count+' dip.':'');
  nu.select('.bg').style('display',d=>(d.children||d._ch)?'block':'none');
  nu.select('.tog-t').text(d=>cc(d));
  nd.exit().remove();
}}

// ── LAYOUT S: Sunburst ──────────────────────────────────────────────────
function drawSunburst() {{
  const el=document.getElementById('svg-area');
  const W=el.clientWidth||800, H=el.clientHeight||700;
  const radius=Math.min(W,H)/2 - 40;

  // Build fresh fully-expanded hierarchy
  const sroot=stratify(RAW.map(d=>Object.assign({{}},d)));
  sroot.sum(d=>d.data.employee_count||1);
  d3.partition().size([2*Math.PI, radius])(sroot);

  const arc=d3.arc()
    .startAngle(d=>d.x0).endAngle(d=>d.x1)
    .padAngle(d=>Math.min((d.x1-d.x0)/2, 0.003))
    .innerRadius(d=>d.y0).outerRadius(d=>d.y1-1);

  const depthColors=['#1e3a8a','#1d4ed8','#1e40af','#2563eb','#3b82f6','#60a5fa','#93c5fd'];

  g.attr('transform',`translate(${{W/2}},${{H/2}})`);

  // Clear existing content
  g.selectAll('*').remove();

  // Arcs
  g.selectAll('.sb-arc').data(sroot.descendants().filter(d=>d.depth>0))
    .join('path').attr('class','sb-arc')
    .attr('d',arc)
    .attr('fill',d=>depthColors[Math.min(d.depth-1,depthColors.length-1)])
    .attr('stroke','#0f172a').attr('stroke-width',1)
    .on('mouseover',(ev,d)=>{{
      d3.select(ev.currentTarget).attr('fill','#f59e0b');
      showTip(ev, d.data.name+' ('+d.value+' dip.)');
    }})
    .on('mouseout',(ev,d)=>{{
      d3.select(ev.currentTarget).attr('fill',depthColors[Math.min(d.depth,depthColors.length-1)]);
      hideTip();
    }})
    .on('click',(ev,d)=>openModalById(d.data.id,d.data.name));

  // Radial labels for arcs with enough angular space
  g.selectAll('.sb-label')
    .data(sroot.descendants().filter(d=>d.depth>0&&(d.x1-d.x0)>0.07))
    .join('text').attr('class','sb-label')
    .attr('transform',d=>{{
      const x=(d.x0+d.x1)/2*180/Math.PI;
      const y=(d.y0+d.y1)/2;
      return `rotate(${{x-90}}) translate(${{y}},0) rotate(${{x<180?0:180}})`;
    }})
    .attr('text-anchor','middle').attr('font-size','8px').attr('fill','#f1f5f9')
    .text(d=>cut(d.data.name,11));
}}

// ── LAYOUT T: Treemap ────────────────────────────────────────────────────
function drawTreemap() {{
  const el=document.getElementById('svg-area');
  const W=el.clientWidth||800, H=el.clientHeight||700;

  const troot=stratify(RAW.map(d=>Object.assign({{}},d)));
  troot.sum(d=>d.data.employee_count||1).sort((a,b)=>b.value-a.value);
  d3.treemap().size([W,H]).padding(2).paddingTop(20).round(true)(troot);

  // Clear existing and reset transform
  g.selectAll('*').remove();
  g.attr('transform','');
  const depthColors=['#0f172a','#1e3a8a','#1e40af','#1d4ed8','#2563eb','#3b82f6'];

  const cell=g.selectAll('.tm-node')
    .data(troot.descendants().filter(d=>d.depth>0))
    .join('g').attr('class','tm-node')
    .attr('transform',d=>`translate(${{d.x0}},${{d.y0}})`);

  cell.append('rect').attr('class','tm-rect')
    .attr('width', d=>Math.max(0,d.x1-d.x0))
    .attr('height',d=>Math.max(0,d.y1-d.y0))
    .attr('fill',d=>depthColors[Math.min(d.depth,depthColors.length-1)])
    .on('mouseover',(ev,d)=>showTip(ev,d.data.name+' — '+(d.value||0)+' dip.'))
    .on('mouseout',hideTip)
    .on('click',(ev,d)=>openModalById(d.data.id,d.data.name));

  cell.filter(d=>(d.x1-d.x0)>50&&(d.y1-d.y0)>20)
    .append('text').attr('class','tm-label')
    .attr('x',4).attr('y',13).attr('font-size','10px').attr('fill','#e2e8f0')
    .text(d=>cut(d.data.name,Math.max(1,Math.floor((d.x1-d.x0-8)/7))));

  cell.filter(d=>(d.x1-d.x0)>50&&(d.y1-d.y0)>32)
    .append('text').attr('class','tm-label')
    .attr('x',4).attr('y',27).attr('font-size','9px').attr('fill','#64748b')
    .text(d=>(d.value||0)+' dip.');
}}

// ── LAYOUT P: Panels (Finder-style) ─────────────────────────────────────
function drawPanels() {{
  const container=document.getElementById('panels-container');
  container.innerHTML='';
  let selectedPath=[];

  function getChildren(id) {{ return RAW.filter(d=>d.parentId===id); }}
  function getRoots()       {{ return RAW.filter(d=>!d.parentId||d.parentId===''); }}

  function renderColumn(nodes,depth) {{
    while(container.children.length>depth) container.lastChild.remove();
    const col=document.createElement('div');
    col.className='panel-col';
    col.style.height='100%';
    nodes.forEach(node=>{{
      const isSelected=selectedPath[depth]===node.id;
      const children=getChildren(node.id);
      const item=document.createElement('div');
      item.className='panel-item'+(isSelected?' selected':'');
      item.innerHTML=
        `<span class="pi-name" title="${{node.name}}">${{cut(node.name,26)}}</span>`+
        `<div style="display:flex;align-items:center;gap:2px">`+
          `<span class="pi-count">${{node.employee_count||0}}</span>`+
          (children.length?`<span class="pi-arrow">›</span>`:'')+
        `</div>`;
      item.onclick=()=>{{
        selectedPath=selectedPath.slice(0,depth);
        selectedPath[depth]=node.id;
        if(children.length) renderColumn(children,depth+1);
        else {{ while(container.children.length>depth+1) container.lastChild.remove(); }}
        renderColumn(nodes,depth);
      }};
      col.appendChild(item);
    }});
    container.appendChild(col);
  }}
  renderColumn(getRoots(),0);
}}

// ── LAYOUT C: Card Grid (OrgVue-style) ──────────────────────────────────
function drawCardGrid() {{
  const container=document.getElementById('card-grid-container');
  container.innerHTML='';
  container.style.cssText=
    'flex:1;display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));'+
    'gap:8px;padding:10px;overflow:auto;background:#0f172a;';

  const sorted=[...RAW].sort((a,b)=>(b.employee_count||0)-(a.employee_count||0));
  sorted.forEach(node=>{{
    const isManager=(node.employee_count||0)>0;
    const emps=EMP[node.id]||[];
    const apprCount=emps.filter(e=>e.roles.includes('App')).length;
    const card=document.createElement('div');
    card.className='orgcard'+(isManager?' orgcard-manager':'');
    card.innerHTML=
      `<div class="oc-header">`+
        `<div class="oc-name" title="${{node.name}}">${{cut(node.name,28)}}</div>`+
        `<div class="oc-role">${{cut(node.title||'—',34)}}</div>`+
      `</div>`+
      `<div class="oc-body">`+
        `<div class="oc-row"><span>Dipendenti</span><span>${{node.employee_count||0}}</span></div>`+
        `<div class="oc-row"><span>Approvatori</span><span>${{apprCount}}</span></div>`+
      `</div>`;
    card.onclick=()=>openModalById(node.id,node.name);
    container.appendChild(card);
  }});
}}

// ── Toolbar actions ──────────────────────────────────────────────────────
function resetView() {{
  // Reset focus to show all nodes
  focusedNode = null;
  const el=document.getElementById('svg-area');
  const w=el.clientWidth, h=el.clientHeight;

  // Redraw first to calculate actual tree size
  g.selectAll('*').remove();
  if(currentLayout==='h') drawHorizontal();
  else if(currentLayout==='v') drawVertical();

  // Auto-fit to viewport
  setTimeout(() => {{
    const bbox = g.node().getBBox();
    const fullWidth = bbox.width;
    const fullHeight = bbox.height;

    // Calculate scale to fit with padding
    const scale = Math.min(
      (w - 60) / fullWidth,
      (h - 60) / fullHeight,
      1.5  // Max zoom in
    );

    // Center the tree
    const centerX = w / 2 - (bbox.x + fullWidth / 2) * scale;
    const centerY = h / 2 - (bbox.y + fullHeight / 2) * scale;

    svg.transition().duration(300).call(zoom.transform,
      d3.zoomIdentity.translate(centerX, centerY).scale(scale));
  }}, 100);
}}

function expandOne() {{
  let did=false;
  root.each(d=>{{
    if(!d.children&&d._ch&&d.parent&&d.parent.children)
      {{d.children=d._ch;d._ch=null;did=true;}}
  }});
  if(!did) root.each(d=>{{if(d._ch){{d.children=d._ch;d._ch=null;}}}});
  g.selectAll('*').remove();
  if(currentLayout==='h') drawHorizontal(); else drawVertical();
  setTimeout(autoFit, 100);
}}

function collapseAll() {{
  // Reset focus when collapsing all
  focusedNode = null;
  root.each(d=>{{if(d.depth>=1&&d.children){{d._ch=d.children;d.children=null;}}}});
  g.selectAll('*').remove();
  if(currentLayout==='h') drawHorizontal(); else drawVertical();
  setTimeout(autoFit,250);
}}

function doSearch(q) {{
  RAW.forEach(d=>d._hl=false);
  if(!q||q.length<2) {{
    if(currentLayout==='h') drawHorizontal();
    else if(currentLayout==='v') drawVertical();
    return;
  }}
  q=q.toLowerCase();
  let found=null;
  root.each(d=>{{if(d.data.name.toLowerCase().includes(q)){{d.data._hl=true;if(!found)found=d;}}}});
  if(!found) return;
  let cur=found; while(cur){{if(cur._ch){{cur.children=cur._ch;cur._ch=null;}} cur=cur.parent;}}
  g.selectAll('*').remove();
  if(currentLayout==='h'||currentLayout==='v') {{
    if(currentLayout==='h') drawHorizontal(); else drawVertical();
    setTimeout(()=>{{
      const el=document.getElementById('svg-area');
      const w=el.clientWidth, h=el.clientHeight;
      const cx=currentLayout==='h'?found.y:found.x;
      const cy=currentLayout==='h'?found.x:found.y;
      svg.transition().duration(450).call(zoom.transform,
        d3.zoomIdentity.translate(w/2-cx, h/2-cy).scale(1));
    }},250);
  }}
}}

function goFullscreen() {{
  const el=document.getElementById('main');
  if(!document.fullscreenElement) el.requestFullscreen().catch(()=>{{}});
  else document.exitFullscreen();
}}
document.addEventListener('fullscreenchange',()=>setTimeout(resetView,200));

// ── Tooltip ──────────────────────────────────────────────────────────────
function showTip(ev,text) {{
  const t=document.getElementById('tooltip');
  t.textContent=text;
  t.style.left=(ev.clientX+12)+'px';
  t.style.top=(ev.clientY-8)+'px';
  t.style.display='block';
}}
function hideTip() {{ document.getElementById('tooltip').style.display='none'; }}

// ── Modal ────────────────────────────────────────────────────────────────
function openModalById(id,name) {{
  const emps=EMP[id]||[];
  curEmp=emps;
  document.getElementById('mt').textContent=name;
  document.getElementById('mc').textContent='Codice: '+id;
  document.getElementById('m-d').textContent=emps.length;
  document.getElementById('m-a').textContent=emps.filter(e=>e.roles.includes('App')).length;
  document.getElementById('m-v').textContent=emps.filter(e=>e.roles.includes('Viag')).length;
  document.querySelector('#msi input').value='';
  renderList(emps);
  document.getElementById('ov').style.display='block';
  document.getElementById('modal').style.display='flex';
}}
function openModal(d) {{ openModalById(d.id, d.data.name); }}

function renderList(emps) {{
  const l=document.getElementById('ml');
  if(!emps.length){{l.innerHTML='<div class="noemp">Nessun dipendente assegnato</div>';return;}}
  l.innerHTML=emps.map(e=>
    `<div class="me"><div class="mn">${{e.name}}</div>`+
    `<div class="mr">${{e.roles.map(r=>`<span class="rt ${{r}}">${{r}}</span>`).join('')}}</div></div>`
  ).join('');
}}
function filterM(q) {{
  renderList(q?curEmp.filter(e=>e.name.toLowerCase().includes(q.toLowerCase())):curEmp);
}}
function closeModal() {{
  document.getElementById('ov').style.display='none';
  document.getElementById('modal').style.display='none';
}}

// ── Init ─────────────────────────────────────────────────────────────────
drawHorizontal();
setTimeout(autoFit,120);
</script>
</body></html>"""

            components.html(html_content, height=1060, scrolling=False)

            # ── Streamlit-side search results ──
            if search_query:
                st.markdown("### 🔍 Risultati Ricerca")
                search_result = orgchart_service.search_employee(search_query, hierarchy_type='HR')
                if search_result:
                    emp  = search_result['employee']
                    path = search_result['path']
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.markdown(f"**{emp.get('Titolare', emp.get('titolare', ''))}**")
                        st.text(f"CF: {emp.get('TxCodFiscale', emp.get('tx_cod_fiscale', ''))}")
                    with col2:
                        if path:
                            st.markdown(" **>** ".join([p['name'] for p in path]))
                        else:
                            st.info("Nessuna assegnazione gerarchica HR")
                else:
                    st.warning(f"⚠️ Nessun risultato per: {search_query}")

            with st.expander("📖 Legenda e Istruzioni"):
                st.markdown("""
**Layout disponibili (switcher in alto):**
- 🌲 **Albero H** — Tree orizzontale LR, click=espandi, dbl-click=lista dipendenti
- 🏛️ **Albero V** — Tree verticale top-down, stessa interazione
- ☀️ **Sunburst** — Anelli radiali per livello, hover=tooltip, click=lista dipendenti
- 📦 **Treemap** — Rettangoli proporzionali a n° dipendenti, hover=tooltip
- 🗂️ **Pannelli** — Finder-style, click colonna→espande figli a destra
- 📋 **Card Grid** — Schede OrgVue, manager con bordo blu, click=lista dipendenti

**Navigazione alberi (H/V):** zoom con rotella · trascina per pan · Reset centralizza
                """)

        except Exception as e:
            st.error(f"❌ Errore durante caricamento organigramma: {str(e)}")
            import traceback
            st.code(traceback.format_exc())


if __name__ == "__main__":
    render_orgchart_hr_view()
