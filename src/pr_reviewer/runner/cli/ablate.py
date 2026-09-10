"""`reviewer ablate` -- run a retrieval ablation over the frozen holdout."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import TextIO

from pr_reviewer.agent_surfaces.backend import resolve_model_provider
from pr_reviewer.evals.run_eval import (
    format_retrieval_ablation,
    load_public_eval_cases,
    run_retrieval_ablation,
)
from pr_reviewer.retrieval.embed import EmbeddingCostLedger
from pr_reviewer.runner.eval_ablation import (
    OFFLINE_EMBEDDINGS_WARNING,
    EvalAblationConfigurationError,
    EvalAblationDependencies,
    EvalRepositoryCache,
    build_eval_ablation_reviewers,
    estimate_ablation_cost_usd,
    format_ablation_cost_summary,
    local_retrieval_connection,
    resolve_eval_embedder,
)

DEFAULT_CACHE = Path.home() / ".cache" / "pr-reviewer" / "eval-repos"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reviewer ablate",
        description="Run a retrieval ablation over the frozen holdout.",
    )
    parser.add_argument("--cases", type=Path, default=None, help="eval_cases.jsonl path")
    parser.add_argument("--repeats", type=int, default=1, help="repeats per arm (default 1)")
    parser.add_argument(
        "--json", action="store_true", help="skip cost confirmation and print JSON"
    )
    parser.add_argument(
        "--cache-dir", type=Path, default=DEFAULT_CACHE, help="repository clone cache"
    )
    parser.add_argument(
        "--offline-embeddings",
        action="store_true",
        help="use deterministic hash embeddings for wiring smoke tests only",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    in_stream = stdin if stdin is not None else sys.stdin
    out = stdout if stdout is not None else sys.stdout
    err = stderr if stderr is not None else sys.stderr
    args = list(sys.argv[1:] if argv is None else argv)
    parser = _build_parser()
    if args and args[0] in {"-h", "--help"}:
        print(parser.format_help(), file=out, end="")
        return 0
    namespace = parser.parse_args(args)

    if namespace.offline_embeddings:
        print(OFFLINE_EMBEDDINGS_WARNING, file=err)
        return 2

    provider_choice = resolve_model_provider()
    if provider_choice is None:
        print("No model provider configured. Run reviewer setup, then retry.", file=err)
        return 2
    provider_name, model = provider_choice
    from pr_reviewer.models.catalogue import default_model_for

    model_name = default_model_for(provider_name)
    cases = load_public_eval_cases(namespace.cases)
    holdout = [case for case in cases if case.split == "holdout"]
    if not holdout:
        print("Holdout is empty; nothing to ablate.", file=err)
        return 2

    try:
        embedding_ledger = EmbeddingCostLedger()
        embedder, _offline = resolve_eval_embedder(
            offline=False,
            ledger=embedding_ledger,
        )
    except EvalAblationConfigurationError as exc:
        print(str(exc), file=err)
        return 2

    estimated = estimate_ablation_cost_usd(
        cases,
        model_name,
        repeats=namespace.repeats,
        offline_embeddings=False,
        cache_root=namespace.cache_dir,
    )
    if not namespace.json:
        print(
            f"Estimated cost: ${estimated:.4f} for {len(holdout)} holdout cases, "
            f"2 arms, {namespace.repeats} repeat(s), including embeddings.",
            file=err,
        )
        answer = in_stream.readline().strip().lower()
        if answer not in {"y", "yes"}:
            print("Cancelled.", file=err)
            return 2

    with local_retrieval_connection() as conn:
        deps = EvalAblationDependencies(
            model=model,
            model_name=model_name,
            conn=conn,
            repo_cache=EvalRepositoryCache(namespace.cache_dir),
            embedder=embedder,
            embedding_ledger=embedding_ledger,
            offline_embeddings=False,
        )
        diff_only, retrieval_backed = build_eval_ablation_reviewers(deps)
        result = run_retrieval_ablation(
            cases,
            diff_only,
            retrieval_backed,
            repeats=namespace.repeats,
        )

    model_cost = Decimal(str(result.diff_only.metrics.cost_usd)) + Decimal(
        str(result.retrieval_backed.metrics.cost_usd)
    )
    cost_summary = format_ablation_cost_summary(
        model_cost_usd=model_cost,
        embedding_cost_usd=embedding_ledger.total_cost_usd,
    )
    text = format_retrieval_ablation(result)
    if namespace.json:
        payload = result.model_dump()
        payload["cost_summary"] = {
            "model_cost_usd": float(model_cost),
            "embedding_cost_usd": float(embedding_ledger.total_cost_usd),
            "total_cost_usd": float(model_cost + embedding_ledger.total_cost_usd),
        }
        print(json.dumps(payload, indent=2), file=out)
    else:
        print(text, file=out)
        print(cost_summary, file=out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
