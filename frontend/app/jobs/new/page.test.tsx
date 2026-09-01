import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import NewJobPage from "@/app/jobs/new/page";
import { analyzeJobDescription, importJobDocument } from "@/lib/api/client";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/api/client", () => ({
  analyzeJobDescription: vi.fn(),
  createJob: vi.fn(),
  createRequirement: vi.fn(),
  deleteJob: vi.fn(),
  getErrorMessage: (_error: unknown, fallback: string) => fallback,
  importJobDocument: vi.fn(),
}));

const description = `Minimum Qualifications:
- Git is required.
- Candidates must have SQL experience.
Preferred Qualifications:
- Docker experience is a plus.
`;

describe("manual vacancy flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("analyzes the entered description and opens a pre-populated review", async () => {
    vi.mocked(analyzeJobDescription).mockResolvedValue({
      title: "Backend Engineer Intern",
      description,
      requirements: [
        { name: "Git", description: null, type: "required" },
        { name: "SQL", description: null, type: "required" },
        { name: "Docker", description: null, type: "preferred" },
      ],
      warnings: [],
    });
    const user = userEvent.setup();
    render(<NewJobPage />);

    await user.type(screen.getByLabelText("Job title"), "Backend Engineer Intern");
    await user.type(screen.getByLabelText("Job description"), description);
    await user.click(screen.getByRole("button", { name: "Create & review criteria" }));

    expect(analyzeJobDescription).toHaveBeenCalledWith({
      title: "Backend Engineer Intern",
      description,
    });
    expect(await screen.findByText("AI-generated draft — review before continuing")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Git")).toBeInTheDocument();
    expect(screen.getByDisplayValue("SQL")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Docker")).toBeInTheDocument();
  });

  it("falls back to editable empty criteria when AI analysis fails", async () => {
    vi.mocked(analyzeJobDescription).mockRejectedValue(new Error("provider detail"));
    const user = userEvent.setup();
    render(<NewJobPage />);

    await user.type(screen.getByLabelText("Job title"), "Backend Engineer Intern");
    await user.type(screen.getByLabelText("Job description"), "Candidates must have Git.");
    await user.click(screen.getByRole("button", { name: "Create & review criteria" }));

    expect(await screen.findByText(/Qualification suggestions could not be generated/)).toBeInTheDocument();
    expect(screen.queryByText("provider detail")).not.toBeInTheDocument();
    expect(screen.getByText("No required qualifications in this draft.")).toBeInTheDocument();
  });

  it("keeps the existing upload flow routed to the shared review", async () => {
    vi.mocked(importJobDocument).mockResolvedValue({
      title: "Uploaded Engineer",
      description: "Required: Git.",
      requirements: [{ name: "Git", description: null, type: "required" }],
      warnings: [],
    });
    const user = userEvent.setup();
    render(<NewJobPage />);

    await user.click(screen.getByRole("tab", { name: /Upload job document/ }));
    const input = document.querySelector<HTMLInputElement>("input[type='file']");
    expect(input).not.toBeNull();
    const file = new File(["Required: Git."], "role.txt", { type: "text/plain" });
    await user.upload(input as HTMLInputElement, file);
    await user.click(screen.getByRole("button", { name: "Analyze document" }));

    expect(importJobDocument).toHaveBeenCalledWith(file);
    expect(await screen.findByDisplayValue("Uploaded Engineer")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Git")).toBeInTheDocument();
  });
});
