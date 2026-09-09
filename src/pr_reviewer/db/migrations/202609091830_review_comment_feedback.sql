-- Feedback capture for human replies to our posted PR review comments.
-- This is not self-improvement: nothing in this schema is read by prompt
-- registry, eval labels, or model settings.

create table review_comment_posts (
  installation_id bigint not null references installations(id),
  github_repository_id bigint not null,
  github_comment_id bigint not null,
  finding_id text,
  created_at timestamptz not null default now(),
  primary key (installation_id, github_repository_id, github_comment_id)
);

create table review_comment_feedback (
  id uuid primary key default gen_random_uuid(),
  delivery_id text not null references github_deliveries(id),
  installation_id bigint not null references installations(id),
  github_repository_id bigint not null,
  github_comment_id bigint not null,
  in_reply_to_comment_id bigint not null,
  finding_id text,
  classification text not null check (
    classification in ('useful', 'wrong', 'unclear', 'follow_up', 'unknown')
  ),
  reply_text text not null,
  created_at timestamptz not null default now(),
  unique (delivery_id),
  unique (installation_id, github_repository_id, github_comment_id)
);

create index review_comment_feedback_parent_idx
  on review_comment_feedback (installation_id, github_repository_id, in_reply_to_comment_id);

create trigger review_comment_posts_append_only
before update or delete on review_comment_posts
for each row execute function reject_append_only_mutation();

create trigger review_comment_feedback_append_only
before update or delete on review_comment_feedback
for each row execute function reject_append_only_mutation();
