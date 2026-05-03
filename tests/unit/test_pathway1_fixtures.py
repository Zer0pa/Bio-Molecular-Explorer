"""Pathway 1 fixture validation tests.

Tests:
1. All 6 target fixtures validate against schemas/fixtures/pathway1/target.schema.json
2. All 12 hit fixtures validate against schemas/fixtures/pathway1/hit.schema.json
3. All negative fixtures load as valid JSON (structural check)
4. KG pathway1_seed.jsonl loads on top of cardiac_seed.jsonl in a temp KGStore
5. KGValidator passes on the combined KG (no dangling refs, K1/K3 hold)
6. Boundary string verbatim in every fixture file
7. Hit IDs match pattern P1-HIT-<GENE>-<NNN>
8. Target IDs match uniprot: pattern
9. Negative fixtures each carry target_falsifier field
10. KG seed produces expected node/edge counts

Research use only. Not for diagnosis, treatment, cure claims, prescribing,
clinical deployment, regulatory compliance, or drug-safety certification.
"""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

import pytest

try:
    import jsonschema
    from jsonschema import Draft202012Validator
    _JSONSCHEMA_AVAILABLE = True
except ImportError:
    _JSONSCHEMA_AVAILABLE = False

from zer0pa_biomolecular_explorer.kg import KGStore, KGValidator
from zer0pa_biomolecular_explorer.boundary import RESEARCH_BOUNDARY

# ──────────────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_P1 = REPO_ROOT / "fixtures" / "pathway1"
TARGETS_DIR = FIXTURES_P1 / "targets"
HITS_DIR = FIXTURES_P1 / "hits"
NEGATIVE_DIR = FIXTURES_P1 / "negative"
SCHEMAS_P1 = REPO_ROOT / "schemas" / "fixtures" / "pathway1"
TARGET_SCHEMA_PATH = SCHEMAS_P1 / "target.schema.json"
HIT_SCHEMA_PATH = SCHEMAS_P1 / "hit.schema.json"
KG_CARDIAC_SEED = REPO_ROOT / "kg" / "cardiac_seed.jsonl"
KG_PATHWAY1_SEED = REPO_ROOT / "kg" / "pathway1_seed.jsonl"

_EXPECTED_TARGET_FILES = {
    "KCNH2.json", "SCN5A.json", "KCNQ1.json", "CACNA1C.json", "EGFR.json", "BACE1.json"
}
_CARDIAC_GENES = {"KCNH2", "SCN5A", "KCNQ1", "CACNA1C"}
_EXPECTED_CARDIAC_HIT_FILES = {
    "KCNH2_hit_001.json", "KCNH2_hit_002.json", "KCNH2_hit_003.json",
    "SCN5A_hit_001.json", "SCN5A_hit_002.json", "SCN5A_hit_003.json",
    "KCNQ1_hit_001.json", "KCNQ1_hit_002.json", "KCNQ1_hit_003.json",
    "CACNA1C_hit_001.json", "CACNA1C_hit_002.json", "CACNA1C_hit_003.json",
}


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _load_schema(schema_path: Path) -> dict:
    with schema_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _validate_against_schema(instance: dict, schema: dict) -> list[str]:
    """Return list of validation error messages (empty = valid)."""
    if not _JSONSCHEMA_AVAILABLE:
        return []
    errors = []
    validator = Draft202012Validator(schema)
    for error in validator.iter_errors(instance):
        errors.append(f"{'.'.join(str(p) for p in error.absolute_path)}: {error.message}")
    return errors


# ──────────────────────────────────────────────────────────────────────
# Test: Schema files exist
# ──────────────────────────────────────────────────────────────────────

def test_target_schema_exists():
    assert TARGET_SCHEMA_PATH.is_file(), f"Missing: {TARGET_SCHEMA_PATH}"


def test_hit_schema_exists():
    assert HIT_SCHEMA_PATH.is_file(), f"Missing: {HIT_SCHEMA_PATH}"


# ──────────────────────────────────────────────────────────────────────
# Test: All expected target fixture files exist
# ──────────────────────────────────────────────────────────────────────

def test_all_target_fixtures_present():
    found = {f.name for f in TARGETS_DIR.glob("*.json")}
    missing = _EXPECTED_TARGET_FILES - found
    assert not missing, f"Missing target fixtures: {missing}"
    assert len(found) == 6, f"Expected 6 target fixtures, found {len(found)}"


def test_all_cardiac_hit_fixtures_present():
    found = {f.name for f in HITS_DIR.glob("*.json")}
    missing = _EXPECTED_CARDIAC_HIT_FILES - found
    assert not missing, f"Missing hit fixtures: {missing}"
    assert len(found) == 12, f"Expected 12 hit fixtures, found {len(found)}"


# ──────────────────────────────────────────────────────────────────────
# Test: Target fixtures validate against schema
# ──────────────────────────────────────────────────────────────────────

def test_target_fixtures_validate_against_schema():
    pytest.importorskip("jsonschema")
    schema = _load_schema(TARGET_SCHEMA_PATH)
    failures = []
    for fixture_file in sorted(TARGETS_DIR.glob("*.json")):
        instance = _load_json(fixture_file)
        errors = _validate_against_schema(instance, schema)
        if errors:
            failures.append(f"{fixture_file.name}: {errors[:2]}")
    assert not failures, f"Target schema validation failures:\n" + "\n".join(failures)


@pytest.mark.parametrize("fixture_name", sorted(_EXPECTED_TARGET_FILES))
def test_individual_target_fixture_validates(fixture_name):
    pytest.importorskip("jsonschema")
    schema = _load_schema(TARGET_SCHEMA_PATH)
    path = TARGETS_DIR / fixture_name
    assert path.is_file(), f"Missing fixture: {path}"
    instance = _load_json(path)
    errors = _validate_against_schema(instance, schema)
    assert not errors, f"{fixture_name} failed schema validation: {errors}"


# ──────────────────────────────────────────────────────────────────────
# Test: Hit fixtures validate against schema
# ──────────────────────────────────────────────────────────────────────

def test_hit_fixtures_validate_against_schema():
    pytest.importorskip("jsonschema")
    schema = _load_schema(HIT_SCHEMA_PATH)
    failures = []
    for fixture_file in sorted(HITS_DIR.glob("*.json")):
        instance = _load_json(fixture_file)
        errors = _validate_against_schema(instance, schema)
        if errors:
            failures.append(f"{fixture_file.name}: {errors[:2]}")
    assert not failures, f"Hit schema validation failures:\n" + "\n".join(failures)


@pytest.mark.parametrize("fixture_name", sorted(_EXPECTED_CARDIAC_HIT_FILES))
def test_individual_hit_fixture_validates(fixture_name):
    pytest.importorskip("jsonschema")
    schema = _load_schema(HIT_SCHEMA_PATH)
    path = HITS_DIR / fixture_name
    assert path.is_file(), f"Missing fixture: {path}"
    instance = _load_json(path)
    errors = _validate_against_schema(instance, schema)
    assert not errors, f"{fixture_name} failed schema validation: {errors}"


# ──────────────────────────────────────────────────────────────────────
# Test: Research boundary in all fixtures
# ──────────────────────────────────────────────────────────────────────

def test_research_boundary_in_all_target_fixtures():
    for fixture_file in TARGETS_DIR.glob("*.json"):
        instance = _load_json(fixture_file)
        assert instance.get("research_boundary") == RESEARCH_BOUNDARY, (
            f"{fixture_file.name} has wrong or missing research_boundary"
        )


def test_research_boundary_in_all_hit_fixtures():
    for fixture_file in HITS_DIR.glob("*.json"):
        instance = _load_json(fixture_file)
        assert instance.get("research_boundary") == RESEARCH_BOUNDARY, (
            f"{fixture_file.name} has wrong or missing research_boundary"
        )


def test_research_boundary_in_all_negative_fixtures():
    for fixture_file in NEGATIVE_DIR.glob("*.json"):
        instance = _load_json(fixture_file)
        assert instance.get("research_boundary") == RESEARCH_BOUNDARY, (
            f"{fixture_file.name} has wrong or missing research_boundary"
        )


# ──────────────────────────────────────────────────────────────────────
# Test: Target ID pattern in target fixtures
# ──────────────────────────────────────────────────────────────────────

def test_target_id_pattern_in_target_fixtures():
    pattern = re.compile(r"^uniprot:[A-Z0-9_]+$")
    for fixture_file in TARGETS_DIR.glob("*.json"):
        instance = _load_json(fixture_file)
        tid = instance.get("target_id", "")
        assert pattern.match(tid), (
            f"{fixture_file.name}: target_id '{tid}' does not match uniprot: pattern"
        )


def test_target_id_values_match_spec():
    expected = {
        "KCNH2.json": "uniprot:Q12809",
        "SCN5A.json": "uniprot:Q14524",
        "KCNQ1.json": "uniprot:P51787",
        "CACNA1C.json": "uniprot:Q13936",
        "EGFR.json": "uniprot:P00533",
        "BACE1.json": "uniprot:P56817",
    }
    for fname, expected_id in expected.items():
        instance = _load_json(TARGETS_DIR / fname)
        assert instance["target_id"] == expected_id, (
            f"{fname}: expected {expected_id}, got {instance['target_id']}"
        )


# ──────────────────────────────────────────────────────────────────────
# Test: Hit ID pattern
# ──────────────────────────────────────────────────────────────────────

def test_hit_id_pattern_in_hit_fixtures():
    pattern = re.compile(r"^P1-HIT-[A-Z0-9]+-[0-9]+$")
    for fixture_file in HITS_DIR.glob("*.json"):
        instance = _load_json(fixture_file)
        hid = instance.get("hit_id", "")
        assert pattern.match(hid), (
            f"{fixture_file.name}: hit_id '{hid}' does not match P1-HIT-<GENE>-<NNN>"
        )


# ──────────────────────────────────────────────────────────────────────
# Test: Cardiac hits reference correct UniProt IDs
# ──────────────────────────────────────────────────────────────────────

def test_cardiac_hits_target_ids():
    gene_to_uniprot = {
        "KCNH2": "uniprot:Q12809",
        "SCN5A": "uniprot:Q14524",
        "KCNQ1": "uniprot:P51787",
        "CACNA1C": "uniprot:Q13936",
    }
    for fixture_file in HITS_DIR.glob("*.json"):
        instance = _load_json(fixture_file)
        hit_id = instance.get("hit_id", "")
        # Extract gene from hit_id
        m = re.match(r"^P1-HIT-([A-Z0-9]+)-\d+$", hit_id)
        if m:
            gene = m.group(1)
            if gene in gene_to_uniprot:
                assert instance["target_id"] == gene_to_uniprot[gene], (
                    f"{fixture_file.name}: expected target_id {gene_to_uniprot[gene]}, "
                    f"got {instance['target_id']}"
                )


# ──────────────────────────────────────────────────────────────────────
# Test: ADMET panel required fields in hits
# ──────────────────────────────────────────────────────────────────────

def test_hit_admet_panel_required_fields():
    required = {"logP", "tpsa", "BBB_penetration_prob", "hERG_IC50_uM", "hepatotox_flag"}
    for fixture_file in HITS_DIR.glob("*.json"):
        instance = _load_json(fixture_file)
        admet = instance.get("admet_panel", {})
        missing = required - set(admet.keys())
        assert not missing, (
            f"{fixture_file.name}: admet_panel missing required fields: {missing}"
        )


def test_hit_predicted_pic50_in_range():
    for fixture_file in HITS_DIR.glob("*.json"):
        instance = _load_json(fixture_file)
        pic50 = instance.get("predicted_pIC50")
        assert pic50 is not None, f"{fixture_file.name}: missing predicted_pIC50"
        assert 4.0 <= pic50 <= 12.0, (
            f"{fixture_file.name}: predicted_pIC50 = {pic50} out of [4, 12] range"
        )


def test_hit_confidence_tier_valid():
    for fixture_file in HITS_DIR.glob("*.json"):
        instance = _load_json(fixture_file)
        tier = instance.get("confidence_tier")
        assert tier in {"A", "B", "C"}, (
            f"{fixture_file.name}: confidence_tier '{tier}' not in (A, B, C)"
        )


# ──────────────────────────────────────────────────────────────────────
# Test: Negative fixtures load as valid JSON and carry target_falsifier
# ──────────────────────────────────────────────────────────────────────

def test_negative_fixtures_load_as_json():
    neg_files = list(NEGATIVE_DIR.glob("*.json"))
    assert len(neg_files) >= 13, (
        f"Expected at least 13 negative fixtures, found {len(neg_files)}"
    )
    for fixture_file in neg_files:
        try:
            _load_json(fixture_file)
        except json.JSONDecodeError as exc:
            pytest.fail(f"{fixture_file.name}: JSON parse error: {exc}")


def test_negative_fixtures_have_target_falsifier():
    for fixture_file in NEGATIVE_DIR.glob("*.json"):
        instance = _load_json(fixture_file)
        assert "target_falsifier" in instance, (
            f"{fixture_file.name}: missing 'target_falsifier' field"
        )
        assert instance["target_falsifier"], (
            f"{fixture_file.name}: target_falsifier is empty"
        )


def test_negative_fixtures_have_note():
    for fixture_file in NEGATIVE_DIR.glob("*.json"):
        instance = _load_json(fixture_file)
        assert "note" in instance, f"{fixture_file.name}: missing 'note' field"
        assert len(instance["note"]) > 10, f"{fixture_file.name}: note too short"


def test_negative_fixtures_have_trigger_inputs():
    for fixture_file in NEGATIVE_DIR.glob("*.json"):
        instance = _load_json(fixture_file)
        assert "trigger_inputs" in instance, (
            f"{fixture_file.name}: missing 'trigger_inputs' field"
        )


# ──────────────────────────────────────────────────────────────────────
# Test: KG seed loads and validates (combined cardiac + pathway1)
# ──────────────────────────────────────────────────────────────────────

def test_kg_pathway1_seed_file_exists():
    assert KG_PATHWAY1_SEED.is_file(), f"Missing KG seed: {KG_PATHWAY1_SEED}"
    assert KG_CARDIAC_SEED.is_file(), f"Missing KG seed: {KG_CARDIAC_SEED}"


def test_kg_combined_loads_without_error():
    """Load cardiac + pathway1 seeds into a temp KGStore; no exceptions expected."""
    with tempfile.TemporaryDirectory() as tmp:
        store = KGStore(Path(tmp))
        n_cardiac = store.load_seed(KG_CARDIAC_SEED)
        n_pathway1 = store.load_seed(KG_PATHWAY1_SEED)
        assert n_cardiac > 0, "cardiac_seed.jsonl loaded 0 records"
        assert n_pathway1 > 0, "pathway1_seed.jsonl loaded 0 records"


def test_kg_combined_validator_passes():
    """KGValidator must pass on the combined seed (K1/K3, no dangling refs)."""
    with tempfile.TemporaryDirectory() as tmp:
        store = KGStore(Path(tmp))
        store.load_seed(KG_CARDIAC_SEED)
        store.load_seed(KG_PATHWAY1_SEED)
        result = KGValidator(store).validate()
        # Combined nodes/edges must be positive
        assert result["nodes"] > 0
        assert result["edges"] > 0


def test_kg_combined_no_dangling_refs():
    """No dangling source or target node references in combined KG."""
    with tempfile.TemporaryDirectory() as tmp:
        store = KGStore(Path(tmp))
        store.load_seed(KG_CARDIAC_SEED)
        store.load_seed(KG_PATHWAY1_SEED)
        # KGValidator.validate() raises KGValidationError on dangling refs
        from zer0pa_biomolecular_explorer.kg.validator import KGValidator as V
        try:
            result = V(store).validate()
        except Exception as exc:
            pytest.fail(f"KGValidator raised: {exc}")


def test_kg_pathway1_has_target_nodes():
    """pathway1_seed.jsonl must contain exactly 4 Target nodes for cardiac genes."""
    with tempfile.TemporaryDirectory() as tmp:
        store = KGStore(Path(tmp))
        store.load_seed(KG_PATHWAY1_SEED)
        from zer0pa_biomolecular_explorer.kg.schema import NodeType
        target_nodes = [
            n for n in store.iter_nodes() if n.node_type == NodeType.TARGET
        ]
        assert len(target_nodes) == 4, (
            f"Expected 4 Target nodes in pathway1_seed, found {len(target_nodes)}"
        )
        gene_symbols = {n.properties.get("gene_symbol") for n in target_nodes}
        assert gene_symbols == {"KCNH2", "SCN5A", "KCNQ1", "CACNA1C"}, (
            f"Target nodes gene symbols mismatch: {gene_symbols}"
        )


def test_kg_pathway1_has_binding_pocket_nodes():
    """pathway1_seed.jsonl must contain 4 BindingPocket nodes."""
    with tempfile.TemporaryDirectory() as tmp:
        store = KGStore(Path(tmp))
        store.load_seed(KG_PATHWAY1_SEED)
        from zer0pa_biomolecular_explorer.kg.schema import NodeType
        pocket_nodes = [
            n for n in store.iter_nodes() if n.node_type == NodeType.BINDING_POCKET
        ]
        assert len(pocket_nodes) == 4, (
            f"Expected 4 BindingPocket nodes, found {len(pocket_nodes)}"
        )


def test_kg_pathway1_has_disease_nodes():
    """pathway1_seed.jsonl must contain 4 Disease nodes."""
    with tempfile.TemporaryDirectory() as tmp:
        store = KGStore(Path(tmp))
        store.load_seed(KG_PATHWAY1_SEED)
        from zer0pa_biomolecular_explorer.kg.schema import NodeType
        disease_nodes = [
            n for n in store.iter_nodes() if n.node_type == NodeType.DISEASE
        ]
        assert len(disease_nodes) == 4, (
            f"Expected 4 Disease nodes, found {len(disease_nodes)}"
        )


def test_kg_pathway1_has_source_manifest_nodes():
    """pathway1_seed.jsonl must contain 5 new SourceManifest nodes for P1 sources."""
    with tempfile.TemporaryDirectory() as tmp:
        store = KGStore(Path(tmp))
        store.load_seed(KG_PATHWAY1_SEED)
        from zer0pa_biomolecular_explorer.kg.schema import NodeType
        source_nodes = [
            n for n in store.iter_nodes() if n.node_type == NodeType.SOURCE_MANIFEST
        ]
        expected_ids = {
            "source:OpenTargets_v25_06",
            "source:TTD_2026",
            "source:GWAS_Catalog_EBI",
            "source:ChEMBL_36",
            "source:UniProt_SwissProt",
        }
        found_ids = {n.node_id for n in source_nodes}
        missing = expected_ids - found_ids
        assert not missing, f"Missing SourceManifest nodes: {missing}"


def test_kg_pathway1_encodes_target_edges():
    """pathway1_seed.jsonl must have 4 ENCODES_TARGET edges."""
    with tempfile.TemporaryDirectory() as tmp:
        store = KGStore(Path(tmp))
        store.load_seed(KG_PATHWAY1_SEED)
        from zer0pa_biomolecular_explorer.kg.schema import EdgeType
        et_edges = [
            e for e in store.iter_edges() if e.edge_type == EdgeType.ENCODES_TARGET
        ]
        assert len(et_edges) == 4, (
            f"Expected 4 ENCODES_TARGET edges, found {len(et_edges)}"
        )


def test_kg_pathway1_encodes_target_edges_source_gene_nodes():
    """ENCODES_TARGET edges must reference gene:KCNH2, gene:SCN5A, gene:KCNQ1, gene:CACNA1C."""
    with tempfile.TemporaryDirectory() as tmp:
        store = KGStore(Path(tmp))
        store.load_seed(KG_CARDIAC_SEED)
        store.load_seed(KG_PATHWAY1_SEED)
        from zer0pa_biomolecular_explorer.kg.schema import EdgeType
        et_edges = [
            e for e in store.iter_edges() if e.edge_type == EdgeType.ENCODES_TARGET
        ]
        sources = {e.source_node_id for e in et_edges}
        assert sources == {"gene:KCNH2", "gene:SCN5A", "gene:KCNQ1", "gene:CACNA1C"}, (
            f"ENCODES_TARGET edge sources mismatch: {sources}"
        )


def test_kg_pathway1_has_binding_pocket_edges():
    """pathway1_seed.jsonl must have 4 HAS_BINDING_POCKET edges."""
    with tempfile.TemporaryDirectory() as tmp:
        store = KGStore(Path(tmp))
        store.load_seed(KG_PATHWAY1_SEED)
        from zer0pa_biomolecular_explorer.kg.schema import EdgeType
        hbp_edges = [
            e for e in store.iter_edges() if e.edge_type == EdgeType.HAS_BINDING_POCKET
        ]
        assert len(hbp_edges) == 4, (
            f"Expected 4 HAS_BINDING_POCKET edges, found {len(hbp_edges)}"
        )


def test_kg_pathway1_has_disease_association_edges():
    """pathway1_seed.jsonl must have at least 5 HAS_DISEASE_ASSOCIATION edges."""
    with tempfile.TemporaryDirectory() as tmp:
        store = KGStore(Path(tmp))
        store.load_seed(KG_PATHWAY1_SEED)
        from zer0pa_biomolecular_explorer.kg.schema import EdgeType
        hda_edges = [
            e for e in store.iter_edges() if e.edge_type == EdgeType.HAS_DISEASE_ASSOCIATION
        ]
        assert len(hda_edges) >= 5, (
            f"Expected >= 5 HAS_DISEASE_ASSOCIATION edges, found {len(hda_edges)}"
        )


def test_kg_combined_node_and_edge_counts():
    """Sanity check: combined KG has >= 45 nodes and >= 35 edges."""
    with tempfile.TemporaryDirectory() as tmp:
        store = KGStore(Path(tmp))
        store.load_seed(KG_CARDIAC_SEED)
        store.load_seed(KG_PATHWAY1_SEED)
        result = KGValidator(store).validate()
        assert result["nodes"] >= 45, f"Expected >= 45 nodes, got {result['nodes']}"
        assert result["edges"] >= 35, f"Expected >= 35 edges, got {result['edges']}"


# ──────────────────────────────────────────────────────────────────────
# Test: Target fixture specific field values
# ──────────────────────────────────────────────────────────────────────

def test_kcnh2_target_scores():
    instance = _load_json(TARGETS_DIR / "KCNH2.json")
    assert instance["genetic_evidence_score"] == 0.91
    assert instance["druggability_score"] == 0.87
    assert instance["novelty_flag"] is False


def test_bace1_novelty_flag_true():
    instance = _load_json(TARGETS_DIR / "BACE1.json")
    assert instance["novelty_flag"] is True, "BACE1 should have novelty_flag = true"


def test_all_cardiac_targets_have_kg_gene_node_ref():
    for gene in _CARDIAC_GENES:
        instance = _load_json(TARGETS_DIR / f"{gene}.json")
        ref = instance.get("kg_gene_node_ref")
        assert ref == f"gene:{gene}", (
            f"{gene}.json: expected kg_gene_node_ref 'gene:{gene}', got {ref!r}"
        )


def test_target_structure_refs_not_empty():
    for fixture_file in TARGETS_DIR.glob("*.json"):
        instance = _load_json(fixture_file)
        refs = instance.get("structure_refs", [])
        assert len(refs) >= 2, (
            f"{fixture_file.name}: expected >= 2 structure_refs, got {refs}"
        )


def test_target_disease_associations_not_empty():
    for fixture_file in TARGETS_DIR.glob("*.json"):
        instance = _load_json(fixture_file)
        das = instance.get("disease_associations", [])
        assert len(das) >= 2, (
            f"{fixture_file.name}: expected >= 2 disease_associations, got {das}"
        )


def test_target_source_manifest_refs_not_empty():
    for fixture_file in TARGETS_DIR.glob("*.json"):
        instance = _load_json(fixture_file)
        refs = instance.get("source_manifest_refs", [])
        assert len(refs) >= 3, (
            f"{fixture_file.name}: expected >= 3 source_manifest_refs, got {refs}"
        )
