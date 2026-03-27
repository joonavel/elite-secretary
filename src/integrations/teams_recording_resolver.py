from __future__ import annotations

from dataclasses import dataclass

from src.domain.models import MeetingContext, RecordingAsset


class RecordingResolver:
    def resolve(self, meeting_context: MeetingContext) -> RecordingAsset:
        raise NotImplementedError


@dataclass(slots=True)
class LocalRecordingResolver(RecordingResolver):
    """MVP resolver used by foundation tasks.

    T-020+ implements real Teams/Graph retrieval.
    """

    def resolve(self, meeting_context: MeetingContext) -> RecordingAsset:
        file_path = meeting_context.local_recording_path or "./artifacts/mock_recording.m4a"
        return RecordingAsset(
            file_path=file_path,
            metadata={"meeting_id": meeting_context.meeting_id, "source": "local"},
        )
