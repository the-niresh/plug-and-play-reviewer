## Summary

What changed, in plain English.

## Red proof

Paste the failure text you saw before the fix:

```text

```

## Checks

Run these on the files you changed:

```bash
uv run ruff check <files>
uv run mypy src
flock -w 1800 /tmp/pr-reviewer-pytest.lock uv run pytest -q
```

- ruff:
- mypy:
- pytest:

## Data-boundary impact

Does this change what the hosted plane stores or what crosses the runner or hosted
split? See [docs/DATA_BOUNDARIES.md](docs/DATA_BOUNDARIES.md).

- [ ] No hosted schema or boundary change
- [ ] Hosted allowlist or `control_plane/boundary.py` changed (say which columns and why)
- [ ] Runner-only change (source, diffs, or model keys stay local)

If you checked the second box, say how you verified `tests/test_hosted_boundary_enforcement.py`
still passes.
