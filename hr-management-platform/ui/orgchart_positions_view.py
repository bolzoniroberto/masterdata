"""
Orgchart Unità Organizzative (Positions) View - Multi-Layout

Org chart built from ALL rows: strutture + personale as SEPARATE tree nodes.
Hierarchy uses Codice (column AB = ID) → UNITA_OPERATIVA_PADRE (column AC = ReportsTo).

Two node types:
  - 'struttura': organizational units (blue/gray if has_employees, orange if FTE=0)
  - 'person': individual employees/caselline (green boxes with role badges)

Supports 6 JS-side layouts (no Streamlit rerun):
  H - Albero Orizzontale (LR tree)
  V - Albero Verticale   (top-down tree)
  S - Sunburst           (radial partition)
  T - Treemap            (squarified)
  P - Pannelli           (Finder-style columns)
  C - Card Grid          (OrgVue-style cards)
"""
import streamlit as st
import streamlit.components.v1 as components
import json
from typing import Optional

from services.orgchart_data_service import get_orgchart_data_service
from services.lookup_service import get_lookup_service


def render_orgchart_positions_view():
    """Render Unità Organizzative orgchart with strutture + personale as separate nodes."""

    orgchart_service = get_orgchart_data_service()
    lookup_service = get_lookup_service()

    # ========== FILTERS & SEARCH ==========
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

    with col1:
        search_query = st.text_input(
            "🔍 Cerca struttura o dipendente",
            placeholder="Nome struttura o dipendente…",
            key="org_pos_search"
        )

    with col2:
        companies = lookup_service.get_company_names()
        company_filter = st.selectbox(
            "Società", options=["Tutte"] + companies, key="org_pos_company"
        )

    with col3:
        show_vacant_only = st.checkbox("Solo vacanti (FTE=0)", key="org_pos_vacant")

    with col4:
        st.button("📥 Export PNG", use_container_width=True, disabled=True,
                  help="Disponibile nel layout Albero con tasto destro → Salva immagine")

    # ========== LOAD DATA ==========
    with st.spinner("Caricamento organigramma…"):
        try:
            data = orgchart_service.get_positions_tree()
            nodes = data.get('nodes', [])

            if not nodes:
                st.warning("Nessun dato disponibile per le unità organizzative")
                st.info("Importa strutture e personale nel database per visualizzare l'organigramma.")
                return

            # Apply vacant filter if requested
            if show_vacant_only:
                # Keep vacant strutture + their ancestors for context
                vacant_ids = {n['id'] for n in nodes if n['node_type']=='struttura' and not n['has_employees']}
                # Build ancestor set
                ancestor_ids = set(vacant_ids)
                changed = True
                while changed:
                    changed = False
                    for n in nodes:
                        if n['id'] in ancestor_ids and n['parentId']:
                            if n['parentId'] not in ancestor_ids:
                                ancestor_ids.add(n['parentId'])
                                changed = True
                # Filter: vacant strutture + their ancestors only
                nodes = [n for n in nodes if n['id'] in ancestor_ids]

            strutture_count = sum(1 for n in nodes if n['node_type']=='struttura')
            person_count = sum(1 for n in nodes if n['node_type']=='person')
            vacant_count = sum(1 for n in nodes if n['node_type']=='struttura' and not n['has_employees'])
            filled_count = strutture_count - vacant_count

            hierarchy_json = json.dumps(nodes, ensure_ascii=False)

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
  padding:2px 7px;border-radius:4px;font-size:11px;width:200px;outline:none}}
#search-input:focus{{border-color:#3b82f6}}
.btn{{background:#1e293b;border:1px solid #334155;color:#cbd5e1;
  padding:2px 8px;border-radius:4px;font-size:11px;cursor:pointer;
  white-space:nowrap;transition:all .15s}}
.btn:hover{{background:#3b82f6;border-color:#3b82f6;color:#fff}}
.sep{{width:1px;background:#334155;height:18px;flex-shrink:0}}
#legend{{display:flex;gap:8px;font-size:10px;color:#64748b;align-items:center}}
.ld{{width:8px;height:8px;border-radius:2px;border:2px solid;display:inline-block;
  vertical-align:middle;margin-right:2px}}
#info{{font-size:10px;color:#475569;margin-left:auto}}

/* ── svg canvas ── */
#svg-area{{flex:1;overflow:hidden;cursor:grab}}
#svg-area:active{{cursor:grabbing}}
svg{{width:100%;height:100%}}

/* ── tree nodes: STRUTTURA (org units) ── */
.node-g{{cursor:pointer}}
.node-box{{fill:#1e293b;stroke:#334155;stroke-width:1.5;rx:4}}
.node-g:hover .node-box{{stroke:#3b82f6;fill:#1a2e4a}}
.node-box.struttura-filled{{stroke:#3b82f6;fill:#1e3a5f}}
.node-box.struttura-vacant{{stroke:#f59e0b;fill:#1c1608}}
.node-box.person{{stroke:#22c55e;fill:#0d3320}}
.node-box.collapsed{{stroke:#6366f1}}
.node-box.hl{{stroke:#f59e0b;stroke-width:2.5;fill:#2a2000}}
.nd-name{{fill:#e2e8f0;font-size:11px;font-weight:600;pointer-events:none}}
.nd-type{{fill:#64748b;font-size:8.5px;pointer-events:none}}
.nd-roles{{fill:#cbd5e1;font-size:8.5px;pointer-events:none}}
.nd-vacant{{fill:#f59e0b;font-size:9px;pointer-events:none}}
.nd-cnt{{fill:#86efac;font-size:9px;pointer-events:none}}
.tog-c{{fill:#1d4ed8;stroke:#0f172a;stroke-width:1;cursor:pointer}}
.tog-c:hover{{fill:#3b82f6}}
.tog-t{{fill:#fff;font-size:8.5px;text-anchor:middle;dominant-baseline:central;pointer-events:none}}
.link{{fill:none;stroke:#1e3a5f;stroke-width:1.5}}

/* ── role badges ── */
.role-badge{{rx:2}}
.rb-text{{fill:#fff;font-size:7.5px;text-anchor:middle;dominant-baseline:central;pointer-events:none}}

/* ── sunburst ── */
.sb-arc{{cursor:pointer}}
.sb-label{{pointer-events:none;dominant-baseline:central}}

/* ── treemap ── */
.tm-node{{cursor:pointer}}
.tm-rect{{stroke:#0f172a;stroke-width:0.5}}
.tm-label{{pointer-events:none;dominant-baseline:hanging}}
.tm-info{{pointer-events:none;dominant-baseline:hanging}}

/* ── panels (Finder) ── */
#panels-container{{flex:1;display:none;overflow-x:auto;overflow-y:hidden;flex-direction:row}}
.panel-col{{min-width:240px;border-right:1px solid #334155;overflow-y:auto;flex-shrink:0;background:#1e293b}}
.panel-item{{padding:7px 10px;cursor:pointer;display:flex;align-items:center;
  border-bottom:1px solid #1a2535;gap:6px}}
.panel-item:hover{{background:#263348}}
.panel-item.selected{{background:#1d4ed8}}
.pi-name{{font-size:12px;color:#e2e8f0;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.pi-type{{font-size:9px;color:#475569;padding:1px 4px;border-radius:2px;border:1px solid #334155}}
.pi-type.struttura{{background:#1e3a5f}}
.pi-type.person{{background:#0d3320;border-color:#22c55e}}
.pi-roles{{display:flex;gap:2px}}
.pi-rb{{background:#2563eb;color:#fff;font-size:8px;padding:1px 3px;border-radius:2px}}
.pi-rb.App{{background:#16a34a}}
.pi-rb.Viag{{background:#0891b2}}
.pi-rb.Contr{{background:#d97706}}
.pi-rb.Cass{{background:#dc2626}}
.pi-count{{font-size:10px;color:#64748b;white-space:nowrap}}
.pi-arrow{{color:#64748b;font-size:16px;margin-left:3px;line-height:1}}
.panel-item.selected .pi-name{{color:#fff}}
.panel-item.selected .pi-count,.panel-item.selected .pi-arrow{{color:#93c5fd}}

/* ── card grid ── */
#card-grid-container{{flex:1;display:none;overflow:auto;padding:10px;background:#0f172a}}
.orgcard{{background:#1e293b;border:1px solid #334155;border-radius:6px;
  padding:9px;cursor:pointer;transition:border-color 150ms}}
.orgcard:hover{{border-color:#3b82f6}}
.orgcard-struttura{{border-left:3px solid #3b82f6}}
.orgcard-vacant{{border-left:3px solid #f59e0b;background:#1a1208}}
.orgcard-person{{border-left:3px solid #22c55e;background:#0d2217}}
.oc-header{{margin-bottom:6px;border-bottom:1px solid #1a2535;padding-bottom:5px}}
.oc-name{{font-weight:600;font-size:12px;color:#e2e8f0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.oc-type{{font-size:9px;color:#64748b}}
.oc-roles{{display:flex;gap:3px;flex-wrap:wrap;margin-top:4px}}
.oc-rb{{background:#2563eb;color:#fff;font-size:8px;padding:2px 5px;border-radius:3px}}
.oc-rb.App{{background:#16a34a}}
.oc-rb.Viag{{background:#0891b2}}
.oc-rb.Contr{{background:#d97706}}
.oc-rb.Cass{{background:#dc2626}}
.oc-vacant-badge{{color:#f59e0b;font-size:10px;padding:2px 0}}
.oc-stat{{font-size:10px;color:#64748b;margin-top:3px}}

/* ── tooltip ── */
#tooltip{{display:none;position:fixed;background:#1e293b;border:1px solid #475569;
  border-radius:4px;padding:4px 8px;font-size:11px;color:#e2e8f0;
  pointer-events:none;z-index:200;max-width:260px}}

/* ── modal ── */
#ov{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:99}}
#modal{{display:none;position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);
  background:#1e293b;border:1px solid #334155;border-radius:8px;
  width:440px;max-height:80vh;flex-direction:column;overflow:hidden;z-index:100}}
#mh{{padding:10px 14px;border-bottom:1px solid #334155;display:flex;align-items:flex-start;
  gap:8px;background:#0f172a}}
#mt{{font-size:12px;font-weight:700;color:#e2e8f0;flex:1;line-height:1.3}}
#mc{{font-size:9px;color:#475569}}
#mx{{background:none;border:none;color:#64748b;cursor:pointer;font-size:16px;padding:0}}
#mx:hover{{color:#ef4444}}
#ms{{padding:6px 14px;background:#0f172a;border-bottom:1px solid #1e293b;
  font-size:10px;color:#64748b;flex-shrink:0}}
#ms b{{color:#e2e8f0}}
#minfo{{padding:10px 14px;background:#1a2535;border-bottom:1px solid #1e293b;
  font-size:10px;color:#cbd5e1;line-height:1.5}}
.mroles{{display:flex;gap:4px;flex-wrap:wrap;margin-top:5px}}
.mr{{padding:2px 6px;border-radius:3px;font-size:9px;font-weight:600;color:#fff}}
.mr.App{{background:#16a34a}}
.mr.Viag{{background:#0891b2}}
.mr.Contr{{background:#d97706}}
.mr.Cass{{background:#dc2626}}
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
    <span style="margin-left:auto;font-size:10px;color:#64748b;display:flex;align-items:center;gap:8px">
      <span style="color:#3b82f6">🏢 {strutture_count} strutture</span>
      <span style="color:#22c55e">👤 {person_count} dipendenti</span>
      <span style="color:#f59e0b">⬜ {vacant_count} vacanti</span>
    </span>
  </div>

  <!-- Standard toolbar -->
  <div id="toolbar">
    <input id="search-input" placeholder="Cerca struttura o dipendente…" oninput="doSearch(this.value)"/>
    <div class="sep"></div>
    <button class="btn" id="btn-reset" onclick="resetView()">&#8635; Reset</button>
    <button class="btn" id="btn-expand" onclick="expandOne()">+1 Livello</button>
    <button class="btn" id="btn-collapse" onclick="collapseAll()">Chiudi tutti</button>
    <button class="btn" onclick="goFullscreen()">&#x26F6; Fullscreen</button>
    <div class="sep"></div>
    <div id="legend">
      <span><i class="ld" style="border-color:#3b82f6"></i>Struttura org</span>
      <span><i class="ld" style="border-color:#22c55e"></i>Dipendente</span>
      <span><i class="ld" style="border-color:#f59e0b"></i>Vacante (FTE=0)</span>
    </div>
    <span id="info">{strutture_count + person_count} nodi &nbsp;·&nbsp; click=espandi &nbsp;·&nbsp; dbl-click=dettagli</span>
  </div>

  <!-- Content areas -->
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
  <div id="ms"></div>
  <div id="minfo"></div>
</div>

<script>
const RAW = {hierarchy_json};

// ── Stratify ──────────────────────────────────────────────────────────────
const stratify = d3.stratify().id(d=>d.id).parentId(d=>d.parentId);
let root;
try {{ root = stratify(RAW); }}
catch(e) {{
  document.body.innerHTML='<div style="padding:20px;color:#ef4444">Errore gerarchia: '+e.message+'</div>';
  throw e;
}}
root.each(d=>{{ if(d.depth>=1&&d.children){{ d._ch=d.children; d.children=null; }} }});

// ── Constants ─────────────────────────────────────────────────────────────
// Struttura nodes: larger boxes
const SNW=180, SNH=50;
// Person nodes: smaller "casellina" boxes
const PNW=140, PNH=42;
// Tree spacing
const ROW_H=70, COL_W=210;
const VGX=170, VGY=90;

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
  }}
}});

let currentLayout='h';

// ── Layout switcher ───────────────────────────────────────────────────────
function setLayout(type) {{
  document.querySelectorAll('.ls-btn').forEach(b=>b.classList.remove('active'));
  document.getElementById('btn-'+type).classList.add('active');
  currentLayout=type;

  const svgArea=document.getElementById('svg-area');
  const panelsEl=document.getElementById('panels-container');
  const cardsEl=document.getElementById('card-grid-container');

  svgArea.style.display='none';
  panelsEl.style.display='none';
  cardsEl.style.display='none';

  g.selectAll('*').remove();
  g.attr('transform','');

  const treeOnly = type==='h'||type==='v';
  document.getElementById('btn-expand').style.display=treeOnly?'':'none';
  document.getElementById('btn-collapse').style.display=treeOnly?'':'none';
  document.getElementById('btn-reset').style.display=treeOnly?'':'none';

  if(treeOnly) {{
    svg.call(zoom);
    svgArea.style.cssText='flex:1;overflow:hidden;cursor:grab';
  }} else {{
    svg.on('.zoom',null);
    svgArea.style.cssText='flex:1;overflow:hidden;cursor:default';
  }}

  if(['h','v','s','t'].includes(type)) {{
    svgArea.style.display='';
  }} else if(type==='p') {{
    panelsEl.style.cssText='flex:1;display:flex;overflow-x:auto;overflow-y:hidden';
  }} else if(type==='c') {{
    cardsEl.style.cssText='flex:1;display:block;overflow:auto;padding:10px;background:#0f172a';
  }}

  ({{h:drawHorizontal,v:drawVertical,s:drawSunburst,t:drawTreemap,p:drawPanels,c:drawCardGrid}}[type])();

  if(treeOnly) setTimeout(resetView,80);
}}

// ── Helpers ───────────────────────────────────────────────────────────────
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

  // Show all descendants of focused node
  const descendants = getDescendants(focusedNode);
  if (descendants.includes(node)) return true;

  // Hide everything else (siblings and their branches)
  return false;
}}

function toggle(d) {{
  if(d.children){{
    // Collapsing - set as focused to hide other branches
    focusedNode = d;
    d._ch=d.children;
    d.children=null;
  }}
  else if(d._ch){{
    // Expanding - keep focus to filter visibility
    focusedNode = d;
    d.children=d._ch;
    d._ch=null;
  }}
  g.selectAll('*').remove();
  if(currentLayout==='h') drawHorizontal();
  else if(currentLayout==='v') drawVertical();
}}

function nodeClass(d) {{
  if(d.data._hl) return 'node-box hl';
  if(d._ch) return 'node-box collapsed';
  if(d.data.node_type==='person') return 'node-box person';
  // struttura
  if(d.data.has_employees) return 'node-box struttura-filled';
  return 'node-box struttura-vacant';
}}

function nodeW(d) {{ return d.data.node_type==='person' ? PNW : SNW; }}
function nodeH(d) {{ return d.data.node_type==='person' ? PNH : SNH; }}

// Draw role badges for person nodes
function drawRoles(nodeG, roles, nw, y) {{
  if(!roles || !roles.length) return;
  const colors = {{App:'#16a34a',Viag:'#0891b2',Contr:'#d97706',Cass:'#dc2626'}};
  const bw=28, bh=11, gap=2;
  const startX = (nw - roles.length*bw - (roles.length-1)*gap)/2;
  roles.slice(0,4).forEach((r,i)=>{{
    const x = startX + i*(bw+gap);
    nodeG.append('rect').attr('class','role-badge')
      .attr('x',x).attr('y',y).attr('width',bw).attr('height',bh)
      .attr('fill',colors[r]||'#475569');
    nodeG.append('text').attr('class','rb-text')
      .attr('x',x+bw/2).attr('y',y+bh/2).text(r);
  }});
}}

// ── LAYOUT H: Horizontal Tree ─────────────────────────────────────────────
function drawHorizontal() {{
  const tree=d3.tree().nodeSize([ROW_H,COL_W]);
  tree(root);
  const nodes=root.descendants(), links=root.links();

  const lk=g.selectAll('.link').data(links,d=>d.source.id+'>'+d.target.id);
  lk.enter().insert('path','.node-g').attr('class','link')
    .merge(lk).transition().duration(200)
    .attr('d',d=>{{
      const snw=nodeW(d.source), snh=nodeH(d.source);
      const tnw=nodeW(d.target), tnh=nodeH(d.target);
      const sx=d.source.y+snw, sy=d.source.x+snh/2;
      const tx=d.target.y,    ty=d.target.x+tnh/2;
      const mx=(sx+tx)/2;
      return `M${{sx}},${{sy}} L${{mx}},${{sy}} L${{mx}},${{ty}} L${{tx}},${{ty}}`;
    }});
  lk.exit().remove();

  const nd=g.selectAll('.node-g').data(nodes,d=>d.id);
  const ne=nd.enter().append('g').attr('class','node-g')
    .attr('transform',d=>`translate(${{d.y}},${{d.x}})`)
    .on('click',  (ev,d)=>{{ev.stopPropagation();toggle(d);}})
    .on('dblclick',(ev,d)=>{{ev.stopPropagation();openModal(d);}});

  ne.each(function(d) {{
    const nw=nodeW(d), nh=nodeH(d);
    const g=d3.select(this);
    g.append('rect').attr('class','node-box').attr('width',nw).attr('height',nh);
    g.append('text').attr('class','nd-name').attr('x',6).attr('y',14)
      .text(cut(d.data.name, d.data.node_type==='person'?18:24));
    g.append('text').attr('class','nd-type').attr('x',6).attr('y',nh-5)
      .text(d.data.node_type==='struttura'?'🏢 Struttura':'👤 Dipendente');

    if(d.data.node_type==='person') {{
      drawRoles(g, d.data.roles, nw, 22);
    }} else if(!d.data.has_employees) {{
      g.append('text').attr('class','nd-vacant').attr('x',nw-6).attr('y',14)
        .attr('text-anchor','end').text('⬜ FTE=0');
    }}

    // Toggle badge
    const bg=g.append('g').attr('class','bg').attr('transform',`translate(${{nw}},${{nh/2}})`);
    bg.append('circle').attr('class','tog-c').attr('r',8)
      .on('click',(ev,dd)=>{{ev.stopPropagation();toggle(dd);}});
    bg.append('text').attr('class','tog-t').text(cc(d));
  }});

  const nu=ne.merge(nd);
  nu.transition().duration(200).attr('transform',d=>`translate(${{d.y}},${{d.x}})`);
  nu.select('.node-box').attr('class',nodeClass);
  nu.select('.nd-name').text(d=>cut(d.data.name, d.data.node_type==='person'?18:24));
  nu.select('.bg').style('display',d=>(d.children||d._ch)?'block':'none');
  nu.select('.tog-t').text(d=>cc(d));
  nd.exit().remove();
}}

// ── LAYOUT V: Vertical Tree (con wrapping automatico) ─────────────────────
function drawVertical() {{
  // Calcola larghezza disponibile e wrapping
  const el=document.getElementById('svg-area');
  const availableWidth = (el.clientWidth || 1200) - 100;
  const maxNodesPerRow = Math.max(1, Math.floor(availableWidth / VGX));

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

  // Riposiziona con wrapping
  Object.keys(nodesByLevel).forEach(depth => {{
    const levelNodes = nodesByLevel[depth];
    levelNodes.forEach((d, i) => {{
      const row = Math.floor(i / maxNodesPerRow);
      const colInRow = i % maxNodesPerRow;
      const nodesInThisRow = Math.min(maxNodesPerRow, levelNodes.length - row * maxNodesPerRow);
      const rowWidth = nodesInThisRow * VGX;
      const rowStartX = -rowWidth / 2;
      d.x = rowStartX + colInRow * VGX + VGX / 2;
      d.y = parseInt(depth) * VGY + row * (VGY + 20);
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
      const snh=nodeH(d.source);
      const sx=d.source.x, sy=d.source.y+snh;
      const tx=d.target.x, ty=d.target.y;
      const my=(sy+ty)/2;
      return `M${{sx}},${{sy}} C${{sx}},${{my}} ${{tx}},${{my}} ${{tx}},${{ty}}`;
    }});
  lk.exit().remove();

  const nd=g.selectAll('.node-g').data(nodes,d=>d.id);
  const ne=nd.enter().append('g').attr('class','node-g')
    .attr('transform',d=>`translate(${{d.x-nodeW(d)/2}},${{d.y}})`)
    .on('click',  (ev,d)=>{{ev.stopPropagation();toggle(d);}})
    .on('dblclick',(ev,d)=>{{ev.stopPropagation();openModal(d);}});

  ne.each(function(d) {{
    const nw=nodeW(d), nh=nodeH(d);
    const g=d3.select(this);
    g.append('rect').attr('class','node-box').attr('width',nw).attr('height',nh);
    g.append('text').attr('class','nd-name').attr('x',5).attr('y',13)
      .text(cut(d.data.name, d.data.node_type==='person'?16:21));
    g.append('text').attr('class','nd-type').attr('x',5).attr('y',nh-4)
      .text(d.data.node_type==='struttura'?'🏢':'👤');

    if(d.data.node_type==='person') {{
      drawRoles(g, d.data.roles, nw, 21);
    }} else if(!d.data.has_employees) {{
      g.append('text').attr('class','nd-vacant').attr('x',nw-5).attr('y',13)
        .attr('text-anchor','end').text('⬜ FTE=0');
    }}

    const bg=g.append('g').attr('class','bg').attr('transform',`translate(${{nw/2}},${{nh}})`);
    bg.append('circle').attr('class','tog-c').attr('r',8)
      .on('click',(ev,dd)=>{{ev.stopPropagation();toggle(dd);}});
    bg.append('text').attr('class','tog-t').text(cc(d));
  }});

  const nu=ne.merge(nd);
  nu.transition().duration(200).attr('transform',d=>`translate(${{d.x-nodeW(d)/2}},${{d.y}})`);
  nu.select('.node-box').attr('class',nodeClass);
  nu.select('.nd-name').text(d=>cut(d.data.name, d.data.node_type==='person'?16:21));
  nu.select('.bg').style('display',d=>(d.children||d._ch)?'block':'none');
  nu.select('.tog-t').text(d=>cc(d));
  nd.exit().remove();
}}

// ── LAYOUT S: Sunburst ────────────────────────────────────────────────────
function drawSunburst() {{
  const el=document.getElementById('svg-area');
  const W=el.clientWidth||800, H=el.clientHeight||700;
  const radius=Math.min(W,H)/2 - 20;

  const sroot=stratify(RAW.map(d=>Object.assign({{}},d)));
  sroot.sum(d=>1);
  d3.partition().size([2*Math.PI, radius])(sroot);

  const arc=d3.arc()
    .startAngle(d=>d.x0).endAngle(d=>d.x1)
    .padAngle(d=>Math.min((d.x1-d.x0)/2, 0.003))
    .innerRadius(d=>d.y0).outerRadius(d=>d.y1-1);

  const strutturaColors=['#1e3a8a','#1d4ed8','#1e40af','#2563eb','#3b82f6','#60a5fa'];
  const personColors=['#14532d','#15803d','#16a34a','#22c55e','#4ade80','#86efac'];
  const vacantColors=['#78350f','#92400e','#b45309','#d97706','#f59e0b','#fcd34d'];

  g.attr('transform',`translate(${{W/2}},${{H/2}})`);

  g.selectAll('.sb-arc').data(sroot.descendants().filter(d=>d.depth>0))
    .join('path').attr('class','sb-arc')
    .attr('d',arc)
    .attr('fill',d=>{{
      if(d.data.node_type==='person') {{
        return personColors[Math.min(d.depth,personColors.length-1)];
      }}
      const palette = d.data.has_employees ? strutturaColors : vacantColors;
      return palette[Math.min(d.depth,palette.length-1)];
    }})
    .attr('stroke','#0f172a').attr('stroke-width',0.5)
    .on('mouseover',(ev,d)=>{{
      const typeLabel = d.data.node_type==='person'?'Dipendente':'Struttura';
      const info = d.data.node_type==='struttura'&&!d.data.has_employees?' (FTE=0)':'';
      showTip(ev, d.data.name+' — '+typeLabel+info);
    }})
    .on('mouseout',hideTip)
    .on('click',(ev,d)=>openModal(d));

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

// ── LAYOUT T: Treemap ─────────────────────────────────────────────────────
function drawTreemap() {{
  const el=document.getElementById('svg-area');
  const W=el.clientWidth||800, H=el.clientHeight||700;

  const troot=stratify(RAW.map(d=>Object.assign({{}},d)));
  troot.sum(d=>1).sort((a,b)=>b.value-a.value);
  d3.treemap().size([W,H]).padding(1).paddingTop(18).round(true)(troot);

  g.attr('transform','');

  const strutturaColors=['#0f172a','#1e3a8a','#1e40af','#1d4ed8','#2563eb','#3b82f6'];
  const personColors=['#0a2108','#14532d','#15803d','#16a34a','#22c55e','#86efac'];
  const vacantColors=['#1c1204','#78350f','#92400e','#b45309','#d97706','#fcd34d'];

  const cell=g.selectAll('.tm-node')
    .data(troot.descendants().filter(d=>d.depth>0))
    .join('g').attr('class','tm-node')
    .attr('transform',d=>`translate(${{d.x0}},${{d.y0}})`);

  cell.append('rect').attr('class','tm-rect')
    .attr('width', d=>Math.max(0,d.x1-d.x0))
    .attr('height',d=>Math.max(0,d.y1-d.y0))
    .attr('fill',d=>{{
      if(d.data.node_type==='person') {{
        return personColors[Math.min(d.depth,personColors.length-1)];
      }}
      const palette = d.data.has_employees ? strutturaColors : vacantColors;
      return palette[Math.min(d.depth,palette.length-1)];
    }})
    .on('mouseover',(ev,d)=>{{
      const typeLabel = d.data.node_type==='person'?'👤 Dipendente':'🏢 Struttura';
      const info = d.data.node_type==='struttura'&&!d.data.has_employees?' (FTE=0)':'';
      showTip(ev,d.data.name+' — '+typeLabel+info);
    }})
    .on('mouseout',hideTip)
    .on('click',(ev,d)=>openModal(d));

  cell.filter(d=>(d.x1-d.x0)>50&&(d.y1-d.y0)>20)
    .append('text').attr('class','tm-label')
    .attr('x',4).attr('y',13).attr('font-size','10px').attr('fill','#e2e8f0')
    .text(d=>cut(d.data.name,Math.max(1,Math.floor((d.x1-d.x0-8)/7))));

  cell.filter(d=>(d.x1-d.x0)>50&&(d.y1-d.y0)>30)
    .append('text').attr('class','tm-info')
    .attr('x',4).attr('y',27).attr('font-size','9px')
    .attr('fill',d=>d.data.node_type==='person'?'#86efac':'#94a3b8')
    .text(d=>{{
      if(d.data.node_type==='person') {{
        return '👤 '+(d.data.roles||[]).join(' ');
      }}
      return d.data.has_employees?'🏢 Struttura':'⬜ FTE=0';
    }});
}}

// ── LAYOUT P: Panels (Finder-style) ──────────────────────────────────────
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

      const typeHtml = node.node_type==='struttura'
        ? '<span class="pi-type struttura">🏢 Stru</span>'
        : '<span class="pi-type person">👤 Dip</span>';

      const rolesHtml = node.node_type==='person'&&node.roles&&node.roles.length
        ? '<div class="pi-roles">'+node.roles.slice(0,2).map(r=>`<span class="pi-rb ${{r}}">${{r}}</span>`).join('')+'</div>'
        : '';

      const vacantHtml = node.node_type==='struttura'&&!node.has_employees
        ? '<span style="color:#f59e0b;font-size:9px">⬜ FTE=0</span>'
        : '';

      item.innerHTML=
        `<span class="pi-name" title="${{node.name}}">${{cut(node.name,20)}}</span>`+
        typeHtml+rolesHtml+vacantHtml+
        `<div style="display:flex;align-items:center;gap:2px">`+
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

// ── LAYOUT C: Card Grid ───────────────────────────────────────────────────
function drawCardGrid() {{
  const container=document.getElementById('card-grid-container');
  container.innerHTML='';
  container.style.cssText=
    'flex:1;display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));'+
    'gap:8px;padding:10px;overflow:auto;background:#0f172a;';

  // Sort: strutture first, then persons
  const sorted=[...RAW].sort((a,b)=>{{
    if(a.node_type==='struttura'&&b.node_type==='person') return -1;
    if(a.node_type==='person'&&b.node_type==='struttura') return 1;
    if(a.node_type==='struttura') {{
      if(a.has_employees&&!b.has_employees) return -1;
      if(!a.has_employees&&b.has_employees) return 1;
    }}
    return 0;
  }});

  sorted.forEach(node=>{{
    const card=document.createElement('div');
    let cardClass='orgcard ';
    if(node.node_type==='person') cardClass+='orgcard-person';
    else if(node.has_employees) cardClass+='orgcard-struttura';
    else cardClass+='orgcard-vacant';
    card.className=cardClass;

    let contentHtml='';
    if(node.node_type==='struttura') {{
      contentHtml=
        `<div class="oc-header">`+
          `<div class="oc-name" title="${{node.name}}">${{cut(node.name,26)}}</div>`+
          `<div class="oc-type">🏢 Struttura org &bull; ID: ${{node.id}}</div>`+
        `</div>`+
        (node.has_employees
          ? `<div class="oc-stat">✅ Con dipendenti</div>`
          : `<div class="oc-vacant-badge">⬜ Posizione vacante (FTE=0)</div>`);
    }} else {{
      const rolesHtml = node.roles&&node.roles.length
        ? `<div class="oc-roles">${{node.roles.map(r=>`<span class="oc-rb ${{r}}">${{r}}</span>`).join('')}}</div>`
        : '';
      contentHtml=
        `<div class="oc-header">`+
          `<div class="oc-name" title="${{node.name}}">${{cut(node.name,26)}}</div>`+
          `<div class="oc-type">👤 Dipendente &bull; CF: ${{node.id.slice(0,8)}}&hellip;</div>`+
        `</div>`+
        rolesHtml+
        `<div class="oc-stat">ID: ${{node.id}}</div>`;
    }}

    card.innerHTML=contentHtml;
    card.onclick=()=>openModal({{data:node}});
    container.appendChild(card);
  }});
}}

// ── Toolbar ───────────────────────────────────────────────────────────────
function resetView() {{
  // Reset focus to show all nodes
  focusedNode = null;
  const el=document.getElementById('svg-area');
  const w=el.clientWidth, h=el.clientHeight;
  if(currentLayout==='h') {{
    svg.transition().duration(300).call(zoom.transform,
      d3.zoomIdentity.translate(30,h/2).scale(0.75));
  }} else if(currentLayout==='v') {{
    svg.transition().duration(300).call(zoom.transform,
      d3.zoomIdentity.translate(w/2,40).scale(0.75));
  }}
  // Redraw to show all nodes
  g.selectAll('*').remove();
  if(currentLayout==='h') drawHorizontal();
  else if(currentLayout==='v') drawVertical();
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
}}

function collapseAll() {{
  // Reset focus when collapsing all
  focusedNode = null;
  root.each(d=>{{if(d.depth>=1&&d.children){{d._ch=d.children;d.children=null;}}}});
  g.selectAll('*').remove();
  if(currentLayout==='h') drawHorizontal(); else drawVertical();
  setTimeout(resetView,250);
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
  root.each(d=>{{
    if(d.data.name.toLowerCase().includes(q)){{d.data._hl=true;if(!found)found=d;}}
  }});
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

// ── Tooltip ───────────────────────────────────────────────────────────────
function showTip(ev,text) {{
  const t=document.getElementById('tooltip');
  t.textContent=text;
  t.style.left=(ev.clientX+12)+'px';
  t.style.top=(ev.clientY-8)+'px';
  t.style.display='block';
}}
function hideTip() {{ document.getElementById('tooltip').style.display='none'; }}

// ── Modal ─────────────────────────────────────────────────────────────────
function openModal(d) {{
  const data = d.data || d;
  document.getElementById('mt').textContent = data.name;
  document.getElementById('mc').textContent = 'ID: '+data.id;

  let statusHtml='';
  if(data.node_type==='struttura') {{
    statusHtml = data.has_employees
      ? '<b>✅ Struttura con dipendenti assegnati</b>'
      : '<span style="color:#f59e0b">⬜ Struttura vacante — FTE = 0</span>';
  }} else {{
    statusHtml = '<b>👤 Dipendente (Casellina)</b>';
  }}
  document.getElementById('ms').innerHTML = statusHtml;

  let infoHtml='';
  if(data.node_type==='person' && data.roles && data.roles.length) {{
    infoHtml='<div><b>Ruoli assegnati:</b></div>'+
      '<div class="mroles">'+data.roles.map(r=>`<span class="mr ${{r}}">${{r}}</span>`).join('')+'</div>';
  }} else if(data.node_type==='struttura') {{
    infoHtml='<div>Tipo: <b>Unità Organizzativa</b></div>'+
      '<div>Codice: <b>'+data.id+'</b></div>'+
      '<div>Parent ID: <b>'+(data.parentId||'(radice)')+'</b></div>';
  }}
  document.getElementById('minfo').innerHTML = infoHtml||'<div style="color:#64748b">Nessuna informazione aggiuntiva</div>';

  document.getElementById('ov').style.display='block';
  document.getElementById('modal').style.display='flex';
}}

function closeModal() {{
  document.getElementById('ov').style.display='none';
  document.getElementById('modal').style.display='none';
}}

// ── Init ──────────────────────────────────────────────────────────────────
drawHorizontal();
setTimeout(resetView,120);
</script>
</body></html>"""

            components.html(html_content, height=1060, scrolling=False)

            # ── Streamlit side stats ──
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("🏢 Strutture org", strutture_count)
            with c2:
                st.metric("👤 Dipendenti", person_count)
            with c3:
                st.metric("⬜ Vacanti (FTE=0)", vacant_count)
            with c4:
                perc = round(filled_count / strutture_count * 100) if strutture_count else 0
                st.metric("Copertura", f"{perc}%")

            with st.expander("📖 Legenda e Istruzioni"):
                st.markdown("""
**Layout disponibili (switcher in alto):**
- 🌲 **Albero H** — Tree orizzontale LR; click=espandi/collassa, dbl-click=dettagli
- 🏛️ **Albero V** — Tree verticale top-down
- ☀️ **Sunburst** — Blu=strutture, Verde=dipendenti, Arancione=vacante (FTE=0)
- 📦 **Treemap** — Rettangoli proporzionali; colori per tipo e stato
- 🗂️ **Pannelli** — Finder-style: click colonna → figli a destra
- 📋 **Card Grid** — Schede separate per strutture e dipendenti

**Due tipi di nodo:**
- 🏢 **Struttura org** — Box blu (con dipendenti) o arancione (vacante, FTE=0)
- 👤 **Dipendente** — Box verde con badge ruoli (App, Viag, Contr, Cass)

**Search**: cerca nome struttura o dipendente (evidenzia il nodo pertinente)

**Nota**: Tutte le 875 righe del file sono visualizzate come nodi separati nell'albero gerarchico.
                """)

        except Exception as e:
            st.error(f"❌ Errore durante caricamento organigramma: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
