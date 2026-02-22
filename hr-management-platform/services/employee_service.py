"""
Employee Service

Business logic for managing employees in the normalized DB_ORG schema.
Provides CRUD operations and complex queries.
"""
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal

import config
from models.employee import (
    Employee, EmployeeCreate, EmployeeUpdate,
    EmployeeListItem, EmployeeSearchResult
)


class EmployeeService:
    """Service for employee management operations"""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or config.DB_PATH

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _log_audit(
        self,
        conn: sqlite3.Connection,
        table_name: str,
        record_id: int,
        action: str,
        field_name: str = None,
        old_value: str = None,
        new_value: str = None,
        change_severity: str = "MEDIUM"
    ):
        """Log change to audit_log"""
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_log
            (table_name, record_id, action, field_name, old_value, new_value, change_severity, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (table_name, record_id, action, field_name, old_value, new_value, change_severity, datetime.now()))

    # === CREATE ===

    def create_employee(self, employee: EmployeeCreate) -> int:
        """
        Create a new employee.

        Args:
            employee: EmployeeCreate model with employee data

        Returns:
            employee_id of created employee

        Raises:
            ValueError: If employee already exists or validation fails
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Check if employee already exists
            cursor.execute(
                "SELECT employee_id FROM employees WHERE tx_cod_fiscale = ?",
                (employee.tx_cod_fiscale,)
            )
            if cursor.fetchone():
                raise ValueError(f"Employee with CF {employee.tx_cod_fiscale} already exists")

            # Check if codice already exists
            cursor.execute(
                "SELECT employee_id FROM employees WHERE codice = ?",
                (employee.codice,)
            )
            if cursor.fetchone():
                raise ValueError(f"Employee with codice {employee.codice} already exists")

            # Insert employee
            cursor.execute("""
                INSERT INTO employees (
                    tx_cod_fiscale, codice, titolare, company_id,
                    cognome, nome, area, sottoarea, sede,
                    contratto, qualifica, ral, data_assunzione, email,
                    active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """, (
                employee.tx_cod_fiscale.upper(),
                employee.codice,
                employee.titolare,
                employee.company_id,
                employee.cognome,
                employee.nome,
                employee.area,
                employee.sottoarea,
                employee.sede,
                employee.contratto,
                employee.qualifica,
                float(employee.ral) if employee.ral else None,
                employee.data_assunzione,
                employee.email,
                datetime.now(),
                datetime.now()
            ))

            employee_id = cursor.lastrowid

            # Log audit
            self._log_audit(
                conn, "employees", employee_id, "INSERT",
                change_severity="HIGH"
            )

            conn.commit()
            return employee_id

        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    # === READ ===

    def get_employee(self, employee_id: int) -> Optional[Employee]:
        """
        Get employee by ID.

        Args:
            employee_id: Employee ID

        Returns:
            Employee model or None if not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM employees WHERE employee_id = ?", (employee_id,))
            row = cursor.fetchone()

            if row:
                return Employee(**dict(row))
            return None

        finally:
            conn.close()

    def get_employee_by_cf(self, tx_cod_fiscale: str) -> Optional[Employee]:
        """Get employee by Codice Fiscale"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "SELECT * FROM employees WHERE tx_cod_fiscale = ?",
                (tx_cod_fiscale.upper(),)
            )
            row = cursor.fetchone()

            if row:
                return Employee(**dict(row))
            return None

        finally:
            conn.close()

    def list_employees(
        self,
        active_only: bool = True,
        company_id: Optional[int] = None,
        area: Optional[str] = None,
        sede: Optional[str] = None,
        qualifica: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> List[EmployeeListItem]:
        """
        List employees with filters.

        Args:
            active_only: Only return active employees
            company_id: Filter by company
            area: Filter by area
            sede: Filter by sede
            qualifica: Filter by qualifica
            limit: Maximum results
            offset: Offset for pagination

        Returns:
            List of EmployeeListItem
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            query = """
                SELECT
                    employee_id, tx_cod_fiscale, codice, titolare,
                    cognome, nome, qualifica, area, sede, ral, active
                FROM employees
                WHERE 1=1
            """
            params = []

            if active_only:
                query += " AND active = 1"

            if company_id:
                query += " AND company_id = ?"
                params.append(company_id)

            if area:
                query += " AND area = ?"
                params.append(area)

            if sede:
                query += " AND sede = ?"
                params.append(sede)

            if qualifica:
                query += " AND qualifica = ?"
                params.append(qualifica)

            query += " ORDER BY titolare LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [EmployeeListItem(**dict(row)) for row in rows]

        finally:
            conn.close()

    def count_employees(
        self,
        active_only: bool = True,
        company_id: Optional[int] = None,
        area: Optional[str] = None
    ) -> int:
        """Count employees with filters"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            query = "SELECT COUNT(*) FROM employees WHERE 1=1"
            params = []

            if active_only:
                query += " AND active = 1"

            if company_id:
                query += " AND company_id = ?"
                params.append(company_id)

            if area:
                query += " AND area = ?"
                params.append(area)

            cursor.execute(query, params)
            return cursor.fetchone()[0]

        finally:
            conn.close()

    def search_employees(
        self,
        query: str,
        active_only: bool = True,
        limit: int = 50
    ) -> List[EmployeeSearchResult]:
        """
        Search employees by name, CF, or codice.

        Args:
            query: Search query
            active_only: Only active employees
            limit: Max results

        Returns:
            List of EmployeeSearchResult with match info
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            query_pattern = f"%{query}%"

            sql = """
                SELECT
                    employee_id, tx_cod_fiscale, codice, titolare,
                    cognome, nome, qualifica, area, sede, ral, active
                FROM employees
                WHERE (
                    titolare LIKE ?
                    OR cognome LIKE ?
                    OR nome LIKE ?
                    OR tx_cod_fiscale LIKE ?
                    OR codice LIKE ?
                )
            """

            if active_only:
                sql += " AND active = 1"

            sql += " ORDER BY titolare LIMIT ?"

            cursor.execute(sql, (query_pattern,) * 5 + (limit,))
            rows = cursor.fetchall()

            results = []
            for row in rows:
                result = EmployeeSearchResult(**dict(row))

                # Determine which field matched
                if query.upper() in (row['titolare'] or '').upper():
                    result.match_field = 'titolare'
                    result.match_value = row['titolare']
                elif query.upper() in (row['tx_cod_fiscale'] or '').upper():
                    result.match_field = 'tx_cod_fiscale'
                    result.match_value = row['tx_cod_fiscale']

                results.append(result)

            return results

        finally:
            conn.close()

    # === UPDATE ===

    def update_employee(
        self,
        employee_id: int,
        updates: EmployeeUpdate
    ) -> bool:
        """
        Update employee fields.

        Args:
            employee_id: Employee ID
            updates: EmployeeUpdate model with fields to update

        Returns:
            True if successful

        Raises:
            ValueError: If employee not found
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Get current employee
            current = self.get_employee(employee_id)
            if not current:
                raise ValueError(f"Employee {employee_id} not found")

            # Build update query
            update_fields = []
            params = []

            for field, value in updates.dict(exclude_unset=True).items():
                if value is not None:
                    update_fields.append(f"{field} = ?")
                    params.append(value)

                    # Log audit for each field change
                    old_value = getattr(current, field)
                    if old_value != value:
                        severity = "HIGH" if field in ['ral', 'qualifica', 'data_cessazione'] else "MEDIUM"
                        self._log_audit(
                            conn, "employees", employee_id, "UPDATE",
                            field_name=field,
                            old_value=str(old_value) if old_value else None,
                            new_value=str(value) if value else None,
                            change_severity=severity
                        )

            if not update_fields:
                return True  # No changes

            # Add updated_at
            update_fields.append("updated_at = ?")
            params.append(datetime.now())
            params.append(employee_id)

            query = f"UPDATE employees SET {', '.join(update_fields)} WHERE employee_id = ?"
            cursor.execute(query, params)

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    # === DELETE / DEACTIVATE ===

    def deactivate_employee(self, employee_id: int, data_cessazione: date = None) -> bool:
        """
        Deactivate employee (soft delete).

        Args:
            employee_id: Employee ID
            data_cessazione: Optional cessation date

        Returns:
            True if successful
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE employees
                SET active = 0,
                    data_cessazione = ?,
                    updated_at = ?
                WHERE employee_id = ?
            """, (data_cessazione, datetime.now(), employee_id))

            self._log_audit(
                conn, "employees", employee_id, "DEACTIVATE",
                field_name="active",
                old_value="1",
                new_value="0",
                change_severity="HIGH"
            )

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def delete_employee(self, employee_id: int) -> bool:
        """
        Permanently delete employee (use with caution!).

        Args:
            employee_id: Employee ID

        Returns:
            True if successful
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Log before deleting
            self._log_audit(
                conn, "employees", employee_id, "DELETE",
                change_severity="CRITICAL"
            )

            cursor.execute("DELETE FROM employees WHERE employee_id = ?", (employee_id,))

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    # === STATISTICS ===

    def get_employee_stats(self) -> Dict[str, Any]:
        """Get employee statistics for dashboard"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            stats = {}

            # Total active employees
            cursor.execute("SELECT COUNT(*) FROM employees WHERE active = 1")
            stats['total_active'] = cursor.fetchone()[0]

            # Total inactive
            cursor.execute("SELECT COUNT(*) FROM employees WHERE active = 0")
            stats['total_inactive'] = cursor.fetchone()[0]

            # By qualifica
            cursor.execute("""
                SELECT qualifica, COUNT(*) as count
                FROM employees
                WHERE active = 1 AND qualifica IS NOT NULL
                GROUP BY qualifica
                ORDER BY count DESC
            """)
            stats['by_qualifica'] = [dict(row) for row in cursor.fetchall()]

            # By area
            cursor.execute("""
                SELECT area, COUNT(*) as count
                FROM employees
                WHERE active = 1 AND area IS NOT NULL
                GROUP BY area
                ORDER BY count DESC
                LIMIT 10
            """)
            stats['by_area'] = [dict(row) for row in cursor.fetchall()]

            # Average RAL
            cursor.execute("""
                SELECT AVG(ral) as avg_ral
                FROM employees
                WHERE active = 1 AND ral IS NOT NULL AND ral > 0
            """)
            avg_ral = cursor.fetchone()[0]
            stats['avg_ral'] = float(avg_ral) if avg_ral else 0

            return stats

        finally:
            conn.close()


# Singleton instance
_employee_service_instance = None


def get_employee_service() -> EmployeeService:
    """Get singleton instance of EmployeeService"""
    global _employee_service_instance
    if _employee_service_instance is None:
        _employee_service_instance = EmployeeService()
    return _employee_service_instance
