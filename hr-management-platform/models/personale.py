"""
Modelli Pydantic per validazione record TNS Personale
"""
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re


class PersonaleRecord(BaseModel):
    """
    Modello per record dipendente in TNS Personale.
    REGOLA: deve avere sempre TxCodFiscale valorizzato.
    """
    unita_organizzativa: str = Field(alias="Unità Organizzativa")
    cdccosto: Optional[str] = Field(default=None, alias="CDCCOSTO")
    tx_cod_fiscale: str = Field(alias="TxCodFiscale")
    descrizione: Optional[str] = Field(default=None, alias="DESCRIZIONE")
    titolare: str = Field(alias="Titolare")
    livello: Optional[str] = Field(default=None, alias="LIVELLO")
    codice: str = Field(alias="Codice")
    unita_operativa_padre: Optional[str] = Field(default=None, alias="UNITA' OPERATIVA PADRE ")

    # Ruoli e permessi
    ruoli_oltrev: Optional[str] = Field(default=None, alias="RUOLI OltreV")
    ruoli: Optional[str] = Field(default=None, alias="RUOLI")
    viaggiatore: Optional[str] = Field(default=None, alias="Viaggiatore")
    segr_redaz: Optional[str] = Field(default=None, alias="Segr_Redaz")
    approvatore: Optional[str] = Field(default=None, alias="Approvatore")
    cassiere: Optional[str] = Field(default=None, alias="Cassiere")
    visualizzatori: Optional[str] = Field(default=None, alias="Visualizzatori")
    segretario: Optional[str] = Field(default=None, alias="Segretario")
    controllore: Optional[str] = Field(default=None, alias="Controllore")
    amministrazione: Optional[str] = Field(default=None, alias="Amministrazione")
    segreteria_red_assta: Optional[str] = Field(default=None, alias="SegreteriA Red. Ass.ta")
    segretario_assto: Optional[str] = Field(default=None, alias="SegretariO Ass.to")
    controllore_assto: Optional[str] = Field(default=None, alias="Controllore Ass.to")
    ruoli_afc: Optional[str] = Field(default=None, alias="RuoliAFC")
    ruoli_hr: Optional[str] = Field(default=None, alias="RuoliHR")
    altri_ruoli: Optional[str] = Field(default=None, alias="AltriRuoli")

    # Sede e gruppo
    sede_tns: Optional[str] = Field(default=None, alias="Sede_TNS")
    gruppo_sind: Optional[str] = Field(default=None, alias="GruppoSind")

    class Config:
        populate_by_name = True
        str_strip_whitespace = True
        arbitrary_types_allowed = True

    @field_validator('*', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        """Converte stringhe vuote, NaN e numeri in formato appropriato"""
        import pandas as pd

        # NaN → None
        if pd.isna(v):
            return None

        # Stringhe vuote → None
        if isinstance(v, str) and v.strip() == '':
            return None

        # Numeri (int, float) → Stringa
        # Excel spesso carica CDCCOSTO, LIVELLO come numeri invece di stringhe
        if isinstance(v, (int, float)):
            # Se è un float intero (es: 16100.0), converti in int prima
            if isinstance(v, float) and v.is_integer():
                return str(int(v))
            return str(v)

        return v

    @field_validator('tx_cod_fiscale')
    @classmethod
    def validate_codice_fiscale(cls, v: str) -> str:
        """Valida formato codice fiscale italiano (16 caratteri alfanumerici)"""
        if not v or not v.strip():
            raise ValueError("Codice fiscale obbligatorio per record Personale")

        v = v.strip().upper()

        # Pattern CF italiano: 16 caratteri (lettere e numeri)
        if not re.match(r'^[A-Z0-9]{16}$', v):
            raise ValueError(f"Codice fiscale non valido: {v} (deve essere 16 caratteri alfanumerici)")

        return v

    @field_validator('codice')
    @classmethod
    def validate_codice(cls, v: str) -> str:
        """Valida presenza codice"""
        if not v or not v.strip():
            raise ValueError("Codice obbligatorio")
        return v.strip()

    @field_validator('titolare')
    @classmethod
    def validate_titolare(cls, v: str) -> str:
        """Valida presenza titolare (nome dipendente)"""
        if not v or not v.strip():
            raise ValueError("Titolare (nome dipendente) obbligatorio")
        return v.strip()

    @field_validator('unita_organizzativa')
    @classmethod
    def validate_unita_org(cls, v: str) -> str:
        """Valida presenza unità organizzativa"""
        if not v or not v.strip():
            raise ValueError("Unità Organizzativa obbligatoria")
        return v.strip()

    def get_validation_errors(self) -> list[str]:
        """
        Restituisce lista errori di validazione business logic.
        Da usare dopo validazione Pydantic base.
        """
        errors = []

        # Verifica coerenza Codice vs TxCodFiscale
        # Spesso il Codice coincide con il CF per i dipendenti
        if self.codice != self.tx_cod_fiscale:
            # Potrebbe essere warning, non errore bloccante
            pass

        return errors

    def is_complete(self) -> bool:
        """Verifica se il record ha tutti i campi principali compilati"""
        return all([
            self.tx_cod_fiscale,
            self.titolare,
            self.codice,
            self.unita_organizzativa
        ])
