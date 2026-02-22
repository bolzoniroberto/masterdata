"""
Migration 004: Add Multiple Hierarchies Support

This migration adds support for managing 5 different organizational hierarchies
simultaneously (HR, TNS, SGSL, GDPR, IT_DIR).

Tables created:
- hierarchy_types: Defines the 5 hierarchy types
- hierarchy_assignments: Maps employees to org_units for each hierarchy type
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
    Apply migration 004 to database.

    Creates tables for managing multiple organizational hierarchies.

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
        print("🔄 Starting migration 004: Add Multiple Hierarchies...")

        # === CREATE HIERARCHY_TYPES TABLE ===
        if not check_table_exists(cursor, 'hierarchy_types'):
            print("  📝 Creating hierarchy_types table...")
            cursor.execute("""
                CREATE TABLE hierarchy_types (
                    hierarchy_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type_code TEXT UNIQUE NOT NULL,
                    type_name TEXT NOT NULL,
                    description TEXT,
                    color_hex TEXT,
                    active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Insert the 5 hierarchy types
            cursor.execute("""
                INSERT INTO hierarchy_types (type_code, type_name, description, color_hex) VALUES
                ('HR', 'HR Hierarchy', 'Gerarchia Risorse Umane - Area/SottoArea/Manager', '#1f77b4'),
                ('TNS', 'TNS Travel', 'Gerarchia Travel & Expense - Approvatori e Controllori', '#ff7f0e'),
                ('SGSL', 'SGSL Safety', 'Salute e Sicurezza sul Lavoro - RSPP/RLS/Coordinatori', '#2ca02c'),
                ('GDPR', 'GDPR Privacy', 'Privacy e Protezione Dati - DPO/Delegati', '#d62728'),
                ('IT_DIR', 'IT Directory', 'Gerarchia IT - Manager Area/SottoArea tecnica', '#9467bd')
            """)
            print("  ✅ hierarchy_types table created with 5 types")
        else:
            print("  ℹ️ hierarchy_types table already exists")

        # === CREATE HIERARCHY_ASSIGNMENTS TABLE ===
        if not check_table_exists(cursor, 'hierarchy_assignments'):
            print("  📝 Creating hierarchy_assignments table...")
            cursor.execute("""
                CREATE TABLE hierarchy_assignments (
                    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER NOT NULL,
                    org_unit_id INTEGER NOT NULL,
                    hierarchy_type_id INTEGER NOT NULL,
                    effective_date DATE NOT NULL,
                    end_date DATE,
                    is_primary BOOLEAN DEFAULT 0,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
                    FOREIGN KEY (org_unit_id) REFERENCES org_units(org_unit_id),
                    FOREIGN KEY (hierarchy_type_id) REFERENCES hierarchy_types(hierarchy_type_id),

                    UNIQUE (employee_id, hierarchy_type_id, org_unit_id, effective_date)
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX idx_ha_employee ON hierarchy_assignments(employee_id)")
            cursor.execute("CREATE INDEX idx_ha_org_unit ON hierarchy_assignments(org_unit_id)")
            cursor.execute("CREATE INDEX idx_ha_type ON hierarchy_assignments(hierarchy_type_id)")
            cursor.execute("CREATE INDEX idx_ha_effective_date ON hierarchy_assignments(effective_date)")

            print("  ✅ hierarchy_assignments table created")
        else:
            print("  ℹ️ hierarchy_assignments table already exists")

        # Commit all changes
        conn.commit()
        print("✅ Migration 004 completed successfully!")
        return True

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration 004 failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        cursor.close()
        conn.close()


def rollback(db_path: Path) -> bool:
    """Rollback migration 004 (drops hierarchy tables)."""
    print("⚠️ WARNING: Rolling back migration 004 will drop hierarchy tables!")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        cursor.execute("DROP TABLE IF EXISTS hierarchy_assignments")
        cursor.execute("DROP TABLE IF EXISTS hierarchy_types")

        conn.commit()
        print("✅ Migration 004 rolled back")
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

    print("=== Testing Migration 004 ===")
    success = migrate(config.DB_PATH)

    if success:
        print("\n✅ Migration test successful!")
    else:
        print("\n❌ Migration test failed!")
