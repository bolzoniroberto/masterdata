"""
Migration 001: Add Import Versioning and Enhanced Audit Log

Changes:
- Adds import_versions table for tracking import history
- Adds columns to audit_log: import_version_id, change_severity, field_name
- Creates necessary indexes
- Safe for existing databases (checks if columns/tables exist)
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
    Apply migration 001 to database.

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
        print("🔄 Starting migration 001: Add Import Versioning...")

        # === CREATE IMPORT_VERSIONS TABLE ===
        if not check_table_exists(cursor, 'import_versions'):
            print("  📝 Creating import_versions table...")
            cursor.execute("""
                CREATE TABLE import_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source_filename TEXT NOT NULL,
                    user_note TEXT,
                    personale_count INTEGER,
                    strutture_count INTEGER,
                    changes_summary TEXT,
                    completed BOOLEAN DEFAULT 0,
                    completed_at TIMESTAMP
                )
            """)
            print("  ✅ import_versions table created")
        else:
            print("  ℹ️ import_versions table already exists")

        # === ADD COLUMNS TO AUDIT_LOG ===
        if not check_column_exists(cursor, 'audit_log', 'import_version_id'):
            print("  📝 Adding import_version_id column to audit_log...")
            cursor.execute("ALTER TABLE audit_log ADD COLUMN import_version_id INTEGER")
            print("  ✅ import_version_id column added")
        else:
            print("  ℹ️ import_version_id column already exists")

        if not check_column_exists(cursor, 'audit_log', 'change_severity'):
            print("  📝 Adding change_severity column to audit_log...")
            cursor.execute("ALTER TABLE audit_log ADD COLUMN change_severity TEXT DEFAULT 'MEDIUM'")
            print("  ✅ change_severity column added")
        else:
            print("  ℹ️ change_severity column already exists")

        if not check_column_exists(cursor, 'audit_log', 'field_name'):
            print("  📝 Adding field_name column to audit_log...")
            cursor.execute("ALTER TABLE audit_log ADD COLUMN field_name TEXT")
            print("  ✅ field_name column added")
        else:
            print("  ℹ️ field_name column already exists")

        # === CREATE INDEXES ===
        if not check_index_exists(cursor, 'idx_import_timestamp'):
            print("  📝 Creating index on import_versions.timestamp...")
            cursor.execute("CREATE INDEX idx_import_timestamp ON import_versions(timestamp)")
            print("  ✅ idx_import_timestamp created")
        else:
            print("  ℹ️ idx_import_timestamp already exists")

        if not check_index_exists(cursor, 'idx_audit_import_version'):
            print("  📝 Creating index on audit_log.import_version_id...")
            cursor.execute("CREATE INDEX idx_audit_import_version ON audit_log(import_version_id)")
            print("  ✅ idx_audit_import_version created")
        else:
            print("  ℹ️ idx_audit_import_version already exists")

        if not check_index_exists(cursor, 'idx_audit_severity'):
            print("  📝 Creating index on audit_log.change_severity...")
            cursor.execute("CREATE INDEX idx_audit_severity ON audit_log(change_severity)")
            print("  ✅ idx_audit_severity created")
        else:
            print("  ℹ️ idx_audit_severity already exists")

        # Commit all changes
        conn.commit()
        print("✅ Migration 001 completed successfully!")
        return True

    except Exception as e:
        conn.rollback()
        print(f"❌ Migration 001 failed: {str(e)}")
        return False

    finally:
        cursor.close()
        conn.close()


def rollback(db_path: Path) -> bool:
    """
    Rollback migration 001 (NOT RECOMMENDED - would lose audit history).

    This is provided for completeness but should NOT be used in production
    as it would drop the import_versions table and remove audit columns.
    """
    print("⚠️ WARNING: Rolling back migration 001 will lose import history!")
    print("⚠️ This operation is NOT RECOMMENDED.")
    return False


if __name__ == "__main__":
    # Test migration on database
    import config

    print("=== Testing Migration 001 ===")
    success = migrate(config.DB_PATH)

    if success:
        print("\n✅ Migration test successful!")
    else:
        print("\n❌ Migration test failed!")
