-- The email transport was implemented on the runner and rejected by the hosted
-- table. contracts/notification.py's TransportName has always listed 'email',
-- senders/email.py sends through Resend, and senders/deliver.py routes to it,
-- but this check constraint predates all three, so declaring an email channel
-- failed with a constraint violation that named no cause. Widen the constraint
-- rather than narrow TransportName: the sender works, it is the table that is
-- behind. No new column, so the hosted boundary allowlist is unchanged.

alter table notification_channels
  drop constraint notification_channels_transport_check;

alter table notification_channels
  add constraint notification_channels_transport_check
  check (transport in ('slack', 'telegram', 'discord', 'email'));
