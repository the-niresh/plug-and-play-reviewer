-- Runner presence for the hosted dashboard. Updated on each job claim and job heartbeat.

alter table runners
  add column last_heartbeat_at timestamptz;
