"use client";

import { useEffect, useState } from "react";

type TeamMember = { id: string; name: string; role: string };
type TeamStats = {
  searches: number;
  invokes: number;
  dms: number;
  human_intervention: number;
} | null;
type TeamRead = {
  id: string;
  mission: string;
  members: TeamMember[];
  stats: TeamStats;
  created_at: string;
};

const API = "http://localhost:8000";

function formatDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/* ── Delete Confirmation Modal ───────────────────────────────── */
function DeleteModal({
  team,
  deleting,
  onCancel,
  onConfirm,
}: {
  team: TeamRead;
  deleting: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center px-4"
      style={{ background: "rgba(0,0,0,0.35)", backdropFilter: "blur(4px)" }}
    >
      <div
        className="w-full max-w-sm rounded-lg border border-black bg-white p-8"
        style={{ fontFeatureSettings: '"kern"' }}
      >
        <p
          className="text-xl font-semibold leading-[1.35] text-black"
          style={{ letterSpacing: "-0.26px" }}
        >
          팀을 삭제하시겠습니까?
        </p>
        <p
          className="mt-3 line-clamp-2 text-sm font-light leading-snug text-black/50"
          style={{ letterSpacing: "-0.14px" }}
        >
          {team.mission}
        </p>
        <p
          className="mt-2 text-xs text-black/40"
          style={{ letterSpacing: "-0.1px" }}
        >
          이 작업은 되돌릴 수 없습니다.
        </p>
        <div className="mt-8 flex justify-end gap-3">
          <button
            onClick={onCancel}
            disabled={deleting}
            className="rounded-full border border-black px-5 py-2 text-sm font-medium text-black transition hover:bg-black/5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-dashed focus-visible:outline-black disabled:opacity-40"
            style={{ letterSpacing: "-0.14px" }}
          >
            취소
          </button>
          <button
            onClick={onConfirm}
            disabled={deleting}
            className="rounded-full bg-black px-5 py-2 text-sm font-medium text-white transition hover:opacity-80 focus-visible:outline focus-visible:outline-2 focus-visible:outline-dashed focus-visible:outline-black disabled:opacity-40"
            style={{ letterSpacing: "-0.14px" }}
          >
            {deleting ? "삭제 중…" : "삭제"}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Team Card ───────────────────────────────────────────────── */
function TeamCard({
  team,
  index,
  onDelete,
}: {
  team: TeamRead;
  index: number;
  onDelete: (team: TeamRead) => void;
}) {
  return (
    <article
      className="flex flex-col rounded-lg border border-black bg-white p-6"
      style={{ fontFeatureSettings: '"kern"' }}
    >
      {/* Top row: mono label + date */}
      <div className="flex items-center justify-between">
        <span
          className="font-mono text-[11px] font-normal uppercase text-black/40"
          style={{ letterSpacing: "0.6px" }}
        >
          Team #{index + 1}
        </span>
        <span
          className="font-mono text-[11px] text-black/40"
          style={{ letterSpacing: "0.4px" }}
        >
          {formatDate(team.created_at)}
        </span>
      </div>

      {/* Mission */}
      <p
        className="mt-4 line-clamp-3 text-[15px] font-semibold leading-[1.45] text-black"
        style={{ letterSpacing: "-0.26px" }}
      >
        {team.mission}
      </p>

      {/* Members */}
      <ul className="mt-5 flex flex-col gap-2">
        {team.members.map((m) => (
          <li key={m.id} className="flex items-center gap-2">
            <span
              className="rounded-full border border-black px-2.5 py-0.5 font-mono text-[10px] uppercase text-black"
              style={{ letterSpacing: "0.5px" }}
            >
              {m.role}
            </span>
            <span
              className="text-sm font-light text-black"
              style={{ letterSpacing: "-0.14px" }}
            >
              {m.name}
            </span>
          </li>
        ))}
      </ul>

      {/* Stats row (if present) */}
      {team.stats && (
        <div
          className="mt-5 flex gap-4 border-t border-black/10 pt-4 text-[11px] text-black/40"
          style={{ letterSpacing: "0.3px" }}
        >
          <span>검색 {team.stats.searches}</span>
          <span>위임 {team.stats.invokes}</span>
          <span>DM {team.stats.dms}</span>
        </div>
      )}

      {/* Delete button */}
      <div className="mt-5 flex justify-end">
        <button
          onClick={() => onDelete(team)}
          className="rounded-full border border-black/30 px-4 py-1.5 text-xs font-medium text-black/50 transition hover:border-black hover:text-black focus-visible:outline focus-visible:outline-2 focus-visible:outline-dashed focus-visible:outline-black"
          style={{ letterSpacing: "-0.1px" }}
        >
          삭제
        </button>
      </div>
    </article>
  );
}

/* ── Page ────────────────────────────────────────────────────── */
export default function TeamsPage() {
  const [teams, setTeams] = useState<TeamRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<TeamRead | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    const html = document.documentElement;
    const prev = {
      bg: html.style.getPropertyValue("--bg"),
      surface: html.style.getPropertyValue("--surface"),
      border: html.style.getPropertyValue("--border"),
      text: html.style.getPropertyValue("--text"),
      muted: html.style.getPropertyValue("--muted"),
    };
    html.style.setProperty("--bg", "#ffffff");
    html.style.setProperty("--surface", "#f5f5f5");
    html.style.setProperty("--border", "#e0e0e0");
    html.style.setProperty("--text", "#000000");
    html.style.setProperty("--muted", "#555555");
    document.body.style.background = "#ffffff";
    document.body.style.color = "#000000";
    return () => {
      html.style.setProperty("--bg", prev.bg);
      html.style.setProperty("--surface", prev.surface);
      html.style.setProperty("--border", prev.border);
      html.style.setProperty("--text", prev.text);
      html.style.setProperty("--muted", prev.muted);
      document.body.style.background = "";
      document.body.style.color = "";
    };
  }, []);

  useEffect(() => {
    fetch(`${API}/api/teams`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<TeamRead[]>;
      })
      .then(setTeams)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : String(e))
      )
      .finally(() => setLoading(false));
  }, []);

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      const res = await fetch(`${API}/api/teams/${deleteTarget.id}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setTeams((prev) => prev.filter((t) => t.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "삭제 실패");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <>
      <div style={{ fontFeatureSettings: '"kern"', letterSpacing: "-0.01em" }}>
        <div>
          {/* Header */}
          <div className="mb-10 flex items-end justify-between">
            <div>
              <p
                className="font-mono text-xs uppercase text-black/40"
                style={{ letterSpacing: "0.54px" }}
              >
                Formed Teams
              </p>
              <h1
                className="mt-2 text-4xl font-semibold leading-tight text-black"
                style={{ letterSpacing: "-0.96px" }}
              >
                결성된 팀
              </h1>
            </div>
            {!loading && !error && (
              <span
                className="font-mono text-sm text-black/40"
                style={{ letterSpacing: "0.3px" }}
              >
                {teams.length} team{teams.length !== 1 ? "s" : ""}
              </span>
            )}
          </div>

          {/* Loading */}
          {loading && (
            <p
              className="text-sm font-light text-black/40"
              style={{ letterSpacing: "-0.14px" }}
            >
              불러오는 중…
            </p>
          )}

          {/* Error */}
          {error && (
            <div className="rounded-lg border border-black/20 p-6 text-sm text-black/50">
              {error}
            </div>
          )}

          {/* Empty state */}
          {!loading && !error && teams.length === 0 && (
            <div className="rounded-lg border border-dashed border-black/30 px-8 py-16 text-center">
              <p
                className="font-mono text-xs uppercase text-black/30"
                style={{ letterSpacing: "0.54px" }}
              >
                No Teams Yet
              </p>
              <p
                className="mt-3 text-sm font-light text-black/40"
                style={{ letterSpacing: "-0.14px" }}
              >
                Live Demo를 실행하면 이곳에 결성된 팀이 기록됩니다.
              </p>
              <a
                href="/demo"
                className="mt-6 inline-block rounded-full bg-black px-6 py-2.5 text-sm font-medium text-white transition hover:opacity-80 focus-visible:outline focus-visible:outline-2 focus-visible:outline-dashed focus-visible:outline-black"
                style={{ letterSpacing: "-0.14px" }}
              >
                Live Demo 실행 →
              </a>
            </div>
          )}

          {/* Grid */}
          {!loading && !error && teams.length > 0 && (
            <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
              {teams.map((team, i) => (
                <TeamCard
                  key={team.id}
                  team={team}
                  index={i}
                  onDelete={setDeleteTarget}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Delete modal */}
      {deleteTarget && (
        <DeleteModal
          team={deleteTarget}
          deleting={deleting}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={handleDelete}
        />
      )}
    </>
  );
}
