-- Free mode is the default product tier: one GitHub user and one repository per installation.
-- Team tier exists for a future paid path; nothing in this migration turns billing on.

alter table installations
  add column access_tier text not null default 'free'
  check (access_tier in ('free', 'team'));
