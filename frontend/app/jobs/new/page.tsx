"use client";

import Link from "next/link";
import { type FormEvent, useState } from "react";

import { JobDocumentImport } from "@/components/jobs/job-document-import";
import { JobDraftReview } from "@/components/jobs/job-draft-review";
import { PageHeader } from "@/components/layout/page-header";
import { analyzeJobDescription } from "@/lib/api/client";
import type { JobImportDraft } from "@/types/api";

type CreationMode = "manual" | "upload";

export default function NewJobPage() {
  const [mode, setMode] = useState<CreationMode>("manual");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [manualDraft, setManualDraft] = useState<JobImportDraft | null>(null);
  const [fallbackMessage, setFallbackMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setFallbackMessage(null);
    try {
      setManualDraft(await analyzeJobDescription({ title, description }));
    } catch {
      setManualDraft({
        title,
        description,
        requirements: [],
        warnings: [],
      });
      setFallbackMessage(
        "Qualification suggestions could not be generated. You can add them manually.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  function changeMode(nextMode: CreationMode) {
    setMode(nextMode);
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
          id="manual-vacancy-panel"
          role="tabpanel"
        >
          {manualDraft ? (
            <JobDraftReview
              initialDraft={manualDraft}
              onRevise={() => {
                setManualDraft(null);
                setFallbackMessage(null);
              }}
              reviseLabel="Back to job description"
              fallbackMessage={fallbackMessage}
            />
          ) : (
            <div className="form-layout">
              <form className="panel form-panel" onSubmit={handleSubmit}>
                <div className="panel-heading">
                  <div>
                    <p className="section-kicker">Vacancy details</p>
                    <h2>Describe the role</h2>
                  </div>
                  <span className="step-chip">Step 1 of 2</span>
                </div>

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
                    Include required and preferred qualifications. AI will prepare editable criteria for your review.
                  </small>
                </div>

                <div className="form-actions">
                  <Link className="button button-secondary" href="/dashboard">Cancel</Link>
                  <button className="button button-primary" disabled={submitting} type="submit">
                    {submitting ? <span className="button-spinner" aria-hidden="true" /> : null}
                    {submitting ? "Generating criteria…" : "Create & review criteria"}
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
          )}
        </div>
      ) : (
        <div id="upload-vacancy-panel" role="tabpanel">
          <JobDocumentImport />
        </div>
      )}
    </div>
  );
}
