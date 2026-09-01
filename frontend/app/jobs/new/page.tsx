"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { JobDocumentImport } from "@/components/jobs/job-document-import";
import { PageHeader } from "@/components/layout/page-header";
import { Alert } from "@/components/ui/alert";
import { createJob, getErrorMessage } from "@/lib/api/client";

type CreationMode = "manual" | "upload";

export default function NewJobPage() {
  const router = useRouter();
  const [mode, setMode] = useState<CreationMode>("manual");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const job = await createJob({ title, description });
      router.push(`/jobs/${job.id}`);
    } catch (submitError) {
      setError(getErrorMessage(submitError, "Unable to create this vacancy."));
      setSubmitting(false);
    }
  }

  function changeMode(nextMode: CreationMode) {
    setMode(nextMode);
    setError(null);
  }

  return (
    <div className="page-stack vacancy-create-page">
      <div className="breadcrumbs" aria-label="Breadcrumb">
        <Link href="/dashboard">Vacancies</Link>
        <span aria-hidden="true">/</span>
        <span>Create vacancy</span>
      </div>
      <PageHeader
        eyebrow="New recruitment brief"
        title="Create a vacancy"
        description="Write the role yourself or turn a job document into an editable, recruiter-reviewed draft."
      />

      <section className="creation-mode-section" aria-labelledby="creation-mode-title">
        <div>
          <p className="section-kicker">Starting point</p>
          <h2 id="creation-mode-title">How would you like to start?</h2>
        </div>
        <div className="creation-mode-tabs" role="tablist" aria-label="Vacancy creation mode">
          <button
            className={mode === "manual" ? "creation-mode-active" : ""}
            type="button"
            role="tab"
            aria-selected={mode === "manual"}
            aria-controls="manual-vacancy-panel"
            onClick={() => changeMode("manual")}
          >
            <span aria-hidden="true">✎</span>
            <span><strong>Write manually</strong><small>Enter the role yourself</small></span>
          </button>
          <button
            className={mode === "upload" ? "creation-mode-active" : ""}
            type="button"
            role="tab"
            aria-selected={mode === "upload"}
            aria-controls="upload-vacancy-panel"
            onClick={() => changeMode("upload")}
          >
            <span aria-hidden="true">↑</span>
            <span><strong>Upload job document</strong><small>Generate an editable AI draft</small></span>
          </button>
        </div>
      </section>

      {mode === "manual" ? (
        <div
          className="form-layout"
          id="manual-vacancy-panel"
          role="tabpanel"
        >
          <form className="panel form-panel" onSubmit={handleSubmit}>
            <div className="panel-heading">
              <div>
                <p className="section-kicker">Vacancy details</p>
                <h2>Describe the role</h2>
              </div>
              <span className="step-chip">Step 1 of 2</span>
            </div>

            {error ? <Alert>{error}</Alert> : null}

            <div className="field">
              <label htmlFor="job-title">Job title</label>
              <input
                id="job-title"
                name="title"
                placeholder="e.g. Backend Engineer Intern"
                required
                maxLength={255}
                value={title}
                onChange={(event) => setTitle(event.target.value)}
              />
              <small>Use the title candidates will recognize.</small>
            </div>

            <div className="field">
              <label htmlFor="job-description">Job description</label>
              <textarea
                id="job-description"
                name="description"
                placeholder="Describe the role, responsibilities, team context, and the evidence you want to review..."
                required
                rows={12}
                value={description}
                onChange={(event) => setDescription(event.target.value)}
              />
              <small>
                Requirements are added manually after creation. AI analysis will not run automatically.
              </small>
            </div>

            <div className="form-actions">
              <Link className="button button-secondary" href="/dashboard">Cancel</Link>
              <button className="button button-primary" disabled={submitting} type="submit">
                {submitting ? <span className="button-spinner" aria-hidden="true" /> : null}
                {submitting ? "Creating vacancy" : "Create vacancy"}
              </button>
            </div>
          </form>

          <aside className="guidance-card">
            <span className="guidance-number">01</span>
            <h2>Evidence starts with clarity</h2>
            <p>A focused job description helps the screening workflow compare candidates against the right context.</p>
            <ul>
              <li>Describe concrete responsibilities.</li>
              <li>Keep required and preferred criteria distinct.</li>
              <li>Avoid traits that cannot be evidenced consistently.</li>
            </ul>
          </aside>
        </div>
      ) : (
        <div id="upload-vacancy-panel" role="tabpanel">
          <JobDocumentImport />
        </div>
      )}
    </div>
  );
}
