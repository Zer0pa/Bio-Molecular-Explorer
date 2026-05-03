"""Cloud-lab adapter package (PRD section 9).

Exports:
    CloudLabAdapter   — Protocol (structural typing) defining the vendor-neutral interface.
    StrateosStub      — Strateos dry-run stub.
    EmeraldStub       — Emerald Cloud Lab dry-run stub.
    ArctorisStub      — Arctoris dry-run stub.
    BlockedClassError — Raised when protocol contains a PRD-blocked class.
    ApprovalTokenRequiredError — Raised when submit called without valid token.
    BudgetExceededError        — Raised when cost exceeds max_budget_usd.
    NetworkSubmitDisabledError — Raised when allow_network_submit=False.
    default_config    — Returns PRD-default CloudLabConfig (all interlocks on).
"""

from zer0pa_biomolecular_explorer.cloud_lab.arctoris import ArctorisStub
from zer0pa_biomolecular_explorer.cloud_lab.config import CloudLabConfig, default_config
from zer0pa_biomolecular_explorer.cloud_lab.emerald import EmeraldStub
from zer0pa_biomolecular_explorer.cloud_lab.interlocks import (
    ApprovalTokenRequiredError,
    BlockedClassError,
    BudgetExceededError,
    NetworkSubmitDisabledError,
)
from zer0pa_biomolecular_explorer.cloud_lab.protocol import CloudLabAdapter
from zer0pa_biomolecular_explorer.cloud_lab.strateos import StrateosStub

__all__ = [
    "CloudLabAdapter",
    "StrateosStub",
    "EmeraldStub",
    "ArctorisStub",
    "BlockedClassError",
    "ApprovalTokenRequiredError",
    "BudgetExceededError",
    "NetworkSubmitDisabledError",
    "CloudLabConfig",
    "default_config",
]
