import Link from "next/link";
import { listAgents, type Agent } from "@/lib/api";

export const dynamic = "force-dynamic";

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(0)}%`;
}

function ScoreBadge({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex flex-col items-start rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 py-2">
      <span className="text-xs uppercase tracking-wide text-[var(--muted)]">
        {label}
      </span>
      <span className="text-sm font-medium">{value.toFixed(2)}</span>
    </div>
  );
}

function AgentCard({ agent }: { agent: Agent }) {
  return (
    <Link
      href={`/agents/${agent.id}`}
      className="block rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5 transition hover:border-[var(--accent)]"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">{agent.name}</h2>
          {agent.publisher ? (
            <p className="mt-1 text-sm text-[var(--muted)]">
              by {agent.publisher.name}
              {agent.publisher.verified ? " · verified" : ""}
            </p>
          ) : (
            <p className="mt-1 text-sm text-[var(--muted)]">Unpublished</p>
          )}
        </div>
        <span className="shrink-0 rounded-full border border-[var(--border)] px-3 py-1 text-xs text-[var(--muted)]">
          v{agent.version}
        </span>
      </div>
      {agent.description ? (
        <p className="mt-3 line-clamp-3 text-sm text-[var(--text)]">
          {agent.description}
        </p>
      ) : null}
      <div className="mt-4 flex flex-wrap gap-2">
        {agent.skill_tags.slice(0, 6).map((tag) => (
          <span
            key={tag}
            className="rounded-full border border-[var(--border)] px-2 py-1 text-xs text-[var(--muted)]"
          >
            {tag}
          </span>
        ))}
      </div>
      <div className="mt-4 grid grid-cols-3 gap-2">
        <ScoreBadge label="Trust" value={agent.trust_score} />
        <ScoreBadge label="Community" value={agent.community_score} />
        <ScoreBadge label="Success" value={agent.success_rate} />
      </div>
      <div className="mt-3 flex justify-between text-xs text-[var(--muted)]">
        <span>★ {agent.star_rating.toFixed(1)}</span>
        <span>{agent.total_calls} calls</span>
        <span>{formatPercent(agent.success_rate)} success</span>
      </div>
    </Link>
  );
}

export default async function HomePage() {
  let agents: Agent[] = [];
  let errorMessage: string | null = null;
  try {
    agents = await listAgents();
  } catch (error) {
    errorMessage =
      error instanceof Error ? error.message : "Failed to load agents";
  }

  return (
    <section>
      <div className="mb-6 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Directory</h1>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Browse verified AI agents and their publishers.
          </p>
        </div>
        <span className="text-sm text-[var(--muted)]">
          {agents.length} agents
        </span>
      </div>
      {errorMessage ? (
        <div className="rounded-md border border-[var(--border)] bg-[var(--surface)] p-4 text-sm text-[var(--muted)]">
          Backend unreachable: {errorMessage}
        </div>
      ) : agents.length === 0 ? (
        <div className="rounded-md border border-[var(--border)] bg-[var(--surface)] p-4 text-sm text-[var(--muted)]">
          No agents registered yet.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>
      )}
    </section>
  );
}
