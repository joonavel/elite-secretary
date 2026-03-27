from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from src.domain.errors import ErrorCode, PipelineError
from src.domain.models import MeetingContext, RecordingAsset
from src.integrations.graph_client import GraphClient


class RecordingResolver:
    def resolve(self, meeting_context: MeetingContext) -> RecordingAsset:
        raise NotImplementedError


@dataclass(slots=True)
class TeamsChatRecordingResolver(RecordingResolver):
    graph_client: GraphClient
    download_dir: Path
    recording_extensions: tuple[str, ...] = (".mp4", ".m4a", ".wav")
    page_size: int = 50

    def resolve(self, meeting_context: MeetingContext) -> RecordingAsset:
        if not meeting_context.chat_id:
            raise PipelineError(
                code=ErrorCode.RECORDING_NOT_FOUND,
                message="T-020 requires chat_id to resolve Teams chat attachments",
                recoverable=False,
                step="T-020_RECORDING_RESOLVE",
            )

        candidates = self._collect_candidate_attachments(meeting_context.chat_id)
        if not candidates:
            raise PipelineError(
                code=ErrorCode.RECORDING_NOT_FOUND,
                message=f"T-020 no recording attachments found for chat_id={meeting_context.chat_id}",
                recoverable=False,
                step="T-020_RECORDING_RESOLVE",
            )

        attachment = candidates[0]
        return self._download_attachment(attachment, meeting_context)

    def _collect_candidate_attachments(self, chat_id: str) -> list[dict[str, Any]]:
        attachments: list[dict[str, Any]] = []
        path = f"/chats/{chat_id}/messages"
        params: dict[str, Any] | None = {"$top": self.page_size}
        while path:
            response = self.graph_client.request("GET", path, params=params)
            params = None
            for message in response.get("value", []):
                for attachment in message.get("attachments", []):
                    if str(attachment.get("contentType", "")).lower() == "reference":
                        continue
                    name = str(attachment.get("name", "")).lower()
                    if any(name.endswith(ext.lower()) for ext in self.recording_extensions):
                        attachment_copy = dict(attachment)
                        attachment_copy["messageId"] = message.get("id")
                        attachments.append(attachment_copy)
            next_link = response.get("@odata.nextLink")
            if next_link and isinstance(next_link, str) and next_link.startswith("http"):
                prefix = "https://graph.microsoft.com/v1.0"
                path = next_link[len(prefix) :] if next_link.startswith(prefix) else next_link
            else:
                path = ""
        return attachments

    def _download_attachment(self, attachment: dict[str, Any], meeting_context: MeetingContext) -> RecordingAsset:
        content_url = attachment.get("contentUrl")
        if not content_url or not isinstance(content_url, str):
            raise PipelineError(
                code=ErrorCode.RECORDING_NOT_FOUND,
                message=f"T-020 attachment missing contentUrl (attachment_id={attachment.get('id')})",
                recoverable=False,
                step="T-020_RECORDING_DOWNLOAD",
            )

        parsed_path = self._normalize_graph_path(content_url)
        payload = self.graph_client.request_bytes(parsed_path)

        self.download_dir.mkdir(parents=True, exist_ok=True)
        filename = str(attachment.get("name") or f"{attachment.get('id', 'recording')}.bin")
        target_path = self.download_dir / filename
        target_path.write_bytes(payload)

        meeting_time = meeting_context.meeting_time.isoformat() if meeting_context.meeting_time else None
        return RecordingAsset(
            file_path=str(target_path),
            file_id=str(attachment.get("id")) if attachment.get("id") else None,
            source_link=content_url,
            mime_type=attachment.get("contentType"),
            metadata={
                "meeting_id": meeting_context.meeting_id,
                "meeting_title": meeting_context.meeting_title,
                "meeting_time": meeting_time,
                "chat_id": meeting_context.chat_id,
                "message_id": attachment.get("messageId"),
                "source": "teams-chat-attachment",
            },
        )

    @staticmethod
    def _normalize_graph_path(content_url: str) -> str:
        prefix = "https://graph.microsoft.com/v1.0"
        if content_url.startswith(prefix):
            return content_url[len(prefix) :]
        parsed = urlparse(content_url)
        if parsed.netloc.lower() == "graph.microsoft.com" and parsed.path.startswith("/v1.0"):
            path = parsed.path[len("/v1.0") :]
            if parsed.query:
                return f"{path}?{parsed.query}"
            return path
        return content_url


@dataclass(slots=True)
class LocalRecordingResolver(RecordingResolver):
    def resolve(self, meeting_context: MeetingContext) -> RecordingAsset:
        file_path = meeting_context.local_recording_path or "./artifacts/mock_recording.m4a"
        return RecordingAsset(
            file_path=file_path,
            metadata={"meeting_id": meeting_context.meeting_id, "source": "local"},
        )
