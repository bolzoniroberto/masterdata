# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Approval Workflow Management for Travel & Expense System** - Gruppo Il Sole 24 ORE

A Streamlit web application for defining and managing the approval model for the company's travel and expense management system. The tool manages organizational structure (Strutture) and employee role assignments (Personale) with focus on approval workflows:

- **Primary Purpose**: Define who approves, controls, and manages travel/expense requests
- **Key Roles**: Viaggiatore (Traveler), Approvatore (Approver), Controllore (Controller), Cassiere (Cashier), Segretario (Secretary), and assistants
- **Data Management**: Validate, edit, and merge organizational hierarchy with employee approval roles
- **Export**: Generate DB_TNS file for import into travel/expense IT system

## Development Commands

### Running the Application
```bash
# Start the Streamlit application
streamlit run app.py

# Application will open on http://localhost:8501
```

### Python Environment
```bash
# Install dependencies
python3 -m pip install -r requirements.txt

# Python 3.9+ required
python3 --version

# Streamlit 1.35.0+ required for interactive selection features
python3 -c "import streamlit; print(streamlit.__version__)"
```

### Testing
```bash
# Run the test suite
python3 test_platform.py

# Note: Tests are in test_platform.py, not in tests/ directory
```

## Architecture Overview

### Three-Layer Architecture

**Models Layer** (`models/`): Pydantic validation models
- `personale.py`: PersonaleRecord model - validates employee records
- `strutture.py`: StrutturaRecord model - validates organizational structure records
- All models enforce Italian fiscal code format, mandatory fields, and business rules

**Services Layer** (`services/`): Business logic
- `excel_handler.py`: ExcelHandler - I/O operations for Excel files with backup management
- `validator.py`: DataValidator - Pydantic-based validation with business logic checks
- `merger.py`: DBTNSMerger - Merges Strutture + Personale into DB_TNS sheet
- `database.py`: DatabaseHandler - SQLite CRUD operations with audit logging (NEW)

**UI Layer** (`ui/`): Streamlit views
- `dashboard.py`: Statistics, KPIs, and anomaly alerts
- `strutture_view.py`: CRUD for organizational structures
- `personale_view.py`: CRUD for employees
- `merger_view.py`: DB_TNS generation interface
- `save_export_view.py`: Save/export/backup management

### Database-Centric Architecture (NEW - Phase 1-3 Complete)

**Primary Datastore**: SQLite (`data/db/app.db`)
**Session Cache**: Streamlit session state for UI performance

```
Excel Upload
    ↓
DatabaseHandler.import_from_dataframe()
    ↓
SQLite (source of truth)
    ↓
DatabaseHandler.export_to_dataframe()
    ↓
Session State (UI cache)
```

**Why Database-Centric?**
- ✅ Persistenza: Dati salvati tra sessioni
- ✅ No Excel reload: Primo run importa Excel, successivi caricano da DB
- ✅ Audit trail: Tutte le modifiche tracciare con before/after values
- ✅ Performance: Session state cache per UI veloce

### Streamlit Session State

The application uses Streamlit's session state to maintain data between page navigations:
- `st.session_state.data_loaded`: Boolean flag for data loaded status
- `st.session_state.personale_df`: DataFrame for employee data (cache from DB)
- `st.session_state.strutture_df`: DataFrame for organizational structures (cache from DB)
- `st.session_state.db_tns_df`: DataFrame for merged DB_TNS (generated on-demand)
- `st.session_state.excel_handler`: ExcelHandler instance with file path
- `st.session_state.database_handler`: DatabaseHandler instance (NEW)

**Critical**: Session state DataFrames are caches. All writes go to SQLite database, then update session state.

## DatabaseHandler (services/database.py)

SQLite with raw queries (no ORM) for maximum simplicity and performance.

### Initialization
```python
from services.database import DatabaseHandler

db = DatabaseHandler()  # Uses config.DB_PATH
db.init_db()  # Create schema if not exists
```

### CRUD Operations

**Personale (Employees)**:
```python
# Insert
db.insert_personale({
    'TxCodFiscale': 'RSSXXX00A01X001',
    'Titolare': 'Mario Rossi',
    'Codice': 'P001',
    ...
})

# Update
db.update_personale('RSSXXX00A01X001', {
    'Titolare': 'Mario Rossi Updated',
    'Approvatore': 'SÌ'
})

# Read
record = db.get_personale_by_cf('RSSXXX00A01X001')
all_records = db.get_personale_all()

# Delete
db.delete_personale('RSSXXX00A01X001')
```

**Strutture (Organizational Structures)**:
```python
# Similar API:
db.insert_struttura({...})
db.update_struttura('CODICE', {...})
db.get_struttura_by_codice('CODICE')
db.get_strutture_all()
db.delete_struttura('CODICE')
```

### Import/Export
```python
# Import from DataFrames (clearing existing data)
personale_count, strutture_count = db.import_from_dataframe(personale_df, strutture_df)

# Export to DataFrames
personale_df, strutture_df = db.export_to_dataframe()
```

### Audit Logging
```python
# Get audit log (last 100 entries)
logs = db.get_audit_log(limit=100)

# Each entry contains: timestamp, table_name, operation (INSERT/UPDATE/DELETE),
# record_key, before_values (JSON), after_values (JSON)
```

### Database Schema

**4 Tables**:

1. **personale**: Employees
   - Columns: All 26 standard Excel columns + created_at, updated_at
   - Primary Key: TxCodFiscale (Italian fiscal code, NOT NULL UNIQUE)
   - Secondary Key: Codice (employee code, UNIQUE)
   - Indices: CF, Codice, UO, Sede

2. **strutture**: Organizational structures
   - Columns: All 26 standard Excel columns + created_at, updated_at
   - Primary Key: Codice (structure code, NOT NULL UNIQUE)
   - TxCodFiscale: Always NULL (distinguishes from personale)
   - Indices: Codice, UO, UNITA_OPERATIVA_PADRE

3. **audit_log**: Modification tracking
   - Columns: id (PK), timestamp, table_name, operation, record_key, before_values (JSON), after_values (JSON)
   - Tracks all INSERT/UPDATE/DELETE with full before/after state

4. **db_tns**: Cache of merged Strutture + Personale
   - Created by merger_view when user requests merge

### Important Notes

- **No ORM**: Uses raw sqlite3 queries for simplicity and debuggability
- **Minimal SQL**: Direct INSERT/UPDATE/DELETE with parameter binding (safe from SQL injection)
- **Audit by default**: All CRUD operations logged automatically
- **Column mapping**: DB uses underscores (Unità_Organizzativa) while Excel uses spaces (Unità Organizzativa)
  - DatabaseHandler normalizes both ways automatically
- **Null handling**: NaN values converted to None for Pydantic compatibility

## Data Model and Business Logic

### Excel File Structure

The application works with Excel files containing exactly 26 columns (defined in `config.EXCEL_COLUMNS`) across three sheets:

1. **TNS Personale** (Employees):
   - **Must have** `TxCodFiscale` (Italian fiscal code, 16 alphanumeric chars)
   - Mandatory fields: TxCodFiscale, Titolare, Codice, Unità Organizzativa
   - **Key Role Fields** (for travel/expense approval workflow):
     - `Viaggiatore` - Can submit travel/expense requests
     - `Approvatore` - Approves requests
     - `Controllore` - Controls/audits expenses
     - `Cassiere` - Manages payments
     - `Visualizzatori` - View-only access
     - `Segretario` - Administrative support
     - `Amministrazione` - Administrative role
     - Assistant roles: `SegreteriA Red. Ass.ta`, `SegretariO Ass.to`, `Controllore Ass.to`
     - Additional roles: `RuoliAFC`, `RuoliHR`, `AltriRuoli`
     - Location: `Sede_TNS`, `GruppoSind`

2. **TNS Strutture** (Organizational Structure):
   - **Must NOT have** `TxCodFiscale` (must be empty/null)
   - Mandatory fields: Codice, DESCRIZIONE
   - Represents organizational units
   - Hierarchical relationships via `UNITA' OPERATIVA PADRE ` field

3. **DB_TNS** (Generated Merge):
   - Automatically generated by concatenating Strutture + Personale
   - **Order matters**: Strutture records first, then Personale records
   - Used for IT system import

### Critical Distinction: Personale vs Strutture

The **only reliable way** to distinguish between employee and structure records is:
- **Personale**: `TxCodFiscale` is NOT NULL/empty
- **Strutture**: `TxCodFiscale` IS NULL/empty

This distinction is used throughout the codebase, especially in:
- `DBTNSMerger.split_db_tns()`: Splits DB_TNS back into components
- All validation logic
- Models (`PersonaleRecord` requires CF, `StrutturaRecord` forbids it)

### Validation Rules

**Personale Validation** (`models/personale.py`):
- TxCodFiscale: Required, must match regex `^[A-Z0-9]{16}$`
  - **Duplicate CF**: Flagged as WARNING (not blocking) - may be legitimate in some cases
- Codice: Required, must be unique across all Personale records
- Titolare: Required (employee name)
- Unità Organizzativa: Required

**Strutture Validation** (`models/strutture.py`):
- TxCodFiscale: Must be empty/null (enforced in validator)
- Codice: Required, must be unique across all Strutture records
- DESCRIZIONE: Required (structure name)
- UNITA' OPERATIVA PADRE: If present, must reference an existing Codice
- Cycle detection: Hierarchical relationships checked for circular references

**DB_TNS Validation** (`services/merger.py`):
- Record count must equal Strutture count + Personale count
- All `Codice` values should be unique (duplicates are warnings)
- All parent references must exist in the merged data
- Proper separation maintained (CF present only in Personale portion)

### The Merge Process (DB_TNS Generation)

Located in `services/merger.py`, the merge follows this critical sequence:

1. **Column Alignment**: Ensure both DataFrames have all 26 standard columns
2. **Concatenation**: `pd.concat([strutture_df, personale_df])`
   - **Order is critical**: Structures first, employees second
3. **Integrity Checks**:
   - Verify record counts
   - Check for duplicate codes
   - Validate parent references
   - Confirm CF presence only in Personale records

**Important**: After any modification to Personale or Strutture, DB_TNS must be regenerated. The application does NOT auto-regenerate.

## Common Workflows

### Adding New Validation Rules

1. Add validator to appropriate Pydantic model (`models/personale.py` or `models/strutture.py`)
2. Use `@field_validator` decorator for field-level validation
3. Add business logic checks in `get_validation_errors()` method
4. Update `DataValidator` in `services/validator.py` if cross-record validation needed

### Working with Excel Files

**Reading**:
```python
handler = ExcelHandler(file_path)
personale_df, strutture_df, db_tns_df = handler.load_data()
```

**Saving** (with automatic backup):
```python
# Overwrites original file, creates timestamped backup
handler.save_data(personale_df, strutture_df, db_tns_df, create_backup=True)
```

**Exporting** (new timestamped file):
```python
# Creates new file in output/ directory
output_path = handler.export_to_output(personale_df, strutture_df, db_tns_df)
```

**Backup Management**:
- Automatic backup on save (max 50 backups, configurable in `config.MAX_BACKUPS`)
- Backup naming: `{stem}_backup_{YYYYMMDD_HHMMSS}.xls`
- Old backups auto-deleted when limit exceeded
- List/restore available via `handler.get_backup_list()` and `handler.restore_backup()`

### Adding New UI Views

1. Create new view file in `ui/` directory
2. Define `show_*_view()` function (follows naming convention)
3. Import and add routing in `app.py` main() function:
   ```python
   elif page == "🆕 New View":
       from ui.new_view import show_new_view
       show_new_view()
   ```
4. Add menu item to sidebar radio button in `app.py`
5. Access session state DataFrames via `st.session_state.*_df`

## Configuration

All configuration centralized in `config.py`:
- **Paths**: BASE_DIR, DATA_DIR, INPUT_DIR, OUTPUT_DIR, BACKUP_DIR
- **Excel Schema**: EXCEL_COLUMNS (26-column list), sheet names
- **Mandatory Fields**: MANDATORY_PERSONALE, MANDATORY_STRUTTURE
- **Backup Settings**: BACKUP_TIMESTAMP_FORMAT, MAX_BACKUPS
- **UI Settings**: PAGE_TITLE, PAGE_ICON, LAYOUT

**Never hardcode** paths, column names, or sheet names - always reference `config.*`.

## Data Integrity Patterns

### Handling NaN/None Values

Pandas NaN values are converted to None for Pydantic compatibility:
```python
df_clean = df.where(pd.notna(df), None)
```

All Pydantic models include `empty_str_to_none` validator to normalize empty strings.

### Parent Reference Validation

Parent references (`UNITA' OPERATIVA PADRE `) must always point to existing `Codice` values:
```python
all_codici = set(df['Codice'].dropna().unique())
# Validate that parent references are in all_codici
```

### Cycle Detection

Hierarchical cycles are detected in `models/strutture.py` using `detect_cycles()` function. This prevents infinite loops when traversing org structure.

## File Naming Conventions

- Input files: `TNS_HR_Data.xls` (expected in `data/input/`)
- Backups: `TNS_HR_Data_backup_YYYYMMDD_HHMMSS.xls` (in `data/backups/`)
- Exports: `TNS_HR_Export_YYYYMMDD_HHMMSS.xlsx` (in `data/output/`)

## Important Notes

1. **Pydantic Only (No SQLModel)**: This project uses **Pydantic for data validation**, NOT SQLModel. The application validates and transforms Excel data in-memory, not a database. Always use:
   - `from pydantic import BaseModel, Field, field_validator` ✅
   - NOT `from sqlmodel import Field, SQLModel` ❌

2. **Column Name Quirk**: `UNITA' OPERATIVA PADRE ` has a trailing space in the actual Excel schema - this is intentional and must be preserved.

2. **Excel Engine Selection**:
   - `.xlsx` files use `openpyxl` engine
   - `.xls` files use `xlwt` engine for writing, `xlrd` for reading
   - Automatic engine selection in `ExcelHandler.save_data()`

3. **Streamlit Rerun Behavior**: After modifying session state DataFrames, use `st.rerun()` to refresh the UI and reflect changes.

4. **Validation Timing**: Pydantic validation happens at model instantiation. Business logic validation (parent refs, cycles) requires a second pass with access to all records.

5. **DataFrame Mutability**: Always use `.copy()` when creating derivative DataFrames to avoid unintended side effects on session state.
