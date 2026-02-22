"""
MergeEngine service for differential/enrichment imports.

Handles:
- Record matching between Excel file and database
- Gap analysis (DB records not in file)
- Merge preview with conflict detection
- Merge execution using BatchOperations
"""

import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
import logging

from models.merge_models import (
    MatchedPair, MatchResult, GapDetail, GapAnalysis,
    FieldConflict, MergeRecord, MergePreview, MergeResult,
    MergeStrategy, ImportType, MergeStrategyDict
)
from models.bot_models import ChangeProposal, OperationType
from services.batch_operations import BatchOperations
from services.database import DatabaseHandler

logger = logging.getLogger(__name__)


class MergeEngine:
    """
    Core engine per import merge/arricchimento differenziale.

    Gestisce matching file-DB, gap analysis, conflict detection,
    e applicazione merge con strategie configurabili.
    """

    def __init__(self, db_handler: Optional[DatabaseHandler] = None):
        """
        Initialize MergeEngine.

        Args:
            db_handler: Database handler (crea nuovo se None)
        """
        self.db = db_handler or DatabaseHandler()

    # ========== MATCHING ==========

    def match_records(
        self,
        source_df: pd.DataFrame,
        target_df: pd.DataFrame,
        key_column: str,
        import_type: str
    ) -> MatchResult:
        """
        Match records tra file Excel (source) e database (target).

        Esegue exact match su key_column. Per ogni record:
        - Se key in entrambi → matched
        - Se key solo in source → new (da inserire)
        - Se key solo in target → gap (non aggiornato)

        Args:
            source_df: DataFrame da file Excel
            target_df: DataFrame da database
            key_column: Nome colonna chiave (es. 'tx_cod_fiscale', 'cod_tns')
            import_type: Tipo import (per future ottimizzazioni)

        Returns:
            MatchResult con matched_pairs, unmatched_source, unmatched_target

        Example:
            >>> result = engine.match_records(
            ...     file_df, db_df, 'tx_cod_fiscale', 'salary_review'
            ... )
            >>> print(f"Matched: {len(result.matched_pairs)}")
            >>> print(f"New: {len(result.unmatched_source)}")
            >>> print(f"Gap: {len(result.unmatched_target)}")
        """
        logger.info(f"Matching records on key '{key_column}' for import type '{import_type}'")

        # Normalizza key column (strip, uppercase se CF)
        source_keys = set(self._normalize_key(source_df[key_column]))
        target_keys = set(self._normalize_key(target_df[key_column]))

        # Compute sets
        matched_keys = source_keys & target_keys
        new_keys = source_keys - target_keys
        gap_keys = target_keys - source_keys

        logger.info(
            f"Match results: {len(matched_keys)} matched, "
            f"{len(new_keys)} new, {len(gap_keys)} gap"
        )

        # Build matched pairs
        matched_pairs = []
        for key in matched_keys:
            source_row = source_df[source_df[key_column].apply(self._normalize_single_key) == key].iloc[0]
            target_row = target_df[target_df[key_column].apply(self._normalize_single_key) == key].iloc[0]

            matched_pairs.append(MatchedPair(
                source_id=str(key),
                target_id=str(key),
                source_data=source_row.to_dict(),
                target_data=target_row.to_dict(),
                match_confidence=1.0  # Exact match
            ))

        # Build unmatched source (new records)
        unmatched_source = [
            row.to_dict()
            for key in new_keys
            for _, row in source_df[source_df[key_column].apply(self._normalize_single_key) == key].iterrows()
        ]

        # Build unmatched target (gap records)
        unmatched_target = [
            row.to_dict()
            for key in gap_keys
            for _, row in target_df[target_df[key_column].apply(self._normalize_single_key) == key].iterrows()
        ]

        return MatchResult(
            matched_pairs=matched_pairs,
            unmatched_source=unmatched_source,
            unmatched_target=unmatched_target
        )

    def _normalize_key(self, series: pd.Series) -> pd.Series:
        """Normalizza colonna chiave (strip, upper per CF)."""
        return series.astype(str).str.strip().str.upper()

    def _normalize_single_key(self, value: Any) -> str:
        """Normalizza singolo valore chiave."""
        return str(value).strip().upper()

    # ========== GAP ANALYSIS ==========

    def analyze_gaps(
        self,
        match_result: MatchResult,
        import_type: str,
        target_df: Optional[pd.DataFrame] = None
    ) -> GapAnalysis:
        """
        Analizza gap (record DB non nel file).

        Per import tipo 'cessati_assunti':
        - Gap potrebbero essere cessati
        - Identifica manager/approvatori tra gap (critical)

        Per altri tipi:
        - Gap = record che non saranno aggiornati

        Args:
            match_result: Risultato matching
            import_type: Tipo import
            target_df: DataFrame DB completo (per critical gap detection)

        Returns:
            GapAnalysis con total_gaps, critical_gaps, recommendations
        """
        logger.info(f"Analyzing {len(match_result.unmatched_target)} gap records")

        gap_records = []
        critical_count = 0

        for gap_data in match_result.unmatched_target:
            is_critical = False
            criticality_reason = None

            # Detect critical gaps
            if import_type == ImportType.CESSATI_ASSUNTI.value:
                # Manager o approvatore?
                is_manager = self._is_manager(gap_data, target_df)
                is_approver = self._is_approver(gap_data, target_df)

                if is_manager:
                    is_critical = True
                    criticality_reason = "Manager con riporti diretti"
                    critical_count += 1
                elif is_approver:
                    is_critical = True
                    criticality_reason = "Approvatore TNS attivo"
                    critical_count += 1

            gap_records.append(GapDetail(
                record_id=self._get_record_id(gap_data),
                record_data=gap_data,
                is_critical=is_critical,
                criticality_reason=criticality_reason
            ))

        # Generate recommendations
        recommendations = self._generate_gap_recommendations(
            gap_records, import_type, critical_count
        )

        return GapAnalysis(
            total_gaps=len(gap_records),
            critical_gaps=critical_count,
            gap_records=gap_records,
            recommendations=recommendations
        )

    def _is_manager(self, record: Dict[str, Any], target_df: Optional[pd.DataFrame]) -> bool:
        """Check se record è manager (ha riporti diretti)."""
        if not target_df is not None:
            return False

        cf = record.get('tx_cod_fiscale') or record.get('codice_fiscale')
        if not cf:
            return False

        # Count riporti diretti
        if 'reports_to_cf' in target_df.columns:
            riporti = target_df[target_df['reports_to_cf'] == cf]
            return len(riporti) > 0

        return False

    def _is_approver(self, record: Dict[str, Any], target_df: Optional[pd.DataFrame]) -> bool:
        """Check se record è approvatore TNS."""
        if not target_df is not None:
            return False

        cf = record.get('tx_cod_fiscale') or record.get('codice_fiscale')
        if not cf:
            return False

        # Check se è approvatore TNS
        if 'approvatore_tns_cf' in target_df.columns:
            approvazioni = target_df[target_df['approvatore_tns_cf'] == cf]
            return len(approvazioni) > 0

        return False

    def _get_record_id(self, record: Dict[str, Any]) -> str:
        """Estrai ID record da dict (CF, cod_tns, etc.)."""
        return (
            record.get('tx_cod_fiscale') or
            record.get('codice_fiscale') or
            record.get('cod_tns') or
            record.get('codice') or
            str(record.get('id', 'unknown'))
        )

    def _generate_gap_recommendations(
        self,
        gap_records: List[GapDetail],
        import_type: str,
        critical_count: int
    ) -> List[str]:
        """Genera raccomandazioni basate su gap rilevati."""
        recommendations = []

        if import_type == ImportType.CESSATI_ASSUNTI.value:
            if critical_count > 0:
                recommendations.append(
                    f"⚠️ Verifica {critical_count} manager/approvatori non nel file - possibili cessazioni critiche"
                )
            if len(gap_records) > 10:
                recommendations.append(
                    f"📊 {len(gap_records)} gap rilevati - considera export CSV per analisi dettagliata"
                )
        elif import_type == ImportType.SALARY_REVIEW.value:
            recommendations.append(
                f"✅ {len(gap_records)} dipendenti senza variazione RAL (corretto)"
            )
        elif import_type == ImportType.TNS_REORG.value:
            recommendations.append(
                f"✅ {len(gap_records)} strutture non coinvolte in riorganizzazione"
            )

        return recommendations

    # ========== MERGE PREVIEW ==========

    def preview_merge(
        self,
        matched_pairs: List[MatchedPair],
        merge_strategy: MergeStrategy = MergeStrategy.OVERWRITE,
        per_field_strategies: Optional[MergeStrategyDict] = None
    ) -> MergePreview:
        """
        Genera preview del merge con detection conflitti.

        Per ogni matched pair, calcola:
        - before: dati attuali DB
        - after: dati post-merge
        - changed_fields: campi modificati
        - conflicts: campi con file ≠ DB

        Args:
            matched_pairs: Coppie matched da match_records()
            merge_strategy: Strategia default
            per_field_strategies: Strategie specifiche per campo

        Returns:
            MergePreview con merge_records, conflicts, stats
        """
        logger.info(f"Generating merge preview for {len(matched_pairs)} records")

        per_field_strategies = per_field_strategies or {}
        merge_records = []

        for pair in matched_pairs:
            before = pair.target_data
            after, conflicts, strategies_used = self._compute_merge(
                source_data=pair.source_data,
                target_data=pair.target_data,
                default_strategy=merge_strategy,
                per_field_strategies=per_field_strategies,
                record_id=pair.source_id
            )

            merge_records.append(MergeRecord(
                record_id=pair.source_id,
                before=before,
                after=after,
                conflicts=conflicts,
                merge_strategy_used=strategies_used
            ))

        return MergePreview(merge_records=merge_records)

    def _compute_merge(
        self,
        source_data: Dict[str, Any],
        target_data: Dict[str, Any],
        default_strategy: MergeStrategy,
        per_field_strategies: MergeStrategyDict,
        record_id: str
    ) -> Tuple[Dict[str, Any], List[FieldConflict], MergeStrategyDict]:
        """
        Computa merge per singolo record.

        Returns:
            (after_data, conflicts, strategies_used)
        """
        after = target_data.copy()
        conflicts = []
        strategies_used = {}

        # Merge ogni campo
        for field, source_value in source_data.items():
            if field not in target_data:
                # Campo nuovo, aggiungi
                after[field] = source_value
                strategies_used[field] = MergeStrategy.OVERWRITE
                continue

            target_value = target_data[field]

            # Se valori uguali, skip
            if source_value == target_value or (pd.isna(source_value) and pd.isna(target_value)):
                strategies_used[field] = MergeStrategy.KEEP_TARGET
                continue

            # Applica strategia
            strategy = per_field_strategies.get(field, default_strategy)
            strategies_used[field] = strategy

            merged_value, has_conflict = self._apply_field_strategy(
                field=field,
                source_value=source_value,
                target_value=target_value,
                strategy=strategy
            )

            after[field] = merged_value

            # Detect conflict
            if has_conflict:
                conflicts.append(FieldConflict(
                    record_id=record_id,
                    field_name=field,
                    file_value=source_value,
                    db_value=target_value,
                    suggested_strategy=strategy
                ))

        return after, conflicts, strategies_used

    def _apply_field_strategy(
        self,
        field: str,
        source_value: Any,
        target_value: Any,
        strategy: MergeStrategy
    ) -> Tuple[Any, bool]:
        """
        Applica strategia merge a singolo campo.

        Returns:
            (merged_value, has_conflict)
        """
        if strategy == MergeStrategy.OVERWRITE:
            # File > DB sempre
            return source_value, (source_value != target_value)

        elif strategy == MergeStrategy.FILL_EMPTY:
            # File > DB solo se DB vuoto
            if pd.isna(target_value) or target_value == '' or target_value is None:
                return source_value, False
            else:
                return target_value, False

        elif strategy == MergeStrategy.KEEP_TARGET:
            # DB > File (mantieni DB)
            return target_value, False

        elif strategy == MergeStrategy.ASK_USER:
            # Conflict - richiede risoluzione utente
            return target_value, True  # Default DB, ma flag conflict

        elif strategy == MergeStrategy.SMART_MERGE:
            # TODO: Implementa merge intelligente (es. merge liste, concat stringhe)
            # Per ora default a OVERWRITE
            return source_value, (source_value != target_value)

        else:
            # Default: OVERWRITE
            return source_value, (source_value != target_value)

    # ========== APPLY MERGE ==========

    def apply_merge(
        self,
        preview: MergePreview,
        selected_record_ids: Optional[List[str]] = None,
        validate: bool = True,
        record_type: str = "personale"
    ) -> MergeResult:
        """
        Applica merge usando BatchOperations.

        Args:
            preview: MergePreview da preview_merge()
            selected_record_ids: Lista ID record da applicare (None = tutti)
            validate: Se True, valida con DataValidator post-merge
            record_type: Tipo record ("personale" o "strutture")

        Returns:
            MergeResult con applied_count, errors, etc.
        """
        logger.info(f"Applying merge for {len(preview.merge_records)} records")

        # Filtra record selezionati
        if selected_record_ids:
            records_to_apply = [
                rec for rec in preview.merge_records
                if rec.record_id in selected_record_ids
            ]
        else:
            records_to_apply = preview.merge_records

        # Converti a ChangeProposal
        changes = self._convert_to_change_proposals(records_to_apply, record_type)

        # Apply usando BatchOperations
        try:
            batch_ops = BatchOperations()
            batch_result = batch_ops.apply_changes(
                changes=changes,
                record_type=record_type,
                validate=validate
            )

            return MergeResult(
                success=batch_result.success,
                applied_count=batch_result.applied_count,
                skipped_count=len(preview.merge_records) - len(records_to_apply),
                error_count=len(batch_result.errors),
                errors=batch_result.errors
            )

        except Exception as e:
            logger.error(f"Merge application failed: {e}", exc_info=True)
            return MergeResult(
                success=False,
                error_count=1,
                errors=[f"Merge failed: {str(e)}"]
            )

    def _convert_to_change_proposals(
        self,
        merge_records: List[MergeRecord],
        record_type: str
    ) -> List[ChangeProposal]:
        """Converti MergeRecord a ChangeProposal per BatchOperations."""
        key_field = self._get_key_field(record_type)
        changes = []

        for rec in merge_records:
            # Skip record senza modifiche
            if not rec.changed_fields:
                continue

            changes.append(ChangeProposal(
                change_id=f"merge_{rec.record_id}",
                operation=OperationType.UPDATE_RECORD,
                filter_criteria={key_field: rec.record_id},
                before_values=rec.before,
                after_values=rec.after,
                description=f"Merge: {', '.join(rec.changed_fields)}",
                risk_level="low"
            ))

        return changes

    def _get_key_field(self, record_type: str) -> str:
        """Get key field name per record type."""
        if record_type == "personale":
            return "tx_cod_fiscale"
        elif record_type == "strutture":
            return "cod_tns"
        else:
            return "id"
