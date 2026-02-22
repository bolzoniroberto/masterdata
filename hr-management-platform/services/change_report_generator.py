"""
Change Report Generator - Genera report modifiche human-readable in italiano
"""
import pandas as pd
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from services.database import DatabaseHandler


class ChangeReportGenerator:
    """
    Genera report leggibili delle modifiche dal database audit_log.

    Trasforma JSON audit log in descrizioni italiane comprensibili:
    - "Dipendente ROSSI MARIO ha cambiato approvatore da BIANCHI a VERDI"
    - "Struttura DIREZIONE ha cambiato padre da ROOT a AMMINISTRAZIONE"
    """

    def __init__(self, db_handler: DatabaseHandler):
        """
        Inizializza generator.

        Args:
            db_handler: Istanza DatabaseHandler per accesso audit_log
        """
        self.db = db_handler

    def generate_import_report(self, import_version_id: int) -> pd.DataFrame:
        """
        Genera report per un singolo import version.

        Args:
            import_version_id: ID della versione import da analizzare

        Returns:
            DataFrame con colonne:
            - Timestamp: Data/ora modifica
            - Gravità: CRITICAL/HIGH/MEDIUM/LOW
            - Tipo: personale/strutture
            - Operazione: Aggiunta/Modifica/Eliminazione
            - Chiave: TxCodFiscale o Codice
            - Campo: Nome campo modificato
            - Descrizione: Frase italiana descrittiva
        """
        cursor = self.db.conn.cursor()

        try:
            # Query audit log per questa versione
            cursor.execute("""
                SELECT timestamp, table_name, operation, record_key,
                       before_values, after_values, change_severity, field_name
                FROM audit_log
                WHERE import_version_id = ?
                ORDER BY timestamp DESC
            """, (import_version_id,))

            rows = cursor.fetchall()

            if not rows:
                return pd.DataFrame(columns=[
                    'Timestamp', 'Gravità', 'Tipo', 'Operazione',
                    'Chiave', 'Campo', 'Descrizione'
                ])

            # Converti in report entries
            report_entries = []
            for row in rows:
                timestamp, table_name, operation, record_key, before_json, after_json, severity, field_name = row

                # Parse JSON
                before = json.loads(before_json) if before_json else None
                after = json.loads(after_json) if after_json else None

                # Genera descrizione italiana
                description = self._generate_change_description(
                    operation, table_name, record_key, field_name, before, after
                )

                report_entries.append({
                    'Timestamp': timestamp,
                    'Gravità': severity or 'MEDIUM',
                    'Tipo': table_name,
                    'Operazione': self._translate_operation(operation),
                    'Chiave': record_key,
                    'Campo': self._translate_field_name(field_name) if field_name else '-',
                    'Descrizione': description
                })

            return pd.DataFrame(report_entries)

        finally:
            cursor.close()

    def generate_summary_report(self, days: int = 30) -> pd.DataFrame:
        """
        Genera summary aggregato delle modifiche degli ultimi N giorni.

        Args:
            days: Numero giorni da includere nel report

        Returns:
            DataFrame con report completo modifiche recenti
        """
        cursor = self.db.conn.cursor()

        try:
            # Calcola data limite
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')

            # Query tutte le modifiche recenti
            cursor.execute("""
                SELECT timestamp, table_name, operation, record_key,
                       before_values, after_values, change_severity, field_name
                FROM audit_log
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
            """, (cutoff_date,))

            rows = cursor.fetchall()

            if not rows:
                return pd.DataFrame(columns=[
                    'Timestamp', 'Gravità', 'Tipo', 'Operazione',
                    'Chiave', 'Campo', 'Descrizione'
                ])

            # Converti in report entries
            report_entries = []
            for row in rows:
                timestamp, table_name, operation, record_key, before_json, after_json, severity, field_name = row

                # Parse JSON
                before = json.loads(before_json) if before_json else None
                after = json.loads(after_json) if after_json else None

                # Genera descrizione
                description = self._generate_change_description(
                    operation, table_name, record_key, field_name, before, after
                )

                report_entries.append({
                    'Timestamp': timestamp,
                    'Gravità': severity or 'MEDIUM',
                    'Tipo': table_name,
                    'Operazione': self._translate_operation(operation),
                    'Chiave': record_key,
                    'Campo': self._translate_field_name(field_name) if field_name else '-',
                    'Descrizione': description
                })

            return pd.DataFrame(report_entries)

        finally:
            cursor.close()

    def export_to_excel(self, report_df: pd.DataFrame, output_path: str):
        """
        Export report a Excel con color-coding per severity.

        Args:
            report_df: DataFrame report da esportare
            output_path: Path file Excel output
        """
        # Basic export (color-coding opzionale, non prioritario)
        report_df.to_excel(output_path, index=False, engine='openpyxl')

    # === HELPER METHODS ===

    def _translate_operation(self, operation: str) -> str:
        """Traduce operation code in italiano"""
        translations = {
            'INSERT': 'Aggiunta',
            'UPDATE': 'Modifica',
            'DELETE': 'Eliminazione'
        }
        return translations.get(operation, operation)

    def _translate_field_name(self, field: str) -> str:
        """Traduce nome campo tecnico in italiano leggibile"""
        if not field:
            return ''

        translations = {
            'Approvatore': 'Approvatore',
            'Controllore': 'Controllore',
            'Cassiere': 'Cassiere',
            'Viaggiatore': 'Viaggiatore',
            'Segretario': 'Segretario',
            'UNITA_OPERATIVA_PADRE': 'Padre organizzativo',
            'Unità_Organizzativa': 'Unità organizzativa',
            'DESCRIZIONE': 'Descrizione',
            'Codice': 'Codice',
            'Titolare': 'Titolare',
            'Sede_TNS': 'Sede',
            'TxCodFiscale': 'Codice fiscale',
            'GruppoSind': 'Gruppo sindacale'
        }

        # Try exact match first
        if field in translations:
            return translations[field]

        # Fallback: capitalize and replace underscores
        return field.replace('_', ' ').title()

    def _generate_change_description(self, operation: str, table_name: str,
                                     record_key: str, field_name: Optional[str],
                                     before: Optional[Dict], after: Optional[Dict]) -> str:
        """
        Genera descrizione italiana completa della modifica.

        Examples:
        - "Dipendente ROSSI MARIO ha cambiato approvatore da BIANCHI a VERDI"
        - "Struttura DIREZIONE ha cambiato padre organizzativo da ROOT a AMMINISTRAZIONE"
        - "Aggiunto nuovo dipendente ROSSI MARIO (CF: RSSMRA80A01H501Z)"
        - "Eliminata struttura DIREZIONE MARKETING"

        Args:
            operation: INSERT/UPDATE/DELETE
            table_name: personale/strutture
            record_key: TxCodFiscale o Codice
            field_name: Nome campo modificato (solo per UPDATE)
            before: Valori precedenti (dict JSON)
            after: Valori nuovi (dict JSON)

        Returns:
            Stringa descrizione italiana
        """
        # Determina tipo entità
        entity_type = "Dipendente" if table_name == "personale" else "Struttura"

        # Get entity name
        entity_name = self._get_entity_display_name(record_key, before, after)

        if operation == 'INSERT':
            # Aggiunta
            return f"Aggiunto nuovo {entity_type.lower()} **{entity_name}** (Chiave: {record_key})"

        elif operation == 'DELETE':
            # Eliminazione
            return f"Eliminato {entity_type.lower()} **{entity_name}** (Chiave: {record_key})"

        elif operation == 'UPDATE' and field_name:
            # Modifica campo specifico
            field_italian = self._translate_field_name(field_name)

            # Extract old and new values for this field
            old_value = before.get(field_name, '') if before else ''
            new_value = after.get(field_name, '') if after else ''

            # Format values
            old_display = self._format_value(old_value)
            new_display = self._format_value(new_value)

            return (f"{entity_type} **{entity_name}** ha cambiato *{field_italian}* "
                   f"da `{old_display}` a `{new_display}`")

        else:
            # Fallback generico
            return f"{entity_type} **{entity_name}** modificato"

    def _get_entity_display_name(self, record_key: str,
                                 before: Optional[Dict],
                                 after: Optional[Dict]) -> str:
        """
        Estrai nome display dell'entità (Titolare per personale, DESCRIZIONE per strutture).

        Args:
            record_key: Chiave record
            before: Valori precedenti
            after: Valori nuovi

        Returns:
            Nome display o chiave se non disponibile
        """
        # Try to get Titolare (personale) or DESCRIZIONE (strutture)
        data = after or before
        if not data:
            return record_key

        name = data.get('Titolare') or data.get('DESCRIZIONE') or record_key
        return str(name).strip() if name else record_key

    def _format_value(self, value) -> str:
        """Format value for display (handle None, empty strings)"""
        if value is None or value == '':
            return '(vuoto)'
        return str(value)
