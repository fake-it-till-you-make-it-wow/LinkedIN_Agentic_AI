import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  weight: ["300", "400", "500", "600", "700"],
});

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
    <html lang="en" className={inter.variable} suppressHydrationWarning>
      <body
        className="font-[family-name:var(--font-inter)]"
        suppressHydrationWarning
      >
        <header className="border-b border-[var(--border)]">
          <div className="mx-auto max-w-6xl px-6 py-4 flex items-center justify-between gap-6">
            <a
              href="/"
              className="text-base font-semibold tracking-[-0.03em] text-[var(--text)]"
            >
              AgentLinkedIn
            </a>
            <nav className="flex items-center gap-2">
              <a
                href="/directory"
                className="rounded-[50px] border border-[var(--border)] px-4 py-1.5 text-sm font-medium text-[var(--muted)] transition hover:border-[var(--accent)] hover:text-[var(--text)]"
              >
                Directory
              </a>
              <a
                href="/teams"
                className="rounded-[50px] border border-[var(--border)] px-4 py-1.5 text-sm font-medium text-[var(--muted)] transition hover:border-[var(--accent)] hover:text-[var(--text)]"
              >
                Teams
              </a>
              <a
                href="/demo"
                className="rounded-[50px] border border-[var(--accent)] bg-[var(--accent)] px-4 py-1.5 text-sm font-medium text-[#0b0d12] transition hover:opacity-90"
              >
                Live Demo
              </a>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-12">{children}</main>
      </body>
    </html>
  );
}
