"""Eclipse Ditto digital twin stub — PAT sensor state registry.

Real implementation:
    Eclipse Ditto is an open-source IoT digital twin framework (Eclipse Foundation).
    It manages a mirrored representation of each PAT instrument as a 'Thing' with
    live state synchronised via MQTT/HTTP. In production:
        - Each sensor is registered as a Ditto Thing (sensor_id = Thing ID).
        - State updates stream from the PAT instruments into Ditto via AMQP bridge.
        - The FMU bus reads sensor values from Ditto on every step, closing the
          virtual-plant feedback loop.
        - Fault detection drives maintenance work orders and L4 back-edges to L2.5.

Stub implementation:
    - In-memory registry keyed by sensor_id.
    - inject_fault() simulates sensor failure modes for falsifier testing.
    - No network I/O; no Eclipse Ditto SDK imports.
"""

from __future__ import annotations

import math
from typing import Literal

from zer0pa_biomolecular_explorer.contracts.l4 import L4SensorState


class EclipseDittoStub:
    """Stub Eclipse Ditto digital twin for PAT sensor state management.

    Simulates the sensor registry without network I/O or the Ditto SDK.
    inject_fault() enables testing of the L4 sensor-failure falsifier.
    """

    def __init__(self) -> None:
        self._sensors: dict[str, L4SensorState] = {}

    def add_sensor(self, state: L4SensorState) -> None:
        """Register or overwrite a sensor's current state."""
        self._sensors[state.sensor_id] = state

    def read_sensors(self) -> list[L4SensorState]:
        """Return current state for all registered sensors."""
        return list(self._sensors.values())

    def inject_fault(
        self,
        sensor_id: str,
        fault_kind: Literal["stale", "out_of_range", "nonfinite"],
    ) -> None:
        """Simulate a sensor fault for falsifier testing.

        Modifies the named sensor in-place:
            - "stale"       : sets value = None, in_range = False
            - "out_of_range": sets value to a value outside expected_range (or 9e9)
            - "nonfinite"   : sets value = float('nan'), in_range = False

        Raises KeyError if sensor_id is not registered.
        """
        sensor = self._sensors[sensor_id]

        if fault_kind == "stale":
            self._sensors[sensor_id] = L4SensorState(
                sensor_id=sensor.sensor_id,
                sensor_class=sensor.sensor_class,
                value=None,
                unit=sensor.unit,
                timestamp_utc=sensor.timestamp_utc,
                in_range=False,
                expected_range=sensor.expected_range,
            )
        elif fault_kind == "out_of_range":
            # Put value way outside expected_range
            out_val: float
            if sensor.expected_range is not None:
                low, high = sensor.expected_range
                out_val = high + abs(high - low) * 10.0 + 1.0
            else:
                out_val = 9e9
            self._sensors[sensor_id] = L4SensorState(
                sensor_id=sensor.sensor_id,
                sensor_class=sensor.sensor_class,
                value=out_val,
                unit=sensor.unit,
                timestamp_utc=sensor.timestamp_utc,
                in_range=False,
                expected_range=sensor.expected_range,
            )
        elif fault_kind == "nonfinite":
            self._sensors[sensor_id] = L4SensorState(
                sensor_id=sensor.sensor_id,
                sensor_class=sensor.sensor_class,
                value=float("nan"),
                unit=sensor.unit,
                timestamp_utc=sensor.timestamp_utc,
                in_range=False,
                expected_range=sensor.expected_range,
            )
        else:
            raise ValueError(f"Unknown fault_kind: {fault_kind!r}")
