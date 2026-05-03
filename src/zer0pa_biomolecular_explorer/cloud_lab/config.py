"""CloudLabConfig — Pydantic v2 configuration model (PRD section 9).

Default: disabled, dry_run, all interlocks on, no real network submission.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CloudLabConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    mode: Literal["dry_run", "real"] = "dry_run"
    allow_network_submit: bool = False
    max_budget_usd: float = Field(default=0.0, ge=0)
    require_user_approval_token: bool = True
    vendor: Literal["strateos", "emerald", "arctoris", "none"] = "none"
    blocked_classes: list[str] = Field(
        default_factory=lambda: [
            "clinical",
            "human_diagnosis",
            "treatment",
            "prescribing",
            "regulated_safety_certification",
            "PHI",
            "controlled_or_hazardous_material",
            "autonomous_wet_lab_execution",
        ]
    )


def default_config() -> CloudLabConfig:
    """Return the PRD-default cloud-lab configuration.

    All interlocks on:
      - enabled=False
      - mode="dry_run"
      - allow_network_submit=False
      - max_budget_usd=0.0
      - require_user_approval_token=True
      - vendor="none"
      - blocked_classes=PRD defaults
    """
    return CloudLabConfig()
