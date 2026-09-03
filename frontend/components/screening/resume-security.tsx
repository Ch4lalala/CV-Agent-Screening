import { titleCase } from "@/lib/format";
import type { SecurityAnalysis } from "@/types/api";

export function ResumeSecurity({ security }: { security: SecurityAnalysis }) {
  const warning = security.status === "warning";
  const unavailable = security.status === "unavailable";

  return (
    <section
      className={`panel resume-security resume-security-${security.status}`}
      aria-labelledby="resume-security-title"
    >
      <div className="resume-security-heading">
        <div>
          <p className="section-kicker">Document safety</p>
          <h2 id="resume-security-title">
            {warning ? "Resume Security Warning" : "Resume Security"}
          </h2>
        </div>
        <span className={`security-status security-status-${security.status}`}>
          {titleCase(security.status)}
        </span>
      </div>

      {security.status === "clean" ? (
        <p>No suspicious AI-manipulation instructions detected.</p>
      ) : warning ? (
        <p>
          Potential AI-manipulation content was detected and excluded from
          evaluation. This warning does not reject or lower the priority of the candidate.
        </p>
      ) : (
        <p>
          Security check unavailable. Potential instruction-like content was excluded
          conservatively when identified.
        </p>
      )}

      {security.flags.length > 0 ? (
        <div className="security-flag-list">
          {security.flags.map((flag) => (
            <article key={flag.id}>
              <div className="security-flag-meta">
                <strong>{titleCase(flag.flag_type)}</strong>
                <span className={`security-severity security-severity-${flag.severity}`}>
                  {titleCase(flag.severity)} severity
                </span>
              </div>
              <blockquote>{flag.detected_text}</blockquote>
              <p>{flag.explanation}</p>
              <small>
                {flag.excluded_from_evaluation
                  ? "Excluded from candidate profile and evidence evaluation"
                  : "Retained for evaluation"}
                {flag.source_page ? ` · Page ${flag.source_page}` : ""}
              </small>
            </article>
          ))}
        </div>
      ) : null}

      {warning || unavailable ? (
        <p className="security-review-note">
          Human review is recommended. Treat the flag as a document-safety signal,
          not evidence of candidate intent.
        </p>
      ) : null}
    </section>
  );
}
