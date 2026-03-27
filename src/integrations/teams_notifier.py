from __future__ import annotations

from src.domain.models import MeetingContext, PublishedResult


class TeamsNotifier:
    def notify(self, meeting_context: MeetingContext, published: PublishedResult) -> None:
        raise NotImplementedError


class StubTeamsNotifier(TeamsNotifier):
    def notify(self, meeting_context: MeetingContext, published: PublishedResult) -> None:
        _ = (meeting_context, published)
