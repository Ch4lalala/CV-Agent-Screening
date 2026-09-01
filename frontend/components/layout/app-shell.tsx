import Link from "next/link";
import type { ReactNode } from "react";

import { Navigation } from "@/components/layout/navigation";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="brand" href="/dashboard" aria-label="ProofHire dashboard">
          <span className="brand-mark" aria-hidden="true">
            P
          </span>
          <span>
            <strong>ProofHire</strong>
            <small>Evidence-first recruiting</small>
          </span>
        </Link>

        <Navigation />

        <div className="sidebar-principle">
          <span className="principle-icon" aria-hidden="true">
            ✓
          </span>
          <div>
            <strong>Human-led decisions</strong>
            <p>AI surfaces evidence. Recruiters stay in control.</p>
          </div>
        </div>
      </aside>

      <div className="workspace">
        <div className="workspace-bar">
          <span>Recruiter workspace</span>
          <span className="environment-chip">
            <i aria-hidden="true" /> Development user
          </span>
        </div>
        <main className="page-content">{children}</main>
      </div>
    </div>
  );
}
