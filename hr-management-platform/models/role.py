"""
Role Models

Pydantic models for role management (TNS, SGSL, GDPR roles).
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date, datetime


class RoleDefinition(BaseModel):
    """
    Role definition model.

    Maps to role_definitions table.
    Defines available roles in the system.
    """
    role_id: Optional[int] = None
    role_code: str = Field(..., description="Unique code for role (e.g., APPROVATORE)")
    role_name: str = Field(..., description="Human-readable role name")
    role_category: str = Field(..., description="Category: TNS, SGSL, GDPR, AFC, HR, OTHER")
    description: Optional[str] = None
    icon: Optional[str] = Field(None, description="Emoji icon for role")
    color_hex: Optional[str] = Field(None, description="Color code for UI")
    requires_scope: bool = Field(False, description="True if role requires org_unit scope")
    is_mandatory: bool = Field(False, description="True if role is mandatory for units")
    active: bool = True
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @validator('role_category')
    def validate_category(cls, v):
        """Validate role category"""
        valid_categories = ['TNS', 'SGSL', 'GDPR', 'AFC', 'HR', 'OTHER']
        if v not in valid_categories:
            raise ValueError(f"Role category must be one of {valid_categories}")
        return v


class RoleAssignment(BaseModel):
    """
    Role assignment model.

    Maps to role_assignments table.
    Assigns roles to employees with temporal validity.
    """
    assignment_id: Optional[int] = None
    employee_id: int = Field(..., description="FK to employees")
    role_id: int = Field(..., description="FK to role_definitions")
    org_unit_id: Optional[int] = Field(None, description="FK to org_units (NULL = global scope)")

    effective_date: date = Field(..., description="Start date of assignment")
    end_date: Optional[date] = Field(None, description="End date (NULL = current)")

    assigned_by: Optional[str] = Field(None, description="Who assigned this role")
    notes: Optional[str] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @validator('end_date')
    def validate_end_date(cls, v, values):
        """Validate end date is after effective date"""
        if v and values.get('effective_date') and v < values['effective_date']:
            raise ValueError("End date must be after effective date")
        return v


class RoleAssignmentCreate(BaseModel):
    """Model for creating a new role assignment"""
    employee_id: int
    role_id: int
    org_unit_id: Optional[int] = None
    effective_date: date
    end_date: Optional[date] = None
    notes: Optional[str] = None


class RoleAssignmentUpdate(BaseModel):
    """Model for updating a role assignment"""
    end_date: Optional[date] = None
    notes: Optional[str] = None


class RoleAssignmentListItem(BaseModel):
    """Simplified model for role assignment lists"""
    assignment_id: int
    employee_id: int
    employee_name: str
    role_id: int
    role_code: str
    role_name: str
    role_category: str
    org_unit_id: Optional[int]
    org_unit_name: Optional[str]
    effective_date: date
    end_date: Optional[date]
    is_active: bool  # Computed: True if currently active

    class Config:
        from_attributes = True


class EmployeeRoles(BaseModel):
    """
    Model representing all roles for an employee.

    Used for displaying employee role matrix.
    """
    employee_id: int
    employee_name: str
    tx_cod_fiscale: str

    # TNS roles (19 roles)
    viaggiatore: bool = False
    approvatore: bool = False
    controllore: bool = False
    cassiere: bool = False
    segretario: bool = False
    visualizzatori: bool = False
    amministrazione: bool = False

    # SGSL roles
    rspp: bool = False
    rls: bool = False
    coord_hse: bool = False

    # GDPR roles
    dpo: bool = False
    delegato_privacy: bool = False

    # AFC/HR roles
    ruoli_afc: bool = False
    ruoli_hr: bool = False

    # All role details
    role_assignments: List[RoleAssignmentListItem] = []

    class Config:
        from_attributes = True


class RoleMatrix(BaseModel):
    """
    Model for role matrix view.

    Shows employees × roles matrix for a specific category.
    """
    category: str  # TNS, SGSL, GDPR, etc.
    roles: List[RoleDefinition]
    employees: List[EmployeeRoles]


class RoleCoverageReport(BaseModel):
    """
    Model for role coverage validation report.

    Checks if organizational units have required role coverage.
    """
    org_unit_id: int
    org_unit_name: str
    required_roles: List[str]  # List of role codes that are required
    missing_roles: List[str]  # List of role codes that are missing
    has_full_coverage: bool  # True if all required roles are assigned

    class Config:
        from_attributes = True
