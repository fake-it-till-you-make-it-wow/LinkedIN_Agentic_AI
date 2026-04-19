"use client";

import { useEffect, useState } from "react";

/** 문자 단위로 점진 노출되는 타이핑 애니메이션 훅.
 *
 * Phase 3-E 레벨-3B: 실제 LLM 토큰 스트리밍 대신, 완성된 문자열을
 * 받아 프론트에서 한 글자씩 렌더해 "생각하며 답하는" 효과를 낸다.
 */
export function useTypingText(full: string, speedMs = 22): {
  text: string;
  done: boolean;
} {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    setIndex(0);
  }, [full]);

  useEffect(() => {
    if (index >= full.length) return;
    const handle = window.setTimeout(() => setIndex((i) => i + 1), speedMs);
    return () => window.clearTimeout(handle);
  }, [full, index, speedMs]);

  return { text: full.slice(0, index), done: index >= full.length };
}
