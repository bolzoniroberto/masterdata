"""
Migration 007: Add merge imports audit log table.

Creates audit_merge_imports table to track all differential/enrichment imports:
- Matching statistics (matched, new, gap counts)
- Merge execution results (applied, skipped, errors)
- Critical gaps detection
- Snapshot and validation tracking
"""

from services.database import DatabaseHandler


SQL_CREATE_MERGE_AUDIT = """
CREATE TABLE IF NOT EXISTS audit_merge_imports (
    -- Primary key
    merge_id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Import metadata
    import_type TEXT NOT NULL,                   -- 'salary_review', 'tns_reorg', 'cessati_assunti', 'banding', 'custom'
    key_column TEXT NOT NULL,                    -- 'tx_cod_fiscale', 'cod_tns', 'position_id'
    file_name TEXT,                              -- Nome file Excel originale
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Matching statistics
    matched_count INTEGER DEFAULT 0,             -- Record matched (file E DB)
    new_count INTEGER DEFAULT 0,                 -- Record nuovi (file NON in DB)
    gap_count INTEGER DEFAULT 0,                 -- Record gap (DB NON in file)

    -- Merge execution results
    applied_count INTEGER DEFAULT 0,             -- Record effettivamente aggiornati
    skipped_count INTEGER DEFAULT 0,             -- Record saltati dall'utente
    error_count INTEGER DEFAULT 0,               -- Record con errori

    -- Gap analysis
    critical_gaps INTEGER DEFAULT 0,             -- Gap su ruoli critici (manager, approvatori)
    coverage_percentage REAL,                    -- matched/(matched+gap)*100

    -- Configuration
    merge_strategies TEXT,                       -- JSON dict strategie usate per campo
    conflict_resolutions TEXT,                   -- JSON dict conflitti risolti manualmente

    -- Validation & snapshot
    snapshot_path TEXT,                          -- Path snapshot pre-merge (per rollback)
    validation_passed BOOLEAN DEFAULT NULL,      -- NULL se non validato, TRUE/FALSE se validato

    -- Notes
    notes TEXT                                   -- Note aggiuntive utente
);
"""

SQL_CREATE_INDEX_TYPE = """
CREATE INDEX IF NOT EXISTS idx_merge_import_type
    ON audit_merge_imports(import_type)
"""

SQL_CREATE_INDEX_UPLOADED = """
CREATE INDEX IF NOT EXISTS idx_merge_uploaded_at
    ON audit_merge_imports(uploaded_at DESC)
"""

SQL_CREATE_INDEX_VALIDATION = """
CREATE INDEX IF NOT EXISTS idx_merge_validation
    ON audit_merge_imports(validation_passed)
"""


def migrate():
    """
    Apply migration 007: create audit_merge_imports table.

    Example:
        >>> from migrations.migration_007_add_merge_audit import migrate
        >>> migrate()
        ✅ Migration 007 applied: audit_merge_imports table created
    """
    db = DatabaseHandler()

    try:
        cursor = db.get_connection().cursor()

        # Create table
        cursor.execute(SQL_CREATE_MERGE_AUDIT)
        print("✅ Table audit_merge_imports created")

        # Create indexes
        cursor.execute(SQL_CREATE_INDEX_TYPE)
        cursor.execute(SQL_CREATE_INDEX_UPLOADED)
        cursor.execute(SQL_CREATE_INDEX_VALIDATION)
        print("✅ Indexes created on audit_merge_imports")

        db.get_connection().commit()
        print("✅ Migration 007 applied successfully")

    except Exception as e:
        print(f"❌ Migration 007 failed: {e}")
        raise


def rollback():
    """
    Rollback migration 007: drop audit_merge_imports table.

    WARNING: This will delete all merge audit history!

    Example:
        >>> from migrations.migration_007_add_merge_audit import rollback
        >>> rollback()
        ✅ Migration 007 rolled back
    """
    db = DatabaseHandler()

    try:
        cursor = db.get_connection().cursor()
        cursor.execute("DROP TABLE IF EXISTS audit_merge_imports")
        db.get_connection().commit()
        print("✅ Table audit_merge_imports dropped")
        print("✅ Migration 007 rolled back successfully")

    except Exception as e:
        print(f"❌ Rollback migration 007 failed: {e}")
        raise


if __name__ == "__main__":
    # Apply migration when run directly
    migrate()
