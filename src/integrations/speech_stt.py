from __future__ import annotations

from dataclasses import dataclass

from src.domain.models import RecordingAsset, Transcript


class SpeechToText:
    def transcribe(self, recording: RecordingAsset) -> Transcript:
        raise NotImplementedError


@dataclass(slots=True)
class MockSpeechToText(SpeechToText):
    """Foundation stub for T-022 handoff."""

    diarization_enabled: bool = True

    def transcribe(self, recording: RecordingAsset) -> Transcript:
        _ = recording
        text = "올해 상반기 전사 LLM 토큰 사용량과 비용을 팀별로 정리해 주세요."
        segments = [{"speaker": "S1" if self.diarization_enabled else None, "text": text, "offset": 0.0}]
        return Transcript(text=text, segments=segments)
