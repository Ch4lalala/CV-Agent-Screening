"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navigation = [
  { href: "/dashboard", label: "Dashboard", icon: "grid" },
  { href: "/dashboard", label: "Jobs", icon: "briefcase" },
] as const;

function NavIcon({ name }: { name: "grid" | "briefcase" }) {
  if (name === "briefcase") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M8 7V5.8A1.8 1.8 0 0 1 9.8 4h4.4A1.8 1.8 0 0 1 16 5.8V7m-13 4.5h18M5 7h14a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2Z" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 4h6v6H4V4Zm10 0h6v6h-6V4ZM4 14h6v6H4v-6Zm10 0h6v6h-6v-6Z" />
    </svg>
  );
}

export function Navigation() {
  const pathname = usePathname();

  return (
    <nav className="sidebar-nav" aria-label="Primary navigation">
      <p className="sidebar-label">Workspace</p>
      {navigation.map((item, index) => {
        const active =
          index === 0
            ? pathname === "/dashboard"
            : pathname.startsWith("/jobs") || pathname.startsWith("/candidates");
        return (
          <Link
            className={`nav-link${active ? " nav-link-active" : ""}`}
            href={item.href}
            key={item.label}
          >
            <NavIcon name={item.icon} />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
