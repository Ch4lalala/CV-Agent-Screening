"use client";

import { useState } from "react";

import type { InterviewQuestion } from "@/types/api";

export function InterviewQuestions({ questions }: { questions: InterviewQuestion[] }) {
  const [copiedId, setCopiedId] = useState<number | null>(null);

  async function copyQuestion(item: InterviewQuestion) {
    try {
      await navigator.clipboard.writeText(item.question);
      setCopiedId(item.id);
      window.setTimeout(() => setCopiedId(null), 1800);
    } catch {
      setCopiedId(null);
    }
  }

  return (
    <section className="panel" aria-labelledby="questions-title">
      <div className="panel-heading">
        <div>
          <p className="section-kicker">Prepared from uncertainty</p>
          <h2 id="questions-title">Suggested interview questions</h2>
          <p>Use these prompts during human review; nothing is sent automatically.</p>
        </div>
        <span className="section-count">{questions.length} questions</span>
      </div>
      {questions.length === 0 ? (
        <p className="inline-empty">No targeted interview questions were generated for this run.</p>
      ) : (
        <ol className="question-list">
          {questions.map((item) => (
            <li key={item.id}>
              <span className="question-number" aria-hidden="true" />
              <div>
                {item.requirement_name ? <small>{item.requirement_name}</small> : null}
                <p>{item.question}</p>
              </div>
              <button
                className="copy-button"
                type="button"
                onClick={() => void copyQuestion(item)}
                aria-label={`Copy interview question about ${item.requirement_name ?? "the candidate"}`}
              >
                {copiedId === item.id ? "Copied" : "Copy"}
              </button>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
