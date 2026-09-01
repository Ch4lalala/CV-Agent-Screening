const workflow = [
  "Understanding job requirements",
  "Extracting candidate profile",
  "Matching evidence",
  "Checking uncertainty",
  "Preparing interview questions",
];

export function AnalysisWorkflow({ candidateName }: { candidateName: string }) {
  return (
    <div className="analysis-overlay" role="status" aria-live="polite">
      <div className="analysis-dialog">
        <div className="agent-orbit" aria-hidden="true">
          <span>P</span>
        </div>
        <p className="section-kicker">Recruitment agent</p>
        <h2>Analyzing {candidateName}</h2>
        <p className="analysis-summary">
          The evidence workflow may take several seconds. Keep this page open while the report is
          prepared.
        </p>
        <div className="workflow-list" aria-label="Analysis workflow">
          {workflow.map((step, index) => (
            <div className="workflow-step" key={step}>
              <span>{index + 1}</span>
              <p>{step}</p>
            </div>
          ))}
        </div>
        <p className="workflow-note">
          Workflow stages are shown for context; the backend does not report live node completion.
        </p>
      </div>
    </div>
  );
}
