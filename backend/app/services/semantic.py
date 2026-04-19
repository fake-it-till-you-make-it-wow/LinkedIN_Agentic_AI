"""TF-IDF cosine similarity for agent discovery.

Phase 3-A: semantic_score는 임베딩 대신 순수 Python TF-IDF로 근사한다.
코퍼스 규모가 작아(수십 건) 매 검색마다 재계산해도 충분하며,
새 의존성 없이 동작한다. 임베딩 모델 도입은 Phase 4 후보.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence

from backend.app.models import Agent

_TOKEN_RE = re.compile(r"[A-Za-z0-9\uac00-\ud7a3]+")


def _tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in _TOKEN_RE.finditer(text)]


def _agent_corpus_text(agent: Agent) -> str:
    parts: list[str] = [agent.name or ""]
    if agent.description:
        parts.append(agent.description)
    if agent.skill_tags:
        parts.extend(agent.skill_tags)
    if agent.career_projects:
        parts.append(agent.career_projects)
    return " ".join(parts)


def _tfidf_vector(
    tokens: list[str], doc_freq: Counter[str], n_docs: int
) -> dict[str, float]:
    if not tokens:
        return {}
    term_counts: Counter[str] = Counter(tokens)
    total = len(tokens)
    vector: dict[str, float] = {}
    for term, freq in term_counts.items():
        df = doc_freq.get(term, 0)
        if df == 0:
            continue
        idf = math.log((n_docs + 1) / (df + 1)) + 1.0
        vector[term] = (freq / total) * idf
    return vector


def _cosine(u: dict[str, float], v: dict[str, float]) -> float:
    if not u or not v:
        return 0.0
    norm_u = math.sqrt(sum(value * value for value in u.values()))
    norm_v = math.sqrt(sum(value * value for value in v.values()))
    if norm_u == 0.0 or norm_v == 0.0:
        return 0.0
    shorter, longer = (u, v) if len(u) <= len(v) else (v, u)
    dot = sum(weight * longer.get(term, 0.0) for term, weight in shorter.items())
    return dot / (norm_u * norm_v)


def compute_semantic_scores(
    agents: Sequence[Agent], query_text: str
) -> dict[str, float]:
    """Return agent_id → cosine similarity in [0, 1].

    Args:
        agents: 점수를 매길 대상 에이전트 시퀀스.
        query_text: 사용자가 입력한 자연어 질의.

    Returns:
        agent.id → similarity 매핑. 빈 질의나 빈 코퍼스는 `{}`.
    """

    query_tokens = _tokenize(query_text)
    if not query_tokens or not agents:
        return {}

    doc_tokens = [_tokenize(_agent_corpus_text(agent)) for agent in agents]
    doc_freq: Counter[str] = Counter()
    for tokens in doc_tokens:
        doc_freq.update(set(tokens))
    n_docs = len(agents)

    query_vec = _tfidf_vector(query_tokens, doc_freq, n_docs)
    if not query_vec:
        return {}

    scores: dict[str, float] = {}
    for agent, tokens in zip(agents, doc_tokens, strict=True):
        doc_vec = _tfidf_vector(tokens, doc_freq, n_docs)
        similarity = _cosine(query_vec, doc_vec)
        scores[agent.id] = round(max(0.0, min(1.0, similarity)), 4)
    return scores
