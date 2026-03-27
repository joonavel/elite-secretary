from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from uuid import uuid4

from src.agents.agent_a_intent import AgentAIntentExtractor
from src.agents.agent_b_aggregation import AgentBAggregator
from src.agents.agent_c_excel import AgentCExcelBuilder
from src.agents.agent_d_insight import AgentDInsightWriter
from src.domain.errors import ErrorCode, PipelineError
from src.domain.models import ArtifactMetadata, MeetingContext, PipelineResult, PipelineStatus, PipelineStep
from src.integrations.sharepoint_publisher import SharePointPublisher, StubSharePointPublisher
from src.integrations.speech_stt import MockSpeechToText, SpeechToText
from src.integrations.teams_notifier import StubTeamsNotifier, TeamsNotifier
from src.integrations.teams_recording_resolver import LocalRecordingResolver, RecordingResolver
from src.pipeline.state_store import PipelineStateStore


@dataclass(slots=True)
class PipelineDeps:
    recording_resolver: RecordingResolver
    stt: SpeechToText
    agent_a: AgentAIntentExtractor
    agent_b: AgentBAggregator
    agent_c: AgentCExcelBuilder
    agent_d: AgentDInsightWriter
    publisher: SharePointPublisher
    notifier: TeamsNotifier


def default_deps(diarization_enabled: bool) -> PipelineDeps:
    return PipelineDeps(
        recording_resolver=LocalRecordingResolver(),
        stt=MockSpeechToText(diarization_enabled=diarization_enabled),
        agent_a=AgentAIntentExtractor(),
        agent_b=AgentBAggregator(),
        agent_c=AgentCExcelBuilder(),
        agent_d=AgentDInsightWriter(),
        publisher=StubSharePointPublisher(),
        notifier=StubTeamsNotifier(),
    )


def run_pipeline(
    meeting_context: MeetingContext,
    state_store: PipelineStateStore,
    deps: PipelineDeps,
) -> PipelineResult:
    run_id = str(uuid4())
    result = PipelineResult(run_id=run_id, status=PipelineStatus.PENDING)
    state_store.create_run(run_id=run_id, meeting_context=meeting_context)
    state_store.mark_run_status(run_id, PipelineStatus.RUNNING)

    try:
        state_store.mark_step_running(run_id, PipelineStep.STEP_1_COLLECT, input_summary=meeting_context.meeting_id)
        recording = deps.recording_resolver.resolve(meeting_context)
        state_store.mark_step_finished(run_id, PipelineStep.STEP_1_COLLECT, PipelineStatus.SUCCEEDED, recording.file_path)

        state_store.mark_step_running(run_id, PipelineStep.STEP_2_PREPROCESS, input_summary=recording.file_path)
        preprocessed_recording = recording
        state_store.mark_step_finished(
            run_id,
            PipelineStep.STEP_2_PREPROCESS,
            PipelineStatus.SUCCEEDED,
            preprocessed_recording.file_path,
        )

        state_store.mark_step_running(run_id, PipelineStep.STEP_3_STT, input_summary=preprocessed_recording.file_path)
        transcript = deps.stt.transcribe(preprocessed_recording)
        state_store.mark_step_finished(
            run_id,
            PipelineStep.STEP_3_STT,
            PipelineStatus.SUCCEEDED,
            f"segments={len(transcript.segments)}",
        )

        state_store.mark_step_running(run_id, PipelineStep.STEP_4_AGENT_A, input_summary="transcript")
        intent = deps.agent_a.extract(meeting_context, transcript)
        state_store.mark_step_finished(
            run_id,
            PipelineStep.STEP_4_AGENT_A,
            PipelineStatus.SUCCEEDED,
            f"period={intent.period_value}",
        )

        state_store.mark_step_running(run_id, PipelineStep.STEP_5_AGENT_B, input_summary="intent")
        aggregation = deps.agent_b.aggregate(meeting_context, intent)
        if aggregation.validation_errors:
            raise PipelineError(
                code=ErrorCode.VALIDATION_ERROR,
                message="; ".join(aggregation.validation_errors),
                recoverable=False,
                step=PipelineStep.STEP_5_AGENT_B.value,
            )
        output_summary = f"metrics={len(aggregation.metrics)}"
        if aggregation.validation_warnings:
            output_summary = output_summary + f", warnings={len(aggregation.validation_warnings)}"
        state_store.mark_step_finished(run_id, PipelineStep.STEP_5_AGENT_B, PipelineStatus.SUCCEEDED, output_summary)

        state_store.mark_step_running(run_id, PipelineStep.STEP_6_AGENT_C, input_summary="aggregation")
        state_store.mark_step_running(run_id, PipelineStep.STEP_6_AGENT_D, input_summary="aggregation+intent")
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_c = executor.submit(deps.agent_c.build, meeting_context, aggregation, run_id)
            future_d = executor.submit(deps.agent_d.build, meeting_context, intent, aggregation, run_id)
            artifact_c = future_c.result()
            artifact_d = future_d.result()
        artifacts: list[ArtifactMetadata] = [artifact_c, artifact_d]
        state_store.mark_step_finished(
            run_id,
            PipelineStep.STEP_6_AGENT_C,
            PipelineStatus.SUCCEEDED,
            artifact_c.artifact_path,
        )
        state_store.mark_step_finished(
            run_id,
            PipelineStep.STEP_6_AGENT_D,
            PipelineStatus.SUCCEEDED,
            artifact_d.artifact_path,
        )

        state_store.mark_step_running(run_id, PipelineStep.STEP_7_PUBLISH, input_summary=f"artifacts={len(artifacts)}")
        published = deps.publisher.publish(meeting_context, artifacts)
        deps.notifier.notify(meeting_context, published)
        state_store.mark_step_finished(
            run_id,
            PipelineStep.STEP_7_PUBLISH,
            PipelineStatus.SUCCEEDED,
            f"destinations={len(published.destinations)}",
        )

        state_store.mark_run_status(run_id, PipelineStatus.SUCCEEDED)
        result.status = PipelineStatus.SUCCEEDED
        result.artifacts = artifacts
        result.published_result = published
        return result
    except PipelineError as error:
        if error.step:
            try:
                step = PipelineStep(error.step)
            except ValueError:
                step = PipelineStep.STEP_7_PUBLISH
            state_store.mark_step_finished(
                run_id,
                step,
                PipelineStatus.FAILED,
                error.message,
                error={"code": error.code.value, "message": error.message, "recoverable": error.recoverable},
            )
        state_store.mark_run_status(run_id, PipelineStatus.FAILED)
        result.status = PipelineStatus.FAILED
        return result
    except Exception as error:  # explicit wrapping to preserve run status contract
        state_store.mark_run_status(run_id, PipelineStatus.FAILED)
        raise PipelineError(
            code=ErrorCode.PIPELINE_STEP_FAILED,
            message=str(error),
            recoverable=False,
        ) from error
