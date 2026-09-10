# Test suite move plan

Baseline: 1598 tests collected, 252 test modules at `tests/test_*.py`.

## Keep at tests root

- `conftest.py` (shared fixtures, autouse DB cleanup)
- `eval_holdout_fixtures.py` (imported as `eval_holdout_fixtures` via pythonpath)
- `repo_paths.py`, `boundary_guards.py` (shared helpers)
- `_move_mapping.json` (this move only; delete before commit)

## Target folders

| Folder | Count | Purpose |
|--------|------:|---------|
| control_plane | 24 | Hosted API, webhooks, dashboard, notifications, jobs |
| docs | 3 | Documentation readability and product polish |
| evals | 12 | Eval runner, holdout, scorecard, regression gate |
| github | 12 | GitHub OAuth, webhooks, PR posting |
| install | 5 | Doctor, installer, local install flows |
| integration | 69 | Cross-cutting CLI, models, jobs, misc |
| release | 6 | Release images, dockerignore, deploy blueprint |
| retrieval | 11 | Embeddings, hybrid search, code graph |
| reviewer | 62 | Review pipeline, TUI, prompts, reflection |
| runner | 20 | Runner daemon, local auth/store, compose |
| security | 7 | Boundaries, supply chain, injection corpus |
| web | 21 | Next.js hosted UI routes and metadata |

## Batches

1. release + docs + install + security (21 files)
2. retrieval + evals (23 files)
3. github + web (33 files)
4. runner + control_plane (44 files)
5. reviewer + integration (131 files)

## Path fixes after each batch

- `Path(__file__).resolve().parent.parent` -> `from repo_paths import REPO_ROOT`
- Update doc references in `docs/FAILED_EXPERIMENTS.md`, `docs/EVALS.md`
- Update catcher paths in `tests/evals/test_failed_experiments.py`
- Update `tests/evals/test_eval_stays_local.py` self-path assertion
- Update `tests/security/test_supply_chain.py` connector path

## Gates (final)

```bash
uv run ruff check tests
uv run mypy src
grep -Pn '[\x{2013}\x{2014}]' tests
flock -w 1800 /tmp/pr-reviewer-pytest.lock uv run pytest -q
```
