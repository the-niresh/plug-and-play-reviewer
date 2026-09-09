"""Read hosted feedback rows and build human-reviewable improvement reports."""

from __future__ import annotations

import uuid
from typing import cast

from psycopg import Connection

from pr_reviewer.db.client import Row, connection
from pr_reviewer.evals.feedback_to_evals import (
    FeedbackClassification,
    FeedbackImprovementReport,
    ReviewCommentFeedbackRow,
    build_feedback_improvement_report,
    format_feedback_improvement_report,
)


def _review_job_id_from_finding_id(finding_id: str | None) -> str | None:
    if finding_id is None or ":" not in finding_id:
        return None
    prefix = finding_id.rsplit(":", 1)[0]
    try:
        uuid.UUID(prefix)
    except ValueError:
        return None
    return prefix


def _pull_request_numbers_by_job_id(
    conn: Connection[Row], job_ids: set[str]
) -> dict[str, int | None]:
    if not job_ids:
        return {}
    rows = conn.execute(
        """
        select id::text as id, pull_request_number
        from review_jobs
        where id = any(%s::uuid[])
        """,
        (list(job_ids),),
    ).fetchall()
    return {str(row["id"]): row["pull_request_number"] for row in rows}


def load_review_comment_feedback_rows() -> tuple[ReviewCommentFeedbackRow, ...]:
    with connection() as conn:
        rows = conn.execute(
            """
            select
              id::text as id,
              installation_id,
              github_repository_id,
              github_comment_id,
              in_reply_to_comment_id,
              finding_id,
              classification,
              reply_text,
              created_at
            from review_comment_feedback
            order by created_at, id
            """
        ).fetchall()
        job_ids = {
            job_id
            for row in rows
            if (job_id := _review_job_id_from_finding_id(row["finding_id"])) is not None
        }
        pr_by_job = _pull_request_numbers_by_job_id(conn, job_ids)

    loaded: list[ReviewCommentFeedbackRow] = []
    for row in rows:
        job_id = _review_job_id_from_finding_id(row["finding_id"])
        pull_request_number = pr_by_job.get(job_id) if job_id is not None else None
        loaded.append(
            ReviewCommentFeedbackRow(
                id=str(row["id"]),
                installation_id=int(row["installation_id"]),
                github_repository_id=int(row["github_repository_id"]),
                pull_request_number=pull_request_number,
                github_comment_id=int(row["github_comment_id"]),
                in_reply_to_comment_id=int(row["in_reply_to_comment_id"]),
                finding_id=row["finding_id"],
                classification=cast(FeedbackClassification, row["classification"]),
                reply_text=str(row["reply_text"]),
                created_at=row["created_at"],
            )
        )
    return tuple(loaded)


def build_feedback_improvement_report_from_hosted() -> FeedbackImprovementReport:
    return build_feedback_improvement_report(load_review_comment_feedback_rows())


def render_feedback_improvement_report(report: FeedbackImprovementReport) -> str:
    return format_feedback_improvement_report(report)
