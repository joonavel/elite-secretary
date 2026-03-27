from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import azure.cognitiveservices.speech as speechsdk

from src.domain.errors import ErrorCode, PipelineError
from src.domain.models import RecordingAsset, Transcript


logger = logging.getLogger(__name__)


class SpeechToText:
    def transcribe(self, recording: RecordingAsset) -> Transcript:
        raise NotImplementedError


@dataclass(slots=True)
class AzureSpeechFileInputSTT(SpeechToText):
    speech_key: str
    speech_region: str
    language: str = "ko-KR"
    phrase_list: tuple[str, ...] = ()
    diarization_enabled: bool = True

    def transcribe(self, recording: RecordingAsset) -> Transcript:
        source_path = Path(recording.file_path)
        if not source_path.exists():
            raise PipelineError(
                code=ErrorCode.STT_FAILED,
                message=f"T-022 recording not found: {source_path}",
                recoverable=False,
                step="T-022_STT",
            )
        if not self.speech_key or not self.speech_region:
            raise PipelineError(
                code=ErrorCode.CONFIG_MISSING,
                message="T-022 requires AZURE_SPEECH_KEY and AZURE_SPEECH_REGION",
                recoverable=False,
                step="T-022_STT",
            )

        speech_config = speechsdk.SpeechConfig(subscription=self.speech_key, region=self.speech_region)
        speech_config.speech_recognition_language = self.language
        if self.diarization_enabled:
            self._try_enable_diarization(speech_config)

        audio_config = speechsdk.audio.AudioConfig(filename=str(source_path))
        recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
        phrase_list_grammar = speechsdk.PhraseListGrammar.from_recognizer(recognizer)
        for phrase in self.phrase_list:
            phrase_list_grammar.addPhrase(phrase)

        segments: list[dict[str, Any]] = []
        full_text_parts: list[str] = []
        canceled: dict[str, Any] | None = None
        done = {"finished": False}

        def _recognized(evt: speechsdk.SpeechRecognitionEventArgs) -> None:
            result = evt.result
            if result.reason != speechsdk.ResultReason.RecognizedSpeech:
                return
            text = (result.text or "").strip()
            if not text:
                return
            speaker = None
            if hasattr(result, "speaker_id"):
                speaker = getattr(result, "speaker_id")
            segments.append(
                {
                    "speaker": speaker,
                    "text": text,
                    "offset": float(result.offset) / 10_000_000.0,
                    "duration": float(result.duration) / 10_000_000.0,
                }
            )
            full_text_parts.append(text)

        def _session_stopped(_: Any) -> None:
            done["finished"] = True

        def _canceled(evt: speechsdk.SpeechRecognitionCanceledEventArgs) -> None:
            nonlocal canceled
            details = speechsdk.CancellationDetails(evt.result)
            canceled = {
                "reason": str(details.reason),
                "error_details": details.error_details,
            }
            done["finished"] = True

        recognizer.recognized.connect(_recognized)
        recognizer.session_stopped.connect(_session_stopped)
        recognizer.canceled.connect(_canceled)

        recognizer.start_continuous_recognition()
        while not done["finished"]:
            time.sleep(0.1)
        recognizer.stop_continuous_recognition()

        if canceled:
            raise PipelineError(
                code=ErrorCode.STT_FAILED,
                message=f"T-022 speech recognition canceled: {json.dumps(canceled, ensure_ascii=True)}",
                recoverable=False,
                step="T-022_STT",
            )

        return Transcript(text=" ".join(full_text_parts).strip(), segments=segments)

    def export_transcript(self, transcript: Transcript, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"text": transcript.text, "segments": transcript.segments}
        output_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    def _try_enable_diarization(self, speech_config: speechsdk.SpeechConfig) -> None:
        try:
            speech_config.set_property(
                speechsdk.PropertyId.SpeechServiceResponse_RequestWordLevelTimestamps,
                "true",
            )
            # ConversationTranscriber 기반 화자 분리 확장 속성(런타임 지원 여부에 따라 동작).
            speech_config.set_service_property(
                name="diarizationEnabled",
                value="true",
                channel=speechsdk.ServicePropertyChannel.UriQueryParameter,
            )
        except Exception as error:
            logger.warning(
                "T-022 diarization fallback (%s): diarization config failed, continuing STT",
                ErrorCode.STT_DIARIZATION_FALLBACK.value,
                exc_info=error,
            )


@dataclass(slots=True)
class MockSpeechToText(SpeechToText):
    diarization_enabled: bool = True

    def transcribe(self, recording: RecordingAsset) -> Transcript:
        _ = recording
        text = "올해 상반기 전사 LLM 토큰 사용량과 비용을 팀별로 정리해 주세요."
        segments = [{"speaker": "S1" if self.diarization_enabled else None, "text": text, "offset": 0.0}]
        return Transcript(text=text, segments=segments)
