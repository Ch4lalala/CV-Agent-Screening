import { CandidateReportClient } from "@/components/candidates/candidate-report-client";
import { notFound } from "next/navigation";

export default async function HistoricalScreeningPage({
  params,
}: {
  params: Promise<{ candidateId: string; runId: string }>;
}) {
  const { candidateId, runId } = await params;
  const parsedCandidateId = Number(candidateId);
  const parsedRunId = Number(runId);
  if (
    !Number.isInteger(parsedCandidateId) ||
    parsedCandidateId < 1 ||
    !Number.isInteger(parsedRunId) ||
    parsedRunId < 1
  ) {
    notFound();
  }
  return (
    <CandidateReportClient
      candidateId={parsedCandidateId}
      historicalRunId={parsedRunId}
    />
  );
}
