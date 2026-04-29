"""Zer0pa Health falsification-engine pipeline.

Research use only. Not for diagnosis, treatment, cure claims, prescribing,
clinical deployment, regulatory compliance, or drug-safety certification.
"""

from zer0pa_health.boundary import RESEARCH_BOUNDARY
from zer0pa_health.envelope import LayerEnvelope, EnvelopeFalsifier, EnvelopeAudit, EnvelopeConfidence

__version__ = "0.1.0"

__all__ = [
    "RESEARCH_BOUNDARY",
    "LayerEnvelope",
    "EnvelopeFalsifier",
    "EnvelopeAudit",
    "EnvelopeConfidence",
    "__version__",
]
