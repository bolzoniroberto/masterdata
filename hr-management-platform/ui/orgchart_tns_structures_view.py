"""
Orgchart TNS Structures View - Multi-Layout

Interactive organizational chart showing TNS structures with their approvers.
Supports 4 JS-side layouts (no Streamlit rerun):
  H - Albero Orizzontale (LR tree)
  V - Albero Verticale   (top-down tree)
  S - Sunburst           (radial partition)
  T - Treemap            (squarified rectangles)

Nodes with no approver have orange border + ⚠ indicator.
"""
import streamlit as st
import streamlit.components.v1 as components
import json
from typing import Optional

from services.orgchart_data_service import get_orgchart_data_service
from services.lookup_service import get_lookup_service


def render_orgchart_tns_structures_view():
    """Render TNS Structures orgchart view with multi-layout switcher"""

    orgchart_service = get_orgchart_data_service()
    lookup_service = get_lookup_service()

    # ========== FILTERS & SEARCH ==========
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

    with col1:
        search_query = st.text_input(
            "🔍 Cerca struttura",
            placeholder="Nome struttura…",
            key="org_tns_search"
        )

    with col2:
        companies = lookup_service.get_company_names()
        company_filter = st.selectbox(
            "Società", options=["Tutte"] + companies, key="org_tns_company"
        )

    with col3:
        areas = lookup_service.get_areas()
        area_filter = st.selectbox(
            "Area", options=["Tutte"] + areas, key="org_tns_area"
        )

    with col4:
        st.button("📥 Export PNG", use_container_width=True, disabled=True,
                  help="Disponibile nel layout Albero con tasto destro → Salva immagine")

    # ========== LOAD DATA ==========
    with st.spinner("Caricamento organigramma TNS…"):
        try:
            hierarchy_data = orgchart_service.get_tns_hierarchy_tree(
                company_id=None,
                area_filter=None if area_filter == "Tutte" else area_filter
            )

            nodes = hierarchy_data.get('nodes', [])
            if not nodes:
                st.warning("Nessun dato disponibile per l'organigramma TNS Strutture")
                st.info("Verifica che siano state importate strutture nel database.")
                return

            # Count structures without approver for stats
            no_appr_count = sum(1 for n in nodes if not n.get('has_approver', False))
            hierarchy_json = json.dumps(nodes, ensure_ascii=False)

            # Employees grouped by TNS code (for modal detail popup)
            emp_rows = orgchart_service._query("""
                SELECT tx_cod_fiscale, titolare, cod_tns, padre_tns
                FROM employees
                WHERE cod_tns IS NOT NULL AND cod_tns != ''
                ORDER BY titolare
            """)
            emp_by_struttura = {}
            for e in emp_rows:
                tns_code = e['cod_tns']
                if tns_code not in emp_by_struttura:
                    emp_by_struttura[tns_code] = []
                emp_by_struttura[tns_code].append({
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
.node-box.has-appr{{stroke:#22c55e}}
.node-box.no-appr{{stroke:#f59e0b;fill:#1c1608}}
.node-box.collapsed{{stroke:#f59e0b}}
.node-box.hl{{stroke:#f59e0b;stroke-width:2.5;fill:#2a2000}}
.nd-name{{fill:#e2e8f0;font-size:11px;font-weight:600;pointer-events:none}}
.nd-resp{{fill:#64748b;font-size:9.5px;pointer-events:none}}
.nd-resp.warn{{fill:#f59e0b}}
.nd-cnt{{fill:#3b82f6;font-size:9.5px;pointer-events:none}}
.nd-appr{{fill:#22c55e;font-size:9px;pointer-events:none}}
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

/* ── tooltip ── */
#tooltip{{display:none;position:fixed;background:#1e293b;border:1px solid #475569;
  border-radius:4px;padding:4px 8px;font-size:11px;color:#e2e8f0;pointer-events:none;z-index:200;max-width:260px}}

/* ── modal ── */
#ov{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:99}}
#modal{{display:none;position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);
  background:#1e293b;border:1px solid #334155;border-radius:8px;
  width:420px;max-height:78vh;flex-direction:column;overflow:hidden;z-index:100}}
#mh{{padding:10px 14px;border-bottom:1px solid #334155;display:flex;align-items:flex-start;
  gap:8px;background:#0f172a}}
#mt{{font-size:12px;font-weight:700;color:#e2e8f0;flex:1;line-height:1.3}}
#mc{{font-size:9px;color:#475569}}
#mx{{background:none;border:none;color:#64748b;cursor:pointer;font-size:16px;padding:0}}
#mx:hover{{color:#ef4444}}
#ms{{padding:6px 14px;background:#0f172a;border-bottom:1px solid #1e293b;
  display:flex;gap:14px;font-size:10px;color:#64748b;flex-shrink:0}}
#ms b{{color:#e2e8f0}}
#m-appr-list{{padding:6px 14px;background:#0a1120;border-bottom:1px solid #1e293b;
  flex-shrink:0;font-size:10px;min-height:26px}}
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
    <span style="margin-left:auto;font-size:10px;color:#f59e0b;display:flex;align-items:center;gap:4px">
      ⚠️ <b>{no_appr_count}</b> strutture senza approvatore
    </span>
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
      <span><i class="ld" style="border-color:#22c55e"></i>Ha appr.</span>
      <span><i class="ld" style="border-color:#f59e0b"></i>No appr.</span>
      <span><i class="ld" style="border-color:#1d4ed8"></i>Collassato</span>
    </div>
    <span id="info">{node_count} strutture &nbsp;·&nbsp; click=espandi &nbsp;·&nbsp; dbl-click=dettaglio</span>
  </div>

  <!-- Content areas (one visible at a time) -->
  <div id="svg-area"><svg id="svg"><g id="rg"></g></svg></div>

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
  <div id="ms">Dip: <b id="m-d">0</b> &nbsp; Approvatori: <b id="m-a">0</b> &nbsp; Viaggiatori: <b id="m-v">0</b></div>
  <div id="m-appr-list"></div>
  <div id="msi"><input placeholder="Filtra dipendenti…" oninput="filterM(this.value)"/></div>
  <div id="ml"></div>
</div>

<script>
const RAW  = {hierarchy_json};
const EMP  = {emp_json};

// Build approver index from node data
const APPR = {{}};
RAW.forEach(d=>{{ APPR[d.id] = d.approvers || []; }});

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

// ── SVG & zoom ──────────────────────────────────────────────────────────
const ROW_H=48, COL_W=220, NW=200, NH=44;
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

let curEmp=[], currentLayout='h';

// ── LAYOUT SWITCHER ─────────────────────────────────────────────────────
function setLayout(type) {{
  document.querySelectorAll('.ls-btn').forEach(b=>b.classList.remove('active'));
  document.getElementById('btn-'+type).classList.add('active');
  currentLayout=type;

  const svgArea=document.getElementById('svg-area');

  // Clear SVG content
  g.selectAll('*').remove();
  g.attr('transform','');

  // Tree-only toolbar buttons
  const treeOnly = type==='h'||type==='v';
  document.getElementById('btn-expand').style.display=treeOnly?'':'none';
  document.getElementById('btn-collapse').style.display=treeOnly?'':'none';
  document.getElementById('btn-reset').style.display=treeOnly?'':'none';

  // Re-enable or disable zoom
  if(treeOnly) {{
    svg.call(zoom);
    svgArea.style.cssText='flex:1;overflow:hidden;cursor:grab';
  }} else {{
    svg.on('.zoom',null);
    svgArea.style.cssText='flex:1;overflow:hidden;cursor:default';
  }}

  ({{h:drawHorizontal,v:drawVertical,s:drawSunburst,t:drawTreemap}}[type])();

  if(treeOnly) setTimeout(autoFit,80);
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
  setTimeout(autoFit, 100);
}}

function nodeClass(d) {{
  if(d.data._hl)        return 'node-box hl';
  if(d._ch)             return 'node-box collapsed';
  if(d.data.has_approver) return 'node-box has-appr';
  return 'node-box no-appr';
}}

function titleClass(d) {{
  return d.data.has_approver ? 'nd-resp' : 'nd-resp warn';
}}

// ── Approver badge text (up to 2 names + "+N more") ──────────────────
function apprBadge(d) {{
  const appr = d.data.approvers || [];
  if(!appr.length) return '⚠ Nessun approvatore';
  const shorts = appr.slice(0,2).map(a=>{{
    // Show first surname word shortened
    const parts=a.trim().split(' ');
    return '✅ '+(parts[0]||a).slice(0,10);
  }});
  if(appr.length>2) shorts.push('+'+(appr.length-2));
  return shorts.join(' ');
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
    .on('dblclick',(ev,d)=>{{ev.stopPropagation();openModal(d);}});

  ne.append('rect').attr('class','node-box').attr('width',NW).attr('height',NH).attr('rx',4);
  ne.append('text').attr('class','nd-name').attr('x',7).attr('y',14).text(d=>cut(d.data.name,26));
  ne.append('text').attr('class','nd-appr').attr('x',7).attr('y',26).text(d=>cut(apprBadge(d),28));
  ne.append('text').attr('class','nd-cnt') .attr('x',7).attr('y',37).text(d=>d.data.employee_count>0?d.data.employee_count+' dip.':'');

  const bg=ne.append('g').attr('class','bg').attr('transform',`translate(${{NW}},${{NH/2}})`);
  bg.append('circle').attr('class','tog-c').attr('r',8).on('click',(ev,d)=>{{ev.stopPropagation();toggle(d);}});
  bg.append('text').attr('class','tog-t').text(d=>cc(d));

  const nu=ne.merge(nd);
  nu.transition().duration(200).attr('transform',d=>`translate(${{d.y}},${{d.x}})`);
  nu.select('.node-box').attr('class',nodeClass);
  nu.select('.nd-name').text(d=>cut(d.data.name,26));
  nu.select('.nd-appr').text(d=>cut(apprBadge(d),28))
    .attr('fill',d=>d.data.has_approver?'#22c55e':'#f59e0b');
  nu.select('.nd-cnt') .text(d=>d.data.employee_count>0?d.data.employee_count+' dip.':'');
  nu.select('.bg').style('display',d=>(d.children||d._ch)?'block':'none');
  nu.select('.tog-t').text(d=>cc(d));
  nd.exit().remove();
}}

// ── LAYOUT V: Vertical Tree (con wrapping automatico) ────────────────────
function drawVertical() {{
  const VNW=160, VNH=50, VGY=95;

  // Calcola larghezza disponibile e wrapping
  const el=document.getElementById('svg-area');
  const availableWidth = (el.clientWidth || 1200) - 100;
  const VGX = 185;
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
    .on('dblclick',(ev,d)=>{{ev.stopPropagation();openModal(d);}});

  ne.append('rect').attr('class','node-box').attr('width',VNW).attr('height',VNH).attr('rx',4);
  ne.append('text').attr('class','nd-name').attr('x',6).attr('y',14).text(d=>cut(d.data.name,21));
  ne.append('text').attr('class','nd-appr').attr('x',6).attr('y',27).text(d=>cut(apprBadge(d),22));
  ne.append('text').attr('class','nd-cnt') .attr('x',6).attr('y',40).text(d=>d.data.employee_count>0?d.data.employee_count+' dip.':'');

  // Toggle badge at bottom center
  const bg=ne.append('g').attr('class','bg').attr('transform',`translate(${{VNW/2}},${{VNH}})`);
  bg.append('circle').attr('class','tog-c').attr('r',8).on('click',(ev,d)=>{{ev.stopPropagation();toggle(d);}});
  bg.append('text').attr('class','tog-t').text(d=>cc(d));

  const nu=ne.merge(nd);
  nu.transition().duration(200).attr('transform',d=>`translate(${{d.x-VNW/2}},${{d.y}})`);
  nu.select('.node-box').attr('class',nodeClass);
  nu.select('.nd-name').text(d=>cut(d.data.name,21));
  nu.select('.nd-appr').text(d=>cut(apprBadge(d),22))
    .attr('fill',d=>d.data.has_approver?'#22c55e':'#f59e0b');
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

  // TNS color palette: green shades for has-approver, orange for no-approver
  const depthColors=['#14532d','#166534','#15803d','#16a34a','#22c55e','#4ade80','#86efac'];

  // Clear existing content
  g.selectAll('*').remove();
  g.attr('transform',`translate(${{W/2}},${{H/2}})`);

  // Arcs — color by approver status at leaf level, depth color for branches
  g.selectAll('.sb-arc').data(sroot.descendants().filter(d=>d.depth>0))
    .join('path').attr('class','sb-arc')
    .attr('d',arc)
    .attr('fill',d=>{{
      if(!d.data.has_approver && d.depth>=1) return '#78350f'; // dark orange for no-approver
      return depthColors[Math.min(d.depth,depthColors.length-1)];
    }})
    .attr('stroke','#0f172a').attr('stroke-width',0.5)
    .on('mouseover',(ev,d)=>{{
      const appr=d.data.approvers||[];
      const apprText=appr.length?appr.slice(0,2).join(', ')+(appr.length>2?'…':''):'⚠ Nessuno';
      showTip(ev, d.data.name+' — '+(d.value||0)+' dip. | App: '+apprText);
      d3.select(ev.currentTarget).attr('fill','#f59e0b');
    }})
    .on('mouseout',(ev,d)=>{{
      d3.select(ev.currentTarget).attr('fill',
        !d.data.has_approver && d.depth>=1 ? '#78350f' :
        depthColors[Math.min(d.depth,depthColors.length-1)]);
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

  // Color: green shades for has-approver, orange shades for no-approver
  const greenPalette=['#0f172a','#14532d','#166534','#15803d','#16a34a','#22c55e'];
  const orangePalette=['#78350f','#92400e','#b45309','#d97706','#f59e0b','#fbbf24'];

  const cell=g.selectAll('.tm-node')
    .data(troot.descendants().filter(d=>d.depth>0))
    .join('g').attr('class','tm-node')
    .attr('transform',d=>`translate(${{d.x0}},${{d.y0}})`);

  cell.append('rect').attr('class','tm-rect')
    .attr('width', d=>Math.max(0,d.x1-d.x0))
    .attr('height',d=>Math.max(0,d.y1-d.y0))
    .attr('fill',d=>{{
      const palette = d.data.has_approver ? greenPalette : orangePalette;
      return palette[Math.min(d.depth,palette.length-1)];
    }})
    .on('mouseover',(ev,d)=>{{
      const appr=d.data.approvers||[];
      const apprText=appr.length?appr.slice(0,2).join(', ')+(appr.length>2?'…':''):'⚠ Nessuno';
      showTip(ev,d.data.name+' — '+(d.value||0)+' dip. | Appr: '+apprText);
    }})
    .on('mouseout',hideTip)
    .on('click',(ev,d)=>openModalById(d.data.id,d.data.name));

  cell.filter(d=>(d.x1-d.x0)>50&&(d.y1-d.y0)>20)
    .append('text').attr('class','tm-label')
    .attr('x',4).attr('y',13).attr('font-size','10px').attr('fill','#f1f5f9')
    .text(d=>cut(d.data.name,Math.max(1,Math.floor((d.x1-d.x0-8)/7))));

  cell.filter(d=>(d.x1-d.x0)>60&&(d.y1-d.y0)>32)
    .append('text').attr('class','tm-label')
    .attr('x',4).attr('y',27).attr('font-size','9px')
    .attr('fill',d=>d.data.has_approver?'#86efac':'#fcd34d')
    .text(d=>{{
      const appr=d.data.approvers||[];
      if(!appr.length) return '⚠ No appr.';
      return '✅ '+(d.data.employee_count||0)+' dip.';
    }});
}}

// ── Toolbar actions ──────────────────────────────────────────────────────
function autoFit() {{
  const el=document.getElementById('svg-area');
  const w=el.clientWidth, h=el.clientHeight;
  try {{
    const bbox = g.node().getBBox();
    if (bbox.width === 0 || bbox.height === 0) return;
    const fullWidth = bbox.width;
    const fullHeight = bbox.height;
    const scale = Math.min(
      (w - 60) / fullWidth,
      (h - 60) / fullHeight,
      1.5
    );
    const centerX = w / 2 - (bbox.x + fullWidth / 2) * scale;
    const centerY = h / 2 - (bbox.y + fullHeight / 2) * scale;
    svg.transition().duration(300).call(zoom.transform,
      d3.zoomIdentity.translate(centerX, centerY).scale(scale));
  }} catch(e) {{
    console.error('AutoFit error:', e);
  }}
}}

function resetView() {{
  // Reset focus to show all nodes
  focusedNode = null;
  g.selectAll('*').remove();
  if(currentLayout==='h') drawHorizontal();
  else if(currentLayout==='v') drawVertical();
  setTimeout(() => autoFit(), 100);
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
  const apprNames=APPR[id]||[];
  curEmp=emps;
  document.getElementById('mt').textContent=name;
  document.getElementById('mc').textContent='Codice: '+id;
  document.getElementById('m-d').textContent=emps.length;
  document.getElementById('m-a').textContent=emps.filter(e=>e.roles.includes('App')).length;
  document.getElementById('m-v').textContent=emps.filter(e=>e.roles.includes('Viag')).length;

  // Show approvers section
  const apprDiv=document.getElementById('m-appr-list');
  if(apprNames.length) {{
    apprDiv.innerHTML='<span style="color:#64748b">Approvatori: </span>'+
      apprNames.map(a=>`<span style="color:#22c55e;margin-right:6px">✅ ${{a}}</span>`).join('');
  }} else {{
    apprDiv.innerHTML='<span style="color:#f59e0b">⚠️ Nessun approvatore assegnato a questa struttura</span>';
  }}

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
setTimeout(resetView,120);
</script>
</body></html>"""

            components.html(html_content, height=1060, scrolling=False)

            # ── Streamlit-side stats ──
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("Strutture totali", node_count)
            with col_b:
                st.metric("Con approvatore", node_count - no_appr_count, delta=None)
            with col_c:
                st.metric("⚠ Senza approvatore", no_appr_count,
                          delta=None, delta_color="inverse" if no_appr_count > 0 else "normal")

            # ── Streamlit-side search results ──
            if search_query:
                st.markdown("### 🔍 Risultati Ricerca")
                search_result = orgchart_service.search_employee(search_query, hierarchy_type='TNS')
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
                            st.info("Nessuna assegnazione gerarchica TNS")
                else:
                    # Try struttura search
                    matching_nodes = [n for n in nodes
                                      if search_query.lower() in (n.get('name') or '').lower()]
                    if matching_nodes:
                        st.info(f"Trovate {len(matching_nodes)} strutture corrispondenti (usa la search bar nel grafico per navigare)")
                    else:
                        st.warning(f"⚠️ Nessun risultato per: {search_query}")

            with st.expander("📖 Legenda e Istruzioni"):
                st.markdown("""
**Layout disponibili (switcher in alto):**
- 🌲 **Albero H** — Tree orizzontale LR, click=espandi, dbl-click=dettaglio struttura
- 🏛️ **Albero V** — Tree verticale top-down, stessa interazione
- ☀️ **Sunburst** — Anelli radiali: verde=ha approvatori, arancione=nessun approvatore
- 📦 **Treemap** — Rettangoli proporzionali a n° dipendenti: verde/arancione per stato approvatori

**Badge approvatori nei nodi:**
- ✅ `ROSSI M.` — approvatore assegnato (fino a 2 nomi visibili)
- `+N` — altri N approvatori non mostrati
- ⚠️ — struttura senza approvatore (bordo arancione)

**Navigazione alberi (H/V):** zoom con rotella · trascina per pan · Reset centralizza
                """)

        except Exception as e:
            st.error(f"❌ Errore durante caricamento organigramma TNS: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
