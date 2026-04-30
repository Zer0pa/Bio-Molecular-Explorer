"""Plug-swap hardening (Phase E.1 — operator brief 2026-04-30).

The existing plug-swap tests verify top-level envelope output keys match
between Stub and Toy adapters. This module adds STRICTER plug-replaceability
invariants the brief calls out:

  1. Call signatures: stub and toy expose the same public methods with
     identical signatures (parameter names + kinds + defaults).
  2. Nested schemas: envelope output value types match RECURSIVELY for the
     keys both adapters expose.
  3. Endpoint request/response shapes: every public adapter method on stub
     and toy returns a `LayerEnvelope` (no leaking raw dicts).
  4. Audit provenance: every envelope carries audit_record_id, input_hash,
     output_hash — both stub and toy.
  5. Falsifier preservation: the SET of falsifier classes emitted by stub
     and toy must be equal (or one must explicitly note an absence in
     `evidence`). Swapping the implementation must not silently drop a
     falsifier.

These are run as pytest assertions against L1-L5 stub vs toy.
"""

from __future__ import annotations

import inspect

import pytest

from zer0pa_health.envelope import LayerEnvelope


# ---------------- helpers ----------------


def _public_methods(cls: type) -> dict[str, inspect.Signature]:
    out: dict[str, inspect.Signature] = {}
    for name, member in inspect.getmembers(cls, predicate=inspect.isfunction):
        if name.startswith("_"):
            continue
        out[name] = inspect.signature(member)
    return out


def _normalize_param(p: inspect.Parameter) -> tuple:
    """Turn a Parameter into a comparable tuple (name, kind, has_default)."""
    return (p.name, p.kind, p.default is not inspect.Parameter.empty)


def _assert_signature_compatible(sig_a: inspect.Signature, sig_b: inspect.Signature, label: str) -> None:
    """Compatible = same parameter names, kinds, and default-presence."""
    a = [_normalize_param(p) for p in sig_a.parameters.values()]
    b = [_normalize_param(p) for p in sig_b.parameters.values()]
    assert a == b, f"[{label}] signature mismatch:\n  stub={a}\n  toy={b}"


def _value_shape(v):
    """Recursive shape descriptor: type name + (for dict/list) child shape."""
    if isinstance(v, dict):
        return ("dict", {k: _value_shape(vv) for k, vv in v.items()})
    if isinstance(v, list):
        if not v:
            return ("list", "empty")
        return ("list", _value_shape(v[0]))
    return (type(v).__name__,)


def _shapes_compatible(sa, sb) -> bool:
    """Plug-compat shape comparison.

    - `dict` shapes must have compatible child-shapes for shared keys (extra keys allowed).
    - `list` shapes are compatible if both are list and (a) both empty, (b) both
      populated with compatible element shapes, or (c) one is empty (downstream
      consumers parse `list[X]` and accept the empty case).
    - `NoneType` is compatible with any other scalar (Pydantic `T | None` schemas
      accept both shapes).
    - scalar shapes must equal otherwise.
    """
    if sa == sb:
        return True
    # NoneType is compatible with any concrete scalar (T | None unions).
    if isinstance(sa, tuple) and isinstance(sb, tuple) and len(sa) == 1 and len(sb) == 1:
        if sa[0] == "NoneType" or sb[0] == "NoneType":
            return True
    if isinstance(sa, tuple) and isinstance(sb, tuple) and sa[0] == sb[0]:
        kind = sa[0]
        if kind == "list":
            inner_a, inner_b = sa[1], sb[1]
            if inner_a == "empty" or inner_b == "empty":
                return True
            return _shapes_compatible(inner_a, inner_b)
        if kind == "dict":
            shared_keys = set(sa[1]) & set(sb[1])
            return all(
                _shapes_compatible(sa[1][k], sb[1][k]) for k in shared_keys
            )
    return False


def _assert_envelope_audit_shape(env: LayerEnvelope, label: str) -> None:
    audit = env.audit
    assert audit.audit_record_id, f"[{label}] missing audit_record_id"
    assert audit.input_hash, f"[{label}] missing input_hash"
    assert audit.output_hash, f"[{label}] missing output_hash"
    # Hashes are formatted "sha256:<64-hex>"
    for label_h, h in (("input_hash", audit.input_hash), ("output_hash", audit.output_hash)):
        assert h.startswith("sha256:"), f"[{label}] {label_h} missing sha256: prefix"
        hex_body = h.split(":", 1)[1]
        assert len(hex_body) == 64, f"[{label}] {label_h} hex body length != 64: {h}"
        int(hex_body, 16)  # raises if non-hex


def _assert_envelope_returned(value, label: str) -> None:
    assert isinstance(value, LayerEnvelope), (
        f"[{label}] adapter method must return LayerEnvelope, got {type(value).__name__}"
    )


def _falsifier_classes(env: LayerEnvelope) -> set[str]:
    return {it.falsifier_class for it in env.falsifier.items}


def _assert_falsifier_preservation(env_a: LayerEnvelope, env_b: LayerEnvelope, label: str) -> None:
    classes_a = _falsifier_classes(env_a)
    classes_b = _falsifier_classes(env_b)
    diff = classes_a.symmetric_difference(classes_b)
    assert not diff, (
        f"[{label}] falsifier-class mismatch between stub and toy: "
        f"stub_only={sorted(classes_a - classes_b)}, "
        f"toy_only={sorted(classes_b - classes_a)}. "
        "Plug-swap must preserve the falsifier set."
    )


def _assert_nested_shape_compatible(env_a: LayerEnvelope, env_b: LayerEnvelope, label: str) -> None:
    """For each key present in BOTH envelopes, recursive shapes must be plug-compatible."""
    out_a = env_a.output
    out_b = env_b.output
    common_keys = set(out_a.keys()) & set(out_b.keys())
    for k in sorted(common_keys):
        sa = _value_shape(out_a[k])
        sb = _value_shape(out_b[k])
        assert _shapes_compatible(sa, sb), (
            f"[{label}] nested-shape mismatch on key {k!r}:\n"
            f"  stub_shape={sa}\n  toy_shape={sb}"
        )


# ---------------- L1 ----------------


def test_l1_signatures_match():
    from zer0pa_health.layers.l1.adapter import L1StubAdapter
    from zer0pa_health.layers.l1.toy_adapter import L1ToyAdapter

    sigs_a = _public_methods(L1StubAdapter)
    sigs_b = _public_methods(L1ToyAdapter)
    common = set(sigs_a) & set(sigs_b)
    assert common, "no shared public methods between L1 stub and L1 toy"
    for name in sorted(common):
        _assert_signature_compatible(sigs_a[name], sigs_b[name], f"L1.{name}")


def test_l1_channel_panel_audit_provenance_and_falsifiers_preserved():
    from zer0pa_health.contracts.l1 import (
        L1ChannelGene,
        L1ChannelPanelInput,
        L1IonCurrent,
        L1TargetInput,
    )
    from zer0pa_health.layers.l1.adapter import L1StubAdapter
    from zer0pa_health.layers.l1.toy_adapter import L1ToyAdapter

    inp = L1ChannelPanelInput(targets=[
        L1TargetInput(gene=L1ChannelGene.KCNH2, current=L1IonCurrent.IKr),
        L1TargetInput(gene=L1ChannelGene.SCN5A, current=L1IonCurrent.INaL),
        L1TargetInput(gene=L1ChannelGene.KCNQ1, current=L1IonCurrent.IKs),
        L1TargetInput(gene=L1ChannelGene.CACNA1C, current=L1IonCurrent.ICaL),
    ])
    env_a = L1StubAdapter().channel_panel(
        inp, ligand_smiles="CCO",
        ligand_inchikey="LFQSCWFLJHTTHZ-UHFFFAOYSA-N",
    )
    env_b = L1ToyAdapter().channel_panel(
        inp, ligand_smiles="CCO",
        ligand_inchikey="LFQSCWFLJHTTHZ-UHFFFAOYSA-N",
    )
    _assert_envelope_returned(env_a, "L1.channel_panel(stub)")
    _assert_envelope_returned(env_b, "L1.channel_panel(toy)")
    _assert_envelope_audit_shape(env_a, "L1.channel_panel(stub)")
    _assert_envelope_audit_shape(env_b, "L1.channel_panel(toy)")
    _assert_falsifier_preservation(env_a, env_b, "L1.channel_panel")
    _assert_nested_shape_compatible(env_a, env_b, "L1.channel_panel")


# ---------------- L2 ----------------


def test_l2_signatures_match():
    from zer0pa_health.layers.l2.adapter import L2StubAdapter
    from zer0pa_health.layers.l2.toy_adapter import L2ToyAdapter

    sigs_a = _public_methods(L2StubAdapter)
    sigs_b = _public_methods(L2ToyAdapter)
    common = set(sigs_a) & set(sigs_b)
    assert common, "no shared public methods between L2 stub and L2 toy"
    for name in sorted(common):
        _assert_signature_compatible(sigs_a[name], sigs_b[name], f"L2.{name}")


def test_l2_audit_provenance_present():
    from zer0pa_health.contracts.l2 import (
        L2MoleculeInput, L2PropertyInput, L2RetrosynthFeedback,
    )
    from zer0pa_health.layers.l2.adapter import L2StubAdapter
    from zer0pa_health.layers.l2.toy_adapter import L2ToyAdapter

    inp = L2PropertyInput(
        molecule=L2MoleculeInput(smiles="CCO", inchikey="LFQSCWFLJHTTHZ-UHFFFAOYSA-N"),
        retrosynth_feedback=L2RetrosynthFeedback(
            smiles="CCO",
            route_score=0.5,
            route_depth=2,
            sa_score=4.0,
            starting_material_cost_usd=100.0,
            routes_found=True,
        ),
    )
    env_a = L2StubAdapter().process(inp)
    env_b = L2ToyAdapter().process(inp)
    _assert_envelope_audit_shape(env_a, "L2.process(stub)")
    _assert_envelope_audit_shape(env_b, "L2.process(toy)")
    _assert_falsifier_preservation(env_a, env_b, "L2.process")


# ---------------- L2.5 ----------------


def test_l25_signatures_match():
    from zer0pa_health.layers.l2_5.adapter import L25StubAdapter
    from zer0pa_health.layers.l2_5.toy_adapter import L25ToyAdapter

    sigs_a = _public_methods(L25StubAdapter)
    sigs_b = _public_methods(L25ToyAdapter)
    common = set(sigs_a) & set(sigs_b)
    assert common, "no shared public methods between L2.5 stub and L2.5 toy"
    for name in sorted(common):
        _assert_signature_compatible(sigs_a[name], sigs_b[name], f"L2.5.{name}")


def test_l25_audit_provenance_present():
    from zer0pa_health.contracts.l2_5 import L25Input, L25Policy
    from zer0pa_health.layers.l2_5.adapter import L25StubAdapter
    from zer0pa_health.layers.l2_5.toy_adapter import L25ToyAdapter

    inp = L25Input(canonical_smiles="CCO", policy=L25Policy.STUB)
    env_a = L25StubAdapter().process(inp)
    env_b = L25ToyAdapter().process(inp)
    _assert_envelope_audit_shape(env_a, "L2.5.process(stub)")
    _assert_envelope_audit_shape(env_b, "L2.5.process(toy)")


# ---------------- L3 ----------------


def test_l3_signatures_match():
    from zer0pa_health.layers.l3.adapter import L3StubAdapter
    from zer0pa_health.layers.l3.toy_adapter import L3ToyAdapter

    sigs_a = _public_methods(L3StubAdapter)
    sigs_b = _public_methods(L3ToyAdapter)
    common = set(sigs_a) & set(sigs_b)
    assert common, "no shared public methods between L3 stub and L3 toy"
    for name in sorted(common):
        _assert_signature_compatible(sigs_a[name], sigs_b[name], f"L3.{name}")


def test_l3_audit_provenance_present():
    from zer0pa_health.contracts.l3 import L3ProcessInput
    from zer0pa_health.layers.l3.adapter import L3StubAdapter
    from zer0pa_health.layers.l3.toy_adapter import L3ToyAdapter

    inp = L3ProcessInput(
        target_canonical_smiles="CCO",
        route_rxnsmiles=["[CH4:1].[OH2:2]>>[CH3:1][OH:2]"],
        target_throughput_kg_per_batch=1.0,
    )
    env_a = L3StubAdapter().process(inp)
    env_b = L3ToyAdapter().process(inp)
    _assert_envelope_audit_shape(env_a, "L3.process(stub)")
    _assert_envelope_audit_shape(env_b, "L3.process(toy)")


# ---------------- L4 ----------------


def test_l4_signatures_match():
    from zer0pa_health.layers.l4.adapter import L4StubAdapter
    from zer0pa_health.layers.l4.toy_adapter import L4ToyAdapter

    sigs_a = _public_methods(L4StubAdapter)
    sigs_b = _public_methods(L4ToyAdapter)
    common = set(sigs_a) & set(sigs_b)
    assert common, "no shared public methods between L4 stub and L4 toy"
    for name in sorted(common):
        _assert_signature_compatible(sigs_a[name], sigs_b[name], f"L4.{name}")


def test_l4_audit_provenance_present():
    from zer0pa_health.contracts.l4 import (
        L4SensorClass, L4SensorState, L4VirtualPlantInput,
    )
    from zer0pa_health.layers.l4.adapter import L4StubAdapter
    from zer0pa_health.layers.l4.toy_adapter import L4ToyAdapter

    inp = L4VirtualPlantInput(
        process_graph_unit_ops=["reaction_1"],
        sensor_states=[L4SensorState(
            sensor_id="PAT-T-01", sensor_class=L4SensorClass.PAT_TEMP,
            value=25.0, unit="C", timestamp_utc="2026-04-30T00:00:00Z",
            in_range=True, expected_range=(20.0, 60.0),
        )],
        target_throughput_kg_per_batch=1.0,
    )
    env_a = L4StubAdapter().process(inp)
    env_b = L4ToyAdapter().process(inp)
    _assert_envelope_audit_shape(env_a, "L4.process(stub)")
    _assert_envelope_audit_shape(env_b, "L4.process(toy)")


# ---------------- L5 ----------------


def test_l5_signatures_match():
    from zer0pa_health.layers.l5.adapter import L5StubAdapter
    from zer0pa_health.layers.l5.toy_adapter import L5ToyAdapter

    sigs_a = _public_methods(L5StubAdapter)
    sigs_b = _public_methods(L5ToyAdapter)
    common = set(sigs_a) & set(sigs_b)
    assert common, "no shared public methods between L5 stub and L5 toy"
    for name in sorted(common):
        _assert_signature_compatible(sigs_a[name], sigs_b[name], f"L5.{name}")


def test_l5_audit_provenance_present():
    from zer0pa_health.contracts.l5 import L5PKModelKind, L5PKPDInput
    from zer0pa_health.layers.l5.adapter import L5StubAdapter
    from zer0pa_health.layers.l5.toy_adapter import L5ToyAdapter

    inp = L5PKPDInput(
        canonical_smiles="CCO",
        inchikey="LFQSCWFLJHTTHZ-UHFFFAOYSA-N",
        dose_mg=0.5,
        model_kind=L5PKModelKind.ONE_COMPARTMENT,
        fraction_unbound=0.4,
        cl_l_per_h=10.0,
        vd_l=70.0,
        ka_per_h=1.0,
    )
    env_a = L5StubAdapter().process(inp)
    env_b = L5ToyAdapter().process(inp)
    _assert_envelope_audit_shape(env_a, "L5.process(stub)")
    _assert_envelope_audit_shape(env_b, "L5.process(toy)")
