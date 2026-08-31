const foundations = ["Next.js frontend", "FastAPI backend", "PostgreSQL database"];

export default function Home() {
  return (
    <main>
      <section className="hero" aria-labelledby="page-title">
        <p className="eyebrow">Phase 1 foundation</p>
        <h1 id="page-title">Evidence-Grounded Recruitment Agent</h1>
        <p className="summary">
          AI shouldn&apos;t decide who&apos;s qualified. It should show recruiters the
          evidence and keep the final decision human.
        </p>
        <div className="status" role="status">
          <span className="status-dot" aria-hidden="true" />
          Application foundation is running
        </div>
        <ul>
          {foundations.map((foundation) => (
            <li key={foundation}>{foundation}</li>
          ))}
        </ul>
        <p className="note">
          Recruitment workflows and AI analysis are intentionally reserved for later phases.
        </p>
      </section>
    </main>
  );
}

