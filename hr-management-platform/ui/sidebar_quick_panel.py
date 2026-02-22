"""
Sidebar Quick Panel - Quick actions and contextual tools.

Sections:
- Quick Stats Header
- Quick Actions (collapsible)
- Global Filters (collapsible)
- Recent Activity (collapsible)
- Database Info (collapsible footer)
"""

import streamlit as st
from datetime import datetime
from typing import List, Dict, Any


def render_quick_stats():
    """Compact metrics header"""

    if not st.session_state.data_loaded:
        return

    try:
        db = st.session_state.database_handler

        # Get counts
        cursor = db.conn.cursor()

        # Count employees (rows with CF)
        cursor.execute("SELECT COUNT(*) FROM personale WHERE TxCodFiscale IS NOT NULL AND TxCodFiscale != ''")
        employee_count = cursor.fetchone()[0]

        # Count structures (rows without CF or from strutture table)
        cursor.execute("SELECT COUNT(*) FROM strutture")
        structure_count = cursor.fetchone()[0]

        # Get latest version
        cursor.execute("""
            SELECT version_number, created_at
            FROM import_versions
            WHERE completed = 1
            ORDER BY version_number DESC
            LIMIT 1
        """)
        version_row = cursor.fetchone()

        cursor.close()

        # Display header
        st.markdown("### 📊 Panoramica Rapida")

        # Metrics in columns
        col1, col2 = st.columns(2)

        with col1:
            st.metric("👥 Dipendenti", f"{employee_count:,}")

        with col2:
            st.metric("🏢 Strutture", f"{structure_count:,}")

        # Version and sync status
        if version_row:
            version_num, created_at = version_row
            # Parse datetime
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at)
                    date_str = dt.strftime("%d/%m")
                except:
                    date_str = created_at[:10]
            else:
                date_str = "N/A"

            st.caption(f"📦 Versione {version_num:.1f} ({date_str}) • ✅ Sincronizzato")
        else:
            st.caption("📦 Nessuna versione • ⚠️ Importa dati")

    except Exception as e:
        st.caption(f"⚠️ Statistiche non disponibili")


def render_quick_actions():
    """Common actions shortcuts"""

    if not st.session_state.data_loaded:
        return

    with st.expander("⚡ Azioni Rapide", expanded=True):

        # Import action
        if st.button("📥 Nuovo Import", use_container_width=True,
                    help="Importa nuovi dati da file Excel"):
            from ui.wizard_state_manager import get_import_wizard
            get_import_wizard().activate()
            st.rerun()

        # Export action
        if st.button("📤 Esporta TNS", use_container_width=True,
                    help="Genera ed esporta file DB_TNS"):
            st.session_state.current_page = "💾 Salvataggio & Export"
            st.rerun()

        # Snapshot action
        if st.button("📸 Snapshot", use_container_width=True,
                    help="Crea snapshot manuale dello stato attuale"):
            st.session_state.show_manual_snapshot_dialog = True
            st.rerun()

        # Global search
        if st.button("🔍 Ricerca Globale", use_container_width=True,
                    help="Cerca dipendenti e strutture"):
            st.session_state.current_page = "Ricerca Intelligente"
            st.rerun()

        # Dashboard
        if st.button("📊 Dashboard", use_container_width=True,
                    help="Vai alla dashboard principale"):
            st.session_state.current_page = "Dashboard Home"
            st.rerun()


def render_global_filters():
    """Global filters that apply across all pages"""

    if not st.session_state.data_loaded:
        return

    with st.expander("🔍 Filtri Globali", expanded=False):

        st.caption("Filtri applicati a tutte le viste")

        try:
            db = st.session_state.database_handler
            cursor = db.conn.cursor()

            # Get unique UO
            cursor.execute("""
                SELECT DISTINCT "UNITA' OPERATIVA PADRE"
                FROM personale
                WHERE "UNITA' OPERATIVA PADRE" IS NOT NULL
                AND "UNITA' OPERATIVA PADRE" != ''
                ORDER BY "UNITA' OPERATIVA PADRE"
            """)
            uo_list = [row[0] for row in cursor.fetchall()]

            # Get unique roles (from Ruolo column)
            cursor.execute("""
                SELECT DISTINCT Ruolo
                FROM personale
                WHERE Ruolo IS NOT NULL
                AND Ruolo != ''
                ORDER BY Ruolo
            """)
            role_list = [row[0] for row in cursor.fetchall()]

            cursor.close()

            # UO filter
            uo_options = ["Tutte le UO"] + uo_list
            selected_uo = st.selectbox(
                "Unità Organizzativa",
                uo_options,
                key="global_filter_uo"
            )

            # Role filter
            role_options = ["Tutti i ruoli"] + role_list
            selected_role = st.selectbox(
                "Ruolo",
                role_options,
                key="global_filter_role"
            )

            # Active only checkbox
            active_only = st.checkbox(
                "Solo attivi",
                value=True,
                key="global_filter_active"
            )

            st.markdown("---")

            # Action buttons
            col1, col2 = st.columns(2)

            with col1:
                if st.button("🔄 Applica", use_container_width=True, type="primary"):
                    # Store filters in session state
                    st.session_state.global_filters = {
                        'uo': None if selected_uo == "Tutte le UO" else selected_uo,
                        'role': None if selected_role == "Tutti i ruoli" else selected_role,
                        'active_only': active_only
                    }
                    st.success("Filtri applicati!")
                    st.rerun()

            with col2:
                if st.button("✕ Reset", use_container_width=True):
                    # Clear filters
                    if 'global_filters' in st.session_state:
                        del st.session_state.global_filters
                    st.info("Filtri rimossi")
                    st.rerun()

            # Show current filter status
            if 'global_filters' in st.session_state:
                filters = st.session_state.global_filters
                active_filters = []
                if filters.get('uo'):
                    active_filters.append(f"UO: {filters['uo']}")
                if filters.get('role'):
                    active_filters.append(f"Ruolo: {filters['role']}")
                if filters.get('active_only'):
                    active_filters.append("Solo attivi")

                if active_filters:
                    st.caption("**Filtri attivi:** " + ", ".join(active_filters))

        except Exception as e:
            st.caption(f"⚠️ Filtri non disponibili")


def render_recent_activity():
    """Recent activity timeline from audit log"""

    if not st.session_state.data_loaded:
        return

    with st.expander("📜 Attività Recente", expanded=False):

        try:
            db = st.session_state.database_handler
            cursor = db.conn.cursor()

            # Get recent activities from audit log
            cursor.execute("""
                SELECT timestamp, table_name, operation, changes, user_id
                FROM audit_log
                ORDER BY timestamp DESC
                LIMIT 5
            """)

            activities = cursor.fetchall()
            cursor.close()

            if not activities:
                st.caption("Nessuna attività registrata")
                return

            # Display activities
            for timestamp, table_name, operation, changes, user_id in activities:
                # Parse timestamp
                try:
                    dt = datetime.fromisoformat(timestamp)
                    time_str = dt.strftime("%H:%M")
                    date_str = dt.strftime("%d/%m")

                    # Today or yesterday?
                    today = datetime.now().date()
                    activity_date = dt.date()

                    if activity_date == today:
                        display_time = f"Oggi {time_str}"
                    elif (today - activity_date).days == 1:
                        display_time = f"Ieri {time_str}"
                    else:
                        display_time = f"{date_str} {time_str}"

                except:
                    display_time = timestamp[:16]

                # Icon based on operation
                if operation == 'INSERT':
                    icon = "➕"
                    op_label = "Aggiunto"
                elif operation == 'UPDATE':
                    icon = "✏️"
                    op_label = "Modificato"
                elif operation == 'DELETE':
                    icon = "🗑️"
                    op_label = "Eliminato"
                elif operation == 'IMPORT':
                    icon = "📥"
                    op_label = "Import"
                else:
                    icon = "•"
                    op_label = operation

                # Table label
                if table_name == 'personale':
                    table_label = "Dipendente"
                elif table_name == 'strutture':
                    table_label = "Struttura"
                else:
                    table_label = table_name

                st.markdown(f"""
                **{icon} {display_time}**
                {op_label} {table_label}
                """)

            st.markdown("---")

            # View all button
            if st.button("Vedi tutto →", use_container_width=True):
                st.session_state.current_page = "Log Modifiche"
                st.rerun()

        except Exception as e:
            st.caption(f"⚠️ Attività non disponibili")


def render_database_info():
    """Database status and management actions"""

    if not st.session_state.data_loaded:
        return

    with st.expander("💾 Database Info", expanded=False):

        try:
            db = st.session_state.database_handler
            cursor = db.conn.cursor()

            # Get last modified timestamp
            cursor.execute("SELECT MAX(timestamp) FROM audit_log")
            last_mod_row = cursor.fetchone()
            last_mod = last_mod_row[0] if last_mod_row else None

            # Count versions and milestones
            cursor.execute("SELECT COUNT(*) FROM import_versions WHERE completed = 1")
            version_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM import_versions WHERE completed = 1 AND certified = 1")
            milestone_count = cursor.fetchone()[0]

            cursor.close()

            # Display info
            if last_mod:
                try:
                    dt = datetime.fromisoformat(last_mod)
                    today = datetime.now().date()
                    mod_date = dt.date()

                    if mod_date == today:
                        date_display = f"Oggi {dt.strftime('%H:%M')}"
                    elif (today - mod_date).days == 1:
                        date_display = f"Ieri {dt.strftime('%H:%M')}"
                    else:
                        date_display = dt.strftime("%d/%m/%Y %H:%M")

                    st.caption(f"**Ultima modifica:** {date_display}")
                except:
                    st.caption(f"**Ultima modifica:** {last_mod[:19]}")
            else:
                st.caption("**Ultima modifica:** Nessuna")

            st.caption(f"**Versioni:** {version_count} completate")
            if milestone_count > 0:
                st.caption(f"**Milestone:** {milestone_count} certificate")

            st.markdown("---")

            # Management actions
            if st.button("📸 Snapshot Manuale", use_container_width=True,
                        help="Crea un punto di ripristino manuale"):
                st.session_state.show_manual_snapshot_dialog = True
                st.rerun()

            if st.button("🗑️ Svuota Database", use_container_width=True,
                        help="Elimina tutti i dati (azione irreversibile)"):
                st.session_state.show_clear_db_confirm = True
                st.rerun()

        except Exception as e:
            st.caption(f"⚠️ Info database non disponibili")


def render_sidebar_minimal():
    """Minimal sidebar for empty database state"""

    st.markdown("### 🏠 Menu")

    st.info("Completa la configurazione iniziale per accedere a tutte le funzionalità")

    st.markdown("---")

    if st.button("🚀 Avvia Setup", use_container_width=True, type="primary",
                help="Avvia la configurazione guidata"):
        from ui.wizard_onboarding_modal import get_onboarding_wizard
        get_onboarding_wizard().activate()
        st.rerun()

    st.markdown("---")

    # Alternative: direct import
    st.caption("Utenti esperti:")

    if st.button("📂 Import Diretto", use_container_width=True,
                help="Salta la guida e importa direttamente"):
        from ui.wizard_state_manager import get_import_wizard
        get_import_wizard().activate()
        st.rerun()


def render_sidebar_full():
    """Full sidebar quick panel for loaded database"""

    render_quick_stats()
    st.markdown("---")

    render_quick_actions()
    st.markdown("---")

    render_global_filters()
    st.markdown("---")

    render_recent_activity()
    st.markdown("---")

    render_database_info()


def render_sidebar():
    """Main sidebar rendering function"""

    # Header
    st.header("Menu")

    # Render appropriate sidebar based on state
    if st.session_state.data_loaded:
        render_sidebar_full()
    else:
        render_sidebar_minimal()

    # Footer
    st.markdown("---")
    st.caption(f"**v2.1** | UX Redesign with Ribbon")
