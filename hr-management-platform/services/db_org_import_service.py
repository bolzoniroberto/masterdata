"""
DB_ORG Import Service

Service for importing the complete DB_ORG Excel file (135 columns) into
the normalized database schema.

Maps the 135 columns across 6 domains:
- Ambito 1: Organizzativo (col A-AC = 1-29)
- Ambito 2: Anagrafico/Retributivo (col AF-BH = 32-60)
- Ambito 3: TNS Travel (col BS-CV = 71-100)
- Ambito 4: Gerarchie IT (col CW-DG = 101-111)
- Ambito 5: SGSL Safety (col 121-126)
- Ambito 6: GDPR Privacy (col 127-132)
"""
import sqlite3
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, date
from decimal import Decimal

import config
from services.employee_service import get_employee_service
from services.hierarchy_service import get_hierarchy_service
from services.role_service import get_role_service


class DBOrgImportService:
    """Service for importing DB_ORG Excel file into normalized schema"""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or config.DB_PATH
        self.emp_service = get_employee_service()
        self.hierarchy_service = get_hierarchy_service()
        self.role_service = get_role_service()

        # Column mappings for DB_ORG (135 columns)
        self.column_mappings = self._init_column_mappings()

    def _init_column_mappings(self) -> Dict[str, str]:
        """
        Initialize mapping of Excel column names to database fields.

        Returns dict with mappings for each domain.
        """
        return {
            # AMBITO ORGANIZZATIVO (A-AC = 1-29)
            'SocietàOrg': 'societa',
            'Unità Organizzativa': 'unita_org_livello1',
            'Unità Organizzativa 2': 'unita_org_livello2',
            'Testata GG/2': 'testata_gg',
            'CdC': 'cdccosto',
            'CdC Amm': 'cdc_amm',
            'Titolare': 'titolare',
            'Sede': 'sede',
            'Tipo Collaborazione': 'tipo_collaborazione',
            'Formato': 'formato',
            'Funzione': 'funzione',
            'FTE': 'fte',
            'ID': 'codice',
            'ReportsTo': 'reports_to_codice',
            'Photo': 'photo_url',

            # AMBITO ANAGRAFICO (AF-BH = 32-60)
            'TxCodFiscale': 'tx_cod_fiscale',
            'Cognome': 'cognome',
            'Nome': 'nome',
            'Società': 'societa',
            'Area': 'area',
            'SottoArea': 'sottoarea',
            'Data Assunzione': 'data_assunzione',
            'Data Cessazione': 'data_cessazione',
            'Sesso': 'sesso',
            'Contratto': 'contratto',
            'Qualifica': 'qualifica',
            'Livello': 'livello',
            'Indirizzo Via': 'indirizzo_via',
            'CAP': 'indirizzo_cap',
            'Città': 'indirizzo_citta',
            'RAL': 'ral',
            'Data Nascita': 'data_nascita',
            'Email': 'email',
            'Matricola': 'matricola',

            # AMBITO TNS (BS-CV = 71-100)
            'Viaggiatore': 'role_viaggiatore',
            'Approvatore': 'role_approvatore',
            'Controllore': 'role_controllore',
            'Cassiere': 'role_cassiere',
            'Segretario': 'role_segretario',
            'Visualizzatori': 'role_visualizzatori',
            'Amministrazione': 'role_amministrazione',
            'RuoliAFC': 'role_afc',
            'RuoliHR': 'role_hr',
            'Sede_TNS': 'sede_tns',
            'GruppoSind': 'gruppo_sind',
            'Codice TNS': 'cod_tns',           # CB - Codice TNS per organigramma TNS
            'Padre TNS': 'padre_tns',          # CC - Parent TNS per organigramma TNS

            # GERARCHIA HR (CZ)
            'CF Responsabile Diretto': 'reports_to_cf',  # CZ - CF Responsabile per organigramma HR
        }

    def import_db_org_file(
        self,
        excel_path: Path,
        sheet_name: str = 'DB_ORG',
        import_note: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Import complete DB_ORG Excel file into normalized database.

        Args:
            excel_path: Path to Excel file
            sheet_name: Name of sheet to import (default: DB_ORG)
            import_note: Optional note for import version

        Returns:
            Dict with import statistics and results
        """
        results = {
            'success': False,
            'message': '',
            'employees_imported': 0,
            'org_units_imported': 0,
            'hierarchies_assigned': 0,
            'roles_assigned': 0,
            'errors': []
        }

        try:
            # Read Excel file
            print(f"📂 Reading Excel file: {excel_path}")
            df = pd.read_excel(excel_path, sheet_name=sheet_name)

            print(f"✅ Loaded {len(df)} rows, {len(df.columns)} columns")

            # Validate structure
            validation_errors = self._validate_structure(df)
            if validation_errors:
                results['errors'] = validation_errors
                results['message'] = f"Validation failed: {len(validation_errors)} errors"
                return results

            # Start import transaction
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            try:
                # Create import version
                import_version_id = self._create_import_version(
                    cursor,
                    excel_path.name,
                    import_note
                )

                # Step 1: Import companies (if new)
                print("\n📊 Step 1: Processing companies...")
                companies_map = self._import_companies(cursor, df)

                # Step 2: Import organizational units
                print("\n🏢 Step 2: Processing organizational units...")
                org_units_map = self._import_org_units(cursor, df, companies_map)
                results['org_units_imported'] = len(org_units_map)

                # Step 3: Import employees
                print("\n👥 Step 3: Processing employees...")
                employees_map = self._import_employees(cursor, df, companies_map, import_version_id)
                results['employees_imported'] = len(employees_map)

                # Step 4: Assign hierarchies
                print("\n🌳 Step 4: Assigning hierarchies...")
                hierarchy_count = self._assign_hierarchies(cursor, df, employees_map, org_units_map)
                results['hierarchies_assigned'] = hierarchy_count

                # Step 5: Assign roles
                print("\n🎭 Step 5: Assigning roles...")
                role_count = self._assign_roles(cursor, df, employees_map)
                results['roles_assigned'] = role_count

                # Complete import version
                self._complete_import_version(
                    cursor,
                    import_version_id,
                    results['employees_imported'],
                    results['org_units_imported']
                )

                # Commit transaction
                conn.commit()

                results['success'] = True
                results['message'] = f"✅ Import completed successfully"

                print(f"\n✅ Import complete:")
                print(f"  - Employees: {results['employees_imported']}")
                print(f"  - Org Units: {results['org_units_imported']}")
                print(f"  - Hierarchies: {results['hierarchies_assigned']}")
                print(f"  - Roles: {results['roles_assigned']}")

            except Exception as e:
                conn.rollback()
                raise

            finally:
                cursor.close()
                conn.close()

        except Exception as e:
            results['message'] = f"Import failed: {str(e)}"
            results['errors'].append(str(e))
            print(f"❌ Error: {str(e)}")

        return results

    def _validate_structure(self, df: pd.DataFrame) -> List[str]:
        """Validate Excel file structure"""
        errors = []

        # Check for required columns (only ID is truly required for organizational positions)
        if 'ID' not in df.columns:
            errors.append(f"Missing required column: ID")

        # Warn about optional but important columns
        if 'TxCodFiscale' not in df.columns:
            print("  ⚠️ Warning: TxCodFiscale column not found - employees won't be imported")
        if 'Titolare' not in df.columns:
            print("  ⚠️ Warning: Titolare column not found - only vacant positions will be imported")

        # Check for duplicate Codice Fiscale (excluding legitimate AD/CEO duplicates)
        if 'TxCodFiscale' in df.columns:
            # Count unique CF that appear more than once
            cf_counts = df['TxCodFiscale'].value_counts()
            duplicate_cfs = cf_counts[cf_counts > 1]

            # Check if duplicates are legitimate (AD/CEO can have 2 CF)
            legitimate_duplicates = []
            if len(duplicate_cfs) > 0:
                for cf in duplicate_cfs.index:
                    cf_rows = df[df['TxCodFiscale'] == cf]
                    titolari = cf_rows['Titolare'].values if 'Titolare' in cf_rows.columns else []
                    qualifiche = cf_rows['Qualifica'].values if 'Qualifica' in cf_rows.columns else []

                    # Check if it's AD/CEO
                    is_ad = any(
                        'CEO' in str(t).upper() or 'AMMINISTRATORE DELEGATO' in str(t).upper()
                        for t in titolari
                    ) or any(
                        'DIRIGENTE' in str(q).upper() and len(cf_rows) == 2
                        for q in qualifiche
                    )

                    if is_ad:
                        legitimate_duplicates.append(cf)

            # Filter out legitimate duplicates
            actual_duplicates = [cf for cf in duplicate_cfs.index if cf not in legitimate_duplicates]

            if len(actual_duplicates) > 0:
                errors.append(f"Found {len(actual_duplicates)} duplicate Codice Fiscale (excluding AD/CEO)")
            elif len(legitimate_duplicates) > 0:
                # Just a warning, not an error
                pass  # AD/CEO duplicates are allowed

        return errors

    def _create_import_version(
        self,
        cursor: sqlite3.Cursor,
        filename: str,
        note: Optional[str]
    ) -> int:
        """Create import version record"""
        cursor.execute("""
            INSERT INTO import_versions (
                timestamp, source_filename, user_note, completed
            ) VALUES (?, ?, ?, 0)
        """, (datetime.now(), filename, note))

        return cursor.lastrowid

    def _complete_import_version(
        self,
        cursor: sqlite3.Cursor,
        version_id: int,
        personale_count: int,
        strutture_count: int
    ):
        """Complete import version"""
        cursor.execute("""
            UPDATE import_versions
            SET completed = 1,
                completed_at = ?,
                personale_count = ?,
                strutture_count = ?
            WHERE id = ?
        """, (datetime.now(), personale_count, strutture_count, version_id))

    def _import_companies(
        self,
        cursor: sqlite3.Cursor,
        df: pd.DataFrame
    ) -> Dict[str, int]:
        """Import/update companies, return mapping"""
        companies_map = {}

        # Get unique companies from data
        if 'Società' in df.columns:
            unique_companies = df['Società'].dropna().unique()

            for company_name in unique_companies:
                # Check if exists
                cursor.execute(
                    "SELECT company_id FROM companies WHERE company_name = ?",
                    (company_name,)
                )
                row = cursor.fetchone()

                if row:
                    companies_map[company_name] = row[0]
                else:
                    # Insert new company
                    cursor.execute("""
                        INSERT INTO companies (company_code, company_name, active)
                        VALUES (?, ?, 1)
                    """, (company_name.upper().replace(' ', '_'), company_name))

                    companies_map[company_name] = cursor.lastrowid

        # Default to Il Sole 24 ORE
        cursor.execute("SELECT company_id FROM companies WHERE company_code = 'IL_SOLE_24ORE'")
        default_row = cursor.fetchone()
        if default_row:
            companies_map['_DEFAULT'] = default_row[0]
        else:
            # If default company doesn't exist, use the first company or create one
            if companies_map:
                companies_map['_DEFAULT'] = list(companies_map.values())[0]
            else:
                # Create default company
                cursor.execute("""
                    INSERT INTO companies (company_code, company_name, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                """, ('IL_SOLE_24ORE', 'Il Sole 24 ORE', datetime.now(), datetime.now()))
                companies_map['_DEFAULT'] = cursor.lastrowid

        return companies_map

    def _import_org_units(
        self,
        cursor: sqlite3.Cursor,
        df: pd.DataFrame,
        companies_map: Dict[str, int]
    ) -> Dict[str, int]:
        """Import organizational units"""
        org_units_map = {}

        # Get unique org units
        if 'ID' in df.columns:
            # Include ReportsTo for parent relationship
            columns_to_include = ['ID', 'Unità Organizzativa', 'Unità Organizzativa 2', 'CdC', 'Società']
            if 'ReportsTo' in df.columns:
                columns_to_include.append('ReportsTo')

            unique_units = df[columns_to_include].drop_duplicates()

            # FIRST PASS: Insert all org units without parent
            for _, row in unique_units.iterrows():
                codice = str(row.get('ID', '')).strip() if pd.notna(row.get('ID')) else None
                if not codice:
                    continue

                descrizione = str(row.get('Unità Organizzativa', '')).strip() if pd.notna(row.get('Unità Organizzativa')) else codice
                livello1 = str(row.get('Unità Organizzativa', '')).strip() if pd.notna(row.get('Unità Organizzativa')) else None
                livello2 = str(row.get('Unità Organizzativa 2', '')).strip() if pd.notna(row.get('Unità Organizzativa 2')) else None
                cdccosto = str(row.get('CdC', '')).strip() if pd.notna(row.get('CdC')) else None
                societa = str(row.get('Società', '')).strip() if pd.notna(row.get('Società')) else None

                company_id = companies_map.get(societa, companies_map['_DEFAULT'])

                # Check if exists
                cursor.execute("SELECT org_unit_id FROM org_units WHERE codice = ?", (codice,))
                existing = cursor.fetchone()

                if existing:
                    org_units_map[codice] = existing[0]
                else:
                    # Insert new org unit (parent will be set in second pass)
                    cursor.execute("""
                        INSERT INTO org_units (
                            codice, descrizione, company_id,
                            cdccosto, unita_org_livello1, unita_org_livello2,
                            livello, active, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                    """, (
                        codice, descrizione, company_id,
                        cdccosto, livello1, livello2,
                        2 if livello2 else 1,  # Determine level
                        datetime.now(), datetime.now()
                    ))

                    org_units_map[codice] = cursor.lastrowid

            # SECOND PASS: Update parent relationships using ReportsTo (AC column)
            if 'ReportsTo' in df.columns:
                print("  🔗 Setting up parent relationships...")
                parent_count = 0

                for _, row in unique_units.iterrows():
                    codice = str(row.get('ID', '')).strip() if pd.notna(row.get('ID')) else None
                    if not codice:
                        continue

                    parent_codice = str(row.get('ReportsTo', '')).strip() if pd.notna(row.get('ReportsTo')) else None

                    if parent_codice and parent_codice in org_units_map:
                        parent_id = org_units_map[parent_codice]

                        cursor.execute("""
                            UPDATE org_units
                            SET parent_org_unit_id = ?
                            WHERE codice = ?
                        """, (parent_id, codice))

                        parent_count += 1

                print(f"  ✅ Set {parent_count} parent relationships")

        return org_units_map

    def _import_employees(
        self,
        cursor: sqlite3.Cursor,
        df: pd.DataFrame,
        companies_map: Dict[str, int],
        import_version_id: int
    ) -> Dict[str, int]:
        """Import employees"""
        employees_map = {}
        imported_count = 0

        for idx, row in df.iterrows():
            try:
                # Extract required fields (use .get() to handle unmapped columns)
                cf = str(row.get('TxCodFiscale', '')).strip().upper() if pd.notna(row.get('TxCodFiscale')) else None
                codice = str(row.get('ID', '')).strip() if pd.notna(row.get('ID')) else None
                titolare = str(row.get('Titolare', '')).strip() if pd.notna(row.get('Titolare')) else None

                if not cf or not codice or not titolare:
                    continue

                # Get company
                societa = str(row.get('Società', '')).strip() if pd.notna(row.get('Società')) else None
                company_id = companies_map.get(societa, companies_map['_DEFAULT'])

                # Extract all fields
                cognome = str(row.get('Cognome', '')).strip() if pd.notna(row.get('Cognome')) else None
                nome = str(row.get('Nome', '')).strip() if pd.notna(row.get('Nome')) else None
                area = str(row.get('Area', '')).strip() if pd.notna(row.get('Area')) else None
                sottoarea = str(row.get('SottoArea', '')).strip() if pd.notna(row.get('SottoArea')) else None
                sede = str(row.get('Sede', '')).strip() if pd.notna(row.get('Sede')) else None
                contratto = str(row.get('Contratto', '')).strip() if pd.notna(row.get('Contratto')) else None
                qualifica = str(row.get('Qualifica', '')).strip() if pd.notna(row.get('Qualifica')) else None
                livello = str(row.get('Livello', '')).strip() if pd.notna(row.get('Livello')) else None
                email = str(row.get('Email', '')).strip() if pd.notna(row.get('Email')) else None
                matricola = str(row.get('Matricola', '')).strip() if pd.notna(row.get('Matricola')) else None

                # Parse RAL
                ral = None
                if pd.notna(row.get('RAL')):
                    try:
                        ral = float(row.get('RAL'))
                    except:
                        pass

                # Parse dates
                data_assunzione = self._parse_date(row.get('Data Assunzione'))
                data_cessazione = self._parse_date(row.get('Data Cessazione'))
                data_nascita = self._parse_date(row.get('Data Nascita'))

                # Other fields
                sesso = str(row.get('Sesso', '')).strip() if pd.notna(row.get('Sesso')) else None
                fte = float(row.get('FTE', 1.0)) if pd.notna(row.get('FTE')) else 1.0

                # Hierarchy fields
                reports_to = str(row.get('ReportsTo', '')).strip() if pd.notna(row.get('ReportsTo')) else None
                reports_to_cf = str(row.get('CF Responsabile Diretto', '')).strip() if pd.notna(row.get('CF Responsabile Diretto')) else None
                cod_tns = str(row.get('Codice TNS', '')).strip() if pd.notna(row.get('Codice TNS')) else None
                padre_tns = str(row.get('Padre TNS', '')).strip() if pd.notna(row.get('Padre TNS')) else None

                # PREVENT CYCLES: Employee cannot report to themselves
                if reports_to_cf and reports_to_cf.upper() == cf.upper():
                    reports_to_cf = None  # Make them a top manager instead

                if cod_tns and padre_tns and cod_tns.upper() == padre_tns.upper():
                    padre_tns = None  # Prevent TNS cycle

                # Check if employee exists
                cursor.execute("SELECT employee_id FROM employees WHERE tx_cod_fiscale = ?", (cf,))
                existing = cursor.fetchone()

                if existing:
                    # UPDATE existing employee with new data (including hierarchy fields!)
                    employee_id = existing[0]
                    cursor.execute("""
                        UPDATE employees SET
                            codice = ?, titolare = ?, company_id = ?,
                            cognome = ?, nome = ?, societa = ?, area = ?, sottoarea = ?, sede = ?,
                            contratto = ?, qualifica = ?, livello = ?, ral = ?,
                            data_assunzione = ?, data_cessazione = ?, data_nascita = ?,
                            sesso = ?, email = ?, matricola = ?, fte = ?, reports_to_codice = ?,
                            reports_to_cf = ?, cod_tns = ?, padre_tns = ?,
                            updated_at = ?
                        WHERE employee_id = ?
                    """, (
                        codice, titolare, company_id,
                        cognome, nome, societa, area, sottoarea, sede,
                        contratto, qualifica, livello, ral,
                        data_assunzione, data_cessazione, data_nascita,
                        sesso, email, matricola, fte, reports_to,
                        reports_to_cf, cod_tns, padre_tns,
                        datetime.now(), employee_id
                    ))
                    employees_map[cf] = employee_id
                    imported_count += 1
                else:
                    # Insert new employee
                    cursor.execute("""
                        INSERT INTO employees (
                            tx_cod_fiscale, codice, titolare, company_id,
                            cognome, nome, societa, area, sottoarea, sede,
                            contratto, qualifica, livello, ral,
                            data_assunzione, data_cessazione, data_nascita,
                            sesso, email, matricola, fte, reports_to_codice,
                            reports_to_cf, cod_tns, padre_tns,
                            active, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                                  ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                    """, (
                        cf, codice, titolare, company_id,
                        cognome, nome, societa, area, sottoarea, sede,
                        contratto, qualifica, livello, ral,
                        data_assunzione, data_cessazione, data_nascita,
                        sesso, email, matricola, fte, reports_to,
                        reports_to_cf, cod_tns, padre_tns,
                        datetime.now(), datetime.now()
                    ))

                    employee_id = cursor.lastrowid
                    employees_map[cf] = employee_id
                    imported_count += 1

                    # Log audit
                    cursor.execute("""
                        INSERT INTO audit_log (
                            table_name, record_id, action, import_version_id,
                            change_severity, timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, ('employees', employee_id, 'INSERT', import_version_id, 'HIGH', datetime.now()))

            except Exception as e:
                print(f"  ⚠️ Error importing row {idx}: {str(e)}")
                continue

        print(f"  ✅ Imported {imported_count} employees")
        return employees_map

    def _assign_hierarchies(
        self,
        cursor: sqlite3.Cursor,
        df: pd.DataFrame,
        employees_map: Dict[str, int],
        org_units_map: Dict[str, int]
    ) -> int:
        """Assign employees to organizational hierarchies"""
        count = 0

        # Get HR hierarchy type
        cursor.execute("SELECT hierarchy_type_id FROM hierarchy_types WHERE type_code = 'HR'")
        hr_type_row = cursor.fetchone()
        if not hr_type_row:
            print("  ⚠️ Warning: HR hierarchy type not found, skipping hierarchy assignments")
            return 0
        hr_type_id = hr_type_row[0]

        today = date.today()

        for _, row in df.iterrows():
            cf = str(row.get('TxCodFiscale', '')).strip().upper() if pd.notna(row.get('TxCodFiscale')) else None
            org_unit_code = str(row.get('ID', '')).strip() if pd.notna(row.get('ID')) else None

            if not cf or not org_unit_code:
                continue

            employee_id = employees_map.get(cf)
            org_unit_id = org_units_map.get(org_unit_code)

            if employee_id and org_unit_id:
                # Check if assignment exists
                cursor.execute("""
                    SELECT assignment_id FROM hierarchy_assignments
                    WHERE employee_id = ? AND org_unit_id = ? AND hierarchy_type_id = ?
                """, (employee_id, org_unit_id, hr_type_id))

                if not cursor.fetchone():
                    # Insert hierarchy assignment
                    cursor.execute("""
                        INSERT INTO hierarchy_assignments (
                            employee_id, org_unit_id, hierarchy_type_id,
                            effective_date, is_primary, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, 1, ?, ?)
                    """, (employee_id, org_unit_id, hr_type_id, today, datetime.now(), datetime.now()))

                    count += 1

        print(f"  ✅ Assigned {count} hierarchy relationships")
        return count

    def _assign_roles(
        self,
        cursor: sqlite3.Cursor,
        df: pd.DataFrame,
        employees_map: Dict[str, int]
    ) -> int:
        """Assign TNS roles to employees"""
        count = 0

        # Role mappings
        role_columns = {
            'Viaggiatore': 'VIAGGIATORE',
            'Approvatore': 'APPROVATORE',
            'Controllore': 'CONTROLLORE',
            'Cassiere': 'CASSIERE',
            'Segretario': 'SEGRETARIO',
            'Visualizzatori': 'VISUALIZZATORI',
            'Amministrazione': 'AMMINISTRAZIONE'
        }

        today = date.today()

        for _, row in df.iterrows():
            cf = str(row.get('TxCodFiscale', '')).strip().upper() if pd.notna(row.get('TxCodFiscale')) else None
            if not cf:
                continue

            employee_id = employees_map.get(cf)
            if not employee_id:
                continue

            # Check each role column
            for excel_col, role_code in role_columns.items():
                if excel_col not in df.columns:
                    continue

                value = str(row.get(excel_col, '')).strip().upper() if pd.notna(row.get(excel_col)) else ''

                # If "SI" or similar, assign role
                if value in ['SI', 'SÌ', 'YES', 'S', 'X', '1']:
                    # Get role_id
                    cursor.execute("SELECT role_id FROM role_definitions WHERE role_code = ?", (role_code,))
                    role_row = cursor.fetchone()

                    if role_row:
                        role_id = role_row[0]

                        # Check if assignment exists
                        cursor.execute("""
                            SELECT assignment_id FROM role_assignments
                            WHERE employee_id = ? AND role_id = ?
                              AND (end_date IS NULL OR end_date > ?)
                        """, (employee_id, role_id, today))

                        if not cursor.fetchone():
                            # Insert role assignment
                            cursor.execute("""
                                INSERT INTO role_assignments (
                                    employee_id, role_id, effective_date,
                                    created_at, updated_at
                                ) VALUES (?, ?, ?, ?, ?)
                            """, (employee_id, role_id, today, datetime.now(), datetime.now()))

                            count += 1

        print(f"  ✅ Assigned {count} role assignments")
        return count

    def _parse_date(self, value) -> Optional[date]:
        """Parse date from various formats"""
        if pd.isna(value):
            return None

        try:
            if isinstance(value, datetime):
                return value.date()
            elif isinstance(value, date):
                return value
            elif isinstance(value, str):
                # Try common formats
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                    try:
                        return datetime.strptime(value, fmt).date()
                    except:
                        continue
        except:
            pass

        return None


# Singleton instance
_db_org_import_service_instance = None


def get_db_org_import_service() -> DBOrgImportService:
    """Get singleton instance of DBOrgImportService"""
    global _db_org_import_service_instance
    if _db_org_import_service_instance is None:
        _db_org_import_service_instance = DBOrgImportService()
    return _db_org_import_service_instance
