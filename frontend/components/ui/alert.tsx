import type { ReactNode } from "react";

export function Alert({
  tone = "error",
  title,
  children,
}: {
  tone?: "error" | "warning" | "info" | "success";
  title?: string;
  children: ReactNode;
}) {
  return (
    <div className={`alert alert-${tone}`} role={tone === "error" ? "alert" : "status"}>
      <span className="alert-icon" aria-hidden="true">
        {tone === "success" ? "✓" : tone === "info" ? "i" : "!"}
      </span>
      <div>
        {title ? <strong>{title}</strong> : null}
        <div>{children}</div>
      </div>
    </div>
  );
}
