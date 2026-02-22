"""
Employee Models

Pydantic models for normalized employee data from DB_ORG.
Represents the 135 columns of DB_ORG in a structured format.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import date, datetime
from decimal import Decimal


class Employee(BaseModel):
    """
    Employee model representing normalized data from DB_ORG.

    Maps to employees table in database.
    """
    employee_id: Optional[int] = None
    tx_cod_fiscale: str = Field(..., description="Codice Fiscale (Primary Key)")
    codice: str = Field(..., description="Codice dipendente")
    titolare: str = Field(..., description="Nome completo dipendente")
    company_id: int = Field(..., description="FK to companies table")

    # Dati anagrafici (Ambito AF-BH)
    cognome: Optional[str] = None
    nome: Optional[str] = None
    societa: Optional[str] = None
    area: Optional[str] = None
    sottoarea: Optional[str] = None
    sede: Optional[str] = None
    contratto: Optional[str] = None
    qualifica: Optional[str] = None
    livello: Optional[str] = None
    ral: Optional[Decimal] = None
    data_assunzione: Optional[date] = None
    data_cessazione: Optional[date] = None
    data_nascita: Optional[date] = None
    sesso: Optional[str] = None
    email: Optional[str] = None
    matricola: Optional[str] = None

    # Indirizzo
    indirizzo_via: Optional[str] = None
    indirizzo_cap: Optional[str] = None
    indirizzo_citta: Optional[str] = None

    # Dati organizzativi (Ambito A-AC)
    formato: Optional[str] = None
    funzione: Optional[str] = None
    fte: Optional[float] = 1.0
    tipo_collaborazione: Optional[str] = None
    reports_to_codice: Optional[str] = None
    photo_url: Optional[str] = None

    # Dati TNS (Ambito BS-CV)
    sede_tns: Optional[str] = None
    gruppo_sind: Optional[str] = None

    # Metadata
    active: bool = True
    ultimo_sync_payroll: Optional[date] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v) if v is not None else None,
            date: lambda v: v.isoformat() if v is not None else None,
            datetime: lambda v: v.isoformat() if v is not None else None
        }

    @validator('tx_cod_fiscale')
    def validate_codice_fiscale(cls, v):
        """Validate Italian fiscal code format"""
        if v:
            v = v.strip().upper()
            if len(v) != 16:
                raise ValueError(f"Codice Fiscale must be 16 characters, got {len(v)}")
        return v

    @validator('email')
    def validate_email(cls, v):
        """Basic email validation"""
        if v and '@' not in v:
            raise ValueError("Invalid email format")
        return v

    @validator('fte')
    def validate_fte(cls, v):
        """Validate FTE is between 0 and 1"""
        if v is not None and (v < 0 or v > 1.0):
            raise ValueError("FTE must be between 0 and 1.0")
        return v

    @validator('data_cessazione')
    def validate_cessazione(cls, v, values):
        """Validate cessazione date is after assunzione"""
        if v and values.get('data_assunzione') and v < values['data_assunzione']:
            raise ValueError("Data cessazione must be after data assunzione")
        return v


class EmployeeCreate(BaseModel):
    """Model for creating a new employee"""
    tx_cod_fiscale: str
    codice: str
    titolare: str
    company_id: int = 1  # Default to Il Sole 24 ORE
    cognome: Optional[str] = None
    nome: Optional[str] = None
    area: Optional[str] = None
    sottoarea: Optional[str] = None
    sede: Optional[str] = None
    contratto: Optional[str] = None
    qualifica: Optional[str] = None
    ral: Optional[Decimal] = None
    data_assunzione: Optional[date] = None
    email: Optional[str] = None


class EmployeeUpdate(BaseModel):
    """Model for updating an employee (all fields optional)"""
    titolare: Optional[str] = None
    cognome: Optional[str] = None
    nome: Optional[str] = None
    area: Optional[str] = None
    sottoarea: Optional[str] = None
    sede: Optional[str] = None
    contratto: Optional[str] = None
    qualifica: Optional[str] = None
    livello: Optional[str] = None
    ral: Optional[Decimal] = None
    data_cessazione: Optional[date] = None
    email: Optional[str] = None
    active: Optional[bool] = None


class EmployeeListItem(BaseModel):
    """Simplified model for employee lists"""
    employee_id: int
    tx_cod_fiscale: str
    codice: str
    titolare: str
    cognome: Optional[str]
    nome: Optional[str]
    qualifica: Optional[str]
    area: Optional[str]
    sede: Optional[str]
    ral: Optional[Decimal]
    active: bool

    class Config:
        from_attributes = True


class EmployeeSearchResult(EmployeeListItem):
    """Model for search results with highlighting"""
    match_field: Optional[str] = None  # Field that matched the search
    match_value: Optional[str] = None  # Value that matched
