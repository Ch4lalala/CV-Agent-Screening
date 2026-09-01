import type { Coverage } from "@/types/api";

function CoverageCard({ label, coverage }: { label: string; coverage: Coverage }) {
  const percentage = coverage.total === 0 ? 0 : (coverage.supported / coverage.total) * 100;
  return (
    <article className="coverage-card">
      <div className="coverage-card-top">
        <span>{label}</span>
        <strong>
          {coverage.supported}<small> / {coverage.total}</small>
        </strong>
      </div>
      <div
        className="coverage-track"
        role="progressbar"
        aria-label={`${label}: ${coverage.supported} of ${coverage.total} supported`}
        aria-valuemin={0}
        aria-valuemax={coverage.total}
        aria-valuenow={coverage.supported}
      >
        <span style={{ width: `${percentage}%` }} />
      </div>
      <p>
        <strong>{coverage.supported} of {coverage.total}</strong> qualifications supported by
        resume evidence
      </p>
    </article>
  );
}

export function CoverageSummary({
  required,
  preferred,
}: {
  required: Coverage;
  preferred: Coverage;
}) {
  return (
    <section aria-labelledby="coverage-title">
      <div className="section-heading">
        <div>
          <p className="section-kicker">Transparent coverage</p>
          <h2 id="coverage-title">Qualification coverage</h2>
          <p className="section-description">
            Coverage counts supported requirements only. It is not a candidate score.
          </p>
        </div>
      </div>
      <div className="coverage-grid">
        <CoverageCard label="Required qualifications" coverage={required} />
        <CoverageCard label="Preferred qualifications" coverage={preferred} />
      </div>
    </section>
  );
}
