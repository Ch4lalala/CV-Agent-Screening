import { CandidateReportClient } from "@/components/candidates/candidate-report-client";
import { notFound } from "next/navigation";

export default async function CandidatePage({
  params,
}: {
  params: Promise<{ candidateId: string }>;
}) {
  const { candidateId } = await params;
  const parsedCandidateId = Number(candidateId);
  if (!Number.isInteger(parsedCandidateId) || parsedCandidateId < 1) {
    notFound();
  }
  return <CandidateReportClient candidateId={parsedCandidateId} />;
}
