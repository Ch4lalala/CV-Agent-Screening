"use client";

import { type FormEvent, useMemo, useState } from "react";

import { Alert } from "@/components/ui/alert";
import {
  createRequirement,
  deleteRequirement,
  getErrorMessage,
  updateRequirement,
} from "@/lib/api/client";
import type { JobRequirement, RequirementType } from "@/types/api";

interface RequirementDraft {
  name: string;
  description: string;
  requirement_type: RequirementType;
  priority: string;
}

const emptyDraft: RequirementDraft = {
  name: "",
  description: "",
  requirement_type: "required",
  priority: "",
};

export function RequirementManager({
  jobId,
  requirements,
  onChanged,
}: {
  jobId: number;
  requirements: JobRequirement[];
  onChanged: () => Promise<void>;
}) {
  const [draft, setDraft] = useState<RequirementDraft>(emptyDraft);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const grouped = useMemo(
    () => ({
      required: requirements.filter((item) => item.requirement_type === "required"),
      preferred: requirements.filter((item) => item.requirement_type === "preferred"),
    }),
    [requirements],
  );

  function beginEdit(requirement: JobRequirement) {
    setEditingId(requirement.id);
    setDraft({
      name: requirement.name,
      description: requirement.description ?? "",
      requirement_type: requirement.requirement_type,
      priority: requirement.priority?.toString() ?? "",
    });
    setError(null);
  }

  function resetForm() {
    setEditingId(null);
    setDraft(emptyDraft);
    setError(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    const data = {
      name: draft.name.trim(),
      description: draft.description.trim() || null,
      requirement_type: draft.requirement_type,
      priority: draft.priority === "" ? null : Number(draft.priority),
    };
    try {
      if (editingId === null) {
        await createRequirement(jobId, data);
      } else {
        await updateRequirement(jobId, editingId, data);
      }
      resetForm();
      await onChanged();
    } catch (saveError) {
      setError(getErrorMessage(saveError, "Unable to save this requirement."));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(requirement: JobRequirement) {
    const confirmed = window.confirm(
      `Delete “${requirement.name}”? Historical reports will keep their original snapshot.`,
    );
    if (!confirmed) {
      return;
    }
    setDeletingId(requirement.id);
    setError(null);
    try {
      await deleteRequirement(jobId, requirement.id);
      if (editingId === requirement.id) {
        resetForm();
      }
      await onChanged();
    } catch (deleteError) {
      setError(getErrorMessage(deleteError, "Unable to delete this requirement."));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <section className="panel" aria-labelledby="requirements-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Recruiter-owned criteria</p>
          <h2 id="requirements-title">Qualification requirements</h2>
          <p>These requirements remain authoritative during candidate screening.</p>
        </div>
        <span className="section-count">{requirements.length} total</span>
      </div>

      {error ? <Alert>{error}</Alert> : null}

      <div className="requirements-layout">
        <div className="requirement-groups">
          {(["required", "preferred"] as const).map((type) => (
            <div className="requirement-group" key={type}>
              <div className="requirement-group-heading">
                <h3>{type === "required" ? "Required" : "Preferred"}</h3>
                <span>{grouped[type].length}</span>
              </div>
              {grouped[type].length === 0 ? (
                <p className="inline-empty">No {type} requirements defined.</p>
              ) : (
                <div className="requirement-list">
                  {grouped[type].map((requirement) => (
                    <article className="requirement-item" key={requirement.id}>
                      <div>
                        <div className="requirement-title-line">
                          <strong>{requirement.name}</strong>
                          {requirement.priority !== null ? (
                            <span>Priority {requirement.priority}</span>
                          ) : null}
                        </div>
                        {requirement.description ? <p>{requirement.description}</p> : null}
                      </div>
                      <div className="row-actions">
                        <button
                          className="icon-button"
                          type="button"
                          aria-label={`Edit ${requirement.name}`}
                          onClick={() => beginEdit(requirement)}
                        >
                          Edit
                        </button>
                        <button
                          className="icon-button icon-button-danger"
                          type="button"
                          disabled={deletingId === requirement.id}
                          aria-label={`Delete ${requirement.name}`}
                          onClick={() => void handleDelete(requirement)}
                        >
                          {deletingId === requirement.id ? "Deleting" : "Delete"}
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>

        <form className="requirement-form" onSubmit={handleSubmit}>
          <div className="mini-form-heading">
            <span aria-hidden="true">{editingId === null ? "+" : "✎"}</span>
            <div>
              <strong>{editingId === null ? "Add requirement" : "Edit requirement"}</strong>
              <small>Be concrete and evidence-oriented.</small>
            </div>
          </div>
          <div className="field field-compact">
            <label htmlFor="requirement-name">Name</label>
            <input
              id="requirement-name"
              required
              maxLength={255}
              placeholder="e.g. REST API development"
              value={draft.name}
              onChange={(event) => setDraft({ ...draft, name: event.target.value })}
            />
          </div>
          <div className="field field-compact">
            <label htmlFor="requirement-description">Description</label>
            <textarea
              id="requirement-description"
              rows={3}
              placeholder="What evidence would support this?"
              value={draft.description}
              onChange={(event) => setDraft({ ...draft, description: event.target.value })}
            />
          </div>
          <div className="field-grid">
            <div className="field field-compact">
              <label htmlFor="requirement-type">Type</label>
              <select
                id="requirement-type"
                value={draft.requirement_type}
                onChange={(event) =>
                  setDraft({
                    ...draft,
                    requirement_type: event.target.value as RequirementType,
                  })
                }
              >
                <option value="required">Required</option>
                <option value="preferred">Preferred</option>
              </select>
            </div>
            <div className="field field-compact">
              <label htmlFor="requirement-priority">Priority</label>
              <input
                id="requirement-priority"
                type="number"
                min="0"
                inputMode="numeric"
                placeholder="Optional"
                value={draft.priority}
                onChange={(event) => setDraft({ ...draft, priority: event.target.value })}
              />
            </div>
          </div>
          <div className="mini-form-actions">
            {editingId !== null ? (
              <button className="button button-ghost" type="button" onClick={resetForm}>
                Cancel
              </button>
            ) : null}
            <button className="button button-primary" disabled={saving} type="submit">
              {saving ? "Saving…" : editingId === null ? "Add requirement" : "Save changes"}
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}
