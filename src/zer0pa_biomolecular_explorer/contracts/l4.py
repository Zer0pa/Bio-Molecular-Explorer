"""L4 — Manufacturing digital twin contracts.

Inputs: process graph, unit ops, sensor-state stubs.
Outputs: FMU-like unit states, digital twin readiness, manufacturability backedges.
Replaceable tools: PharmaPy, OpenModelica, FMI/FMU, Eclipse Ditto, OpenFOAM, stubs.

CORRECTION (Brief #2): COPASI/Tellurium are L5, NOT L4 — they model biochemical
networks, not manufacturing equipment. L4 needs equipment-level dynamic simulation
linked to PAT sensor streams.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class L4SensorClass(str, Enum):
    NIR = "NIR"  # near-infrared
    PAT_TEMP = "PAT_temperature"
    PAT_PRESSURE = "PAT_pressure"
    PAT_FLOW = "PAT_flow"
    PAT_PH = "PAT_pH"
    PAT_RAMAN = "PAT_raman"
    SCALE = "scale"


class L4SensorState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sensor_id: str
    sensor_class: L4SensorClass
    value: float | None = Field(
        default=None,
        description="Current reading; None means stale/missing → triggers L4 sensor falsifier.",
    )
    unit: str
    timestamp_utc: str
    in_range: bool
    expected_range: tuple[float, float] | None = None


class L4FMUUnitState(BaseModel):
    """Snapshot of a single unit operation modeled as an FMU-like component."""

    model_config = ConfigDict(extra="forbid")

    fmu_name: str
    unit_op_kind: str
    inputs: dict[str, float] = Field(default_factory=dict)
    outputs: dict[str, float] = Field(default_factory=dict)
    state_vars: dict[str, float] = Field(default_factory=dict)
    sim_time_s: float = Field(ge=0.0)


class L4VirtualPlantInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    process_graph_unit_ops: list[str]  # unit-op names from L3
    sensor_states: list[L4SensorState] = Field(default_factory=list)
    target_throughput_kg_per_batch: float = Field(default=1.0, gt=0.0)


class L4VirtualPlantOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fmu_states: list[L4FMUUnitState]
    sensor_states: list[L4SensorState]
    digital_twin_ready: bool
    manufacturability_backedges: list[str] = Field(
        default_factory=list,
        description="Names of unit ops that fail manufacturability and should feed back into L2.5/L3.",
    )
    sensor_fault_count: int = Field(ge=0)
    bus_format: str = Field(default="FMI_2_0", description="Co-simulation bus format identifier.")
