"""L5 PK models — pure-Python analytic pharmacokinetics. No scipy required.

STUB ASSUMPTION: Molecular weight is set to 400 g/mol for all compounds when
converting cmax_ng_per_ml to cmax_unbound_uM. This is documented as a stub
default and must be replaced with real MW from the compound fixture before
any real simulation.

STUB ASSUMPTION: Oral bioavailability F = 1.0. Real adapters must supply
measured F from ADMET layer (L2).
"""

from __future__ import annotations

import math


def tmax_analytic(ke: float, ka: float) -> float:
    """Return theoretical tmax (h) for a 1-compartment first-order absorption model.

    tmax = ln(ka / ke) / (ka - ke)

    Defined for ka != ke and both > 0. Returns 0.0 for degenerate inputs.
    """
    if ke <= 0.0 or ka <= 0.0:
        return 0.0
    if abs(ka - ke) < 1e-12:
        # ka ≈ ke: limit form tmax = 1/ke
        return 1.0 / ke
    return math.log(ka / ke) / (ka - ke)


def one_compartment_pk(
    dose_mg: float,
    cl_l_per_h: float,
    vd_l: float,
    ka_per_h: float,
    fraction_unbound: float,
    t_hours: list[float],
    molecular_weight_g_per_mol: float = 400.0,
) -> dict:
    """Analytic 1-compartment first-order absorption PK model.

    Formula:
        C(t) = (Dose_mg_to_ng * F * ka) / (Vd_ml * (ka - ke)) * (exp(-ke*t) - exp(-ka*t))

    where:
        ke = CL / Vd  (h^-1)
        F  = 1.0     (oral bioavailability stub; replace with ADMET-derived value)
        Dose converted: dose_mg * 1e6 ng/mg; Vd converted: vd_l * 1000 mL/L → ng/mL output

    Parameters
    ----------
    dose_mg:
        Oral dose in milligrams.
    cl_l_per_h:
        Clearance in L/h.
    vd_l:
        Volume of distribution in litres.
    ka_per_h:
        First-order absorption rate constant (h^-1).
    fraction_unbound:
        Unbound fraction (fu); 0 < fu <= 1.
    t_hours:
        List of time points in hours.
    molecular_weight_g_per_mol:
        Molecular weight in g/mol. STUB DEFAULT = 400 g/mol. Must be replaced
        with real MW from compound fixture before mechanism escalation.

    Returns
    -------
    dict with keys:
        c_total_ng_per_ml:      list[float], total plasma concentration (ng/mL)
        c_unbound_ng_per_ml:    list[float], unbound concentration (ng/mL)
        cmax_ng_per_ml:         float, peak total plasma concentration (ng/mL)
        tmax_h:                 float, time of peak concentration (h)
        auc_0_inf_ng_h_per_ml:  float, AUC 0→∞ by trapezoidal + terminal phase (ng·h/mL)
        cmax_unbound_uM:        float, peak unbound concentration in micromolar
        half_life_h:            float, elimination half-life (h)
    """
    if not t_hours:
        raise ValueError("t_hours must be non-empty")

    F = 1.0  # STUB: bioavailability assumed 1.0

    ke = cl_l_per_h / vd_l  # elimination rate constant (h^-1)
    half_life_h = math.log(2.0) / ke

    # Convert dose to ng (1 mg = 1e6 ng); Vd to mL (1 L = 1000 mL)
    dose_ng = dose_mg * 1e6
    vd_ml = vd_l * 1000.0

    # Handle ka == ke edge case (Bateman function singularity)
    ka_eq_ke = abs(ka_per_h - ke) < 1e-9

    c_total: list[float] = []
    for t in t_hours:
        if t < 0.0:
            raise ValueError(f"Negative time point: {t}")
        if t == 0.0:
            c_total.append(0.0)
            continue
        if ka_eq_ke:
            # Limit form: C(t) = (Dose * F * ke / Vd) * t * exp(-ke*t)
            c = (dose_ng * F * ke / vd_ml) * t * math.exp(-ke * t)
        else:
            c = (
                (dose_ng * F * ka_per_h)
                / (vd_ml * (ka_per_h - ke))
                * (math.exp(-ke * t) - math.exp(-ka_per_h * t))
            )
        c_total.append(max(0.0, c))

    c_unbound = [c * fraction_unbound for c in c_total]

    cmax_ng_per_ml = max(c_total) if c_total else 0.0
    tmax_h_val = tmax_analytic(ke, ka_per_h)
    # Clamp tmax to the observation window; note tmax from analytic formula may
    # exceed the grid if grid doesn't cover the full absorption phase.

    # AUC 0→∞: trapezoidal up to last time point, then terminal phase
    auc_trap = 0.0
    for i in range(1, len(t_hours)):
        dt = t_hours[i] - t_hours[i - 1]
        auc_trap += 0.5 * (c_total[i - 1] + c_total[i]) * dt
    # Terminal phase tail: C(t_last) / ke (assuming elimination phase dominates at last point)
    c_last = c_total[-1] if c_total else 0.0
    auc_tail = c_last / ke if ke > 0 else 0.0
    auc_0_inf = auc_trap + auc_tail

    # cmax_unbound_uM: ng/mL → µM
    # ng/mL = µg/L; divide by MW (g/mol = mg/mmol) to get µmol/L = µM
    # cmax_unbound_ng_per_ml / (MW_g_per_mol) = µM  (since 1 ng/mL = 1 µg/L = 1/MW µmol/L)
    cmax_unbound_ng = cmax_ng_per_ml * fraction_unbound
    cmax_unbound_uM = cmax_unbound_ng / molecular_weight_g_per_mol  # µM

    return {
        "c_total_ng_per_ml": c_total,
        "c_unbound_ng_per_ml": c_unbound,
        "cmax_ng_per_ml": cmax_ng_per_ml,
        "tmax_h": tmax_h_val,
        "auc_0_inf_ng_h_per_ml": auc_0_inf,
        "cmax_unbound_uM": cmax_unbound_uM,
        "half_life_h": half_life_h,
    }
