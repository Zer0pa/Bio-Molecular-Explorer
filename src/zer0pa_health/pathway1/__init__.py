"""Pathway 1 — R&D / Drug Discovery front-end.

Sub-layers (semantic naming, not numeric to avoid collision with the existing pipeline):
  P1.Target    — target identification (genomic + literature + structural evidence)
  P1.Structure — protein structure prediction + binding pocket
  P1.Generate  — generative molecule design
  P1.Screen    — in silico screening (affinity + ADMET + selectivity + synthesizability)
  P1.Optimize  — hit-to-lead refinement (RL / Bayesian optimization)
  P1.Handoff   — CRO-ready candidate dossier; bridges into the existing cardiac wedge

Research use only. Not for diagnosis, treatment, cure claims, prescribing,
clinical deployment, regulatory compliance, or drug-safety certification.
"""

from zer0pa_health.pathway1 import contracts, layers

__all__ = ["contracts", "layers"]
