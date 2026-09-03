import type { ScreeningRunStatus, ScreeningStage } from "@/types/api";

const workflow: Array<{ stage: ScreeningStage; label: string }> = [
  { stage: "normalize_requirements", label: "Understanding job requirements" },
  { stage: "resume_security", label: "Checking resume security" },
  { stage: "extract_candidate_profile", label: "Extracting candidate profile" },
  { stage: "match_evidence", label: "Matching resume evidence" },
  { stage: "analyze_uncertainty", label: "Checking uncertainty" },
  { stage: "generate_interview_questions", label: "Preparing interview questions" },
  { stage: "generate_report", label: "Finalizing evidence report" },
];

type StepState = "completed" | "current" | "waiting";

function stepState(
  stepIndex: number,
  status: ScreeningRunStatus,
  currentStage: ScreeningStage,
): StepState {
  if (status === "completed" || currentStage === "completed") {
    return "completed";
  }
  if (status === "failed" || currentStage === "failed" || currentStage === "queued") {
    return "waiting";
  }
  const currentIndex = workflow.findIndex((item) => item.stage === currentStage);
  if (stepIndex < currentIndex) {
    return "completed";
  }
  return stepIndex === currentIndex ? "current" : "waiting";
}

export function AnalysisWorkflow({
  candidateName,
  status,
  currentStage,
  onClose,
  onViewReport,
  onRetry,
}: {
  candidateName: string;
  status: ScreeningRunStatus;
  currentStage: ScreeningStage;
  onClose: () => void;
  onViewReport?: () => void;
  onRetry?: () => void;
}) {
  const completed = status === "completed" || currentStage === "completed";
  const failed = status === "failed" || currentStage === "failed";
  const queued = currentStage === "queued" && !completed && !failed;
  const heading = completed
    ? "Screening complete"
    : failed
      ? "Screening failed"
      : `Analyzing ${candidateName}`;

  return (
    <div className="analysis-overlay">
      <div
        className="analysis-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="analysis-dialog-title"
        aria-describedby="analysis-dialog-summary"
      >
        <button
          className="analysis-close"
          type="button"
          aria-label="Close screening progress"
          onClick={onClose}
        >
          ×
        </button>
        <div className={`agent-orbit${completed ? " agent-orbit-complete" : failed ? " agent-orbit-failed" : ""}`} aria-hidden="true">
          <span>{completed ? "✓" : failed ? "!" : "P"}</span>
        </div>
        <p className="section-kicker">Recruitment agent</p>
        <h2 id="analysis-dialog-title">{heading}</h2>
        <p className="analysis-summary" id="analysis-dialog-summary">
          {completed
            ? "The evidence report is ready for recruiter review."
            : failed
              ? "ProofHire could not complete this analysis. No provider details were exposed."
              : queued
                ? "The screening run is queued and will begin shortly."
                : "Progress reflects completed LangGraph stages reported by the backend."}
        </p>

        {!failed ? (
          <div className="workflow-list" aria-label="Live screening workflow">
            {workflow.map((step, index) => {
              const state = stepState(index, status, currentStage);
              return (
                <div className={`workflow-step workflow-step-${state}`} key={step.stage}>
                  <span className="workflow-step-icon" aria-hidden="true">
                    {state === "completed" ? "✓" : state === "current" ? <i /> : "○"}
                  </span>
                  <p>{step.label}</p>
                  <small>
                    {state === "completed" ? "Completed" : state === "current" ? "In progress" : "Waiting"}
                  </small>
                </div>
              );
            })}
          </div>
        ) : null}

        {!completed && !failed ? (
          <p className="workflow-note">
            Screening continues even if you close this window or navigate elsewhere.
          </p>
        ) : null}

        <div className="analysis-actions">
          {completed && onViewReport ? (
            <button className="button button-primary" type="button" onClick={onViewReport}>
              View candidate report
            </button>
          ) : null}
          {failed && onRetry ? (
            <button className="button button-primary" type="button" onClick={onRetry}>
              Retry screening
            </button>
          ) : null}
          <button className="button button-secondary" type="button" onClick={onClose}>
            {!completed && !failed ? "Continue in background" : "Close"}
          </button>
        </div>
      </div>
    </div>
  );
}
