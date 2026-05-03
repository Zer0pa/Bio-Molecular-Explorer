"""P1.Structure toy adapter — same interface as P1StructureStubAdapter,
different deterministic seed values for plug-swap / shape-match testing.

backend=stub, structure_source_tag="stub".
Same falsifier-class set as P1StructureStubAdapter.
Same envelope shape.
"""

from __future__ import annotations

from zer0pa_biomolecular_explorer.envelope import (
    Backend,
    LayerEnvelope,
    ToolAdapter,
)
from zer0pa_biomolecular_explorer.ids import run_id as new_run_id
from zer0pa_biomolecular_explorer.pathway1.contracts.p1_structure import P1StructureInput
from zer0pa_biomolecular_explorer.pathway1.layers.structure.adapter import (
    _ADAPTER_VERSION,
    _build_dossier,
    _build_envelope,
    _run_falsifiers,
)

_TOY_ADAPTER_NAME = "p1-structure-toy"
_TOY_ENGINE = "stub_canned_toy"
_TOY_SEED_PREFIX = "p1structure_toy"


class P1StructureToyAdapter:
    """P1.Structure toy adapter.

    Same interface as P1StructureStubAdapter; uses a different seed prefix
    ("p1structure_toy") so that same-input → different deterministic values,
    but the output keys and falsifier classes are identical.
    backend=stub, structure_source_tag="stub".
    """

    NAME = _TOY_ADAPTER_NAME
    VERSION = _ADAPTER_VERSION
    ENGINE = _TOY_ENGINE

    def __init__(self) -> None:
        self._tool_adapter = ToolAdapter(
            name=self.NAME,
            version=self.VERSION,
            backend=Backend.STUB,
            engine=self.ENGINE,
        )

    def process(
        self,
        input: P1StructureInput,
        *,
        run_id: str | None = None,
    ) -> LayerEnvelope:
        rid = run_id or new_run_id()
        dossier = _build_dossier(
            input,
            rid,
            seed_prefix=_TOY_SEED_PREFIX,
            structure_source_tag="stub",
            uniprot_af_id=None,
            openfold3_run_id=None,  # auto-filled to "stub:run:{rid}"
        )
        falsifier_items = _run_falsifiers(
            dossier,
            backend=Backend.STUB.value,
            mechanism_escalation=False,
            structure_source="stub",
        )
        return _build_envelope(
            run_id=rid,
            dossier=dossier,
            falsifier_items=falsifier_items,
            tool_adapter=self._tool_adapter,
            confidence_score=0.6,
            confidence_basis=["stub_canned_structure"],
            input_obj=input.model_dump(mode="json"),
            output_obj=dossier.model_dump(mode="json"),
        )
