"""
Service per lettura e scrittura file Excel TNS
"""
import pandas as pd
from pathlib import Path
from typing import Tuple, Optional
import config
from datetime import datetime


class ExcelHandler:
    """Gestisce operazioni I/O su file Excel TNS"""
    
    def __init__(self, file_path: Optional[Path] = None):
        """
        Inizializza handler.
        
        Args:
            file_path: Path al file Excel. Se None, usa config.INPUT_FILE_PATH
        """
        self.file_path = file_path or config.INPUT_FILE_PATH
        self.personale_df: Optional[pd.DataFrame] = None
        self.strutture_df: Optional[pd.DataFrame] = None
        self.db_tns_df: Optional[pd.DataFrame] = None
        
    def load_data(self) -> Tuple[pd.DataFrame, pd.DataFrame, Optional[pd.DataFrame]]:
        """
        Carica tutti i fogli dal file Excel.
        
        Returns:
            Tuple (personale_df, strutture_df, db_tns_df)
            
        Raises:
            FileNotFoundError: se file non esiste
            ValueError: se fogli richiesti mancano
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"File non trovato: {self.file_path}")
        
        # Leggi file Excel
        xls = pd.ExcelFile(self.file_path)
        
        # Verifica presenza fogli obbligatori
        required_sheets = [config.SHEET_PERSONALE, config.SHEET_STRUTTURE]
        missing_sheets = [s for s in required_sheets if s not in xls.sheet_names]
        if missing_sheets:
            raise ValueError(f"Fogli mancanti: {missing_sheets}")
        
        # Carica fogli
        self.personale_df = pd.read_excel(xls, sheet_name=config.SHEET_PERSONALE)
        self.strutture_df = pd.read_excel(xls, sheet_name=config.SHEET_STRUTTURE)
        
        # DB_TNS è opzionale (potrebbe non esistere se non ancora generato)
        if config.SHEET_DB_TNS in xls.sheet_names:
            self.db_tns_df = pd.read_excel(xls, sheet_name=config.SHEET_DB_TNS)
        else:
            self.db_tns_df = None
        
        return self.personale_df, self.strutture_df, self.db_tns_df
    
    def save_data(
        self,
        personale_df: pd.DataFrame,
        strutture_df: pd.DataFrame,
        db_tns_df: Optional[pd.DataFrame] = None,
        output_path: Optional[Path] = None,
        create_backup: bool = True
    ) -> Path:
        """
        Salva dataframes su file Excel con 3 fogli.
        
        Args:
            personale_df: DataFrame TNS Personale
            strutture_df: DataFrame TNS Strutture
            db_tns_df: DataFrame DB_TNS (opzionale)
            output_path: Path output. Se None, usa file input originale
            create_backup: Se True, crea backup prima di sovrascrivere
            
        Returns:
            Path del file salvato
        """
        target_path = output_path or self.file_path
        
        # Crea backup se richiesto e file esiste
        if create_backup and target_path.exists():
            self._create_backup(target_path)
        
        # Assicura che le directory esistano
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Scrivi Excel con engine openpyxl per .xlsx o xlwt per .xls
        if target_path.suffix == '.xlsx':
            engine = 'openpyxl'
        elif target_path.suffix == '.xls':
            engine = 'xlwt'
        else:
            # Default to xlsx
            target_path = target_path.with_suffix('.xlsx')
            engine = 'openpyxl'
        
        with pd.ExcelWriter(target_path, engine=engine) as writer:
            # Ordine fogli: DB_TNS, TNS Personale, TNS Strutture
            if db_tns_df is not None:
                db_tns_df.to_excel(writer, sheet_name=config.SHEET_DB_TNS, index=False)
            
            personale_df.to_excel(writer, sheet_name=config.SHEET_PERSONALE, index=False)
            strutture_df.to_excel(writer, sheet_name=config.SHEET_STRUTTURE, index=False)
        
        return target_path
    
    def _create_backup(self, file_path: Path) -> Path:
        """
        Crea backup del file con timestamp.
        
        Args:
            file_path: File da backuppare
            
        Returns:
            Path del file backup creato
        """
        backup_name = config.get_backup_filename(file_path.name)
        backup_path = config.BACKUP_DIR / backup_name
        
        # Assicura esistenza directory backup
        config.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        
        # Copia file
        import shutil
        shutil.copy2(file_path, backup_path)
        
        # Cleanup vecchi backup se superano il limite
        self._cleanup_old_backups()
        
        return backup_path
    
    def _cleanup_old_backups(self):
        """Rimuove backup più vecchi se superano MAX_BACKUPS"""
        if not config.BACKUP_DIR.exists():
            return
        
        # Lista backup ordinati per data modifica
        backups = sorted(
            config.BACKUP_DIR.glob("*_backup_*.xls*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        # Rimuovi backup eccedenti
        for old_backup in backups[config.MAX_BACKUPS:]:
            old_backup.unlink()
    
    def export_to_output(
        self,
        personale_df: pd.DataFrame,
        strutture_df: pd.DataFrame,
        db_tns_df: Optional[pd.DataFrame] = None,
        prefix: str = "TNS_HR_Export"
    ) -> Path:
        """
        Esporta dati in directory output con nome timestampato.
        
        Args:
            personale_df: DataFrame TNS Personale
            strutture_df: DataFrame TNS Strutture
            db_tns_df: DataFrame DB_TNS
            prefix: Prefisso nome file
            
        Returns:
            Path del file esportato
        """
        filename = config.get_output_filename(prefix)
        output_path = config.OUTPUT_DIR / filename
        
        return self.save_data(
            personale_df,
            strutture_df,
            db_tns_df,
            output_path=output_path,
            create_backup=False  # Non serve backup per nuovi export
        )
    
    def get_backup_list(self) -> list[dict]:
        """
        Restituisce lista backup disponibili.
        
        Returns:
            Lista dizionari con info backup (nome, data, dimensione)
        """
        if not config.BACKUP_DIR.exists():
            return []
        
        backups = []
        for backup_file in sorted(
            config.BACKUP_DIR.glob("*_backup_*.xls*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        ):
            stat = backup_file.stat()
            backups.append({
                'name': backup_file.name,
                'path': backup_file,
                'date': datetime.fromtimestamp(stat.st_mtime),
                'size_mb': stat.st_size / (1024 * 1024)
            })
        
        return backups
    
    def restore_backup(self, backup_path: Path) -> Tuple[pd.DataFrame, pd.DataFrame, Optional[pd.DataFrame]]:
        """
        Ripristina dati da un backup.
        
        Args:
            backup_path: Path del backup da ripristinare
            
        Returns:
            Tuple (personale_df, strutture_df, db_tns_df)
        """
        # Cambia temporaneamente il file path
        original_path = self.file_path
        self.file_path = backup_path
        
        try:
            result = self.load_data()
        finally:
            self.file_path = original_path
        
        return result
