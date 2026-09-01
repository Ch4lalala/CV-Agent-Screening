"use client";

import { type FormEvent, useRef, useState } from "react";

import { Alert } from "@/components/ui/alert";
import { getErrorMessage, uploadCandidate } from "@/lib/api/client";

interface UploadItem {
  name: string;
  state: "queued" | "uploading" | "uploaded" | "failed";
  message?: string;
}

export function CandidateUpload({
  jobId,
  onComplete,
}: {
  jobId: number;
  onComplete: () => Promise<void>;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [items, setItems] = useState<UploadItem[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (files.length === 0) {
      setError("Choose at least one PDF to upload.");
      return;
    }

    setUploading(true);
    setError(null);
    setItems(files.map((file) => ({ name: file.name, state: "queued" })));
    let createdCandidate = false;

    for (const [index, file] of files.entries()) {
      setItems((current) =>
        current.map((item, itemIndex) =>
          itemIndex === index ? { ...item, state: "uploading" } : item,
        ),
      );
      try {
        const candidate = await uploadCandidate(
          jobId,
          file,
          files.length === 1 ? { name, email } : undefined,
        );
        createdCandidate = true;
        const extractionFailed = candidate.resume.extraction_status === "failed";
        setItems((current) =>
          current.map((item, itemIndex) =>
            itemIndex === index
              ? {
                  ...item,
                  state: extractionFailed ? "failed" : "uploaded",
                  message: extractionFailed
                    ? candidate.resume.message ?? "Text extraction failed."
                    : `${candidate.resume.page_count} page${candidate.resume.page_count === 1 ? "" : "s"} extracted`,
                }
              : item,
          ),
        );
      } catch (uploadError) {
        setItems((current) =>
          current.map((item, itemIndex) =>
            itemIndex === index
              ? {
                  ...item,
                  state: "failed",
                  message: getErrorMessage(uploadError, "Upload failed."),
                }
              : item,
          ),
        );
      }
    }

    if (createdCandidate) {
      try {
        await onComplete();
      } catch {
        setError(
          "The upload completed, but the candidate list could not be refreshed. Reload the page to view the new candidate.",
        );
      }
    }
    setUploading(false);
    setFiles([]);
    setName("");
    setEmail("");
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }

  return (
    <section className="panel upload-panel" aria-labelledby="upload-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Candidate intake</p>
          <h2 id="upload-title">Upload candidate CVs</h2>
          <p>PDF only · maximum 5 MB per file · text-based documents work best</p>
        </div>
        <span className="upload-icon" aria-hidden="true">
          ↑
        </span>
      </div>

      {error ? <Alert>{error}</Alert> : null}

      <form className="upload-form" onSubmit={handleSubmit}>
        <label className="drop-zone" htmlFor="candidate-files">
          <span className="drop-zone-icon" aria-hidden="true">
            PDF
          </span>
          <strong>{files.length > 0 ? `${files.length} file(s) selected` : "Choose PDF files"}</strong>
          <span>
            {files.length > 0
              ? files.map((file) => file.name).join(", ")
              : "Select one or several candidate resumes"}
          </span>
          <input
            ref={inputRef}
            id="candidate-files"
            type="file"
            accept="application/pdf,.pdf"
            multiple
            disabled={uploading}
            onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
          />
        </label>

        <div className="upload-metadata">
          <div className="field field-compact">
            <label htmlFor="candidate-name">Candidate name <span>Optional</span></label>
            <input
              id="candidate-name"
              maxLength={255}
              placeholder="For a single upload"
              disabled={uploading || files.length > 1}
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </div>
          <div className="field field-compact">
            <label htmlFor="candidate-email">Email <span>Optional</span></label>
            <input
              id="candidate-email"
              type="email"
              placeholder="candidate@example.com"
              disabled={uploading || files.length > 1}
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>
          <button className="button button-primary" type="submit" disabled={uploading}>
            {uploading ? "Uploading…" : "Upload CVs"}
          </button>
        </div>
        {files.length > 1 ? (
          <p className="form-note">Name and email are omitted for batch uploads; filenames remain visible.</p>
        ) : null}
      </form>

      {items.length > 0 ? (
        <div className="upload-progress" aria-live="polite">
          {items.map((item, index) => (
            <div className="upload-progress-row" key={`${item.name}-${index}`}>
              <span className={`upload-state upload-state-${item.state}`} aria-hidden="true">
                {item.state === "uploaded" ? "✓" : item.state === "failed" ? "!" : ""}
              </span>
              <div>
                <strong>{item.name}</strong>
                {item.message ? <small>{item.message}</small> : null}
              </div>
              <span>{item.state === "queued" ? "Waiting" : item.state}</span>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}
