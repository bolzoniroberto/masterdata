"""
Hierarchy Models

Pydantic models for managing multiple organizational hierarchies.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date, datetime


class HierarchyType(BaseModel):
    """
    Hierarchy type model.

    Maps to hierarchy_types table.
    Defines the 5 types of hierarchies: HR, TNS, SGSL, GDPR, IT_DIR.
    """
    hierarchy_type_id: Optional[int] = None
    type_code: str = Field(..., description="Unique code: HR, TNS, SGSL, GDPR, IT_DIR")
    type_name: str = Field(..., description="Human-readable name")
    description: Optional[str] = None
    color_hex: Optional[str] = Field(None, description="Color for UI visualization")
    active: bool = True
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @validator('type_code')
    def validate_type_code(cls, v):
        """Validate hierarchy type code"""
        valid_codes = ['HR', 'TNS', 'SGSL', 'GDPR', 'IT_DIR']
        if v not in valid_codes:
            raise ValueError(f"Type code must be one of {valid_codes}")
        return v


class HierarchyAssignment(BaseModel):
    """
    Hierarchy assignment model.

    Maps to hierarchy_assignments table.
    Assigns employees to org units for specific hierarchy types.
    """
    assignment_id: Optional[int] = None
    employee_id: int = Field(..., description="FK to employees")
    org_unit_id: int = Field(..., description="FK to org_units")
    hierarchy_type_id: int = Field(..., description="FK to hierarchy_types")

    effective_date: date = Field(..., description="Start date of assignment")
    end_date: Optional[date] = Field(None, description="End date (NULL = current)")
    is_primary: bool = Field(False, description="True if this is primary assignment")

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


class HierarchyAssignmentCreate(BaseModel):
    """Model for creating a new hierarchy assignment"""
    employee_id: int
    org_unit_id: int
    hierarchy_type_id: int
    effective_date: date
    end_date: Optional[date] = None
    is_primary: bool = False
    notes: Optional[str] = None


class HierarchyAssignmentUpdate(BaseModel):
    """Model for updating a hierarchy assignment"""
    org_unit_id: Optional[int] = None
    end_date: Optional[date] = None
    is_primary: Optional[bool] = None
    notes: Optional[str] = None


class HierarchyAssignmentListItem(BaseModel):
    """Simplified model for hierarchy assignment lists"""
    assignment_id: int
    employee_id: int
    employee_name: str
    org_unit_id: int
    org_unit_name: str
    hierarchy_type_id: int
    hierarchy_type_code: str
    hierarchy_type_name: str
    effective_date: date
    end_date: Optional[date]
    is_primary: bool
    is_active: bool  # Computed: True if currently active

    class Config:
        from_attributes = True


class EmployeeHierarchies(BaseModel):
    """
    Model representing all hierarchy assignments for an employee.

    Shows which org units an employee belongs to in each hierarchy.
    """
    employee_id: int
    employee_name: str
    tx_cod_fiscale: str

    # Hierarchy assignments by type
    hr_hierarchy: Optional[HierarchyAssignmentListItem] = None
    tns_hierarchy: Optional[HierarchyAssignmentListItem] = None
    sgsl_hierarchy: Optional[HierarchyAssignmentListItem] = None
    gdpr_hierarchy: Optional[HierarchyAssignmentListItem] = None
    it_hierarchy: Optional[HierarchyAssignmentListItem] = None

    # All assignments
    all_assignments: List[HierarchyAssignmentListItem] = []

    class Config:
        from_attributes = True


class HierarchyTreeNode(BaseModel):
    """
    Model for hierarchy tree representation.

    Used for building orgchart JSON for d3-org-chart.
    """
    # Node identification
    id: str  # Unique ID for d3-org-chart
    employee_id: Optional[int] = None
    org_unit_id: Optional[int] = None

    # Display data
    name: str  # Employee or org unit name
    title: Optional[str] = None  # Qualifica or role
    area: Optional[str] = None
    photo: Optional[str] = None

    # Role badges
    roles: List[str] = []  # List of role icons/codes

    # Hierarchy info
    hierarchy_type: str  # HR, TNS, SGSL, etc.
    parent_id: Optional[str] = None

    # Subordinates
    subordinate_count: int = 0
    children: List['HierarchyTreeNode'] = []

    class Config:
        from_attributes = True


# Enable forward references for recursive model
HierarchyTreeNode.model_rebuild()


class ApprovalChain(BaseModel):
    """
    Model representing approval chain in TNS hierarchy.

    Shows the path from employee to top approver.
    """
    employee_id: int
    employee_name: str

    chain: List[dict] = []  # List of {employee_id, name, role, level}

    top_approver_id: Optional[int] = None
    top_approver_name: Optional[str] = None

    class Config:
        from_attributes = True


class HierarchyStats(BaseModel):
    """
    Statistics for a specific hierarchy type.

    Used for dashboard and reporting.
    """
    hierarchy_type_code: str
    hierarchy_type_name: str

    total_org_units: int = 0
    total_employees_assigned: int = 0
    employees_without_assignment: int = 0
    org_units_without_responsible: int = 0

    # Coverage metrics
    coverage_percentage: float = 0.0  # % of employees with assignment

    class Config:
        from_attributes = True
