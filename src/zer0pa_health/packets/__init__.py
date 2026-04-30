"""Cardiac evidence packet generator (PRD section 7).

The packet is the engine's deliverable for the cardiac wedge. It is what
PubMed plus a competent reader cannot produce: a rerunnable source manifest,
machine-valid graph, explicit contradiction table, falsifier ledger, local
morphology linkage, audit trail, and next-experiment backedges.
"""

from zer0pa_health.packets.schema import (
    CardiacEvidencePacket,
    PacketChannelPanel,
    PacketClaim,
    PacketContradiction,
    PacketEngineValueAdd,
    PacketMorphologyBridge,
    PacketCompound,
    PacketVerdict,
)
from zer0pa_health.packets.assembler import CardiacPacketAssembler
from zer0pa_health.packets.morphology_gate import morphology_gate, MorphologyResult
from zer0pa_health.packets.morphology_fixtures import (
    MorphologyFixtureError,
    fixture_provenance_summary,
    load_morphology_fixture,
)
from zer0pa_health.packets.pubmed_baseline import (
    BaselineHarness,
    BaselineScorecard,
    EngineScorecard,
    score_packet,
    score_baseline_for_compound,
)

__all__ = [
    "CardiacEvidencePacket",
    "PacketChannelPanel",
    "PacketClaim",
    "PacketContradiction",
    "PacketEngineValueAdd",
    "PacketMorphologyBridge",
    "PacketCompound",
    "PacketVerdict",
    "CardiacPacketAssembler",
    "morphology_gate",
    "MorphologyResult",
    "BaselineHarness",
    "BaselineScorecard",
    "EngineScorecard",
    "score_packet",
    "score_baseline_for_compound",
    "MorphologyFixtureError",
    "load_morphology_fixture",
    "fixture_provenance_summary",
]
