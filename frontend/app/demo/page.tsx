"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE } from "@/lib/api";
import { useTypingText } from "./useTypingText";

// ────────────────────────────────────────────────────────────────
// 이벤트 페이로드 타입 (backend/app/services/demo_runner.py 와 일치)
// ────────────────────────────────────────────────────────────────

type ActorRef = { id: string; name: string };

type SearchRow = {
  id: string;
  name: string;
  star_rating: number;
  avg_response_ms: number;
  success_rate: number;
  specialization_match: number;
  semantic_score: number;
  final_score: number;
  publisher: { name: string; title: string | null; verified: boolean } | null;
  skill_tags: string[];
};

type MissionBrief = {
  act: number;
  title: string;
  pm: ActorRef;
  mission: string;
};

type ActTransition = { to: number; label: string };

type SearchStarted = {
  act: number;
  title: string;
  tags: string[];
  weights: Record<string, number>;
};

type SearchCompleted = { act: number; title: string; rows: SearchRow[] };

type Selection = {
  act: number;
  agent: ActorRef;
  score: number;
  reason: string;
};

type InvokeSent = {
  from: ActorRef;
  to: ActorRef;
  input: Record<string, unknown>;
  transport: "inline" | "http";
};

type InvokeCompleted = {
  agent: ActorRef;
  status: string;
  output: Record<string, unknown> | null;
  response_ms: number;
};

type DmSent = {
  thread_id: string;
  from: ActorRef;
  to: ActorRef;
  message: string;
  transport: "inline" | "http" | "none";
};

type DmReceived = {
  thread_id: string;
  from: ActorRef;
  to: ActorRef;
  response: string;
  status: string;
};

type Finale = {
  mission_complete: boolean;
  team: { id: string; name: string; role: string }[];
  stats: Record<string, number>;
};

type ErrorPayload = { stage: string; message: string };

// ────────────────────────────────────────────────────────────────
// 타임라인 아이템 (UI 렌더링 단위)
// ────────────────────────────────────────────────────────────────

type TimelineItem =
  | { kind: "mission"; id: string; data: MissionBrief }
  | { kind: "act_header"; id: string; data: ActTransition }
  | {
      kind: "log";
      id: string;
      actor: string;
      color: LogColor;
      text: string;
    }
  | { kind: "search_table"; id: string; data: SearchCompleted; started: SearchStarted | null }
  | { kind: "selection"; id: string; data: Selection }
  | { kind: "invoke_result"; id: string; data: InvokeCompleted }
  | { kind: "dm_out"; id: string; data: DmSent }
  | { kind: "dm_in"; id: string; data: DmReceived }
  | { kind: "finale"; id: string; data: Finale }
  | { kind: "error"; id: string; data: ErrorPayload };

type LogColor = "blue" | "purple" | "yellow" | "green" | "red" | "gray";

const COLOR_STYLES: Record<LogColor, string> = {
  blue: "text-[#4da3ff]",
  purple: "text-[#c394ff]",
  yellow: "text-[#f5c344]",
  green: "text-[#5bd391]",
  red: "text-[#ff6b6b]",
  gray: "text-[var(--muted)]",
};

const COLOR_DOTS: Record<LogColor, string> = {
  blue: "bg-[#4da3ff]",
  purple: "bg-[#c394ff]",
  yellow: "bg-[#f5c344]",
  green: "bg-[#5bd391]",
  red: "bg-[#ff6b6b]",
  gray: "bg-[var(--muted)]",
};

// ────────────────────────────────────────────────────────────────
// 메인 페이지
// ────────────────────────────────────────────────────────────────

export default function DemoPage() {
  const [items, setItems] = useState<TimelineItem[]>([]);
  const [status, setStatus] = useState<"idle" | "running" | "done" | "error">(
    "idle"
  );
  const [errorText, setErrorText] = useState<string | null>(null);
  const sourceRef = useRef<EventSource | null>(null);
  const counterRef = useRef(0);
  const lastSearchStartedRef = useRef<SearchStarted | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const nextId = useCallback(() => {
    counterRef.current += 1;
    return `item-${counterRef.current}`;
  }, []);

  const append = useCallback((item: TimelineItem) => {
    setItems((prev) => [...prev, item]);
  }, []);

  // 새 아이템이 추가될 때마다 하단으로 스크롤
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [items.length]);

  const stopStream = useCallback(() => {
    sourceRef.current?.close();
    sourceRef.current = null;
  }, []);

  const startDemo = useCallback(() => {
    if (status === "running") return;
    setItems([]);
    setErrorText(null);
    setStatus("running");
    counterRef.current = 0;
    lastSearchStartedRef.current = null;

    const source = new EventSource(`${API_BASE}/api/demo/stream`);
    sourceRef.current = source;

    const bind = <T,>(name: string, handler: (data: T) => void) => {
      source.addEventListener(name, (evt) => {
        const msg = evt as MessageEvent<string>;
        try {
          handler(JSON.parse(msg.data) as T);
        } catch (err) {
          console.error(`Failed to parse ${name}:`, err);
        }
      });
    };

    bind<MissionBrief>("mission_brief", (data) => {
      append({ kind: "mission", id: nextId(), data });
    });

    bind<ActTransition>("act_transition", (data) => {
      append({ kind: "act_header", id: nextId(), data });
    });

    bind<SearchStarted>("search_started", (data) => {
      lastSearchStartedRef.current = data;
      const tagLabel = data.tags.map((t) => `#${t}`).join(" ");
      const weightLabel = Object.entries(data.weights)
        .map(([k, v]) => `${k} ${v}`)
        .join(" · ");
      append({
        kind: "log",
        id: nextId(),
        actor: "PM",
        color: "blue",
        text: `[Act ${data.act}] ${tagLabel} 태그로 에이전트 검색 시작 (가중치: ${weightLabel})`,
      });
    });

    bind<SearchCompleted>("search_completed", (data) => {
      append({
        kind: "log",
        id: nextId(),
        actor: "PM",
        color: "blue",
        text: `${data.rows.length}명 후보 확인 → 가중치 기반 점수 계산 완료`,
      });
      append({
        kind: "search_table",
        id: nextId(),
        data,
        started: lastSearchStartedRef.current,
      });
    });

    bind<Selection>("selection", (data) => {
      append({ kind: "selection", id: nextId(), data });
    });

    bind<InvokeSent>("invoke_sent", (data) => {
      append({
        kind: "log",
        id: nextId(),
        actor: data.from.name,
        color: "purple",
        text: `→ ${data.to.name} 에게 작업 위임 (${data.transport === "inline" ? "in-process" : "HTTP"}). LLM 생성 중...`,
      });
    });

    bind<InvokeCompleted>("invoke_completed", (data) => {
      append({
        kind: "log",
        id: nextId(),
        actor: data.agent.name,
        color: "green",
        text: `응답 완료 (${data.response_ms}ms, status: ${data.status})`,
      });
      append({ kind: "invoke_result", id: nextId(), data });
    });

    bind<DmSent>("dm_sent", (data) => {
      append({ kind: "dm_out", id: nextId(), data });
    });

    bind<DmReceived>("dm_received", (data) => {
      append({ kind: "dm_in", id: nextId(), data });
    });

    bind<Finale>("finale", (data) => {
      append({ kind: "finale", id: nextId(), data });
      setStatus("done");
      stopStream();
    });

    bind<ErrorPayload>("error", (data) => {
      append({ kind: "error", id: nextId(), data });
      setErrorText(`${data.stage}: ${data.message}`);
      setStatus("error");
      stopStream();
    });

    source.onerror = () => {
      // Server closed stream (finale/error already handled) or connection dropped.
      // 함수형 setState로 최신 상태를 읽어, 종료 이벤트를 못 받은 경우에만 done 처리.
      setStatus((prev) => (prev === "running" ? "done" : prev));
      stopStream();
    };
  }, [append, nextId, status, stopStream]);

  useEffect(() => {
    return () => stopStream();
  }, [stopStream]);

  return (
    <section>
      <div className="mb-6 flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Live Demo</h1>
          <p className="mt-1 text-sm text-[var(--muted)]">
            PM 에이전트가 다른 에이전트를 자율적으로 검색·위임·섭외하는 과정을 실시간으로 관전합니다.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={status} />
          <button
            onClick={startDemo}
            disabled={status === "running"}
            className="rounded-md border border-[var(--accent)] bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[#0b0d12] transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {status === "running" ? "실행 중..." : "▶ Start Demo"}
          </button>
        </div>
      </div>

      {errorText ? (
        <div className="mb-4 rounded-md border border-[#ff6b6b] bg-[var(--surface)] p-4 text-sm text-[#ff6b6b]">
          {errorText}
        </div>
      ) : null}

      {items.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="flex flex-col gap-3">
          {items.map((item) => (
            <TimelineRow key={item.id} item={item} />
          ))}
          <div ref={bottomRef} />
        </div>
      )}
    </section>
  );
}

// ────────────────────────────────────────────────────────────────
// 타임라인 row 라우터
// ────────────────────────────────────────────────────────────────

function TimelineRow({ item }: { item: TimelineItem }) {
  switch (item.kind) {
    case "mission":
      return <MissionCard data={item.data} />;
    case "act_header":
      return <ActDivider data={item.data} />;
    case "log":
      return <LogLine actor={item.actor} color={item.color} text={item.text} />;
    case "search_table":
      return <SearchTable data={item.data} started={item.started} />;
    case "selection":
      return <SelectionCard data={item.data} />;
    case "invoke_result":
      return <InvokeResultCard data={item.data} />;
    case "dm_out":
      return <DmOutgoing data={item.data} />;
    case "dm_in":
      return <DmIncoming data={item.data} />;
    case "finale":
      return <FinaleCard data={item.data} />;
    case "error":
      return <ErrorCard data={item.data} />;
  }
}

// ────────────────────────────────────────────────────────────────
// 개별 렌더러
// ────────────────────────────────────────────────────────────────

type DemoStatus = "idle" | "running" | "done" | "error";

function StatusBadge({ status }: { status: DemoStatus }) {
  const labels: Record<DemoStatus, string> = {
    idle: "대기",
    running: "실행 중",
    done: "완료",
    error: "오류",
  };
  const colors: Record<DemoStatus, string> = {
    idle: "border-[var(--border)] text-[var(--muted)]",
    running: "border-[#4da3ff] text-[#4da3ff]",
    done: "border-[#5bd391] text-[#5bd391]",
    error: "border-[#ff6b6b] text-[#ff6b6b]",
  };
  return (
    <span
      className={`rounded-full border px-3 py-1 text-xs ${colors[status]}`}
    >
      {labels[status]}
    </span>
  );
}

function EmptyState() {
  return (
    <div className="rounded-md border border-dashed border-[var(--border)] bg-[var(--surface)] p-10 text-center text-sm text-[var(--muted)]">
      <p className="mb-2 text-base text-[var(--text)]">아직 실행되지 않았습니다.</p>
      <p>
        위 <span className="text-[var(--accent)]">▶ Start Demo</span> 버튼을 눌러
        <br />
        PM이 팀을 구성하는 과정을 실시간으로 확인하세요.
      </p>
    </div>
  );
}

function MissionCard({ data }: { data: MissionBrief }) {
  return (
    <div className="rounded-lg border border-[var(--accent)] bg-[var(--surface)] p-5">
      <div className="mb-2 text-xs uppercase tracking-wide text-[var(--accent)]">
        {data.title}
      </div>
      <h2 className="text-lg font-semibold">{data.pm.name} 가동</h2>
      <p className="mt-2 text-sm text-[var(--muted)]">미션</p>
      <p className="text-base">{data.mission}</p>
    </div>
  );
}

function ActDivider({ data }: { data: ActTransition }) {
  return (
    <div className="mt-3 flex items-center gap-3 border-t border-[var(--border)] pt-4 text-sm">
      <span className="rounded-full border border-[var(--border)] px-3 py-1 text-xs text-[var(--muted)]">
        Act {data.to}
      </span>
      <span className="text-[var(--text)]">{data.label}</span>
    </div>
  );
}

function LogLine({
  actor,
  color,
  text,
}: {
  actor: string;
  color: LogColor;
  text: string;
}) {
  return (
    <div className="flex items-start gap-3 text-sm">
      <span
        className={`mt-1.5 inline-block h-2 w-2 shrink-0 rounded-full ${COLOR_DOTS[color]}`}
      />
      <div>
        <span className={`font-medium ${COLOR_STYLES[color]}`}>[{actor}]</span>{" "}
        <span className="text-[var(--text)]">{text}</span>
      </div>
    </div>
  );
}

function SearchTable({
  data,
  started,
}: {
  data: SearchCompleted;
  started: SearchStarted | null;
}) {
  return (
    <div className="overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--surface)]">
      <div className="border-b border-[var(--border)] p-4">
        <div className="text-sm font-semibold">{data.title}</div>
        {started ? (
          <div className="mt-1 flex flex-wrap gap-2 text-xs text-[var(--muted)]">
            {started.tags.map((t) => (
              <span
                key={t}
                className="rounded-full border border-[var(--border)] px-2 py-0.5"
              >
                #{t}
              </span>
            ))}
          </div>
        ) : null}
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--border)] text-left text-xs uppercase tracking-wide text-[var(--muted)]">
            <th className="px-4 py-2">Name</th>
            <th className="px-4 py-2">Publisher</th>
            <th className="px-4 py-2">★</th>
            <th className="px-4 py-2">응답(ms)</th>
            <th className="px-4 py-2">전문성</th>
            <th className="px-4 py-2">Score</th>
          </tr>
        </thead>
        <tbody>
          {data.rows.map((row, idx) => (
            <tr
              key={row.id}
              className={`border-b border-[var(--border)] last:border-b-0 ${
                idx === 0 ? "bg-[rgba(77,163,255,0.08)]" : ""
              }`}
            >
              <td className="px-4 py-2 font-medium">
                {idx === 0 ? "▸ " : ""}
                {row.name}
              </td>
              <td className="px-4 py-2 text-[var(--muted)]">
                {row.publisher?.name ?? "—"}
              </td>
              <td className="px-4 py-2">{row.star_rating.toFixed(1)}</td>
              <td className="px-4 py-2">{row.avg_response_ms}</td>
              <td className="px-4 py-2">
                {row.specialization_match.toFixed(2)}
              </td>
              <td className="px-4 py-2 font-semibold text-[var(--accent)]">
                {row.final_score.toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SelectionCard({ data }: { data: Selection }) {
  return (
    <div className="rounded-md border border-[#c394ff] bg-[var(--surface)] p-4 text-sm">
      <div className="flex items-center gap-2">
        <span className="text-[#c394ff]">▸ 선택</span>
        <span className="font-semibold">{data.agent.name}</span>
        <span className="rounded border border-[var(--border)] px-2 py-0.5 text-xs text-[var(--muted)]">
          score {data.score.toFixed(2)}
        </span>
      </div>
      <p className="mt-2 text-[var(--muted)]">{data.reason}</p>
    </div>
  );
}

function InvokeResultCard({ data }: { data: InvokeCompleted }) {
  const json = data.output ? JSON.stringify(data.output, null, 2) : "(no output)";
  return (
    <div className="rounded-md border border-[var(--border)] bg-[var(--surface)] p-4">
      <div className="mb-2 flex items-center justify-between text-xs text-[var(--muted)]">
        <span>{data.agent.name} 의 응답</span>
        <span>
          {data.status} · {data.response_ms}ms
        </span>
      </div>
      <pre className="overflow-x-auto whitespace-pre-wrap break-words text-xs text-[var(--text)]">
        {json}
      </pre>
    </div>
  );
}

function DmOutgoing({ data }: { data: DmSent }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[80%] rounded-2xl rounded-br-sm border border-[var(--accent)] bg-[rgba(77,163,255,0.12)] px-4 py-2 text-sm">
        <div className="mb-1 text-xs text-[var(--accent)]">
          {data.from.name} → {data.to.name}
        </div>
        <div className="text-[var(--text)]">{data.message}</div>
      </div>
    </div>
  );
}

function DmIncoming({ data }: { data: DmReceived }) {
  const { text, done } = useTypingText(data.response, 22);
  const isError = data.status !== "success";
  return (
    <div className="flex justify-start">
      <div
        className={`max-w-[80%] rounded-2xl rounded-bl-sm border px-4 py-2 text-sm ${
          isError
            ? "border-[#ff6b6b] bg-[rgba(255,107,107,0.08)]"
            : "border-[var(--border)] bg-[var(--surface)]"
        }`}
      >
        <div
          className={`mb-1 text-xs ${
            isError ? "text-[#ff6b6b]" : "text-[var(--muted)]"
          }`}
        >
          {data.from.name}
        </div>
        <div className="whitespace-pre-wrap text-[var(--text)]">
          {text}
          {!done ? <span className="animate-pulse text-[var(--accent)]">▍</span> : null}
        </div>
      </div>
    </div>
  );
}

function FinaleCard({ data }: { data: Finale }) {
  return (
    <div className="mt-4 rounded-lg border border-[#5bd391] bg-[var(--surface)] p-5">
      <div className="mb-2 text-xs uppercase tracking-wide text-[#5bd391]">
        Finale
      </div>
      <h2 className="text-lg font-semibold">
        {data.mission_complete ? "팀 구성 완료!" : "팀 구성 미완료"}
      </h2>
      <div className="mt-4">
        <div className="text-sm text-[var(--muted)]">팀원</div>
        <ul className="mt-2 space-y-1 text-sm">
          {data.team.map((member, idx) => (
            <li key={member.id}>
              <span className="text-[var(--muted)]">
                {idx === data.team.length - 1 ? "└── " : "├── "}
              </span>
              <span className="text-[var(--text)]">{member.name}</span>
              <span className="ml-2 text-xs text-[var(--muted)]">
                ({member.role})
              </span>
            </li>
          ))}
        </ul>
      </div>
      <div className="mt-4 flex flex-wrap gap-2 text-xs text-[var(--muted)]">
        <span>검색 {data.stats.searches}회</span>
        <span>·</span>
        <span>invoke {data.stats.invokes}회</span>
        <span>·</span>
        <span>DM {data.stats.dms}회</span>
        <span>·</span>
        <span className="text-[#5bd391]">
          사람 개입 {data.stats.human_intervention}회
        </span>
      </div>
    </div>
  );
}

function ErrorCard({ data }: { data: ErrorPayload }) {
  return (
    <div className="rounded-md border border-[#ff6b6b] bg-[var(--surface)] p-4 text-sm">
      <div className="mb-1 text-xs text-[#ff6b6b]">
        Error · stage: {data.stage}
      </div>
      <div className="text-[var(--text)]">{data.message}</div>
    </div>
  );
}
