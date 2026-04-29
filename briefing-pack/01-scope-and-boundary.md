# Scope and Boundary

## What this portfolio is

Research infrastructure that turns deterministic bioelectric signal phenotypes (ECG, extracellular neurophysiology) into auditable mechanism graphs, evidence syntheses, and falsification plans for ion-channel disease and drug-safety research. The intended consumer is a research scientist or future research agent — not a clinician, regulator, or patient.

The unique angle: combine deterministic signal lineage from the existing ECG / extracellular-electrophysiology proof base with cross-evidence biological reasoning from life-science research-agent tooling (GPT-Rosalind / OpenAI Life Sciences Research Plugin pattern). Either layer alone is generic; the bridge is the point.

## What this portfolio is not

It is not, and during this phase will not become, any of the following:

- A diagnostic system, screen, or interpretive aid for any condition.
- A treatment recommender, prescribing aid, or therapy selector.
- A cure-claim engine for any disease.
- A patient-facing decision-support product.
- A clinical-decision-support (CDS) device, in any FDA tier.
- A QT / proarrhythmic safety certifier or replacement for E14 / S7B compliance work.
- A regulatory submission artefact in any jurisdiction.
- A drug-development or clinical-trial enrichment tool with claims of efficacy.
- A live triage or monitoring product.

## What every output must carry

Every artifact (README, schema, dataset card, mechanism node, evidence packet, falsification entry) carries this boundary verbatim:

> Research use only. Not for diagnosis, treatment, cure claims, prescribing, clinical deployment, regulatory compliance, or drug-safety certification.

## Operating posture

- **Falsification first.** A claim without a stated disconfirming observation is not a claim.
- **Source separation.** Every mechanism edge must mark whether it comes from regulatory science, peer-reviewed literature, public dataset metadata, local proof artifact, or inference. "Inference" is allowed; "unmarked" is not.
- **No clinical entity.** The portfolio does not have, sign, or imply medical authority for any output.
- **No data exfiltration.** No patient identifiers, no credentialed clinical data, no restricted regulatory or risk lists republished. Cite-only where licenses constrain redistribution (e.g., CredibleMeds taxonomy framing).
- **No bulk local data.** Public datasets are referenced via manifest and metadata; bulk artifacts go to private off-machine storage when offload is needed.
- **Verbatim verdicts.** PASS / FAIL / INCONCLUSIVE / UNTESTED / BLOCKED / SUSPENDED / ACTIVE — never paraphrased — with a named authority.

## Active falsifiers (carried over from Brain Phase 8)

These four are live constraints. If an output triggers any of them, the output is invalid and must be revised:

1. **Codec-as-mechanism.** Compression ratio, event ratio, SNR, RMSE, PRD, replay hash — none of these alone is biological mechanism evidence. They support phenotype *integrity*. They do not prove disease mechanism.
2. **Noise-brittle phenotype.** A rhythm or morphology claim that does not survive calibrated noise (NSTDB-style) must be downgraded.
3. **hERG-only overreach.** A torsade-risk story that ranks hERG / KCNH2 alone without multi-current or clinical-context caveats is rejected. CiPA framing is the minimum.
4. **Clinical overclaim.** Any output that reads as diagnosis, treatment, cure, prescribing, clinical deployment, regulatory compliance, or drug-safety certification — stop the output and revise.

## Failure-mode phrasings (auto-stop)

In addition to the four falsifiers, any of these phrasing patterns in an output should auto-stop and revise:

- Diagnostic — "indicates X disease", "suggests Y diagnosis".
- Treatment — "should be treated with", "consider drug X for".
- Cure — "eliminates", "cures", "reverses".
- Prescribing — "dose", "regimen", "alternative agent".
- Clinical deployment — "for use in clinic", "device-grade", "monitoring".
- Regulatory — "FDA-cleared", "compliant for certification".
- Drug-safety certification — "safe to use", "non-proarrhythmic", "low-risk drug".

The disclaimer block does not insulate against these phrasings. A reader who skims past the disclaimer reads the recommendation. The reviewer's job includes pressure-testing the *prose patterns*, not just the disclaimer presence.
