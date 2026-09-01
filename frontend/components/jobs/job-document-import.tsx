"use client";

import { type DragEvent, type FormEvent, useRef, useState } from "react";

import { JobDraftReview } from "@/components/jobs/job-draft-review";
import { Alert } from "@/components/ui/alert";
import { getErrorMessage, importJobDocument } from "@/lib/api/client";
import type { JobImportDraft } from "@/types/api";

const MAX_FILE_BYTES = 5 * 1024 * 1024;
const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".txt"];
const analysisSteps = [
  "Extracting document text",
  "Structuring vacancy information",
  "Identifying atomic qualifications",
  "Preparing recruiter review",
];

function extensionOf(filename: string): string {
  const dotIndex = filename.lastIndexOf(".");
  return dotIndex >= 0 ? filename.slice(dotIndex).toLowerCase() : "";
}

export function JobDocumentImport() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [draft, setDraft] = useState<JobImportDraft | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function chooseFile(selected: File | null) {
    setError(null);
    if (!selected) {
      setFile(null);
      return;
    }
    if (!ALLOWED_EXTENSIONS.includes(extensionOf(selected.name))) {
      setError("Choose a PDF, DOCX, or TXT job document.");
      setFile(null);
      return;
    }
    if (selected.size > MAX_FILE_BYTES) {
      setError("This job document exceeds the maximum size of 5 MB.");
      setFile(null);
      return;
    }
    setFile(selected);
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    chooseFile(event.dataTransfer.files.item(0));
  }

  async function handleImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("Choose a job document before starting analysis.");
      return;
    }
    setAnalyzing(true);
    setError(null);
    try {
      setDraft(await importJobDocument(file));
    } catch (importError) {
      setError(getErrorMessage(importError, "Unable to analyze this job document."));
    } finally {
      setAnalyzing(false);
    }
  }

  function resetImport() {
    setDraft(null);
    setFile(null);
    setError(null);
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }

  if (analyzing) {
    return (
      <section className="panel import-analysis" role="status" aria-live="polite">
        <div className="import-analysis-orbit" aria-hidden="true"><span>AI</span></div>
        <p className="section-kicker">Analysis workflow</p>
        <h2>Analyzing job document…</h2>
        <p>The source remains temporary while the vacancy draft is prepared.</p>
        <div className="import-analysis-steps">
          {analysisSteps.map((step, index) => (
            <div key={step}><span>{index + 1}</span>{step}</div>
          ))}
        </div>
        <small>Stages describe the workflow; exact live step completion is not reported.</small>
      </section>
    );
  }

  if (draft) {
    return (
      <JobDraftReview
        initialDraft={draft}
        onRevise={resetImport}
        reviseLabel="Upload another document"
      />
    );
  }

  return (
    <div className="import-layout">
      <form className="panel import-upload-panel" onSubmit={handleImport}>
        <div className="panel-heading">
          <div>
            <p className="section-kicker">Document-assisted setup</p>
            <h2>Upload job description</h2>
            <p>The document is parsed temporarily and is not retained after analysis.</p>
          </div>
          <span className="step-chip">Draft only</span>
        </div>

        {error ? <Alert>{error}</Alert> : null}

        <label
          className="job-document-drop"
          htmlFor="job-document"
          onDragOver={(event) => event.preventDefault()}
          onDrop={handleDrop}
        >
          <span className="job-document-icon" aria-hidden="true">DOC</span>
          <strong>{file ? file.name : "Choose or drop a job document"}</strong>
          <span>
            {file
              ? `${Math.max(1, Math.round(file.size / 1024))} KB selected`
              : "PDF, DOCX, or TXT · maximum 5 MB"}
          </span>
          <input
            ref={inputRef}
            id="job-document"
            type="file"
            accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
            onChange={(event) => chooseFile(event.target.files?.item(0) ?? null)}
          />
        </label>

        <div className="form-actions">
          <span className="form-note">Scanned PDFs and image/OCR documents are not supported.</span>
          <button className="button button-primary" type="submit" disabled={!file}>
            Analyze document
          </button>
        </div>
      </form>

      <aside className="guidance-card import-guidance">
        <span className="guidance-number">AI</span>
        <h2>Recruiter confirmation is required</h2>
        <p>The generated title, description, and qualifications remain an editable draft.</p>
        <ul>
          <li>No vacancy is created during analysis.</li>
          <li>Combined technologies are split into atomic qualifications.</li>
          <li>Screening never starts automatically.</li>
        </ul>
      </aside>
    </div>
  );
}
