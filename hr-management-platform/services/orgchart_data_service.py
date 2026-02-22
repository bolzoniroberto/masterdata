"""
OrgChart Data Service

Prepares JSON data for interactive orgchart views using d3-org-chart.

Data sources:
- HR orgchart: strutture table (Codice = ID, UNITA_OPERATIVA_PADRE = ReportsTo)
- TNS orgchart: strutture + personale with approvatore roles
"""
from typing import Dict, List, Optional, Any

from services.database import DatabaseHandler


class OrgChartDataService:
    """Service for preparing orgchart data in d3-org-chart flat-list format."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.db = DatabaseHandler()
        self._initialized = True

    def _query(self, sql: str, params: tuple = ()) -> List[Dict]:
        """Execute a query and return list of dicts."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    # ========== VIEW 1: HR HIERARCHY (employees tree by reports_to_cf) ==========

    def get_hr_hierarchy_tree(
        self,
        company_id: Optional[int] = None,
        area_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build HR hierarchy as flat list for d3-org-chart.

        Tree based on employees: tx_cod_fiscale (ID) → reports_to_cf (Parent CF).
        Each node is a person with their direct reports.

        Returns flat list format required by d3-org-chart:
        [{"id": "RSSMRA80A01H501Z", "parentId": "VRDGPP75B12F205L", "name": "...", ...}, ...]
        """
        # Load all employees with hierarchy info
        employees = self._query("""
            SELECT
                tx_cod_fiscale,
                codice,
                titolare,
                reports_to_cf,
                cognome,
                nome,
                qualifica,
                area,
                sede,
                company_id
            FROM employees
            WHERE tx_cod_fiscale IS NOT NULL
            ORDER BY titolare
        """)

        if not employees:
            return {}

        # Build valid CF set for parent validation
        valid_cfs = {e['tx_cod_fiscale'] for e in employees}

        # Build flat list
        nodes = []
        for emp in employees:
            parent_cf = emp['reports_to_cf']

            # Clean up parent: if empty or not in valid set, assign to virtual ROOT
            if not parent_cf or parent_cf.strip() == '' or parent_cf not in valid_cfs:
                parent_cf = 'ROOT'  # Virtual root for multiple orphans

            node = {
                'id': emp['tx_cod_fiscale'],
                'parentId': parent_cf,
                'name': emp['titolare'] or emp['tx_cod_fiscale'],
                'title': emp['qualifica'] or '',
                'area': emp['area'] or '',
                'sede': emp['sede'] or '',
                'codice': emp['codice'] or '',
                'employee_count': 0,  # Calculated by frontend
                'has_responsible': parent_cf != 'ROOT',
                'roles': []
            }

            if emp['qualifica']:
                node['roles'].append({'name': emp['qualifica'], 'color': 'blue'})

            nodes.append(node)

        # Add virtual ROOT node
        nodes.insert(0, {
            'id': 'ROOT',
            'parentId': None,
            'name': 'Organizzazione',
            'title': 'Root virtuale',
            'area': '',
            'sede': '',
            'codice': '',
            'employee_count': 0,
            'has_responsible': False,
            'roles': []
        })

        return {'nodes': nodes, 'type': 'HR'}

    # ========== VIEW 2: TNS HIERARCHY (employees tree by cod_tns → padre_tns) ==========

    def get_tns_hierarchy_tree(
        self,
        company_id: Optional[int] = None,
        area_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build TNS hierarchy showing employees with TNS codes.

        Tree based on employees: cod_tns (ID) → padre_tns (Parent TNS code).
        Only includes employees with TNS codes assigned.

        Returns flat list of employee nodes with TNS hierarchy.
        """
        # Load employees with TNS codes
        employees = self._query("""
            SELECT
                cod_tns,
                padre_tns,
                tx_cod_fiscale,
                titolare,
                qualifica,
                area,
                sede
            FROM employees
            WHERE cod_tns IS NOT NULL AND cod_tns != ''
            ORDER BY titolare
        """)

        if not employees:
            return {}

        # Build valid TNS codes set for parent validation
        valid_tns_codes = {e['cod_tns'] for e in employees}

        # Build flat list
        nodes = []
        for emp in employees:
            parent_tns = emp['padre_tns']

            # Clean up parent: if empty or not in valid set, assign to virtual ROOT
            if not parent_tns or parent_tns.strip() == '' or parent_tns not in valid_tns_codes:
                parent_tns = 'ROOT_TNS'  # Virtual root for TNS hierarchy

            node = {
                'id': emp['cod_tns'],
                'parentId': parent_tns,
                'name': emp['titolare'] or emp['tx_cod_fiscale'],
                'title': emp['qualifica'] or '',
                'area': emp['area'] or '',
                'sede': emp['sede'] or '',
                'tx_cod_fiscale': emp['tx_cod_fiscale'],
                'employee_count': 0,  # Calculated by frontend
                'has_parent': parent_tns != 'ROOT_TNS',
                'roles': []
            }

            if emp['qualifica']:
                node['roles'].append({'name': emp['qualifica'], 'color': 'green'})

            nodes.append(node)

        # Add virtual ROOT node for TNS
        nodes.insert(0, {
            'id': 'ROOT_TNS',
            'parentId': None,
            'name': 'Struttura TNS',
            'title': 'Root TNS',
            'area': '',
            'sede': '',
            'tx_cod_fiscale': '',
            'employee_count': 0,
            'has_parent': False,
            'roles': []
        })

        return {'nodes': nodes, 'type': 'TNS'}

    # ========== VIEW 3: SGSL HIERARCHY ==========

    def get_sgsl_hierarchy_tree(self) -> Dict[str, Any]:
        """
        Build SGSL safety hierarchy showing employees with safety roles.

        Groups by struttura, shows RSPP/RLS/HSE role holders.
        """
        # Employees with SGSL-related roles via RUOLI field
        sgsl_people = self._query("""
            SELECT p.TxCodFiscale, p.Titolare, p.RUOLI, p.RUOLI_OltreV,
                   p.UNITA_OPERATIVA_PADRE, p.Unità_Organizzativa
            FROM personale p
            WHERE (p.RUOLI IS NOT NULL AND p.RUOLI != '')
               OR (p.RUOLI_OltreV IS NOT NULL AND p.RUOLI_OltreV != '')
            ORDER BY p.Titolare
        """)

        # Build virtual tree by struttura
        struttura_nodes: Dict[str, Dict] = {}
        for p in sgsl_people:
            sc = p['UNITA_OPERATIVA_PADRE'] or 'UNKNOWN'
            if sc not in struttura_nodes:
                struttura_nodes[sc] = {
                    'id': f'sgsl_{sc}',
                    'parentId': None,
                    'name': sc,
                    'title': 'Struttura',
                    'area': '',
                    'children_people': []
                }
            roles_raw = (p['RUOLI'] or '') + ' ' + (p['RUOLI_OltreV'] or '')
            struttura_nodes[sc]['children_people'].append({
                'id': p['TxCodFiscale'],
                'name': p['Titolare'] or p['TxCodFiscale'],
                'title': roles_raw.strip()[:50],
                'area': p['Unità_Organizzativa'] or '',
                'roles': self._parse_sgsl_roles(roles_raw)
            })

        # Build flat list
        nodes = []
        root = {
            'id': 'sgsl_root',
            'parentId': None,
            'name': 'SGSL - Salute e Sicurezza',
            'title': 'Struttura SGSL',
            'area': '',
            'roles': []
        }
        nodes.append(root)

        for sc, sn in struttura_nodes.items():
            # Get struttura description
            struttura_info = self._query(
                "SELECT DESCRIZIONE FROM strutture WHERE Codice = ?", (sc,)
            )
            sn['name'] = struttura_info[0]['DESCRIZIONE'] if struttura_info else sc
            sn['parentId'] = 'sgsl_root'
            sn['roles'] = []
            nodes.append(sn)

            for person in sn.get('children_people', []):
                person['parentId'] = f'sgsl_{sc}'
                nodes.append(person)

        return {'nodes': nodes, 'type': 'SGSL'}

    def _parse_sgsl_roles(self, roles_str: str) -> List[Dict]:
        """Parse SGSL role strings into badge format."""
        roles = []
        roles_upper = roles_str.upper()
        if 'RSPP' in roles_upper:
            roles.append({'name': 'RSPP', 'color': 'red'})
        if 'RLS' in roles_upper:
            roles.append({'name': 'RLS', 'color': 'orange'})
        if 'HSE' in roles_upper or 'COORDINAT' in roles_upper:
            roles.append({'name': 'HSE', 'color': 'orange'})
        if not roles and roles_str.strip():
            roles.append({'name': roles_str.strip()[:20], 'color': 'gray'})
        return roles

    # ========== VIEW 5: POSITIONS TREE (all rows: strutture + personale as nodes) ==========

    def get_positions_tree(self) -> Dict[str, Any]:
        """
        Build the full org hierarchy for the 'Unità Organizzative' view.

        Uses columns AB (ID = Codice) and AC (ReportsTo = UNITA_OPERATIVA_PADRE).
        Returns ALL rows from both tables as separate tree nodes:

        - Struttura nodes (281): structural/organizational units, node_type='struttura'
          • has_employees=True  → unit has at least one personale assigned (normal)
          • has_employees=False → unit is empty (FTE=0, orange styling)
        - Personale nodes (733): individual employees, node_type='person'
          • always has_employees=True (they ARE the employees, the "caselline")
          • parentId = their UNITA_OPERATIVA_PADRE (a struttura.Codice)

        No ID collisions: strutture.Codice and personale.TxCodFiscale are disjoint.
        """
        strutture = self._query("""
            SELECT Codice, DESCRIZIONE, UNITA_OPERATIVA_PADRE
            FROM strutture
            ORDER BY Codice
        """)
        if not strutture:
            return {}

        valid_strut = {s['Codice'].strip() for s in strutture if s['Codice']}

        # Track which strutture have at least one employee (for FTE=0 detection)
        emp_rows = self._query("""
            SELECT p.TxCodFiscale, p.Titolare, p.UNITA_OPERATIVA_PADRE,
                   p.Approvatore, p.Viaggiatore, p.Controllore, p.Cassiere
            FROM personale p
            WHERE p.TxCodFiscale IS NOT NULL AND p.TxCodFiscale != ''
            ORDER BY p.Titolare
        """)

        strutture_with_emp = set()
        for e in emp_rows:
            uo = (e['UNITA_OPERATIVA_PADRE'] or '').strip()
            if uo in valid_strut:
                strutture_with_emp.add(uo)

        nodes = []

        # --- Struttura nodes ---
        for s in strutture:
            sid = (s['Codice'] or '').strip()
            if not sid:
                continue
            parent = (s['UNITA_OPERATIVA_PADRE'] or '').strip()
            if not parent or parent not in valid_strut:
                parent = None

            nodes.append({
                'id':           sid,
                'parentId':     parent,
                'name':         (s['DESCRIZIONE'] or sid),
                'node_type':    'struttura',
                'has_employees': sid in strutture_with_emp,
                'employee_count': 0,  # filled in JS from children count
                'roles':        [],
            })

        # --- Personale nodes (the "caselline per dipendente") ---
        for e in emp_rows:
            cf = (e['TxCodFiscale'] or '').strip()
            if not cf:
                continue
            titolare = (e['Titolare'] or cf).strip()
            parent_uo = (e['UNITA_OPERATIVA_PADRE'] or '').strip()
            parent = parent_uo if parent_uo in valid_strut else None

            roles = []
            if e.get('Approvatore'): roles.append('App')
            if e.get('Viaggiatore'): roles.append('Viag')
            if e.get('Controllore'): roles.append('Contr')
            if e.get('Cassiere'):    roles.append('Cass')

            nodes.append({
                'id':           cf,
                'parentId':     parent,
                'name':         titolare,
                'node_type':    'person',
                'has_employees': True,
                'employee_count': 0,
                'roles':        roles,
            })

        return {'nodes': nodes, 'type': 'POSITIONS'}

    # ========== VIEW 4: TNS STRUCTURES WITH APPROVERS ==========

    def get_tns_structures_tree(self) -> Dict[str, Any]:
        """
        Same as TNS hierarchy but focused on structures + their approvers.
        Highlights structures without approvers in red.
        """
        return self.get_tns_hierarchy_tree()

    # ========== VIEW 0: ORGANIZATION HIERARCHY (strutture + personale leaves) ==========

    def get_org_hierarchy_tree(self) -> Dict[str, Any]:
        """
        Full organization hierarchy: strutture as internal nodes, personale as leaf nodes.

        IDs:
        - Struttura nodes: id = "s_" + Codice  (prefix avoids collision)
        - Personale nodes: id = "p_" + TxCodFiscale
        - Personale parentId = "s_" + their UNITA_OPERATIVA_PADRE

        ReportsTo chain: personale.UNITA_OPERATIVA_PADRE -> struttura.Codice
                         struttura.UNITA_OPERATIVA_PADRE -> parent struttura.Codice
        """
        strutture = self._query("""
            SELECT Codice, DESCRIZIONE, UNITA_OPERATIVA_PADRE
            FROM strutture ORDER BY Codice
        """)
        personale = self._query("""
            SELECT TxCodFiscale, Titolare, UNITA_OPERATIVA_PADRE,
                   Approvatore, Viaggiatore, Controllore, Cassiere
            FROM personale
            WHERE UNITA_OPERATIVA_PADRE IS NOT NULL AND UNITA_OPERATIVA_PADRE != ''
            ORDER BY Titolare
        """)

        if not strutture:
            return {}

        valid_s = {s['Codice'] for s in strutture}
        nodes = []

        # Struttura nodes
        for s in strutture:
            parent = s['UNITA_OPERATIVA_PADRE']
            if not parent or parent not in valid_s:
                parent_id = None
            else:
                parent_id = 's_' + parent

            nodes.append({
                'id': 's_' + s['Codice'],
                'parentId': parent_id,
                'name': s['DESCRIZIONE'] or s['Codice'],
                'title': '',
                'area': '',
                'node_type': 'struttura',
                'codice': s['Codice'],
                'employee_count': 0,
                'has_responsible': False,
                'roles': []
            })

        # Employee count per struttura
        emp_counts: Dict[str, int] = {}
        for p in personale:
            sc = p['UNITA_OPERATIVA_PADRE']
            emp_counts[sc] = emp_counts.get(sc, 0) + 1

        # Update employee counts on struttura nodes
        for n in nodes:
            n['employee_count'] = emp_counts.get(n['codice'], 0)

        # Personale nodes (leaves)
        for p in personale:
            sc = p['UNITA_OPERATIVA_PADRE']
            if sc not in valid_s:
                continue  # skip if struttura unknown
            roles = []
            if p.get('Approvatore'): roles.append({'name': 'App', 'color': 'blue'})
            if p.get('Viaggiatore'): roles.append({'name': 'Viag', 'color': 'green'})
            if p.get('Controllore'): roles.append({'name': 'Contr', 'color': 'orange'})
            if p.get('Cassiere'):    roles.append({'name': 'Cass', 'color': 'red'})
            nodes.append({
                'id': 'p_' + p['TxCodFiscale'],
                'parentId': 's_' + sc,
                'name': p['Titolare'] or p['TxCodFiscale'],
                'title': ', '.join(r['name'] for r in roles) if roles else '',
                'area': '',
                'node_type': 'person',
                'tx_cod_fiscale': p['TxCodFiscale'],
                'employee_count': 0,
                'has_responsible': bool(roles),
                'roles': roles
            })

        return {'nodes': nodes, 'type': 'ORG'}

    # ========== VIEW 5: PURE ORG UNITS TREE (org_units with parent_org_unit_id) ==========

    def get_org_units_tree(self) -> Dict[str, Any]:
        """
        Pure org unit tree showing only organizational positions (no employee names).
        Uses new org_units table with parent_org_unit_id for hierarchy.
        Color-coded by hierarchy depth.
        """
        # Load org_units with parent relationship resolved
        org_units = self._query("""
            SELECT
                o.org_unit_id,
                o.codice,
                o.descrizione,
                o.parent_org_unit_id,
                o.cdccosto,
                o.livello,
                parent.codice AS parent_codice
            FROM org_units o
            LEFT JOIN org_units parent ON o.parent_org_unit_id = parent.org_unit_id
            ORDER BY o.descrizione
        """)

        if not org_units:
            return {}

        # Count employees per org unit (by codice)
        # For now, we don't have a direct link, so set to 0
        # TODO: When employees have org_unit_id FK, count properly
        emp_counts = {}

        nodes = []
        for unit in org_units:
            parent_codice = unit['parent_codice']

            # If no parent, assign to virtual ROOT
            if not parent_codice or parent_codice.strip() == '':
                parent_codice = 'ROOT_ORG'

            emp_count = emp_counts.get(unit['codice'], 0)

            nodes.append({
                'id': unit['codice'],
                'parentId': parent_codice,
                'name': unit['descrizione'] or unit['codice'],
                'title': f"Livello: {unit['livello'] or 'N/A'}",
                'area': f"CdC: {unit['cdccosto']}" if unit['cdccosto'] else '',
                'employee_count': emp_count,
                'livello': unit['livello'],
                'cdccosto': unit['cdccosto'] or '',
                'roles': []
            })

        # Add virtual ROOT node for org units
        nodes.insert(0, {
            'id': 'ROOT_ORG',
            'parentId': None,
            'name': 'Organizzazione',
            'title': 'Root Org',
            'area': '',
            'employee_count': 0,
            'livello': 0,
            'cdccosto': '',
            'roles': []
        })

        return {'nodes': nodes, 'type': 'ORG_UNITS'}

    # ========== SEARCH ==========

    def search_employee(self, query: str, hierarchy_type: str = 'HR') -> Optional[Dict]:
        """Search employee by name or CF and return their hierarchy path."""
        if not query or len(query) < 2:
            return None

        results = self._query("""
            SELECT p.TxCodFiscale, p.Titolare, p.Codice,
                   p.Unità_Organizzativa, p.UNITA_OPERATIVA_PADRE,
                   p.Approvatore, p.Viaggiatore
            FROM personale p
            WHERE p.Titolare LIKE ? OR p.TxCodFiscale LIKE ?
            LIMIT 5
        """, (f'%{query}%', f'%{query}%'))

        if not results:
            return None

        emp = results[0]
        path = self._get_struttura_path(emp['UNITA_OPERATIVA_PADRE'])

        return {
            'employee': emp,
            'path': path
        }

    def search_structure(self, query: str) -> Optional[Dict]:
        """Search struttura by name or code."""
        if not query or len(query) < 2:
            return None

        results = self._query("""
            SELECT Codice, DESCRIZIONE, UNITA_OPERATIVA_PADRE, Titolare
            FROM strutture
            WHERE DESCRIZIONE LIKE ? OR Codice LIKE ?
            LIMIT 5
        """, (f'%{query}%', f'%{query}%'))

        if not results:
            return None

        s = results[0]
        path = self._get_struttura_path(s['Codice'])
        return {'struttura': s, 'path': path}

    def _get_struttura_path(self, codice: str) -> List[Dict]:
        """Walk up strutture hierarchy and return path from root to node."""
        if not codice:
            return []

        path = []
        current = codice
        visited = set()

        while current and current not in visited:
            visited.add(current)
            rows = self._query(
                "SELECT Codice, DESCRIZIONE, UNITA_OPERATIVA_PADRE FROM strutture WHERE Codice = ?",
                (current,)
            )
            if not rows:
                break
            row = rows[0]
            path.append({'id': row['Codice'], 'name': row['DESCRIZIONE'] or row['Codice']})
            current = row['UNITA_OPERATIVA_PADRE']

        path.reverse()
        return path

    def get_node_details(self, employee_cf: str) -> Optional[Dict]:
        """Get full employee details for tooltip/popup."""
        results = self._query("""
            SELECT * FROM personale WHERE TxCodFiscale = ?
        """, (employee_cf,))

        if not results:
            return None

        emp = results[0]
        path = self._get_struttura_path(emp.get('UNITA_OPERATIVA_PADRE'))

        return {
            'employee': emp,
            'path': path
        }


def get_orgchart_data_service() -> OrgChartDataService:
    """Get singleton OrgChartDataService instance."""
    return OrgChartDataService()
