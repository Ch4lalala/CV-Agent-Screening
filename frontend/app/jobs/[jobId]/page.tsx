import { JobDetailClient } from "@/components/jobs/job-detail-client";
import { notFound } from "next/navigation";

export default async function JobDetailPage({
  params,
}: {
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = await params;
  const parsedJobId = Number(jobId);
  if (!Number.isInteger(parsedJobId) || parsedJobId < 1) {
    notFound();
  }
  return <JobDetailClient jobId={parsedJobId} />;
}
