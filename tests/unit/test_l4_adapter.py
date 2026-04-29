"""Unit tests for L4 manufacturing digital twin adapter.

Coverage:
    - FMUStubBus: register, step, snapshot
    - EclipseDittoStub: add_sensor, read_sensors, inject_fault
    - L4StubAdapter.process: healthy path, sensor failure, NaN injection
    - Envelope validates against schemas/envelope/layer-envelope-v1.json
"""

from __future__ import annotations

import json
import math
import pathlib
from datetime import datetime, timezone

import pytest

from zer0pa_health.contracts.l4 import (
    L4SensorClass,
    L4SensorState,
    L4VirtualPlantInput,
)
from zer0pa_health.envelope import FalsifierStatus, LayerName
from zer0pa_health.layers.l4 import EclipseDittoStub, FMUStubBus, L4StubAdapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _healthy_sensor(sensor_id: str = "T-01", value: float = 35.0) -> L4SensorState:
    return L4SensorState(
        sensor_id=sensor_id,
        sensor_class=L4SensorClass.PAT_TEMP,
        value=value,
        unit="C",
        timestamp_utc=_utc_now(),
        in_range=True,
        expected_range=(20.0, 60.0),
    )


def _load_stale_fixture() -> list[L4SensorState]:
    """Load the negative fixture l4_sensor_stale.json and return sensor states."""
    fixture_path = (
        pathlib.Path(__file__).parent.parent.parent / "fixtures" / "negative" / "l4_sensor_stale.json"
    )
    data = json.loads(fixture_path.read_text())
    sensors = []
    for s in data["sensors"]:
        expected_range = s.get("expected_range")
        sensors.append(
            L4SensorState(
                sensor_id=s["sensor_id"],
                sensor_class=L4SensorClass(s["sensor_class"]),
                value=s["value"],
                unit=s["unit"],
                timestamp_utc=s["timestamp_utc"],
                in_range=s["in_range"],
                expected_range=tuple(expected_range) if expected_range else None,
            )
        )
    return sensors


# ---------------------------------------------------------------------------
# FMUStubBus tests
# ---------------------------------------------------------------------------

class TestFMUStubBus:
    def test_register_and_snapshot_two_fmus(self) -> None:
        bus = FMUStubBus()
        bus.register_fmu("reaction_01", "reaction", {"temperature_C": 30.0})
        bus.register_fmu("crystallization_01", "crystallization", {"temperature_C": 5.0})

        snaps = bus.snapshot()
        assert len(snaps) == 2
        names = {s.fmu_name for s in snaps}
        assert "reaction_01" in names
        assert "crystallization_01" in names

    def test_step_returns_finite_outputs(self) -> None:
        bus = FMUStubBus()
        bus.register_fmu("reaction_01", "reaction", {"temperature_C": 30.0, "pressure_bar": 1.5})

        state = bus.step("reaction_01", dt_s=1.0, inputs={"temperature_C": 30.0, "pressure_bar": 1.5})

        assert state.fmu_name == "reaction_01"
        assert state.unit_op_kind == "reaction"
        assert state.sim_time_s == pytest.approx(1.0)

        for v in state.outputs.values():
            assert math.isfinite(v), f"Non-finite output: {v}"
        for v in state.state_vars.values():
            assert math.isfinite(v), f"Non-finite state_var: {v}"

    def test_two_fmus_step_and_snapshot_both_have_entries(self) -> None:
        bus = FMUStubBus()
        bus.register_fmu("fmu_a", "reaction", {"temperature_C": 25.0})
        bus.register_fmu("fmu_b", "drying", {"temperature_C": 80.0})

        for name in ("fmu_a", "fmu_b"):
            bus.step(name, dt_s=1.0, inputs={"temperature_C": 25.0, "pressure_bar": 1.0})

        snaps = bus.snapshot()
        assert len(snaps) == 2
        for snap in snaps:
            for v in snap.outputs.values():
                assert math.isfinite(v)

    def test_deterministic_dynamics(self) -> None:
        """Same inputs must produce same outputs on a fresh bus."""
        inputs = {"temperature_C": 40.0, "pressure_bar": 2.0}

        bus1 = FMUStubBus()
        bus1.register_fmu("op", "reaction", {"temperature_C": 25.0})
        state1 = bus1.step("op", dt_s=1.0, inputs=inputs)

        bus2 = FMUStubBus()
        bus2.register_fmu("op", "reaction", {"temperature_C": 25.0})
        state2 = bus2.step("op", dt_s=1.0, inputs=inputs)

        assert state1.outputs == state2.outputs
        assert state1.state_vars == state2.state_vars

    def test_bus_format_default(self) -> None:
        bus = FMUStubBus()
        assert bus.bus_format == "FMI_2_0"

    def test_bus_format_custom(self) -> None:
        bus = FMUStubBus(bus_format="FMI_3_0")
        assert bus.bus_format == "FMI_3_0"


# ---------------------------------------------------------------------------
# EclipseDittoStub tests
# ---------------------------------------------------------------------------

class TestEclipseDittoStub:
    def test_add_and_read_two_sensors(self) -> None:
        ditto = EclipseDittoStub()
        s1 = _healthy_sensor("T-01", 35.0)
        s2 = _healthy_sensor("T-02", 40.0)
        ditto.add_sensor(s1)
        ditto.add_sensor(s2)

        sensors = ditto.read_sensors()
        assert len(sensors) == 2
        ids = {s.sensor_id for s in sensors}
        assert "T-01" in ids
        assert "T-02" in ids

    def test_inject_fault_stale_sets_value_none(self) -> None:
        ditto = EclipseDittoStub()
        ditto.add_sensor(_healthy_sensor("T-01", 35.0))
        ditto.inject_fault("T-01", "stale")

        sensors = ditto.read_sensors()
        assert len(sensors) == 1
        assert sensors[0].value is None
        assert sensors[0].in_range is False

    def test_inject_fault_out_of_range(self) -> None:
        ditto = EclipseDittoStub()
        ditto.add_sensor(_healthy_sensor("T-01", 35.0))
        ditto.inject_fault("T-01", "out_of_range")

        sensors = ditto.read_sensors()
        assert sensors[0].in_range is False
        assert sensors[0].value is not None
        # Value should be outside [20, 60]
        v = sensors[0].value
        assert v < 20.0 or v > 60.0

    def test_inject_fault_nonfinite(self) -> None:
        ditto = EclipseDittoStub()
        ditto.add_sensor(_healthy_sensor("T-01", 35.0))
        ditto.inject_fault("T-01", "nonfinite")

        sensors = ditto.read_sensors()
        assert sensors[0].value is not None
        assert math.isnan(sensors[0].value)
        assert sensors[0].in_range is False

    def test_inject_fault_unknown_sensor_raises(self) -> None:
        ditto = EclipseDittoStub()
        with pytest.raises(KeyError):
            ditto.inject_fault("NONEXISTENT", "stale")


# ---------------------------------------------------------------------------
# L4StubAdapter tests
# ---------------------------------------------------------------------------

class TestL4StubAdapter:
    def test_healthy_single_op_and_sensor_digital_twin_ready(self) -> None:
        """Healthy sensor + one unit op → digital_twin_ready=True, no backedges."""
        adapter = L4StubAdapter()
        inp = L4VirtualPlantInput(
            process_graph_unit_ops=["reaction_step_01"],
            sensor_states=[_healthy_sensor("T-01", 35.0)],
            target_throughput_kg_per_batch=1.0,
        )
        envelope = adapter.process(inp)

        out = envelope.output
        assert out["digital_twin_ready"] is True
        assert out["manufacturability_backedges"] == []
        assert envelope.layer == "L4"
        assert envelope.falsifier.status == "pass"
        assert envelope.back_edges == []

    def test_stale_fixture_emits_sensor_fail_and_digital_twin_false(self) -> None:
        """l4_sensor_stale.json → l4_sensor_failure FAIL, digital_twin_ready=False."""
        sensors = _load_stale_fixture()
        adapter = L4StubAdapter()
        inp = L4VirtualPlantInput(
            process_graph_unit_ops=["reaction_main"],
            sensor_states=sensors,
            target_throughput_kg_per_batch=1.0,
        )
        envelope = adapter.process(inp)

        out = envelope.output
        assert out["digital_twin_ready"] is False
        assert len(out["manufacturability_backedges"]) > 0
        assert "reaction_main" in out["manufacturability_backedges"]

        # Check falsifier items
        item_classes = [item.falsifier_class for item in envelope.falsifier.items]
        assert "l4_sensor_failure" in item_classes

        sensor_item = next(
            i for i in envelope.falsifier.items if i.falsifier_class == "l4_sensor_failure"
        )
        assert sensor_item.status == "fail"

        # Back-edge to L2.5
        assert len(envelope.back_edges) >= 1
        be = envelope.back_edges[0]
        assert be.target_layer == "L2.5"
        assert "reaction_main" in be.proposed_constraint["unmanufacturable_unit_ops"]

    def test_stale_fixture_manufacturability_backedges_populated(self) -> None:
        """Confirm manufacturability_backedges is non-empty for stale fixture."""
        sensors = _load_stale_fixture()
        adapter = L4StubAdapter()
        inp = L4VirtualPlantInput(
            process_graph_unit_ops=["reaction_main", "crystallization_step"],
            sensor_states=sensors,
        )
        envelope = adapter.process(inp)
        assert len(envelope.output["manufacturability_backedges"]) > 0

    def test_nan_sensor_value_emits_nonfinite_fail(self) -> None:
        """Sensor with NaN value → nonfinite_input FAIL (via sensor falsifier)."""
        nan_sensor = L4SensorState(
            sensor_id="T-NaN",
            sensor_class=L4SensorClass.PAT_TEMP,
            value=float("nan"),
            unit="C",
            timestamp_utc=_utc_now(),
            in_range=False,
            expected_range=(20.0, 60.0),
        )
        adapter = L4StubAdapter()
        inp = L4VirtualPlantInput(
            process_graph_unit_ops=["reaction_nan_test"],
            sensor_states=[nan_sensor],
        )
        envelope = adapter.process(inp)

        item_classes = [item.falsifier_class for item in envelope.falsifier.items]
        # NaN in sensor value triggers l4_sensor_failure (detect_l4_sensor_failure handles NaN)
        assert "l4_sensor_failure" in item_classes
        sensor_item = next(
            i for i in envelope.falsifier.items if i.falsifier_class == "l4_sensor_failure"
        )
        assert sensor_item.status == "fail"
        assert envelope.output["digital_twin_ready"] is False

    def test_envelope_validates_against_json_schema(self) -> None:
        """Envelope must validate against schemas/envelope/layer-envelope-v1.json."""
        try:
            import jsonschema
        except ImportError:
            pytest.skip("jsonschema not installed")

        schema_path = (
            pathlib.Path(__file__).parent.parent.parent
            / "schemas"
            / "envelope"
            / "layer-envelope-v1.json"
        )
        schema = json.loads(schema_path.read_text())

        adapter = L4StubAdapter()
        inp = L4VirtualPlantInput(
            process_graph_unit_ops=["reaction_schema_test"],
            sensor_states=[_healthy_sensor("T-01", 35.0)],
        )
        envelope = adapter.process(inp)
        envelope_dict = json.loads(envelope.model_dump_json())

        jsonschema.validate(instance=envelope_dict, schema=schema)

    def test_multiple_unit_ops_all_stepped(self) -> None:
        """Three unit ops should all appear in FMU snapshots."""
        adapter = L4StubAdapter()
        inp = L4VirtualPlantInput(
            process_graph_unit_ops=["reaction_a", "crystallization_b", "drying_c"],
            sensor_states=[_healthy_sensor("T-01", 35.0)],
        )
        envelope = adapter.process(inp)

        out = envelope.output
        fmu_names = {s["fmu_name"] for s in out["fmu_states"]}
        assert "reaction_a" in fmu_names
        assert "crystallization_b" in fmu_names
        assert "drying_c" in fmu_names

    def test_confidence_in_allowed_range(self) -> None:
        """Confidence score must be in [0.5, 0.7] per spec."""
        adapter = L4StubAdapter()
        inp = L4VirtualPlantInput(
            process_graph_unit_ops=["reaction_01"],
            sensor_states=[_healthy_sensor("T-01", 35.0)],
        )
        envelope = adapter.process(inp)
        assert 0.5 <= envelope.confidence.score <= 0.7

    def test_back_edge_target_is_l2_5(self) -> None:
        """Back-edges must always target L2.5, never L3."""
        sensors = _load_stale_fixture()
        adapter = L4StubAdapter()
        inp = L4VirtualPlantInput(
            process_graph_unit_ops=["reaction_01"],
            sensor_states=sensors,
        )
        envelope = adapter.process(inp)
        for be in envelope.back_edges:
            assert be.target_layer == "L2.5", (
                f"Back-edge must target L2.5, got {be.target_layer}"
            )

    def test_no_copasi_or_tellurium_imports(self) -> None:
        """L4 modules must NOT import COPASI or Tellurium (those are L5)."""
        import importlib
        import sys

        # Import l4 modules
        for mod_name in [
            "zer0pa_health.layers.l4",
            "zer0pa_health.layers.l4.adapter",
            "zer0pa_health.layers.l4.fmu_bus",
            "zer0pa_health.layers.l4.ditto",
        ]:
            importlib.import_module(mod_name)

        # Verify forbidden tools are NOT imported
        assert "copasi" not in sys.modules, "COPASI must not be imported in L4 (belongs to L5)"
        assert "tellurium" not in sys.modules, "Tellurium must not be imported in L4 (belongs to L5)"
