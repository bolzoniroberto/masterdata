"""
Migration 003: Add Hierarchy Fields for Organigrammi

Adds three new columns to employees table:
- reports_to_cf: Codice Fiscale del responsabile diretto (per organigramma HR)
- cod_tns: Codice TNS del dipendente (per organigramma TNS)
- padre_tns: Codice TNS del parent (per organigramma TNS)

Created: 2026-02-21
"""
import sqlite3
from pathlib import Path


def migrate(db_path: Path):
    """Execute migration to add hierarchy fields"""
    print(f"\n🔄 Running Migration 003: Add Hierarchy Fields")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(employees)")
        columns = [col[1] for col in cursor.fetchall()]

        changes_made = False

        # Add reports_to_cf if not exists
        if 'reports_to_cf' not in columns:
            print("  ➕ Adding column: reports_to_cf (CF Responsabile Diretto)")
            cursor.execute("""
                ALTER TABLE employees
                ADD COLUMN reports_to_cf TEXT
            """)
            changes_made = True
        else:
            print("  ✓ Column reports_to_cf already exists")

        # Add cod_tns if not exists
        if 'cod_tns' not in columns:
            print("  ➕ Adding column: cod_tns (Codice TNS)")
            cursor.execute("""
                ALTER TABLE employees
                ADD COLUMN cod_tns TEXT
            """)
            changes_made = True
        else:
            print("  ✓ Column cod_tns already exists")

        # Add padre_tns if not exists
        if 'padre_tns' not in columns:
            print("  ➕ Adding column: padre_tns (Padre TNS)")
            cursor.execute("""
                ALTER TABLE employees
                ADD COLUMN padre_tns TEXT
            """)
            changes_made = True
        else:
            print("  ✓ Column padre_tns already exists")

        if changes_made:
            conn.commit()
            print("  ✅ Migration 003 completed successfully")
        else:
            print("  ℹ️  Migration 003 already applied - no changes needed")

        return True

    except Exception as e:
        conn.rollback()
        print(f"  ❌ Migration 003 failed: {str(e)}")
        raise

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    # Test migration
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    import config

    migrate(config.DB_PATH)
