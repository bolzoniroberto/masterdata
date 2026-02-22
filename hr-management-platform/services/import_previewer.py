"""
Import Previewer - Preview modifiche prima dell'import con severity classification
"""
import pandas as pd
from typing import Tuple, Dict
from services.database import DatabaseHandler
from services.file_differ import FileDiffer, DiffResult


class ImportPreview:
    """
    Preview modifiche prima di importare un nuovo Excel nel database.

    Usa FileDiffer esistente per confrontare stato attuale DB con nuovo Excel,
    classificando le modifiche per severity (CRITICAL/HIGH/MEDIUM/LOW).
    """

    def __init__(self, db_handler: DatabaseHandler):
        """
        Inizializza preview service.

        Args:
            db_handler: Istanza DatabaseHandler per accesso al DB corrente
        """
        self.db = db_handler

    def preview_import(self, personale_new: pd.DataFrame,
                      strutture_new: pd.DataFrame) -> Tuple[DiffResult, DiffResult, Dict]:
        """
        Compara nuovo Excel con stato corrente database.

        Args:
            personale_new: DataFrame TNS Personale dal nuovo file
            strutture_new: DataFrame TNS Strutture dal nuovo file

        Returns:
            Tuple: (personale_diff, strutture_diff, summary_dict)
                - personale_diff: DiffResult per confronto personale
                - strutture_diff: DiffResult per confronto strutture
                - summary_dict: Statistiche aggregate con severity classification
        """
        # Esporta stato corrente da database
        personale_old, strutture_old = self.db.export_to_dataframe()

        # Usa FileDiffer esistente per confronto completo
        personale_diff, strutture_diff = FileDiffer.compare_full_files(
            personale_old, strutture_old,
            personale_new, strutture_new
        )

        # Genera summary con severity classification
        summary = self._generate_severity_summary(personale_diff, strutture_diff)

        return personale_diff, strutture_diff, summary

    def _generate_severity_summary(self, personale_diff: DiffResult,
                                   strutture_diff: DiffResult) -> Dict:
        """
        Genera summary delle modifiche con conteggio per severity.

        Classifica le modifiche in:
        - CRITICAL: Approvatore, Controllore, Cassiere, Viaggiatore
        - HIGH: UNITA_OPERATIVA_PADRE, Codice, DESCRIZIONE
        - MEDIUM: Titolare, Unità_Organizzativa, Sede_TNS, Segretario
        - LOW: Altri campi

        Args:
            personale_diff: DiffResult personale
            strutture_diff: DiffResult strutture

        Returns:
            Dict con contatori severity e dettagli critical/high
        """
        summary = {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'critical_details': [],
            'high_details': [],
            'total_added': personale_diff.added_count + strutture_diff.added_count,
            'total_deleted': personale_diff.deleted_count + strutture_diff.deleted_count,
            'total_modified': personale_diff.modified_count + strutture_diff.modified_count
        }

        # Analizza modifiche Personale
        for modified in personale_diff.modified_records:
            for change in modified['changes']:
                severity = self._classify_field_severity(change['field'])

                # Incrementa contatore severity
                summary[severity.lower()] += 1

                # Salva dettagli per CRITICAL e HIGH
                if severity == 'CRITICAL':
                    summary['critical_details'].append({
                        'tipo': 'Personale',
                        'chiave': modified['key'],
                        'campo': change['field'],
                        'prima': change['old_value'],
                        'dopo': change['new_value']
                    })
                elif severity == 'HIGH':
                    summary['high_details'].append({
                        'tipo': 'Personale',
                        'chiave': modified['key'],
                        'campo': change['field'],
                        'prima': change['old_value'],
                        'dopo': change['new_value']
                    })

        # Analizza modifiche Strutture
        for modified in strutture_diff.modified_records:
            for change in modified['changes']:
                severity = self._classify_field_severity(change['field'])

                # Incrementa contatore
                summary[severity.lower()] += 1

                # Salva dettagli
                if severity == 'CRITICAL':
                    summary['critical_details'].append({
                        'tipo': 'Struttura',
                        'chiave': modified['key'],
                        'campo': change['field'],
                        'prima': change['old_value'],
                        'dopo': change['new_value']
                    })
                elif severity == 'HIGH':
                    summary['high_details'].append({
                        'tipo': 'Struttura',
                        'chiave': modified['key'],
                        'campo': change['field'],
                        'prima': change['old_value'],
                        'dopo': change['new_value']
                    })

        return summary

    def _classify_field_severity(self, field_name: str) -> str:
        """
        Classifica severity di un campo modificato.

        Args:
            field_name: Nome del campo

        Returns:
            Severity: 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
        """
        field_lower = field_name.replace('_', ' ').lower()

        # CRITICAL: Ruoli di approvazione
        critical_fields = ['approvatore', 'controllore', 'cassiere', 'viaggiatore']
        if any(cf in field_lower for cf in critical_fields):
            return 'CRITICAL'

        # HIGH: Campi strutturali
        high_fields = ['unita operativa padre', 'codice', 'descrizione']
        if any(hf in field_lower for hf in high_fields):
            return 'HIGH'

        # MEDIUM: Campi informativi importanti
        medium_fields = ['titolare', 'unità organizzativa', 'sede', 'segretario']
        if any(mf in field_lower for mf in medium_fields):
            return 'MEDIUM'

        # LOW: Tutti gli altri
        return 'LOW'
