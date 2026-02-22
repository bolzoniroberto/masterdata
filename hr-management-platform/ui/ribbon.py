"""
Ribbon Interface Component for HR Platform

Implements Microsoft Office-style ribbon with:
- 5 task-based tabs (Home, Gestione Dati, Organigrammi, Analisi, Versioni)
- Quick Access Toolbar
- Integrated search bar
- Account/Settings menu
- Collapse/minimize functionality
- Responsive mobile hamburger menu

USES st.components.v1.html() to render complete HTML with JavaScript support.
"""

import streamlit as st
import streamlit.components.v1 as components
from typing import Literal, Optional

RibbonTab = Literal["Home", "Gestione Dati", "Organigrammi", "Analisi", "Versioni"]


def render_ribbon(active_tab: Optional[RibbonTab] = None):
    """
    Render the complete ribbon interface using st.components.v1.html().

    Args:
        active_tab: Currently active tab (if None, defaults to Home)
    """
    # Initialize session state
    if 'ribbon_collapsed' not in st.session_state:
        st.session_state.ribbon_collapsed = False
    if 'qat_commands' not in st.session_state:
        st.session_state.qat_commands = ['save', 'undo', 'redo', 'export', 'refresh']
    if 'active_ribbon_tab' not in st.session_state:
        st.session_state.active_ribbon_tab = active_tab or "Home"

    # Leggi il tab dalla URL se disponibile
    url_tab = st.query_params.get('active_ribbon_tab')
    if url_tab:
        st.session_state.active_ribbon_tab = url_tab

    # Build complete HTML document (HTML + CSS + JavaScript)
    full_html = _build_complete_html()

    # Render using components.html (preserves onclick and JavaScript)
    # CRITICAL: Use exact height to prevent Streamlit container collapse
    # Height calculation: QAT (32px) + Tabs (40px) + Content (80px) + buffer = 180px
    height = 180 if not st.session_state.ribbon_collapsed else 90

    # Use unsafe_allow_html wrapper to ensure proper rendering
    components.html(full_html, height=height, scrolling=False)


def _build_complete_html() -> str:
    """Build complete HTML document with CSS and JavaScript."""

    collapsed_class = "collapsed" if st.session_state.ribbon_collapsed else ""
    active_tab = st.session_state.active_ribbon_tab

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        /* ═══ DESIGN TOKENS ═══ */
        :root {{
            /* Palette dark */
            --c-base:    #0f172a;
            --c-surface: #1e293b;
            --c-raised:  #263348;
            --c-border:  #334155;
            --c-border-l:#1e293b;

            /* Testo */
            --c-text:    #f1f5f9;
            --c-text-2:  #cbd5e1;
            --c-text-3:  #94a3b8;

            /* Accenti */
            --c-blue:    #3b82f6;
            --c-blue-h:  #2563eb;
            --c-green:   #22c55e;
            --c-amber:   #f59e0b;
            --c-red:     #ef4444;
            --c-sky:     #0ea5e9;
            --c-violet:  #8b5cf6;

            /* Spaziatura */
            --sp-1: 4px;
            --sp-2: 8px;
            --sp-3: 12px;
            --sp-4: 16px;
            --sp-5: 20px;
            --sp-6: 24px;
            --sp-8: 32px;

            /* Tipografia */
            --t-xs:   0.70rem;
            --t-sm:   0.78rem;
            --t-base: 0.875rem;
            --t-md:   0.9375rem;
            --t-lg:   1rem;
            --t-xl:   1.125rem;

            /* Bordi arrotondati */
            --r-sm:  4px;
            --r-md:  6px;
            --r-lg:  8px;
            --r-xl:  12px;
            --r-pill:9999px;

            /* Ombre */
            --sh-sm: 0 1px 3px rgba(0,0,0,.35);
            --sh-md: 0 3px 8px rgba(0,0,0,.4);
            --sh-lg: 0 8px 20px rgba(0,0,0,.45);

            /* Transizioni */
            --tr: 150ms ease;
        }}

        /* ═══ RESET & BASE ═══ */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        html {{
            width: 100%;
            height: 100%;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: var(--c-base);
            color: var(--c-text);
            margin: 0;
            padding: 0;
            width: 100%;
            height: auto;
            min-height: 180px !important;
            overflow-x: hidden !important;
            overflow-y: auto !important;
            display: flex;
            flex-direction: column;
        }}

        /* ═══ RIBBON CSS ═══ */
        .hr-ribbon {{
            width: 100%;
            background: var(--c-base);
            border-bottom: 1px solid var(--c-border);
            box-shadow: var(--sh-md);
            transition: height 0.2s ease;
        }}

        .hr-ribbon.collapsed .hr-ribbon-content {{
            display: none;
        }}

        /* Quick Access Toolbar */
        .hr-qat {{
            display: flex;
            gap: 2px;
            padding: 4px 8px;
            background: var(--c-surface);
            border-bottom: 1px solid var(--c-border);
            height: 32px;
            align-items: center;
        }}

        .hr-qat-btn {{
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
        }}

        .hr-qat-btn:hover {{
            background: var(--c-raised);
            border-color: var(--c-border);
        }}

        /* Tab Bar */
        .hr-ribbon-tabs {{
            display: flex;
            align-items: center;
            background: var(--c-surface);
            height: 40px;
            border-bottom: 1px solid var(--c-border);
            padding-left: 8px;
            gap: 2px;
            position: relative;
        }}

        .hr-ribbon-tab {{
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
        }}

        .hr-ribbon-tab:hover {{
            background: var(--c-raised);
            color: var(--c-text);
        }}

        .hr-ribbon-tab.active {{
            background: var(--c-base);
            border-bottom-color: var(--c-blue);
            color: var(--c-blue);
        }}

        .hr-ribbon-tab-extras {{
            margin-left: auto;
            display: flex;
            align-items: center;
            gap: 12px;
            padding-right: 48px;
        }}

        /* Ribbon Content */
        .hr-ribbon-content {{
            display: flex;
            gap: 24px;
            padding: 12px 16px;
            background: var(--c-base);
            overflow-x: auto;
            overflow-y: hidden;
            min-height: 80px;
        }}

        /* Group */
        .hr-ribbon-group {{
            display: flex;
            flex-direction: column;
            border-right: 1px solid var(--c-border);
            padding-right: 24px;
            min-width: fit-content;
        }}

        .hr-ribbon-group:last-child {{
            border-right: none;
        }}

        .hr-ribbon-group-label {{
            font-size: var(--t-xs);
            color: var(--c-text-3);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
            font-weight: 600;
        }}

        .hr-ribbon-commands {{
            display: flex;
            gap: 4px;
            align-items: flex-start;
            flex: 1;
        }}

        /* Command Button */
        .hr-ribbon-cmd {{
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
        }}

        .hr-ribbon-cmd:hover {{
            background: var(--c-raised);
            border-color: var(--c-border);
        }}

        .hr-ribbon-cmd:active {{
            background: var(--c-surface);
            border-color: var(--c-blue);
        }}

        .hr-ribbon-cmd.large {{
            min-width: 80px;
            padding: 8px 14px;
        }}

        .hr-ribbon-cmd.danger:hover {{
            background: rgba(239,68,68,.15);
            border-color: var(--c-red);
        }}

        .hr-ribbon-cmd-icon {{
            font-size: 20px;
        }}

        .hr-ribbon-cmd.large .hr-ribbon-cmd-icon {{
            font-size: 32px;
        }}

        .hr-ribbon-cmd-label {{
            font-size: var(--t-xs);
            color: var(--c-text-2);
            text-align: center;
            line-height: 1.2;
            max-width: 80px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .hr-ribbon-cmd:hover .hr-ribbon-cmd-label {{
            color: var(--c-text);
        }}

        .hr-ribbon-cmd-badge {{
            display: inline-block;
            margin-left: 4px;
            padding: 1px 4px;
            background: var(--c-amber);
            color: var(--c-base);
            font-size: 9px;
            font-weight: 700;
            border-radius: 3px;
            vertical-align: super;
        }}

        /* Search Bar */
        .hr-ribbon-search {{
            position: relative;
            width: 300px;
        }}

        .hr-ribbon-search input {{
            width: 100%;
            padding: 6px 12px 6px 32px;
            background: var(--c-surface);
            border: 1px solid var(--c-border);
            border-radius: var(--r-md);
            color: var(--c-text);
            font-size: var(--t-sm);
            outline: none;
            transition: all 0.15s;
        }}

        .hr-ribbon-search input:focus {{
            border-color: var(--c-blue);
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }}

        .hr-ribbon-search-icon {{
            position: absolute;
            left: 10px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--c-text-3);
            font-size: 14px;
            pointer-events: none;
        }}

        /* Account Menu */
        .hr-ribbon-account {{
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
        }}

        .hr-ribbon-account:hover {{
            background: var(--c-raised);
            border-color: var(--c-border);
        }}

        .hr-ribbon-account-avatar {{
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
        }}

        .hr-ribbon-account-info {{
            display: flex;
            flex-direction: column;
            gap: 2px;
        }}

        .hr-ribbon-account-name {{
            font-size: var(--t-sm);
            color: var(--c-text);
            font-weight: 500;
            max-width: 120px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .hr-ribbon-account-role {{
            font-size: var(--t-xs);
            color: var(--c-text-3);
        }}

        .hr-ribbon-account-chevron {{
            font-size: 10px;
            color: var(--c-text-3);
        }}

        /* Account Dropdown */
        .hr-ribbon-account-dropdown {{
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
            display: none;
        }}

        .hr-ribbon-account-dropdown.show {{
            display: block;
        }}

        .hr-ribbon-account-dropdown-section {{
            padding: 8px;
        }}

        .hr-ribbon-account-dropdown-header {{
            font-size: var(--t-xs);
            color: var(--c-text-3);
            text-transform: uppercase;
            font-weight: 600;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
        }}

        .hr-ribbon-account-dropdown-info {{
            padding: 6px;
            font-size: var(--t-sm);
            color: var(--c-text);
        }}

        .hr-ribbon-account-dropdown-email {{
            font-size: var(--t-xs);
            color: var(--c-text-3);
            margin-top: 2px;
        }}

        .hr-ribbon-account-dropdown-item {{
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
        }}

        .hr-ribbon-account-dropdown-item:hover {{
            background: var(--c-raised);
            color: var(--c-text);
        }}

        .hr-ribbon-account-dropdown-item.danger {{
            color: var(--c-red);
        }}

        .hr-ribbon-account-dropdown-item.danger:hover {{
            background: rgba(239,68,68,.15);
        }}

        .hr-ribbon-account-dropdown-divider {{
            height: 1px;
            background: var(--c-border);
            margin: 4px 0;
        }}

        /* Collapse Button */
        .hr-ribbon-collapse-btn {{
            position: absolute;
            right: 8px;
            top: 8px;
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
        }}

        .hr-ribbon-collapse-btn:hover {{
            background: var(--c-raised);
            color: var(--c-text);
        }}

        /* Responsive */
        @media (max-width: 768px) {{
            .hr-ribbon {{
                display: none !important;
            }}
        }}

        @media (min-width: 769px) and (max-width: 1024px) {{
            .hr-ribbon-cmd-label {{
                display: none;
            }}
            .hr-ribbon-cmd {{
                min-width: 40px;
                padding: 6px 8px;
            }}
            .hr-ribbon-search {{
                width: 200px;
            }}
            .hr-ribbon-account-info {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <div class="hr-ribbon {collapsed_class}" id="hr-ribbon">
        {_build_qat_html()}
        <div class="hr-ribbon-tabs">
            {_build_tabs_html(active_tab)}
            {_build_tab_extras_html()}
            {_build_collapse_button_html()}
        </div>
        <div class="hr-ribbon-content">
            {_build_tab_content_html(active_tab)}
        </div>
    </div>

    <script>
        // Command to page mapping
        const COMMAND_TO_PAGE = {{
            'dashboard_home': 'Dashboard Home',
            'dashboard_db_org': 'Dashboard DB_ORG',
            'stats_refresh': null,  // Special: reload
            'new_employee': 'Scheda Dipendente',
            'new_structure': 'Scheda Strutture',
            'import_file': 'Import DB_ORG',
            'export_tns': '💾 Salvataggio & Export',
            'smart_search': 'Ricerca Intelligente',
            'gestione_personale': 'Gestione Personale',
            'scheda_dipendente': 'Scheda Dipendente',
            'gestione_strutture': 'Gestione Strutture',
            'scheda_strutture': 'Scheda Strutture',
            'gestione_ruoli': 'Gestione Ruoli',
            'import_db_org': 'Import DB_ORG',
            'export_file': '💾 Salvataggio & Export',
            'hr_hierarchy': 'HR Hierarchy',
            'org_hierarchy': 'TNS Travel',
            'sgsl_safety': 'SGSL Safety',
            'strutture_tns': 'Strutture TNS',
            'unita_org': 'Unità Organizzative',
            'ricerca_intelligente': 'Ricerca Intelligente',
            'confronta_versioni': 'Confronta Versioni',
            'log_modifiche': 'Log Modifiche',
            'snapshot_manuale': 'Gestione Versioni',
            'checkpoint_rapido': 'Gestione Versioni',
            'gestione_versioni': 'Gestione Versioni',
            'verifica_consistenza': 'Verifica Consistenza',
            'genera_db_tns': 'Genera DB_TNS',
            'svuota_db': null,  // Special: confirmation dialog
        }};

        // Handle ribbon command
        function handleRibbonCommand(cmdId) {{
            console.log('Ribbon command:', cmdId);

            // Special commands
            if (cmdId === 'stats_refresh') {{
                window.parent.location.reload();
                return;
            }}

            if (cmdId === 'svuota_db') {{
                if (confirm('⚠️ ATTENZIONE: Questa operazione eliminerà tutti i dati dal database.\\n\\nSei sicuro di voler continuare?')) {{
                    navigateToPage('show_clear_db_confirm', true);
                }}
                return;
            }}

            if (cmdId === 'snapshot_manuale' || cmdId === 'checkpoint_rapido') {{
                navigateToPage('show_manual_snapshot_dialog', true);
                return;
            }}

            // Standard navigation
            const page = COMMAND_TO_PAGE[cmdId];
            if (page) {{
                navigateToPage('current_page', page);
            }} else {{
                console.warn('No page mapping for command:', cmdId);
            }}
        }}

        // QAT command handlers
        function handleQATCommand(cmd) {{
            console.log('QAT command:', cmd);
            const actions = {{
                'save': () => handleRibbonCommand('snapshot_manuale'),
                'export': () => handleRibbonCommand('export_tns'),
                'refresh': () => window.parent.location.reload(),
                'undo': () => console.log('Undo not yet implemented'),
                'redo': () => console.log('Redo not yet implemented'),
            }};
            if (actions[cmd]) actions[cmd]();
        }}

        // Set active tab
        function setRibbonTab(tabName) {{
            console.log('Ribbon: Switching to tab:', tabName);

            // Save to sessionStorage so Streamlit can read it
            let sessionStorageSaved = false;

            try {{
                window.parent.sessionStorage.setItem('active_ribbon_tab', tabName);
                console.log('✓ Ribbon: Saved to parent sessionStorage:', tabName);
                sessionStorageSaved = true;
            }} catch (e) {{
                console.log('✗ Ribbon: Cannot access parent sessionStorage:', e.message);
            }}

            if (!sessionStorageSaved) {{
                try {{
                    window.top.sessionStorage.setItem('active_ribbon_tab', tabName);
                    console.log('✓ Ribbon: Saved to window.top sessionStorage:', tabName);
                    sessionStorageSaved = true;
                }} catch (e2) {{
                    console.log('✗ Ribbon: Cannot access window.top sessionStorage:', e2.message);
                }}
            }}

            if (!sessionStorageSaved) {{
                try {{
                    window.sessionStorage.setItem('active_ribbon_tab', tabName);
                    console.log('✓ Ribbon: Saved to local window sessionStorage:', tabName);
                    sessionStorageSaved = true;
                }} catch (e3) {{
                    console.log('✗ Ribbon: Cannot access local sessionStorage:', e3.message);
                }}
            }}

            if (!sessionStorageSaved) {{
                console.warn('⚠ Ribbon: FAILED to save to any sessionStorage!');
            }}

            // FIX: Navigare il parent direttamente (non replaceState in iframe)
            console.log('Ribbon: Updating URL with new tab:', tabName);

            const url = new URL(window.parent.location.href);
            url.searchParams.set('active_ribbon_tab', tabName);
            window.parent.location.href = url.toString();

            console.log('✓ Navigating parent to:', url.toString());
        }}

        // Toggle ribbon collapse
        function toggleRibbonCollapse() {{
            const ribbon = document.getElementById('hr-ribbon');
            const isCollapsed = ribbon.classList.toggle('collapsed');
            const btn = document.querySelector('.hr-ribbon-collapse-btn');
            btn.textContent = isCollapsed ? '⌄' : '⌃';

            // Notify parent to update session state
            window.parent.postMessage({{
                type: 'streamlit:setComponentValue',
                key: 'ribbon_collapsed',
                value: isCollapsed
            }}, '*');
        }}

        // Toggle account menu
        function toggleAccountMenu() {{
            const dropdown = document.getElementById('account-dropdown');
            dropdown.classList.toggle('show');
        }}

        // Handle account actions
        function handleAccountAction(action) {{
            console.log('Account action:', action);
            toggleAccountMenu();

            if (action === 'logout') {{
                if (confirm('Sei sicuro di voler uscire?')) {{
                    alert('Logout functionality to be implemented');
                }}
            }} else if (action === 'settings') {{
                alert('Settings panel to be implemented');
            }} else if (action === 'theme') {{
                alert('Theme switcher to be implemented');
            }} else if (action === 'help') {{
                alert('Help center to be implemented');
            }}
        }}

        // Navigate to page (communicate with Streamlit parent via postMessage)
        function navigateToPage(key, value) {{
            console.log('Ribbon: Sending postMessage to parent:', key, '=', value);

            // Send message to parent Streamlit window
            // Parent will handle the URL change safely
            window.parent.postMessage({{
                type: 'ribbon-navigation',
                key: key,
                value: value
            }}, '*');

            console.log('postMessage sent to parent');
        }}

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {{
            if (e.ctrlKey && e.key === 'k') {{
                e.preventDefault();
                document.getElementById('ribbon-search-input')?.focus();
            }}
            if (e.key === 'F1') {{
                e.preventDefault();
                toggleRibbonCollapse();
            }}
            if (e.ctrlKey && e.key === 's') {{
                e.preventDefault();
                handleQATCommand('save');
            }}
            if (e.ctrlKey && e.key === 'e') {{
                e.preventDefault();
                handleQATCommand('export');
            }}
        }});

        // Close account dropdown when clicking outside
        document.addEventListener('click', (e) => {{
            const account = document.querySelector('.hr-ribbon-account');
            const dropdown = document.getElementById('account-dropdown');
            if (account && dropdown && !account.contains(e.target) && !dropdown.contains(e.target)) {{
                dropdown.classList.remove('show');
            }}
        }});

        // CRITICAL: Attach event listeners to tab buttons
        // This avoids the issue of Streamlit stripping onclick attributes
        document.addEventListener('DOMContentLoaded', () => {{
            console.log('Ribbon: Initializing tab click listeners...');

            // Get all tab buttons
            const tabButtons = document.querySelectorAll('.hr-ribbon-tab[data-tab]');
            console.log('Ribbon: Found', tabButtons.length, 'tab buttons');

            // Attach click listener to each tab
            tabButtons.forEach((btn) => {{
                btn.addEventListener('click', (e) => {{
                    const tabName = btn.getAttribute('data-tab');
                    console.log('Ribbon: Tab button clicked:', tabName);
                    setRibbonTab(tabName);
                }});
            }});

            console.log('Ribbon: Tab listeners attached successfully');
        }});

        // ═══ NOTE: postMessage listener REMOVED ═══
        // The ribbon now uses sessionStorage instead of trying to navigate the parent
        // The main Streamlit window has a poller that watches sessionStorage
        console.log('Ribbon: Using sessionStorage for tab changes (no direct navigation needed)');
    </script>
</body>
</html>
"""

    return html


def _build_qat_html() -> str:
    """Build Quick Access Toolbar HTML."""
    commands = st.session_state.qat_commands
    buttons = ""

    qat_info = {
        'save': ('💾', 'Salva snapshot'),
        'undo': ('↩️', 'Annulla'),
        'redo': ('↪️', 'Ripeti'),
        'export': ('📤', 'Export DB_TNS'),
        'refresh': ('🔄', 'Aggiorna'),
    }

    for cmd in commands:
        icon, tooltip = qat_info.get(cmd, ('❓', 'Unknown'))
        buttons += f'<button class="hr-qat-btn" title="{tooltip}" onclick="handleQATCommand(\'{cmd}\')">{icon}</button>\n'

    return f'<div class="hr-qat">{buttons}</div>'


def _build_tabs_html(active_tab: str) -> str:
    """Build ribbon tabs HTML."""
    tabs = ["Home", "Gestione Dati", "Organigrammi", "Analisi", "Versioni"]
    html = ""

    for tab in tabs:
        active_class = "active" if tab == active_tab else ""
        # Use data-tab attribute instead of onclick to avoid Streamlit stripping event handlers
        html += f'<button class="hr-ribbon-tab {active_class}" data-tab="{tab}">{tab}</button>\n'

    return html


def _build_tab_extras_html() -> str:
    """Build search bar and account menu."""
    return """
    <div class="hr-ribbon-tab-extras">
        <div class="hr-ribbon-search">
            <span class="hr-ribbon-search-icon">🔎</span>
            <input type="text" id="ribbon-search-input" placeholder="Cerca comandi, dati, help... (Ctrl+K)" autocomplete="off">
        </div>
        <div class="hr-ribbon-account" onclick="toggleAccountMenu()">
            <div class="hr-ribbon-account-avatar">RB</div>
            <div class="hr-ribbon-account-info">
                <div class="hr-ribbon-account-name">Roberto Bolzoni</div>
                <div class="hr-ribbon-account-role">HR Admin</div>
            </div>
            <span class="hr-ribbon-account-chevron">▼</span>
        </div>
        <div class="hr-ribbon-account-dropdown" id="account-dropdown">
            <div class="hr-ribbon-account-dropdown-section">
                <div class="hr-ribbon-account-dropdown-header">Profilo</div>
                <div class="hr-ribbon-account-dropdown-info">
                    <div>Roberto Bolzoni</div>
                    <div class="hr-ribbon-account-dropdown-email">roberto.bolzoni@ilsole24ore.com</div>
                </div>
            </div>
            <div class="hr-ribbon-account-dropdown-divider"></div>
            <div class="hr-ribbon-account-dropdown-section">
                <button class="hr-ribbon-account-dropdown-item" onclick="handleAccountAction('settings')">⚙️ Impostazioni</button>
                <button class="hr-ribbon-account-dropdown-item" onclick="handleAccountAction('theme')">🎨 Tema</button>
                <button class="hr-ribbon-account-dropdown-item" onclick="handleAccountAction('help')">❓ Centro Assistenza</button>
            </div>
            <div class="hr-ribbon-account-dropdown-divider"></div>
            <div class="hr-ribbon-account-dropdown-section">
                <button class="hr-ribbon-account-dropdown-item danger" onclick="handleAccountAction('logout')">🚪 Esci</button>
            </div>
        </div>
    </div>
    """


def _build_collapse_button_html() -> str:
    """Build collapse button."""
    icon = "⌃" if not st.session_state.ribbon_collapsed else "⌄"
    return f'<button class="hr-ribbon-collapse-btn" onclick="toggleRibbonCollapse()" title="Comprimi ribbon (F1)">{icon}</button>'


def _build_tab_content_html(active_tab: str) -> str:
    """Build content for active tab."""

    content_builders = {
        "Home": _build_home_content,
        "Gestione Dati": _build_gestione_content,
        "Organigrammi": _build_organigrammi_content,
        "Analisi": _build_analisi_content,
        "Versioni": _build_versioni_content,
    }

    builder = content_builders.get(active_tab, _build_home_content)
    return builder()


def _build_home_content() -> str:
    """Build Home tab content."""
    return """
    <div class="hr-ribbon-group">
        <div class="hr-ribbon-group-label">Dashboard</div>
        <div class="hr-ribbon-commands">
            <button class="hr-ribbon-cmd" onclick="handleRibbonCommand('dashboard_home')">
                <div class="hr-ribbon-cmd-icon">📊</div>
                <div class="hr-ribbon-cmd-label">Dashboard Home</div>
            </button>
            <button class="hr-ribbon-cmd" onclick="handleRibbonCommand('dashboard_db_org')">
                <div class="hr-ribbon-cmd-icon">🗄️</div>
                <div class="hr-ribbon-cmd-label">Dashboard DB_ORG</div>
            </button>
            <button class="hr-ribbon-cmd" onclick="handleRibbonCommand('stats_refresh')">
                <div class="hr-ribbon-cmd-icon">🔄</div>
                <div class="hr-ribbon-cmd-label">Aggiorna Stats</div>
            </button>
        </div>
    </div>
    <div class="hr-ribbon-group">
        <div class="hr-ribbon-group-label">Azioni Rapide</div>
        <div class="hr-ribbon-commands">
            <button class="hr-ribbon-cmd large" onclick="handleRibbonCommand('new_employee')">
                <div class="hr-ribbon-cmd-icon">👤➕</div>
                <div class="hr-ribbon-cmd-label">Nuovo Dipendente</div>
            </button>
            <button class="hr-ribbon-cmd large" onclick="handleRibbonCommand('new_structure')">
                <div class="hr-ribbon-cmd-icon">🏢➕</div>
                <div class="hr-ribbon-cmd-label">Nuova Struttura</div>
            </button>
            <button class="hr-ribbon-cmd large" onclick="handleRibbonCommand('import_file')">
                <div class="hr-ribbon-cmd-icon">📥</div>
                <div class="hr-ribbon-cmd-label">Import File</div>
            </button>
            <button class="hr-ribbon-cmd large" onclick="handleRibbonCommand('export_tns')">
                <div class="hr-ribbon-cmd-icon">📤</div>
                <div class="hr-ribbon-cmd-label">Export DB_TNS</div>
            </button>
        </div>
    </div>
    <div class="hr-ribbon-group">
        <div class="hr-ribbon-group-label">Ricerca</div>
        <div class="hr-ribbon-commands">
            <button class="hr-ribbon-cmd" onclick="handleRibbonCommand('smart_search')">
                <div class="hr-ribbon-cmd-icon">🔎</div>
                <div class="hr-ribbon-cmd-label">Ricerca Intelligente</div>
            </button>
        </div>
    </div>
    """


def _build_gestione_content() -> str:
    """Build Gestione Dati tab content."""
    return """
    <div class="hr-ribbon-group">
        <div class="hr-ribbon-group-label">Dipendenti</div>
        <div class="hr-ribbon-commands">
            <button class="hr-ribbon-cmd" onclick="handleRibbonCommand('gestione_personale')">
                <div class="hr-ribbon-cmd-icon">📋</div>
                <div class="hr-ribbon-cmd-label">Gestione Personale</div>
            </button>
            <button class="hr-ribbon-cmd" onclick="handleRibbonCommand('scheda_dipendente')">
                <div class="hr-ribbon-cmd-icon">🪪</div>
                <div class="hr-ribbon-cmd-label">Scheda Dipendente</div>
            </button>
        </div>
    </div>
    <div class="hr-ribbon-group">
        <div class="hr-ribbon-group-label">Strutture</div>
        <div class="hr-ribbon-commands">
            <button class="hr-ribbon-cmd" onclick="handleRibbonCommand('gestione_strutture')">
                <div class="hr-ribbon-cmd-icon">🏛️</div>
                <div class="hr-ribbon-cmd-label">Gestione Strutture</div>
            </button>
            <button class="hr-ribbon-cmd" onclick="handleRibbonCommand('scheda_strutture')">
                <div class="hr-ribbon-cmd-icon">📐</div>
                <div class="hr-ribbon-cmd-label">Scheda Strutture</div>
            </button>
        </div>
    </div>
    <div class="hr-ribbon-group">
        <div class="hr-ribbon-group-label">Ruoli</div>
        <div class="hr-ribbon-commands">
            <button class="hr-ribbon-cmd" onclick="handleRibbonCommand('gestione_ruoli')">
                <div class="hr-ribbon-cmd-icon">🎯</div>
                <div class="hr-ribbon-cmd-label">Gestione Ruoli</div>
            </button>
        </div>
    </div>
    <div class="hr-ribbon-group">
        <div class="hr-ribbon-group-label">Import/Export</div>
        <div class="hr-ribbon-commands">
            <button class="hr-ribbon-cmd large" onclick="handleRibbonCommand('import_db_org')">
                <div class="hr-ribbon-cmd-icon">📥</div>
                <div class="hr-ribbon-cmd-label">Import DB_ORG</div>
            </button>
            <button class="hr-ribbon-cmd large" onclick="handleRibbonCommand('export_file')">
                <div class="hr-ribbon-cmd-icon">💾</div>
                <div class="hr-ribbon-cmd-label">Export File</div>
            </button>
        </div>
    </div>
    """


def _build_organigrammi_content() -> str:
    """Build Organigrammi tab content."""
    return """
    <div class="hr-ribbon-group">
        <div class="hr-ribbon-group-label">Viste Organigrammi</div>
        <div class="hr-ribbon-commands">
            <button class="hr-ribbon-cmd large" onclick="handleRibbonCommand('hr_hierarchy')">
                <div class="hr-ribbon-cmd-icon">👥</div>
                <div class="hr-ribbon-cmd-label">HR Hierarchy</div>
            </button>
            <button class="hr-ribbon-cmd large" onclick="handleRibbonCommand('org_hierarchy')">
                <div class="hr-ribbon-cmd-icon">🧳</div>
                <div class="hr-ribbon-cmd-label">Org Hierarchy</div>
            </button>
            <button class="hr-ribbon-cmd large" onclick="handleRibbonCommand('sgsl_safety')">
                <div class="hr-ribbon-cmd-icon">🛡️</div>
                <div class="hr-ribbon-cmd-label">SGSL Safety<span class="hr-ribbon-cmd-badge">BETA</span></div>
            </button>
            <button class="hr-ribbon-cmd large" onclick="handleRibbonCommand('strutture_tns')">
                <div class="hr-ribbon-cmd-icon">✅</div>
                <div class="hr-ribbon-cmd-label">Strutture TNS</div>
            </button>
            <button class="hr-ribbon-cmd large" onclick="handleRibbonCommand('unita_org')">
                <div class="hr-ribbon-cmd-icon">🏛️</div>
                <div class="hr-ribbon-cmd-label">Unità Organizzative</div>
            </button>
        </div>
    </div>
    """


def _build_analisi_content() -> str:
    """Build Analisi tab content."""
    return """
    <div class="hr-ribbon-group">
        <div class="hr-ribbon-group-label">Ricerca Avanzata</div>
        <div class="hr-ribbon-commands">
            <button class="hr-ribbon-cmd" onclick="handleRibbonCommand('ricerca_intelligente')">
                <div class="hr-ribbon-cmd-icon">🔍</div>
                <div class="hr-ribbon-cmd-label">Ricerca Intelligente</div>
            </button>
        </div>
    </div>
    <div class="hr-ribbon-group">
        <div class="hr-ribbon-group-label">Confronti</div>
        <div class="hr-ribbon-commands">
            <button class="hr-ribbon-cmd" onclick="handleRibbonCommand('confronta_versioni')">
                <div class="hr-ribbon-cmd-icon">⚖️</div>
                <div class="hr-ribbon-cmd-label">Confronta Versioni</div>
            </button>
        </div>
    </div>
    <div class="hr-ribbon-group">
        <div class="hr-ribbon-group-label">Audit Log</div>
        <div class="hr-ribbon-commands">
            <button class="hr-ribbon-cmd" onclick="handleRibbonCommand('log_modifiche')">
                <div class="hr-ribbon-cmd-icon">📜</div>
                <div class="hr-ribbon-cmd-label">Log Modifiche</div>
            </button>
        </div>
    </div>
    """


def _build_versioni_content() -> str:
    """Build Versioni tab content."""
    return """
    <div class="hr-ribbon-group">
        <div class="hr-ribbon-group-label">Snapshot</div>
        <div class="hr-ribbon-commands">
            <button class="hr-ribbon-cmd large" onclick="handleRibbonCommand('snapshot_manuale')">
                <div class="hr-ribbon-cmd-icon">📸</div>
                <div class="hr-ribbon-cmd-label">Snapshot Manuale</div>
            </button>
            <button class="hr-ribbon-cmd large" onclick="handleRibbonCommand('checkpoint_rapido')">
                <div class="hr-ribbon-cmd-icon">⚡</div>
                <div class="hr-ribbon-cmd-label">Checkpoint Rapido</div>
            </button>
        </div>
    </div>
    <div class="hr-ribbon-group">
        <div class="hr-ribbon-group-label">Gestione Versioni</div>
        <div class="hr-ribbon-commands">
            <button class="hr-ribbon-cmd" onclick="handleRibbonCommand('gestione_versioni')">
                <div class="hr-ribbon-cmd-icon">📚</div>
                <div class="hr-ribbon-cmd-label">Lista Versioni</div>
            </button>
        </div>
    </div>
    <div class="hr-ribbon-group">
        <div class="hr-ribbon-group-label">Sincronizzazione</div>
        <div class="hr-ribbon-commands">
            <button class="hr-ribbon-cmd" onclick="handleRibbonCommand('verifica_consistenza')">
                <div class="hr-ribbon-cmd-icon">✅</div>
                <div class="hr-ribbon-cmd-label">Verifica Consistenza</div>
            </button>
        </div>
    </div>
    <div class="hr-ribbon-group">
        <div class="hr-ribbon-group-label">Operazioni Avanzate</div>
        <div class="hr-ribbon-commands">
            <button class="hr-ribbon-cmd" onclick="handleRibbonCommand('genera_db_tns')">
                <div class="hr-ribbon-cmd-icon">🔄</div>
                <div class="hr-ribbon-cmd-label">Genera DB_TNS</div>
            </button>
            <button class="hr-ribbon-cmd danger" onclick="handleRibbonCommand('svuota_db')">
                <div class="hr-ribbon-cmd-icon">🗑️</div>
                <div class="hr-ribbon-cmd-label">Svuota Database</div>
            </button>
        </div>
    </div>
    """
