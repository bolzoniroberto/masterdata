"""
Modelli Pydantic per bot conversazionale HR Management
"""
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class OperationType(str, Enum):
    """Tipo operazione supportata dal bot"""
    ADD_RECORD = "add_record"
    UPDATE_RECORD = "update_record"
    DELETE_RECORD = "delete_record"
    BATCH_UPDATE = "batch_update"
    QUERY = "query"
    VALIDATE_FIX = "validate_fix"


class RecordType(str, Enum):
    """Tipo record target (Personale o Strutture)"""
    PERSONALE = "personale"
    STRUTTURE = "strutture"


class ChangeProposal(BaseModel):
    """
    Singola modifica proposta dal bot.
    Rappresenta una operazione da applicare a un record.
    """
    change_id: str = Field(description="UUID univoco della modifica")
    operation: OperationType = Field(description="Tipo operazione (add/update/delete/batch)")
    record_type: RecordType = Field(description="Target: personale o strutture")

    # Filtro/identificazione record target
    filter_criteria: Dict[str, Any] = Field(
        default_factory=dict,
        description="Criteri per identificare record target (es. {'TxCodFiscale': 'RSSMRA...'})"
    )
    affected_records_count: int = Field(
        default=1,
        description="Numero record impattati da questa modifica"
    )

    # Dettagli modifica
    before_values: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Valori originali del record (None per add_record)"
    )
    after_values: Dict[str, Any] = Field(
        description="Nuovi valori da applicare"
    )

    # Stato UI
    selected: bool = Field(
        default=True,
        description="Stato checkbox UI (True = selezionato per apply)"
    )
    validation_status: Literal["valid", "warning", "error"] = Field(
        default="valid",
        description="Stato validazione: valid, warning, error"
    )
    validation_message: Optional[str] = Field(
        default=None,
        description="Messaggio errore/warning validazione"
    )

    # Metadata
    description: str = Field(
        description="Descrizione human-readable della modifica"
    )
    risk_level: Literal["low", "medium", "high"] = Field(
        default="low",
        description="Livello rischio: low (singolo), medium (<10), high (≥10 o delete)"
    )

    class Config:
        use_enum_values = True


class BotResponse(BaseModel):
    """
    Risposta strutturata del bot a un comando utente.
    Contiene risultato interpretazione e lista modifiche proposte.
    """
    success: bool = Field(
        description="True se comando interpretato correttamente"
    )
    message: str = Field(
        description="Messaggio conversazionale per l'utente"
    )
    operation: OperationType = Field(
        description="Tipo operazione identificata"
    )
    changes: List[ChangeProposal] = Field(
        default_factory=list,
        description="Lista modifiche proposte (vuota per query)"
    )
    query_result: Optional[Any] = Field(
        default=None,
        description="Risultato query (per operation=query)"
    )

    class Config:
        use_enum_values = True


class ConversationTurn(BaseModel):
    """
    Turno conversazione bot (history).
    Salvato in st.session_state.chat_history[]
    """
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Timestamp ISO 8601"
    )
    user_input: str = Field(
        description="Comando utente in linguaggio naturale"
    )
    bot_response: BotResponse = Field(
        description="Risposta bot strutturata"
    )
    changes_applied: List[str] = Field(
        default_factory=list,
        description="Lista change_id delle modifiche effettivamente applicate"
    )
