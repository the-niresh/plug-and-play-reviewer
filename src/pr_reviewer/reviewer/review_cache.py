"""Local per-PR review cache. Finding text stays on the runner, never on Neon."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from pr_reviewer.contracts.finding_candidate import FindingCandidate
from pr_reviewer.github.pull_request import PullRequestFile, PullRequestSnapshot
from pr_reviewer.local_store.sqlite import LocalStore
from pr_reviewer.reviewer.hunk_format import split_patch_hunks


@dataclass(frozen=True)
class ReviewedHunk:
    file_path: str
    line_start: int
    line_end: int
    content_hash: str


@dataclass(frozen=True)
class CachedFinding:
    finding_id: str
    file_path: str
    line_start: int
    line_end: int
    title: str
    rationale: str
    concern: str
    severity: str
    category: str
    evidence: tuple[str, ...]
    confidence: float

    def to_candidate(self) -> FindingCandidate:
        return FindingCandidate(
            concern=self.concern,  # type: ignore[arg-type]
            severity=self.severity,  # type: ignore[arg-type]
            category=self.category,
            file_path=self.file_path,
            line_start=self.line_start,
            line_end=self.line_end,
            title=self.title,
            rationale=self.rationale,
            evidence=list(self.evidence),
            confidence=self.confidence,
        )


@dataclass(frozen=True)
class ReviewCacheRecord:
    installation_id: int
    repository_id: int
    pull_request_number: int
    head_sha: str
    reviewed_files: tuple[str, ...]
    reviewed_hunks: tuple[ReviewedHunk, ...]
    findings: tuple[CachedFinding, ...]
    cost_usd: Decimal


class ReviewCacheStore(Protocol):
    def load_previous(
        self, installation_id: int, repository_id: int, pull_request_number: int
    ) -> ReviewCacheRecord | None: ...

    def save(self, record: ReviewCacheRecord) -> None: ...


class MemoryReviewCache:
    def __init__(self) -> None:
        self._latest: dict[tuple[int, int, int], ReviewCacheRecord] = {}

    def load_previous(
        self, installation_id: int, repository_id: int, pull_request_number: int
    ) -> ReviewCacheRecord | None:
        return self._latest.get((installation_id, repository_id, pull_request_number))

    def save(self, record: ReviewCacheRecord) -> None:
        self._latest[
            (record.installation_id, record.repository_id, record.pull_request_number)
        ] = record


class LocalReviewCache:
    def __init__(self, store: LocalStore) -> None:
        self._store = store

    def load_previous(
        self, installation_id: int, repository_id: int, pull_request_number: int
    ) -> ReviewCacheRecord | None:
        row = self._store.connection.execute(
            """
            select head_sha, cost_usd
            from review_cache_heads
            where installation_id = ?
              and repository_id = ?
              and pull_request_number = ?
            order by created_at desc
            limit 1
            """,
            (installation_id, repository_id, pull_request_number),
        ).fetchone()
        if row is None:
            return None
        head_sha = str(row["head_sha"])
        files = tuple(
            str(item["file_path"])
            for item in self._store.connection.execute(
                """
                select file_path from review_cache_files
                where installation_id = ? and repository_id = ?
                  and pull_request_number = ? and head_sha = ?
                order by file_path
                """,
                (installation_id, repository_id, pull_request_number, head_sha),
            )
        )
        hunks = tuple(
            ReviewedHunk(
                file_path=str(item["file_path"]),
                line_start=int(item["line_start"]),
                line_end=int(item["line_end"]),
                content_hash=str(item["content_hash"]),
            )
            for item in self._store.connection.execute(
                """
                select file_path, line_start, line_end, content_hash
                from review_cache_hunks
                where installation_id = ? and repository_id = ?
                  and pull_request_number = ? and head_sha = ?
                """,
                (installation_id, repository_id, pull_request_number, head_sha),
            )
        )
        findings = tuple(
            CachedFinding(
                finding_id=str(item["finding_id"]),
                file_path=str(item["file_path"]),
                line_start=int(item["line_start"]),
                line_end=int(item["line_end"]),
                title=str(item["title"]),
                rationale=str(item["rationale"]),
                concern=str(item["concern"]),
                severity=str(item["severity"]),
                category=str(item["category"]),
                evidence=tuple(json.loads(str(item["evidence_json"]))),
                confidence=float(item["confidence"]),
            )
            for item in self._store.connection.execute(
                """
                select finding_id, file_path, line_start, line_end, title, rationale,
                       concern, severity, category, evidence_json, confidence
                from review_cache_findings
                where installation_id = ? and repository_id = ?
                  and pull_request_number = ? and head_sha = ?
                """,
                (installation_id, repository_id, pull_request_number, head_sha),
            )
        )
        return ReviewCacheRecord(
            installation_id=installation_id,
            repository_id=repository_id,
            pull_request_number=pull_request_number,
            head_sha=head_sha,
            reviewed_files=files,
            reviewed_hunks=hunks,
            findings=findings,
            cost_usd=Decimal(str(row["cost_usd"])),
        )

    def save(self, record: ReviewCacheRecord) -> None:
        conn = self._store.connection
        conn.execute(
            """
            insert or replace into review_cache_heads (
              installation_id, repository_id, pull_request_number, head_sha, cost_usd
            )
            values (?, ?, ?, ?, ?)
            """,
            (
                record.installation_id,
                record.repository_id,
                record.pull_request_number,
                record.head_sha,
                str(record.cost_usd),
            ),
        )
        key = (
            record.installation_id,
            record.repository_id,
            record.pull_request_number,
            record.head_sha,
        )
        conn.execute(
            """
            delete from review_cache_files
            where installation_id = ? and repository_id = ?
              and pull_request_number = ? and head_sha = ?
            """,
            key,
        )
        conn.execute(
            """
            delete from review_cache_hunks
            where installation_id = ? and repository_id = ?
              and pull_request_number = ? and head_sha = ?
            """,
            key,
        )
        conn.execute(
            """
            delete from review_cache_findings
            where installation_id = ? and repository_id = ?
              and pull_request_number = ? and head_sha = ?
            """,
            key,
        )
        for path in record.reviewed_files:
            conn.execute(
                """
                insert into review_cache_files (
                  installation_id, repository_id, pull_request_number, head_sha, file_path
                )
                values (?, ?, ?, ?, ?)
                """,
                (*key, path),
            )
        for hunk in record.reviewed_hunks:
            conn.execute(
                """
                insert into review_cache_hunks (
                  installation_id, repository_id, pull_request_number, head_sha,
                  file_path, line_start, line_end, content_hash
                )
                values (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (*key, hunk.file_path, hunk.line_start, hunk.line_end, hunk.content_hash),
            )
        for finding in record.findings:
            conn.execute(
                """
                insert into review_cache_findings (
                  installation_id, repository_id, pull_request_number, head_sha,
                  finding_id, file_path, line_start, line_end, title, rationale,
                  concern, severity, category, evidence_json, confidence
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    *key,
                    finding.finding_id,
                    finding.file_path,
                    finding.line_start,
                    finding.line_end,
                    finding.title,
                    finding.rationale,
                    finding.concern,
                    finding.severity,
                    finding.category,
                    json.dumps(list(finding.evidence)),
                    finding.confidence,
                ),
            )
        conn.commit()


def hunks_from_file(file: PullRequestFile) -> tuple[ReviewedHunk, ...]:
    if not file.patch:
        return ()
    hunks: list[ReviewedHunk] = []
    for hunk in split_patch_hunks(file.patch):
        digest = hashlib.sha256(hunk.text.encode("utf-8")).hexdigest()
        hunks.append(
            ReviewedHunk(
                file_path=file.path,
                line_start=hunk.new_start,
                line_end=hunk.new_end,
                content_hash=digest,
            )
        )
    return tuple(hunks)


def hunks_from_snapshot(snapshot: PullRequestSnapshot) -> tuple[ReviewedHunk, ...]:
    hunks: list[ReviewedHunk] = []
    for file in snapshot.files:
        hunks.extend(hunks_from_file(file))
    return tuple(hunks)


def finding_id_for(candidate: FindingCandidate) -> str:
    raw = f"{candidate.file_path}:{candidate.line_start}:{candidate.line_end}:{candidate.title}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def cached_from_candidate(candidate: FindingCandidate) -> CachedFinding:
    return CachedFinding(
        finding_id=finding_id_for(candidate),
        file_path=candidate.file_path,
        line_start=candidate.line_start,
        line_end=candidate.line_end,
        title=candidate.title,
        rationale=candidate.rationale,
        concern=candidate.concern,
        severity=candidate.severity,
        category=candidate.category,
        evidence=tuple(candidate.evidence),
        confidence=candidate.confidence,
    )


def record_from_review(
    *,
    installation_id: int,
    repository_id: int,
    snapshot: PullRequestSnapshot,
    findings: Sequence[FindingCandidate],
    cost_usd: Decimal,
) -> ReviewCacheRecord:
    return ReviewCacheRecord(
        installation_id=installation_id,
        repository_id=repository_id,
        pull_request_number=snapshot.number,
        head_sha=snapshot.head_sha,
        reviewed_files=tuple(file.path for file in snapshot.files),
        reviewed_hunks=hunks_from_snapshot(snapshot),
        findings=tuple(cached_from_candidate(item) for item in findings),
        cost_usd=cost_usd,
    )


def seed_cache(
    cache: ReviewCacheStore,
    *,
    installation_id: int,
    repository_id: int,
    pull_request_number: int,
    head_sha: str,
    files: Sequence[PullRequestFile],
    findings: Sequence[FindingCandidate],
) -> None:
    snapshot = PullRequestSnapshot(
        repo_owner="acme",
        repo_name="widgets",
        number=pull_request_number,
        base_sha="a" * 40,
        head_sha=head_sha,
        title="seed",
        body="",
        files=list(files),
    )
    cache.save(
        record_from_review(
            installation_id=installation_id,
            repository_id=repository_id,
            snapshot=snapshot,
            findings=findings,
            cost_usd=Decimal("0"),
        )
    )
