"""
Extended Dashboard View

Enhanced dashboard showing DB_ORG masterdata statistics.
"""
import streamlit as st
import pandas as pd
from datetime import date
import plotly.express as px
import plotly.graph_objects as go

from services.employee_service import get_employee_service
from services.hierarchy_service import get_hierarchy_service
from services.role_service import get_role_service
from services.lookup_service import get_lookup_service

def render_dashboard_extended():
    """Render extended dashboard with DB_ORG data"""

    # Get services
    emp_service = get_employee_service()
    hierarchy_service = get_hierarchy_service()
    role_service = get_role_service()
    lookup_service = get_lookup_service()

    # === KPI ROW ===

    col1, col2, col3, col4 = st.columns(4)

    try:
        # Get employee stats
        emp_stats = emp_service.get_employee_stats()

        with col1:
            st.metric(
                label="👥 Dipendenti Attivi",
                value=f"{emp_stats['total_active']:,}",
                delta=None
            )

        with col2:
            avg_ral = emp_stats.get('avg_ral', 0)
            st.metric(
                label="💰 RAL Media",
                value=f"€ {avg_ral:,.0f}",
                delta=None
            )

        with col3:
            # Count companies
            companies = lookup_service.get_companies()
            st.metric(
                label="🏢 Società",
                value=len(companies),
                delta=None
            )

        with col4:
            # Count roles
            roles = role_service.get_role_definitions()
            st.metric(
                label="🎭 Ruoli Definiti",
                value=len(roles),
                delta=None
            )

    except Exception as e:
        st.error(f"Errore caricamento KPI: {str(e)}")

    # === HIERARCHY STATS ===

    hierarchy_types = ['HR', 'TNS', 'SGSL', 'GDPR', 'IT_DIR']

    try:
        hierarchy_data = []

        for h_type in hierarchy_types:
            try:
                stats = hierarchy_service.get_hierarchy_stats(h_type)
                hierarchy_data.append({
                    'Gerarchia': stats.hierarchy_type_name,
                    'Dipendenti Assegnati': stats.total_employees_assigned,
                    'Senza Assegnazione': stats.employees_without_assignment,
                    'Copertura %': f"{stats.coverage_percentage:.1f}%"
                })
            except ValueError as e:
                # Silently skip hierarchy types that don't exist in DB yet
                # This is expected for newly initialized databases
                if "Invalid hierarchy type" not in str(e):
                    st.warning(f"Errore stats {h_type}: {str(e)}")
            except Exception as e:
                # Show other unexpected errors
                st.warning(f"Errore imprevisto per {h_type}: {str(e)}")

        if hierarchy_data:
            df_hierarchies = pd.DataFrame(hierarchy_data)
            st.dataframe(df_hierarchies, use_container_width=True)
        else:
            st.info("ℹ️ Nessuna gerarchia configurata. Le gerarchie verranno inizializzate al primo import di dati.")

    except Exception as e:
        st.error(f"Errore caricamento statistiche gerarchie: {str(e)}")

    # === DISTRIBUTION BY QUALIFICA ===

    try:
        emp_stats = emp_service.get_employee_stats()

        if emp_stats.get('by_qualifica'):
            df_qualifica = pd.DataFrame(emp_stats['by_qualifica'])

            fig = px.pie(
                df_qualifica,
                values='count',
                names='qualifica',
                title='Dipendenti per Qualifica'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nessun dato qualifica disponibile")

    except Exception as e:
        st.error(f"Errore grafico qualifiche: {str(e)}")

    # === DISTRIBUTION BY AREA (TOP 10) ===

    try:
        emp_stats = emp_service.get_employee_stats()

        if emp_stats.get('by_area'):
            df_area = pd.DataFrame(emp_stats['by_area'])

            fig = px.bar(
                df_area,
                x='count',
                y='area',
                orientation='h',
                title='Dipendenti per Area (Top 10)',
                labels={'count': 'Numero Dipendenti', 'area': 'Area'}
            )
            fig.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nessun dato area disponibile")

    except Exception as e:
        st.error(f"Errore grafico aree: {str(e)}")

    # === ROLE DISTRIBUTION ===

    try:
        roles = role_service.get_role_definitions()

        # Count by category
        category_counts = {}
        for role in roles:
            cat = role.role_category
            category_counts[cat] = category_counts.get(cat, 0) + 1

        if category_counts:
            df_roles = pd.DataFrame([
                {'Categoria': k, 'Numero Ruoli': v}
                for k, v in category_counts.items()
            ])

            fig = px.bar(
                df_roles,
                x='Categoria',
                y='Numero Ruoli',
                title='Ruoli Definiti per Categoria',
                color='Categoria'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nessun ruolo definito")

    except Exception as e:
        st.error(f"Errore grafico ruoli: {str(e)}")

    # === RECENT ACTIVITY ===

    try:
        # This would query audit_log for recent changes
        st.info("📝 Moduli audit log in development")
        st.markdown("""
        **Prossime funzionalità:**
        - Import DB_ORG completo (135 colonne)
        - Gestione gerarchie multiple (5 viste)
        - Organigrammi interattivi con d3-org-chart
        - Verifica consistenza payroll
        - Import e tracking retribuzioni mensili
        """)

    except Exception as e:
        st.error(f"Errore attività recenti: {str(e)}")

    # === QUICK ACTIONS ===

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("➕ Nuovo Dipendente", use_container_width=True):
            st.info("🔧 Vista 'Scheda Utente' in development")

    with col2:
        if st.button("🏢 Nuova Struttura", use_container_width=True):
            st.info("🔧 Vista 'Scheda Strutture' in development")

    with col3:
        if st.button("📥 Import DB_ORG", use_container_width=True):
            st.info("🔧 Vista 'Import DB_ORG' in development")

    # === SYSTEM INFO ===

    info_col1, info_col2 = st.columns(2)

    with info_col1:
        st.markdown("""
        **Database Schema:**
        - ✅ Companies (4 società)
        - ✅ Employees (schema normalizzato 135 colonne)
        - ✅ Org Units (strutture con gerarchia)
        - ✅ Hierarchy Types (5 tipi: HR, TNS, SGSL, GDPR, IT_DIR)
        - ✅ Role Definitions (24 ruoli: TNS, SGSL, GDPR)
        - ✅ Salary Records (tracking retribuzioni mensili)
        """)

    with info_col2:
        st.markdown("""
        **Services Attivi:**
        - ✅ EmployeeService (CRUD dipendenti)
        - ✅ HierarchyService (gestione 5 gerarchie)
        - ✅ RoleService (gestione ruoli)
        - ✅ LookupService (dropdown values)
        - ⏳ DBOrgImportService (in development)
        - ⏳ OrgChartDataService (in development)
        """)

    # === FOOTER ===
    st.caption("HR Management Platform - Il Sole 24 ORE | v2.0 DB_ORG Edition")

if __name__ == "__main__":
    render_dashboard_extended()
