import type { CandidateProfile } from "@/types/api";

export function CandidateProfileCard({ profile }: { profile: CandidateProfile }) {
  const hasExperience = profile.work_experience.length > 0;
  const hasEducation = profile.education.length > 0;
  const hasProjects = profile.projects.length > 0;

  return (
    <section className="panel profile-panel" aria-labelledby="profile-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Structured resume context</p>
          <h2 id="profile-title">Candidate profile</h2>
          <p>AI-extracted context is secondary to the evidence matrix.</p>
        </div>
      </div>

      <div className="profile-section">
        <h3>Skills</h3>
        {profile.skills.length > 0 ? (
          <div className="tag-list">
            {profile.skills.map((skill) => <span key={skill}>{skill}</span>)}
          </div>
        ) : (
          <p className="inline-empty">No skills were extracted.</p>
        )}
      </div>

      {hasExperience ? (
        <div className="profile-section">
          <h3>Experience</h3>
          <div className="profile-timeline">
            {profile.work_experience.map((experience, index) => (
              <article key={`${experience.role}-${experience.company}-${index}`}>
                <span aria-hidden="true" />
                <div>
                  <strong>{experience.role ?? "Role not specified"}</strong>
                  <small>
                    {[experience.company, experience.period].filter(Boolean).join(" · ")}
                  </small>
                  {experience.description.slice(0, 3).map((line) => <p key={line}>{line}</p>)}
                </div>
              </article>
            ))}
          </div>
        </div>
      ) : null}

      {hasProjects ? (
        <div className="profile-section">
          <h3>Projects</h3>
          <div className="profile-cards">
            {profile.projects.map((project, index) => (
              <article key={`${project.name}-${index}`}>
                <strong>{project.name ?? "Project"}</strong>
                {project.description.slice(0, 2).map((line) => <p key={line}>{line}</p>)}
                {project.technologies.length > 0 ? (
                  <small>{project.technologies.join(" · ")}</small>
                ) : null}
              </article>
            ))}
          </div>
        </div>
      ) : null}

      {hasEducation ? (
        <div className="profile-section">
          <h3>Education</h3>
          <div className="profile-cards">
            {profile.education.map((education, index) => (
              <article key={`${education.institution}-${index}`}>
                <strong>{education.qualification ?? "Qualification"}</strong>
                <p>{[education.field_of_study, education.institution].filter(Boolean).join(" · ")}</p>
                {education.period ? <small>{education.period}</small> : null}
              </article>
            ))}
          </div>
        </div>
      ) : null}

      {profile.certifications.length > 0 ? (
        <div className="profile-section">
          <h3>Certifications</h3>
          <ul className="simple-list">
            {profile.certifications.map((certification) => <li key={certification}>{certification}</li>)}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
