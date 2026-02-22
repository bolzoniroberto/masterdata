"""
Design System – HR Management Platform (Il Sole 24 ORE)
=======================================================
Unico punto di verità per tutti gli stili CSS.
Dark theme, compact layout, Streamlit-compatible.

Chiama apply_common_styles() UNA SOLA VOLTA in app.py, non nelle singole view.
"""
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# TOKENS – Non modificare qui senza aggiornare anche gli alias più in basso
# ─────────────────────────────────────────────────────────────────────────────
_DESIGN_TOKENS = """
<style>
:root {
    /* ── Palette dark ── */
    --c-base:    #0f172a;   /* pagina, sidebar */
    --c-surface: #1e293b;   /* card, input, sidebar hover */
    --c-raised:  #263348;   /* elevato su surface */
    --c-border:  #334155;   /* bordi standard */
    --c-border-l:#1e293b;   /* bordi sottili */

    /* ── Testo ── */
    --c-text:    #f1f5f9;
    --c-text-2:  #cbd5e1;
    --c-text-3:  #94a3b8;

    /* ── Accenti ── */
    --c-blue:    #3b82f6;
    --c-blue-h:  #2563eb;
    --c-green:   #22c55e;
    --c-amber:   #f59e0b;
    --c-red:     #ef4444;
    --c-sky:     #0ea5e9;
    --c-violet:  #8b5cf6;

    /* ── Spaziatura (base 4px) ── */
    --sp-1: 4px;
    --sp-2: 8px;
    --sp-3: 12px;
    --sp-4: 16px;
    --sp-5: 20px;
    --sp-6: 24px;
    --sp-8: 32px;

    /* ── Tipografia ── */
    --t-xs:   0.70rem;   /* ~11px */
    --t-sm:   0.78rem;   /* ~12.5px */
    --t-base: 0.875rem;  /* ~14px  – default UI */
    --t-md:   0.9375rem; /* ~15px */
    --t-lg:   1rem;      /* ~16px */
    --t-xl:   1.125rem;  /* ~18px */

    /* ── Bordi arrotondati ── */
    --r-sm:  4px;
    --r-md:  6px;
    --r-lg:  8px;
    --r-xl:  12px;
    --r-pill:9999px;

    /* ── Ombre ── */
    --sh-sm: 0 1px 3px rgba(0,0,0,.35);
    --sh-md: 0 3px 8px rgba(0,0,0,.4);
    --sh-lg: 0 8px 20px rgba(0,0,0,.45);

    /* ── Transizioni ── */
    --tr: 150ms ease;
}
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL LAYOUT – Override Streamlit defaults
# ─────────────────────────────────────────────────────────────────────────────
_GLOBAL_LAYOUT = """
<style>
/* ── Nascondi branding / chrome Streamlit (NON toccare stHeader: ha il hamburger) ── */
#MainMenu                          { visibility: hidden !important; }
footer                             { visibility: hidden !important; }
.viewerBadge_container__1QSob     { visibility: hidden !important; }
div[data-testid="stDecoration"]   { display: none !important; }
div[data-testid="stStatusWidget"] { display: none !important; }

/* ── Pagina compatta ── */
/* Nota: padding-top è impostato nel blocco _TOPBAR_CSS per compensare topbar fissa */
.main .block-container {
    padding-bottom: 1rem !important;
    padding-left:   1.5rem !important;
    padding-right:  1.5rem !important;
    max-width: 100% !important;
}

/* Azzera il padding che Streamlit aggiunge su .main per il suo header nativo */
.main {
    padding-top: 0 !important;
}

/* ── Riduzione spaziatura default tra elementi ── */
.element-container {
    margin-bottom: var(--sp-2) !important;
}

/* ── Headings compatti (se rimangono nel codice) ── */
h1, h2, h3, h4 {
    margin-top:    var(--sp-2) !important;
    margin-bottom: var(--sp-2) !important;
    color: var(--c-text) !important;
    font-weight: 600 !important;
    line-height: 1.3 !important;
}
h1 { font-size: var(--t-xl)  !important; }
h2 { font-size: var(--t-lg)  !important; }
h3 { font-size: var(--t-md)  !important; }
h4 { font-size: var(--t-base)!important; }

/* ── Caption / testo secondario ── */
.stCaption, [data-testid="stCaptionContainer"] {
    color: var(--c-text-3) !important;
    font-size: var(--t-xs) !important;
}

/* ── Colori globali testo ── */
body, p, span, div, label, li {
    color: var(--c-text) !important;
}
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
_SIDEBAR_CSS = """
<style>
/* ── Sfondo sidebar ── */
section[data-testid="stSidebar"] {
    background: var(--c-base) !important;
    border-right: 1px solid var(--c-border) !important;
}

/* ── Pulsanti navigazione sidebar ── */
section[data-testid="stSidebar"] .stButton {
    margin-bottom: 2px !important;
}
section[data-testid="stSidebar"] .stButton button {
    width: 100% !important;
    text-align: left !important;
    font-size: var(--t-sm) !important;
    font-weight: 500 !important;
    padding: var(--sp-2) var(--sp-3) !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    border-radius: var(--r-md) !important;
}

/* ── Etichette sezione sidebar (uppercase) ── */
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span {
    color: var(--c-text-2) !important;
    font-size: var(--t-sm) !important;
}
section[data-testid="stSidebar"] strong {
    color: var(--c-text-3) !important;
    font-size: var(--t-xs) !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    display: block;
    margin-top: var(--sp-4);
    margin-bottom: var(--sp-1);
}
section[data-testid="stSidebar"] hr {
    margin: var(--sp-2) 0 !important;
    border-color: var(--c-border) !important;
}

/* ── Logo / titolo sidebar ── */
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    font-size: var(--t-base) !important;
    color: var(--c-text) !important;
    margin: var(--sp-2) 0 !important;
}
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# BUTTONS – Standard, primary, danger
# ─────────────────────────────────────────────────────────────────────────────
_BUTTONS_CSS = """
<style>
/* ── Base button ── */
.stButton button {
    background:    var(--c-surface) !important;
    color:         var(--c-text-2)  !important;
    border:        1px solid var(--c-border) !important;
    border-radius: var(--r-md)      !important;
    font-size:     var(--t-sm)      !important;
    font-weight:   500              !important;
    padding:       var(--sp-1) var(--sp-3) !important;
    min-height:    30px             !important;
    height:        auto             !important;
    transition:    all var(--tr)    !important;
    line-height:   1.4              !important;
}
.stButton button:hover {
    background:    var(--c-raised)  !important;
    border-color:  var(--c-blue)    !important;
    color:         var(--c-text)    !important;
}

/* ── Primary button ── */
.stButton button[kind="primary"] {
    background:   var(--c-blue)    !important;
    border-color: var(--c-blue)    !important;
    color:        #fff             !important;
    font-weight:  600              !important;
}
.stButton button[kind="primary"]:hover {
    background:   var(--c-blue-h)  !important;
    border-color: var(--c-blue-h)  !important;
}

/* ── Pulsanti di azione (fullwidth) mantengono margine zero ── */
.stButton + .stButton { margin-top: 0 !important; }
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# FORM INPUTS
# ─────────────────────────────────────────────────────────────────────────────
_INPUTS_CSS = """
<style>
/* ── Etichette input ── */
label[data-testid="stWidgetLabel"] > p,
.stTextInput label, .stSelectbox label, .stMultiSelect label,
.stNumberInput label, .stTextArea label, .stDateInput label,
.stCheckbox label, .stRadio label {
    font-size:   var(--t-sm)   !important;
    font-weight: 500           !important;
    color:       var(--c-text-3)!important;
    margin-bottom: var(--sp-1) !important;
}

/* ── Campi testo, select, textarea ── */
.stTextInput input,
.stNumberInput input,
.stTextArea textarea,
.stDateInput input {
    background:    var(--c-surface) !important;
    border:        1px solid var(--c-border) !important;
    border-radius: var(--r-md)   !important;
    color:         var(--c-text) !important;
    font-size:     var(--t-base) !important;
    padding:       var(--sp-2) var(--sp-3) !important;
    min-height:    32px !important;
    transition:    border-color var(--tr) !important;
}
.stTextInput input:focus,
.stNumberInput input:focus,
.stTextArea textarea:focus,
.stDateInput input:focus {
    border-color: var(--c-blue) !important;
    outline: none !important;
    box-shadow: 0 0 0 2px rgba(59,130,246,.18) !important;
}

/* ── Selectbox / Multiselect ── */
div[data-baseweb="select"] > div,
div[data-baseweb="select"] input {
    background:    var(--c-surface) !important;
    border:        1px solid var(--c-border) !important;
    border-radius: var(--r-md) !important;
    color:         var(--c-text) !important;
    font-size:     var(--t-base) !important;
    min-height:    32px !important;
}
div[data-baseweb="select"] > div:focus-within {
    border-color: var(--c-blue) !important;
}

/* ── Checkbox / toggle ── */
.stCheckbox > label, .stToggle > label {
    font-size: var(--t-base) !important;
    color: var(--c-text-2) !important;
}
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# DATAFRAME / TABELLE
# ─────────────────────────────────────────────────────────────────────────────
_DATAFRAME_CSS = """
<style>
div[data-testid="stDataFrame"] {
    border:        1px solid var(--c-border) !important;
    border-radius: var(--r-lg) !important;
    overflow:      hidden !important;
    box-shadow:    var(--sh-sm) !important;
}
/* header row */
div[data-testid="stDataFrame"] th {
    background:  var(--c-raised)  !important;
    color:       var(--c-text-3)  !important;
    font-size:   var(--t-xs)      !important;
    font-weight: 600              !important;
    text-transform: uppercase     !important;
    letter-spacing: 0.04em        !important;
    padding:     var(--sp-2) var(--sp-3) !important;
    border-bottom: 1px solid var(--c-border) !important;
}
/* data rows */
div[data-testid="stDataFrame"] td {
    font-size: var(--t-sm) !important;
    padding:   var(--sp-2) var(--sp-3) !important;
    color:     var(--c-text-2) !important;
    border-bottom: 1px solid var(--c-border-l) !important;
}
div[data-testid="stDataFrame"] tbody tr:hover td {
    background: rgba(59,130,246,.07) !important;
    cursor: pointer;
}
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# METRICS
# ─────────────────────────────────────────────────────────────────────────────
_METRICS_CSS = """
<style>
div[data-testid="stMetric"] {
    background:    var(--c-surface) !important;
    border:        1px solid var(--c-border) !important;
    border-radius: var(--r-lg) !important;
    padding:       var(--sp-3) var(--sp-4) !important;
    box-shadow:    var(--sh-sm) !important;
}
div[data-testid="stMetric"] label {
    font-size:      var(--t-xs)   !important;
    color:          var(--c-text-3)!important;
    text-transform: uppercase     !important;
    letter-spacing: 0.05em        !important;
    font-weight:    600           !important;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-size:   var(--t-xl)  !important;
    font-weight: 700          !important;
    color:       var(--c-text)!important;
    line-height: 1.2          !important;
}
div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
    font-size: var(--t-xs) !important;
}
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
_TABS_CSS = """
<style>
.stTabs [data-baseweb="tab-list"] {
    gap:           3px !important;
    background:    var(--c-surface) !important;
    padding:       var(--sp-1) !important;
    border-radius: var(--r-lg) !important;
    border:        1px solid var(--c-border) !important;
    margin-bottom: var(--sp-3) !important;
}
.stTabs [data-baseweb="tab"] {
    background:    transparent !important;
    border:        none !important;
    border-radius: var(--r-md) !important;
    padding:       var(--sp-1) var(--sp-3) !important;
    font-size:     var(--t-sm) !important;
    font-weight:   500 !important;
    color:         var(--c-text-3) !important;
    transition:    all var(--tr) !important;
    white-space:   nowrap !important;
}
.stTabs [data-baseweb="tab"]:hover {
    background: var(--c-raised) !important;
    color:      var(--c-text-2) !important;
}
.stTabs [aria-selected="true"] {
    background: var(--c-blue) !important;
    color:      #fff !important;
    font-weight: 600 !important;
}
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# EXPANDER
# ─────────────────────────────────────────────────────────────────────────────
_EXPANDER_CSS = """
<style>
.streamlit-expanderHeader,
details > summary {
    background:    var(--c-surface)  !important;
    border:        1px solid var(--c-border) !important;
    border-radius: var(--r-md)       !important;
    padding:       var(--sp-2) var(--sp-3) !important;
    font-size:     var(--t-sm)       !important;
    font-weight:   500               !important;
    color:         var(--c-text-2)   !important;
    transition:    all var(--tr)     !important;
}
.streamlit-expanderHeader:hover,
details > summary:hover {
    background:   var(--c-raised)    !important;
    border-color: var(--c-blue)      !important;
    color:        var(--c-text)      !important;
}
.streamlit-expanderContent,
details > div {
    border:        1px solid var(--c-border) !important;
    border-top:    none                      !important;
    border-radius: 0 0 var(--r-md) var(--r-md) !important;
    padding:       var(--sp-3) var(--sp-3)   !important;
    background:    var(--c-base)             !important;
}
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# ALERTS (info, success, warning, error)
# ─────────────────────────────────────────────────────────────────────────────
_ALERTS_CSS = """
<style>
/* ── Streamlit alert boxes ── */
div[data-testid="stAlert"] {
    border-radius: var(--r-md)   !important;
    border-left:   3px solid     !important;
    padding:       var(--sp-2) var(--sp-3) !important;
    font-size:     var(--t-sm)   !important;
    margin:        var(--sp-2) 0 !important;
}
div[data-testid="stAlert"][data-type="info"] {
    background:  rgba(14,165,233,.10) !important;
    border-color: var(--c-sky)        !important;
}
div[data-testid="stAlert"][data-type="success"] {
    background:  rgba(34,197,94,.10)  !important;
    border-color: var(--c-green)      !important;
}
div[data-testid="stAlert"][data-type="warning"] {
    background:  rgba(245,158,11,.10) !important;
    border-color: var(--c-amber)      !important;
}
div[data-testid="stAlert"][data-type="error"] {
    background:  rgba(239,68,68,.10)  !important;
    border-color: var(--c-red)        !important;
}
/* ── Spinner ── */
.stSpinner > div { color: var(--c-blue) !important; }
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# STICKY TOPBAR (mostra pagina corrente + stats)
# ─────────────────────────────────────────────────────────────────────────────
_TOPBAR_CSS = """
<style>
.hr-topbar {
    position:    fixed;
    top: 0; left: 0; right: 0;
    z-index:     999;
    background:  var(--c-surface);
    border-bottom: 1px solid var(--c-border);
    padding:     0 var(--sp-4);
    height:      34px;
    display:     flex;
    align-items: center;
    justify-content: space-between;
    font-size:   var(--t-xs);
    box-shadow:  var(--sh-sm);
}
.hr-topbar-left   { color: var(--c-text-3); }
.hr-topbar-center { color: var(--c-text); font-weight: 600; }
.hr-topbar-right  { color: var(--c-green); }

/* Offset sotto la topbar fissa (34px) + piccolo gap */
.main .block-container {
    padding-top: 42px !important;
}
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# UTILITY COMPONENTS – richiamabili dalle view via st.markdown
# ─────────────────────────────────────────────────────────────────────────────
_COMPONENTS_CSS = """
<style>
/* ── Sezione divider ── */
.hr-section {
    border-top:    1px solid var(--c-border);
    margin:        var(--sp-4) 0 var(--sp-3) 0;
    padding-top:   var(--sp-3);
}
.hr-section-label {
    font-size:      var(--t-xs);
    font-weight:    700;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color:          var(--c-text-3);
    margin-bottom:  var(--sp-2);
}

/* ── Badge stato ── */
.badge {
    display:       inline-flex;
    align-items:   center;
    gap:           var(--sp-1);
    padding:       2px var(--sp-2);
    border-radius: var(--r-pill);
    font-size:     var(--t-xs);
    font-weight:   600;
    line-height:   1;
    white-space:   nowrap;
}
.badge-blue   { background: rgba(59,130,246,.18); color: #93c5fd; }
.badge-green  { background: rgba(34,197,94,.18);  color: #86efac; }
.badge-amber  { background: rgba(245,158,11,.18); color: #fcd34d; }
.badge-red    { background: rgba(239,68,68,.18);  color: #fca5a5; }
.badge-gray   { background: rgba(148,163,184,.15);color: #94a3b8; }
.badge-violet { background: rgba(139,92,246,.18); color: #c4b5fd; }

/* ── Card surface ── */
.hr-card {
    background:    var(--c-surface);
    border:        1px solid var(--c-border);
    border-radius: var(--r-xl);
    padding:       var(--sp-4);
    box-shadow:    var(--sh-sm);
}

/* ── Filter row (header sticky) ── */
.hr-filter-row {
    background:    var(--c-base);
    position:      sticky;
    top:           34px;   /* sotto topbar */
    z-index:       90;
    padding:       var(--sp-2) 0;
    border-bottom: 1px solid var(--c-border);
    margin-bottom: var(--sp-3);
}

/* ── Count badge (in filtri) ── */
.hr-count {
    font-size:  var(--t-xs);
    color:      var(--c-text-3);
    padding:    2px var(--sp-2);
    background: var(--c-surface);
    border:     1px solid var(--c-border);
    border-radius: var(--r-pill);
    white-space: nowrap;
}

/* ── Custom alert boxes ── */
.hr-alert-error {
    background:   rgba(239,68,68,.10);
    border-left:  3px solid var(--c-red);
    border-radius:var(--r-md);
    padding:      var(--sp-3) var(--sp-4);
    font-size:    var(--t-sm);
}
.hr-alert-warn {
    background:   rgba(245,158,11,.10);
    border-left:  3px solid var(--c-amber);
    border-radius:var(--r-md);
    padding:      var(--sp-3) var(--sp-4);
    font-size:    var(--t-sm);
}
.hr-alert-ok {
    background:   rgba(34,197,94,.10);
    border-left:  3px solid var(--c-green);
    border-radius:var(--r-md);
    padding:      var(--sp-3) var(--sp-4);
    font-size:    var(--t-sm);
}
.hr-alert-info {
    background:   rgba(14,165,233,.10);
    border-left:  3px solid var(--c-sky);
    border-radius:var(--r-md);
    padding:      var(--sp-3) var(--sp-4);
    font-size:    var(--t-sm);
}

/* ── Master-detail border ── */
.hr-detail {
    border-left: 2px solid var(--c-border);
    padding-left: var(--sp-4);
}
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# RIBBON INTERFACE – Microsoft Office-style navigation
# ─────────────────────────────────────────────────────────────────────────────
_RIBBON_CSS = """
<style>
/* ── Ribbon Container ── */
.hr-ribbon {
    position: sticky !important;
    top: 0 !important;
    z-index: 9999 !important;
    background: var(--c-base);
    border-bottom: 1px solid var(--c-border);
    box-shadow: var(--sh-md);
    transition: height 0.2s ease;
}

.hr-ribbon.collapsed {
    overflow: hidden;
}

.hr-ribbon.collapsed .hr-ribbon-content {
    display: none;
}

/* ── Quick Access Toolbar ── */
.hr-qat {
    position: absolute;
    top: 0;
    left: 0;
    display: flex;
    gap: 2px;
    padding: 4px 8px;
    background: var(--c-surface);
    border-bottom: 1px solid var(--c-border);
    z-index: 1001;
    height: 32px;
    align-items: center;
}

.hr-qat-btn {
    width: 28px;
    height: 24px;
    padding: 0;
    background: transparent;
    border: 1px solid transparent;
    border-radius: var(--r-sm);
    color: var(--c-text);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    transition: all 0.12s;
}

.hr-qat-btn:hover {
    background: var(--c-raised);
    border-color: var(--c-border);
}

/* ── Ribbon Container (tabs + content) ── */
.hr-ribbon-container {
    margin-top: 32px; /* Space for QAT */
}

/* ── Tab Bar ── */
.hr-ribbon-tabs {
    display: flex;
    align-items: center;
    background: var(--c-surface);
    height: 40px;
    border-bottom: 1px solid var(--c-border);
    padding-left: 8px;
    gap: 2px;
}

.hr-ribbon-tab {
    padding: 8px 20px;
    border: none;
    background: transparent;
    color: var(--c-text-2);
    font-size: var(--t-sm);
    font-weight: 500;
    cursor: pointer;
    border-bottom: 3px solid transparent;
    transition: all 0.15s;
    height: 100%;
    display: flex;
    align-items: center;
}

.hr-ribbon-tab:hover {
    background: var(--c-raised);
    color: var(--c-text);
}

.hr-ribbon-tab.active {
    background: var(--c-base);
    border-bottom-color: var(--c-blue);
    color: var(--c-blue);
}

.hr-ribbon-tab-extras {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 12px;
    padding-right: 48px; /* Space for collapse button */
}

/* ── Ribbon Content Area ── */
.hr-ribbon-content {
    display: flex;
    gap: 24px;
    padding: 12px 16px;
    background: var(--c-base);
    overflow-x: auto;
    overflow-y: hidden;
    min-height: 80px;
}

/* ── Ribbon Group ── */
.hr-ribbon-group {
    display: flex;
    flex-direction: column;
    border-right: 1px solid var(--c-border);
    padding-right: 24px;
    min-width: fit-content;
}

.hr-ribbon-group:last-child {
    border-right: none;
}

.hr-ribbon-group-label {
    font-size: var(--t-xs);
    color: var(--c-text-3);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
    font-weight: 600;
}

/* ── Commands Row ── */
.hr-ribbon-commands {
    display: flex;
    gap: 4px;
    align-items: flex-start;
    flex: 1;
}

/* ── Command Button ── */
.hr-ribbon-cmd {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    padding: 6px 12px;
    background: transparent;
    border: 1px solid transparent;
    border-radius: var(--r-md);
    cursor: pointer;
    transition: all 0.12s;
    min-width: 60px;
    position: relative;
}

.hr-ribbon-cmd:hover {
    background: var(--c-raised);
    border-color: var(--c-border);
}

.hr-ribbon-cmd:active {
    background: var(--c-surface);
    border-color: var(--c-blue);
}

.hr-ribbon-cmd.large {
    min-width: 80px;
    padding: 8px 14px;
}

.hr-ribbon-cmd.danger:hover {
    background: rgba(239,68,68,.15);
    border-color: var(--c-red);
}

.hr-ribbon-cmd-icon {
    font-size: 20px;
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.hr-ribbon-cmd.large .hr-ribbon-cmd-icon {
    font-size: 32px;
    width: 32px;
    height: 32px;
}

.hr-ribbon-cmd-label {
    font-size: var(--t-xs);
    color: var(--c-text-2);
    text-align: center;
    line-height: 1.2;
    max-width: 80px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.hr-ribbon-cmd:hover .hr-ribbon-cmd-label {
    color: var(--c-text);
}

.hr-ribbon-cmd-badge {
    display: inline-block;
    margin-left: 4px;
    padding: 1px 4px;
    background: var(--c-amber);
    color: var(--c-base);
    font-size: 9px;
    font-weight: 700;
    border-radius: 3px;
    vertical-align: super;
}

/* ── Search Bar ── */
.hr-ribbon-search {
    position: relative;
    width: 300px;
}

.hr-ribbon-search input {
    width: 100%;
    padding: 6px 12px 6px 32px;
    background: var(--c-surface);
    border: 1px solid var(--c-border);
    border-radius: var(--r-md);
    color: var(--c-text);
    font-size: var(--t-sm);
    outline: none;
    transition: all 0.15s;
}

.hr-ribbon-search input:focus {
    border-color: var(--c-blue);
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.hr-ribbon-search-icon {
    position: absolute;
    left: 10px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--c-text-3);
    font-size: 14px;
    pointer-events: none;
}

/* ── Account Menu ── */
.hr-ribbon-account {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    background: transparent;
    border: 1px solid transparent;
    border-radius: var(--r-md);
    cursor: pointer;
    transition: all 0.12s;
    position: relative;
}

.hr-ribbon-account:hover {
    background: var(--c-raised);
    border-color: var(--c-border);
}

.hr-ribbon-account-avatar {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: var(--c-blue);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: var(--t-xs);
    font-weight: 600;
}

.hr-ribbon-account-info {
    display: flex;
    flex-direction: column;
    gap: 2px;
}

.hr-ribbon-account-name {
    font-size: var(--t-sm);
    color: var(--c-text);
    font-weight: 500;
    max-width: 120px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.hr-ribbon-account-role {
    font-size: var(--t-xs);
    color: var(--c-text-3);
}

.hr-ribbon-account-chevron {
    font-size: 10px;
    color: var(--c-text-3);
}

/* ── Account Dropdown ── */
.hr-ribbon-account-dropdown {
    position: absolute;
    top: 48px;
    right: 8px;
    min-width: 240px;
    background: var(--c-surface);
    border: 1px solid var(--c-border);
    border-radius: var(--r-md);
    box-shadow: var(--sh-lg);
    z-index: 1002;
    overflow: hidden;
}

.hr-ribbon-account-dropdown-section {
    padding: 8px;
}

.hr-ribbon-account-dropdown-header {
    font-size: var(--t-xs);
    color: var(--c-text-3);
    text-transform: uppercase;
    font-weight: 600;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
}

.hr-ribbon-account-dropdown-info {
    padding: 6px;
    font-size: var(--t-sm);
    color: var(--c-text);
}

.hr-ribbon-account-dropdown-email {
    font-size: var(--t-xs);
    color: var(--c-text-3);
    margin-top: 2px;
}

.hr-ribbon-account-dropdown-item {
    width: 100%;
    padding: 8px 12px;
    background: transparent;
    border: none;
    border-radius: var(--r-sm);
    color: var(--c-text-2);
    font-size: var(--t-sm);
    text-align: left;
    cursor: pointer;
    transition: all 0.12s;
    display: flex;
    align-items: center;
    gap: 8px;
}

.hr-ribbon-account-dropdown-item:hover {
    background: var(--c-raised);
    color: var(--c-text);
}

.hr-ribbon-account-dropdown-item.danger {
    color: var(--c-red);
}

.hr-ribbon-account-dropdown-item.danger:hover {
    background: rgba(239,68,68,.15);
}

.hr-ribbon-account-dropdown-divider {
    height: 1px;
    background: var(--c-border);
    margin: 4px 0;
}

/* ── Collapse Button ── */
.hr-ribbon-collapse-btn {
    position: absolute;
    right: 8px;
    top: 40px; /* Aligned with tab bar */
    width: 24px;
    height: 24px;
    padding: 0;
    background: transparent;
    border: 1px solid var(--c-border);
    border-radius: var(--r-sm);
    color: var(--c-text-3);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.12s;
    z-index: 999;
}

.hr-ribbon-collapse-btn:hover {
    background: var(--c-raised);
    color: var(--c-text);
}

/* ── Mobile Responsive ── */
@media (max-width: 768px) {
    .hr-ribbon {
        display: none !important;
    }

    .hr-mobile-menu {
        position: fixed;
        top: 0;
        left: -280px;
        width: 280px;
        height: 100vh;
        background: var(--c-base);
        box-shadow: 2px 0 8px rgba(0,0,0,0.3);
        z-index: 2000;
        transition: left 0.3s ease;
        overflow-y: auto;
        padding: 16px;
    }

    .hr-mobile-menu.open {
        left: 0;
    }

    .hr-mobile-hamburger {
        position: fixed;
        top: 16px;
        left: 16px;
        width: 44px;
        height: 44px;
        background: var(--c-blue);
        border: none;
        border-radius: var(--r-md);
        color: white;
        font-size: 20px;
        cursor: pointer;
        z-index: 1999;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        display: none;
    }
}

@media (max-width: 768px) {
    .hr-mobile-hamburger {
        display: flex;
        align-items: center;
        justify-content: center;
    }

    /* Adjust main content padding on mobile */
    .main .block-container {
        padding-top: 70px !important; /* Space for hamburger button */
    }
}

/* ── Tablet Responsive (simplified ribbon) ── */
@media (min-width: 769px) and (max-width: 1024px) {
    .hr-ribbon-cmd-label {
        display: none; /* Icon-only on tablet */
    }

    .hr-ribbon-cmd {
        min-width: 40px;
        padding: 6px 8px;
    }

    .hr-ribbon-search {
        width: 200px;
    }

    .hr-ribbon-account-info {
        display: none; /* Only avatar on tablet */
    }
}
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# MODAL OVERLAY SYSTEM
# ─────────────────────────────────────────────────────────────────────────────

_MODAL_CSS = """
<style>
/* ═══════════════════════════════════════════════════════ */
/* MODAL OVERLAY SYSTEM                                   */
/* ═══════════════════════════════════════════════════════ */

.modal-overlay {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(0, 0, 0, 0.75);
    backdrop-filter: blur(4px);
    z-index: 9998;
    display: flex;
    align-items: center;
    justify-content: center;
    animation: fadeIn 300ms ease-out;
}

.modal-container {
    background: var(--c-surface);
    border: 1px solid var(--c-border);
    border-radius: var(--r-lg);
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
    max-width: 800px;
    width: 90%;
    max-height: 85vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    animation: scaleIn 200ms ease-out 100ms both;
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--sp-4) var(--sp-5);
    border-bottom: 1px solid var(--c-border);
    background: var(--c-raised);
}

.modal-header h2 {
    margin: 0;
    font-size: var(--t-xl);
    color: var(--c-text);
}

.modal-close-btn {
    width: 32px;
    height: 32px;
    border: none;
    background: transparent;
    color: var(--c-text-3);
    font-size: 24px;
    cursor: pointer;
    border-radius: var(--r-md);
    transition: all 0.15s;
}

.modal-close-btn:hover {
    background: var(--c-surface);
    color: var(--c-text);
}

/* Progress Bar */
.modal-progress {
    display: flex;
    gap: var(--sp-2);
    padding: var(--sp-3) var(--sp-5);
    background: var(--c-base);
}

.progress-step {
    flex: 1;
    height: 4px;
    background: var(--c-border);
    border-radius: var(--r-pill);
    transition: background 0.3s;
}

.progress-step.active {
    background: var(--c-blue);
}

.progress-step.completed {
    background: var(--c-green);
}

/* Body */
.modal-body {
    padding: var(--sp-5);
    overflow-y: auto;
    flex: 1;
    min-height: 300px;
}

/* Footer */
.modal-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--sp-4) var(--sp-5);
    border-top: 1px solid var(--c-border);
    background: var(--c-raised);
}

.modal-footer-left {
    display: flex;
    gap: var(--sp-2);
}

.modal-footer-right {
    display: flex;
    gap: var(--sp-2);
}

/* Animations */
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

@keyframes scaleIn {
    from {
        transform: scale(0.95);
        opacity: 0;
    }
    to {
        transform: scale(1);
        opacity: 1;
    }
}

/* Mobile Responsive */
@media (max-width: 768px) {
    .modal-container {
        width: 95%;
        max-height: 90vh;
    }

    .modal-body {
        padding: var(--sp-4);
    }
}
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def apply_common_styles():
    """
    Inietta l'intero design system nell'app.
    Chiamare UNA SOLA VOLTA in app.py, non nelle singole view.

    FIX: Concatena tutti i blocchi CSS in un'unica chiamata st.markdown()
    per evitare spazio vuoto causato dal gap flex di Streamlit (16px × 12 = 192px).
    """
    all_styles = "".join([
        _DESIGN_TOKENS,
        _GLOBAL_LAYOUT,
        _SIDEBAR_CSS,
        _BUTTONS_CSS,
        _INPUTS_CSS,
        _DATAFRAME_CSS,
        _METRICS_CSS,
        _TABS_CSS,
        _EXPANDER_CSS,
        _ALERTS_CSS,
        _TOPBAR_CSS,
        _COMPONENTS_CSS,
        _RIBBON_CSS,
        _MODAL_CSS,
    ])
    st.markdown(all_styles, unsafe_allow_html=True)


def render_topbar(page_name: str, stats: str = "", status: str = "✓ Attivo"):
    """
    Topbar fissa: stats a sinistra, nome pagina al centro, stato a destra.
    """
    st.markdown(f"""
    <div class="hr-topbar">
        <span class="hr-topbar-left">{stats}</span>
        <span class="hr-topbar-center">{page_name}</span>
        <span class="hr-topbar-right">{status}</span>
    </div>
    """, unsafe_allow_html=True)


def render_section(label: str):
    """Divisore di sezione con etichetta uppercase."""
    st.markdown(f"""
    <div class="hr-section">
        <div class="hr-section-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def badge(text: str, color: str = "gray") -> str:
    """
    Restituisce HTML per un badge inline.
    color: blue | green | amber | red | gray | violet
    """
    return f'<span class="badge badge-{color}">{text}</span>'


def render_count(filtered: int, total: int):
    """Record counter compatto sotto filtri."""
    st.markdown(
        f'<span class="hr-count">{filtered} / {total}</span>',
        unsafe_allow_html=True
    )


# ── Backwards-compat (alcune view chiamano queste funzioni) ───────────────────

def render_critical_alert(message: str, details: list = None):
    html = f'<div class="hr-alert-error">❌ <strong>{message}</strong>'
    if details:
        html += "<ul>" + "".join(f"<li>{d}</li>" for d in details) + "</ul>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_warning_alert(message: str, details: list = None, expanded: bool = False):
    with st.expander(f"⚠️ {message}", expanded=expanded):
        if details:
            for d in details:
                st.markdown(f"- {d}")


def render_feedback_banner(message: str, actions: list = None):
    st.success(message)
    if actions:
        cols = st.columns(len(actions))
        for col, action in zip(cols, actions):
            with col:
                if st.button(action["label"], use_container_width=True):
                    action["callback"]()


def render_filter_badge(total_filtered: int, total_records: int):
    render_count(total_filtered, total_records)
