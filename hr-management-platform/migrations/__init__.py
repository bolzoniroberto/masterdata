"""
Database migrations package for HR Management Platform

Available migrations:
- 001: Import Versioning and Enhanced Audit Log
- 002: Checkpoint Milestone
- 003: Normalize DB_ORG Schema
- 004: Multiple Hierarchies Support
- 005: Role Management
- 006: Salary Management
"""

# Import all migrations for easy access
from . import migration_001_add_import_versioning
from . import migration_002_add_checkpoint_milestone
from . import migration_003_normalize_db_org
from . import migration_004_add_hierarchies
from . import migration_005_add_roles
from . import migration_006_add_salaries

__all__ = [
    'migration_001_add_import_versioning',
    'migration_002_add_checkpoint_milestone',
    'migration_003_normalize_db_org',
    'migration_004_add_hierarchies',
    'migration_005_add_roles',
    'migration_006_add_salaries',
]
