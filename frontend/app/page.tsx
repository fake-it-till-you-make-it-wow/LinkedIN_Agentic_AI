import OrchestratorUpload from "@/components/OrchestratorUpload";

const HOW_IT_WORKS = [
  {
    step: "01",
    title: "템플릿 다운로드",
    description:
      "제공된 Python 템플릿을 받아 TASK_DESCRIPTION과 TEAM_REQUIREMENTS를 작성합니다. 어떤 팀이 필요한지 자연어로 정의하세요.",
  },
  {
    step: "02",
    title: "파일 업로드",
    description:
      "작성한 .py 파일을 업로드하면 서버가 안전하게 파싱합니다. exec 없이 AST로만 처리되므로 코드가 실행되지 않습니다.",
  },
  {
    step: "03",
    title: "팀 섭외 시작",
    description:
      "Groq AI가 역할별 검색 태그를 생성하고 최적 에이전트를 선별합니다. 섭외 과정이 실시간 스트리밍으로 펼쳐집니다.",
  },
];

export default function HomePage() {
  return (
    <section className="flex flex-col gap-20">
      {/* Hero */}
      <div
        className="relative -mx-6 -mt-12 px-6 pt-20 pb-16 text-center overflow-hidden"
        style={{
          background:
            "radial-gradient(ellipse 80% 50% at 50% -10%, rgba(77,163,255,0.14) 0%, transparent 70%)",
        }}
      >
        <p className="mb-4 font-mono text-xs uppercase tracking-[0.3em] text-[var(--accent)]">
          AI Agent Platform
        </p>
        <h1
          className="text-5xl font-semibold leading-[1.08] tracking-[-0.04em] md:text-6xl"
          style={{ letterSpacing: "-0.04em" }}
        >
          AI 에이전트 팀을
          <br />
          자율적으로 구성하세요
        </h1>
        <p className="mx-auto mt-5 max-w-lg text-base font-light leading-relaxed text-[var(--muted)]"
           style={{ letterSpacing: "-0.01em" }}>
          오케스트레이터 에이전트가 디렉터리에서 최적의 팀원을 검색·평가·섭외합니다.
          당신은 목표만 정의하면 됩니다.
        </p>
      </div>

      {/* How it works */}
      <div>
        <p className="mb-8 text-center font-mono text-xs uppercase tracking-[0.3em] text-[var(--muted)]">
          어떻게 작동하나요
        </p>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {HOW_IT_WORKS.map(({ step, title, description }) => (
            <div
              key={step}
              className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-7"
            >
              <div
                className="mb-4 font-mono text-3xl font-bold text-[var(--accent)]"
                style={{ opacity: 0.45, letterSpacing: "-0.04em" }}
              >
                {step}
              </div>
              <h3
                className="mb-2 text-base font-semibold"
                style={{ letterSpacing: "-0.02em" }}
              >
                {title}
              </h3>
              <p className="text-sm font-light leading-relaxed text-[var(--muted)]">
                {description}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Orchestrator upload */}
      <OrchestratorUpload />
    </section>
  );
}
