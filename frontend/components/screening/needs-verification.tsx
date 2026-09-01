import type { EvidenceResult } from "@/types/api";

export function NeedsVerification({
  names,
  results,
}: {
  names: string[];
  results: EvidenceResult[];
}) {
  const uncertainResults = results.filter((result) => result.needs_human_verification);
  const represented = new Set(uncertainResults.map((result) => result.requirement_name));
  const remainingNames = names.filter((name) => !represented.has(name));

  return (
    <section className="verification-section" aria-labelledby="verification-title">
      <div className="verification-heading">
        <span aria-hidden="true">?</span>
        <div>
          <p className="section-kicker">Human interview focus</p>
          <h2 id="verification-title">Needs verification</h2>
        </div>
      </div>
      {uncertainResults.length === 0 && remainingNames.length === 0 ? (
        <p className="verification-clear">
          No evaluated requirements were marked for additional human verification.
        </p>
      ) : (
        <div className="verification-grid">
          {uncertainResults.map((result) => (
            <article key={result.id}>
              <strong>{result.requirement_name}</strong>
              <span>{result.status === "no_evidence" ? "No evidence found" : "Partial evidence"}</span>
              <p>{result.explanation}</p>
            </article>
          ))}
          {remainingNames.map((name) => (
            <article key={name}>
              <strong>{name}</strong>
              <span>Needs human verification</span>
              <p>Clarify this qualification directly with the candidate.</p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
