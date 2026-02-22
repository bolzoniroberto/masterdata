"""
Settings Wizard Modal - 3-step configuration flow.

Steps:
1. Theme Selection (with live preview)
2. Notifications Configuration
3. Locale Settings (language & timezone)
"""

import streamlit as st
import time
from ui.wizard_state_manager import get_settings_wizard
from services.settings_service import get_settings_service


# ═══════════════════════════════════════════════════════════
# STEP RENDERERS
# ═══════════════════════════════════════════════════════════

def render_step_1_theme(wizard):
    """Step 1: Theme Selection"""
    st.markdown("### 🎨 Tema Interfaccia (1/3)")
    st.markdown("Scegli il tema per l'interfaccia della piattaforma.")

    # Theme options
    theme = st.radio(
        "Seleziona tema",
        options=['dark', 'light', 'auto'],
        format_func=lambda x: {
            'dark': '🌙 Dark Mode',
            'light': '☀️ Light Mode',
            'auto': '🔄 Auto (sistema)'
        }[x],
        index=0,
        key="theme_radio"
    )

    wizard.set_data('theme', theme)

    # Live preview
    st.markdown("#### Anteprima")

    if theme == 'dark':
        st.markdown("""
        <div style="background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 1rem; color: #e2e8f0;">
            <h4 style="margin: 0; color: #e2e8f0;">Dashboard</h4>
            <p style="color: #94a3b8; margin: 0.5rem 0;">Tema scuro con sfondo blu scuro e testo chiaro</p>
            <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem;">
                <span style="background: #3b82f6; padding: 0.25rem 0.75rem; border-radius: 4px; font-size: 0.875rem;">Primary</span>
                <span style="background: #334155; padding: 0.25rem 0.75rem; border-radius: 4px; font-size: 0.875rem;">Surface</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    elif theme == 'light':
        st.markdown("""
        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1rem; color: #1e293b;">
            <h4 style="margin: 0; color: #1e293b;">Dashboard</h4>
            <p style="color: #64748b; margin: 0.5rem 0;">Tema chiaro con sfondo bianco e testo scuro</p>
            <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem;">
                <span style="background: #3b82f6; color: white; padding: 0.25rem 0.75rem; border-radius: 4px; font-size: 0.875rem;">Primary</span>
                <span style="background: #f1f5f9; color: #1e293b; padding: 0.25rem 0.75rem; border-radius: 4px; font-size: 0.875rem;">Surface</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Il tema seguirà le impostazioni del sistema operativo")

    st.caption("ℹ️ Puoi cambiare il tema in qualsiasi momento dalle Impostazioni")

    # Navigation
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("⏭️ Salta configurazione", key="step1_skip"):
            wizard.deactivate()
            st.session_state.current_page = "Dashboard DB_ORG"
            st.rerun()

    with col2:
        if st.button("✕ Chiudi", key="step1_close"):
            wizard.deactivate()
            st.rerun()

    with col3:
        if st.button("Avanti →", key="step1_next", type="primary"):
            wizard.next_step()
            st.rerun()


def render_step_2_notifications(wizard):
    """Step 2: Notifications Configuration"""
    st.markdown("### 📬 Notifiche (2/3)")
    st.markdown("Configura le notifiche email per eventi importanti.")

    # Enable toggle
    notifications_enabled = st.toggle(
        "Abilita notifiche email",
        value=True,
        key="notifications_toggle",
        help="Ricevi email per eventi importanti come import completati, errori critici, modifiche bulk"
    )

    wizard.set_data('notifications_enabled', notifications_enabled)

    if notifications_enabled:
        # Frequency
        frequency = st.selectbox(
            "Frequenza riassunto",
            options=['daily', 'weekly', 'monthly'],
            format_func=lambda x: {
                'daily': '📅 Giornaliera',
                'weekly': '📆 Settimanale (Consigliato)',
                'monthly': '🗓️ Mensile'
            }[x],
            index=1,
            key="frequency_select"
        )

        wizard.set_data('notifications_frequency', frequency)

        # Email (optional)
        email = st.text_input(
            "Email (opzionale)",
            placeholder="tuo.nome@azienda.it",
            key="email_input",
            help="Lascia vuoto per usare l'email del tuo account"
        )

        wizard.set_data('notifications_email', email if email else None)

        st.info("""
        📧 **Riceverai notifiche per**:
        - Import DB_ORG completati o falliti
        - Errori critici di validazione
        - Modifiche bulk (es. >100 record modificati)
        - Snapshot automatici creati
        """)
    else:
        wizard.set_data('notifications_frequency', 'weekly')
        wizard.set_data('notifications_email', None)
        st.warning("⚠️ Notifiche disabilitate. Non riceverai email per eventi della piattaforma.")

    # Navigation
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("← Indietro", key="step2_back"):
            wizard.prev_step()
            st.rerun()

    with col2:
        if st.button("⏭️ Salta", key="step2_skip"):
            wizard.deactivate()
            st.session_state.current_page = "Dashboard DB_ORG"
            st.rerun()

    with col3:
        if st.button("Avanti →", key="step2_next", type="primary"):
            wizard.next_step()
            st.rerun()


def render_step_3_locale(wizard):
    """Step 3: Locale Settings"""
    st.markdown("### 🌍 Lingua & Fuso Orario (3/3)")
    st.markdown("Configura lingua e fuso orario per formattazione di date e orari.")

    # Language
    language = st.selectbox(
        "Lingua interfaccia",
        options=['IT', 'EN'],
        format_func=lambda x: {
            'IT': '🇮🇹 Italiano',
            'EN': '🇬🇧 English'
        }[x],
        index=0,
        key="language_select"
    )

    wizard.set_data('language', language)

    # Timezone
    timezone = st.selectbox(
        "Fuso orario",
        options=['Europe/Rome', 'UTC', 'America/New_York', 'Asia/Tokyo'],
        format_func=lambda x: {
            'Europe/Rome': '🇮🇹 Europe/Rome (GMT+1)',
            'UTC': '🌐 UTC (GMT+0)',
            'America/New_York': '🇺🇸 America/New_York (GMT-5)',
            'Asia/Tokyo': '🇯🇵 Asia/Tokyo (GMT+9)'
        }[x],
        index=0,
        key="timezone_select"
    )

    wizard.set_data('timezone', timezone)

    st.caption("ℹ️ Usato per formattare date e orari nei report e nelle dashboard")

    # Example preview
    st.markdown("#### Anteprima Formattazione")
    st.code(f"""
Timestamp: 2026-02-21 14:30:00 {timezone}
Formato data: 21/02/2026 (IT) | 02/21/2026 (EN)
Formato ora: 14:30 (24h)
    """, language="text")

    # Navigation
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("← Indietro", key="step3_back"):
            wizard.prev_step()
            st.rerun()

    with col2:
        if st.button("⏭️ Salta", key="step3_skip"):
            wizard.deactivate()
            st.session_state.current_page = "Dashboard DB_ORG"
            st.rerun()

    with col3:
        if st.button("✅ Completa Configurazione", key="step3_complete", type="primary"):
            complete_settings_wizard(wizard)
            st.rerun()


def complete_settings_wizard(wizard):
    """Complete settings wizard and save preferences"""
    settings_service = get_settings_service()

    # Get all wizard data
    theme = wizard.get_data('theme', 'dark')
    notifications_enabled = wizard.get_data('notifications_enabled', True)
    notifications_frequency = wizard.get_data('notifications_frequency', 'weekly')
    notifications_email = wizard.get_data('notifications_email')
    language = wizard.get_data('language', 'IT')
    timezone = wizard.get_data('timezone', 'Europe/Rome')

    # Save settings
    success = settings_service.save_settings({
        'theme': theme,
        'notifications': {
            'enabled': notifications_enabled,
            'frequency': notifications_frequency,
            'email': notifications_email
        },
        'locale': {
            'language': language,
            'timezone': timezone
        },
        'wizard_completed': True
    })

    if success:
        # Apply theme immediately
        settings_service.apply_theme(theme)

        # Mark as completed
        settings_service.mark_wizard_completed()

        # Deactivate wizard
        wizard.deactivate()

        # Navigate to dashboard
        st.session_state.current_page = "Dashboard DB_ORG"

        st.success("✅ Configurazione salvata con successo!")
        time.sleep(1)
    else:
        st.error("❌ Errore salvataggio configurazione")


# ═══════════════════════════════════════════════════════════
# MAIN MODAL RENDERER WITH @st.dialog
# ═══════════════════════════════════════════════════════════

@st.dialog("⚙️ Configurazione Iniziale", width="large")
def render_wizard_settings_dialog():
    """Main dialog renderer for settings wizard using Streamlit native dialog"""
    wizard = get_settings_wizard()

    # Progress indicator
    current = wizard.current_step
    total = wizard.total_steps

    # Progress bar using columns
    st.caption(f"Step {current}/{total}")
    progress_cols = st.columns(total)
    for i in range(total):
        with progress_cols[i]:
            step_num = i + 1
            if step_num < current:
                st.markdown("🟢", help="Completato")
            elif step_num == current:
                st.markdown("🔵", help="Corrente")
            else:
                st.markdown("⚪", help="Da completare")

    st.markdown("---")

    # Render current step
    if current == 1:
        render_step_1_theme(wizard)
    elif current == 2:
        render_step_2_notifications(wizard)
    elif current == 3:
        render_step_3_locale(wizard)


def render_wizard_settings_modal():
    """Main entry point for settings wizard modal"""
    wizard = get_settings_wizard()

    if wizard.is_active:
        render_wizard_settings_dialog()
