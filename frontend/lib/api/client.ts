import type {
  Candidate,
  CandidateComparison,
  CandidateReport,
  CandidateUploadResponse,
  Job,
  JobCreateInput,
  JobImportDraft,
  JobRequirement,
  JobUpdateInput,
  RequirementInput,
  ResumeMetadata,
  ScreeningProgressResponse,
  ScreeningRun,
  ScreeningStart,
} from "@/types/api";

interface BackendErrorBody {
  detail?: unknown;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly detail?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function getApiBaseUrl(): string {
  const value = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (!value) {
    throw new ApiError("Frontend API URL is not configured.", 0);
  }
  return value.replace(/\/$/, "");
}

function detailText(detail: unknown): string | undefined {
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    const firstMessage = detail.find(
      (entry): entry is { msg: string } =>
        typeof entry === "object" &&
        entry !== null &&
        "msg" in entry &&
        typeof entry.msg === "string",
    );
    return firstMessage?.msg;
  }
  return undefined;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${getApiBaseUrl()}${path}`, {
      ...init,
      cache: "no-store",
      headers: {
        Accept: "application/json",
        ...init.headers,
      },
    });
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError("Unable to connect to the application API.", 0);
  }

  if (!response.ok) {
    let body: BackendErrorBody = {};
    try {
      body = (await response.json()) as BackendErrorBody;
    } catch {
      // Non-JSON upstream errors are intentionally not exposed to the UI.
    }
    const detail = detailText(body.detail);
    throw new ApiError(detail ?? "The request could not be completed.", response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

function jsonRequest(method: "POST" | "PATCH", body: object): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

export function getErrorMessage(error: unknown, fallback: string): string {
  if (!(error instanceof ApiError)) {
    return fallback;
  }
  if (error.status === 0) {
    return "The application API is unavailable. Check that the backend is running.";
  }
  if (error.status === 404) {
    return error.detail ?? "The requested resource was not found.";
  }
  if (error.status === 409) {
    return error.detail ?? "This action conflicts with the current resource state.";
  }
  if (error.status === 413) {
    return error.detail ?? "The uploaded file exceeds the configured maximum size.";
  }
  if (error.status === 503) {
    return "AI service is not configured or temporarily unavailable.";
  }
  if (error.status === 400 || error.status === 422) {
    return error.detail ?? "Please check the submitted information and try again.";
  }
  return fallback;
}

export const getJobs = () => request<Job[]>("/api/v1/jobs");

export const createJob = (data: JobCreateInput) =>
  request<Job>("/api/v1/jobs", jsonRequest("POST", data));

export const analyzeJobDescription = (data: Pick<JobCreateInput, "title" | "description">) =>
  request<JobImportDraft>(
    "/api/v1/jobs/analyze-description",
    jsonRequest("POST", data),
  );

export async function importJobDocument(file: File): Promise<JobImportDraft> {
  const form = new FormData();
  form.append("file", file);
  return request<JobImportDraft>("/api/v1/jobs/import", {
    method: "POST",
    body: form,
  });
}

export const getJob = (jobId: number) => request<Job>(`/api/v1/jobs/${jobId}`);

export const updateJob = (jobId: number, data: JobUpdateInput) =>
  request<Job>(`/api/v1/jobs/${jobId}`, jsonRequest("PATCH", data));

export const deleteJob = (jobId: number) =>
  request<void>(`/api/v1/jobs/${jobId}`, { method: "DELETE" });

export const getRequirements = (jobId: number) =>
  request<JobRequirement[]>(`/api/v1/jobs/${jobId}/requirements`);

export const createRequirement = (jobId: number, data: RequirementInput) =>
  request<JobRequirement>(
    `/api/v1/jobs/${jobId}/requirements`,
    jsonRequest("POST", data),
  );

export const updateRequirement = (
  jobId: number,
  requirementId: number,
  data: Partial<RequirementInput>,
) =>
  request<JobRequirement>(
    `/api/v1/jobs/${jobId}/requirements/${requirementId}`,
    jsonRequest("PATCH", data),
  );

export const deleteRequirement = (jobId: number, requirementId: number) =>
  request<void>(`/api/v1/jobs/${jobId}/requirements/${requirementId}`, {
    method: "DELETE",
  });

export const getCandidates = (jobId: number) =>
  request<Candidate[]>(`/api/v1/jobs/${jobId}/candidates`);

export const getCandidateComparison = (jobId: number) =>
  request<CandidateComparison>(`/api/v1/jobs/${jobId}/candidate-comparison`);

export const getCandidate = (candidateId: number) =>
  request<Candidate>(`/api/v1/candidates/${candidateId}`);

export const getCandidateResume = (candidateId: number) =>
  request<ResumeMetadata>(`/api/v1/candidates/${candidateId}/resume`);

export async function uploadCandidate(
  jobId: number,
  file: File,
  metadata?: { name?: string; email?: string },
): Promise<CandidateUploadResponse> {
  const form = new FormData();
  form.append("file", file);
  if (metadata?.name?.trim()) {
    form.append("name", metadata.name.trim());
  }
  if (metadata?.email?.trim()) {
    form.append("email", metadata.email.trim());
  }
  return request<CandidateUploadResponse>(`/api/v1/jobs/${jobId}/candidates`, {
    method: "POST",
    body: form,
  });
}

export const screenCandidate = (candidateId: number) =>
  request<ScreeningStart>(`/api/v1/candidates/${candidateId}/screen`, {
    method: "POST",
  });

export const getLatestScreening = (candidateId: number) =>
  request<CandidateReport>(`/api/v1/candidates/${candidateId}/screening`);

export const getScreeningHistory = (candidateId: number) =>
  request<ScreeningRun[]>(`/api/v1/candidates/${candidateId}/screenings`);

export const getScreeningRun = (candidateId: number, runId: number) =>
  request<CandidateReport>(
    `/api/v1/candidates/${candidateId}/screenings/${runId}`,
  );

export const getScreeningProgress = (candidateId: number, runId: number) =>
  request<ScreeningProgressResponse>(
    `/api/v1/candidates/${candidateId}/screenings/${runId}`,
  );
