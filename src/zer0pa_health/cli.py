"""Zer0pa Health CLI.

Entry point: `zer0pa-health` (declared in pyproject.toml).

Subcommands:
  run-cardiac        — end-to-end cardiac wedge run (writes audit, KG, packet, reasoner tuple)
  validate-audit     — validate an existing audit log run dir
  validate-kg        — validate the cardiac KG seed + any runtime nodes
  validate-packet    — re-load a packet JSON and re-score it against the PubMed baseline
  runpod-precheck    — dry-run the cutover steps and report which would block
  graph-export       — export the runtime KG (or seed) as Graphviz DOT
  bundle             — tar a single run's artifacts (audit + KG + packet + reasoner queue)
  compare-runs       — diff two cardiac run results side-by-side
  health-check       — repo-wide health check (audit + KG + falsification + packets)
"""

from __future__ import annotations

import json
import tarfile
from pathlib import Path

import typer

from zer0pa_health.audit import AuditValidator
from zer0pa_health.kg import KGStore, KGValidator
from zer0pa_health.packets import (
    BaselineHarness,
    CardiacEvidencePacket,
    score_baseline_for_compound,
    score_packet,
)
from zer0pa_health.runs import run_cardiac_compound, run_cardiac_wedge


app = typer.Typer(
    no_args_is_help=True,
    help=(
        "Zer0pa Health falsification engine CLI. Research use only. Not for diagnosis, "
        "treatment, cure claims, prescribing, clinical deployment, regulatory compliance, "
        "or drug-safety certification."
    ),
)


_SEED_COMPOUNDS = ["dofetilide", "verapamil", "ranolazine"]
_HELD_OUT = ["quinidine", "moxifloxacin", "diltiazem", "sotalol", "mexiletine", "lidocaine"]


@app.command("run-cardiac")
def run_cardiac(
    compound: str = typer.Argument(
        "all",
        help="Compound name. 'all' for the seed wedge; 'all+held-out' for the wedge plus held-out compounds.",
    ),
    runtime_dir: Path = typer.Option(
        Path(".runtime"),
        "--runtime",
        help="Runtime root directory (default: .runtime). audit/, kg/, packets/, reasoner_queue/ live under here.",
    ),
    cmax_unbound_uM: float = typer.Option(
        None,
        "--cmax-uM",
        help="Override the canned Cmax_unbound for the compound. Defaults to compound-specific stub value.",
    ),
) -> None:
    """End-to-end cardiac wedge run. Writes every audit table + KG runtime nodes + packet + reasoner tuple."""
    runtime_dir.mkdir(parents=True, exist_ok=True)
    if compound == "all":
        results = run_cardiac_wedge(runtime_dir, _SEED_COMPOUNDS)
    elif compound == "all+held-out":
        results = run_cardiac_wedge(runtime_dir, _SEED_COMPOUNDS + _HELD_OUT)
    else:
        from zer0pa_health.runs.cardiac_run import _DEFAULT_CMAX_uM

        cmax = cmax_unbound_uM if cmax_unbound_uM is not None else _DEFAULT_CMAX_uM.get(compound, 1.0)
        results = [run_cardiac_compound(compound, runtime_root=runtime_dir, cmax_unbound_uM=cmax)]

    typer.echo("\nRESEARCH USE ONLY. Not for diagnosis, treatment, cure claims, prescribing,")
    typer.echo("clinical deployment, regulatory compliance, or drug-safety certification.\n")
    typer.echo(f"{'compound':<18}{'verdict':<14}{'engine':>8}{'baseline':>10}{'lift':>8}{'fails':>8}{'audit':>10}")
    typer.echo("-" * 76)
    for r in results:
        n_fails = sum(r.falsifier_fail_counts.values())
        n_audit = sum(r.audit_table_counts.values())
        typer.echo(
            f"{r.compound:<18}{r.packet_verdict:<14}"
            f"{r.engine_score:>8.2f}{r.baseline_score:>10.2f}"
            f"{r.pubmed_lift:>+8.2f}{n_fails:>8}{n_audit:>10}"
        )
    typer.echo()
    for r in results:
        typer.echo(f"  {r.compound:<14} run_id={r.run_id} packet={r.packet_path.name}")


@app.command("validate-audit")
def validate_audit(
    runtime_dir: Path = typer.Argument(..., help="Runtime root containing audit/runs/<run_id>/"),
    run_id: str = typer.Argument(..., help="The run id to validate."),
) -> None:
    """Validate the audit log for a given run (boundary string, hash chain, dangling refs, PHI/secrets, bulk)."""
    counts = AuditValidator(runtime_dir / "audit", run_id).validate()
    typer.echo(json.dumps(counts, indent=2))


@app.command("validate-kg")
def validate_kg(
    runtime_dir: Path = typer.Argument(..., help="Runtime root containing kg/"),
) -> None:
    """Validate KG (no dangling refs; cardiac claims have multi_current_context; supported claims have evidence/source/falsifier/audit)."""
    store = KGStore(runtime_dir / "kg")
    res = KGValidator(store).validate()
    typer.echo(json.dumps(res, indent=2))


@app.command("validate-packet")
def validate_packet(
    packet_path: Path = typer.Argument(..., help="Path to a cardiac evidence packet JSON file."),
) -> None:
    """Re-load the packet JSON, validate against the Pydantic schema, and re-score against the PubMed baseline."""
    raw = json.loads(packet_path.read_text())
    packet = CardiacEvidencePacket.model_validate(raw)
    engine = score_packet(packet)
    baseline = score_baseline_for_compound(packet.compound.name)
    typer.echo(
        json.dumps(
            {
                "packet_id": packet.packet_id,
                "verdict": packet.verdict.value,
                "engine": engine.__dict__,
                "baseline": baseline.__dict__,
                "lift": engine.total - baseline.total,
                "research_boundary": packet.research_boundary,
            },
            indent=2,
        )
    )


def _runpod_precheck_logic(config_path: Path) -> int:
    """Pure logic: returns 0 on success, non-zero on config errors. No typer.Exit."""
    import yaml  # type: ignore[import-untyped]

    if not config_path.exists():
        typer.echo(f"missing: {config_path}", err=True)
        return 2
    cfg = yaml.safe_load(config_path.read_text())

    typer.echo("RESEARCH USE ONLY. Cutover precheck — CPU stub state expected.\n")
    blockers: list[tuple[str, str]] = []
    ok: list[str] = []

    for layer_name, layer_cfg in cfg.get("layers", {}).items():
        for adapter_key, ac in layer_cfg.items():
            backend = ac.get("backend", "stub")
            endpoint = ac.get("endpoint")
            label = f"{layer_name}.{adapter_key}"
            if backend == "stub":
                ok.append(f"{label}: backend=stub (CPU)")
            elif backend == "runpod_gpu":
                if not endpoint:
                    blockers.append((label, "backend=runpod_gpu but endpoint=null"))
                else:
                    ok.append(f"{label}: backend=runpod_gpu, endpoint set")

    parked = cfg.get("what_stays_parked_until_runpod", [])
    typer.echo(f"layers configured     : {sum(len(v) for v in cfg.get('layers', {}).values())}")
    typer.echo(f"on stub (CPU-ready)   : {len(ok)}")
    typer.echo(f"would-block at cutover: {len(blockers)}")
    typer.echo(f"parked-work items     : {len(parked)}")
    typer.echo()
    for label, reason in blockers:
        typer.echo(f"  BLOCK {label}: {reason}")
    typer.echo()
    typer.echo("Acceptance gates declared:")
    for g in cfg.get("acceptance_gates", []):
        typer.echo(f"  - {g['id']}: {g['description']}")
    return 0


@app.command("runpod-precheck")
def runpod_precheck(
    config_path: Path = typer.Option(
        Path("runpod.config.yaml"), "--config", help="Path to runpod.config.yaml"
    ),
) -> None:
    """Dry-run cutover steps; report which would block right now (e.g., no GPU, no endpoint)."""
    rc = _runpod_precheck_logic(config_path)
    if rc != 0:
        raise typer.Exit(rc)


@app.command("graph-export")
def graph_export(
    kg_root: Path = typer.Argument(..., help="kg/ directory"),
    out_dot: Path = typer.Option(Path("kg.dot"), "--out", help="Output DOT path"),
) -> None:
    """Export the KG (seed + runtime) as a Graphviz DOT file. No graphviz binary needed."""
    store = KGStore(kg_root)
    g = store.to_networkx()
    lines = ["digraph zer0pa_health_kg {", '  rankdir="LR";', '  node [shape=box, fontsize=10];']
    for n, data in g.nodes(data=True):
        nt = data.get("node_type", "?")
        lines.append(f'  "{n}" [label="{n}\\n[{nt}]"];')
    for u, v, data in g.edges(data=True):
        et = data.get("edge_type", "?")
        lines.append(f'  "{u}" -> "{v}" [label="{et}", fontsize=8];')
    lines.append("}")
    out_dot.write_text("\n".join(lines), encoding="utf-8")
    typer.echo(f"wrote {out_dot} (nodes={g.number_of_nodes()}, edges={g.number_of_edges()})")


@app.command("bundle")
def bundle(
    runtime_dir: Path = typer.Argument(..., help="Runtime root that contains audit/runs/<run_id>/"),
    run_id: str = typer.Argument(..., help="The run_id to bundle"),
    out_path: Path = typer.Option(
        None, "--out", help="Output .tar.gz path (default: <runtime>/bundles/<run_id>.tar.gz)"
    ),
) -> None:
    """Tar a single cardiac run's artifacts into a self-contained bundle.

    Bundle contents:
      - audit/runs/<run_id>/*.jsonl (all 12 tables + falsifier ledger)
      - kg/{nodes,edges}.jsonl (current snapshot)
      - packets/cardiac_evidence_packet_v0_1__*<run_id>*.json (the run's packet)
      - reasoner_queue/runs/<run_id>/tuples.jsonl
    """
    audit_run_dir = runtime_dir / "audit" / "runs" / run_id
    if not audit_run_dir.is_dir():
        typer.echo(f"missing: {audit_run_dir}", err=True)
        raise typer.Exit(1)

    if out_path is None:
        bundles_dir = runtime_dir / "bundles"
        bundles_dir.mkdir(parents=True, exist_ok=True)
        safe_id = run_id.replace(":", "_")
        out_path = bundles_dir / f"{safe_id}.tar.gz"

    with tarfile.open(out_path, "w:gz") as tf:
        # Audit (mandatory)
        for path in sorted(audit_run_dir.glob("*.jsonl")):
            tf.add(path, arcname=f"audit/runs/{run_id}/{path.name}")

        # KG snapshot
        kg_root = runtime_dir / "kg"
        for fname in ("nodes.jsonl", "edges.jsonl"):
            p = kg_root / fname
            if p.exists():
                tf.add(p, arcname=f"kg/{fname}")

        # Reasoner queue
        rq_dir = runtime_dir / "reasoner_queue" / "runs" / run_id
        if rq_dir.exists():
            for path in sorted(rq_dir.glob("*.jsonl")):
                tf.add(path, arcname=f"reasoner_queue/runs/{run_id}/{path.name}")

        # Packets matching the run
        packets_dir = runtime_dir / "packets"
        if packets_dir.exists():
            safe_id = run_id.replace(":", "_")
            for path in packets_dir.glob(f"*{safe_id}*"):
                tf.add(path, arcname=f"packets/{path.name}")

    typer.echo(f"wrote {out_path}")


@app.command("compare-runs")
def compare_runs(
    runtime_a: Path = typer.Argument(..., help="Runtime A root"),
    run_id_a: str = typer.Argument(..., help="Run ID A"),
    runtime_b: Path = typer.Argument(..., help="Runtime B root"),
    run_id_b: str = typer.Argument(..., help="Run ID B"),
) -> None:
    """Diff two cardiac runs' audit table counts + falsifier counts side-by-side."""
    def _audit_counts(rt: Path, rid: str) -> dict[str, int]:
        out: dict[str, int] = {}
        run_dir = rt / "audit" / "runs" / rid
        if not run_dir.exists():
            return out
        for p in run_dir.glob("*.jsonl"):
            n = sum(1 for line in p.read_text().splitlines() if line.strip())
            out[p.stem] = n
        return out

    a = _audit_counts(runtime_a, run_id_a)
    b = _audit_counts(runtime_b, run_id_b)
    keys = sorted(set(a) | set(b))
    typer.echo(f"{'table':<25}{'A':>10}{'B':>10}{'delta':>10}")
    typer.echo("-" * 55)
    for k in keys:
        va, vb = a.get(k, 0), b.get(k, 0)
        typer.echo(f"{k:<25}{va:>10}{vb:>10}{vb - va:>+10}")


@app.command("health-check")
def health_check(
    runtime_dir: Path = typer.Option(
        None, "--runtime",
        help="Optional runtime root with audit/runs/. If absent, only repo-level checks run.",
    ),
) -> None:
    """Run all top-level health checks: KG seed validity, runpod precheck, schemas, falsification spot-check.

    Exits non-zero if any check fails.
    """
    fails: list[str] = []

    # 1. KG seed loads + validates
    try:
        from zer0pa_health.kg import KGStore, KGValidator
        repo_root = Path(__file__).resolve().parents[2]
        store = KGStore(repo_root / "kg")
        if not (repo_root / "kg" / "cardiac_seed.jsonl").exists():
            fails.append("kg/cardiac_seed.jsonl missing")
        else:
            # Load seed into a temporary store to validate
            import tempfile

            tmp = Path(tempfile.mkdtemp())
            tmp_store = KGStore(tmp)
            tmp_store.load_seed(repo_root / "kg" / "cardiac_seed.jsonl")
            res = KGValidator(tmp_store).validate()
            typer.echo(f"  KG seed: nodes={res['nodes']} edges={res['edges']}")
    except Exception as e:  # noqa: BLE001
        fails.append(f"KG seed: {e}")

    # 2. runpod-precheck
    try:
        repo_root = Path(__file__).resolve().parents[2]
        rc = _runpod_precheck_logic(repo_root / "runpod.config.yaml")
        if rc != 0:
            fails.append(f"runpod precheck returned {rc}")
    except Exception as e:  # noqa: BLE001
        fails.append(f"runpod precheck: {e}")

    # 3. compound fixtures load
    try:
        repo_root = Path(__file__).resolve().parents[2]
        n_compounds = 0
        for path in (repo_root / "fixtures" / "compounds").glob("*.json"):
            data = json.loads(path.read_text())
            assert "research_boundary" in data
            assert "channel_panel_canned" in data
            n_compounds += 1
        typer.echo(f"  compound fixtures: {n_compounds} loaded and basic-shape validated")
    except Exception as e:  # noqa: BLE001
        fails.append(f"compound fixtures: {e}")

    # 4. Optional: live runtime audit validation
    if runtime_dir:
        try:
            for run_dir in (runtime_dir / "audit" / "runs").iterdir():
                if run_dir.is_dir():
                    AuditValidator(runtime_dir / "audit", run_dir.name).validate()
            typer.echo(f"  runtime audit: all runs in {runtime_dir} validated")
        except Exception as e:  # noqa: BLE001
            fails.append(f"runtime audit: {e}")

    if fails:
        typer.echo()
        typer.echo("HEALTH CHECK FAILED")
        for f in fails:
            typer.echo(f"  FAIL: {f}", err=True)
        raise typer.Exit(1)

    typer.echo()
    typer.echo("HEALTH CHECK PASSED")


@app.command("export-finetune-corpus")
def export_finetune_corpus(
    runtime_dir: Path = typer.Argument(..., help="Runtime root containing reasoner_queue/runs/"),
    out_path: Path = typer.Option(
        Path("finetune_corpus.jsonl"),
        "--out",
        help="Output JSONL of (positives, negatives) for fine-tuning",
    ),
) -> None:
    """Walk all reasoner_queue/runs/<rid>/tuples.jsonl and emit a corpus split into
    fine-tune positives (passed + ground-truth available/human-adjudication) and
    fine-tune negatives (failed status OR clinical_overclaim class).

    Each output line: {"split": "positive|negative", "tuple": <full tuple JSON>}.
    """
    from zer0pa_health.reasoner.queue import ReasonerQueue
    from zer0pa_health.reasoner.tuple_schema import (
        GroundTruthStatus,
        GroundTruthType,
        ReasonerFalsifierClass,
        ReasonerFalsifierStatus,
    )

    runs_dir = runtime_dir / "reasoner_queue" / "runs"
    if not runs_dir.is_dir():
        typer.echo(f"missing: {runs_dir}", err=True)
        raise typer.Exit(1)

    n_pos = 0
    n_neg = 0
    n_skipped = 0

    with out_path.open("w", encoding="utf-8") as out_fh:
        for run_dir in sorted(runs_dir.iterdir()):
            if not run_dir.is_dir():
                continue
            queue_path = run_dir / "tuples.jsonl"
            if not queue_path.exists():
                continue
            queue = ReasonerQueue(
                queue_path=runtime_dir / "reasoner_queue", run_id=run_dir.name
            )
            for t in queue.iter():
                # Positive eligibility:
                is_positive = (
                    t.falsifier.status == ReasonerFalsifierStatus.PASSED
                    and (
                        t.ground_truth.status == GroundTruthStatus.AVAILABLE
                        or t.ground_truth.type == GroundTruthType.HUMAN_ADJUDICATION
                    )
                )
                # Negative eligibility:
                is_negative = (
                    t.falsifier.status == ReasonerFalsifierStatus.FAILED
                    or t.falsifier.falsifier_class == ReasonerFalsifierClass.CLINICAL_OVERCLAIM
                )
                if is_positive:
                    out_fh.write(
                        json.dumps({"split": "positive", "tuple": t.model_dump(mode="json")})
                        + "\n"
                    )
                    n_pos += 1
                elif is_negative:
                    out_fh.write(
                        json.dumps({"split": "negative", "tuple": t.model_dump(mode="json")})
                        + "\n"
                    )
                    n_neg += 1
                else:
                    n_skipped += 1

    typer.echo(f"wrote {out_path}")
    typer.echo(f"  positives: {n_pos}")
    typer.echo(f"  negatives: {n_neg}")
    typer.echo(f"  skipped (neither): {n_skipped}")


def main() -> int:
    app()
    return 0


if __name__ == "__main__":
    main()
