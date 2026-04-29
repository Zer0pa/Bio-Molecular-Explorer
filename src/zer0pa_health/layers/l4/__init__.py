"""L4 manufacturing digital twin layer — stub adapters and co-simulation bus.

Research use only. Not for diagnosis, treatment, cure claims, prescribing,
clinical deployment, regulatory compliance, or drug-safety certification.

Toolchain (real, Runpod):
    PharmaPy        — pharma process models (reactors, crystallizers, filtration)
    OpenModelica    — Modelica equipment simulation → FMU export
    FMI/FMU         — co-simulation standard (FMI 2.0 / 3.0)
    Eclipse Ditto   — IoT digital twin for PAT sensor streams
    OpenFOAM        — CFD for mixing vessels and heat transfer

Toolchain (this stub):
    FMUStubBus      — in-process toy-dynamics FMI bus
    EclipseDittoStub — in-memory PAT sensor registry
    L4StubAdapter   — wires bus + ditto, runs falsifiers, emits LayerEnvelope

CORRECTION (Brief #2): COPASI/Tellurium are L5 (PKPD/QSP), NOT L4.
"""

from zer0pa_health.layers.l4.adapter import L4StubAdapter
from zer0pa_health.layers.l4.ditto import EclipseDittoStub
from zer0pa_health.layers.l4.fmu_bus import FMUStubBus

__all__ = ["L4StubAdapter", "FMUStubBus", "EclipseDittoStub"]
