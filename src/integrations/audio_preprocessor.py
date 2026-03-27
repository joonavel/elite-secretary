from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.domain.errors import ErrorCode, PipelineError
from src.domain.models import RecordingAsset

try:
    from pydub import AudioSegment
except Exception:  # optional dependency gate
    AudioSegment = None  # type: ignore[assignment]


class AudioPreprocessor:
    def process(self, recording: RecordingAsset) -> RecordingAsset:
        raise NotImplementedError


@dataclass(slots=True)
class PassthroughAudioPreprocessor(AudioPreprocessor):
    def process(self, recording: RecordingAsset) -> RecordingAsset:
        return recording


@dataclass(slots=True)
class FfmpegAudioPreprocessor(AudioPreprocessor):
    output_dir: Path
    sample_rate: int = 16000
    channels: int = 1
    target_extension: str = ".wav"
    supported_input_extensions: tuple[str, ...] = (".wav", ".m4a", ".mp4")

    def process(self, recording: RecordingAsset) -> RecordingAsset:
        source_path = Path(recording.file_path)
        if not source_path.exists():
            raise PipelineError(
                code=ErrorCode.AUDIO_PREPROCESS_FAILED,
                message=f"T-021 source recording not found: {source_path}",
                recoverable=False,
                step="T-021_AUDIO_PREPROCESS",
            )
        if AudioSegment is None:
            raise PipelineError(
                code=ErrorCode.AUDIO_PREPROCESS_FAILED,
                message="T-021 pydub is not installed. Install optional dependency: pydub + ffmpeg",
                recoverable=False,
                step="T-021_AUDIO_PREPROCESS",
            )

        suffix = source_path.suffix.lower()
        if suffix not in self.supported_input_extensions:
            raise PipelineError(
                code=ErrorCode.AUDIO_PREPROCESS_FAILED,
                message=f"T-021 unsupported audio extension: {suffix}",
                recoverable=False,
                step="T-021_AUDIO_PREPROCESS",
            )
        if suffix == self.target_extension and self._is_already_compatible(recording):
            return recording

        try:
            audio = AudioSegment.from_file(source_path)
            audio = audio.set_channels(self.channels).set_frame_rate(self.sample_rate)
            self.output_dir.mkdir(parents=True, exist_ok=True)
            target_path = self.output_dir / f"{source_path.stem}_stt{self.target_extension}"
            audio.export(target_path, format=self.target_extension.lstrip("."))
        except Exception as error:
            raise PipelineError(
                code=ErrorCode.AUDIO_PREPROCESS_FAILED,
                message=f"T-021 ffmpeg conversion failed: {error}",
                recoverable=False,
                step="T-021_AUDIO_PREPROCESS",
            ) from error

        metadata = dict(recording.metadata)
        metadata["preprocessed"] = True
        metadata["preprocess_target"] = f"{self.channels}ch/{self.sample_rate}Hz"
        return RecordingAsset(
            file_path=str(target_path),
            file_id=recording.file_id,
            source_link=recording.source_link,
            mime_type="audio/wav",
            metadata=metadata,
        )

    def _is_already_compatible(self, recording: RecordingAsset) -> bool:
        metadata = recording.metadata
        if "preprocess_target" in metadata:
            return metadata["preprocess_target"] == f"{self.channels}ch/{self.sample_rate}Hz"
        return False

