import { titleCase } from "@/lib/format";

export function StatusBadge({ status, label }: { status: string; label?: string }) {
  return (
    <span className={`status-badge status-${status}`}>
      <i aria-hidden="true" />
      {label ?? titleCase(status)}
    </span>
  );
}
