"""P1.Generate toy adapter.

Research use only. Not for diagnosis, treatment, cure claims, prescribing,
clinical deployment, regulatory compliance, or drug-safety certification.

Same envelope shape and falsifier-class set as P1GenerateStubAdapter but uses
a rotated SMILES pool (shifted by 1) to simulate a second model/source.
"""

from __future__ import annotations

from zer0pa_biomolecular_explorer.envelope import Backend, ToolAdapter
from zer0pa_biomolecular_explorer.pathway1.layers.generate.adapter import (
    P1GenerateStubAdapter,
    _SMILES_POOL,
)

_TOY_SMILES_POOL: tuple[str, ...] = _SMILES_POOL[1:] + _SMILES_POOL[:1]

_TOY_NAME = "p1-generate-toy"
_TOY_VERSION = "0.1.0"
_TOY_ENGINE = "stub_toy_smiles_pool"


class P1GenerateToyAdapter(P1GenerateStubAdapter):
    """Toy adapter: rotated SMILES pool, same envelope shape and falsifier-class set."""

    NAME = _TOY_NAME
    VERSION = _TOY_VERSION
    ENGINE = _TOY_ENGINE

    def __init__(self, *, force_ip_drift_fail: bool = False) -> None:
        super().__init__(force_ip_drift_fail=force_ip_drift_fail)
        self._tool_adapter = ToolAdapter(
            name=self.NAME,
            version=self.VERSION,
            backend=Backend.STUB,
            engine=self.ENGINE,
        )

    def _pool(self) -> tuple[str, ...]:
        return _TOY_SMILES_POOL
