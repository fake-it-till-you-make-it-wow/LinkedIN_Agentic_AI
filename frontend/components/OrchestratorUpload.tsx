"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE, uploadOrchestrator, type OrchestratorUploadResult } from "@/lib/api";

type UploadState =
  | { kind: "idle" }
  | { kind: "uploading" }
  | { kind: "parsed"; result: OrchestratorUploadResult }
  | { kind: "error"; message: string };

export default function OrchestratorUpload() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [state, setState] = useState<UploadState>({ kind: "idle" });

  const handleFile = async (file: File) => {
    if (!file.name.endsWith(".py")) {
      setState({ kind: "error", message: ".py 파일만 업로드할 수 있습니다" });
      return;
    }
    setState({ kind: "uploading" });
    try {
      const result = await uploadOrchestrator(file);
      setState({ kind: "parsed", result });
    } catch (err) {
      setState({
        kind: "error",
        message: err instanceof Error ? err.message : "업로드 실패",
      });
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  const startDemo = () => {
    if (state.kind !== "parsed") return;
    router.push(`/demo?session_id=${state.result.session_id}`);
  };

  const reset = () => {
    setState({ kind: "idle" });
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-8">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <p className="mb-1 font-mono text-xs uppercase tracking-[0.25em] text-[var(--accent)]">
            등록
          </p>
          <h2
            className="text-xl font-semibold"
            style={{ letterSpacing: "-0.025em" }}
          >
            내 오케스트레이터 등록
          </h2>
          <p className="mt-1 text-sm font-light text-[var(--muted)]">
            Python 템플릿 파일을 업로드하면 Groq AI가 팀을 자율 섭외합니다.
          </p>
        </div>
        <a
          href={`${API_BASE}/api/orchestrator/template`}
          download="orchestrator_template.py"
          className="shrink-0 rounded-[50px] border border-[var(--border)] px-4 py-2 text-xs font-medium text-[var(--muted)] transition hover:border-[var(--accent)] hover:text-[var(--accent)]"
        >
          템플릿 다운로드
        </a>
      </div>

      {state.kind === "idle" || state.kind === "error" ? (
        <>
          <div
            className="flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-[var(--border)] p-10 text-center transition hover:border-[var(--accent)]"
            onClick={() => inputRef.current?.click()}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
          >
            <p className="text-sm text-[var(--muted)]">
              .py 파일을 드래그하거나 클릭하여 업로드
            </p>
            <p className="mt-1 text-xs text-[var(--muted)] opacity-60">
              orchestrator_template.py를 수정한 파일을 올려주세요
            </p>
          </div>
          <input
            ref={inputRef}
            type="file"
            accept=".py"
            className="hidden"
            onChange={handleChange}
          />
          {state.kind === "error" ? (
            <p className="mt-3 text-xs text-[#ff6b6b]">{state.message}</p>
          ) : null}
        </>
      ) : state.kind === "uploading" ? (
        <div className="flex items-center justify-center py-10 text-sm text-[var(--muted)]">
          <span className="animate-pulse">파싱 중...</span>
        </div>
      ) : (
        <div className="rounded-lg border border-[var(--border)] bg-[var(--bg)] p-5">
          <div className="mb-3 flex items-center gap-2">
            <span className="font-mono text-xs text-[#5bd391]">✓ 파싱 완료</span>
            <span className="text-sm font-medium">{state.result.agent_name}</span>
          </div>
          <p
            className="mb-4 text-sm leading-relaxed text-[var(--text)]"
            style={{ letterSpacing: "-0.01em" }}
          >
            &ldquo;{state.result.task_description}&rdquo;
          </p>
          <div className="mb-5 flex flex-wrap gap-2">
            {state.result.team_requirements.map((req, i) => (
              <span
                key={i}
                className="rounded-[50px] border border-[var(--border)] px-3 py-1 text-xs text-[var(--muted)]"
              >
                {req.role}
                {req.count && req.count > 1 ? ` ×${req.count}` : ""}
              </span>
            ))}
          </div>
          <div className="flex gap-3">
            <button
              onClick={startDemo}
              className="rounded-[50px] border border-[var(--accent)] bg-[var(--accent)] px-5 py-2 text-sm font-medium text-[#0b0d12] transition hover:opacity-90"
            >
              팀 섭외 시작 →
            </button>
            <button
              onClick={reset}
              className="rounded-[50px] border border-[var(--border)] px-5 py-2 text-sm text-[var(--muted)] transition hover:border-[var(--accent)] hover:text-[var(--accent)]"
            >
              다시 선택
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
