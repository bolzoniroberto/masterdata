"""
Gestione operazioni batch su DataFrame HR.
Applica modifiche proposte e valida risultato.
"""
import pandas as pd
from typing import List, Dict, Any, Tuple
from models.bot_models import ChangeProposal, OperationType, RecordType
from services.validator import DataValidator


class BatchOperations:
    """
    Gestisce applicazione modifiche batch a DataFrame.

    Workflow:
    1. Riceve lista ChangeProposal
    2. Applica modifiche selezionate a df_copy
    3. Valida risultato con DataValidator
    4. Ritorna (df_modificato, errori_validazione)
    """

    @staticmethod
    def apply_changes(
        df: pd.DataFrame,
        changes: List[ChangeProposal],
        validate: bool = True
    ) -> Tuple[pd.DataFrame, List[Dict[str, str]]]:
        """
        Applica lista modifiche a DataFrame.

        Args:
            df: DataFrame originale
            changes: Lista ChangeProposal da applicare
            validate: Se True, valida con DataValidator dopo modifiche

        Returns:
            Tuple (df_modificato, errori_validazione):
                - df_modificato: DataFrame con modifiche applicate
                - errori_validazione: Lista dict con change_id ed errore

        Examples:
            >>> df_result, errors = BatchOperations.apply_changes(
            ...     personale_df,
            ...     selected_changes,
            ...     validate=True
            ... )
            >>> if not errors:
            ...     st.session_state.personale_df = df_result
        """
        # Lavora su copia per non modificare originale fino a validazione OK
        df_result = df.copy()
        validation_errors = []

        # Filtra solo changes selezionate
        selected_changes = [c for c in changes if c.selected]

        for change in selected_changes:
            try:
                if change.operation == OperationType.ADD_RECORD:
                    df_result = BatchOperations._add_record(df_result, change)

                elif change.operation == OperationType.UPDATE_RECORD:
                    df_result = BatchOperations._update_record(df_result, change)

                elif change.operation == OperationType.DELETE_RECORD:
                    df_result = BatchOperations._delete_record(df_result, change)

                elif change.operation == OperationType.BATCH_UPDATE:
                    df_result = BatchOperations._batch_update(df_result, change)

                # Query e validate_fix non modificano DataFrame

            except Exception as e:
                validation_errors.append({
                    'change_id': change.change_id,
                    'error': f"Errore applicazione modifica: {str(e)}"
                })

        # Validazione post-modifica se richiesta
        if validate and selected_changes:
            # Determina tipo record dal primo change
            record_type = selected_changes[0].record_type

            if record_type == RecordType.PERSONALE:
                result = DataValidator.validate_personale(df_result)
            else:
                result = DataValidator.validate_strutture(df_result)

            # Aggiungi errori validazione (limita a primi 10)
            if not result.is_valid():
                for err in result.errors[:10]:
                    validation_errors.append({
                        'change_id': 'validation',
                        'error': f"Row {err['row']}, {err['field']}: {err['message']}"
                    })

            # Aggiungi warning come info (limita a primi 5)
            for warn in result.warnings[:5]:
                validation_errors.append({
                    'change_id': 'warning',
                    'error': f"⚠️ Row {warn['row']}: {warn['message']}"
                })

        return df_result, validation_errors

    @staticmethod
    def _add_record(df: pd.DataFrame, change: ChangeProposal) -> pd.DataFrame:
        """
        Aggiunge nuovo record a DataFrame.

        Args:
            df: DataFrame target
            change: ChangeProposal con after_values

        Returns:
            DataFrame con nuovo record
        """
        # Crea Series con tutti i campi del DataFrame
        new_row_data = {}
        for col in df.columns:
            new_row_data[col] = change.after_values.get(col, None)

        new_row = pd.DataFrame([new_row_data])

        # Concat e reset index
        df_result = pd.concat([df, new_row], ignore_index=True)

        return df_result

    @staticmethod
    def _update_record(df: pd.DataFrame, change: ChangeProposal) -> pd.DataFrame:
        """
        Aggiorna record esistente.

        Args:
            df: DataFrame target
            change: ChangeProposal con filter_criteria e after_values

        Returns:
            DataFrame con record aggiornato
        """
        # Identifica righe da modificare
        mask = BatchOperations._build_mask(df, change.filter_criteria)

        # Applica modifiche solo ai campi specificati in after_values
        for field, value in change.after_values.items():
            if field in df.columns:
                df.loc[mask, field] = value

        return df

    @staticmethod
    def _delete_record(df: pd.DataFrame, change: ChangeProposal) -> pd.DataFrame:
        """
        Elimina record da DataFrame.

        Args:
            df: DataFrame target
            change: ChangeProposal con filter_criteria

        Returns:
            DataFrame senza record eliminati
        """
        # Identifica righe da eliminare
        mask = BatchOperations._build_mask(df, change.filter_criteria)

        # Rimuovi righe (mantieni quelle NON matchate)
        df_result = df[~mask].copy()

        # Reset index
        df_result = df_result.reset_index(drop=True)

        return df_result

    @staticmethod
    def _batch_update(df: pd.DataFrame, change: ChangeProposal) -> pd.DataFrame:
        """
        Batch update multipli record.
        Implementazione identica a _update_record.

        Args:
            df: DataFrame target
            change: ChangeProposal con filter_criteria e after_values

        Returns:
            DataFrame con record aggiornati
        """
        return BatchOperations._update_record(df, change)

    @staticmethod
    def _build_mask(df: pd.DataFrame, criteria: Dict[str, Any]) -> pd.Series:
        """
        Costruisce maschera booleana per filtro DataFrame.

        Args:
            df: DataFrame target
            criteria: Dict con filter_criteria

        Returns:
            Series booleana (True = record matcha criterio)
        """
        mask = pd.Series([True] * len(df), index=df.index)

        for field, value in criteria.items():
            if field not in df.columns:
                continue

            if value is None:
                mask &= df[field].isna()
            elif isinstance(value, list):
                mask &= df[field].isin(value)
            else:
                mask &= (df[field] == value)

        return mask

    @staticmethod
    def preview_changes(
        df: pd.DataFrame,
        changes: List[ChangeProposal]
    ) -> pd.DataFrame:
        """
        Genera DataFrame preview before/after per UI.

        Mostra dettagli modifiche in formato tabellare per ogni campo
        che viene modificato.

        Args:
            df: DataFrame corrente
            changes: Lista ChangeProposal da preview

        Returns:
            DataFrame con colonne:
                - change_id: ID modifica
                - description: Descrizione modifica
                - field: Nome campo modificato
                - before: Valore prima
                - after: Valore dopo
                - status: Stato validazione (valid/warning/error)

        Examples:
            >>> preview_df = BatchOperations.preview_changes(
            ...     personale_df,
            ...     pending_changes
            ... )
            >>> st.dataframe(preview_df)
        """
        preview_rows = []

        for change in changes:
            if not change.selected:
                continue

            # Confronta before vs after
            before = change.before_values or {}
            after = change.after_values

            # Se before è vuoto (add_record), mostra solo after
            if not before:
                for field, value in after.items():
                    preview_rows.append({
                        'change_id': change.change_id,
                        'description': change.description,
                        'field': field,
                        'before': 'N/A (nuovo record)',
                        'after': str(value) if value is not None else 'NULL',
                        'status': change.validation_status
                    })
            else:
                # Mostra solo campi che cambiano
                all_fields = set(list(before.keys()) + list(after.keys()))

                for field in all_fields:
                    before_val = before.get(field, "N/A")
                    after_val = after.get(field, before_val)  # Default a before se non in after

                    # Mostra solo se diverso
                    if before_val != after_val:
                        preview_rows.append({
                            'change_id': change.change_id,
                            'description': change.description,
                            'field': field,
                            'before': str(before_val) if before_val is not None else 'NULL',
                            'after': str(after_val) if after_val is not None else 'NULL',
                            'status': change.validation_status
                        })

        if not preview_rows:
            # Nessuna modifica da mostrare
            return pd.DataFrame(columns=[
                'change_id', 'description', 'field', 'before', 'after', 'status'
            ])

        return pd.DataFrame(preview_rows)
