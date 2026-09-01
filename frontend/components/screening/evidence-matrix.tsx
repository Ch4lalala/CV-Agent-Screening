import { EvidenceCard } from "@/components/screening/evidence-card";
import type { EvidenceResult, RequirementType } from "@/types/api";

function MatrixGroup({
  title,
  type,
  results,
}: {
  title: string;
  type: RequirementType;
  results: EvidenceResult[];
}) {
  const group = results.filter((result) => result.requirement_type === type);
  return (
    <div className="matrix-group">
      <div className="matrix-group-heading">
        <h3>{title}</h3>
        <span>{group.length} requirements</span>
      </div>
      {group.length > 0 ? (
        <div className="evidence-list">
          {group.map((result, index) => (
            <EvidenceCard key={result.id} result={result} defaultExpanded={index === 0} />
          ))}
        </div>
      ) : (
        <p className="inline-empty">No {type} requirements were evaluated.</p>
      )}
    </div>
  );
}

export function EvidenceMatrix({ results }: { results: EvidenceResult[] }) {
  return (
    <section className="panel evidence-panel" aria-labelledby="evidence-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Requirement-by-requirement review</p>
          <h2 id="evidence-title">Evidence matrix</h2>
          <p>Open a qualification to inspect its explanation and grounded resume quotes.</p>
        </div>
        <div className="evidence-legend" aria-label="Evidence status legend">
          <span><i className="legend-supported" /> Supported</span>
          <span><i className="legend-partial" /> Partial</span>
          <span><i className="legend-none" /> No evidence</span>
        </div>
      </div>
      <MatrixGroup title="Required qualifications" type="required" results={results} />
      <MatrixGroup title="Preferred qualifications" type="preferred" results={results} />
    </section>
  );
}
