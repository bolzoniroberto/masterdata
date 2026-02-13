"""
Modelli per la verifica di consistenza DB-Excel.
"""
from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class PersonMismatch(BaseModel):
    """Singola inconsistenza trovata durante la verifica."""

    codice_fiscale: str = Field(..., alias='TxCodFiscale')
    codice: Optional[str] = None
    titolare: str
    unita_organizzativa: Optional[str] = None
    issue_type: Literal[
        'missing_in_db',            # In Excel ma non in DB
        'missing_in_excel',         # In DB ma non in Excel
        'responsabile_missing',     # Responsabile non esiste
        'responsabile_not_approver' # Responsabile senza flag Approvatore=SÌ
    ]
    details: str  # Messaggio descrittivo

    # Campi opzionali per issue_type responsabile_*
    responsabile_codice: Optional[str] = None
    responsabile_nome: Optional[str] = None
    responsabile_approvatore_flag: Optional[str] = None

    class Config:
        populate_by_name = True


class SyncCheckResult(BaseModel):
    """Risultato completo della verifica di consistenza."""

    timestamp: datetime = Field(default_factory=datetime.now)
    excel_file: str
    excel_row_count: int
    db_row_count: int

    # Metriche aggregate
    total_issues: int
    missing_in_db_count: int
    missing_in_excel_count: int
    responsabile_issues_count: int

    # Dettagli per categoria
    missing_in_db: List[PersonMismatch] = []
    missing_in_excel: List[PersonMismatch] = []
    responsabile_missing: List[PersonMismatch] = []
    responsabile_not_approver: List[PersonMismatch] = []

    @property
    def has_issues(self) -> bool:
        """Ritorna True se ci sono problemi di consistenza."""
        return self.total_issues > 0

    @property
    def consistency_percentage(self) -> float:
        """
        Percentuale di consistenza (0-100).
        Calcola quante persone dell'Excel sono consistenti nel DB.
        """
        if self.excel_row_count == 0:
            return 100.0

        # Problemi critici: mancanti in DB + problemi responsabili
        critical_issues = self.missing_in_db_count + self.responsabile_issues_count

        consistent_count = self.excel_row_count - critical_issues
        return (consistent_count / self.excel_row_count) * 100.0
