"""
Migration 005: Add Role Management

This migration adds support for managing role assignments with temporal validity.
Supports 19 TNS roles + SGSL roles + GDPR roles + other roles.

Tables created:
- role_definitions: Catalog of all available roles
- role_assignments: Employee-to-role assignments with temporal validity
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
    Apply migration 005 to database.

    Creates tables for role management with temporal validity.

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
        print("🔄 Starting migration 005: Add Role Management...")

        # === CREATE ROLE_DEFINITIONS TABLE ===
        if not check_table_exists(cursor, 'role_definitions'):
            print("  📝 Creating role_definitions table...")
            cursor.execute("""
                CREATE TABLE role_definitions (
                    role_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role_code TEXT UNIQUE NOT NULL,
                    role_name TEXT NOT NULL,
                    role_category TEXT NOT NULL,
                    description TEXT,
                    icon TEXT,
                    color_hex TEXT,
                    requires_scope BOOLEAN DEFAULT 0,
                    is_mandatory BOOLEAN DEFAULT 0,
                    active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Insert TNS roles (19 roles)
            tns_roles = [
                ('VIAGGIATORE', 'Viaggiatore', 'TNS', 'Può creare e gestire note spese personali', '🧳', '#2ecc71', 0, 0),
                ('APPROVATORE', 'Approvatore', 'TNS', 'Approva note spese dei subordinati', '✅', '#3498db', 1, 1),
                ('CONTROLLORE', 'Controllore', 'TNS', 'Verifica conformità note spese', '🔍', '#e67e22', 1, 0),
                ('CASSIERE', 'Cassiere', 'TNS', 'Gestisce rimborsi e pagamenti', '💰', '#f39c12', 0, 0),
                ('SEGRETARIO', 'Segretario', 'TNS', 'Supporto amministrativo travel', '📋', '#95a5a6', 0, 0),
                ('VISUALIZZATORI', 'Visualizzatori', 'TNS', 'Solo visualizzazione dati travel', '👁️', '#bdc3c7', 0, 0),
                ('AMMINISTRAZIONE', 'Amministrazione', 'TNS', 'Gestione amministrativa completa', '⚙️', '#34495e', 0, 0),
                ('SEGR_REDAZ', 'Segretario Redazionale', 'TNS', 'Segretario specifico per redazioni', '📰', '#95a5a6', 0, 0),
                ('SEGRETERIA_RED_ASST', 'Segreteria Redaz. Assistita', 'TNS', 'Assistenza segreteria redazionale', '📝', '#95a5a6', 0, 0),
                ('SEGRETARIO_ASST', 'Segretario Assistito', 'TNS', 'Segretario con supporto', '📋', '#95a5a6', 0, 0),
                ('CONTROLLORE_ASST', 'Controllore Assistito', 'TNS', 'Controllore con supporto', '🔍', '#e67e22', 0, 0),
                ('RUOLI_OLTREV', 'Ruoli OltreV', 'TNS', 'Ruoli speciali OltreV', '⭐', '#9b59b6', 0, 0),
                ('RUOLI', 'Ruoli Generici', 'TNS', 'Altri ruoli TNS generici', '🎭', '#95a5a6', 0, 0),
                ('RUOLI_AFC', 'Ruoli AFC', 'AFC', 'Ruoli Amministrazione Finanza Controllo', '💼', '#1abc9c', 0, 0),
                ('RUOLI_HR', 'Ruoli HR', 'HR', 'Ruoli Risorse Umane', '👥', '#e74c3c', 0, 0),
                ('ALTRI_RUOLI', 'Altri Ruoli', 'OTHER', 'Altri ruoli non categorizzati', '📌', '#7f8c8d', 0, 0)
            ]

            # Insert SGSL roles
            sgsl_roles = [
                ('RSPP', 'Responsabile Servizio Prevenzione Protezione', 'SGSL', 'RSPP aziendale', '🛡️', '#27ae60', 1, 1),
                ('RLS', 'Rappresentante Lavoratori Sicurezza', 'SGSL', 'Rappresentante eletto lavoratori', '👷', '#16a085', 1, 0),
                ('COORD_HSE', 'Coordinatore HSE', 'SGSL', 'Coordinatore Health Safety Environment', '🏗️', '#2ecc71', 1, 0),
                ('PREPOSTO', 'Preposto Sicurezza', 'SGSL', 'Preposto per area specifica', '⚠️', '#f39c12', 1, 0),
                ('MEDICO_COMPETENTE', 'Medico Competente', 'SGSL', 'Medico per sorveglianza sanitaria', '🩺', '#3498db', 0, 0)
            ]

            # Insert GDPR roles
            gdpr_roles = [
                ('DPO', 'Data Protection Officer', 'GDPR', 'Responsabile protezione dati', '🔒', '#c0392b', 0, 1),
                ('DELEGATO_PRIVACY', 'Delegato Privacy', 'GDPR', 'Delegato trattamento dati personali', '🔐', '#e74c3c', 1, 0),
                ('TITOLARE_TRATT', 'Titolare Trattamento', 'GDPR', 'Titolare trattamento dati', '👔', '#d63031', 1, 0)
            ]

            all_roles = tns_roles + sgsl_roles + gdpr_roles

            cursor.executemany("""
                INSERT INTO role_definitions
                (role_code, role_name, role_category, description, icon, color_hex, requires_scope, is_mandatory)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, all_roles)

            print(f"  ✅ role_definitions table created with {len(all_roles)} roles")
        else:
            print("  ℹ️ role_definitions table already exists")

        # === CREATE ROLE_ASSIGNMENTS TABLE ===
        if not check_table_exists(cursor, 'role_assignments'):
            print("  📝 Creating role_assignments table...")
            cursor.execute("""
                CREATE TABLE role_assignments (
                    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER NOT NULL,
                    role_id INTEGER NOT NULL,
                    org_unit_id INTEGER,
                    effective_date DATE NOT NULL,
                    end_date DATE,
                    assigned_by TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
                    FOREIGN KEY (role_id) REFERENCES role_definitions(role_id),
                    FOREIGN KEY (org_unit_id) REFERENCES org_units(org_unit_id),

                    UNIQUE (employee_id, role_id, org_unit_id, effective_date)
                )
            """)

            # Create indexes
            cursor.execute("CREATE INDEX idx_ra_employee ON role_assignments(employee_id)")
            cursor.execute("CREATE INDEX idx_ra_role ON role_assignments(role_id)")
            cursor.execute("CREATE INDEX idx_ra_org_unit ON role_assignments(org_unit_id)")
            cursor.execute("CREATE INDEX idx_ra_effective_date ON role_assignments(effective_date)")
            cursor.execute("CREATE INDEX idx_ra_active ON role_assignments(end_date)")

            print("  ✅ role_assignments table created")
        else:
            print("  ℹ️ role_assignments table already exists")

        # Commit all changes
        conn.commit()
        print("✅ Migration 005 completed successfully!")
        return True

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration 005 failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        cursor.close()
        conn.close()


def rollback(db_path: Path) -> bool:
    """Rollback migration 005 (drops role tables)."""
    print("⚠️ WARNING: Rolling back migration 005 will drop role tables!")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        cursor.execute("DROP TABLE IF EXISTS role_assignments")
        cursor.execute("DROP TABLE IF EXISTS role_definitions")

        conn.commit()
        print("✅ Migration 005 rolled back")
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

    print("=== Testing Migration 005 ===")
    success = migrate(config.DB_PATH)

    if success:
        print("\n✅ Migration test successful!")
    else:
        print("\n❌ Migration test failed!")
