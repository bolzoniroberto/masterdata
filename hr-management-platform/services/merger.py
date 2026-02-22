"""
Service per generazione foglio DB_TNS (merge TNS Personale + TNS Strutture)
"""
import pandas as pd
from typing import Tuple, List
import config


class DBTNSMerger:
    """Gestisce merge e generazione foglio DB_TNS"""
    
    @staticmethod
    def merge_data(
        personale_df: pd.DataFrame,
        strutture_df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Merge TNS Personale e TNS Strutture per creare DB_TNS.
        
        LOGICA:
        - DB_TNS = UNIONE di tutti i record Personale + Strutture
        - Ordine: prima Strutture (organigramma), poi Personale (dipendenti)
        - Conserva tutte le 26 colonne identiche
        
        Args:
            personale_df: DataFrame TNS Personale
            strutture_df: DataFrame TNS Strutture
            
        Returns:
            Tuple (db_tns_df, warnings_list)
        """
        warnings = []
        
        # Verifica che abbiano le stesse colonne
        if list(personale_df.columns) != list(strutture_df.columns):
            warnings.append(
                "ATTENZIONE: Personale e Strutture hanno colonne diverse! "
                "Procedendo comunque con merge."
            )
        
        # Assicura che entrambi abbiano le colonne standard (26 colonne)
        for col in config.EXCEL_COLUMNS:
            if col not in personale_df.columns:
                personale_df[col] = None
                warnings.append(f"Aggiunta colonna mancante a Personale: {col}")
            
            if col not in strutture_df.columns:
                strutture_df[col] = None
                warnings.append(f"Aggiunta colonna mancante a Strutture: {col}")
        
        # Riordina colonne secondo standard
        personale_df = personale_df[config.EXCEL_COLUMNS]
        strutture_df = strutture_df[config.EXCEL_COLUMNS]
        
        # Concatena: prima Strutture, poi Personale
        # Questo ordine è importante perché l'organigramma va prima dei dipendenti
        db_tns = pd.concat([strutture_df, personale_df], ignore_index=True)
        
        # Verifica integrità
        integrity_warnings = DBTNSMerger._check_integrity(db_tns, strutture_df, personale_df)
        warnings.extend(integrity_warnings)
        
        return db_tns, warnings
    
    @staticmethod
    def _check_integrity(
        db_tns: pd.DataFrame,
        strutture_df: pd.DataFrame,
        personale_df: pd.DataFrame
    ) -> List[str]:
        """
        Verifica integrità del merge.
        
        Args:
            db_tns: DataFrame risultante
            strutture_df: DataFrame originale Strutture
            personale_df: DataFrame originale Personale
            
        Returns:
            Lista warning
        """
        warnings = []
        
        # 1. Verifica conteggio record
        expected_count = len(strutture_df) + len(personale_df)
        actual_count = len(db_tns)
        
        if actual_count != expected_count:
            warnings.append(
                f"ANOMALIA: DB_TNS ha {actual_count} record, "
                f"attesi {expected_count} (Strutture: {len(strutture_df)}, "
                f"Personale: {len(personale_df)})"
            )
        
        # 2. Verifica univocità codici (Codice dovrebbe essere univoco in DB_TNS)
        duplicate_codes = db_tns[db_tns['Codice'].duplicated(keep=False)]
        if len(duplicate_codes) > 0:
            warnings.append(
                f"ATTENZIONE: {len(duplicate_codes)} codici duplicati trovati in DB_TNS"
            )
        
        # 3. Verifica riferimenti padri esistenti
        all_codici = set(db_tns['Codice'].dropna().unique())
        padri_referenziati = set(db_tns['UNITA\' OPERATIVA PADRE '].dropna().unique())
        padri_mancanti = padri_referenziati - all_codici
        
        if padri_mancanti:
            warnings.append(
                f"ATTENZIONE: {len(padri_mancanti)} codici padre referenziati "
                f"ma non presenti: {list(padri_mancanti)[:5]}..."
            )
        
        # 4. Verifica separazione Strutture/Personale (CF presente solo in Personale)
        strutture_with_cf = db_tns[
            (db_tns['TxCodFiscale'].notna()) &
            (db_tns['TxCodFiscale'].str.strip() != '')
        ]
        
        if len(strutture_with_cf) != len(personale_df):
            warnings.append(
                f"ANOMALIA: {len(strutture_with_cf)} record con CF in DB_TNS, "
                f"attesi {len(personale_df)} da Personale"
            )
        
        return warnings
    
    @staticmethod
    def validate_db_tns(db_tns: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Valida il foglio DB_TNS generato.
        
        Args:
            db_tns: DataFrame DB_TNS da validare
            
        Returns:
            Tuple (is_valid, errors_list)
        """
        errors = []
        
        # 1. Verifica presenza colonne obbligatorie
        missing_cols = [col for col in config.EXCEL_COLUMNS if col not in db_tns.columns]
        if missing_cols:
            errors.append(f"Colonne mancanti: {missing_cols}")
        
        # 2. Verifica almeno un record
        if len(db_tns) == 0:
            errors.append("DB_TNS vuoto!")
        
        # 3. Verifica campo Codice sempre valorizzato
        empty_codes = db_tns['Codice'].isna().sum()
        if empty_codes > 0:
            errors.append(f"{empty_codes} record senza Codice in DB_TNS")
        
        # 4. Verifica integrità referenziale padri
        all_codici = set(db_tns['Codice'].dropna().unique())
        padri = db_tns['UNITA\' OPERATIVA PADRE '].dropna()
        invalid_refs = padri[~padri.isin(all_codici)]
        
        if len(invalid_refs) > 0:
            errors.append(
                f"{len(invalid_refs)} riferimenti a padri inesistenti in DB_TNS"
            )
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    @staticmethod
    def split_db_tns(db_tns: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Separa DB_TNS in Strutture e Personale.
        Utile per reverse operation o analisi.
        
        Args:
            db_tns: DataFrame DB_TNS completo
            
        Returns:
            Tuple (strutture_df, personale_df)
        """
        # Separazione basata su presenza TxCodFiscale
        mask_personale = (
            db_tns['TxCodFiscale'].notna() &
            (db_tns['TxCodFiscale'].str.strip() != '')
        )
        
        personale = db_tns[mask_personale].copy()
        strutture = db_tns[~mask_personale].copy()
        
        return strutture, personale
    
    @staticmethod
    def get_statistics(db_tns: pd.DataFrame) -> dict:
        """
        Calcola statistiche sul DB_TNS.
        
        Args:
            db_tns: DataFrame DB_TNS
            
        Returns:
            Dict con statistiche
        """
        strutture, personale = DBTNSMerger.split_db_tns(db_tns)
        
        stats = {
            'total_records': len(db_tns),
            'strutture_count': len(strutture),
            'personale_count': len(personale),
            'unique_codes': db_tns['Codice'].nunique(),
            'duplicate_codes': db_tns['Codice'].duplicated().sum(),
            'records_with_parent': db_tns['UNITA\' OPERATIVA PADRE '].notna().sum(),
            'root_structures': len(strutture[strutture['UNITA\' OPERATIVA PADRE '].isna()]),
            'complete_personale': personale[
                personale[['TxCodFiscale', 'Titolare', 'Codice', 'Unità Organizzativa']]
                .notna().all(axis=1)
            ].shape[0],
            'complete_strutture': strutture[
                strutture[['Codice', 'DESCRIZIONE']]
                .notna().all(axis=1)
            ].shape[0]
        }
        
        return stats
