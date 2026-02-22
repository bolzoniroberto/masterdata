"""
Configurazione globale piattaforma HR Management
"""
from pathlib import Path
from datetime import datetime

# Percorsi base
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"
BACKUP_DIR = DATA_DIR / "backups"

# Percorsi database
DB_DIR = DATA_DIR / "db"
DB_PATH = DB_DIR / "app.db"
DB_BACKUP_DIR = DB_DIR / "backups"

# Percorsi snapshot versioni
SNAPSHOTS_DIR = DATA_DIR / "snapshots"

# Nomi file
INPUT_FILE_NAME = "TNS_HR_Data.xls"
INPUT_FILE_PATH = INPUT_DIR / INPUT_FILE_NAME

# Nomi fogli Excel
SHEET_PERSONALE = "TNS Personale"
SHEET_STRUTTURE = "TNS Strutture"
SHEET_DB_TNS = "DB_TNS"

# Colonne Excel (ordine esatto del file reale)
EXCEL_COLUMNS = [
    "Unità Organizzativa",
    "CDCCOSTO",
    "TxCodFiscale",
    "DESCRIZIONE",
    "Titolare",
    "LIVELLO",
    "Codice",
    "UNITA' OPERATIVA PADRE ",
    "RUOLI OltreV",
    "RUOLI",
    "Viaggiatore",
    "Segr_Redaz",
    "Approvatore",
    "Cassiere",
    "Visualizzatori",
    "Segretario",
    "Controllore",
    "Amministrazione",
    "SegreteriA Red. Ass.ta",
    "SegretariO Ass.to",
    "Controllore Ass.to",
    "RuoliAFC",
    "RuoliHR",
    "AltriRuoli",
    "Sede_TNS",
    "GruppoSind"
]

# Campi obbligatori
MANDATORY_PERSONALE = ["TxCodFiscale", "Titolare", "Codice", "Unità Organizzativa"]
MANDATORY_STRUTTURE = ["Codice", "DESCRIZIONE"]

# Campi chiave per identificazione
KEY_FIELD_PERSONALE = "TxCodFiscale"
KEY_FIELD_STRUTTURE = "Codice"
PARENT_FIELD = "UNITA' OPERATIVA PADRE "

# Settings UI
PAGE_TITLE = "HR Masterdata Management - Gruppo Il Sole 24 ORE"
PAGE_ICON = "📊"
LAYOUT = "wide"

# Versionamento
BACKUP_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"
MAX_BACKUPS = 50

def get_backup_filename(original_name: str) -> str:
    """Genera nome file backup con timestamp"""
    timestamp = datetime.now().strftime(BACKUP_TIMESTAMP_FORMAT)
    stem = Path(original_name).stem
    ext = Path(original_name).suffix
    return f"{stem}_backup_{timestamp}{ext}"

def get_output_filename(prefix: str = "TNS_HR_Data") -> str:
    """Genera nome file output"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.xlsx"

# Ollama Configuration (per bot conversazionale)
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3"  # Alternative: "mistral", "phi3"
OLLAMA_TIMEOUT = 60  # seconds

# Bot Configuration
BOT_MAX_HISTORY = 20  # Max conversation turns
BOT_MAX_BATCH_SIZE = 100  # Max record per batch operation
