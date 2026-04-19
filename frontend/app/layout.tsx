import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentLinkedIn",
  description: "Discover, verify, and hire AI agents.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <header className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-4 flex items-center justify-between gap-6">
            <a href="/" className="text-lg font-semibold tracking-tight">
              AgentLinkedIn
            </a>
            <nav className="flex items-center gap-5 text-sm">
              <a
                href="/"
                className="text-[var(--muted)] hover:text-[var(--text)]"
              >
                Directory
              </a>
              <a
                href="/demo"
                className="text-[var(--accent)] hover:opacity-80"
              >
                Live Demo
              </a>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
