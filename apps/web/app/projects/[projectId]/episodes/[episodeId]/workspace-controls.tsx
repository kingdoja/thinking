"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import {
  isStageType,
  rerunEpisodeStage,
  REVIEW_DECISION_OPTIONS,
  startEpisodeWorkflow,
  STAGE_OPTIONS,
  submitEpisodeReview,
  type ReviewDecisionType,
  type StageType,
  type WorkspaceShot,
  type WorkspaceStageTask,
} from "../../../../../lib/api";

type WorkspaceControlsProps = {
  projectId: string;
  episodeId: string;
  currentStage: string;
  stageTasks: WorkspaceStageTask[];
  shots: WorkspaceShot[];
};

type Feedback = {
  tone: "success" | "error";
  text: string;
};

type ActiveAction = "start" | "rerun" | "review" | null;

function toStageType(value: string, fallback: StageType = "brief"): StageType {
  return isStageType(value) ? value : fallback;
}

function formatStageLabel(stage: string): string {
  return stage.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

export default function WorkspaceControls({
  projectId,
  episodeId,
  currentStage,
  stageTasks,
  shots,
}: WorkspaceControlsProps) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [activeAction, setActiveAction] = useState<ActiveAction>(null);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [startStage, setStartStage] = useState<StageType>(() => toStageType(currentStage));
  const [rerunStage, setRerunStage] = useState<StageType>(() => {
    const latestStage = stageTasks[0]?.stage_type ?? currentStage;
    return toStageType(latestStage, toStageType(currentStage));
  });
  const [targetShotId, setTargetShotId] = useState<string>("");
  const [reviewDecision, setReviewDecision] = useState<ReviewDecisionType>("approved");
  const [reviewNote, setReviewNote] = useState<string>("");

  const rerunStageOptions = useMemo(
    () =>
      Array.from(
        new Set(
          [currentStage, ...stageTasks.map((task) => task.stage_type)].filter((value): value is StageType => isStageType(value)),
        ),
      ).map((value) => ({
        value,
        label: formatStageLabel(value),
      })),
    [currentStage, stageTasks],
  );

  const rerunnableShots = useMemo(
    () => shots.filter((shot): shot is WorkspaceShot & { id: string } => Boolean(shot.id)),
    [shots],
  );

  const reviewableTasks = useMemo(
    () =>
      stageTasks.filter(
        (task) =>
          task.review_required &&
          task.task_status === "succeeded" &&
          (task.review_status === null || task.review_status === "pending"),
      ),
    [stageTasks],
  );

  const [reviewStageTaskId, setReviewStageTaskId] = useState<string>(reviewableTasks[0]?.id ?? "");

  useEffect(() => {
    setReviewStageTaskId((current) => {
      if (reviewableTasks.some((task) => task.id === current)) {
        return current;
      }
      return reviewableTasks[0]?.id ?? "";
    });
  }, [reviewableTasks]);

  function withTransition(action: ActiveAction, runner: () => Promise<void>) {
    setFeedback(null);
    setActiveAction(action);

    startTransition(() => {
      void runner().finally(() => {
        setActiveAction(null);
      });
    });
  }

  function runStartWorkflow() {
    withTransition("start", async () => {
      try {
        const workflow = await startEpisodeWorkflow(projectId, episodeId, startStage);
        setFeedback({
          tone: "success",
          text: `Started ${formatStageLabel(startStage)} workflow. Current status: ${workflow.status}.`,
        });
        router.refresh();
      } catch (error) {
        setFeedback({
          tone: "error",
          text: error instanceof Error ? error.message : "Failed to start workflow.",
        });
      }
    });
  }

  function runRerunStage() {
    withTransition("rerun", async () => {
      try {
        const result = await rerunEpisodeStage(
          projectId,
          episodeId,
          rerunStage,
          targetShotId ? [targetShotId] : [],
        );
        setFeedback({
          tone: "success",
          text:
            result.target_shot_ids.length > 0
              ? `Submitted rerun request for ${formatStageLabel(rerunStage)} on one shot.`
              : `Submitted rerun request for the full ${formatStageLabel(rerunStage)} stage.`,
        });
        router.refresh();
      } catch (error) {
        setFeedback({
          tone: "error",
          text: error instanceof Error ? error.message : "Failed to submit rerun request.",
        });
      }
    });
  }

  function runSubmitReview() {
    if (!reviewStageTaskId) {
      setFeedback({
        tone: "error",
        text: "There is no pending review task right now.",
      });
      return;
    }

    withTransition("review", async () => {
      try {
        const review = await submitEpisodeReview(
          projectId,
          episodeId,
          reviewStageTaskId,
          reviewDecision,
          reviewNote,
        );
        setFeedback({
          tone: "success",
          text: `Submitted review decision: ${formatStageLabel(review.status)}.`,
        });
        if (review.decision_note) {
          setReviewNote("");
        }
        router.refresh();
      } catch (error) {
        setFeedback({
          tone: "error",
          text: error instanceof Error ? error.message : "Failed to submit review.",
        });
      }
    });
  }

  return (
    <section className="workspace-control-grid">
      <div className="workspace-control-card">
        <div>
          <div className="mono">WORKFLOW ACTIONS</div>
          <h3 className="workspace-control-title">Start a new workflow run</h3>
          <p className="subtle workspace-control-copy">
            This calls the real <code>workflow/start</code> endpoint and creates fresh
            <code> WorkflowRun</code> and <code>StageTask</code> records on the backend.
          </p>
        </div>
        <div className="workspace-control-row">
          <label className="workspace-field">
            <span>Start Stage</span>
            <select
              className="workspace-input"
              value={startStage}
              onChange={(event) => setStartStage(event.target.value as StageType)}
              disabled={isPending}
            >
              {STAGE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <button type="button" className="btn primary" onClick={runStartWorkflow} disabled={isPending}>
            {isPending && activeAction === "start" ? "Submitting..." : "Start Workflow"}
          </button>
        </div>
      </div>

      <div className="workspace-control-card">
        <div>
          <div className="mono">REVIEW ACTIONS</div>
          <h3 className="workspace-control-title">Submit a review decision</h3>
          <p className="subtle workspace-control-copy">
            This calls the real <code>review</code> endpoint, writes to
            <code> review_decisions</code>, and updates the target
            <code> StageTask.review_status</code>.
          </p>
        </div>
        <div className="workspace-control-row">
          <label className="workspace-field">
            <span>Target Stage Task</span>
            <select
              className="workspace-input"
              value={reviewStageTaskId}
              onChange={(event) => setReviewStageTaskId(event.target.value)}
              disabled={isPending || reviewableTasks.length === 0}
            >
              {reviewableTasks.length === 0 ? (
                <option value="">No pending review task</option>
              ) : (
                reviewableTasks.map((task) => (
                  <option key={task.id} value={task.id}>
                    {formatStageLabel(task.stage_type)} / {task.task_status}
                  </option>
                ))
              )}
            </select>
          </label>
          <label className="workspace-field">
            <span>Decision</span>
            <select
              className="workspace-input"
              value={reviewDecision}
              onChange={(event) => setReviewDecision(event.target.value as ReviewDecisionType)}
              disabled={isPending || reviewableTasks.length === 0}
            >
              {REVIEW_DECISION_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="workspace-control-row">
          <label className="workspace-field">
            <span>Decision Note</span>
            <textarea
              className="workspace-input"
              rows={3}
              value={reviewNote}
              onChange={(event) => setReviewNote(event.target.value)}
              placeholder="Add review context for later follow-up."
              disabled={isPending || reviewableTasks.length === 0}
            />
          </label>
          <button
            type="button"
            className="btn primary"
            onClick={runSubmitReview}
            disabled={isPending || reviewableTasks.length === 0}
          >
            {isPending && activeAction === "review" ? "Submitting..." : "Submit Review"}
          </button>
        </div>
      </div>

      <div className="workspace-control-card">
        <div>
          <div className="mono">RERUN ACTIONS</div>
          <h3 className="workspace-control-title">Submit a rerun request</h3>
          <p className="subtle workspace-control-copy">
            This calls the real <code>workflow/rerun</code> endpoint. The backend currently
            returns <code>accepted</code> while the real rerun execution is still the next
            implementation step.
          </p>
        </div>
        <div className="workspace-control-row">
          <label className="workspace-field">
            <span>Rerun Stage</span>
            <select
              className="workspace-input"
              value={rerunStage}
              onChange={(event) => setRerunStage(event.target.value as StageType)}
              disabled={isPending}
            >
              {rerunStageOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="workspace-field">
            <span>Target Shot</span>
            <select
              className="workspace-input"
              value={targetShotId}
              onChange={(event) => setTargetShotId(event.target.value)}
              disabled={isPending || rerunnableShots.length === 0}
            >
              <option value="">All Shots</option>
              {rerunnableShots.map((shot) => (
                <option key={shot.id} value={shot.id}>
                  {shot.code}
                </option>
              ))}
            </select>
          </label>
          <button type="button" className="btn" onClick={runRerunStage} disabled={isPending}>
            {isPending && activeAction === "rerun" ? "Submitting..." : "Submit Rerun"}
          </button>
        </div>
      </div>

      {feedback ? <div className={`workspace-feedback ${feedback.tone}`}>{feedback.text}</div> : null}
    </section>
  );
}