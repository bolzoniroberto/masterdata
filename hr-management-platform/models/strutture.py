"""
Modelli Pydantic per validazione record TNS Strutture
"""
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class StrutturaRecord(BaseModel):
    """
    Modello per record unità organizzativa in TNS Strutture.
    REGOLA: NON deve avere TxCodFiscale (rimane None/NaN).
    """
    unita_organizzativa: Optional[str] = Field(default=None, alias="Unità Organizzativa")
    cdccosto: Optional[str] = Field(default=None, alias="CDCCOSTO")
    tx_cod_fiscale: Optional[str] = Field(default=None, alias="TxCodFiscale")  # DEVE essere vuoto
    descrizione: str = Field(alias="DESCRIZIONE")
    titolare: Optional[str] = Field(default=None, alias="Titolare")
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
    def validate_no_codice_fiscale(cls, v: Optional[str]) -> Optional[str]:
        """Le strutture NON devono avere codice fiscale"""
        if v and v.strip():
            raise ValueError("Record Strutture non deve avere TxCodFiscale valorizzato")
        return None

    @field_validator('codice')
    @classmethod
    def validate_codice(cls, v: str) -> str:
        """Valida presenza codice"""
        if not v or not v.strip():
            raise ValueError("Codice obbligatorio")
        return v.strip()

    @field_validator('descrizione')
    @classmethod
    def validate_descrizione(cls, v: str) -> str:
        """Valida presenza descrizione unità organizzativa"""
        if not v or not v.strip():
            raise ValueError("DESCRIZIONE obbligatoria per strutture")
        return v.strip()

    def get_validation_errors(self, all_codici_strutture: set[str]) -> list[str]:
        """
        Restituisce lista errori di validazione business logic.
        
        Args:
            all_codici_strutture: Set di tutti i codici esistenti nelle strutture
                                  per verificare che il padre esista
        """
        errors = []
        
        # Verifica che padre esista (se valorizzato)
        if self.unita_operativa_padre:
            if self.unita_operativa_padre not in all_codici_strutture:
                errors.append(
                    f"Padre '{self.unita_operativa_padre}' non esiste nelle strutture"
                )
        
        # Verifica no auto-referenza
        if self.unita_operativa_padre == self.codice:
            errors.append("Una struttura non può essere padre di se stessa")
        
        return errors

    def is_root(self) -> bool:
        """Verifica se è una struttura root (senza padre)"""
        return not self.unita_operativa_padre or not self.unita_operativa_padre.strip()

    def is_complete(self) -> bool:
        """Verifica se il record ha tutti i campi principali compilati"""
        return all([
            self.codice,
            self.descrizione
        ])


def detect_cycles(strutture_dict: dict[str, StrutturaRecord]) -> list[str]:
    """
    Rileva cicli nell'albero gerarchico delle strutture.
    
    Args:
        strutture_dict: Dict con Codice -> StrutturaRecord
    
    Returns:
        Lista di errori descrittivi per ogni ciclo trovato
    """
    errors = []
    
    def has_cycle(codice: str, visited: set[str], path: list[str]) -> Optional[list[str]]:
        """DFS per rilevare cicli"""
        if codice in visited:
            # Trovato ciclo: ritorna il percorso
            cycle_start = path.index(codice)
            return path[cycle_start:] + [codice]
        
        if codice not in strutture_dict:
            return None
        
        visited.add(codice)
        path.append(codice)
        
        struttura = strutture_dict[codice]
        if struttura.unita_operativa_padre:
            cycle = has_cycle(struttura.unita_operativa_padre, visited, path)
            if cycle:
                return cycle
        
        path.pop()
        visited.remove(codice)
        return None
    
    # Controlla ogni struttura
    for codice in strutture_dict:
        visited = set()
        cycle = has_cycle(codice, visited, [])
        if cycle:
            cycle_str = " -> ".join(cycle)
            errors.append(f"Ciclo rilevato: {cycle_str}")
    
    return errors
