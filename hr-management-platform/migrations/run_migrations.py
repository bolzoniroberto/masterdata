"""
Migration Runner Script

Executes all database migrations in order.
Run this script to initialize or upgrade the database schema.

Usage:
    python migrations/run_migrations.py [--rollback MIGRATION_NUM]

Examples:
    python migrations/run_migrations.py                    # Apply all migrations
    python migrations/run_migrations.py --rollback 003     # Rollback migration 003
"""
import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from migrations import (
    migration_001_add_import_versioning,
    migration_002_add_checkpoint_milestone,
    migration_003_normalize_db_org,
    migration_004_add_hierarchies,
    migration_005_add_roles,
    migration_006_add_salaries
)


MIGRATIONS = [
    ("001", "Import Versioning", migration_001_add_import_versioning),
    ("002", "Checkpoint Milestone", migration_002_add_checkpoint_milestone),
    ("003", "Normalize DB_ORG Schema", migration_003_normalize_db_org),
    ("004", "Multiple Hierarchies", migration_004_add_hierarchies),
    ("005", "Role Management", migration_005_add_roles),
    ("006", "Salary Management", migration_006_add_salaries),
]


def ensure_database_dir():
    """Ensure database directory exists"""
    config.DB_DIR.mkdir(parents=True, exist_ok=True)
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)


def run_all_migrations():
    """Run all migrations in order"""
    ensure_database_dir()

    print("=" * 70)
    print("🚀 HR Management Platform - Database Migrations")
    print("=" * 70)
    print(f"\nDatabase: {config.DB_PATH}")
    print(f"Total migrations: {len(MIGRATIONS)}\n")

    success_count = 0
    failed_migrations = []

    for num, name, migration_module in MIGRATIONS:
        print(f"\n{'='*70}")
        print(f"Migration {num}: {name}")
        print(f"{'='*70}")

        try:
            success = migration_module.migrate(config.DB_PATH)
            if success:
                success_count += 1
                print(f"✅ Migration {num} completed")
            else:
                failed_migrations.append((num, name))
                print(f"⚠️ Migration {num} skipped or failed")
        except Exception as e:
            failed_migrations.append((num, name))
            print(f"❌ Migration {num} error: {str(e)}")
            import traceback
            traceback.print_exc()

    # Summary
    print("\n" + "=" * 70)
    print("📊 Migration Summary")
    print("=" * 70)
    print(f"✅ Successful: {success_count}/{len(MIGRATIONS)}")

    if failed_migrations:
        print(f"❌ Failed: {len(failed_migrations)}")
        for num, name in failed_migrations:
            print(f"   - Migration {num}: {name}")
    else:
        print("🎉 All migrations completed successfully!")

    print("=" * 70)

    return len(failed_migrations) == 0


def rollback_migration(migration_num: str):
    """Rollback a specific migration"""
    ensure_database_dir()

    # Find migration
    migration = None
    for num, name, module in MIGRATIONS:
        if num == migration_num:
            migration = (num, name, module)
            break

    if not migration:
        print(f"❌ Migration {migration_num} not found!")
        print(f"Available migrations: {', '.join([m[0] for m in MIGRATIONS])}")
        return False

    num, name, module = migration

    print("=" * 70)
    print(f"⚠️ Rolling back Migration {num}: {name}")
    print("=" * 70)
    print("\n⚠️ WARNING: This will undo database changes!")
    print("⚠️ Make sure you have a backup before proceeding.\n")

    confirm = input("Type 'yes' to confirm rollback: ")
    if confirm.lower() != 'yes':
        print("❌ Rollback cancelled")
        return False

    try:
        success = module.rollback(config.DB_PATH)
        if success:
            print(f"\n✅ Migration {num} rolled back successfully")
            return True
        else:
            print(f"\n❌ Migration {num} rollback failed")
            return False
    except Exception as e:
        print(f"\n❌ Rollback error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="HR Management Platform - Database Migrations"
    )
    parser.add_argument(
        '--rollback',
        type=str,
        metavar='MIGRATION_NUM',
        help='Rollback a specific migration (e.g., 003)'
    )

    args = parser.parse_args()

    if args.rollback:
        success = rollback_migration(args.rollback)
        sys.exit(0 if success else 1)
    else:
        success = run_all_migrations()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
