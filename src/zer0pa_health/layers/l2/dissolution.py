"""L2 dissolution PINN stub — Weibull-shaped dissolution profiles.

Research use only. Not for diagnosis, treatment, cure claims, prescribing,
clinical deployment, regulatory compliance, or drug-safety certification.

STUB-GRADE — This module returns deterministic Weibull-shaped dissolution
profiles based on formulation type. It is a placeholder for the real DeepXDE
PDE-solve adapter that runs on Runpod GPU.

Real adapter swap path
-----------------------
When the Runpod GPU container (deepxde_runpod_adapter.py) is ready:
1. Instantiate L2DeepXDERunpodAdapter (see parked_runpod.py for the parked
   skeleton).
2. Replace calls to dissolution_pinn_stub() with calls to the Runpod adapter.
3. The envelope contract and L2DissolutionOutput shape are frozen — only the
   pinn_basis field and the actual fractional values change.
4. The swap is controlled by a backend flag (PRD section 2 plug-replaceability
   invariant); no downstream code changes.

Weibull model (stub-grade documentation)
-----------------------------------------
f(t) = 1 - exp(-(t / scale)^shape)

Parameters chosen to approximate typical in-vitro dissolution profiles for
each formulation class. These are NOT calibrated to any specific compound or
excipient system. They exist only to provide plausible, monotone, bounded
values for end-to-end plumbing tests.

Formulation    | scale (min) | shape | Rationale
IR_tablet      | 30          | 0.8   | Typical fast dissolution, slight lag
ER_tablet      | 120         | 0.6   | Extended release, slower and stretched
capsule        | 45          | 0.7   | Slightly slower than IR tablet
solution       | 5           | 1.2   | Near-immediate dissolution
suspension     | 40          | 0.7   | Similar to capsule, particle-size driven

dose_mg is accepted but not currently used in the stub — real DeepXDE PDE
solve would use concentration-dependent dissolution kinetics where dose affects
the driving force. Retained in the interface so the contract is forward-compatible.
"""

from __future__ import annotations

import math

from zer0pa_health.contracts.l2 import L2DissolutionInput, L2DissolutionOutput


# ---------------------------------------------------------------------------
# Weibull dissolution model parameters by formulation
# ---------------------------------------------------------------------------

_WEIBULL_PARAMS: dict[str, tuple[float, float]] = {
    # (scale_min, shape)
    "IR_tablet":   (30.0,  0.8),
    "ER_tablet":   (120.0, 0.6),
    "capsule":     (45.0,  0.7),
    "solution":    (5.0,   1.2),
    "suspension":  (40.0,  0.7),
}

# Evaluation time points for the contract output fields
_T_30:  float = 30.0
_T_60:  float = 60.0
_T_120: float = 120.0


def _weibull_cdf(t: float, scale: float, shape: float) -> float:
    """Weibull cumulative distribution function used as dissolution model.

    f(t) = 1 - exp(-(t / scale)^shape)

    Returns value in [0.0, 1.0]; clamps numerically to that range.
    """
    if t <= 0.0:
        return 0.0
    val = 1.0 - math.exp(-((t / scale) ** shape))
    return max(0.0, min(1.0, val))


def dissolution_pinn_stub(input: L2DissolutionInput) -> L2DissolutionOutput:
    """Return a deterministic Weibull-shaped dissolution profile.

    STUB-GRADE: pinn_basis='DeepXDE_stub'. The real DeepXDE PDE solve is a
    Runpod-deferred adapter (see parked_runpod.py). The swap happens by
    replacing this function call with L2DeepXDERunpodAdapter.compute_dissolution()
    behind the same L2DissolutionInput / L2DissolutionOutput contract.

    Parameters
    ----------
    input : L2DissolutionInput
        Contains molecule SMILES, formulation type, and dose_mg.

    Returns
    -------
    L2DissolutionOutput
        Dissolution fractions at 30, 60, and 120 minutes. All values are in
        [0, 1] and are monotone increasing (guaranteed by Weibull CDF).
    """
    formulation = input.formulation
    scale, shape = _WEIBULL_PARAMS[formulation]

    f30 = _weibull_cdf(_T_30, scale, shape)
    f60 = _weibull_cdf(_T_60, scale, shape)
    f120 = _weibull_cdf(_T_120, scale, shape)

    return L2DissolutionOutput(
        smiles=input.molecule.smiles,
        formulation=formulation,
        dose_mg=input.dose_mg,
        pinn_basis="DeepXDE_stub",
        fraction_dissolved_at_30min=f30,
        fraction_dissolved_at_60min=f60,
        fraction_dissolved_at_120min=f120,
    )
