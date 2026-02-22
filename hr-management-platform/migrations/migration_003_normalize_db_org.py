"""
Migration 003: Normalize DB_ORG Schema

This migration creates the normalized database schema for managing the complete
DB_ORG masterdata (135 columns) in a relational structure.

Tables created:
- companies: Multi-company support for Gruppo 24 ORE
- employees: Normalized employee data (from DB_ORG columns)
- org_units: Organizational units with parent-child hierarchy
- Extended audit_log support for new tables

This replaces the flat 'personale'/'strutture' tables with a proper
normalized schema with referential integrity.
"""
import sqlite3
from pathlib import Path
from typing import Optional


def check_table_exists(cursor: sqlite3.Cursor, table_name: str) -> bool:
    """Check if table exists in database"""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None


def check_column_exists(cursor: sqlite3.Cursor, table_name: str, column_name: str) -> bool:
    """Check if column exists in table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]
    return column_name in columns


def check_index_exists(cursor: sqlite3.Cursor, index_name: str) -> bool:
    """Check if index exists in database"""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
        (index_name,)
    )
    return cursor.fetchone() is not None


def migrate(db_path: Path) -> bool:
    """
    Apply migration 003 to database.

    Creates normalized schema for DB_ORG masterdata with proper
    relational structure and referential integrity.

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
        print("🔄 Starting migration 003: Normalize DB_ORG Schema...")

        # === CREATE COMPANIES TABLE ===
        if not check_table_exists(cursor, 'companies'):
            print("  📝 Creating companies table...")
            cursor.execute("""
                CREATE TABLE companies (
                    company_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_code TEXT UNIQUE NOT NULL,
                    company_name TEXT NOT NULL,
                    parent_company_id INTEGER,
                    active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (parent_company_id) REFERENCES companies(company_id)
                )
            """)

            # Insert default companies for Gruppo Il Sole 24 ORE
            cursor.execute("""
                INSERT INTO companies (company_code, company_name, active) VALUES
                ('GRUPPO_24ORE', 'Gruppo 24 ORE', 1),
                ('IL_SOLE_24ORE', 'Il Sole 24 ORE S.p.A.', 1),
                ('24ORE_CULTURA', '24 ORE Cultura S.r.l.', 1),
                ('24ORE_EVENTI', '24 ORE Eventi S.r.l.', 1)
            """)
            print("  ✅ companies table created with default data")
        else:
            print("  ℹ️ companies table already exists")

        # === CREATE ORG_UNITS TABLE ===
        if not check_table_exists(cursor, 'org_units'):
            print("  📝 Creating org_units table...")
            cursor.execute("""
                CREATE TABLE org_units (
                    org_unit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codice TEXT UNIQUE NOT NULL,
                    descrizione TEXT NOT NULL,
                    company_id INTEGER NOT NULL,
                    parent_org_unit_id INTEGER,
                    cdccosto TEXT,
                    cdc_amm TEXT,
                    livello INTEGER,
                    hierarchy_path TEXT,
                    unita_org_livello1 TEXT,
                    unita_org_livello2 TEXT,
                    testata_gg TEXT,
                    responsible_employee_id INTEGER,
                    active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies(company_id),
                    FOREIGN KEY (parent_org_unit_id) REFERENCES org_units(org_unit_id)
                )
            """)

            # Create indexes for org_units
            cursor.execute("CREATE INDEX idx_org_units_codice ON org_units(codice)")
            cursor.execute("CREATE INDEX idx_org_units_company ON org_units(company_id)")
            cursor.execute("CREATE INDEX idx_org_units_parent ON org_units(parent_org_unit_id)")
            cursor.execute("CREATE INDEX idx_org_units_path ON org_units(hierarchy_path)")

            print("  ✅ org_units table created")
        else:
            print("  ℹ️ org_units table already exists")

        # === CREATE EMPLOYEES TABLE ===
        if not check_table_exists(cursor, 'employees'):
            print("  📝 Creating employees table...")
            cursor.execute("""
                CREATE TABLE employees (
                    employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tx_cod_fiscale TEXT UNIQUE NOT NULL,
                    codice TEXT UNIQUE NOT NULL,
                    titolare TEXT NOT NULL,
                    company_id INTEGER NOT NULL,

                    -- Dati anagrafici (Ambito AF-BH)
                    cognome TEXT,
                    nome TEXT,
                    societa TEXT,
                    area TEXT,
                    sottoarea TEXT,
                    sede TEXT,
                    contratto TEXT,
                    qualifica TEXT,
                    livello TEXT,
                    ral REAL,
                    data_assunzione DATE,
                    data_cessazione DATE,
                    data_nascita DATE,
                    sesso TEXT,
                    email TEXT,
                    matricola TEXT,

                    -- Indirizzo
                    indirizzo_via TEXT,
                    indirizzo_cap TEXT,
                    indirizzo_citta TEXT,

                    -- Dati organizzativi (Ambito A-AC)
                    formato TEXT,
                    funzione TEXT,
                    fte REAL DEFAULT 1.0,
                    tipo_collaborazione TEXT,
                    reports_to_codice TEXT,
                    photo_url TEXT,

                    -- Dati TNS (Ambito BS-CV)
                    sede_tns TEXT,
                    gruppo_sind TEXT,

                    -- Metadata
                    active BOOLEAN DEFAULT 1,
                    ultimo_sync_payroll DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (company_id) REFERENCES companies(company_id)
                )
            """)

            # Create indexes for employees
            cursor.execute("CREATE INDEX idx_employees_cf ON employees(tx_cod_fiscale)")
            cursor.execute("CREATE INDEX idx_employees_codice ON employees(codice)")
            cursor.execute("CREATE INDEX idx_employees_company ON employees(company_id)")
            cursor.execute("CREATE INDEX idx_employees_cognome ON employees(cognome)")
            cursor.execute("CREATE INDEX idx_employees_area ON employees(area)")
            cursor.execute("CREATE INDEX idx_employees_active ON employees(active)")

            print("  ✅ employees table created")
        else:
            print("  ℹ️ employees table already exists")

        # Commit all changes
        conn.commit()
        print("✅ Migration 003 completed successfully!")
        return True

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration 003 failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        cursor.close()
        conn.close()


def rollback(db_path: Path) -> bool:
    """
    Rollback migration 003 (drops normalized tables).

    WARNING: This will drop companies, org_units, and employees tables.
    Only use in development!
    """
    print("⚠️ WARNING: Rolling back migration 003 will drop normalized tables!")
    print("⚠️ This operation will lose all DB_ORG data.")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # Drop tables in reverse order of dependencies
        cursor.execute("DROP TABLE IF EXISTS employees")
        cursor.execute("DROP TABLE IF EXISTS org_units")
        cursor.execute("DROP TABLE IF EXISTS companies")

        conn.commit()
        print("✅ Migration 003 rolled back")
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

    print("=== Testing Migration 003 ===")
    success = migrate(config.DB_PATH)

    if success:
        print("\n✅ Migration test successful!")
    else:
        print("\n❌ Migration test failed!")
