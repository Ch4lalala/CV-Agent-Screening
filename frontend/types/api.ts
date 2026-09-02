export type JobStatus = "draft" | "active" | "closed";
export type RequirementType = "required" | "preferred";
export type CandidateStatus = "uploaded" | "processing" | "completed" | "failed";
export type ResumeExtractionStatus = "pending" | "completed" | "failed";
export type ScreeningRunStatus = "pending" | "processing" | "completed" | "failed";
export type ScreeningStage =
  | "queued"
  | "normalize_requirements"
  | "extract_candidate_profile"
  | "match_evidence"
  | "analyze_uncertainty"
  | "generate_interview_questions"
  | "generate_report"
  | "completed"
  | "failed";
export type EvidenceStatus = "supported" | "partial" | "no_evidence";
export type EvidenceConfidence = "high" | "medium" | "low";
export type ReviewLabel =
  | "strong_evidence"
  | "moderate_evidence"
  | "needs_verification";

export interface Job {
  id: number;
  user_id: number;
  title: string;
  description: string;
  status: JobStatus;
  created_at: string;
  updated_at: string;
}

export interface JobCreateInput {
  title: string;
  description: string;
  status?: JobStatus;
}

export interface JobUpdateInput {
  title?: string;
  description?: string;
  status?: JobStatus;
}

export interface JobRequirement {
  id: number;
  job_id: number;
  name: string;
  description: string | null;
  requirement_type: RequirementType;
  priority: number | null;
  created_at: string;
}

export interface RequirementInput {
  name: string;
  description?: string | null;
  requirement_type: RequirementType;
  priority?: number | null;
}

export type JobImportWarningType =
  | "ambiguous_requirement"
  | "excluded_personal_criterion"
  | "composite_requirement"
  | "duplicate_requirement"
  | "inferred_title"
  | "review_required";

export interface GeneratedJobRequirement {
  name: string;
  description: string | null;
  type: RequirementType;
}

export interface JobImportWarning {
  type: JobImportWarningType;
  message: string;
  related_text: string | null;
}

export interface JobImportDraft {
  title: string | null;
  description: string;
  requirements: GeneratedJobRequirement[];
  warnings: JobImportWarning[];
}

export interface Candidate {
  id: number;
  job_id: number;
  name: string | null;
  email: string | null;
  original_filename: string | null;
  status: CandidateStatus;
  created_at: string;
  updated_at: string;
}

export interface ResumeMetadata {
  original_filename: string;
  page_count: number;
  extraction_status: ResumeExtractionStatus;
  text_length: number;
  message: string | null;
}

export interface ResumeSummary {
  page_count: number;
  extraction_status: ResumeExtractionStatus;
  text_length: number;
  message: string | null;
}

export interface CandidateUploadResponse extends Candidate {
  resume: ResumeSummary;
}

export interface ScreeningRun {
  id: number;
  candidate_id: number;
  status: ScreeningRunStatus;
  current_stage: ScreeningStage;
  current_stage_updated_at: string;
  model_name: string | null;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  created_at: string;
}

export interface ScreeningStart {
  screening_run_id: number;
  candidate_id: number;
  status: ScreeningRunStatus;
  current_stage: ScreeningStage;
}

export interface Coverage {
  supported: number;
  total: number;
}

export interface CoverageCounts extends Coverage {
  partial: number;
  no_evidence: number;
}

export interface CandidateComparisonItem {
  candidate_id: number;
  name: string | null;
  email: string | null;
  original_filename: string | null;
  status: CandidateStatus;
  created_at: string;
  resume_extraction_status: ResumeExtractionStatus | null;
  latest_completed_run_id: number | null;
  latest_completed_at: string | null;
  active_screening_run_id: number | null;
  active_screening_stage: ScreeningStage | null;
  active_screening_stage_updated_at: string | null;
  required: CoverageCounts | null;
  preferred: CoverageCounts | null;
  needs_verification_count: number | null;
  review_priority: number | null;
  review_label: ReviewLabel | null;
  comparable_evidence: boolean;
}

export interface CandidateComparison {
  job_id: number;
  candidates: CandidateComparisonItem[];
}

export interface EvidenceItem {
  id: number;
  quote: string;
  source_section: string | null;
  source_page: number | null;
  created_at: string;
}

export interface EvidenceResult {
  id: number;
  requirement_id: number | null;
  requirement_name: string;
  requirement_type: RequirementType;
  status: EvidenceStatus;
  confidence: EvidenceConfidence;
  explanation: string;
  needs_human_verification: boolean;
  evidence_items: EvidenceItem[];
  created_at: string;
}

export interface InterviewQuestion {
  id: number;
  requirement_name: string | null;
  question: string;
  created_at: string;
}

export interface CandidateExperience {
  role: string | null;
  company: string | null;
  period: string | null;
  description: string[];
}

export interface CandidateEducation {
  institution: string | null;
  qualification: string | null;
  field_of_study: string | null;
  period: string | null;
}

export interface CandidateProject {
  name: string | null;
  description: string[];
  technologies: string[];
  url: string | null;
}

export interface CandidateProfile {
  candidate_name: string | null;
  email: string | null;
  phone: string | null;
  skills: string[];
  work_experience: CandidateExperience[];
  education: CandidateEducation[];
  projects: CandidateProject[];
  certifications: string[];
  github_urls: string[];
  portfolio_urls: string[];
}

export interface NormalizedRequirement {
  source_requirement_id: number | null;
  name: string;
  description: string | null;
  requirement_type: RequirementType;
  source: "recruiter" | "ai_derived";
  priority: number | null;
  recruiter_name: string | null;
  recruiter_description: string | null;
}

export interface CandidateReport {
  screening_run: ScreeningRun;
  candidate: Pick<Candidate, "id" | "name" | "email" | "status">;
  job_title: string;
  normalized_requirements: NormalizedRequirement[];
  candidate_profile: CandidateProfile;
  coverage: {
    required: Coverage;
    preferred: Coverage;
  };
  evidence_results: EvidenceResult[];
  needs_verification: string[];
  interview_questions: InterviewQuestion[];
  security_warning: null;
}

export type ScreeningProgressResponse = ScreeningRun | CandidateReport;
