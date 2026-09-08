"""Outbound notification senders. Runner-side URLs and keys only."""

from pr_reviewer.notifications.senders.deliver import deliver_notifications
from pr_reviewer.notifications.senders.endpoints import ChannelEndpoint

__all__ = ["ChannelEndpoint", "deliver_notifications"]
