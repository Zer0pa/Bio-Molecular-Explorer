"""L4 stub adapter — manufacturing digital twin.

Virtual plant = FMU co-simulation bus (FMI 2.0/3.0) + Eclipse Ditto PAT sensors.

Toolchain (real):
    - PharmaPy      : pharma process models (continuous/batch reactors, crystallizers)
    - OpenModelica  : general equipment-level Modelica simulation → FMU export
    - FMI/FMU       : Functional Mock-up Interface co-simulation standard
    - Eclipse Ditto : IoT digital twin for PAT sensor streams
    - OpenFOAM      : CFD for heat/mass transfer in mixing vessels

CORRECTION (Brief #2): COPASI and Tellurium are L5 (PKPD/QSP), NOT L4.
L4 is equipment-level, not biochemical-network-level.

Inversion C (design intent):
    The virtual plant is built BEFORE a synthesis route is known (L2.5).
    If any unit op is unmanufacturable, a back_edge to L2.5 is emitted so that
    route selection is constrained by plant feasibility.
"""

from __future__ import annotations

import math
from typing import Any

from zer0pa_health.boundary import RESEARCH_BOUNDARY
from zer0pa_health.contracts.l4 import (
    L4FMUUnitState,
    L4SensorState,
    L4VirtualPlantInput,
    L4VirtualPlantOutput,
)
from zer0pa_health.envelope import (
    Backend,
    BackEdge,
    ConfidenceBand,
    EnvelopeAudit,
    EnvelopeConfidence,
    EnvelopeFalsifier,
    EnvelopeFalsifierItem,
    FalsifierStatus,
    LayerEnvelope,
    LayerName,
    ToolAdapter,
)
from zer0pa_health.falsifiers.detectors import (
    detect_l4_sensor_failure,
    detect_nan_or_nonfinite,
)
from zer0pa_health.hashing import sha256_of_obj
from zer0pa_health.ids import audit_id, run_id as new_run_id
from zer0pa_health.layers.l4.ditto import EclipseDittoStub
from zer0pa_health.layers.l4.fmu_bus import FMUStubBus


_ADAPTER_NAME = "l4-stub"
_ADAPTER_VERSION = "0.1.0"
_ENGINE = "stub_fmu_ditto"

# How many simulation steps to run per registered FMU
_N_STEPS = 5
_DT_S = 1.0

# Stub inputs used for FMU stepping when no external inputs are provided
_DEFAULT_STUB_INPUTS: dict[str, float] = {
    "temperature_C": 25.0,
    "pressure_bar": 1.0,
    "flow_kg_s": 0.01,
}

# Map unit-op name substrings to FMU kind strings
_KIND_MAP: list[tuple[str, str]] = [
    ("reaction", "reaction"),
    ("crystallization", "crystallization"),
    ("crystallisation", "crystallization"),
    ("filtration", "filtration"),
    ("drying", "drying"),
    ("granulation", "granulation"),
    ("blending", "blending"),
    ("tablet", "tablet_compression"),
    ("distillation", "distillation"),
    ("extraction", "extraction"),
    ("chromatography", "chromatography"),
]


def _infer_kind(unit_op_name: str) -> str:
    """Infer unit-op kind from name substring matching."""
    lower = unit_op_name.lower()
    for substring, kind in _KIND_MAP:
        if substring in lower:
            return kind
    return "generic"


class L4StubAdapter:
    """CPU-side stub adapter for L4 manufacturing digital twin.

    Wires together:
        - FMUStubBus  (FMI 2.0/3.0 co-simulation)
        - EclipseDittoStub (PAT sensor digital twin)

    Returns a LayerEnvelope with L4VirtualPlantOutput as the `output` dict.
    Back-edges target L2.5 (route reselection) when unit ops are unmanufacturable.

    No COPASI or Tellurium — those are L5 (PKPD/QSP).
    """

    def __init__(
        self,
        bus: FMUStubBus | None = None,
        ditto: EclipseDittoStub | None = None,
    ) -> None:
        self._bus = bus if bus is not None else FMUStubBus()
        self._ditto = ditto if ditto is not None else EclipseDittoStub()

    def process(
        self,
        input: L4VirtualPlantInput,
        run_id: str | None = None,
    ) -> LayerEnvelope:
        """Run the virtual plant simulation and return a LayerEnvelope.

        Steps:
            a) Register an FMU for each unit op in input.process_graph_unit_ops.
            b) Step each FMU _N_STEPS times, capture snapshots.
            c) Use input.sensor_states as authoritative sensor readings.
            d) Run detect_l4_sensor_failure on sensors.
            e) Run detect_nan_or_nonfinite on all FMU output values.
            f) digital_twin_ready = sensor PASS AND nonfinite PASS AND FMUs stepped.
            g) manufacturability_backedges = unit ops with sensor issues or None/NaN values.
            h) Emit back_edge to L2.5 if any unmanufacturable unit ops found.
        """
        rid = run_id or new_run_id()
        input_dict = input.model_dump()

        # ------------------------------------------------------------------
        # a) Register FMUs for each unit op
        # ------------------------------------------------------------------
        for op_name in input.process_graph_unit_ops:
            kind = _infer_kind(op_name)
            default_state = {
                "temperature_C": 25.0,
                "pressure_bar": 1.0,
                "throughput_kg_s": input.target_throughput_kg_per_batch / 3600.0,
            }
            # Register (re-registration is safe: overwrites existing entry)
            self._bus.register_fmu(name=op_name, kind=kind, default_state=default_state)

        # ------------------------------------------------------------------
        # b) Step each FMU _N_STEPS times
        # ------------------------------------------------------------------
        for op_name in input.process_graph_unit_ops:
            for _ in range(_N_STEPS):
                self._bus.step(name=op_name, dt_s=_DT_S, inputs=_DEFAULT_STUB_INPUTS)

        fmu_snapshots: list[L4FMUUnitState] = self._bus.snapshot()

        # ------------------------------------------------------------------
        # c) Sensor states — authoritative from caller (Ditto would augment)
        # ------------------------------------------------------------------
        sensor_states: list[L4SensorState] = list(input.sensor_states)

        # ------------------------------------------------------------------
        # d) detect_l4_sensor_failure
        # ------------------------------------------------------------------
        sensor_item: EnvelopeFalsifierItem = detect_l4_sensor_failure(sensor_states)

        # ------------------------------------------------------------------
        # e) detect_nan_or_nonfinite on all FMU output values
        # ------------------------------------------------------------------
        all_fmu_output_values: list[float] = []
        for snap in fmu_snapshots:
            all_fmu_output_values.extend(snap.outputs.values())
            all_fmu_output_values.extend(snap.state_vars.values())

        nonfinite_item: EnvelopeFalsifierItem = detect_nan_or_nonfinite(
            all_fmu_output_values, context="fmu_outputs"
        )

        falsifier_items: list[EnvelopeFalsifierItem] = [sensor_item, nonfinite_item]

        # ------------------------------------------------------------------
        # f) digital_twin_ready
        # ------------------------------------------------------------------
        sensor_pass = sensor_item.status == FalsifierStatus.PASS
        nonfinite_pass = nonfinite_item.status == FalsifierStatus.PASS
        fmus_produced = len(fmu_snapshots) > 0
        digital_twin_ready = sensor_pass and nonfinite_pass and fmus_produced

        # ------------------------------------------------------------------
        # g) manufacturability_backedges
        # ------------------------------------------------------------------
        # Flag unit ops where any associated sensor is stale/out-of-range/nonfinite
        # Since sensors are not directly tagged to unit ops in this stub, we flag
        # ALL unit ops if ANY sensor fails (conservative approach for back-edge).
        # Additionally, flag ops where FMU output values are non-finite.
        unmanufacturable_ops: list[str] = []

        if not sensor_pass:
            # All unit ops are potentially affected by sensor failure
            unmanufacturable_ops.extend(input.process_graph_unit_ops)
        else:
            # Check individual sensor states for out-of-range or None values
            for s in sensor_states:
                if s.value is None or not s.in_range:
                    # Sensor failure — mark all ops as unmanufacturable
                    for op in input.process_graph_unit_ops:
                        if op not in unmanufacturable_ops:
                            unmanufacturable_ops.append(op)
                    break
                if isinstance(s.value, float) and (math.isnan(s.value) or math.isinf(s.value)):
                    for op in input.process_graph_unit_ops:
                        if op not in unmanufacturable_ops:
                            unmanufacturable_ops.append(op)
                    break

        # Also flag individual ops with non-finite FMU outputs
        if not nonfinite_pass:
            for op in input.process_graph_unit_ops:
                if op not in unmanufacturable_ops:
                    unmanufacturable_ops.append(op)

        # ------------------------------------------------------------------
        # Build output
        # ------------------------------------------------------------------
        sensor_fault_count = sum(
            1
            for s in sensor_states
            if s.value is None
            or not s.in_range
            or (isinstance(s.value, float) and (math.isnan(s.value) or math.isinf(s.value)))
        )

        plant_output = L4VirtualPlantOutput(
            fmu_states=fmu_snapshots,
            sensor_states=sensor_states,
            digital_twin_ready=digital_twin_ready,
            manufacturability_backedges=unmanufacturable_ops,
            sensor_fault_count=sensor_fault_count,
            bus_format=self._bus.bus_format,
        )
        output_dict: dict[str, Any] = plant_output.model_dump()

        # ------------------------------------------------------------------
        # Confidence
        # ------------------------------------------------------------------
        # Stub: 0.5-0.7 range; lower if sensor faults present
        confidence_score = 0.6 if digital_twin_ready else 0.5
        confidence_band = ConfidenceBand.MEDIUM if digital_twin_ready else ConfidenceBand.LOW
        confidence_basis = ["stub_FMU_dynamics", "stub_sensor_states_provided_by_caller"]

        # ------------------------------------------------------------------
        # Back-edges to L2.5 (route reselection)
        # ------------------------------------------------------------------
        back_edges: list[BackEdge] = []
        if unmanufacturable_ops:
            triggered_by = (
                sensor_item.falsifier_id
                if not sensor_pass
                else nonfinite_item.falsifier_id
            )
            back_edges.append(
                BackEdge(
                    target_layer=LayerName.L2_5,
                    reason=(
                        "L4 virtual plant detected unmanufacturable unit ops; "
                        "route reselection required at L2.5."
                    ),
                    proposed_constraint={"unmanufacturable_unit_ops": unmanufacturable_ops},
                    triggered_by_falsifier_id=triggered_by,
                )
            )

        # ------------------------------------------------------------------
        # Assemble envelope
        # ------------------------------------------------------------------
        any_fail = any(item.status == FalsifierStatus.FAIL for item in falsifier_items)
        falsifier_status = FalsifierStatus.FAIL if any_fail else FalsifierStatus.PASS

        envelope = LayerEnvelope(
            run_id=rid,
            layer=LayerName.L4,
            tool_adapter=ToolAdapter(
                name=_ADAPTER_NAME,
                version=_ADAPTER_VERSION,
                backend=Backend.STUB,
                engine=_ENGINE,
            ),
            input_refs=[],
            output=output_dict,
            confidence=EnvelopeConfidence(
                score=confidence_score,
                band=confidence_band,
                basis=confidence_basis,
            ),
            falsifier=EnvelopeFalsifier(
                status=falsifier_status,
                items=falsifier_items,
            ),
            audit=EnvelopeAudit(
                audit_record_id=audit_id(),
                input_hash=sha256_of_obj(input_dict),
                output_hash=sha256_of_obj(output_dict),
                source_manifest_refs=[],
            ),
            back_edges=back_edges,
        )

        return envelope
