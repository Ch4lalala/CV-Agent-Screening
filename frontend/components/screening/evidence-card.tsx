import { StatusBadge } from "@/components/ui/status-badge";
import { titleCase } from "@/lib/format";
import type { EvidenceResult } from "@/types/api";

const statusLabel = {
  supported: "Supported",
  partial: "Partial evidence",
  no_evidence: "No evidence found",
} as const;

export function EvidenceCard({
  result,
  defaultExpanded = false,
}: {
  result: EvidenceResult;
  defaultExpanded?: boolean;
}) {
  return (
    <details className={`evidence-card evidence-${result.status}`} open={defaultExpanded}>
      <summary>
        <span className="evidence-marker" aria-hidden="true">
          {result.status === "supported" ? "✓" : result.status === "partial" ? "◐" : "○"}
        </span>
        <span className="evidence-title">
          <strong>{result.requirement_name}</strong>
          <small>{titleCase(result.requirement_type)} qualification</small>
        </span>
        <StatusBadge status={result.status} label={statusLabel[result.status]} />
        <span className="details-chevron" aria-hidden="true">⌄</span>
      </summary>
      <div className="evidence-body">
        <div className="evidence-meta">
          <span>
            Confidence <strong>{titleCase(result.confidence)}</strong>
          </span>
          {result.needs_human_verification ? (
            <span className="verification-chip">Needs human verification</span>
          ) : null}
        </div>

        <div className="explanation-block">
          <span>Assessment explanation</span>
          <p>{result.explanation}</p>
        </div>

        <div className="evidence-quotes">
          <span>Grounded resume evidence</span>
          {result.evidence_items.length === 0 ? (
            <p className="no-quote">
              No direct supporting quote was retained from the provided resume.
            </p>
          ) : (
            result.evidence_items.map((item) => (
              <blockquote key={item.id}>
                <p>“{item.quote}”</p>
                <footer>
                  {item.source_section ?? "Resume"}
                  {item.source_page ? ` · Page ${item.source_page}` : ""}
                </footer>
              </blockquote>
            ))
          )}
        </div>
      </div>
    </details>
  );
}
