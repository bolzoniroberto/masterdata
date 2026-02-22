"""
Structure Card View

User-friendly 4-tab form for viewing/editing organizational units.
"""
import streamlit as st
import pandas as pd
from typing import Optional, Dict, List
from datetime import datetime

from services.database import DatabaseHandler
from services.lookup_service import get_lookup_service
from services.hierarchy_service import get_hierarchy_service
from services.employee_service import get_employee_service

def render_structure_card_view():
    """Render Structure Card View with 4 tabs"""

    # Initialize services
    lookup_service = get_lookup_service()
    hierarchy_service = get_hierarchy_service()
    employee_service = get_employee_service()
    db = DatabaseHandler()

    # Session state for current structure
    if 'current_structure_id' not in st.session_state:
        st.session_state.current_structure_id = None
    if 'structure_mode' not in st.session_state:
        st.session_state.structure_mode = 'search'  # 'search' or 'edit' or 'create'

    # Mode selector
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("🔍 Cerca Struttura", use_container_width=True):
            st.session_state.structure_mode = 'search'
            st.session_state.current_structure_id = None
            st.rerun()

    with col2:
        if st.button("➕ Nuova Struttura", use_container_width=True):
            st.session_state.structure_mode = 'create'
            st.session_state.current_structure_id = None
            st.rerun()

    with col3:
        if st.session_state.current_structure_id:
            st.success(f"📝 Editing: {st.session_state.current_structure_id}")

    # SEARCH MODE
    if st.session_state.structure_mode == 'search':

        search_query = st.text_input(
            "Cerca per codice o descrizione",
            placeholder="es. REDA_MI o Redazione Milano",
            key="structure_search"
        )

        if search_query:
            # Search org units
            results = lookup_service.search_org_units(search_query, limit=10)

            if results:
                st.success(f"✅ Trovate {len(results)} strutture")

                # Display results as clickable cards
                for org_unit in results:
                    with st.container():
                        col1, col2, col3, col4 = st.columns([2, 2, 1, 1])

                        with col1:
                            st.markdown(f"**{org_unit['descrizione']}**")
                        with col2:
                            st.text(f"Codice: {org_unit['codice']}")
                        with col3:
                            # Count employees
                            employees = db.execute_query(
                                "SELECT COUNT(*) as cnt FROM employees WHERE area = ? OR sottoarea = ?",
                                (org_unit['descrizione'], org_unit['descrizione'])
                            )
                            emp_count = employees[0]['cnt'] if employees else 0
                            st.text(f"👥 {emp_count}")
                        with col4:
                            if st.button("✏️ Modifica", key=f"edit_{org_unit['org_unit_id']}"):
                                st.session_state.current_structure_id = org_unit['org_unit_id']
                                st.session_state.structure_mode = 'edit'
                                st.rerun()

            else:
                st.warning("⚠️ Nessuna struttura trovata")
        else:
            st.info("👆 Inserisci codice o descrizione per cercare una struttura")

    # CREATE/EDIT MODE
    elif st.session_state.structure_mode in ['create', 'edit']:

        # Load existing structure if editing
        structure_data = None
        if st.session_state.structure_mode == 'edit' and st.session_state.current_structure_id:
            structures = db.execute_query(
                "SELECT * FROM org_units WHERE org_unit_id = ?",
                (st.session_state.current_structure_id,)
            )
            if structures:
                structure_data = structures[0]
            else:
                st.error("❌ Struttura non trovata")
                st.session_state.structure_mode = 'search'
                st.rerun()

        # 4-TAB FORM
        tab1, tab2, tab3, tab4 = st.tabs([
            "🏛️ Dati Struttura",
            "📊 Gerarchia",
            "👔 Responsabili e Approvatori",
            "👥 Dipendenti"
        ])

        # ========== TAB 1: DATI STRUTTURA ==========
        with tab1:
            st.markdown("### 🏛️ Informazioni Base")

            col1, col2 = st.columns(2)

            with col1:
                codice = st.text_input(
                    "Codice Struttura *",
                    value=structure_data['codice'] if structure_data else "",
                    placeholder="es. REDA_MI_ECO",
                    disabled=(st.session_state.structure_mode == 'edit'),
                    help="Codice univoco struttura (non modificabile)"
                )

            with col2:
                livello = st.selectbox(
                    "Livello Gerarchico *",
                    options=["Livello 1", "Livello 2", "Livello 3"],
                    index=["Livello 1", "Livello 2", "Livello 3"].index(structure_data['livello'])
                        if structure_data and structure_data.get('livello') else 1
                )

            descrizione = st.text_input(
                "Descrizione *",
                value=structure_data['descrizione'] if structure_data else "",
                placeholder="es. Redazione Milano Economia"
            )

            st.markdown("### 🏢 Organizzazione")

            col1, col2 = st.columns(2)

            with col1:
                # Company dropdown
                companies = lookup_service.get_companies()
                company_idx = 0
                if structure_data and structure_data.get('company_id'):
                    company_rows = db.execute_query(
                        "SELECT company_name FROM companies WHERE company_id = ?",
                        (structure_data['company_id'],)
                    )
                    if company_rows:
                        try:
                            company_idx = companies.index(company_rows[0]['company_name'])
                        except ValueError:
                            company_idx = 0

                company = st.selectbox(
                    "Società *",
                    options=companies,
                    index=company_idx
                )

            with col2:
                # Area autocomplete
                areas = lookup_service.get_areas()
                area = st.selectbox(
                    "Area (Livello 1)",
                    options=[""] + areas,
                    index=0
                )

            sottoarea = st.text_input(
                "SottoArea (Livello 2)",
                value=structure_data.get('sottoarea', '') if structure_data else "",
                placeholder="es. Economia e Finanza"
            )

            st.markdown("### 💰 Contabilità")

            col1, col2 = st.columns(2)

            with col1:
                cdccosto = st.text_input(
                    "Centro di Costo (CdC)",
                    value=structure_data.get('cdccosto', '') if structure_data else "",
                    placeholder="es. 16100"
                )

            with col2:
                cdc_amm = st.text_input(
                    "CdC Amministrativo",
                    value=structure_data.get('cdc_amm', '') if structure_data else "",
                    placeholder="es. 16100"
                )

        # ========== TAB 2: GERARCHIA ==========
        with tab2:
            st.markdown("### 📊 Struttura Gerarchica")

            # Parent org unit search
            parent_search = st.text_input(
                "Cerca unità organizzativa padre",
                placeholder="Cerca per codice o descrizione",
                key="parent_search"
            )

            selected_parent_id = None
            if structure_data and structure_data.get('parent_org_unit_id'):
                selected_parent_id = structure_data['parent_org_unit_id']

            if parent_search:
                parent_results = lookup_service.search_org_units(parent_search, limit=5)
                if parent_results:
                    for parent in parent_results:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.text(f"{parent['descrizione']} (Codice: {parent['codice']})")
                        with col2:
                            if st.button("Seleziona", key=f"select_parent_{parent['org_unit_id']}"):
                                selected_parent_id = parent['org_unit_id']
                                st.success("✅ Selezionato")

            if selected_parent_id:
                parents = db.execute_query(
                    "SELECT * FROM org_units WHERE org_unit_id = ?",
                    (selected_parent_id,)
                )
                if parents:
                    st.success(f"✅ Padre: {parents[0]['descrizione']} (Codice: {parents[0]['codice']})")
            else:
                st.info("ℹ️ Nessuna unità padre selezionata (sarà root)")

            # Children org units (if editing existing)
            if st.session_state.structure_mode == 'edit' and structure_data:

                children = db.execute_query(
                    "SELECT * FROM org_units WHERE parent_org_unit_id = ? AND active = 1",
                    (structure_data['org_unit_id'],)
                )

                if children:
                    st.success(f"✅ {len(children)} unità figlie")
                    for child in children:
                        # Count employees in child
                        emp_count = db.execute_query(
                            "SELECT COUNT(*) as cnt FROM employees WHERE area = ? OR sottoarea = ?",
                            (child['descrizione'], child['descrizione'])
                        )
                        count = emp_count[0]['cnt'] if emp_count else 0

                        st.markdown(f"├─ **{child['descrizione']}** ({count} dip.)")
                else:
                    st.info("ℹ️ Nessuna unità figlia")

                # Hierarchy path

                # Build path by walking up the tree
                path_parts = [structure_data['descrizione']]
                current_parent_id = structure_data.get('parent_org_unit_id')

                while current_parent_id:
                    parent_rows = db.execute_query(
                        "SELECT descrizione, parent_org_unit_id FROM org_units WHERE org_unit_id = ?",
                        (current_parent_id,)
                    )
                    if parent_rows:
                        path_parts.insert(0, parent_rows[0]['descrizione'])
                        current_parent_id = parent_rows[0]['parent_org_unit_id']
                    else:
                        break

                st.markdown(" **>** ".join(path_parts))

        # ========== TAB 3: RESPONSABILI E APPROVATORI ==========
        with tab3:
            st.markdown("### 👔 Persone Chiave")

            # Responsible search
            resp_search = st.text_input(
                "Cerca dipendente responsabile",
                placeholder="Cerca per nome o codice fiscale",
                key="resp_search"
            )

            selected_resp_id = None
            if structure_data and structure_data.get('responsible_employee_id'):
                selected_resp_id = structure_data['responsible_employee_id']

            if resp_search:
                resp_results = lookup_service.search_employees(resp_search, limit=5)
                if resp_results:
                    for emp in resp_results:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.text(f"{emp['titolare']} (CF: {emp['tx_cod_fiscale'][:8]}...)")
                        with col2:
                            if st.button("Seleziona", key=f"select_resp_{emp['employee_id']}"):
                                selected_resp_id = emp['employee_id']
                                st.success("✅ Selezionato")

            if selected_resp_id:
                resp = db.execute_query(
                    "SELECT * FROM employees WHERE employee_id = ?",
                    (selected_resp_id,)
                )
                if resp:
                    st.success(f"✅ Responsabile: {resp[0]['titolare']}")
                    st.text(f"CF: {resp[0]['tx_cod_fiscale']}")
                    st.text(f"Email: {resp[0].get('email', 'N/A')}")
            else:
                st.info("ℹ️ Nessun responsabile assegnato")

            # TNS Approvers/Controllers (if editing existing)
            if st.session_state.structure_mode == 'edit' and structure_data:

                # Get approvers for this org unit
                # Query employees with APPROVATORE role assigned to this structure
                approvers = db.execute_query("""
                    SELECT e.employee_id, e.titolare, e.tx_cod_fiscale
                    FROM employees e
                    JOIN role_assignments ra ON ra.employee_id = e.employee_id
                    JOIN role_definitions rd ON rd.role_id = ra.role_id
                    WHERE rd.role_code = 'TNS_APPROVATORE'
                    AND (ra.org_unit_id = ? OR ra.org_unit_id IS NULL)
                    AND (ra.end_date IS NULL OR ra.end_date > date('now'))
                    AND e.active = 1
                """, (structure_data['org_unit_id'],))

                if approvers:
                    for app in approvers:
                        st.markdown(f"├─ ✅ **{app['titolare']}** (CF: {app['tx_cod_fiscale'][:8]}...)")
                else:
                    st.warning("⚠️ **Alert**: Struttura DEVE avere almeno 1 approvatore!")

                # Get controllers
                controllers = db.execute_query("""
                    SELECT e.employee_id, e.titolare, e.tx_cod_fiscale
                    FROM employees e
                    JOIN role_assignments ra ON ra.employee_id = e.employee_id
                    JOIN role_definitions rd ON rd.role_id = ra.role_id
                    WHERE rd.role_code = 'TNS_CONTROLLORE'
                    AND (ra.org_unit_id = ? OR ra.org_unit_id IS NULL)
                    AND (ra.end_date IS NULL OR ra.end_date > date('now'))
                    AND e.active = 1
                """, (structure_data['org_unit_id'],))

                if controllers:
                    for ctrl in controllers:
                        st.markdown(f"└─ 🔍 **{ctrl['titolare']}** (CF: {ctrl['tx_cod_fiscale'][:8]}...)")
                else:
                    st.info("ℹ️ Nessun controllore assegnato")

        # ========== TAB 4: DIPENDENTI ==========
        with tab4:
            st.markdown("### 👥 Dipendenti Assegnati")

            if st.session_state.structure_mode == 'edit' and structure_data:
                # Get employees assigned to this structure
                employees = db.execute_query("""
                    SELECT employee_id, titolare, tx_cod_fiscale, qualifica, area, sottoarea
                    FROM employees
                    WHERE (area = ? OR sottoarea = ?)
                    AND active = 1
                    ORDER BY titolare
                """, (structure_data['descrizione'], structure_data['descrizione']))

                if employees:
                    st.success(f"✅ {len(employees)} dipendenti assegnati")

                    # Search within employees
                    search_emp = st.text_input(
                        "🔍 Cerca dipendente",
                        placeholder="Filtra per nome...",
                        key="search_structure_emp"
                    )

                    # Filter if search
                    if search_emp:
                        employees = [e for e in employees if search_emp.lower() in e['titolare'].lower()]

                    # Display as table
                    df = pd.DataFrame(employees)
                    df = df[['titolare', 'qualifica', 'area', 'sottoarea']]
                    df.columns = ['Nome', 'Qualifica', 'Area', 'SottoArea']

                    st.dataframe(df, use_container_width=True, height=400)

                    # Export button
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        if st.button("📤 Export Excel", use_container_width=True):
                            # Create Excel file
                            output_file = f"dipendenti_{structure_data['codice']}.xlsx"
                            df.to_excel(output_file, index=False)
                            st.success(f"✅ File esportato: {output_file}")

                    with col2:
                        if st.button("➕ Aggiungi Dipendente", use_container_width=True):
                            st.info("ℹ️ Usa la Scheda Utente per creare/modificare dipendenti")
                else:
                    st.info("ℹ️ Nessun dipendente assegnato a questa struttura")
            else:
                st.info("ℹ️ Salva la struttura per visualizzare i dipendenti assegnati")

        # ========== FOOTER: SAVE/CANCEL BUTTONS ==========

        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

        with col1:
            if st.button("💾 Salva Modifiche", type="primary", use_container_width=True):
                # Validation
                errors = []
                if not codice:
                    errors.append("Codice struttura obbligatorio")
                if not descrizione:
                    errors.append("Descrizione obbligatoria")
                if not company:
                    errors.append("Società obbligatoria")

                if errors:
                    for err in errors:
                        st.error(f"❌ {err}")
                else:
                    try:
                        # Get company_id
                        company_rows = db.execute_query(
                            "SELECT company_id FROM companies WHERE company_name = ?",
                            (company,)
                        )
                        company_id = company_rows[0]['company_id'] if company_rows else None

                        if st.session_state.structure_mode == 'create':
                            # Insert new structure
                            db.execute_update("""
                                INSERT INTO org_units (
                                    codice, descrizione, company_id, parent_org_unit_id,
                                    cdccosto, livello, active, responsible_employee_id
                                )
                                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                            """, (codice, descrizione, company_id, selected_parent_id,
                                  cdccosto, livello, selected_resp_id))

                            # Audit log
                            db.execute_update("""
                                INSERT INTO audit_log (table_name, record_id, action, changed_by, changes)
                                VALUES ('org_units', ?, 'INSERT', 'user', ?)
                            """, (codice, f"Created new org unit: {descrizione}"))

                            st.success(f"✅ Struttura creata: {descrizione}")

                        else:  # edit mode
                            # Update existing structure
                            db.execute_update("""
                                UPDATE org_units
                                SET descrizione = ?,
                                    company_id = ?,
                                    parent_org_unit_id = ?,
                                    cdccosto = ?,
                                    livello = ?,
                                    responsible_employee_id = ?,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE org_unit_id = ?
                            """, (descrizione, company_id, selected_parent_id, cdccosto,
                                  livello, selected_resp_id, structure_data['org_unit_id']))

                            # Audit log
                            db.execute_update("""
                                INSERT INTO audit_log (table_name, record_id, action, changed_by, changes)
                                VALUES ('org_units', ?, 'UPDATE', 'user', ?)
                            """, (structure_data['org_unit_id'],
                                  f"Updated org unit: {descrizione}"))

                            st.success(f"✅ Struttura aggiornata: {descrizione}")

                        # Return to search mode
                        st.session_state.structure_mode = 'search'
                        st.session_state.current_structure_id = None
                        st.rerun()

                    except Exception as e:
                        st.error(f"❌ Errore durante salvataggio: {str(e)}")

        with col2:
            if st.button("❌ Annulla", use_container_width=True):
                st.session_state.structure_mode = 'search'
                st.session_state.current_structure_id = None
                st.rerun()

        with col3:
            if st.session_state.structure_mode == 'edit' and structure_data:
                if st.button("🗑️ Elimina Struttura", use_container_width=True):
                    # Soft delete
                    db.execute_update("""
                        UPDATE org_units
                        SET active = 0,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE org_unit_id = ?
                    """, (structure_data['org_unit_id'],))

                    # Audit log
                    db.execute_update("""
                        INSERT INTO audit_log (table_name, record_id, action, changed_by, changes)
                        VALUES ('org_units', ?, 'DELETE', 'user', ?)
                    """, (structure_data['org_unit_id'],
                          f"Deleted org unit: {structure_data['descrizione']}"))

                    st.success("✅ Struttura eliminata")
                    st.session_state.structure_mode = 'search'
                    st.session_state.current_structure_id = None
                    st.rerun()

        with col4:
            if st.session_state.structure_mode == 'edit' and structure_data:
                if st.button("📊 Visualizza Organigramma", use_container_width=True):
                    st.info("ℹ️ Funzionalità organigramma in arrivo!")

if __name__ == "__main__":
    render_structure_card_view()
