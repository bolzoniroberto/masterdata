"""
Pydantic models for merge/enrichment import functionality.

Defines data structures for:
- Merge strategies and import types
- Record matching and gap analysis
- Conflict detection and resolution
- Merge preview and execution results
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum


class MergeStrategy(str, Enum):
    """
    Strategie di merge campo-specifiche.

    Definisce come gestire conflitti tra file Excel e DB.
    """
    OVERWRITE = "overwrite"        # File > DB sempre (sovrascrive)
    FILL_EMPTY = "fill_empty"      # File > DB solo se DB vuoto
    SMART_MERGE = "smart_merge"    # Regole intelligenti (es. merge liste)
    ASK_USER = "ask_user"          # Chiedi utente per ogni conflitto
    KEEP_TARGET = "keep_target"    # DB > File (mantiene DB, ignora file)


class ImportType(str, Enum):
    """
    Tipi di import merge supportati.

    Ogni tipo ha strategie predefinite e logica gap analysis specifica.
    """
    SALARY_REVIEW = "salary_review"        # Aggiornamento RAL post salary review
    TNS_REORG = "tns_reorg"                # Riorganizzazione struttura TNS
    CESSATI_ASSUNTI = "cessati_assunti"    # Detection cessazioni/assunzioni
    BANDING = "banding"                     # Arricchimento banding/grading
    CUSTOM = "custom"                       # Import personalizzato


class MatchedPair(BaseModel):
    """
    Coppia di record matched tra file Excel e DB.

    Attributes:
        source_id: ID record da file Excel
        target_id: ID record da database
        source_data: Dati completi da file
        target_data: Dati completi da DB
        match_confidence: Score confidenza match (1.0 = exact, <1.0 = fuzzy)
    """
    source_id: str
    target_id: str
    source_data: Dict[str, Any]
    target_data: Dict[str, Any]
    match_confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class MatchResult(BaseModel):
    """
    Risultato completo del matching file-DB.

    Attributes:
        matched_pairs: Record presenti in entrambi (file E DB)
        unmatched_source: Record solo nel file (nuovi, da inserire)
        unmatched_target: Record solo in DB (gap, non aggiornati)
        match_stats: Metriche matching
    """
    matched_pairs: List[MatchedPair]
    unmatched_source: List[Dict[str, Any]]  # Nuovi (file non in DB)
    unmatched_target: List[Dict[str, Any]]  # Gap (DB non in file)
    match_stats: Dict[str, int] = Field(default_factory=dict)

    def __init__(self, **data):
        super().__init__(**data)
        # Auto-calcola stats se non fornite
        if not self.match_stats:
            self.match_stats = {
                'matched': len(self.matched_pairs),
                'new': len(self.unmatched_source),
                'gap': len(self.unmatched_target),
                'total_file': len(self.matched_pairs) + len(self.unmatched_source),
                'total_db': len(self.matched_pairs) + len(self.unmatched_target)
            }


class GapDetail(BaseModel):
    """
    Dettaglio di un singolo record gap (DB non nel file).

    Attributes:
        record_id: ID record (CF, cod_tns, etc.)
        record_data: Dati completi record
        is_critical: True se gap su ruolo critico (manager, approvatore)
        criticality_reason: Spiegazione perché è critico
    """
    record_id: str
    record_data: Dict[str, Any]
    is_critical: bool = False
    criticality_reason: Optional[str] = None


class GapAnalysis(BaseModel):
    """
    Analisi completa gap (record DB non nel file).

    Per import tipo 'cessati_assunti', gap potrebbero indicare cessazioni.
    Per altri tipi, gap = record non aggiornati.

    Attributes:
        total_gaps: Count totale gap
        critical_gaps: Count gap su ruoli critici
        gap_records: Dettagli tutti i gap
        recommendations: Lista azioni suggerite
    """
    total_gaps: int
    critical_gaps: int
    gap_records: List[GapDetail]
    recommendations: List[str] = Field(default_factory=list)

    def __init__(self, **data):
        super().__init__(**data)
        # Auto-calcola totals se non forniti
        if not hasattr(self, '_calculated'):
            self.total_gaps = len(self.gap_records)
            self.critical_gaps = sum(1 for g in self.gap_records if g.is_critical)
            self._calculated = True


class FieldConflict(BaseModel):
    """
    Conflitto su un campo: valore file ≠ valore DB.

    Attributes:
        record_id: ID record con conflitto
        field_name: Nome campo in conflitto
        file_value: Valore da file Excel
        db_value: Valore attuale DB
        suggested_strategy: Strategia suggerita per risoluzione
        user_resolution: Valore scelto da utente (se risolto manualmente)
    """
    record_id: str
    field_name: str
    file_value: Any
    db_value: Any
    suggested_strategy: MergeStrategy
    user_resolution: Optional[Any] = None


class MergeRecord(BaseModel):
    """
    Record merge con dati before/after.

    Rappresenta come sarà un record dopo il merge.

    Attributes:
        record_id: ID record
        before: Dati attuali DB (prima del merge)
        after: Dati post-merge (dopo applicazione)
        changed_fields: Lista campi modificati
        conflicts: Lista conflitti rilevati
        merge_strategy_used: Strategia usata per ogni campo
    """
    record_id: str
    before: Dict[str, Any]
    after: Dict[str, Any]
    changed_fields: List[str] = Field(default_factory=list)
    conflicts: List[FieldConflict] = Field(default_factory=list)
    merge_strategy_used: Dict[str, MergeStrategy] = Field(default_factory=dict)

    def __init__(self, **data):
        super().__init__(**data)
        # Auto-calcola changed_fields se non forniti
        if not self.changed_fields and self.before and self.after:
            self.changed_fields = [
                k for k in self.after.keys()
                if k in self.before and self.before[k] != self.after[k]
            ]


class MergePreview(BaseModel):
    """
    Preview completo del merge prima dell'applicazione.

    Attributes:
        merge_records: Lista tutti i record da mergiare
        total_records: Count totale record
        records_with_changes: Count record con modifiche
        total_conflicts: Count totale conflitti
        stats: Statistiche strategie usate
    """
    merge_records: List[MergeRecord]
    total_records: int = 0
    records_with_changes: int = 0
    total_conflicts: int = 0
    stats: Dict[str, int] = Field(default_factory=dict)

    def __init__(self, **data):
        super().__init__(**data)
        # Auto-calcola metriche se non fornite
        if not self.total_records:
            self.total_records = len(self.merge_records)
            self.records_with_changes = sum(
                1 for r in self.merge_records if r.changed_fields
            )
            self.total_conflicts = sum(
                len(r.conflicts) for r in self.merge_records
            )

            # Stats strategie
            strategy_counts: Dict[str, int] = {}
            for rec in self.merge_records:
                for strategy in rec.merge_strategy_used.values():
                    strategy_counts[strategy.value] = strategy_counts.get(strategy.value, 0) + 1
            self.stats = strategy_counts


class MergeResult(BaseModel):
    """
    Risultato dell'applicazione del merge.

    Attributes:
        success: True se merge completato senza errori critici
        applied_count: Numero record aggiornati
        skipped_count: Numero record saltati
        error_count: Numero record con errori
        errors: Lista errori riscontrati
        snapshot_path: Path snapshot pre-merge (se creato)
        audit_log_id: ID entry audit log (se creato)
    """
    success: bool
    applied_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    errors: List[str] = Field(default_factory=list)
    snapshot_path: Optional[str] = None
    audit_log_id: Optional[int] = None


# Type alias per convenienza
MergeStrategyDict = Dict[str, MergeStrategy]
"""Dict[field_name, MergeStrategy] per strategie campo-specifiche"""
