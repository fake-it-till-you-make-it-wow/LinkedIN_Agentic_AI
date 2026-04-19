export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type Publisher = {
  id: string;
  name: string;
  title: string | null;
  verified: boolean;
  verified_at: string | null;
  verification_note: string | null;
  created_at: string;
};

export type Agent = {
  id: string;
  name: string;
  description: string | null;
  skill_tags: string[];
  endpoint_url: string | null;
  career_projects: string | null;
  publisher: Publisher | null;
  publisher_id: string | null;
  version: string;
  verified: boolean;
  star_rating: number;
  success_rate: number;
  avg_response_ms: number;
  total_calls: number;
  github_repo: string | null;
  github_star_count: number;
  trust_score: number;
  community_score: number;
  created_at: string;
};

export type AgentStats = {
  agent_id: string;
  total_invocations: number;
  success_count: number;
  error_count: number;
  timeout_count: number;
  success_rate: number;
  avg_response_ms: number | null;
  review_count: number;
  star_rating: number;
  last_invoked_at: string | null;
  status: string;
};

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { accept: "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

export async function listAgents(): Promise<Agent[]> {
  return fetchJson<Agent[]>("/api/agents");
}

export async function getAgent(id: string): Promise<Agent> {
  return fetchJson<Agent>(`/api/agents/${id}`);
}

export async function getAgentStats(id: string): Promise<AgentStats> {
  return fetchJson<AgentStats>(`/api/agents/${id}/stats`);
}
