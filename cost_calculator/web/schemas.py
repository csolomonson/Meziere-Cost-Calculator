"""Request models for the public HTTP API."""

from pydantic import BaseModel, Field


class MarkupBreak(BaseModel):
    breakQty: float = Field(..., gt=0)
    material: float = Field(1, gt=0)
    labor: float = Field(1, gt=0)
    machine: float = Field(1, gt=0)
    external: float = Field(1, gt=0)
    additional: float = Field(1, gt=0)


class CostRequest(BaseModel):
    part_id: str = Field(..., min_length=1)
    revision_id: str = ""
    quantity: float = Field(1, gt=0)
    markup_breaks: list[MarkupBreak] | None = None
    # Retained for request-schema compatibility. HTTP costing is attributed to
    # the authenticated principal, just as it was before the module split.
    costed_by: str | None = None
    notes: str | None = None
    make_current: bool = False


class SettingsRequest(BaseModel):
    part_id: str | None = None
    revision_id: str = ""
    markup_breaks: list[MarkupBreak] = []
    global_markup_breaks: list[MarkupBreak] | None = None
    part_markup_breaks: list[MarkupBreak] | None = None
    markup_break_scope: str = "part"
    global_defaults: dict | None = None
    machine_defaults: dict = {}
    shift_settings: dict | None = None


class CostRunSaveRequest(BaseModel):
    part_cost: dict
    operation_lines: list[dict] = []
    material_lines: list[dict] = []
    make_current: bool = False


class CurrentCostRequest(BaseModel):
    part_cost_id: int


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8, max_length=1024)
    groups: list[str] = Field(default_factory=lambda: ["users"])


class UserUpdateRequest(BaseModel):
    password: str | None = Field(default=None, min_length=8, max_length=1024)
    groups: list[str] | None = None


class ConversionCalculationRequest(BaseModel):
    mode: str
    values: dict[str, float] = Field(default_factory=dict)
    multiplier: float = 0
