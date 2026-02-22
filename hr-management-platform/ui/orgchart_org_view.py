"""
Orgchart Organization Hierarchy View - Multi-Layout

Shows strutture (org units) as internal nodes and personale (employees) as leaves.
Supports 4 JS-side layouts:
  H - Albero Orizzontale (LR tree)
  V - Albero Verticale   (top-down tree)
  P - Pannelli           (Finder-style, strutture only)
  C - Card Grid          (OrgVue-style, strutture + persone)
"""
import streamlit as st
import streamlit.components.v1 as components
import json

from services.orgchart_data_service import get_orgchart_data_service
from services.lookup_service import get_lookup_service


def render_orgchart_org_view():
    """Render Organization Hierarchy orgchart view (strutture + persone) with multi-layout"""

    orgchart_service = get_orgchart_data_service()
    lookup_service   = get_lookup_service()

    # ========== FILTERS ==========
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        search_query = st.text_input(
            "🔍 Cerca struttura o dipendente",
            placeholder="Nome struttura o dipendente…",
            key="org_search"
        )
    with col2:
        st.button("📥 Export PNG", use_container_width=True, disabled=True,
                  help="Disponibile nel layout Albero con tasto destro → Salva immagine")
    with col3:
        show_people = st.toggle("👤 Mostra persone", value=True, key="org_show_people")

    # ========== LOAD DATA ==========
    with st.spinner("Caricamento organigramma…"):
        try:
            # Use get_org_units_tree() which reads from new org_units table
            hierarchy_data = orgchart_service.get_org_units_tree()
            all_nodes = hierarchy_data.get('nodes', [])
            if not all_nodes:
                st.warning("Nessun dato disponibile per l'organigramma ORG")
                st.info("Verifica che siano state importate posizioni organizzative nel database.")
                return

            # All nodes are org units (no person nodes in new architecture)
            nodes = all_nodes
            struttura_count = len(nodes) - 1  # Exclude ROOT_ORG
            person_count = 0  # No person nodes in org units tree
            hierarchy_json = json.dumps(nodes, ensure_ascii=False)

            html_content = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:100%;height:100%;overflow:hidden;
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  background:#0f172a;color:#f1f5f9}}
#main{{display:flex;flex-direction:column;height:100vh}}

#ls-bar{{background:#0a1120;padding:4px 10px;display:flex;gap:4px;
  align-items:center;border-bottom:1px solid #1e293b;flex-shrink:0;height:36px}}
.ls-btn{{background:#1e293b;border:1px solid #334155;color:#94a3b8;
  padding:2px 9px;border-radius:5px;font-size:11px;cursor:pointer;transition:all .15s;white-space:nowrap}}
.ls-btn:hover{{background:#334155;color:#e2e8f0}}
.ls-btn.active{{background:#1d4ed8;border-color:#1d4ed8;color:#fff}}

#toolbar{{background:#0f172a;padding:4px 10px;display:flex;gap:5px;
  align-items:center;border-bottom:1px solid #1e293b;flex-shrink:0;height:34px}}
#search-input{{background:#1e293b;border:1px solid #334155;color:#f1f5f9;
  padding:2px 7px;border-radius:4px;font-size:11px;width:200px;outline:none}}
#search-input:focus{{border-color:#3b82f6}}
.btn{{background:#1e293b;border:1px solid #334155;color:#cbd5e1;
  padding:2px 8px;border-radius:4px;font-size:11px;cursor:pointer;white-space:nowrap;transition:all .15s}}
.btn:hover{{background:#3b82f6;border-color:#3b82f6;color:#fff}}
.sep{{width:1px;background:#334155;height:18px;flex-shrink:0}}
#legend{{display:flex;gap:8px;font-size:10px;color:#64748b;align-items:center}}
.ld{{width:8px;height:8px;border-radius:2px;border:2px solid;display:inline-block;vertical-align:middle;margin-right:2px}}
#info{{font-size:10px;color:#475569;margin-left:auto}}

#svg-area{{flex:1;overflow:hidden;cursor:grab}}
#svg-area:active{{cursor:grabbing}}
svg{{width:100%;height:100%}}

.node-g{{cursor:pointer}}
.node-box{{fill:#1e293b;stroke:#334155;stroke-width:1.5}}
.node-g:hover .node-box{{stroke:#3b82f6;fill:#1a2e4a}}
.node-box.has-resp{{stroke:#22c55e}}
.node-box.no-resp{{stroke:#334155}}
.node-box.collapsed{{stroke:#f59e0b}}
.node-box.hl{{stroke:#f59e0b;stroke-width:2.5;fill:#2a2000}}
.node-box.person{{fill:#0f2744;stroke:#1d4ed8}}
.node-box.person.hl{{stroke:#f59e0b;stroke-width:2.5;fill:#2a2000}}
.node-g.person:hover .node-box{{stroke:#60a5fa;fill:#0c1f3a}}
.nd-name{{fill:#e2e8f0;font-size:11px;font-weight:600;pointer-events:none}}
.nd-name.person-name{{fill:#93c5fd;font-size:10px;font-weight:500}}
.nd-resp{{fill:#64748b;font-size:9.5px;pointer-events:none}}
.nd-cnt{{fill:#3b82f6;font-size:9.5px;pointer-events:none}}
.tog-c{{fill:#1d4ed8;stroke:#0f172a;stroke-width:1;cursor:pointer}}
.tog-c:hover{{fill:#3b82f6}}
.tog-t{{fill:#fff;font-size:8.5px;text-anchor:middle;dominant-baseline:central;pointer-events:none}}
.link{{fill:none;stroke:#1e3a5f;stroke-width:1.5}}
.link.person-link{{stroke:#1e3a8a;stroke-width:1;stroke-dasharray:3,2}}

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

#card-grid-container{{flex:1;display:none;overflow:auto;padding:10px;background:#0f172a}}
.orgcard{{background:#1e293b;border:1px solid #334155;border-radius:6px;padding:9px;cursor:pointer;transition:border-color 150ms}}
.orgcard:hover{{border-color:#3b82f6}}
.orgcard-struttura{{border-left:3px solid #22c55e}}
.orgcard-person{{border-left:3px solid #1d4ed8;background:#0f2744}}
.oc-header{{margin-bottom:6px;border-bottom:1px solid #1a2535;padding-bottom:5px}}
.oc-name{{font-weight:600;font-size:12px;color:#e2e8f0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.oc-role{{font-size:10px;color:#64748b;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.oc-body{{display:flex;flex-direction:column;gap:2px}}
.oc-row{{display:flex;justify-content:space-between;font-size:10px;color:#94a3b8}}
.oc-row span:first-child{{color:#64748b}}
.oc-badge{{display:inline-block;padding:1px 5px;border-radius:3px;font-size:9px;font-weight:600;color:#fff;margin-right:2px}}
.oc-badge.App{{background:#2563eb}}.oc-badge.Viag{{background:#16a34a}}
.oc-badge.Contr{{background:#d97706}}.oc-badge.Cass{{background:#dc2626}}

#tooltip{{display:none;position:fixed;background:#1e293b;border:1px solid #475569;
  border-radius:4px;padding:4px 8px;font-size:11px;color:#e2e8f0;pointer-events:none;z-index:200}}

#ov{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:99}}
#modal{{display:none;position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);
  background:#1e293b;border:1px solid #334155;border-radius:8px;
  width:400px;max-height:78vh;flex-direction:column;overflow:hidden;z-index:100}}
#mh{{padding:10px 14px;border-bottom:1px solid #334155;display:flex;align-items:flex-start;gap:8px;background:#0f172a}}
#mt{{font-size:12px;font-weight:700;color:#e2e8f0;flex:1;line-height:1.3}}
#mc{{font-size:9px;color:#475569}}
#mx{{background:none;border:none;color:#64748b;cursor:pointer;font-size:16px;padding:0}}
#mx:hover{{color:#ef4444}}
#ms{{padding:6px 14px;background:#0f172a;border-bottom:1px solid #1e293b;display:flex;gap:14px;font-size:10px;color:#64748b;flex-shrink:0}}
#ms b{{color:#e2e8f0}}
#msi{{padding:6px 14px;border-bottom:1px solid #1e293b;flex-shrink:0}}
#msi input{{width:100%;background:#0f172a;border:1px solid #334155;color:#f1f5f9;padding:3px 7px;border-radius:4px;font-size:11px;outline:none}}
#ml{{overflow-y:auto;flex:1}}
.me{{padding:5px 14px;display:flex;align-items:center;gap:6px;border-bottom:1px solid #0f172a}}
.me:hover{{background:#0f172a}}
.mn{{font-size:11px;color:#e2e8f0;flex:1}}
.mr{{display:flex;gap:3px}}
.rt{{padding:1px 4px;border-radius:3px;font-size:8.5px;font-weight:600;color:#fff}}
.rt.App{{background:#2563eb}}.rt.Viag{{background:#16a34a}}
.rt.Contr{{background:#d97706}}.rt.Cass{{background:#dc2626}}
.noemp{{padding:18px;text-align:center;color:#475569;font-size:11px}}

#person-popup{{display:none;position:fixed;background:#1e293b;border:1px solid #1d4ed8;
  border-radius:6px;padding:10px 14px;z-index:101;max-width:260px;pointer-events:none}}
#person-popup h4{{font-size:11px;color:#93c5fd;margin-bottom:4px}}
.pp-cf{{font-size:9px;color:#475569;margin-bottom:4px}}
.pp-roles{{display:flex;gap:3px;flex-wrap:wrap}}
</style></head>
<body>
<div id="main">
  <div id="ls-bar">
    <button onclick="setLayout('h')" id="btn-h" class="ls-btn active">🌲 Albero H</button>
    <button onclick="setLayout('v')" id="btn-v" class="ls-btn">🏛️ Albero V</button>
    <button onclick="setLayout('p')" id="btn-p" class="ls-btn">🗂️ Pannelli</button>
    <button onclick="setLayout('c')" id="btn-c" class="ls-btn">📋 Card Grid</button>
  </div>
  <div id="toolbar">
    <input id="search-input" placeholder="Cerca struttura o dipendente…" oninput="doSearch(this.value)"/>
    <div class="sep"></div>
    <button class="btn" id="btn-reset" onclick="resetView()">&#8635; Reset</button>
    <button class="btn" id="btn-expand" onclick="expandOne()">+1 Livello</button>
    <button class="btn" id="btn-collapse" onclick="collapseAll()">Chiudi tutti</button>
    <button class="btn" onclick="goFullscreen()">&#x26F6; Fullscreen</button>
    <div class="sep"></div>
    <div id="legend">
      <span><i class="ld" style="border-color:#22c55e"></i>Struttura</span>
      <span><i class="ld" style="border-color:#1d4ed8"></i>Persona</span>
      <span><i class="ld" style="border-color:#f59e0b"></i>Collassato</span>
    </div>
    <span id="info">{struttura_count} strutture &nbsp;·&nbsp; {person_count} persone</span>
  </div>
  <div id="svg-area"><svg id="svg"><g id="rg"></g></svg></div>
  <div id="panels-container"></div>
  <div id="card-grid-container"></div>
</div>

<div id="tooltip"></div>
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
<div id="person-popup">
  <h4 id="pp-name"></h4>
  <div class="pp-cf" id="pp-cf"></div>
  <div class="pp-roles" id="pp-roles"></div>
</div>

<script>
const RAW = {hierarchy_json};

// Build employee index from person nodes
const EMP = {{}};
RAW.forEach(d=>{{
  if(d.node_type==='person'&&d.parentId){{
    if(!EMP[d.parentId]) EMP[d.parentId]=[];
    EMP[d.parentId].push({{cf:d.tx_cod_fiscale||'',name:d.name,roles:(d.roles||[]).map(r=>r.name)}});
  }}
}});

const stratify=d3.stratify().id(d=>d.id).parentId(d=>d.parentId);
let root;
try {{ root=stratify(RAW); }}
catch(e) {{
  document.body.innerHTML='<div style="padding:20px;color:#ef4444">Errore: '+e.message+'</div>';
  throw e;
}}
root.each(d=>{{if(d.depth>=1&&d.children){{d._ch=d.children;d.children=null;}}}});

const ROW_H=42,COL_W=210,NW=190,NH=36;
const svg=d3.select('#svg'),g=d3.select('#rg');
const zoom=d3.zoom().scaleExtent([0.02,5]).on('zoom',e=>g.attr('transform',e.transform));
svg.call(zoom);

let curEmp=[],currentLayout='h';
let focusedNode = null;

// Helper functions for drill-down
function getAncestors(node) {{
  const ancestors = [];
  let current = node;
  while(current.parent) {{
    ancestors.push(current.parent);
    current = current.parent;
  }}
  return ancestors;
}}

function shouldShowNode(node) {{
  if (!focusedNode) return true;
  if (node === focusedNode) return true;
  const ancestors = getAncestors(focusedNode);
  if (ancestors.includes(node)) return true;
  if (node.parent === focusedNode) return true;
  return false;
}}

function setLayout(type) {{
  document.querySelectorAll('.ls-btn').forEach(b=>b.classList.remove('active'));
  document.getElementById('btn-'+type).classList.add('active');
  currentLayout=type;
  const svgArea=document.getElementById('svg-area');
  const panelsEl=document.getElementById('panels-container');
  const cardsEl=document.getElementById('card-grid-container');
  svgArea.style.display='none'; panelsEl.style.display='none'; cardsEl.style.display='none';
  g.selectAll('*').remove(); g.attr('transform','');
  const treeOnly=type==='h'||type==='v';
  document.getElementById('btn-expand').style.display=treeOnly?'':'none';
  document.getElementById('btn-collapse').style.display=treeOnly?'':'none';
  document.getElementById('btn-reset').style.display=treeOnly?'':'none';
  if(treeOnly){{svg.call(zoom);}}else{{svg.on('.zoom',null);}}
  if(type==='h'||type==='v'){{svgArea.style.cssText='flex:1;overflow:hidden;cursor:grab';}}
  else if(type==='p'){{panelsEl.style.cssText='flex:1;display:flex;overflow-x:auto;overflow-y:hidden';}}
  else if(type==='c'){{cardsEl.style.cssText='flex:1;display:block;overflow:auto;padding:10px;background:#0f172a';}}
  ({{h:drawH,v:drawV,p:drawPanels,c:drawCards}}[type])();
  if(treeOnly) setTimeout(autoFit,80);
}}

function cut(s,m){{if(!s)return'';s=String(s);return s.length>m?s.slice(0,m-1)+'…':s;}}
function cc(d){{return d._ch?d._ch.length:(d.children?d.children.length:0)||'';}}
const isPerson=d=>d.data.node_type==='person';

function nodeClass(d) {{
  if(d.data._hl) return 'node-box'+(isPerson(d)?' person':'')+' hl';
  if(isPerson(d)) return 'node-box person';
  if(d._ch) return 'node-box collapsed';
  if(d.data.has_responsible) return 'node-box has-resp';
  return 'node-box no-resp';
}}

function toggle(d) {{
  if(d.children){{
    d._ch=d.children;
    d.children=null;
    if (d.depth > 1) {{
      focusedNode = d.parent;
    }} else {{
      focusedNode = null;
    }}
  }}
  else if(d._ch){{
    focusedNode = d;
    d.children=d._ch;
    d._ch=null;
  }}
  g.selectAll('*').remove();
  if(currentLayout==='h') drawH(); else drawV();
  setTimeout(autoFit, 100);
}}

function drawTreeBase(nodeSize,getTransform,getLinkD,getTogglePos) {{
  const tree=d3.tree().nodeSize(nodeSize);
  tree(root);
  const allNodes = root.descendants();
  const allLinks = root.links();
  const nodes = allNodes.filter(shouldShowNode);
  const links = allLinks.filter(link =>
    shouldShowNode(link.source) && shouldShowNode(link.target)
  );

  const lk=g.selectAll('.link').data(links,d=>d.source.id+'>'+d.target.id);
  lk.enter().insert('path','.node-g')
    .attr('class',d=>'link'+(d.target.data.node_type==='person'?' person-link':''))
    .merge(lk).transition().duration(200).attr('d',getLinkD);
  lk.exit().remove();

  const nd=g.selectAll('.node-g').data(nodes,d=>d.id);
  const ne=nd.enter().append('g')
    .attr('class',d=>'node-g'+(isPerson(d)?' person':''))
    .attr('transform',getTransform)
    .on('click',(ev,d)=>{{ev.stopPropagation();isPerson(d)?showPersonPopup(d,ev):toggle(d);}})
    .on('dblclick',(ev,d)=>{{ev.stopPropagation();if(!isPerson(d))openModal(d);}});

  ne.append('rect').attr('class',d=>'node-box'+(isPerson(d)?' person':'')).attr('width',NW).attr('height',NH).attr('rx',4);
  ne.append('text').attr('class',d=>'nd-name'+(isPerson(d)?' person-name':'')).attr('x',7).attr('y',isPerson?15:14)
    .text(d=>cut(d.data.name,isPerson(d)?27:24));
  ne.append('text').attr('class','nd-resp').attr('x',7).attr('y',26).text(d=>cut(d.data.title||'',28));
  ne.append('text').attr('class','nd-cnt').attr('x',7).attr('y',34)
    .text(d=>(!isPerson(d)&&d.data.employee_count>0)?d.data.employee_count+' dip.':'');

  const bg=ne.append('g').attr('class','bg').attr('transform',getTogglePos);
  bg.append('circle').attr('class','tog-c').attr('r',8).on('click',(ev,d)=>{{ev.stopPropagation();if(!isPerson(d))toggle(d);}});
  bg.append('text').attr('class','tog-t').text(d=>cc(d));

  const nu=ne.merge(nd);
  nu.transition().duration(200).attr('transform',getTransform);
  nu.select('.node-box').attr('class',nodeClass);
  nu.select('.nd-name').text(d=>cut(d.data.name,isPerson(d)?27:24));
  nu.select('.nd-resp').text(d=>cut(d.data.title||'',28));
  nu.select('.nd-cnt').text(d=>(!isPerson(d)&&d.data.employee_count>0)?d.data.employee_count+' dip.':'');
  nu.select('.bg').style('display',d=>(!isPerson(d)&&(d.children||d._ch))?'block':'none');
  nu.select('.tog-t').text(d=>cc(d));
  nd.exit().remove();
}}

function drawH() {{
  drawTreeBase(
    [ROW_H,COL_W],
    d=>`translate(${{d.y}},${{d.x}})`,
    d=>{{
      const sx=d.source.y+NW,sy=d.source.x+NH/2,tx=d.target.y,ty=d.target.x+NH/2,mx=(sx+tx)/2;
      return `M${{sx}},${{sy}} L${{mx}},${{sy}} L${{mx}},${{ty}} L${{tx}},${{ty}}`;
    }},
    `translate(${{NW}},${{NH/2}})`
  );
}}

function drawV() {{
  const VNW=NW,VNH=NH;
  drawTreeBase(
    [VNW+20,90],
    d=>`translate(${{d.x-VNW/2}},${{d.y}})`,
    d=>{{
      const sx=d.source.x,sy=d.source.y+VNH,tx=d.target.x,ty=d.target.y,my=(sy+ty)/2;
      return `M${{sx}},${{sy}} C${{sx}},${{my}} ${{tx}},${{my}} ${{tx}},${{ty}}`;
    }},
    `translate(${{NW/2}},${{NH}})`
  );
}}

function drawPanels() {{
  const container=document.getElementById('panels-container');
  container.innerHTML='';
  let selectedPath=[];
  // Use only struttura nodes for panels
  const strutNodes=RAW.filter(d=>d.node_type==='struttura');
  function getChildren(id){{return strutNodes.filter(d=>d.parentId===id);}}
  function getRoots(){{return strutNodes.filter(d=>!d.parentId||d.parentId==='');}}

  function renderColumn(nodes,depth){{
    while(container.children.length>depth) container.lastChild.remove();
    const col=document.createElement('div');
    col.className='panel-col'; col.style.height='100%';
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
        else {{while(container.children.length>depth+1)container.lastChild.remove();}}
        renderColumn(nodes,depth);
      }};
      col.appendChild(item);
    }});
    container.appendChild(col);
  }}
  renderColumn(getRoots(),0);
}}

function drawCards() {{
  const container=document.getElementById('card-grid-container');
  container.innerHTML='';
  container.style.cssText='flex:1;display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:8px;padding:10px;overflow:auto;background:#0f172a';
  RAW.forEach(node=>{{
    const isPers=node.node_type==='person';
    const emps=EMP[node.id]||[];
    const card=document.createElement('div');
    card.className='orgcard '+(isPers?'orgcard-person':'orgcard-struttura');
    const roles=(node.roles||[]).map(r=>
      `<span class="oc-badge ${{r.name||r}}">${{r.name||r}}</span>`).join('');
    card.innerHTML=
      `<div class="oc-header">`+
        `<div class="oc-name" title="${{node.name}}">${{cut(node.name,26)}}</div>`+
        `<div class="oc-role">${{cut(node.title||'—',30)}}</div>`+
      `</div>`+
      `<div class="oc-body">`+
        (!isPers?`<div class="oc-row"><span>Dipendenti</span><span>${{node.employee_count||0}}</span></div>`+
                 `<div class="oc-row"><span>Approvatori</span><span>${{emps.filter(e=>e.roles.includes('App')).length}}</span></div>`
               :`<div class="oc-row" style="flex-wrap:wrap">${{roles||'<span style="color:#475569">Nessun ruolo</span>'}}</div>`)+
      `</div>`;
    if(!isPers) card.onclick=()=>openModalById(node.id,node.name);
    container.appendChild(card);
  }});
}}

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

function resetView(){{
  focusedNode = null;
  g.selectAll('*').remove();
  if(currentLayout==='h') drawH();
  else if(currentLayout==='v') drawV();
  setTimeout(() => autoFit(), 100);
}}
function expandOne(){{
  let did=false;
  root.each(d=>{{if(!d.children&&d._ch&&d.parent&&d.parent.children){{d.children=d._ch;d._ch=null;did=true;}}}});
  if(!did) root.each(d=>{{if(d._ch){{d.children=d._ch;d._ch=null;}}}});
  g.selectAll('*').remove();
  if(currentLayout==='h') drawH(); else drawV();
  setTimeout(autoFit, 100);
}}
function collapseAll(){{
  focusedNode = null;
  root.each(d=>{{if(d.depth>=1&&d.children){{d._ch=d.children;d.children=null;}}}});
  g.selectAll('*').remove();
  if(currentLayout==='h') drawH(); else drawV();
  setTimeout(autoFit,250);
}}
function doSearch(q){{
  RAW.forEach(d=>d._hl=false);
  if(!q||q.length<2){{if(currentLayout==='h')drawH();else if(currentLayout==='v')drawV();return;}}
  q=q.toLowerCase();
  let found=null;
  root.each(d=>{{if(d.data.name.toLowerCase().includes(q)){{d.data._hl=true;if(!found)found=d;}}}});
  if(!found) return;
  let cur=found;while(cur){{if(cur._ch){{cur.children=cur._ch;cur._ch=null;}}cur=cur.parent;}}
  g.selectAll('*').remove();
  if(currentLayout==='h'||currentLayout==='v'){{
    if(currentLayout==='h')drawH();else drawV();
    setTimeout(()=>{{
      const el=document.getElementById('svg-area');
      const w=el.clientWidth,h=el.clientHeight;
      const cx=currentLayout==='h'?found.y:found.x;
      const cy=currentLayout==='h'?found.x:found.y;
      svg.transition().duration(450).call(zoom.transform,d3.zoomIdentity.translate(w/2-cx,h/2-cy).scale(1));
    }},250);
  }}
}}
function goFullscreen(){{
  const el=document.getElementById('main');
  if(!document.fullscreenElement)el.requestFullscreen().catch(()=>{{}});
  else document.exitFullscreen();
}}
document.addEventListener('fullscreenchange',()=>setTimeout(resetView,200));

function showPersonPopup(d,ev){{
  const pp=document.getElementById('person-popup');
  document.getElementById('pp-name').textContent=d.data.name;
  document.getElementById('pp-cf').textContent=d.data.tx_cod_fiscale?'CF: '+d.data.tx_cod_fiscale:'';
  const rolesHtml=(d.data.roles||[]).map(r=>`<span class="rt ${{r.name}}">${{r.name}}</span>`).join('');
  document.getElementById('pp-roles').innerHTML=rolesHtml||'<span style="color:#475569;font-size:9px">Nessun ruolo TNS</span>';
  const svgRect=document.getElementById('svg-area').getBoundingClientRect();
  const t=d3.zoomTransform(d3.select('#svg').node());
  const px=t.x+(currentLayout==='h'?d.y:d.x-NW/2)*t.k+NW/2;
  const py=t.y+(currentLayout==='h'?d.x:d.y)*t.k-50;
  pp.style.left=Math.min(px+svgRect.left,window.innerWidth-270)+'px';
  pp.style.top=Math.max(py+svgRect.top,10)+'px';
  pp.style.display='block'; pp.style.pointerEvents='none';
  clearTimeout(pp._t); pp._t=setTimeout(()=>{{pp.style.display='none';}},3000);
}}
document.addEventListener('click',()=>{{document.getElementById('person-popup').style.display='none';}});

function openModalById(id,name){{
  const emps=EMP[id]||[]; curEmp=emps;
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
function openModal(d){{openModalById(d.id,d.data.name);}}
function renderList(emps){{
  const l=document.getElementById('ml');
  if(!emps.length){{l.innerHTML='<div class="noemp">Nessun dipendente</div>';return;}}
  l.innerHTML=emps.map(e=>`<div class="me"><div class="mn">${{e.name}}</div><div class="mr">${{e.roles.map(r=>`<span class="rt ${{r}}">${{r}}</span>`).join('')}}</div></div>`).join('');
}}
function filterM(q){{renderList(q?curEmp.filter(e=>e.name.toLowerCase().includes(q.toLowerCase())):curEmp);}}
function closeModal(){{document.getElementById('ov').style.display='none';document.getElementById('modal').style.display='none';}}

drawH();
setTimeout(resetView,120);
</script>
</body></html>"""

            components.html(html_content, height=980, scrolling=False)

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
                            st.info("Nessuna assegnazione gerarchica trovata")
                else:
                    st.warning(f"⚠️ Nessun risultato per: {search_query}")

            with st.expander("📖 Legenda e Istruzioni"):
                st.markdown("""
**Layout disponibili:**
- 🌲 **Albero H** — Orizzontale, strutture (verde) + persone (blu), click=espandi, dbl-click=lista dip.
- 🏛️ **Albero V** — Verticale top-down, stessa interazione
- 🗂️ **Pannelli** — Finder-style colonne navigabili, solo strutture
- 📋 **Card Grid** — Schede OrgVue, verde=struttura, blu=persona con badge ruoli

**Persone:** click=popup con ruoli TNS · **Strutture:** dbl-click=lista dipendenti assegnati
                """)

        except Exception as e:
            st.error(f"❌ Errore durante caricamento organigramma: {str(e)}")
            import traceback
            st.code(traceback.format_exc())


if __name__ == "__main__":
    render_orgchart_org_view()
