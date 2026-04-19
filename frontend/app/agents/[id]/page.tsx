import Link from "next/link";
import { notFound } from "next/navigation";
import { getAgent, getAgentStats, type Agent, type AgentStats } from "@/lib/api";

export const dynamic = "force-dynamic";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-[var(--border)] bg-[var(--surface)] p-4">
      <div className="text-xs uppercase tracking-wide text-[var(--muted)]">
        {label}
      </div>
      <div className="mt-1 text-lg font-semibold">{value}</div>
    </div>
  );
}

function formatDate(value: string | null): string {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

export default async function AgentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let agent: Agent;
  let stats: AgentStats | null = null;
  try {
    agent = await getAgent(id);
  } catch (error) {
    if (error instanceof Error && error.message.startsWith("404")) {
      notFound();
    }
    throw error;
  }
  try {
    stats = await getAgentStats(id);
  } catch {
    stats = null;
  }

  return (
    <article className="space-y-8">
      <div>
        <Link
          href="/"
          className="text-sm text-[var(--muted)] hover:text-[var(--accent)]"
        >
          ← Back to directory
        </Link>
        <div className="mt-4 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold">{agent.name}</h1>
            <p className="mt-2 text-sm text-[var(--muted)]">
              {agent.publisher
                ? `Published by ${agent.publisher.name}${agent.publisher.verified ? " (verified)" : ""}`
                : "Unpublished"}
              {" · "}v{agent.version}
            </p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <span className="rounded-full border border-[var(--border)] px-3 py-1 text-xs text-[var(--muted)]">
              {agent.verified ? "Verified" : "Unverified"}
            </span>
            {agent.endpoint_url ? (
              <a
                href={agent.endpoint_url}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-[var(--accent)] hover:underline"
              >
                {agent.endpoint_url}
              </a>
            ) : null}
          </div>
        </div>
        {agent.description ? (
          <p className="mt-4 text-sm leading-relaxed">{agent.description}</p>
        ) : null}
      </div>

      <section>
        <h2 className="mb-3 text-lg font-semibold">Skills</h2>
        {agent.skill_tags.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {agent.skill_tags.map((tag) => (
              <span
                key={tag}
                className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1 text-sm"
              >
                {tag}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-sm text-[var(--muted)]">No skill tags.</p>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold">Scores</h2>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Stat label="Trust" value={agent.trust_score.toFixed(2)} />
          <Stat label="Community" value={agent.community_score.toFixed(2)} />
          <Stat label="Star Rating" value={agent.star_rating.toFixed(2)} />
          <Stat
            label="Success Rate"
            value={`${(agent.success_rate * 100).toFixed(0)}%`}
          />
        </div>
      </section>

      {stats ? (
        <section>
          <h2 className="mb-3 text-lg font-semibold">Runtime Stats</h2>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat
              label="Total Invocations"
              value={stats.total_invocations.toString()}
            />
            <Stat label="Success" value={stats.success_count.toString()} />
            <Stat label="Errors" value={stats.error_count.toString()} />
            <Stat label="Timeouts" value={stats.timeout_count.toString()} />
            <Stat
              label="Avg Response"
              value={
                stats.avg_response_ms != null
                  ? `${Math.round(stats.avg_response_ms)} ms`
                  : "—"
              }
            />
            <Stat label="Reviews" value={stats.review_count.toString()} />
            <Stat
              label="Last Invoked"
              value={formatDate(stats.last_invoked_at)}
            />
            <Stat label="Status" value={stats.status} />
          </div>
        </section>
      ) : null}

      {agent.career_projects ? (
        <section>
          <h2 className="mb-3 text-lg font-semibold">Career & Projects</h2>
          <pre className="whitespace-pre-wrap rounded-md border border-[var(--border)] bg-[var(--surface)] p-4 text-sm">
            {agent.career_projects}
          </pre>
        </section>
      ) : null}

      {agent.github_repo ? (
        <section>
          <h2 className="mb-3 text-lg font-semibold">GitHub</h2>
          <div className="rounded-md border border-[var(--border)] bg-[var(--surface)] p-4 text-sm">
            <a
              href={`https://github.com/${agent.github_repo}`}
              target="_blank"
              rel="noreferrer"
              className="text-[var(--accent)] hover:underline"
            >
              {agent.github_repo}
            </a>
            <span className="ml-3 text-[var(--muted)]">
              ★ {agent.github_star_count}
            </span>
          </div>
        </section>
      ) : null}
    </article>
  );
}
