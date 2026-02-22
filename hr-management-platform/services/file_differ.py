"""
Service per confronto file Excel TNS.
Identifica differenze tra due versioni: aggiunte, eliminazioni, modifiche.
"""
import pandas as pd
from typing import Dict, List, Tuple, Any
from datetime import datetime


class DiffResult:
    """Risultato confronto con statistiche e dettagli"""

    def __init__(self):
        self.added_records: List[Dict] = []  # Record aggiunti
        self.deleted_records: List[Dict] = []  # Record eliminati
        self.modified_records: List[Dict] = []  # Record modificati con dettagli

        # Statistiche
        self.added_count: int = 0
        self.deleted_count: int = 0
        self.modified_count: int = 0
        self.unchanged_count: int = 0

    def get_summary(self) -> str:
        """Ritorna summary testuale"""
        return (
            f"Aggiunti: {self.added_count} | "
            f"Eliminati: {self.deleted_count} | "
            f"Modificati: {self.modified_count} | "
            f"Invariati: {self.unchanged_count}"
        )

    def has_changes(self) -> bool:
        """True se ci sono differenze"""
        return (self.added_count + self.deleted_count + self.modified_count) > 0


class FileDiffer:
    """
    Confronta due file Excel TNS e identifica differenze.

    Workflow:
    1. Carica due DataFrame (old vs new)
    2. Identifica chiave univoca (TxCodFiscale per Personale, Codice per Strutture)
    3. Confronta record per record
    4. Classifica differenze: added, deleted, modified
    5. Per modified: identifica campi modificati con before/after
    """

    @staticmethod
    def compare_dataframes(
        df_old: pd.DataFrame,
        df_new: pd.DataFrame,
        key_field: str,
        record_type: str = "Personale"
    ) -> DiffResult:
        """
        Confronta due DataFrame e genera DiffResult.

        Args:
            df_old: DataFrame versione precedente
            df_new: DataFrame versione nuova
            key_field: Campo chiave univoca (es. TxCodFiscale, Codice)
            record_type: Tipo record per etichette (Personale/Strutture)

        Returns:
            DiffResult con dettagli differenze
        """
        result = DiffResult()

        # Converti NaN in None per confronto
        df_old_clean = df_old.where(pd.notna(df_old), None)
        df_new_clean = df_new.where(pd.notna(df_new), None)

        # Estrai chiavi univoche
        old_keys = set(df_old_clean[key_field].dropna().unique())
        new_keys = set(df_new_clean[key_field].dropna().unique())

        # Identifica aggiunti, eliminati
        added_keys = new_keys - old_keys
        deleted_keys = old_keys - new_keys
        common_keys = old_keys & new_keys

        # Record aggiunti
        for key in added_keys:
            record = df_new_clean[df_new_clean[key_field] == key].iloc[0].to_dict()
            result.added_records.append({
                'key': key,
                'record_type': record_type,
                'data': record
            })
        result.added_count = len(added_keys)

        # Record eliminati
        for key in deleted_keys:
            record = df_old_clean[df_old_clean[key_field] == key].iloc[0].to_dict()
            result.deleted_records.append({
                'key': key,
                'record_type': record_type,
                'data': record
            })
        result.deleted_count = len(deleted_keys)

        # Record comuni: verifica modifiche
        for key in common_keys:
            old_record = df_old_clean[df_old_clean[key_field] == key].iloc[0]
            new_record = df_new_clean[df_new_clean[key_field] == key].iloc[0]

            # Confronta campo per campo
            changes = []
            for col in df_old_clean.columns:
                old_val = old_record[col]
                new_val = new_record[col]

                # Considera cambiamento solo se diverso
                if old_val != new_val:
                    # Gestisci confronto None vs stringa vuota
                    if not (pd.isna(old_val) and new_val == ''):
                        if not (old_val == '' and pd.isna(new_val)):
                            changes.append({
                                'field': col,
                                'old_value': old_val,
                                'new_value': new_val
                            })

            if changes:
                result.modified_records.append({
                    'key': key,
                    'record_type': record_type,
                    'changes': changes,
                    'old_record': old_record.to_dict(),
                    'new_record': new_record.to_dict()
                })
                result.modified_count += 1
            else:
                result.unchanged_count += 1

        return result

    @staticmethod
    def compare_full_files(
        personale_old: pd.DataFrame,
        strutture_old: pd.DataFrame,
        personale_new: pd.DataFrame,
        strutture_new: pd.DataFrame
    ) -> Tuple[DiffResult, DiffResult]:
        """
        Confronta file completo (Personale + Strutture).

        Returns:
            Tuple (personale_diff, strutture_diff)
        """
        # Confronta Personale
        personale_diff = FileDiffer.compare_dataframes(
            personale_old,
            personale_new,
            key_field='TxCodFiscale',
            record_type='Personale'
        )

        # Confronta Strutture
        strutture_diff = FileDiffer.compare_dataframes(
            strutture_old,
            strutture_new,
            key_field='Codice',
            record_type='Strutture'
        )

        return personale_diff, strutture_diff

    @staticmethod
    def export_diff_report(
        personale_diff: DiffResult,
        strutture_diff: DiffResult,
        output_path: str = None
    ) -> pd.DataFrame:
        """
        Genera report Excel con differenze.

        Crea DataFrame con:
        - Tipo modifica (Added/Deleted/Modified)
        - Record type (Personale/Strutture)
        - Chiave
        - Dettagli modifiche

        Returns:
            DataFrame report
        """
        report_rows = []

        # Aggiunti Personale
        for item in personale_diff.added_records:
            report_rows.append({
                'Timestamp': datetime.now().isoformat(),
                'Tipo Modifica': 'AGGIUNTO',
                'Record Type': 'Personale',
                'Chiave': item['key'],
                'Campo': 'N/A',
                'Valore Precedente': 'N/A',
                'Valore Nuovo': str(item['data'])
            })

        # Eliminati Personale
        for item in personale_diff.deleted_records:
            report_rows.append({
                'Timestamp': datetime.now().isoformat(),
                'Tipo Modifica': 'ELIMINATO',
                'Record Type': 'Personale',
                'Chiave': item['key'],
                'Campo': 'N/A',
                'Valore Precedente': str(item['data']),
                'Valore Nuovo': 'N/A'
            })

        # Modificati Personale
        for item in personale_diff.modified_records:
            for change in item['changes']:
                report_rows.append({
                    'Timestamp': datetime.now().isoformat(),
                    'Tipo Modifica': 'MODIFICATO',
                    'Record Type': 'Personale',
                    'Chiave': item['key'],
                    'Campo': change['field'],
                    'Valore Precedente': str(change['old_value']),
                    'Valore Nuovo': str(change['new_value'])
                })

        # Aggiunti Strutture
        for item in strutture_diff.added_records:
            report_rows.append({
                'Timestamp': datetime.now().isoformat(),
                'Tipo Modifica': 'AGGIUNTO',
                'Record Type': 'Strutture',
                'Chiave': item['key'],
                'Campo': 'N/A',
                'Valore Precedente': 'N/A',
                'Valore Nuovo': str(item['data'])
            })

        # Eliminati Strutture
        for item in strutture_diff.deleted_records:
            report_rows.append({
                'Timestamp': datetime.now().isoformat(),
                'Tipo Modifica': 'ELIMINATO',
                'Record Type': 'Strutture',
                'Chiave': item['key'],
                'Campo': 'N/A',
                'Valore Precedente': str(item['data']),
                'Valore Nuovo': 'N/A'
            })

        # Modificati Strutture
        for item in strutture_diff.modified_records:
            for change in item['changes']:
                report_rows.append({
                    'Timestamp': datetime.now().isoformat(),
                    'Tipo Modifica': 'MODIFICATO',
                    'Record Type': 'Strutture',
                    'Chiave': item['key'],
                    'Campo': change['field'],
                    'Valore Precedente': str(change['old_value']),
                    'Valore Nuovo': str(change['new_value'])
                })

        report_df = pd.DataFrame(report_rows)

        # Export se specificato
        if output_path:
            report_df.to_excel(output_path, index=False)

        return report_df
