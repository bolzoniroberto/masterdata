"""
Migration 006: Add Salary Management

This migration adds support for managing monthly salary data from payroll system
(AR_PAY_014 files) with full component breakdown and change tracking.

Tables created:
- salary_records: Monthly salary snapshots with RAL and aggregated components
- salary_components_detail: Detailed breakdown of 34 salary components
- salary_changes_audit: Automatic tracking of salary changes between months
"""
import sqlite3
from pathlib import Path


def check_table_exists(cursor: sqlite3.Cursor, table_name: str) -> bool:
    """Check if table exists in database"""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None


def check_index_exists(cursor: sqlite3.Cursor, index_name: str) -> bool:
    """Check if index exists in database"""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
        (index_name,)
    )
    return cursor.fetchone() is not None


def migrate(db_path: Path) -> bool:
    """
    Apply migration 006 to database.

    Creates tables for salary management and change tracking.

    Args:
        db_path: Path to SQLite database

    Returns:
        True if migration successful, False if already applied or error
    """
    if not db_path.exists():
        print(f"⚠️ Database not found: {db_path}")
        return False

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        print("🔄 Starting migration 006: Add Salary Management...")

        # === CREATE SALARY_RECORDS TABLE ===
        if not check_table_exists(cursor, 'salary_records'):
            print("  📝 Creating salary_records table...")
            cursor.execute("""
                CREATE TABLE salary_records (
                    salary_record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tx_cod_fiscale TEXT NOT NULL,
                    employee_id INTEGER NOT NULL,

                    -- Periodo
                    periodo_mese TEXT NOT NULL,
                    periodo_date DATE NOT NULL,

                    -- Dati retributivi principali
                    ral DECIMAL(12,2) NOT NULL,
                    monthly_gross DECIMAL(12,2) NOT NULL,
                    monthly_with_edr DECIMAL(12,2),
                    part_time_percentage FLOAT DEFAULT 100.0,

                    -- Componenti retributivi aggregati (per reporting veloce)
                    base_minimum DECIMAL(12,2),
                    contingenza DECIMAL(12,2),
                    seniority_increases DECIMAL(12,2),
                    personal_additions DECIMAL(12,2),
                    overtime_forfait DECIMAL(12,2),
                    shift_increase DECIMAL(12,2),
                    function_allowance DECIMAL(12,2),
                    special_payments DECIMAL(12,2),

                    -- Dati organizzativi (snapshot del mese)
                    area TEXT,
                    sottoarea TEXT,
                    cdc TEXT,
                    contratto TEXT,
                    qualifica TEXT,

                    -- Metadata import
                    import_version_id INTEGER,
                    import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source_file TEXT,

                    -- Timestamps
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
                    FOREIGN KEY (import_version_id) REFERENCES import_versions(id),

                    UNIQUE (tx_cod_fiscale, periodo_mese)
                )
            """)

            # Create indexes for salary_records
            cursor.execute("CREATE INDEX idx_salary_cf ON salary_records(tx_cod_fiscale)")
            cursor.execute("CREATE INDEX idx_salary_period ON salary_records(periodo_mese)")
            cursor.execute("CREATE INDEX idx_salary_employee ON salary_records(employee_id)")
            cursor.execute("CREATE INDEX idx_salary_date ON salary_records(periodo_date)")

            print("  ✅ salary_records table created")
        else:
            print("  ℹ️ salary_records table already exists")

        # === CREATE SALARY_COMPONENTS_DETAIL TABLE ===
        if not check_table_exists(cursor, 'salary_components_detail'):
            print("  📝 Creating salary_components_detail table...")
            cursor.execute("""
                CREATE TABLE salary_components_detail (
                    component_detail_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    salary_record_id INTEGER NOT NULL,
                    tx_cod_fiscale TEXT NOT NULL,
                    periodo_mese TEXT NOT NULL,

                    -- Componente retributiva
                    component_code TEXT NOT NULL,
                    component_name TEXT NOT NULL,
                    component_category TEXT,
                    amount DECIMAL(12,2) NOT NULL,

                    -- Metadata
                    is_recurring BOOLEAN DEFAULT 1,
                    is_taxable BOOLEAN DEFAULT 1,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (salary_record_id) REFERENCES salary_records(salary_record_id)
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX idx_scd_salary ON salary_components_detail(salary_record_id)")
            cursor.execute("CREATE INDEX idx_scd_component ON salary_components_detail(component_code)")
            cursor.execute("CREATE INDEX idx_scd_period ON salary_components_detail(periodo_mese)")
            cursor.execute("CREATE INDEX idx_scd_cf ON salary_components_detail(tx_cod_fiscale)")

            print("  ✅ salary_components_detail table created")
        else:
            print("  ℹ️ salary_components_detail table already exists")

        # === CREATE SALARY_CHANGES_AUDIT TABLE ===
        if not check_table_exists(cursor, 'salary_changes_audit'):
            print("  📝 Creating salary_changes_audit table...")
            cursor.execute("""
                CREATE TABLE salary_changes_audit (
                    change_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tx_cod_fiscale TEXT NOT NULL,
                    employee_id INTEGER NOT NULL,

                    -- Periodo variazione
                    periodo_from TEXT NOT NULL,
                    periodo_to TEXT NOT NULL,
                    change_date DATE NOT NULL,

                    -- Tipo variazione
                    change_type TEXT NOT NULL,
                    field_name TEXT,
                    component_code TEXT,

                    -- Valori before/after
                    previous_value DECIMAL(12,2),
                    new_value DECIMAL(12,2),
                    impact_amount DECIMAL(12,2),
                    impact_percentage FLOAT,

                    -- Metadata
                    severity TEXT,
                    notes TEXT,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX idx_sc_cf ON salary_changes_audit(tx_cod_fiscale)")
            cursor.execute("CREATE INDEX idx_sc_employee ON salary_changes_audit(employee_id)")
            cursor.execute("CREATE INDEX idx_sc_type ON salary_changes_audit(change_type)")
            cursor.execute("CREATE INDEX idx_sc_period ON salary_changes_audit(periodo_to)")
            cursor.execute("CREATE INDEX idx_sc_severity ON salary_changes_audit(severity)")

            print("  ✅ salary_changes_audit table created")
        else:
            print("  ℹ️ salary_changes_audit table already exists")

        # Commit all changes
        conn.commit()
        print("✅ Migration 006 completed successfully!")
        return True

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration 006 failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        cursor.close()
        conn.close()


def rollback(db_path: Path) -> bool:
    """Rollback migration 006 (drops salary tables)."""
    print("⚠️ WARNING: Rolling back migration 006 will drop salary tables!")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        cursor.execute("DROP TABLE IF EXISTS salary_changes_audit")
        cursor.execute("DROP TABLE IF EXISTS salary_components_detail")
        cursor.execute("DROP TABLE IF EXISTS salary_records")

        conn.commit()
        print("✅ Migration 006 rolled back")
        return True

    except Exception as e:
        conn.rollback()
        print(f"❌ Rollback failed: {str(e)}")
        return False

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    # Test migration on database
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    import config

    print("=== Testing Migration 006 ===")
    success = migrate(config.DB_PATH)

    if success:
        print("\n✅ Migration test successful!")
    else:
        print("\n❌ Migration test failed!")
