"""Pydantic request schemas. Units are explicit in field names. Unknown fields are rejected."""
from typing import Optional, Literal, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Equipment(Strict):
    brand: str = "H&M"
    model_code: Optional[str] = None
    configuration: str = "VHP"
    refrigerant: str = "R134a"
    rows: Optional[int] = None
    tube_nominal: Optional[str] = None
    tube_od_mm: Optional[float] = None
    tube_thk_mm: Optional[float] = None
    tube_type: Optional[str] = None
    transverse_pitch_mm: Optional[float] = None
    longitudinal_pitch_mm: Optional[float] = None
    fin_material: Optional[str] = None
    fin_thk_mm: Optional[float] = None
    fin_pitch_mm: Optional[float] = None
    fin_type: Optional[str] = None
    fin_coating: Optional[str] = None
    frame: Optional[str] = None
    tubes_per_row: Optional[int] = None
    fin_length_mm: Optional[float] = None
    fin_height_mm: Optional[float] = None
    circuits: Optional[int] = None
    circuit_orientation: Optional[str] = None
    installation: Optional[str] = None
    altitude_m: Optional[float] = 0
    site_pressure_pa: Optional[float] = None


class Stream(Strict):
    flow: float
    flow_unit: Literal["cfm", "m3/s", "m3/h", "l/s"] = "cfm"
    flow_basis: Literal["actual", "standard"] = "actual"
    input_mode: Literal["db_rh", "db_wb"] = "db_rh"
    db: float
    rh: Optional[float] = None
    wb: Optional[float] = None
    fin_length_mm: Optional[float] = None
    measured_density: Optional[float] = None


class Case(Strict):
    project: Dict[str, Any] = Field(default_factory=dict)
    equipment: Equipment
    scenario: Literal["cooling", "heating"]
    supply: Stream
    exhaust: Stream
    models: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    tolerances: Optional[Dict[str, float]] = None

    def to_core(self):
        d = self.model_dump()
        if d["tolerances"] is None:
            d.pop("tolerances")
        return d


class PsychroRequest(Strict):
    db: float
    mode: Literal["db_rh", "db_wb"]
    rh: Optional[float] = None
    wb: Optional[float] = None
    altitude_m: Optional[float] = 0
    site_pressure_pa: Optional[float] = None


class SweepRequest(Strict):
    case: Case
    factors: List[float] = Field(default_factory=lambda: [0.6, 0.8, 1.0, 1.2, 1.4], max_length=25)
