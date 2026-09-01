"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useRef, useState } from "react";

import { Alert } from "@/components/ui/alert";
import {
  createJob,
  createRequirement,
  deleteJob,
  getErrorMessage,
} from "@/lib/api/client";
import type {
  GeneratedJobRequirement,
  JobImportDraft,
  RequirementType,
} from "@/types/api";

interface EditableRequirement extends GeneratedJobRequirement {
  localId: number;
}

interface EditableDraft extends Omit<JobImportDraft, "requirements"> {
  requirements: EditableRequirement[];
}

interface JobDraftReviewProps {
  initialDraft: JobImportDraft;
  onRevise: () => void;
  reviseLabel: string;
  fallbackMessage?: string | null;
}

export function JobDraftReview({
  initialDraft,
  onRevise,
  reviseLabel,
  fallbackMessage = null,
}: JobDraftReviewProps) {
  const router = useRouter();
  const nextLocalId = useRef(initialDraft.requirements.length);
  const [draft, setDraft] = useState<EditableDraft>(() => ({
    ...initialDraft,
    requirements: initialDraft.requirements.map((requirement, index) => ({
      ...requirement,
      localId: index + 1,
    })),
  }));
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdJobId, setCreatedJobId] = useState<number | null>(null);

  function updateRequirement(
    localId: number,
    update: Partial<GeneratedJobRequirement>,
  ) {
    setDraft((current) => ({
      ...current,
      requirements: current.requirements.map((requirement) =>
        requirement.localId === localId
          ? { ...requirement, ...update }
          : requirement,
      ),
    }));
  }

  function removeRequirement(localId: number) {
    setDraft((current) => ({
      ...current,
      requirements: current.requirements.filter(
        (requirement) => requirement.localId !== localId,
      ),
    }));
  }

  function addRequirement(type: RequirementType) {
    setDraft((current) => ({
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
    }));
  }

  async function handleConfirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const title = draft.title?.trim();
    const description = draft.description.trim();
    const requirements = draft.requirements.map((requirement) => ({
      name: requirement.name.trim(),
      description: requirement.description?.trim() || null,
      type: requirement.type,
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
        <button className="button button-secondary" type="button" onClick={onRevise}>
          {reviseLabel}
        </button>
      </div>

      {fallbackMessage ? (
        <Alert title="Manual criteria entry available">{fallbackMessage}</Alert>
      ) : null}

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
          <label htmlFor="draft-title">Job title</label>
          <input
            id="draft-title"
            required
            maxLength={255}
            value={draft.title ?? ""}
            onChange={(event) => setDraft({ ...draft, title: event.target.value })}
          />
        </div>
        <div className="field">
          <label htmlFor="draft-description">Job description</label>
          <textarea
            id="draft-description"
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
              <h2 id="draft-warnings-title">Analysis notes</h2>
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
