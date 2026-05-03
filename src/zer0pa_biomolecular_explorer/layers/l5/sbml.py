"""L5 SBML stub builder.

Builds minimal SBML-compatible packets as L5SBMLPacket objects.
Full SBML XML is NOT generated here (stub); a real adapter would call
libSBML / Tellurium / COPASI to produce valid XML.

The roundtrip check serialises the packet to canonical JSON, re-parses,
and verifies structural equality (same species, reactions, parameters).

RESEARCH USE ONLY — not for clinical deployment, diagnosis, or prescribing.
"""

from __future__ import annotations

import json

from zer0pa_biomolecular_explorer.contracts.l5 import L5SBMLPacket
from zer0pa_biomolecular_explorer.hashing import canonical_json, sha256_hex


def build_minimal_sbml_packet(
    model_kind: str,
    parameters: dict[str, float],
) -> L5SBMLPacket:
    """Build a minimal SBML-compatible packet with 2 species and 1 reaction.

    The packet satisfies the SBML schema failure falsifier requirements:
      - >= 1 species
      - >= 1 reaction
      - parameters from input

    Species:
      - "drug":             the parent compound (initial amount = 1.0)
      - "drug_metabolite":  the primary metabolite (initial amount = 0.0)

    Reactions:
      - "metabolism": drug → drug_metabolite (first-order, rate = ke * drug)

    Parameters:
      All key-value pairs from the `parameters` argument are included.
      The ke parameter is derived from cl/vd if both present.

    Parameters
    ----------
    model_kind:
        String identifier for the PK model kind (e.g., "one_compartment").
    parameters:
        Numeric parameters to embed in the packet (e.g., {"cl": 10.0, "vd": 70.0}).

    Returns
    -------
    L5SBMLPacket with sbml_version="L3V2".
    """
    species = [
        {"id": "drug", "name": "Parent compound", "initialAmount": 1.0, "compartment": "central"},
        {"id": "drug_metabolite", "name": "Primary metabolite", "initialAmount": 0.0, "compartment": "central"},
    ]

    # Derive ke for the reaction rate expression
    cl = parameters.get("cl", parameters.get("cl_l_per_h", 10.0))
    vd = parameters.get("vd", parameters.get("vd_l", 70.0))
    ke = cl / vd if vd > 0 else 0.0

    reactions = [
        {
            "id": "metabolism",
            "name": f"{model_kind}_drug_elimination",
            "reactants": "drug",
            "products": "drug_metabolite",
            "kineticLaw": f"ke * drug",
            "notes": f"First-order elimination; ke={ke:.6f} h^-1 (stub)",
        }
    ]

    # Merge supplied parameters with derived ke
    merged_params: dict[str, float] = {"ke": round(ke, 8)}
    merged_params.update({k: float(v) for k, v in parameters.items()})

    # Compute a content-addressed hash of the XML stub
    xml_stub_content = canonical_json({
        "sbml_version": "L3V2",
        "model_kind": model_kind,
        "species": species,
        "reactions": reactions,
        "parameters": merged_params,
    })
    sbml_xml_hash = sha256_hex(xml_stub_content)

    return L5SBMLPacket(
        sbml_version="L3V2",
        species=species,
        reactions=reactions,
        parameters=merged_params,
        sbml_xml_hash=sbml_xml_hash,
    )


def sbml_roundtrip_ok(packet: L5SBMLPacket) -> bool:
    """Stub roundtrip check: re-serialise and re-parse the packet, compare equality.

    The roundtrip exercises:
      1. Pydantic model_dump() → canonical JSON
      2. json.loads() → dict
      3. L5SBMLPacket(**dict) reconstruction
      4. model_dump() comparison (structural equality)

    Returns True if both model_dump() representations are identical.
    """
    try:
        original_dump = packet.model_dump()
        serialised = json.dumps(original_dump, sort_keys=True, separators=(",", ":"))
        parsed = json.loads(serialised)
        reconstructed = L5SBMLPacket(**parsed)
        return reconstructed.model_dump() == original_dump
    except Exception:
        return False
