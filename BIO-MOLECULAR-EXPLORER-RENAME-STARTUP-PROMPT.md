# Bio-Molecular Explorer Rename Startup Prompt

Research use only. Not for diagnosis, treatment, cure claims, prescribing, clinical deployment, regulatory compliance, or drug-safety certification. Every artifact you produce carries this boundary verbatim.

You are the rename executor for the Zer0pa repository currently named `Zer0pa/Health`.

Your task is to execute the clean pre-public rename to **Bio-Molecular Explorer** end to end. You have zero permission to do a partial rename. You must follow `docs/BIO_MOLECULAR_EXPLORER_RENAME_PRD.md` meticulously.

Hard target identifiers:

- GitHub repo: `Zer0pa/Bio-Molecular-Explorer`
- Public title: `Zer0pa Bio-Molecular Explorer`
- Short identifier: `Bio-Molecular Explorer`
- Python distribution: `zer0pa-biomolecular-explorer`
- Python import package: `zer0pa_biomolecular_explorer`
- Primary CLI: `zer0pa-biomolecular-explorer`
- L1 stub CLI: `zer0pa-biomolecular-l1-stub`

Hard constraints:

- Do not change repository visibility.
- Preserve the hard research boundary verbatim.
- Preserve all blocker and non-claim language.
- Do not create compatibility aliases for `zer0pa-health` or `zer0pa_health`.
- Do not stop after docs-only changes.
- Do not ask the user for incremental permission unless GitHub permissions or user-owned uncommitted changes block you.
- Do not report completion until GitHub main is pushed and re-read.

Start by cloning or fetching the current repo:

```bash
git clone https://github.com/Zer0pa/Health.git
cd Health
git fetch origin main
git checkout main
git pull --ff-only origin main
```

Then read:

1. `docs/BIO_MOLECULAR_EXPLORER_RENAME_PRD.md`
2. `README.md`
3. `pyproject.toml`
4. `PRD.md`
5. `docs/H100_COMPLETION_PLAN.md`
6. `docs/RUNPOD_READINESS.md`

Execute the PRD exactly:

1. Preflight repo, visibility, branch, and clean worktree.
2. Rename `src/zer0pa_health/` to `src/zer0pa_biomolecular_explorer/`.
3. Update every import, monkeypatch string, CLI command, package name, repo URL, startup prompt, agent handoff, schema title, and current docs reference.
4. Rename GitHub repo to `Bio-Molecular-Explorer` using `gh repo rename`, preserving visibility.
5. Update `origin` to `https://github.com/Zer0pa/Bio-Molecular-Explorer.git`.
6. Run static checks, README structure check, import checks, CLI checks, and full `pytest -q`.
7. Push to GitHub main.
8. Re-read GitHub main and README through `gh api`.
9. Verify README Proof Anchor paths resolve on GitHub main.
10. Report final local head SHA, GitHub main head SHA, README blob SHA, test result, and residual old-identity search summary.

You are done only when the clean rename is live on GitHub main and verified remotely.

