from __future__ import annotations

from src.domain.models import ArtifactMetadata, MeetingContext, PublishedResult


class SharePointPublisher:
    def publish(self, meeting_context: MeetingContext, artifacts: list[ArtifactMetadata]) -> PublishedResult:
        raise NotImplementedError


class StubSharePointPublisher(SharePointPublisher):
    def publish(self, meeting_context: MeetingContext, artifacts: list[ArtifactMetadata]) -> PublishedResult:
        _ = meeting_context
        links = [f"local://{artifact.artifact_name}" for artifact in artifacts]
        return PublishedResult(destinations=links)
