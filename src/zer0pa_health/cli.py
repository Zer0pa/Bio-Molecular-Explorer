"""Zer0pa Health CLI.

Entry point: `zer0pa-health` (declared in pyproject.toml).

Subcommands:
  run-cardiac        — end-to-end cardiac wedge run (writes audit, KG, packet, reasoner tuple)
  validate-audit     — validate an existing audit log run dir
  validate-kg        — validate the cardiac KG seed + any runtime nodes
  validate-packet    — re-load a packet JSON and re-score it against the PubMed baseline
  runpod-precheck    — dry-run the cutover steps and report which would block
  graph-export       — export the runtime KG (or seed) as Graphviz DOT
"""

from __future__ import annotations

import json
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


@app.command("runpod-precheck")
def runpod_precheck(
    config_path: Path = typer.Option(
        Path("runpod.config.yaml"), "--config", help="Path to runpod.config.yaml"
    ),
) -> None:
    """Dry-run cutover steps; report which would block right now (e.g., no GPU, no endpoint).

    Exits 0 if all checks pass for the CPU-stub state. Exits non-zero only on
    config-file errors. Cutover blockers are reported as informational; they
    are EXPECTED on a CPU-only build.
    """
    import yaml  # type: ignore[import-untyped]

    if not config_path.exists():
        typer.echo(f"missing: {config_path}", err=True)
        raise typer.Exit(2)
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


def main() -> int:
    app()
    return 0


if __name__ == "__main__":
    main()
