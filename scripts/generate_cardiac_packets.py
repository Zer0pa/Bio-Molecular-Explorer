"""Generate the three canned cardiac evidence packets to disk.

Output: packets/cardiac_evidence_packet_v0_1__<compound>.json (one per compound).

Research use only. Not for diagnosis, treatment, cure claims, prescribing,
clinical deployment, regulatory compliance, or drug-safety certification.
"""

from __future__ import annotations

import json
from pathlib import Path

from zer0pa_health.packets import (
    BaselineHarness,
    CardiacPacketAssembler,
)
from zer0pa_health.packets.assembler import AssemblerInputs


REPO_ROOT = Path(__file__).resolve().parents[1]
FIX = REPO_ROOT / "fixtures" / "compounds"
OUT = REPO_ROOT / "packets"


# Canonical canned Cmax_unbound for each seed compound — research-only stub values.
# These reproduce the multi-current shape the cardiac packet is supposed to demonstrate.
_CMAX_UNBOUND_uM = {
    "dofetilide": 0.001,
    "verapamil": 0.05,
    "ranolazine": 2.0,
}

# Canned QT-error arrays (ms) — small, deterministic, research-only morphology stubs.
_QT_ERRORS_MS = {
    "dofetilide": [1.2, 1.5, 2.1, 2.4, 1.9, 2.0, 1.7, 2.3],
    "verapamil": [0.9, 1.1, 1.3, 1.5, 1.0, 1.2, 1.4, 1.1],
    "ranolazine": [1.6, 2.0, 1.8, 2.2, 2.5, 1.9, 2.1, 2.3],
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    asm = CardiacPacketAssembler()
    packets = []
    for compound in ("dofetilide", "verapamil", "ranolazine"):
        inputs = AssemblerInputs(
            compound_fixture_path=FIX / f"{compound}.json",
            cmax_unbound_uM=_CMAX_UNBOUND_uM[compound],
            morphology_errors_ms={"QT": _QT_ERRORS_MS[compound]},
        )
        packet, diag = asm.assemble(inputs)
        out_path = OUT / f"cardiac_evidence_packet_v0_1__{compound}.json"
        out_path.write_text(packet.model_dump_json(indent=2), encoding="utf-8")
        packets.append((packet, diag, out_path))
        print(f"OK {compound}: verdict={packet.verdict.value}, diagnostics={diag}")

    rows = BaselineHarness().evaluate([p for p, _d, _p in packets])
    print()
    print("PUBMED-BASELINE BENCHMARK (research only):")
    print(f"{'compound':<15} {'engine':>8} {'baseline':>10} {'lift':>8} {'pass?':>8}")
    for (engine, baseline, passed), (packet, _diag, _out) in zip(rows, packets):
        print(
            f"{packet.compound.name:<15} {engine.total:>8.2f} {baseline.total:>10.2f} "
            f"{engine.total - baseline.total:>8.2f} {str(passed):>8}"
        )

    # Write a small summary
    summary = {
        "research_boundary": "Research use only. Not for diagnosis, treatment, cure claims, prescribing, clinical deployment, regulatory compliance, or drug-safety certification.",
        "n_packets": len(packets),
        "verdicts": {p.compound.name: p.verdict.value for p, _d, _o in packets},
        "scores": {
            packet.compound.name: {
                "engine": engine.total,
                "baseline": baseline.total,
                "lift": engine.total - baseline.total,
                "passed_pubmed_gate": passed,
            }
            for (engine, baseline, passed), (packet, _d, _o) in zip(rows, packets)
        },
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\nWrote", OUT / "summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
