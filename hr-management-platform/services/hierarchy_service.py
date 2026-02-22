"""
Hierarchy Service

Business logic for managing 5 organizational hierarchies (HR, TNS, SGSL, GDPR, IT_DIR).
"""
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import date, datetime

import config
from models.hierarchy import (
    HierarchyType, HierarchyAssignment, HierarchyAssignmentCreate,
    HierarchyAssignmentListItem, EmployeeHierarchies, HierarchyTreeNode,
    ApprovalChain, HierarchyStats
)


class HierarchyService:
    """Service for managing multiple organizational hierarchies"""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or config.DB_PATH

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    # === HIERARCHY TYPES ===

    def get_hierarchy_types(self) -> List[HierarchyType]:
        """Get all hierarchy types"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT * FROM hierarchy_types
                WHERE active = 1
                ORDER BY type_code
            """)
            rows = cursor.fetchall()
            return [HierarchyType(**dict(row)) for row in rows]

        finally:
            conn.close()

    def get_hierarchy_type_by_code(self, type_code: str) -> Optional[HierarchyType]:
        """Get hierarchy type by code (HR, TNS, etc.)"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT * FROM hierarchy_types
                WHERE type_code = ? AND active = 1
            """, (type_code,))
            row = cursor.fetchone()

            if row:
                return HierarchyType(**dict(row))
            return None

        finally:
            conn.close()

    # === ASSIGNMENTS ===

    def assign_employee_to_hierarchy(
        self,
        employee_id: int,
        org_unit_id: int,
        hierarchy_type: str,
        effective_date: date,
        end_date: Optional[date] = None,
        is_primary: bool = False
    ) -> int:
        """
        Assign employee to org unit in specific hierarchy.

        Args:
            employee_id: Employee ID
            org_unit_id: Org unit ID
            hierarchy_type: Type code (HR, TNS, SGSL, GDPR, IT_DIR)
            effective_date: Start date
            end_date: Optional end date
            is_primary: Is this the primary assignment for this hierarchy

        Returns:
            assignment_id

        Raises:
            ValueError: If hierarchy type invalid or assignment exists
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Get hierarchy_type_id
            cursor.execute(
                "SELECT hierarchy_type_id FROM hierarchy_types WHERE type_code = ?",
                (hierarchy_type,)
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Invalid hierarchy type: {hierarchy_type}")

            hierarchy_type_id = row[0]

            # Check if assignment already exists
            cursor.execute("""
                SELECT assignment_id FROM hierarchy_assignments
                WHERE employee_id = ?
                  AND hierarchy_type_id = ?
                  AND org_unit_id = ?
                  AND effective_date = ?
            """, (employee_id, hierarchy_type_id, org_unit_id, effective_date))

            if cursor.fetchone():
                raise ValueError("Assignment already exists")

            # If is_primary, remove primary flag from other assignments
            if is_primary:
                cursor.execute("""
                    UPDATE hierarchy_assignments
                    SET is_primary = 0
                    WHERE employee_id = ?
                      AND hierarchy_type_id = ?
                      AND (end_date IS NULL OR end_date > ?)
                """, (employee_id, hierarchy_type_id, effective_date))

            # Insert assignment
            cursor.execute("""
                INSERT INTO hierarchy_assignments (
                    employee_id, org_unit_id, hierarchy_type_id,
                    effective_date, end_date, is_primary,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                employee_id, org_unit_id, hierarchy_type_id,
                effective_date, end_date, is_primary,
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

    def get_employee_hierarchies(
        self,
        employee_id: int,
        as_of_date: Optional[date] = None
    ) -> EmployeeHierarchies:
        """
        Get all hierarchy assignments for an employee.

        Args:
            employee_id: Employee ID
            as_of_date: Optional date to check (default: today)

        Returns:
            EmployeeHierarchies model with assignments by type
        """
        if as_of_date is None:
            as_of_date = date.today()

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

            # Get all active assignments
            cursor.execute("""
                SELECT
                    ha.assignment_id,
                    ha.employee_id,
                    e.titolare as employee_name,
                    ha.org_unit_id,
                    ou.descrizione as org_unit_name,
                    ha.hierarchy_type_id,
                    ht.type_code as hierarchy_type_code,
                    ht.type_name as hierarchy_type_name,
                    ha.effective_date,
                    ha.end_date,
                    ha.is_primary,
                    (ha.end_date IS NULL OR ha.end_date > ?) as is_active
                FROM hierarchy_assignments ha
                JOIN employees e ON e.employee_id = ha.employee_id
                JOIN org_units ou ON ou.org_unit_id = ha.org_unit_id
                JOIN hierarchy_types ht ON ht.hierarchy_type_id = ha.hierarchy_type_id
                WHERE ha.employee_id = ?
                  AND ha.effective_date <= ?
                  AND (ha.end_date IS NULL OR ha.end_date > ?)
                ORDER BY ht.type_code, ha.effective_date DESC
            """, (as_of_date, employee_id, as_of_date, as_of_date))

            rows = cursor.fetchall()

            # Build EmployeeHierarchies model
            result = EmployeeHierarchies(
                employee_id=emp_row['employee_id'],
                employee_name=emp_row['titolare'],
                tx_cod_fiscale=emp_row['tx_cod_fiscale']
            )

            for row in rows:
                assignment = HierarchyAssignmentListItem(**dict(row))
                result.all_assignments.append(assignment)

                # Assign to specific hierarchy field
                type_code = row['hierarchy_type_code']
                if type_code == 'HR':
                    result.hr_hierarchy = assignment
                elif type_code == 'TNS':
                    result.tns_hierarchy = assignment
                elif type_code == 'SGSL':
                    result.sgsl_hierarchy = assignment
                elif type_code == 'GDPR':
                    result.gdpr_hierarchy = assignment
                elif type_code == 'IT_DIR':
                    result.it_hierarchy = assignment

            return result

        finally:
            conn.close()

    def get_org_unit_employees(
        self,
        org_unit_id: int,
        hierarchy_type: str,
        recursive: bool = False,
        as_of_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all employees assigned to an org unit in a specific hierarchy.

        Args:
            org_unit_id: Org unit ID
            hierarchy_type: Type code (HR, TNS, etc.)
            recursive: Include employees from child units
            as_of_date: Optional date to check (default: today)

        Returns:
            List of employee dicts
        """
        if as_of_date is None:
            as_of_date = date.today()

        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Get hierarchy_type_id
            cursor.execute(
                "SELECT hierarchy_type_id FROM hierarchy_types WHERE type_code = ?",
                (hierarchy_type,)
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Invalid hierarchy type: {hierarchy_type}")

            hierarchy_type_id = row[0]

            if recursive:
                # Get all child org units
                org_unit_ids = self._get_child_org_units(org_unit_id)
                org_unit_ids.append(org_unit_id)

                placeholders = ','.join('?' * len(org_unit_ids))
                query = f"""
                    SELECT DISTINCT
                        e.employee_id,
                        e.tx_cod_fiscale,
                        e.titolare,
                        e.qualifica,
                        e.area,
                        ou.descrizione as org_unit_name
                    FROM hierarchy_assignments ha
                    JOIN employees e ON e.employee_id = ha.employee_id
                    JOIN org_units ou ON ou.org_unit_id = ha.org_unit_id
                    WHERE ha.org_unit_id IN ({placeholders})
                      AND ha.hierarchy_type_id = ?
                      AND ha.effective_date <= ?
                      AND (ha.end_date IS NULL OR ha.end_date > ?)
                      AND e.active = 1
                    ORDER BY e.titolare
                """
                params = org_unit_ids + [hierarchy_type_id, as_of_date, as_of_date]

            else:
                query = """
                    SELECT DISTINCT
                        e.employee_id,
                        e.tx_cod_fiscale,
                        e.titolare,
                        e.qualifica,
                        e.area,
                        ou.descrizione as org_unit_name
                    FROM hierarchy_assignments ha
                    JOIN employees e ON e.employee_id = ha.employee_id
                    JOIN org_units ou ON ou.org_unit_id = ha.org_unit_id
                    WHERE ha.org_unit_id = ?
                      AND ha.hierarchy_type_id = ?
                      AND ha.effective_date <= ?
                      AND (ha.end_date IS NULL OR ha.end_date > ?)
                      AND e.active = 1
                    ORDER BY e.titolare
                """
                params = [org_unit_id, hierarchy_type_id, as_of_date, as_of_date]

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

        finally:
            conn.close()

    def _get_child_org_units(self, org_unit_id: int) -> List[int]:
        """Recursively get all child org unit IDs"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT org_unit_id
                FROM org_units
                WHERE parent_org_unit_id = ?
            """, (org_unit_id,))

            child_ids = [row[0] for row in cursor.fetchall()]

            # Recursively get grandchildren
            all_children = child_ids.copy()
            for child_id in child_ids:
                all_children.extend(self._get_child_org_units(child_id))

            return all_children

        finally:
            conn.close()

    # === APPROVAL CHAIN (TNS) ===

    def get_approval_chain(
        self,
        employee_id: int,
        hierarchy_type: str = "TNS"
    ) -> ApprovalChain:
        """
        Get approval chain for employee in TNS hierarchy.

        Walks up the org hierarchy to find approvers.

        Args:
            employee_id: Employee ID
            hierarchy_type: Hierarchy type (default: TNS)

        Returns:
            ApprovalChain model
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

            chain = ApprovalChain(
                employee_id=emp_row['employee_id'],
                employee_name=emp_row['titolare'],
                chain=[]
            )

            # Get employee's org unit in TNS hierarchy
            hierarchies = self.get_employee_hierarchies(employee_id)
            if hierarchy_type == "TNS" and hierarchies.tns_hierarchy:
                org_unit_id = hierarchies.tns_hierarchy.org_unit_id

                # Walk up the org tree to find approvers
                level = 0
                while org_unit_id and level < 10:  # Max 10 levels to prevent infinite loop
                    # Get org unit responsible
                    cursor.execute("""
                        SELECT
                            ou.responsible_employee_id,
                            e.titolare as responsible_name
                        FROM org_units ou
                        LEFT JOIN employees e ON e.employee_id = ou.responsible_employee_id
                        WHERE ou.org_unit_id = ?
                    """, (org_unit_id,))

                    org_row = cursor.fetchone()
                    if org_row and org_row['responsible_employee_id']:
                        chain.chain.append({
                            'employee_id': org_row['responsible_employee_id'],
                            'name': org_row['responsible_name'],
                            'role': 'Approvatore',
                            'level': level
                        })

                        if level == 0:
                            chain.top_approver_id = org_row['responsible_employee_id']
                            chain.top_approver_name = org_row['responsible_name']

                    # Move up to parent org unit
                    cursor.execute("""
                        SELECT parent_org_unit_id
                        FROM org_units
                        WHERE org_unit_id = ?
                    """, (org_unit_id,))

                    parent_row = cursor.fetchone()
                    if parent_row and parent_row['parent_org_unit_id']:
                        org_unit_id = parent_row['parent_org_unit_id']
                        level += 1
                    else:
                        break

            return chain

        finally:
            conn.close()

    # === STATISTICS ===

    def get_hierarchy_stats(self, hierarchy_type: str) -> HierarchyStats:
        """Get statistics for a specific hierarchy type"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Get hierarchy_type_id
            cursor.execute("""
                SELECT hierarchy_type_id, type_code, type_name
                FROM hierarchy_types
                WHERE type_code = ?
            """, (hierarchy_type,))

            ht_row = cursor.fetchone()
            if not ht_row:
                raise ValueError(f"Invalid hierarchy type: {hierarchy_type}")

            hierarchy_type_id = ht_row['hierarchy_type_id']

            stats = HierarchyStats(
                hierarchy_type_code=ht_row['type_code'],
                hierarchy_type_name=ht_row['type_name']
            )

            # Total org units
            cursor.execute("SELECT COUNT(*) FROM org_units WHERE active = 1")
            stats.total_org_units = cursor.fetchone()[0]

            # Total employees assigned
            cursor.execute("""
                SELECT COUNT(DISTINCT employee_id)
                FROM hierarchy_assignments
                WHERE hierarchy_type_id = ?
                  AND (end_date IS NULL OR end_date > date('now'))
            """, (hierarchy_type_id,))
            stats.total_employees_assigned = cursor.fetchone()[0]

            # Employees without assignment
            cursor.execute("""
                SELECT COUNT(*)
                FROM employees e
                WHERE e.active = 1
                  AND NOT EXISTS (
                      SELECT 1
                      FROM hierarchy_assignments ha
                      WHERE ha.employee_id = e.employee_id
                        AND ha.hierarchy_type_id = ?
                        AND (ha.end_date IS NULL OR ha.end_date > date('now'))
                  )
            """, (hierarchy_type_id,))
            stats.employees_without_assignment = cursor.fetchone()[0]

            # Org units without responsible
            cursor.execute("""
                SELECT COUNT(*)
                FROM org_units
                WHERE active = 1
                  AND responsible_employee_id IS NULL
            """)
            stats.org_units_without_responsible = cursor.fetchone()[0]

            # Coverage percentage
            cursor.execute("SELECT COUNT(*) FROM employees WHERE active = 1")
            total_active = cursor.fetchone()[0]

            if total_active > 0:
                stats.coverage_percentage = (stats.total_employees_assigned / total_active) * 100
            else:
                stats.coverage_percentage = 0.0

            return stats

        finally:
            conn.close()


# Singleton instance
_hierarchy_service_instance = None


def get_hierarchy_service() -> HierarchyService:
    """Get singleton instance of HierarchyService"""
    global _hierarchy_service_instance
    if _hierarchy_service_instance is None:
        _hierarchy_service_instance = HierarchyService()
    return _hierarchy_service_instance
