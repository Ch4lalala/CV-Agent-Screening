import Link from "next/link";

import { StatusBadge } from "@/components/ui/status-badge";
import { formatDateTime } from "@/lib/format";
import type { ScreeningRun } from "@/types/api";

export function ScreeningHistory({
  candidateId,
  runs,
  viewedRunId,
}: {
  candidateId: number;
  runs: ScreeningRun[];
  viewedRunId?: number;
}) {
  return (
    <section className="panel history-panel" aria-labelledby="history-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Preserved snapshots</p>
          <h2 id="history-title">Screening history</h2>
          <p>Completed reports remain unchanged when screening runs again.</p>
        </div>
        <span className="section-count">{runs.length} runs</span>
      </div>

      {runs.length === 0 ? (
        <p className="inline-empty">No screening attempts yet.</p>
      ) : (
        <div className="history-list">
          {runs.map((run, index) => {
            const content = (
              <>
                <span className="history-index">#{run.id}</span>
                <div className="history-main">
                  <strong>{formatDateTime(run.started_at ?? run.created_at)}</strong>
                  <small>{run.model_name ? `Model: ${run.model_name}` : "Model not recorded"}</small>
                  {run.status === "failed" && run.error_message ? <p>{run.error_message}</p> : null}
                </div>
                <div className="history-status">
                  {index === 0 ? <span className="latest-chip">Latest attempt</span> : null}
                  <StatusBadge status={run.status} />
                </div>
                {run.status === "completed" ? <span aria-hidden="true">→</span> : null}
              </>
            );
            const className = `history-row${run.id === viewedRunId ? " history-row-viewed" : ""}`;
            return run.status === "completed" ? (
              <Link
                className={className}
                href={`/candidates/${candidateId}/screenings/${run.id}`}
                key={run.id}
              >
                {content}
              </Link>
            ) : (
              <div className={className} key={run.id}>
                {content}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
