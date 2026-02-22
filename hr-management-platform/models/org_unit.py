"""
Organizational Unit Models

Pydantic models for organizational units with hierarchical structure.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


class OrgUnit(BaseModel):
    """
    Organizational Unit model.

    Maps to org_units table in database.
    Represents organizational structure with parent-child relationships.
    """
    org_unit_id: Optional[int] = None
    codice: str = Field(..., description="Unique code for org unit")
    descrizione: str = Field(..., description="Description/name of org unit")
    company_id: int = Field(..., description="FK to companies table")
    parent_org_unit_id: Optional[int] = None

    cdccosto: Optional[str] = Field(None, description="Centro di Costo")
    cdc_amm: Optional[str] = Field(None, description="Centro di Costo Amministrativo")
    livello: Optional[int] = Field(None, description="Hierarchy level (1, 2, 3)")
    hierarchy_path: Optional[str] = Field(None, description="Materialized path /1/3/5/")

    unita_org_livello1: Optional[str] = Field(None, description="Level 1 org unit name")
    unita_org_livello2: Optional[str] = Field(None, description="Level 2 org unit name")
    testata_gg: Optional[str] = Field(None, description="Testata GG/2")

    responsible_employee_id: Optional[int] = Field(None, description="FK to employees (can be NULL)")

    active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v is not None else None
        }

    @validator('livello')
    def validate_livello(cls, v):
        """Validate hierarchy level is 1, 2, or 3"""
        if v is not None and v not in [1, 2, 3]:
            raise ValueError("Livello must be 1, 2, or 3")
        return v

    @validator('hierarchy_path')
    def validate_hierarchy_path(cls, v):
        """Validate hierarchy path format /1/3/5/"""
        if v is not None:
            if not v.startswith('/') or not v.endswith('/'):
                raise ValueError("Hierarchy path must start and end with /")
        return v


class OrgUnitCreate(BaseModel):
    """Model for creating a new organizational unit"""
    codice: str
    descrizione: str
    company_id: int = 1  # Default to Il Sole 24 ORE
    parent_org_unit_id: Optional[int] = None
    cdccosto: Optional[str] = None
    cdc_amm: Optional[str] = None
    livello: Optional[int] = None
    unita_org_livello1: Optional[str] = None
    unita_org_livello2: Optional[str] = None
    responsible_employee_id: Optional[int] = None


class OrgUnitUpdate(BaseModel):
    """Model for updating an organizational unit"""
    descrizione: Optional[str] = None
    parent_org_unit_id: Optional[int] = None
    cdccosto: Optional[str] = None
    cdc_amm: Optional[str] = None
    livello: Optional[int] = None
    responsible_employee_id: Optional[int] = None
    active: Optional[bool] = None


class OrgUnitTreeNode(BaseModel):
    """
    Model for organizational unit tree representation.

    Used for displaying hierarchical structures like orgcharts.
    """
    org_unit_id: int
    codice: str
    descrizione: str
    parent_org_unit_id: Optional[int]
    livello: Optional[int]
    cdccosto: Optional[str]

    # Computed fields
    employee_count: int = 0  # Number of employees in this unit
    has_responsible: bool = False
    responsible_name: Optional[str] = None

    # Children for tree structure
    children: List['OrgUnitTreeNode'] = []

    class Config:
        from_attributes = True


# Enable forward references for recursive model
OrgUnitTreeNode.model_rebuild()


class OrgUnitListItem(BaseModel):
    """Simplified model for org unit lists"""
    org_unit_id: int
    codice: str
    descrizione: str
    livello: Optional[int]
    cdccosto: Optional[str]
    parent_org_unit_id: Optional[int]
    employee_count: int = 0
    responsible_name: Optional[str] = None
    active: bool

    class Config:
        from_attributes = True


class OrgUnitDetails(OrgUnit):
    """
    Extended model with additional details for display.
    """
    employee_count: int = 0
    responsible_name: Optional[str] = None
    parent_name: Optional[str] = None
    company_name: Optional[str] = None

    # Lists of employees in this unit
    employees: List[dict] = []

    class Config:
        from_attributes = True
