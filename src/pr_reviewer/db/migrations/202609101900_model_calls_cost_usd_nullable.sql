-- Unpriced models record tokens without inventing a cost. NULL passes check (cost_usd >= 0).
alter table model_calls
  alter column cost_usd drop not null;
