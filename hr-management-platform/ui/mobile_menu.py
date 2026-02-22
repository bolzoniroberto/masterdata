"""
Mobile Hamburger Menu for Responsive Design

Replaces ribbon on screens < 768px with collapsible side menu.
Provides touch-friendly navigation for mobile devices.

USES st.components.v1.html() to render complete HTML with JavaScript support.
"""

import streamlit as st
import streamlit.components.v1 as components


def render_mobile_menu():
    """
    Render hamburger menu for mobile devices using st.components.v1.html().

    Shows:
    - Hamburger button (always visible on mobile)
    - Slide-in menu with accordion sections
    - Quick access buttons
    - Account section
    """

    # Initialize mobile menu state
    if 'mobile_menu_open' not in st.session_state:
        st.session_state.mobile_menu_open = False

    # Build complete HTML
    full_html = _build_complete_mobile_html()

    # Render using components.html
    # Height: only shows on mobile (<768px), so minimal height for desktop
    components.html(full_html, height=0, scrolling=False)


def _build_complete_mobile_html() -> str:
    """Build complete mobile menu HTML document."""

    html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        /* Design Tokens (minimal for mobile menu) */
        :root {
            --c-base:    #0f172a;
            --c-surface: #1e293b;
            --c-raised:  #263348;
            --c-border:  #334155;
            --c-text:    #f1f5f9;
            --c-text-2:  #cbd5e1;
            --c-text-3:  #94a3b8;
            --c-blue:    #3b82f6;
            --c-red:     #ef4444;
            --t-xs:   0.70rem;
            --t-sm:   0.78rem;
            --t-base: 0.875rem;
            --t-lg:   1rem;
            --r-sm:  4px;
            --r-md:  6px;
        }

        body {
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        /* Mobile Hamburger Button */
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
            align-items: center;
            justify-content: center;
        }

        /* Mobile Menu Overlay */
        .hr-mobile-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.5);
            z-index: 1998;
            display: none;
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .hr-mobile-overlay.open {
            display: block;
            opacity: 1;
        }

        /* Mobile Menu */
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
            display: flex;
            flex-direction: column;
        }

        .hr-mobile-menu.open {
            left: 0;
        }

        /* Menu Header */
        .hr-mobile-menu-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px;
            border-bottom: 1px solid var(--c-border);
        }

        .hr-mobile-menu-title {
            font-size: var(--t-lg);
            font-weight: 600;
            color: var(--c-text);
        }

        .hr-mobile-menu-close {
            width: 32px;
            height: 32px;
            background: transparent;
            border: 1px solid var(--c-border);
            border-radius: var(--r-sm);
            color: var(--c-text);
            font-size: 18px;
            cursor: pointer;
        }

        /* Quick Access */
        .hr-mobile-quick-access {
            display: flex;
            gap: 8px;
            padding: 12px 16px;
            border-bottom: 1px solid var(--c-border);
        }

        .hr-mobile-qa-btn {
            flex: 1;
            height: 48px;
            background: var(--c-surface);
            border: 1px solid var(--c-border);
            border-radius: var(--r-md);
            color: var(--c-text);
            font-size: 20px;
            cursor: pointer;
        }

        .hr-mobile-qa-btn:active {
            background: var(--c-raised);
            border-color: var(--c-blue);
        }

        /* Menu Sections */
        .hr-mobile-menu-section {
            margin-bottom: 4px;
            padding: 0 8px;
        }

        .hr-mobile-menu-section-header {
            width: 100%;
            padding: 12px 16px;
            background: var(--c-surface);
            border: none;
            border-radius: var(--r-md);
            color: var(--c-text);
            font-size: var(--t-base);
            font-weight: 500;
            text-align: left;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .hr-mobile-menu-section-header:active {
            background: var(--c-raised);
        }

        .hr-mobile-menu-chevron {
            font-size: var(--t-xs);
            color: var(--c-text-3);
        }

        .hr-mobile-menu-section-content {
            padding: 4px 0 4px 16px;
            overflow: hidden;
            display: none;
        }

        .hr-mobile-menu-section-content.open {
            display: block;
        }

        .hr-mobile-menu-item {
            width: 100%;
            padding: 12px 16px;
            background: transparent;
            border: none;
            border-radius: var(--r-sm);
            color: var(--c-text-2);
            font-size: var(--t-sm);
            text-align: left;
            cursor: pointer;
            margin-bottom: 2px;
        }

        .hr-mobile-menu-item:active {
            background: var(--c-raised);
            color: var(--c-text);
        }

        .hr-mobile-menu-item.danger {
            color: var(--c-red);
        }

        /* Account Section */
        .hr-mobile-account {
            margin-top: auto;
            padding: 16px;
            border-top: 1px solid var(--c-border);
        }

        .hr-mobile-account-header {
            display: flex;
            gap: 12px;
            align-items: center;
            margin-bottom: 12px;
        }

        .hr-mobile-account-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: var(--c-blue);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: var(--t-sm);
            font-weight: 600;
        }

        .hr-mobile-account-info {
            flex: 1;
        }

        .hr-mobile-account-name {
            font-size: var(--t-base);
            color: var(--c-text);
            font-weight: 500;
        }

        .hr-mobile-account-role {
            font-size: var(--t-xs);
            color: var(--c-text-3);
        }

        .hr-mobile-account-divider {
            height: 1px;
            background: var(--c-border);
            margin: 12px 0;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .hr-mobile-hamburger {
                display: flex;
            }
        }
    </style>
</head>
<body>
    <button class="hr-mobile-hamburger" onclick="toggleMobileMenu()" id="mobile-hamburger">
        ☰
    </button>

    <div class="hr-mobile-overlay" id="mobile-overlay" onclick="toggleMobileMenu()"></div>

    <div class="hr-mobile-menu" id="mobile-menu">
        <div class="hr-mobile-menu-header">
            <div class="hr-mobile-menu-title">📊 HR Platform</div>
            <button class="hr-mobile-menu-close" onclick="toggleMobileMenu()">✕</button>
        </div>

        <div class="hr-mobile-quick-access">
            <button class="hr-mobile-qa-btn" onclick="handleMobileCommand('snapshot_manuale')" title="Save">💾</button>
            <button class="hr-mobile-qa-btn" onclick="handleMobileCommand('export_tns')" title="Export">📤</button>
            <button class="hr-mobile-qa-btn" onclick="handleMobileCommand('smart_search')" title="Search">🔎</button>
            <button class="hr-mobile-qa-btn" onclick="handleMobileCommand('gestione_versioni')" title="Versions">📚</button>
        </div>

        <!-- Home Section -->
        <div class="hr-mobile-menu-section">
            <button class="hr-mobile-menu-section-header" onclick="toggleMobileSection('home')">
                <span>🏠 Home</span>
                <span class="hr-mobile-menu-chevron" id="chevron-home">▼</span>
            </button>
            <div class="hr-mobile-menu-section-content" id="section-home">
                <button class="hr-mobile-menu-item" onclick="handleMobileCommand('dashboard_home')">Dashboard Home</button>
                <button class="hr-mobile-menu-item" onclick="handleMobileCommand('dashboard_db_org')">Dashboard DB_ORG</button>
                <button class="hr-mobile-menu-item" onclick="handleMobileCommand('smart_search')">Ricerca Intelligente</button>
            </div>
        </div>

        <!-- Gestione Dati Section -->
        <div class="hr-mobile-menu-section">
            <button class="hr-mobile-menu-section-header" onclick="toggleMobileSection('gestione')">
                <span>📝 Gestione Dati</span>
                <span class="hr-mobile-menu-chevron" id="chevron-gestione">▼</span>
            </button>
            <div class="hr-mobile-menu-section-content" id="section-gestione">
                <button class="hr-mobile-menu-item" onclick="handleMobileCommand('gestione_personale')">Gestione Personale</button>
                <button class="hr-mobile-menu-item" onclick="handleMobileCommand('scheda_dipendente')">Scheda Dipendente</button>
                <button class="hr-mobile-menu-item" onclick="handleMobileCommand('gestione_strutture')">Gestione Strutture</button>
                <button class="hr-mobile-menu-item" onclick="handleMobileCommand('scheda_strutture')">Scheda Strutture</button>
                <button class="hr-mobile-menu-item" onclick="handleMobileCommand('gestione_ruoli')">Gestione Ruoli</button>
                <button class="hr-mobile-menu-item" onclick="handleMobileCommand('import_db_org')">Import DB_ORG</button>
                <button class="hr-mobile-menu-item" onclick="handleMobileCommand('export_file')">Export File</button>
            </div>
        </div>

        <!-- Organigrammi Section -->
        <div class="hr-mobile-menu-section">
            <button class="hr-mobile-menu-section-header" onclick="toggleMobileSection('organigrammi')">
                <span>🌳 Organigrammi</span>
                <span class="hr-mobile-menu-chevron" id="chevron-organigrammi">▼</span>
            </button>
            <div class="hr-mobile-menu-section-content" id="section-organigrammi">
                <button class="hr-mobile-menu-item" onclick="handleMobileCommand('hr_hierarchy')">HR Hierarchy</button>
                <button class="hr-mobile-menu-item" onclick="handleMobileCommand('org_hierarchy')">Org Hierarchy</button>
                <button class="hr-mobile-menu-item" onclick="handleMobileCommand('sgsl_safety')">SGSL Safety</button>
                <button class="hr-mobile-menu-item" onclick="handleMobileCommand('strutture_tns')">Strutture TNS</button>
                <button class="hr-mobile-menu-item" onclick="handleMobileCommand('unita_org')">Unità Organizzative</button>
            </div>
        </div>

        <!-- Analisi Section -->
        <div class="hr-mobile-menu-section">
            <button class="hr-mobile-menu-section-header" onclick="toggleMobileSection('analisi')">
                <span>🔍 Analisi</span>
                <span class="hr-mobile-menu-chevron" id="chevron-analisi">▼</span>
            </button>
            <div class="hr-mobile-menu-section-content" id="section-analisi">
                <button class="hr-mobile-menu-item" onclick="handleMobileCommand('ricerca_intelligente')">Ricerca Intelligente</button>
                <button class="hr-mobile-menu-item" onclick="handleMobileCommand('confronta_versioni')">Confronta Versioni</button>
                <button class="hr-mobile-menu-item" onclick="handleMobileCommand('log_modifiche')">Log Modifiche</button>
            </div>
        </div>

        <!-- Versioni Section -->
        <div class="hr-mobile-menu-section">
            <button class="hr-mobile-menu-section-header" onclick="toggleMobileSection('versioni')">
                <span>🕐 Versioni</span>
                <span class="hr-mobile-menu-chevron" id="chevron-versioni">▼</span>
            </button>
            <div class="hr-mobile-menu-section-content" id="section-versioni">
                <button class="hr-mobile-menu-item" onclick="handleMobileCommand('snapshot_manuale')">Snapshot Manuale</button>
                <button class="hr-mobile-menu-item" onclick="handleMobileCommand('gestione_versioni')">Gestione Versioni</button>
                <button class="hr-mobile-menu-item" onclick="handleMobileCommand('verifica_consistenza')">Verifica Consistenza</button>
                <button class="hr-mobile-menu-item" onclick="handleMobileCommand('genera_db_tns')">Genera DB_TNS</button>
            </div>
        </div>

        <!-- Account Section -->
        <div class="hr-mobile-account">
            <div class="hr-mobile-account-header">
                <div class="hr-mobile-account-avatar">RB</div>
                <div class="hr-mobile-account-info">
                    <div class="hr-mobile-account-name">Roberto Bolzoni</div>
                    <div class="hr-mobile-account-role">HR Admin</div>
                </div>
            </div>
            <div class="hr-mobile-account-divider"></div>
            <button class="hr-mobile-menu-item" onclick="handleMobileCommand('settings')">⚙️ Impostazioni</button>
            <button class="hr-mobile-menu-item" onclick="handleMobileCommand('help')">❓ Centro Assistenza</button>
            <button class="hr-mobile-menu-item danger" onclick="handleMobileCommand('logout')">🚪 Esci</button>
        </div>
    </div>

    <script>
        // Command to page mapping (same as ribbon)
        const COMMAND_TO_PAGE = {
            'dashboard_home': 'Dashboard Home',
            'dashboard_db_org': 'Dashboard DB_ORG',
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
            'smart_search': 'Ricerca Intelligente',
            'ricerca_intelligente': 'Ricerca Intelligente',
            'confronta_versioni': 'Confronta Versioni',
            'log_modifiche': 'Log Modifiche',
            'snapshot_manuale': 'Gestione Versioni',
            'gestione_versioni': 'Gestione Versioni',
            'verifica_consistenza': 'Verifica Consistenza',
            'genera_db_tns': 'Genera DB_TNS',
            'export_tns': '💾 Salvataggio & Export',
        };

        // Toggle mobile menu
        function toggleMobileMenu() {
            const menu = document.getElementById('mobile-menu');
            const overlay = document.getElementById('mobile-overlay');
            const hamburger = document.getElementById('mobile-hamburger');

            const isOpen = menu.classList.toggle('open');
            overlay.classList.toggle('open');
            hamburger.textContent = isOpen ? '✕' : '☰';

            // Prevent body scroll when menu open
            document.body.style.overflow = isOpen ? 'hidden' : '';
        }

        // Toggle accordion section
        function toggleMobileSection(sectionId) {
            const content = document.getElementById('section-' + sectionId);
            const chevron = document.getElementById('chevron-' + sectionId);

            const isOpen = content.classList.toggle('open');
            chevron.textContent = isOpen ? '▲' : '▼';
        }

        // Handle mobile command
        function handleMobileCommand(cmdId) {
            console.log('Mobile command:', cmdId);

            // Close menu
            toggleMobileMenu();

            // Special commands
            if (cmdId === 'settings' || cmdId === 'help' || cmdId === 'logout') {
                alert(cmdId.toUpperCase() + ' - To be implemented');
                return;
            }

            // Navigate to page
            const page = COMMAND_TO_PAGE[cmdId];
            if (page) {
                navigateToPage('current_page', page);
            }
        }

        // Navigate to page (communicate with Streamlit)
        function navigateToPage(key, value) {
            const params = new URLSearchParams(window.parent.location.search);
            params.set(key, value);
            params.set('_t', Date.now());
            window.parent.location.search = params.toString();
        }
    </script>
</body>
</html>
"""

    return html
