"use client";

import { useRouter } from "next/navigation";
import { type DragEvent, type FormEvent, useRef, useState } from "react";

import { Alert } from "@/components/ui/alert";
import {
  createJob,
  createRequirement,
  deleteJob,
  getErrorMessage,
  importJobDocument,
} from "@/lib/api/client";
import type {
  GeneratedJobRequirement,
  JobImportDraft,
  RequirementType,
} from "@/types/api";

const MAX_FILE_BYTES = 5 * 1024 * 1024;
const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".txt"];
const analysisSteps = [
  "Extracting document text",
  "Structuring vacancy information",
  "Identifying atomic qualifications",
  "Preparing recruiter review",
];

interface EditableRequirement extends GeneratedJobRequirement {
  localId: number;
}

interface EditableDraft extends Omit<JobImportDraft, "requirements"> {
  requirements: EditableRequirement[];
}

function extensionOf(filename: string): string {
  const dotIndex = filename.lastIndexOf(".");
  return dotIndex >= 0 ? filename.slice(dotIndex).toLowerCase() : "";
}

export function JobDocumentImport() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const nextLocalId = useRef(0);
  const [file, setFile] = useState<File | null>(null);
  const [draft, setDraft] = useState<EditableDraft | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdJobId, setCreatedJobId] = useState<number | null>(null);

  function withLocalIds(imported: JobImportDraft): EditableDraft {
    return {
      ...imported,
      requirements: imported.requirements.map((requirement) => ({
        ...requirement,
        localId: ++nextLocalId.current,
      })),
    };
  }

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
      setDraft(withLocalIds(await importJobDocument(file)));
    } catch (importError) {
      setError(getErrorMessage(importError, "Unable to analyze this job document."));
    } finally {
      setAnalyzing(false);
    }
  }

  function updateRequirement(
    localId: number,
    update: Partial<GeneratedJobRequirement>,
  ) {
    setDraft((current) =>
      current
        ? {
            ...current,
            requirements: current.requirements.map((requirement) =>
              requirement.localId === localId
                ? { ...requirement, ...update }
                : requirement,
            ),
          }
        : current,
    );
  }

  function removeRequirement(localId: number) {
    setDraft((current) =>
      current
        ? {
            ...current,
            requirements: current.requirements.filter(
              (requirement) => requirement.localId !== localId,
            ),
          }
        : current,
    );
  }

  function addRequirement(type: RequirementType) {
    setDraft((current) =>
      current
        ? {
            ...current,
            requirements: [
              ...current.requirements,
              {
                localId: ++nextLocalId.current,
                name: "",
                description: null,
                type,
              },
            ],
          }
        : current,
    );
  }

  function resetImport() {
    setDraft(null);
    setFile(null);
    setError(null);
    setCreatedJobId(null);
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }

  async function handleConfirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft) {
      return;
    }
    const title = draft.title?.trim();
    const description = draft.description.trim();
    const requirements = draft.requirements.map((requirement) => ({
      ...requirement,
      name: requirement.name.trim(),
      description: requirement.description?.trim() || null,
    }));
    if (!title || !description || requirements.some((item) => !item.name)) {
      setError("Add a job title, description, and a name for every qualification.");
      return;
    }

    setCreating(true);
    setError(null);
    setCreatedJobId(null);
    let jobId: number | null = null;
    try {
      const job = await createJob({ title, description });
      jobId = job.id;
      for (const [index, requirement] of requirements.entries()) {
        await createRequirement(job.id, {
          name: requirement.name,
          description: requirement.description,
          requirement_type: requirement.type,
          priority: index + 1,
        });
      }
      router.push(`/jobs/${job.id}`);
    } catch (createError) {
      if (jobId !== null) {
        try {
          await deleteJob(jobId);
          jobId = null;
        } catch {
          setCreatedJobId(jobId);
        }
      }
      setError(
        getErrorMessage(
          createError,
          "The vacancy could not be created. Review the draft and try again.",
        ),
      );
      setCreating(false);
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

  if (!draft) {
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

  return (
    <form className="import-review" onSubmit={handleConfirm}>
      <div className="draft-banner">
        <div>
          <span aria-hidden="true">✦</span>
          <div>
            <strong>AI-generated draft — review before continuing</strong>
            <p>Edit every field as needed. Confirmed qualifications become recruiter-authoritative.</p>
          </div>
        </div>
        <button className="button button-secondary" type="button" onClick={resetImport}>
          Upload another document
        </button>
      </div>

      {error ? (
        <Alert title="Vacancy draft needs attention">
          <p>{error}</p>
          {createdJobId ? (
            <button
              className="text-button"
              type="button"
              onClick={() => router.push(`/jobs/${createdJobId}`)}
            >
              Open the partially created vacancy
            </button>
          ) : null}
        </Alert>
      ) : null}

      <section className="panel draft-details">
        <div className="panel-heading">
          <div>
            <p className="section-kicker">Vacancy draft</p>
            <h2>Review role information</h2>
          </div>
          <span className="step-chip">Human review</span>
        </div>
        <div className="field">
          <label htmlFor="import-title">Job title</label>
          <input
            id="import-title"
            required
            maxLength={255}
            value={draft.title ?? ""}
            onChange={(event) => setDraft({ ...draft, title: event.target.value })}
          />
        </div>
        <div className="field">
          <label htmlFor="import-description">Job description</label>
          <textarea
            id="import-description"
            required
            rows={8}
            value={draft.description}
            onChange={(event) => setDraft({ ...draft, description: event.target.value })}
          />
        </div>
      </section>

      <section className="panel draft-requirements">
        <div className="panel-heading">
          <div>
            <p className="section-kicker">Atomic qualifications</p>
            <h2>Review requirements</h2>
            <p>Each row should describe one independently verifiable qualification.</p>
          </div>
          <span className="section-count">{draft.requirements.length} total</span>
        </div>

        {(["required", "preferred"] as const).map((type) => {
          const grouped = draft.requirements.filter((item) => item.type === type);
          return (
            <div className="draft-requirement-group" key={type}>
              <div className="draft-group-heading">
                <h3>{type === "required" ? "Required qualifications" : "Preferred qualifications"}</h3>
                <button className="text-button" type="button" onClick={() => addRequirement(type)}>
                  + Add requirement
                </button>
              </div>
              {grouped.length === 0 ? (
                <p className="inline-empty">No {type} qualifications in this draft.</p>
              ) : (
                <div className="draft-edit-list">
                  {grouped.map((requirement) => (
                    <article className="draft-edit-row" key={requirement.localId}>
                      <div className="draft-edit-fields">
                        <div className="field field-compact">
                          <label htmlFor={`requirement-name-${requirement.localId}`}>Name</label>
                          <input
                            id={`requirement-name-${requirement.localId}`}
                            required
                            maxLength={255}
                            value={requirement.name}
                            onChange={(event) => updateRequirement(requirement.localId, { name: event.target.value })}
                          />
                        </div>
                        <div className="field field-compact">
                          <label htmlFor={`requirement-description-${requirement.localId}`}>Description</label>
                          <input
                            id={`requirement-description-${requirement.localId}`}
                            value={requirement.description ?? ""}
                            onChange={(event) => updateRequirement(requirement.localId, { description: event.target.value || null })}
                          />
                        </div>
                        <div className="field field-compact">
                          <label htmlFor={`requirement-type-${requirement.localId}`}>Type</label>
                          <select
                            id={`requirement-type-${requirement.localId}`}
                            value={requirement.type}
                            onChange={(event) => updateRequirement(requirement.localId, { type: event.target.value as RequirementType })}
                          >
                            <option value="required">Required</option>
                            <option value="preferred">Preferred</option>
                          </select>
                        </div>
                      </div>
                      <button
                        className="icon-button icon-button-danger"
                        type="button"
                        onClick={() => removeRequirement(requirement.localId)}
                      >
                        Remove
                      </button>
                    </article>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </section>

      {draft.warnings.length > 0 ? (
        <section className="draft-warnings" aria-labelledby="draft-warnings-title">
          <div className="draft-warning-heading">
            <span aria-hidden="true">!</span>
            <div>
              <p className="section-kicker">Recruiter review</p>
              <h2 id="draft-warnings-title">Document notes</h2>
            </div>
          </div>
          <div className="draft-warning-list">
            {draft.warnings.map((warning, index) => (
              <article key={`${warning.type}-${index}`}>
                <strong>{warning.message}</strong>
                {warning.related_text ? <p>Related context: {warning.related_text}</p> : null}
              </article>
            ))}
          </div>
        </section>
      ) : null}

      <div className="draft-confirm-bar">
        <div>
          <strong>Ready to create this vacancy?</strong>
          <p>This saves the edited draft and its requirements. Candidate screening remains separate.</p>
        </div>
        <button
          className="button button-primary"
          type="submit"
          disabled={creating || createdJobId !== null}
        >
          {creating ? "Creating vacancy…" : "Confirm & create vacancy"}
        </button>
      </div>
    </form>
  );
}
