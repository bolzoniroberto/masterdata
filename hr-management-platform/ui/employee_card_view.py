"""
Employee Card View

User-friendly form for viewing/editing employee data.
Organized in 5 tabs by domain with dropdown menus and validation.
"""
import streamlit as st
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from services.employee_service import get_employee_service
from services.lookup_service import get_lookup_service
from services.hierarchy_service import get_hierarchy_service
from services.role_service import get_role_service
from models.employee import EmployeeCreate, EmployeeUpdate

def render_employee_card_view():
    """Render employee card interface"""

    # Get services
    emp_service = get_employee_service()
    lookup_service = get_lookup_service()
    hierarchy_service = get_hierarchy_service()
    role_service = get_role_service()

    # MODE: Create or Edit
    mode = st.radio(
        "Modalità",
        ["🔍 Cerca Dipendente", "➕ Nuovo Dipendente"],
        horizontal=True
    )

    if mode == "🔍 Cerca Dipendente":
        # Search mode
        st.markdown("### 🔍 Cerca Dipendente")

        search_query = st.text_input(
            "Cerca per nome, cognome o codice fiscale",
            placeholder="es. Mario Rossi o RSSMRA80A01H501U"
        )

        if search_query and len(search_query) >= 3:
            results = emp_service.search_employees(search_query, limit=20)

            if results:
                st.markdown(f"**Trovati {len(results)} risultati:**")

                # Show results as cards
                for emp in results:
                    with st.container():
                        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

                        with col1:
                            st.markdown(f"**{emp.titolare}**")
                            st.caption(f"CF: {emp.tx_cod_fiscale}")

                        with col2:
                            st.caption(f"📍 {emp.area or 'N/A'}")

                        with col3:
                            st.caption(f"💼 {emp.qualifica or 'N/A'}")

                        with col4:
                            if st.button("Apri", key=f"open_{emp.employee_id}"):
                                st.session_state.selected_employee_id = emp.employee_id
                                st.rerun()

            else:
                st.info("Nessun dipendente trovato")

        # If employee selected, show card
        if st.session_state.get('selected_employee_id'):
            employee_id = st.session_state.selected_employee_id
            render_employee_form(employee_id, emp_service, lookup_service, hierarchy_service, role_service)

    else:
        # Create new employee mode
        render_employee_form(None, emp_service, lookup_service, hierarchy_service, role_service)

def render_employee_form(
    employee_id: Optional[int],
    emp_service,
    lookup_service,
    hierarchy_service,
    role_service
):
    """Render employee form (create or edit)"""

    is_edit = employee_id is not None

    # Load employee data if editing
    employee = None
    if is_edit:
        employee = emp_service.get_employee(employee_id)
        if not employee:
            st.error(f"Dipendente {employee_id} non trovato")
            return

    # Header with photo
    col1, col2 = st.columns([1, 5])

    with col1:
        # Photo placeholder
        st.image("https://via.placeholder.com/150?text=Photo", width=150)

    with col2:
        if is_edit:
            st.markdown(f"# {employee.titolare}")
            st.markdown(f"**CF**: {employee.tx_cod_fiscale}")

            # Status badge
            if employee.active:
                st.success("✅ Attivo")
            else:
                st.error("❌ Cessato")
        else:
            st.markdown("# Nuovo Dipendente")

    # 5 TABS
    tabs = st.tabs([
        "📋 Dati Anagrafici",
        "💼 Dati Lavorativi",
        "🏢 Struttura Organizzativa",
        "🎭 Ruoli TNS",
        "🔒 Conformità"
    ])

    # Store form data
    form_data = {}

    # TAB 1: DATI ANAGRAFICI
    with tabs[0]:
        st.markdown("### 👤 Dati Personali")

        col1, col2 = st.columns(2)

        with col1:
            form_data['tx_cod_fiscale'] = st.text_input(
                "Codice Fiscale *",
                value=employee.tx_cod_fiscale if is_edit else "",
                max_chars=16,
                disabled=is_edit,
                help="16 caratteri - Non modificabile dopo creazione"
            ).upper()

            form_data['cognome'] = st.text_input(
                "Cognome",
                value=employee.cognome if is_edit else ""
            )

            form_data['nome'] = st.text_input(
                "Nome",
                value=employee.nome if is_edit else ""
            )

            form_data['sesso'] = st.radio(
                "Sesso",
                options=["M", "F"],
                index=0 if not is_edit or employee.sesso == "M" else 1,
                horizontal=True
            )

        with col2:
            form_data['data_nascita'] = st.date_input(
                "Data Nascita",
                value=employee.data_nascita if is_edit and employee.data_nascita else None,
                min_value=date(1940, 1, 1),
                max_value=date.today()
            )

            form_data['email'] = st.text_input(
                "Email",
                value=employee.email if is_edit else "",
                placeholder="nome.cognome@ilsole24ore.com"
            )

        st.markdown("### 🏠 Indirizzo")

        col1, col2, col3 = st.columns([3, 1, 2])

        with col1:
            form_data['indirizzo_via'] = st.text_input(
                "Via",
                value=employee.indirizzo_via if is_edit else "",
                placeholder="Via Roma, 1"
            )

        with col2:
            form_data['indirizzo_cap'] = st.text_input(
                "CAP",
                value=employee.indirizzo_cap if is_edit else "",
                max_chars=5,
                placeholder="20100"
            )

        with col3:
            form_data['indirizzo_citta'] = st.text_input(
                "Città",
                value=employee.indirizzo_citta if is_edit else "",
                placeholder="Milano"
            )

    # TAB 2: DATI LAVORATIVI
    with tabs[1]:
        st.markdown("### 💼 Informazioni Contratto")

        col1, col2 = st.columns(2)

        with col1:
            # Company dropdown
            companies = lookup_service.get_companies()
            company_names = [c['company_name'] for c in companies]

            default_company_idx = 0
            if is_edit and employee.company_id:
                for idx, c in enumerate(companies):
                    if c['company_id'] == employee.company_id:
                        default_company_idx = idx
                        break

            selected_company = st.selectbox(
                "Società *",
                options=company_names,
                index=default_company_idx
            )

            form_data['company_id'] = companies[company_names.index(selected_company)]['company_id']

            # Contract dropdown
            contracts = lookup_service.get_contract_types()
            if contracts:
                default_contract = employee.contratto if is_edit and employee.contratto in contracts else None

                form_data['contratto'] = st.selectbox(
                    "Contratto",
                    options=[""] + contracts,
                    index=contracts.index(default_contract) + 1 if default_contract else 0
                )
            else:
                form_data['contratto'] = st.text_input(
                    "Contratto",
                    value=employee.contratto if is_edit else ""
                )

            # Qualifica dropdown
            qualifiche = lookup_service.get_qualifications()
            default_qualifica = employee.qualifica if is_edit and employee.qualifica in qualifiche else None

            form_data['qualifica'] = st.selectbox(
                "Qualifica",
                options=[""] + qualifiche,
                index=qualifiche.index(default_qualifica) + 1 if default_qualifica else 0
            )

            form_data['livello'] = st.text_input(
                "Livello",
                value=employee.livello if is_edit else "",
                max_chars=10
            )

        with col2:
            form_data['codice'] = st.text_input(
                "Codice Dipendente *",
                value=employee.codice if is_edit else "",
                disabled=is_edit,
                help="Non modificabile dopo creazione"
            )

            form_data['matricola'] = st.text_input(
                "Matricola",
                value=employee.matricola if is_edit else ""
            )

            # Sede dropdown
            sedi = lookup_service.get_offices()
            if sedi:
                default_sede = employee.sede if is_edit and employee.sede in sedi else None

                form_data['sede'] = st.selectbox(
                    "Sede",
                    options=[""] + sedi,
                    index=sedi.index(default_sede) + 1 if default_sede else 0
                )
            else:
                form_data['sede'] = st.text_input(
                    "Sede",
                    value=employee.sede if is_edit else ""
                )

        st.markdown("### 📅 Date")

        col1, col2 = st.columns(2)

        with col1:
            form_data['data_assunzione'] = st.date_input(
                "Data Assunzione",
                value=employee.data_assunzione if is_edit and employee.data_assunzione else None
            )

        with col2:
            form_data['data_cessazione'] = st.date_input(
                "Data Cessazione",
                value=employee.data_cessazione if is_edit and employee.data_cessazione else None,
                help="Lascia vuoto se dipendente attivo"
            )

        st.markdown("### 💰 Retribuzione")

        col1, col2 = st.columns(2)

        with col1:
            form_data['ral'] = st.number_input(
                "RAL (€)",
                min_value=0.0,
                max_value=1000000.0,
                value=float(employee.ral) if is_edit and employee.ral else 0.0,
                step=100.0,
                format="%.2f"
            )

        with col2:
            form_data['fte'] = st.number_input(
                "FTE",
                min_value=0.0,
                max_value=1.0,
                value=float(employee.fte) if is_edit and employee.fte else 1.0,
                step=0.1,
                help="Full Time Equivalent (1.0 = 100%)"
            )

    # TAB 3: STRUTTURA ORGANIZZATIVA
    with tabs[2]:
        st.markdown("### 🏢 Organizzazione")

        col1, col2 = st.columns(2)

        with col1:
            # Area autocomplete (level 1)
            areas = lookup_service.get_areas()

            default_area = employee.area if is_edit else None

            form_data['area'] = st.selectbox(
                "Area (Livello 1)",
                options=[""] + areas,
                index=areas.index(default_area) + 1 if default_area and default_area in areas else 0,
                help="Unità organizzativa livello 1"
            )

        with col2:
            # SottoArea autocomplete (level 2, filtered by Area)
            if form_data.get('area'):
                sottoaree = lookup_service.get_subareas(form_data['area'])
            else:
                sottoaree = []

            default_sottoarea = employee.sottoarea if is_edit and employee.sottoarea in sottoaree else None

            form_data['sottoarea'] = st.selectbox(
                "SottoArea (Livello 2)",
                options=[""] + sottoaree,
                index=sottoaree.index(default_sottoarea) + 1 if default_sottoarea else 0,
                help="Unità organizzativa livello 2"
            )

        st.markdown("### 👔 Responsabile")

        # Search for manager
        manager_search = st.text_input(
            "Cerca Responsabile",
            placeholder="Nome o CF del responsabile diretto",
            help="Cerca per assegnare un responsabile"
        )

        if manager_search and len(manager_search) >= 3:
            managers = emp_service.search_employees(manager_search, limit=10)

            if managers:
                for mgr in managers:
                    if st.button(
                        f"{mgr.titolare} ({mgr.qualifica or 'N/A'})",
                        key=f"mgr_{mgr.employee_id}"
                    ):
                        form_data['reports_to_codice'] = mgr.codice
                        st.success(f"✅ Responsabile selezionato: {mgr.titolare}")

        if is_edit and employee.reports_to_codice:
            st.info(f"📌 Responsabile attuale: {employee.reports_to_codice}")

    # TAB 4: RUOLI TNS
    with tabs[3]:
        st.markdown("### Ruoli Travel & Expense")

        # Get current roles if editing
        current_roles = set()
        if is_edit:
            role_assignments = role_service.get_employee_roles(employee_id, category="TNS")
            current_roles = {ra.role_code for ra in role_assignments if ra.is_active}

        # TNS roles checkboxes
        tns_roles = [
            ("VIAGGIATORE", "🧳 Viaggiatore", "Può creare e gestire note spese personali"),
            ("APPROVATORE", "✅ Approvatore", "Approva note spese dei subordinati"),
            ("CONTROLLORE", "🔍 Controllore", "Verifica conformità note spese"),
            ("CASSIERE", "💰 Cassiere", "Gestisce rimborsi e pagamenti"),
            ("SEGRETARIO", "📋 Segretario", "Supporto amministrativo travel"),
            ("VISUALIZZATORI", "👁️ Visualizzatori", "Solo visualizzazione dati travel"),
            ("AMMINISTRAZIONE", "⚙️ Amministrazione", "Gestione amministrativa completa")
        ]

        form_data['tns_roles'] = []

        col1, col2 = st.columns(2)

        for idx, (code, label, desc) in enumerate(tns_roles):
            col = col1 if idx % 2 == 0 else col2

            with col:
                is_checked = code in current_roles

                if st.checkbox(
                    label,
                    value=is_checked,
                    key=f"role_{code}",
                    help=desc
                ):
                    form_data['tns_roles'].append(code)

        st.markdown("### 📍 Altre Informazioni TNS")

        col1, col2 = st.columns(2)

        with col1:
            sedi_tns = lookup_service.get_offices()
            default_sede_tns = employee.sede_tns if is_edit and employee.sede_tns in sedi_tns else None

            form_data['sede_tns'] = st.selectbox(
                "Sede TNS",
                options=[""] + sedi_tns,
                index=sedi_tns.index(default_sede_tns) + 1 if default_sede_tns else 0
            )

        with col2:
            form_data['gruppo_sind'] = st.text_input(
                "Gruppo Sindacale",
                value=employee.gruppo_sind if is_edit else ""
            )

    # TAB 5: CONFORMITÀ
    with tabs[4]:
        st.markdown("### 🛡️ SGSL / Salute e Sicurezza")

        # Get current SGSL roles
        sgsl_roles_current = set()
        if is_edit:
            sgsl_assignments = role_service.get_employee_roles(employee_id, category="SGSL")
            sgsl_roles_current = {ra.role_code for ra in sgsl_assignments if ra.is_active}

        sgsl_roles = lookup_service.get_sgsl_roles()

        form_data['sgsl_role'] = st.selectbox(
            "Incarico SGSL",
            options=sgsl_roles,
            index=0
        )

        st.markdown("### 🔒 GDPR / Privacy")

        # Get current GDPR roles
        gdpr_roles_current = set()
        if is_edit:
            gdpr_assignments = role_service.get_employee_roles(employee_id, category="GDPR")
            gdpr_roles_current = {ra.role_code for ra in gdpr_assignments if ra.is_active}

        gdpr_roles = lookup_service.get_gdpr_roles()

        form_data['gdpr_role'] = st.selectbox(
            "Incarico GDPR",
            options=gdpr_roles,
            index=0
        )

    # FOOTER - Action Buttons

    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])

    with col1:
        if st.button("💾 Salva Modifiche", type="primary", use_container_width=True):
            if validate_form(form_data, is_edit):
                save_employee(employee_id, form_data, emp_service, role_service, is_edit)
            else:
                st.error("⚠️ Compila tutti i campi obbligatori")

    with col2:
        if st.button("❌ Annulla", use_container_width=True):
            if 'selected_employee_id' in st.session_state:
                del st.session_state.selected_employee_id
            st.rerun()

    with col3:
        if is_edit and st.button("🗑️ Elimina Dipendente", use_container_width=True):
            st.session_state.show_delete_confirm = True

    with col4:
        if is_edit and st.button("📜 Storico", use_container_width=True):
            st.info("🔧 Vista Storico in development")

    # Delete confirmation dialog
    if st.session_state.get('show_delete_confirm'):
        st.warning("⚠️ **Attenzione**: Vuoi davvero eliminare questo dipendente?")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Conferma Eliminazione", type="primary", use_container_width=True):
                emp_service.delete_employee(employee_id)
                st.success("✅ Dipendente eliminato")
                del st.session_state.selected_employee_id
                st.session_state.show_delete_confirm = False
                st.rerun()

        with col2:
            if st.button("❌ Annulla Eliminazione", use_container_width=True):
                st.session_state.show_delete_confirm = False
                st.rerun()

def validate_form(form_data: dict, is_edit: bool) -> bool:
    """Validate form data"""
    # Required fields for new employee
    if not is_edit:
        if not form_data.get('tx_cod_fiscale') or len(form_data['tx_cod_fiscale']) != 16:
            return False
        if not form_data.get('codice'):
            return False

    # Titolare is required (constructed from cognome + nome)
    if not form_data.get('cognome') or not form_data.get('nome'):
        if not is_edit:
            return False

    return True

def save_employee(employee_id, form_data, emp_service, role_service, is_edit):
    """Save employee data"""
    try:
        # Construct titolare from cognome + nome
        titolare = f"{form_data.get('cognome', '')} {form_data.get('nome', '')}".strip()

        if is_edit:
            # Update existing employee
            updates = EmployeeUpdate(
                cognome=form_data.get('cognome'),
                nome=form_data.get('nome'),
                area=form_data.get('area') or None,
                sottoarea=form_data.get('sottoarea') or None,
                sede=form_data.get('sede') or None,
                contratto=form_data.get('contratto') or None,
                qualifica=form_data.get('qualifica') or None,
                livello=form_data.get('livello') or None,
                ral=Decimal(str(form_data.get('ral', 0))) if form_data.get('ral') else None,
                email=form_data.get('email') or None
            )

            emp_service.update_employee(employee_id, updates)

            st.success("✅ Dipendente aggiornato con successo!")

        else:
            # Create new employee
            new_emp = EmployeeCreate(
                tx_cod_fiscale=form_data['tx_cod_fiscale'],
                codice=form_data['codice'],
                titolare=titolare,
                company_id=form_data.get('company_id', 1),
                cognome=form_data.get('cognome'),
                nome=form_data.get('nome'),
                area=form_data.get('area'),
                sottoarea=form_data.get('sottoarea'),
                sede=form_data.get('sede'),
                contratto=form_data.get('contratto'),
                qualifica=form_data.get('qualifica'),
                ral=Decimal(str(form_data.get('ral', 0))) if form_data.get('ral') else None,
                data_assunzione=form_data.get('data_assunzione'),
                email=form_data.get('email')
            )

            new_id = emp_service.create_employee(new_emp)

            st.success(f"✅ Dipendente creato con successo! ID: {new_id}")

            # Set as selected for viewing
            st.session_state.selected_employee_id = new_id

        st.rerun()

    except Exception as e:
        st.error(f"❌ Errore durante salvataggio: {str(e)}")

if __name__ == "__main__":
    render_employee_card_view()
