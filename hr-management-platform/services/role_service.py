"""
Role Service

Business logic for managing role assignments (TNS, SGSL, GDPR roles).
Supports temporal validity and scope-based assignments.
"""
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import date, datetime

import config
from models.role import (
    RoleDefinition, RoleAssignment, RoleAssignmentCreate,
    RoleAssignmentListItem, EmployeeRoles, RoleMatrix,
    RoleCoverageReport
)


class RoleService:
    """Service for managing role assignments"""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or config.DB_PATH

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    # === ROLE DEFINITIONS ===

    def get_role_definitions(
        self,
        category: Optional[str] = None,
        active_only: bool = True
    ) -> List[RoleDefinition]:
        """
        Get role definitions.

        Args:
            category: Filter by category (TNS, SGSL, GDPR, etc.)
            active_only: Only active roles

        Returns:
            List of RoleDefinition
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            query = "SELECT * FROM role_definitions WHERE 1=1"
            params = []

            if active_only:
                query += " AND active = 1"

            if category:
                query += " AND role_category = ?"
                params.append(category)

            query += " ORDER BY role_category, role_name"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [RoleDefinition(**dict(row)) for row in rows]

        finally:
            conn.close()

    def get_role_by_code(self, role_code: str) -> Optional[RoleDefinition]:
        """Get role definition by code"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT * FROM role_definitions
                WHERE role_code = ? AND active = 1
            """, (role_code,))

            row = cursor.fetchone()
            if row:
                return RoleDefinition(**dict(row))
            return None

        finally:
            conn.close()

    # === ROLE ASSIGNMENTS ===

    def assign_role(
        self,
        employee_id: int,
        role_code: str,
        effective_date: date,
        end_date: Optional[date] = None,
        org_unit_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> int:
        """
        Assign role to employee.

        Args:
            employee_id: Employee ID
            role_code: Role code (APPROVATORE, RSPP, etc.)
            effective_date: Start date
            end_date: Optional end date
            org_unit_id: Optional org unit scope
            notes: Optional notes

        Returns:
            assignment_id

        Raises:
            ValueError: If role invalid or assignment exists
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Get role_id
            cursor.execute(
                "SELECT role_id, requires_scope FROM role_definitions WHERE role_code = ?",
                (role_code,)
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Invalid role code: {role_code}")

            role_id = row[0]
            requires_scope = row[1]

            # Validate scope requirement
            if requires_scope and not org_unit_id:
                raise ValueError(f"Role {role_code} requires org_unit_id")

            # Check if assignment already exists
            cursor.execute("""
                SELECT assignment_id FROM role_assignments
                WHERE employee_id = ?
                  AND role_id = ?
                  AND org_unit_id IS ?
                  AND effective_date = ?
            """, (employee_id, role_id, org_unit_id, effective_date))

            if cursor.fetchone():
                raise ValueError("Role assignment already exists")

            # Insert assignment
            cursor.execute("""
                INSERT INTO role_assignments (
                    employee_id, role_id, org_unit_id,
                    effective_date, end_date, notes,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                employee_id, role_id, org_unit_id,
                effective_date, end_date, notes,
                datetime.now(), datetime.now()
            ))

            assignment_id = cursor.lastrowid
            conn.commit()
            return assignment_id

        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def remove_role(
        self,
        employee_id: int,
        role_code: str,
        end_date: date,
        org_unit_id: Optional[int] = None
    ) -> bool:
        """
        Remove role from employee by setting end_date.

        Args:
            employee_id: Employee ID
            role_code: Role code
            end_date: End date
            org_unit_id: Optional org unit scope

        Returns:
            True if successful
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Get role_id
            cursor.execute(
                "SELECT role_id FROM role_definitions WHERE role_code = ?",
                (role_code,)
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Invalid role code: {role_code}")

            role_id = row[0]

            # Update end_date for active assignments
            cursor.execute("""
                UPDATE role_assignments
                SET end_date = ?, updated_at = ?
                WHERE employee_id = ?
                  AND role_id = ?
                  AND org_unit_id IS ?
                  AND (end_date IS NULL OR end_date > ?)
            """, (end_date, datetime.now(), employee_id, role_id, org_unit_id, end_date))

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_employee_roles(
        self,
        employee_id: int,
        as_of_date: Optional[date] = None,
        category: Optional[str] = None
    ) -> List[RoleAssignmentListItem]:
        """
        Get all role assignments for an employee.

        Args:
            employee_id: Employee ID
            as_of_date: Optional date to check (default: today)
            category: Optional category filter (TNS, SGSL, GDPR)

        Returns:
            List of RoleAssignmentListItem
        """
        if as_of_date is None:
            as_of_date = date.today()

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            query = """
                SELECT
                    ra.assignment_id,
                    ra.employee_id,
                    e.titolare as employee_name,
                    ra.role_id,
                    rd.role_code,
                    rd.role_name,
                    rd.role_category,
                    ra.org_unit_id,
                    ou.descrizione as org_unit_name,
                    ra.effective_date,
                    ra.end_date,
                    (ra.end_date IS NULL OR ra.end_date > ?) as is_active
                FROM role_assignments ra
                JOIN employees e ON e.employee_id = ra.employee_id
                JOIN role_definitions rd ON rd.role_id = ra.role_id
                LEFT JOIN org_units ou ON ou.org_unit_id = ra.org_unit_id
                WHERE ra.employee_id = ?
                  AND ra.effective_date <= ?
                  AND (ra.end_date IS NULL OR ra.end_date > ?)
            """
            params = [as_of_date, employee_id, as_of_date, as_of_date]

            if category:
                query += " AND rd.role_category = ?"
                params.append(category)

            query += " ORDER BY rd.role_category, rd.role_name"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [RoleAssignmentListItem(**dict(row)) for row in rows]

        finally:
            conn.close()

    def get_employee_roles_summary(
        self,
        employee_id: int,
        as_of_date: Optional[date] = None
    ) -> EmployeeRoles:
        """
        Get employee roles summary with boolean flags.

        Args:
            employee_id: Employee ID
            as_of_date: Optional date to check (default: today)

        Returns:
            EmployeeRoles model with boolean flags for each role
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Get employee info
            cursor.execute("""
                SELECT employee_id, titolare, tx_cod_fiscale
                FROM employees
                WHERE employee_id = ?
            """, (employee_id,))

            emp_row = cursor.fetchone()
            if not emp_row:
                raise ValueError(f"Employee {employee_id} not found")

            # Get all role assignments
            assignments = self.get_employee_roles(employee_id, as_of_date)

            # Build EmployeeRoles model
            result = EmployeeRoles(
                employee_id=emp_row['employee_id'],
                employee_name=emp_row['titolare'],
                tx_cod_fiscale=emp_row['tx_cod_fiscale'],
                role_assignments=assignments
            )

            # Set boolean flags for specific roles
            for assignment in assignments:
                if not assignment.is_active:
                    continue

                role_code = assignment.role_code.upper()

                # TNS roles
                if role_code == 'VIAGGIATORE':
                    result.viaggiatore = True
                elif role_code == 'APPROVATORE':
                    result.approvatore = True
                elif role_code == 'CONTROLLORE':
                    result.controllore = True
                elif role_code == 'CASSIERE':
                    result.cassiere = True
                elif role_code == 'SEGRETARIO':
                    result.segretario = True
                elif role_code == 'VISUALIZZATORI':
                    result.visualizzatori = True
                elif role_code == 'AMMINISTRAZIONE':
                    result.amministrazione = True

                # SGSL roles
                elif role_code == 'RSPP':
                    result.rspp = True
                elif role_code == 'RLS':
                    result.rls = True
                elif role_code == 'COORD_HSE':
                    result.coord_hse = True

                # GDPR roles
                elif role_code == 'DPO':
                    result.dpo = True
                elif role_code == 'DELEGATO_PRIVACY':
                    result.delegato_privacy = True

                # AFC/HR roles
                elif role_code == 'RUOLI_AFC':
                    result.ruoli_afc = True
                elif role_code == 'RUOLI_HR':
                    result.ruoli_hr = True

            return result

        finally:
            conn.close()

    def get_employees_with_role(
        self,
        role_code: str,
        org_unit_id: Optional[int] = None,
        as_of_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all employees with a specific role.

        Args:
            role_code: Role code
            org_unit_id: Optional org unit filter
            as_of_date: Optional date to check (default: today)

        Returns:
            List of employee dicts
        """
        if as_of_date is None:
            as_of_date = date.today()

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Get role_id
            cursor.execute(
                "SELECT role_id FROM role_definitions WHERE role_code = ?",
                (role_code,)
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Invalid role code: {role_code}")

            role_id = row[0]

            query = """
                SELECT DISTINCT
                    e.employee_id,
                    e.tx_cod_fiscale,
                    e.titolare,
                    e.qualifica,
                    e.area,
                    ou.descrizione as org_unit_name
                FROM role_assignments ra
                JOIN employees e ON e.employee_id = ra.employee_id
                LEFT JOIN org_units ou ON ou.org_unit_id = ra.org_unit_id
                WHERE ra.role_id = ?
                  AND ra.effective_date <= ?
                  AND (ra.end_date IS NULL OR ra.end_date > ?)
                  AND e.active = 1
            """
            params = [role_id, as_of_date, as_of_date]

            if org_unit_id:
                query += " AND ra.org_unit_id = ?"
                params.append(org_unit_id)

            query += " ORDER BY e.titolare"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

        finally:
            conn.close()

    # === ROLE MATRIX ===

    def get_role_matrix(
        self,
        category: str,
        org_unit_id: Optional[int] = None,
        as_of_date: Optional[date] = None
    ) -> RoleMatrix:
        """
        Get role matrix for a specific category.

        Shows employees × roles matrix with boolean flags.

        Args:
            category: Role category (TNS, SGSL, GDPR)
            org_unit_id: Optional org unit filter
            as_of_date: Optional date to check (default: today)

        Returns:
            RoleMatrix model
        """
        if as_of_date is None:
            as_of_date = date.today()

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Get roles for category
            roles = self.get_role_definitions(category=category)

            # Get employees (optionally filtered by org_unit)
            if org_unit_id:
                # Get employees in org unit
                cursor.execute("""
                    SELECT DISTINCT e.employee_id
                    FROM employees e
                    JOIN hierarchy_assignments ha ON ha.employee_id = e.employee_id
                    WHERE ha.org_unit_id = ?
                      AND e.active = 1
                      AND ha.effective_date <= ?
                      AND (ha.end_date IS NULL OR ha.end_date > ?)
                """, (org_unit_id, as_of_date, as_of_date))

                employee_ids = [row[0] for row in cursor.fetchall()]
            else:
                # Get all active employees
                cursor.execute("SELECT employee_id FROM employees WHERE active = 1")
                employee_ids = [row[0] for row in cursor.fetchall()]

            # Get role summaries for each employee
            employees = []
            for emp_id in employee_ids:
                emp_roles = self.get_employee_roles_summary(emp_id, as_of_date)
                employees.append(emp_roles)

            return RoleMatrix(
                category=category,
                roles=roles,
                employees=employees
            )

        finally:
            conn.close()

    # === VALIDATION ===

    def validate_role_coverage(
        self,
        org_unit_id: int,
        hierarchy_type: str = "TNS"
    ) -> RoleCoverageReport:
        """
        Validate that org unit has required role coverage.

        For TNS: Must have at least one APPROVATORE.

        Args:
            org_unit_id: Org unit ID
            hierarchy_type: Hierarchy type (default: TNS)

        Returns:
            RoleCoverageReport
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Get org unit info
            cursor.execute("""
                SELECT org_unit_id, descrizione
                FROM org_units
                WHERE org_unit_id = ?
            """, (org_unit_id,))

            org_row = cursor.fetchone()
            if not org_row:
                raise ValueError(f"Org unit {org_unit_id} not found")

            report = RoleCoverageReport(
                org_unit_id=org_row['org_unit_id'],
                org_unit_name=org_row['descrizione'],
                required_roles=[],
                missing_roles=[]
            )

            # Define required roles by hierarchy type
            if hierarchy_type == "TNS":
                report.required_roles = ['APPROVATORE']
            elif hierarchy_type == "SGSL":
                report.required_roles = ['RSPP']
            elif hierarchy_type == "GDPR":
                report.required_roles = ['DPO']

            # Check if each required role is assigned
            today = date.today()

            for role_code in report.required_roles:
                employees = self.get_employees_with_role(
                    role_code=role_code,
                    org_unit_id=org_unit_id,
                    as_of_date=today
                )

                if not employees:
                    report.missing_roles.append(role_code)

            report.has_full_coverage = len(report.missing_roles) == 0

            return report

        finally:
            conn.close()


# Singleton instance
_role_service_instance = None


def get_role_service() -> RoleService:
    """Get singleton instance of RoleService"""
    global _role_service_instance
    if _role_service_instance is None:
        _role_service_instance = RoleService()
    return _role_service_instance
