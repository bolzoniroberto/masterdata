"""
Service per validazione dati TNS usando modelli Pydantic
"""
import pandas as pd
from typing import List, Dict, Tuple
from models.personale import PersonaleRecord
from models.strutture import StrutturaRecord, detect_cycles
from pydantic import ValidationError


class ValidationResult:
    """Risultato validazione con dettagli errori"""
    
    def __init__(self):
        self.errors: List[Dict] = []
        self.warnings: List[Dict] = []
        self.valid_count: int = 0
        self.invalid_count: int = 0
    
    def add_error(self, row_index: int, field: str, message: str, record_identifier: str = ""):
        """Aggiunge errore bloccante"""
        self.errors.append({
            'row': row_index,
            'field': field,
            'message': message,
            'identifier': record_identifier,
            'type': 'error'
        })
        self.invalid_count += 1
    
    def add_warning(self, row_index: int, field: str, message: str, record_identifier: str = ""):
        """Aggiunge warning non bloccante"""
        self.warnings.append({
            'row': row_index,
            'field': field,
            'message': message,
            'identifier': record_identifier,
            'type': 'warning'
        })
    
    def is_valid(self) -> bool:
        """Ritorna True se nessun errore bloccante"""
        return len(self.errors) == 0
    
    def get_summary(self) -> str:
        """Ritorna summary testuale"""
        return (
            f"Validazione: {self.valid_count} OK, "
            f"{self.invalid_count} errori, "
            f"{len(self.warnings)} warning"
        )


class DataValidator:
    """Validatore per dati TNS Personale e Strutture"""
    
    @staticmethod
    def validate_personale(df: pd.DataFrame) -> ValidationResult:
        """
        Valida DataFrame TNS Personale.
        
        Args:
            df: DataFrame da validare
            
        Returns:
            ValidationResult con dettagli validazione
        """
        result = ValidationResult()
        
        # Converti NaN in None per compatibilità Pydantic
        df_clean = df.where(pd.notna(df), None)
        
        for idx, row in df_clean.iterrows():
            row_dict = row.to_dict()
            
            try:
                # Validazione Pydantic
                record = PersonaleRecord(**row_dict)
                
                # Validazione business logic
                business_errors = record.get_validation_errors()
                if business_errors:
                    for err in business_errors:
                        result.add_warning(
                            idx, 
                            'business_logic', 
                            err,
                            record.tx_cod_fiscale
                        )
                
                # Verifica completezza
                if not record.is_complete():
                    result.add_warning(
                        idx,
                        'completeness',
                        'Record incompleto: mancano campi obbligatori',
                        record.tx_cod_fiscale
                    )
                
                result.valid_count += 1
                
            except ValidationError as e:
                # Errori Pydantic
                for error in e.errors():
                    field = error['loc'][0] if error['loc'] else 'unknown'
                    message = error['msg']
                    identifier = row_dict.get('TxCodFiscale', f"row_{idx}")
                    
                    result.add_error(idx, field, message, identifier)
            
            except Exception as e:
                result.add_error(idx, 'general', str(e), f"row_{idx}")
        
        return result
    
    @staticmethod
    def validate_strutture(df: pd.DataFrame) -> ValidationResult:
        """
        Valida DataFrame TNS Strutture.
        
        Args:
            df: DataFrame da validare
            
        Returns:
            ValidationResult con dettagli validazione
        """
        result = ValidationResult()
        
        # Converti NaN in None
        df_clean = df.where(pd.notna(df), None)
        
        # Prima passata: validazione Pydantic e costruzione dict
        strutture_dict = {}
        
        for idx, row in df_clean.iterrows():
            row_dict = row.to_dict()
            
            try:
                # Validazione Pydantic
                record = StrutturaRecord(**row_dict)
                strutture_dict[record.codice] = record
                
                # Verifica completezza
                if not record.is_complete():
                    result.add_warning(
                        idx,
                        'completeness',
                        'Record incompleto: mancano campi obbligatori',
                        record.codice
                    )
                
                result.valid_count += 1
                
            except ValidationError as e:
                # Errori Pydantic
                for error in e.errors():
                    field = error['loc'][0] if error['loc'] else 'unknown'
                    message = error['msg']
                    identifier = row_dict.get('Codice', f"row_{idx}")
                    
                    result.add_error(idx, field, message, identifier)
            
            except Exception as e:
                result.add_error(idx, 'general', str(e), f"row_{idx}")
        
        # Seconda passata: validazione business logic (padre esistente, cicli)
        all_codici = set(strutture_dict.keys())
        
        for idx, row in df_clean.iterrows():
            codice = row.get('Codice')
            if codice in strutture_dict:
                record = strutture_dict[codice]
                
                # Validazione business logic
                business_errors = record.get_validation_errors(all_codici)
                if business_errors:
                    for err in business_errors:
                        result.add_error(
                            idx,
                            'business_logic',
                            err,
                            record.codice
                        )
        
        # Rilevamento cicli
        cycle_errors = detect_cycles(strutture_dict)
        if cycle_errors:
            for err in cycle_errors:
                result.add_error(-1, 'hierarchy', err, 'cycle_detection')
        
        return result
    
    @staticmethod
    def find_orphan_structures(
        strutture_df: pd.DataFrame,
        personale_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Trova strutture orfane (senza dipendenti assegnati).
        
        Args:
            strutture_df: DataFrame TNS Strutture
            personale_df: DataFrame TNS Personale
            
        Returns:
            DataFrame con strutture orfane
        """
        # Codici strutture presenti
        codici_strutture = set(strutture_df['Codice'].dropna().unique())
        
        # Codici strutture referenziate da personale (come padre)
        codici_usati = set(personale_df['UNITA\' OPERATIVA PADRE '].dropna().unique())
        
        # Strutture mai referenziate
        codici_orfani = codici_strutture - codici_usati
        
        # Filtra DataFrame
        orphans = strutture_df[strutture_df['Codice'].isin(codici_orfani)]
        
        return orphans
    
    @staticmethod
    def find_incomplete_records_personale(df: pd.DataFrame) -> pd.DataFrame:
        """
        Trova record Personale incompleti (campi obbligatori mancanti).
        
        Args:
            df: DataFrame TNS Personale
            
        Returns:
            DataFrame con record incompleti
        """
        mandatory_fields = ['TxCodFiscale', 'Titolare', 'Codice', 'Unità Organizzativa']
        
        # Maschera record incompleti (almeno un campo obbligatorio mancante)
        mask = df[mandatory_fields].isna().any(axis=1)
        
        return df[mask]
    
    @staticmethod
    def find_incomplete_records_strutture(df: pd.DataFrame) -> pd.DataFrame:
        """
        Trova record Strutture incompleti.
        
        Args:
            df: DataFrame TNS Strutture
            
        Returns:
            DataFrame con record incompleti
        """
        mandatory_fields = ['Codice', 'DESCRIZIONE']
        
        # Maschera record incompleti
        mask = df[mandatory_fields].isna().any(axis=1)
        
        return df[mask]
    
    @staticmethod
    def check_duplicate_keys(df: pd.DataFrame, key_field: str) -> Tuple[bool, pd.DataFrame]:
        """
        Verifica duplicati in un campo chiave.
        
        Args:
            df: DataFrame da controllare
            key_field: Nome campo chiave
            
        Returns:
            Tuple (has_duplicates, duplicates_df)
        """
        duplicates = df[df[key_field].duplicated(keep=False)]
        return len(duplicates) > 0, duplicates
