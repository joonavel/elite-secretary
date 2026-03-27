from __future__ import annotations

import unittest
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from src.domain.errors import ErrorCode, PipelineError
from src.domain.models import MeetingContext, RecordingAsset
from src.integrations.audio_preprocessor import PassthroughAudioPreprocessor
from src.integrations.speech_stt import AzureSpeechFileInputSTT
from src.integrations.teams_recording_resolver import TeamsChatRecordingResolver


class _FakeGraphClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def request(self, method: str, path: str, *, payload=None, params=None):  # noqa: ANN001,ANN201
        self.calls.append((method, path))
        if "messages" in path:
            return {
                "value": [
                    {
                        "id": "msg-1",
                        "attachments": [
                            {
                                "id": "att-1",
                                "name": "meeting-recording.m4a",
                                "contentType": "audio/m4a",
                                "contentUrl": "https://graph.microsoft.com/v1.0/chats/chat-1/messages/msg-1/hostedContents/1/$value",
                            }
                        ],
                    }
                ]
            }
        raise AssertionError(f"Unexpected path: {path}")

    def request_bytes(self, path: str, *, params=None):  # noqa: ANN001,ANN201
        self.calls.append(("GET_BYTES", path))
        return b"fake-audio"


class _NoAttachmentGraphClient:
    def request(self, method: str, path: str, *, payload=None, params=None):  # noqa: ANN001,ANN201
        return {"value": [{"id": "msg-1", "attachments": []}]}

    def request_bytes(self, path: str, *, params=None):  # noqa: ANN001,ANN201
        raise AssertionError("should not be called")


class IntegrationsT020ToT022Test(unittest.TestCase):
    def test_t020_resolver_downloads_recording_and_metadata(self) -> None:
        with TemporaryDirectory() as tmpdir:
            resolver = TeamsChatRecordingResolver(
                graph_client=_FakeGraphClient(),
                download_dir=Path(tmpdir),
                recording_extensions=(".m4a",),
            )
            context = MeetingContext(
                meeting_id="meeting-1",
                chat_id="chat-1",
                meeting_title="title",
                meeting_time=datetime.now(UTC),
            )
            asset = resolver.resolve(context)
            self.assertTrue(Path(asset.file_path).exists())
            self.assertEqual(asset.file_id, "att-1")
            self.assertEqual(asset.metadata["source"], "teams-chat-attachment")

    def test_t020_resolver_raises_when_recording_not_found(self) -> None:
        resolver = TeamsChatRecordingResolver(
            graph_client=_NoAttachmentGraphClient(),
            download_dir=Path("."),
        )
        context = MeetingContext(meeting_id="meeting-1", chat_id="chat-1")
        with self.assertRaises(PipelineError) as exc:
            resolver.resolve(context)
        self.assertEqual(exc.exception.code, ErrorCode.RECORDING_NOT_FOUND)

    def test_t021_passthrough_audio_preprocessor(self) -> None:
        recording = RecordingAsset(file_path="a.wav", metadata={"x": 1})
        preprocessor = PassthroughAudioPreprocessor()
        self.assertIs(preprocessor.process(recording), recording)

    def test_t022_diarization_best_effort_logs_warning(self) -> None:
        class _FakeSpeechConfig:
            def __init__(self, *args, **kwargs):  # noqa: ANN002,ANN003
                self.speech_recognition_language = ""

            def set_property(self, *_args, **_kwargs):  # noqa: ANN002,ANN003
                return None

            def set_service_property(self, *_args, **_kwargs):  # noqa: ANN002,ANN003
                raise RuntimeError("diarization unsupported")

        stt = AzureSpeechFileInputSTT(
            speech_key="k",
            speech_region="r",
            diarization_enabled=True,
        )
        with self.assertLogs("src.integrations.speech_stt", level="WARNING") as logs:
            stt._try_enable_diarization(_FakeSpeechConfig())  # noqa: SLF001
        self.assertTrue(any(ErrorCode.STT_DIARIZATION_FALLBACK.value in line for line in logs.output))

    def test_t022_missing_recording_raises(self) -> None:
        stt = AzureSpeechFileInputSTT(speech_key="k", speech_region="r")
        with self.assertRaises(PipelineError) as exc:
            stt.transcribe(RecordingAsset(file_path="./not-found.wav"))
        self.assertEqual(exc.exception.code, ErrorCode.STT_FAILED)

    def test_t022_export_transcript_json(self) -> None:
        from src.domain.models import Transcript

        stt = AzureSpeechFileInputSTT(speech_key="k", speech_region="r")
        transcript = Transcript(text="hello", segments=[{"text": "hello"}])
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "transcript.json"
            stt.export_transcript(transcript, path)
            self.assertTrue(path.exists())
            self.assertIn("hello", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
