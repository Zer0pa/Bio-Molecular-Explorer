"""L4 toy adapter — second, deliberately-different stub for plug-replaceability testing.

Same public interface as L4StubAdapter.process() but different FMU step dt:
  - dt = 0.5s (stub uses 1.0s)
  - Same N_STEPS = 5
  - Same digital_twin_ready logic
  - Same back_edges target (L2.5) on unmanufacturable unit ops
  - Same falsifier classes emitted

RESEARCH USE ONLY — not for clinical deployment, diagnosis, or prescribing.
"""

from __future__ import annotations

import math
from typing import Any

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


_ADAPTER_NAME = "l4-toy"
_ADAPTER_VERSION = "0.1.0"
_ENGINE = "toy_fmu_half_step"

# TOY DIFFERENTIATOR: dt = 0.5s instead of stub's 1.0s
_N_STEPS = 5
_DT_S = 0.5  # different from stub (1.0)

_DEFAULT_STUB_INPUTS: dict[str, float] = {
    "temperature_C": 25.0,
    "pressure_bar": 1.0,
    "flow_kg_s": 0.01,
}

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
    lower = unit_op_name.lower()
    for substring, kind in _KIND_MAP:
        if substring in lower:
            return kind
    return "generic"


class L4ToyAdapter:
    """L4 toy adapter — dt=0.5s FMU steps, identical schema.

    process(input, run_id=None) -> LayerEnvelope
    Same interface as L4StubAdapter.
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
        rid = run_id or new_run_id()
        input_dict = input.model_dump()

        # a) Register FMUs
        for op_name in input.process_graph_unit_ops:
            kind = _infer_kind(op_name)
            default_state = {
                "temperature_C": 25.0,
                "pressure_bar": 1.0,
                "throughput_kg_s": input.target_throughput_kg_per_batch / 3600.0,
            }
            self._bus.register_fmu(name=op_name, kind=kind, default_state=default_state)

        # b) Step each FMU _N_STEPS times at TOY dt=0.5s
        for op_name in input.process_graph_unit_ops:
            for _ in range(_N_STEPS):
                self._bus.step(name=op_name, dt_s=_DT_S, inputs=_DEFAULT_STUB_INPUTS)

        fmu_snapshots: list[L4FMUUnitState] = self._bus.snapshot()

        # c) Sensor states
        sensor_states: list[L4SensorState] = list(input.sensor_states)

        # d) detect_l4_sensor_failure
        sensor_item: EnvelopeFalsifierItem = detect_l4_sensor_failure(sensor_states)

        # e) detect_nan_or_nonfinite on FMU outputs
        all_fmu_output_values: list[float] = []
        for snap in fmu_snapshots:
            all_fmu_output_values.extend(snap.outputs.values())
            all_fmu_output_values.extend(snap.state_vars.values())

        nonfinite_item: EnvelopeFalsifierItem = detect_nan_or_nonfinite(
            all_fmu_output_values, context="toy_fmu_outputs"
        )

        falsifier_items: list[EnvelopeFalsifierItem] = [sensor_item, nonfinite_item]

        # f) digital_twin_ready (same logic as stub)
        sensor_pass = sensor_item.status == FalsifierStatus.PASS
        nonfinite_pass = nonfinite_item.status == FalsifierStatus.PASS
        fmus_produced = len(fmu_snapshots) > 0
        digital_twin_ready = sensor_pass and nonfinite_pass and fmus_produced

        # g) manufacturability_backedges
        unmanufacturable_ops: list[str] = []

        if not sensor_pass:
            unmanufacturable_ops.extend(input.process_graph_unit_ops)
        else:
            for s in sensor_states:
                if s.value is None or not s.in_range:
                    for op in input.process_graph_unit_ops:
                        if op not in unmanufacturable_ops:
                            unmanufacturable_ops.append(op)
                    break
                if isinstance(s.value, float) and (math.isnan(s.value) or math.isinf(s.value)):
                    for op in input.process_graph_unit_ops:
                        if op not in unmanufacturable_ops:
                            unmanufacturable_ops.append(op)
                    break

        if not nonfinite_pass:
            for op in input.process_graph_unit_ops:
                if op not in unmanufacturable_ops:
                    unmanufacturable_ops.append(op)

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

        # Confidence (toy: 0.55 if ready instead of 0.6)
        confidence_score = 0.55 if digital_twin_ready else 0.45
        confidence_band = ConfidenceBand.MEDIUM if digital_twin_ready else ConfidenceBand.LOW
        confidence_basis = ["toy_FMU_half_step_dynamics", "stub_sensor_states_provided_by_caller"]

        # Back-edges to L2.5
        back_edges: list[BackEdge] = []
        if unmanufacturable_ops:
            triggered_by = (
                sensor_item.falsifier_id if not sensor_pass else nonfinite_item.falsifier_id
            )
            back_edges.append(
                BackEdge(
                    target_layer=LayerName.L2_5,
                    reason=(
                        "L4 toy virtual plant detected unmanufacturable unit ops; "
                        "route reselection required at L2.5."
                    ),
                    proposed_constraint={"unmanufacturable_unit_ops": unmanufacturable_ops},
                    triggered_by_falsifier_id=triggered_by,
                )
            )

        any_fail = any(item.status == FalsifierStatus.FAIL for item in falsifier_items)
        falsifier_status = FalsifierStatus.FAIL if any_fail else FalsifierStatus.PASS

        return LayerEnvelope(
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
