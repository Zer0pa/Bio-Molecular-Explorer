# Bio-Molecular Explorer Clean Rename PRD

Research use only. Not for diagnosis, treatment, cure claims, prescribing, clinical deployment, regulatory compliance, or drug-safety certification. Every artifact you produce carries this boundary verbatim.

Status note, 2026-05-03: this PRD is a completed rename execution artifact retained for audit. It is not a current startup prompt. Current agents must use `Zer0pa/Bio-Molecular-Explorer`, `zer0pa-biomolecular-explorer`, and `zer0pa_biomolecular_explorer`.

## 0. Authority

This PRD is the execution authority for the pre-public clean rename of `Zer0pa/Health` to **Bio-Molecular Explorer**.

The executing agent must treat this document as the touchstone. Do not improvise a weaker rename. Do not stop at a README/title rename. Do not preserve legacy `Health` identity for convenience. Execute end to end until the repository is renamed, the code imports and CLI are renamed, the test suite passes, GitHub main is pushed, and GitHub main is re-read.

The only acceptable final state is a clean pre-public rename:

- GitHub repo: `Zer0pa/Bio-Molecular-Explorer`
- Public product/lane title: `Zer0pa Bio-Molecular Explorer`
- Short identifier: `Bio-Molecular Explorer`
- Python distribution package: `zer0pa-biomolecular-explorer`
- Python import package: `zer0pa_biomolecular_explorer`
- Primary CLI command: `zer0pa-biomolecular-explorer`
- L1 stub CLI command: `zer0pa-biomolecular-l1-stub`

## 1. Boundary

Research use only. Not for diagnosis, treatment, cure claims, prescribing, clinical deployment, regulatory compliance, or drug-safety certification. Every artifact you produce carries this boundary verbatim.

The rename must not weaken the research-only posture. The new name must not imply clinical deployment, patient use, diagnosis, treatment, prescribing, regulatory compliance, drug-safety certification, or any operational medical product claim.

## 2. What The Pipeline Is

Bio-Molecular Explorer is a research-only evidence and falsification pipeline for molecular and biological-system exploration.

The current implementation has two connected halves:

1. Pathway 1 R&D front end:
   - target identification,
   - structure modeling,
   - candidate generation,
   - screening,
   - optimization,
   - handoff to downstream evidence paths.

2. Cardiac evidence authority wedge:
   - current compounds: dofetilide, verapamil, ranolazine, and held-out comparators,
   - current targets: KCNH2, SCN5A, KCNQ1, CACNA1C,
   - multi-current CiPA framing,
   - audit, KG, falsifier ledger, morphology gates, PKPD/exposure-channel bridge, and L6 governance.

Plain-English framing for README and docs:

> Bio-Molecular Explorer turns molecular research inputs into auditable, falsifier-governed biological evidence packets, with cardiac evidence as the first proving wedge.

Do not describe the repository as a drug-development product. Do not center the word "drug" in the title. "Drug" may remain only where the domain concept is literally drug discovery, drug candidates, drug safety, or inherited source text.

## 3. Why This Rename Exists

`Health` is too broad and risks consumer/clinical interpretation. The repo is going live as a window into lab operations while still WIP. The public name must be descriptive enough for portfolio visitors and precise enough to avoid medical-product overclaim.

The chosen name, **Bio-Molecular Explorer**, says:

- bio: biological systems, channels, morphology, PKPD, KG, evidence packets,
- molecular: candidate molecules, structure, binding, retrosynthesis, process/formulation,
- explorer: research navigation, evidence generation, falsification, not clinical decisioning.

## 4. Non-Negotiable Invariants

The executing agent must preserve all of these:

1. Repository visibility must not be changed.
2. The research boundary must remain verbatim in every newly touched artifact.
3. The Lab Front Door first-ten README spine must remain intact:
   - `## What This Is`
   - `## Pipeline Mechanics`
   - `## Key Metrics`
   - `## Repo Identity`
   - `## Readiness`
   - `## What We Prove`
   - `## What We Don't Claim`
   - `## Verification Status`
   - `## Proof Anchors`
   - `## Repo Shape`
4. README lead must remain 30 words or fewer.
5. README must have exactly four Key Metrics rows.
6. README must have no more than six Proof Anchors.
7. Every README Proof Anchor path must resolve on GitHub main after the rename.
8. The real blockers must remain visible:
   - synthetic PubMed-reader lift is not authority,
   - user-facing cardiac path must prove L6 governance,
   - packet assembly must consume validated L1-L5 envelopes,
   - cardiac run must populate the governing `FalsifierLedger`,
   - `runpod-precheck` must fail invalid real-cutover states,
   - terminal L6 FAIL/REROUTE/KG divergence must block promotion.
9. H100 status must remain: ready to begin completion work, not ready for authoritative Runpod cutover.
10. Pathway 1 must remain non-governing until cardiac authority passes.
11. Do not make regulatory, clinical, prescribing, diagnosis, cure, treatment, or certification claims.

## 5. Rename Scope

This is a clean pre-public rename. It includes repo, docs, package, module, imports, tests, CLI, and GitHub references.

Required scope:

- GitHub repository name.
- README title, lead, repo identity table, proof anchors, repo shape, package/CLI/path references.
- `pyproject.toml` package name, description, scripts.
- Source directory:
  - from `src/zer0pa_health/`
  - to `src/zer0pa_biomolecular_explorer/`
- Every Python import:
  - from `zer0pa_health...`
  - to `zer0pa_biomolecular_explorer...`
- Tests and monkeypatch strings.
- Scripts.
- JSON Schema titles where they carry `Zer0pa Health`.
- Agent handoffs and startup prompts.
- PRDs and support docs where they refer to the repository or lane identity.
- GitHub URLs:
  - from `https://github.com/Zer0pa/Health`
  - to `https://github.com/Zer0pa/Bio-Molecular-Explorer`
- Local "clone this repo" commands and handoff directions.
- README proof anchors after GitHub rename.

Explicitly out of scope:

- Changing architecture, falsifiers, scientific gates, or packet semantics.
- Fixing the authority blockers in this rename pass.
- Adding H100 adapters.
- Changing repository visibility.
- Rewriting inherited source briefs for style.
- Changing third-party terms such as "Health AI Developer Foundations" when that is a proper name.
- Renaming external HF datasets unless the user explicitly approves a separate dataset migration.

## 6. Target Identifiers

Use exactly these identifiers unless the user explicitly overrides this PRD:

| Surface | Old | New |
| --- | --- | --- |
| GitHub repo | `Zer0pa/Health` | `Zer0pa/Bio-Molecular-Explorer` |
| Display title | `Zer0pa Health` | `Zer0pa Bio-Molecular Explorer` |
| Short identifier | `Health` | `Bio-Molecular Explorer` |
| Python distribution | `zer0pa-health` | `zer0pa-biomolecular-explorer` |
| Python import package | `zer0pa_health` | `zer0pa_biomolecular_explorer` |
| Primary CLI | `zer0pa-health` | `zer0pa-biomolecular-explorer` |
| L1 stub CLI | `zer0pa-l1-stub` | `zer0pa-biomolecular-l1-stub` |
| Repo URL | `https://github.com/Zer0pa/Health` | `https://github.com/Zer0pa/Bio-Molecular-Explorer` |

Do not create compatibility aliases for `zer0pa-health` or `zer0pa_health`. This is pre-public. No agents are currently dependent on the old identity. Leaving compatibility aliases would preserve legacy identity and defeat the clean rename.

## 7. Preflight

Before editing:

1. Confirm current directory is the repo root.
2. Run `git status --short --branch`.
3. Run `git fetch origin main`.
4. If local `main` is behind `origin/main`, pull/rebase before editing.
5. Confirm repository visibility through `gh repo view`.
6. Confirm no uncommitted user changes exist. If unrelated uncommitted changes exist, stop and report. Do not overwrite them.
7. Save the current head SHA for the final report.

Required preflight commands:

```bash
git status --short --branch
git fetch origin main
git rev-parse HEAD
gh repo view Zer0pa/Health --json nameWithOwner,visibility,defaultBranchRef,url
```

Expected before rename:

- default branch is `main`,
- visibility remains `INTERNAL`,
- working tree clean,
- repo is `Zer0pa/Health`.

## 8. Mechanical Rename Procedure

Follow this order. Do not skip steps.

### 8.1 Rename Python Package Directory

Rename:

```bash
git mv src/zer0pa_health src/zer0pa_biomolecular_explorer
```

Then update imports and module strings:

- `from zer0pa_health...` -> `from zer0pa_biomolecular_explorer...`
- `import zer0pa_health...` -> `import zer0pa_biomolecular_explorer...`
- monkeypatch strings:
  - `zer0pa_health.` -> `zer0pa_biomolecular_explorer.`
- module path strings in tests/docs where they are actual import paths.

Do not use a lazy runtime shim package named `zer0pa_health`. This is a clean rename.

### 8.2 Update Python Packaging

In `pyproject.toml`:

- `name = "zer0pa-biomolecular-explorer"`
- description must mention Bio-Molecular Explorer and the research boundary.
- scripts:
  - `zer0pa-biomolecular-explorer = "zer0pa_biomolecular_explorer.cli:app"`
  - `zer0pa-biomolecular-l1-stub = "zer0pa_biomolecular_explorer.layers.l1.server:run"`

Remove `zer0pa-health` and `zer0pa-l1-stub` script entries.

### 8.3 Update CLI References

Every command reference in docs/tests must move from:

- `zer0pa-health ...`

to:

- `zer0pa-biomolecular-explorer ...`

Only keep old command names inside historical quoted text if the file is explicitly historical and changing it would falsify a receipt. If preserved, add a nearby note that the old command is historical and no longer current.

### 8.4 Update README

README must remain the live-lab front door.

Required front matter:

```markdown
# Zer0pa Bio-Molecular Explorer

> Live window into the Zer0pa lab. Bio-Molecular Explorer is a research-only evidence pipeline, not a medical product or safety certification.
```

Lead must be 30 words or fewer. Count it.

In `## What This Is`, include the hard boundary verbatim near the top.

Replace the first descriptive paragraph with wording close to:

> Zer0pa Bio-Molecular Explorer turns molecular research inputs into auditable, falsifier-governed biological evidence packets. The first authority wedge is cardiac: dofetilide, verapamil, ranolazine, and held-out comparators through KCNH2, SCN5A, KCNQ1, and CACNA1C under multi-current CiPA framing. FDA E14/S7B are regulatory-science anchors only; this repo does not claim regulatory compliance.

Update identity:

- Identifier: `Bio-Molecular Explorer`
- Repository: `https://github.com/Zer0pa/Bio-Molecular-Explorer`
- Portfolio: `Bio-molecular research infrastructure`
- Python Package: `zer0pa-biomolecular-explorer`
- Pipeline Code: `src/zer0pa_biomolecular_explorer/`

Keep blockers and non-claims.

Keep exactly four Key Metrics rows.

Keep no more than six Proof Anchors.

Every Proof Anchor path must resolve on GitHub main after push.

### 8.5 Update Agent Docs and PRDs

Update current operational docs so the next agent does not restart with old identity:

- `PRD.md`
- `PATHWAY1_PRD.md`
- `HANDOFF-TO-ORCHESTRATOR.md`
- `HANDOFF-TO-OVERNIGHT-EXECUTOR.md`
- `ORCHESTRATOR-STARTUP-PROMPT.md`
- `OVERNIGHT-EXECUTOR-STARTUP-PROMPT.md`
- `MODUS-OPERANDI.md` only where it identifies this repo instance
- `docs/H100_COMPLETION_PLAN.md`
- `docs/RUNPOD_READINESS.md`
- `docs/runpod-migration.md`
- `docs/CONVENTIONS.md`
- `docs/DECISIONS.md`
- `docs/execution-report.md`

Do not sanitize away historical decision content if the historical content needs the old name for provenance. If a historical line remains, label it historical and make current command/repo identity unambiguous.

### 8.6 Update Schemas, Fixtures, Scripts, Tests

Update:

- schema titles from `Zer0pa Health ...` to `Zer0pa Bio-Molecular Explorer ...`,
- script imports,
- test imports,
- test command strings,
- path assertions,
- docs links inside execution reports,
- package name references in tests.

### 8.7 Search Until Clean

After the mechanical pass, run:

```bash
rg -n "Zer0pa Health|\\bHealth\\b|zer0pa-health|zer0pa_health|Zer0pa/Health|github.com/Zer0pa/Health" .
```

Allowed residuals only:

- the hard boundary word "health" if used generically in inherited source material,
- third-party proper names such as "Health AI Developer Foundations",
- historical notes explicitly marked historical,
- old local fallback paths if they are unavoidable and labeled as historical/local-only.

Disallowed residuals:

- README identity table says `Health`,
- repo URL still says `Zer0pa/Health`,
- current startup prompt tells an agent to clone `Zer0pa/Health`,
- `pyproject.toml` contains `zer0pa-health`,
- code imports `zer0pa_health`,
- tests import or monkeypatch `zer0pa_health`,
- CLI docs use `zer0pa-health` as current command.

Also run:

```bash
rg -n "Bio-Molecular Explorer|Bio-Molecular|biomolecular|zer0pa_biomolecular_explorer|zer0pa-biomolecular-explorer" .
```

Use this to confirm the new identity is present across README, docs, package, imports, tests, and CLI references.

## 9. GitHub Repository Rename

Do not change visibility.

After local docs/code are ready and tests pass, rename the repository on GitHub:

```bash
gh repo rename -R Zer0pa/Health Bio-Molecular-Explorer --yes
git remote set-url origin https://github.com/Zer0pa/Bio-Molecular-Explorer.git
gh repo view Zer0pa/Bio-Molecular-Explorer --json nameWithOwner,visibility,defaultBranchRef,url
```

If `gh repo rename` syntax differs in the installed CLI, check `gh repo rename --help` and use the documented equivalent. Do not use the GitHub web UI unless CLI cannot perform the rename.

Expected after rename:

- `nameWithOwner` is `Zer0pa/Bio-Molecular-Explorer`,
- visibility is unchanged from preflight,
- default branch is `main`,
- origin remote points to `https://github.com/Zer0pa/Bio-Molecular-Explorer.git`.

## 10. Verification Commands

The rename is not complete until all of these pass.

### 10.1 Static Checks

```bash
git diff --check
python3 - <<'PY'
from pathlib import Path
text = Path("README.md").read_text()
lead = next(line for line in text.splitlines() if line.startswith("> "))
words = len(lead[2:].replace(".", " ").replace(",", " ").split())
required = [
    "## What This Is",
    "## Pipeline Mechanics",
    "## Key Metrics",
    "## Repo Identity",
    "## Readiness",
    "## What We Prove",
    "## What We Don't Claim",
    "## Verification Status",
    "## Proof Anchors",
    "## Repo Shape",
]
assert words <= 30, words
for heading in required:
    assert heading in text, heading
assert "Research use only. Not for diagnosis, treatment, cure claims, prescribing, clinical deployment, regulatory compliance, or drug-safety certification. Every artifact you produce carries this boundary verbatim." in text

def table_rows(section: str) -> int:
    start = text.index(section)
    rest = text[start:]
    end = rest.find("\n## ", 1)
    body = rest if end == -1 else rest[:end]
    rows = [line for line in body.splitlines() if line.startswith("| ") and "---" not in line]
    return max(0, len(rows) - 1)

assert table_rows("## Key Metrics") == 4, table_rows("## Key Metrics")
assert table_rows("## Proof Anchors") <= 6, table_rows("## Proof Anchors")
print("README structure PASS")
PY
```

### 10.2 Import and CLI Checks

Use a fresh virtual environment if possible:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[test]"
.venv/bin/python - <<'PY'
import zer0pa_biomolecular_explorer
print(zer0pa_biomolecular_explorer.__name__)
PY
.venv/bin/zer0pa-biomolecular-explorer --help
.venv/bin/zer0pa-biomolecular-explorer health-check
.venv/bin/zer0pa-biomolecular-explorer runpod-precheck
```

Do not call the old CLI. The old CLI must not exist in the new install.

### 10.3 Full Test Suite

```bash
.venv/bin/python -m pytest -q
```

All tests must pass. If tests fail from rename fallout, fix them. Do not mark known failures as acceptable unless unrelated infrastructure is missing and the failure is documented with exact cause.

### 10.4 Current-Command Smoke

Run at least:

```bash
.venv/bin/python -m zer0pa_biomolecular_explorer.cli health-check
.venv/bin/python -m zer0pa_biomolecular_explorer.cli runpod-precheck
```

If time permits and local machine can handle it:

```bash
.venv/bin/python -m zer0pa_biomolecular_explorer.cli cutover-dryrun --layer all+p1 --runtime .runtime-rename-cutover
```

Remove generated runtime folders before commit unless they are intentionally tracked artifacts.

## 11. Commit And Push

After tests pass:

```bash
git status --short
git add -A
git commit -m "Rename Health to Bio-Molecular Explorer"
git push origin main
```

If repository rename must happen before push because origin changed, do the GitHub rename, update `origin`, then push.

Do not split into many commits unless a failure forces it. The final history should make the rename easy to audit.

## 12. Remote Verification

After push, re-read GitHub main. This is mandatory.

Commands:

```bash
git status --short --branch
git rev-parse HEAD
gh repo view Zer0pa/Bio-Molecular-Explorer --json nameWithOwner,visibility,defaultBranchRef,url
gh api repos/Zer0pa/Bio-Molecular-Explorer/commits/main --jq '.sha'
gh api repos/Zer0pa/Bio-Molecular-Explorer/readme --jq '.sha'
gh api repos/Zer0pa/Bio-Molecular-Explorer/readme --jq .content | base64 -d | sed -n '1,140p'
```

Then verify README proof anchors on GitHub main. For each README Proof Anchor path, use:

```bash
gh api repos/Zer0pa/Bio-Molecular-Explorer/contents/<PATH>?ref=main --jq '.path'
```

All anchors must resolve.

## 13. Final Report Requirements

The final report to the user must include:

- boundary verbatim,
- old repo name,
- new repo name,
- GitHub URL,
- visibility after rename,
- local head SHA,
- GitHub main head SHA,
- README blob SHA,
- test command and result,
- search residual summary for old identity,
- any allowed historical residuals,
- statement that no compatibility alias remains for `zer0pa-health` / `zer0pa_health`,
- exact blocker posture preserved.

Do not declare done without the GitHub main head SHA and README blob SHA.

## 14. Failure Modes

Stop and report a blocker only for these cases:

- GitHub authentication lacks permission to rename the repo.
- GitHub API is unavailable after repeated attempts.
- Tests expose a real non-rename behavioral failure that cannot be fixed without changing scientific behavior.
- The working tree has user changes that would be overwritten.
- The repo is not the expected repository.

Do not stop for:

- many import errors,
- many docs references,
- failing tests caused by old module paths,
- search results showing old names,
- CLI entry point fallout.

Those are the task.

## 15. Anti-Shortcut Rules

The executing agent must not:

- only rename the README,
- leave `pyproject.toml` as `zer0pa-health`,
- leave `src/zer0pa_health/` in place,
- leave tests importing `zer0pa_health`,
- leave `zer0pa-health` as a current CLI,
- leave current startup prompts cloning `Zer0pa/Health`,
- hide blockers to make the renamed repo look more complete,
- change visibility,
- add clinical/regulatory readiness language,
- use broad destructive git commands,
- revert unrelated user changes.

The executing agent must:

- perform a real package/module/CLI/doc/repo rename,
- run the full test suite,
- push to GitHub main,
- re-read GitHub main,
- report exact SHAs.
