# Negative fixtures

These fixtures are designed to deliberately trigger named falsifiers in the
pipeline's falsification wave (PRD section 11). Each file is named for the
falsifier class it targets. Tests in `tests/falsification/` load them.

| File | Trigger |
|---|---|
| `invalid_smiles.json` | invalid_molecular_input |
| `missing_rxnsmiles.json` | missing_rxnsmiles_atommap |
| `missing_atommap.json` | missing_rxnsmiles_atommap (mapping required, absent) |
| `mass_balance_break.json` | mass_balance_failure |
| `l4_sensor_stale.json` | l4_sensor_failure |
| `sbml_no_species.json` | sbml_schema_failure |
| `herg_only_panel.json` | hERG_only_overreach |
| `clinical_overclaim_text.json` | clinical_overclaim |
| `stub_laundering.json` | stub_laundering |
| `silent_falsifier_loss.json` | silent_falsifier_loss / missing_falsifier_ref |
| `nan_ecg_input.json` | nonfinite_input / morphology_non_preservation |
| `plug_regression.json` | plug_regression |

Research use only. Not for diagnosis, treatment, cure claims, prescribing,
clinical deployment, regulatory compliance, or drug-safety certification.
