"""
Lookup Service

Provides lookup values for dropdown menus and autocomplete fields.
Values are dynamically queried from database to ensure data quality.
"""
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
from functools import lru_cache
import config


class LookupService:
    """
    Service for managing lookup values for form fields.

    Provides values for dropdowns, autocomplete, and radio buttons
    based on actual data in the database.
    """

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or config.DB_PATH

    def _execute_query(self, query: str, params: tuple = ()) -> List[tuple]:
        """Execute a SELECT query and return results"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    # === COMPANIES ===

    @lru_cache(maxsize=1)
    def get_companies(self) -> List[Dict[str, str]]:
        """
        Get all active companies.

        Returns:
            List of dicts with company_id, company_code, company_name
        """
        query = """
            SELECT company_id, company_code, company_name
            FROM companies
            WHERE active = 1
            ORDER BY company_name
        """
        results = self._execute_query(query)
        return [
            {
                'company_id': row[0],
                'company_code': row[1],
                'company_name': row[2]
            }
            for row in results
        ]

    def get_company_names(self) -> List[str]:
        """Get list of company names for dropdown"""
        companies = self.get_companies()
        return [c['company_name'] for c in companies]

    # === CONTRACT TYPES ===

    @lru_cache(maxsize=1)
    def get_contract_types(self) -> List[str]:
        """
        Get all unique contract types from employees.

        Returns:
            Sorted list of contract descriptions
        """
        query = """
            SELECT DISTINCT contratto
            FROM employees
            WHERE contratto IS NOT NULL
              AND contratto != ''
              AND active = 1
            ORDER BY contratto
        """
        results = self._execute_query(query)
        return [row[0] for row in results]

    # === QUALIFICATIONS ===

    @lru_cache(maxsize=1)
    def get_qualifications(self) -> List[str]:
        """
        Get all unique qualifications from employees.

        Returns:
            Sorted list of qualifica values
        """
        # Hardcoded for consistency (5 standard values)
        return [
            "DIRIGENTE (D)",
            "QUADRO (F)",
            "GIORNALISTA (G)",
            "IMPIEGATO (I)",
            "PRATICANTE (T)"
        ]

    # === AREAS (Organizational Level 1) ===

    @lru_cache(maxsize=1)
    def get_areas(self) -> List[str]:
        """
        Get all unique areas (level 1) from employees.

        Returns:
            Sorted list of area names
        """
        query = """
            SELECT DISTINCT area
            FROM employees
            WHERE area IS NOT NULL
              AND area != ''
              AND active = 1
            ORDER BY area
        """
        results = self._execute_query(query)
        return [row[0] for row in results]

    # === SUBAREAS (Organizational Level 2) ===

    def get_subareas(self, area: Optional[str] = None) -> List[str]:
        """
        Get all unique subareas, optionally filtered by area.

        Args:
            area: Optional area filter to get subareas for specific area

        Returns:
            Sorted list of sottoarea names
        """
        if area:
            query = """
                SELECT DISTINCT sottoarea
                FROM employees
                WHERE sottoarea IS NOT NULL
                  AND sottoarea != ''
                  AND area = ?
                  AND active = 1
                ORDER BY sottoarea
            """
            results = self._execute_query(query, (area,))
        else:
            query = """
                SELECT DISTINCT sottoarea
                FROM employees
                WHERE sottoarea IS NOT NULL
                  AND sottoarea != ''
                  AND active = 1
                ORDER BY sottoarea
            """
            results = self._execute_query(query)

        return [row[0] for row in results]

    # === OFFICES (Sedes) ===

    @lru_cache(maxsize=1)
    def get_offices(self) -> List[str]:
        """
        Get all unique offices/locations from employees.

        Returns:
            Sorted list of sede names
        """
        query = """
            SELECT DISTINCT sede
            FROM employees
            WHERE sede IS NOT NULL
              AND sede != ''
              AND active = 1
            ORDER BY sede
        """
        results = self._execute_query(query)
        return [row[0] for row in results]

    # === SGSL ROLES ===

    def get_sgsl_roles(self) -> List[str]:
        """Get SGSL role options"""
        return [
            "Nessuno",
            "RSPP",
            "RLS",
            "Coordinatore HSE",
            "Preposto",
            "Medico Competente"
        ]

    # === GDPR ROLES ===

    def get_gdpr_roles(self) -> List[str]:
        """Get GDPR role options"""
        return [
            "Nessuno",
            "DPO",
            "Delegato Privacy",
            "Titolare Trattamento"
        ]

    # === HIERARCHY TYPES ===

    @lru_cache(maxsize=1)
    def get_hierarchy_types(self) -> List[Dict[str, any]]:
        """
        Get all hierarchy types.

        Returns:
            List of dicts with hierarchy_type_id, type_code, type_name
        """
        query = """
            SELECT hierarchy_type_id, type_code, type_name, description, color_hex
            FROM hierarchy_types
            WHERE active = 1
            ORDER BY type_code
        """
        results = self._execute_query(query)
        return [
            {
                'hierarchy_type_id': row[0],
                'type_code': row[1],
                'type_name': row[2],
                'description': row[3],
                'color_hex': row[4]
            }
            for row in results
        ]

    # === ROLE CATEGORIES ===

    def get_role_categories(self) -> List[str]:
        """Get role category options"""
        return ["TNS", "SGSL", "GDPR", "AFC", "HR", "OTHER"]

    # === TNS ROLES ===

    @lru_cache(maxsize=1)
    def get_tns_roles(self) -> List[Dict[str, any]]:
        """
        Get all TNS role definitions.

        Returns:
            List of dicts with role_id, role_code, role_name
        """
        query = """
            SELECT role_id, role_code, role_name, icon
            FROM role_definitions
            WHERE role_category = 'TNS'
              AND active = 1
            ORDER BY role_name
        """
        results = self._execute_query(query)
        return [
            {
                'role_id': row[0],
                'role_code': row[1],
                'role_name': row[2],
                'icon': row[3]
            }
            for row in results
        ]

    # === SEARCH EMPLOYEES ===

    def search_employees(
        self,
        query: str,
        limit: int = 20,
        active_only: bool = True
    ) -> List[Dict[str, any]]:
        """
        Search employees by name or codice fiscale for autocomplete.

        Args:
            query: Search query (partial name or CF)
            limit: Maximum results to return
            active_only: Only return active employees

        Returns:
            List of matching employees with basic info
        """
        query_pattern = f"%{query}%"

        sql = """
            SELECT
                employee_id,
                tx_cod_fiscale,
                codice,
                titolare,
                qualifica,
                area
            FROM employees
            WHERE (
                titolare LIKE ?
                OR tx_cod_fiscale LIKE ?
                OR codice LIKE ?
            )
        """

        if active_only:
            sql += " AND active = 1"

        sql += f" ORDER BY titolare LIMIT {limit}"

        results = self._execute_query(sql, (query_pattern, query_pattern, query_pattern))

        return [
            {
                'employee_id': row[0],
                'tx_cod_fiscale': row[1],
                'codice': row[2],
                'titolare': row[3],
                'qualifica': row[4],
                'area': row[5]
            }
            for row in results
        ]

    # === SEARCH ORG UNITS ===

    def search_org_units(
        self,
        query: str,
        limit: int = 20,
        active_only: bool = True
    ) -> List[Dict[str, any]]:
        """
        Search organizational units by code or description.

        Args:
            query: Search query (partial code or description)
            limit: Maximum results to return
            active_only: Only return active org units

        Returns:
            List of matching org units
        """
        query_pattern = f"%{query}%"

        sql = """
            SELECT
                org_unit_id,
                codice,
                descrizione,
                livello,
                cdccosto
            FROM org_units
            WHERE (
                descrizione LIKE ?
                OR codice LIKE ?
            )
        """

        if active_only:
            sql += " AND active = 1"

        sql += f" ORDER BY descrizione LIMIT {limit}"

        results = self._execute_query(sql, (query_pattern, query_pattern))

        return [
            {
                'org_unit_id': row[0],
                'codice': row[1],
                'descrizione': row[2],
                'livello': row[3],
                'cdccosto': row[4]
            }
            for row in results
        ]

    # === CACHE MANAGEMENT ===

    def clear_cache(self):
        """Clear all cached lookup values"""
        self.get_companies.cache_clear()
        self.get_contract_types.cache_clear()
        self.get_qualifications.cache_clear()
        self.get_areas.cache_clear()
        self.get_offices.cache_clear()
        self.get_hierarchy_types.cache_clear()
        self.get_tns_roles.cache_clear()


# Singleton instance
_lookup_service_instance = None


def get_lookup_service() -> LookupService:
    """Get singleton instance of LookupService"""
    global _lookup_service_instance
    if _lookup_service_instance is None:
        _lookup_service_instance = LookupService()
    return _lookup_service_instance
