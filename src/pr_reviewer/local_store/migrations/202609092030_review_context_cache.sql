-- Incremental review cache. Lives only on the runner. Source, diffs, embeddings,
-- evidence hunks, and model keys are not stored here: hunks are content hashes
-- and line ranges, findings are local title/rationale already produced by a review.

create table review_cache_heads (
  installation_id integer not null,
  repository_id integer not null,
  pull_request_number integer not null,
  head_sha text not null,
  cost_usd text not null,
  created_at text not null default (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  primary key (installation_id, repository_id, pull_request_number, head_sha)
);

create table review_cache_files (
  installation_id integer not null,
  repository_id integer not null,
  pull_request_number integer not null,
  head_sha text not null,
  file_path text not null,
  primary key (installation_id, repository_id, pull_request_number, head_sha, file_path),
  foreign key (installation_id, repository_id, pull_request_number, head_sha)
    references review_cache_heads (installation_id, repository_id, pull_request_number, head_sha)
);

create table review_cache_hunks (
  installation_id integer not null,
  repository_id integer not null,
  pull_request_number integer not null,
  head_sha text not null,
  file_path text not null,
  line_start integer not null,
  line_end integer not null,
  content_hash text not null,
  primary key (
    installation_id, repository_id, pull_request_number, head_sha,
    file_path, line_start, line_end
  ),
  foreign key (installation_id, repository_id, pull_request_number, head_sha)
    references review_cache_heads (installation_id, repository_id, pull_request_number, head_sha)
);

create table review_cache_findings (
  installation_id integer not null,
  repository_id integer not null,
  pull_request_number integer not null,
  head_sha text not null,
  finding_id text not null,
  file_path text not null,
  line_start integer not null,
  line_end integer not null,
  title text not null,
  rationale text not null,
  concern text not null,
  severity text not null,
  category text not null,
  evidence_json text not null,
  confidence real not null,
  primary key (installation_id, repository_id, pull_request_number, head_sha, finding_id),
  foreign key (installation_id, repository_id, pull_request_number, head_sha)
    references review_cache_heads (installation_id, repository_id, pull_request_number, head_sha)
);
