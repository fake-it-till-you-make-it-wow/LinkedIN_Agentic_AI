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
          <div className="mx-auto max-w-6xl px-6 py-4 flex items-center justify-between">
            <a href="/" className="text-lg font-semibold tracking-tight">
              AgentLinkedIn
            </a>
            <span className="text-sm text-[var(--muted)]">
              AI Agent Directory
            </span>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
