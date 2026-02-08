const normalizeBase = (value?: string, fallback = "/api") => {
  const raw = (value ?? "").trim();
  if (!raw) return fallback;
  const lower = raw.toLowerCase();
  if (lower.startsWith("http://") || lower.startsWith("https://") || lower.includes("localhost")) {
    return fallback;
  }
  const base = raw.startsWith("/") ? raw : `/${raw}`;
  return base.endsWith("/") ? base.slice(0, -1) : base;
};

export const API_BASE = normalizeBase(
  import.meta.env.VITE_API_BASE ?? import.meta.env.VITE_API_BASE_URL
);
const AGENT_API_BASE_URL = normalizeBase(
  import.meta.env.VITE_AGENT_API_BASE ?? import.meta.env.VITE_AGENT_API_BASE_URL
);

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function fetchAgentJson<T>(path: string, payload?: unknown): Promise<T> {
  const response = await fetch(`${AGENT_API_BASE_URL}${path}`, {
    method: payload ? "POST" : "GET",
    headers: { "Content-Type": "application/json" },
    body: payload ? JSON.stringify(payload) : undefined,
  });
  if (!response.ok) {
    throw new Error(`Agent request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function getDemandData() {
  return fetchJson("/data/demand");
}

export function getSupplyData() {
  return fetchJson("/data/supply");
}

export function getGapAnalysis() {
  return fetchJson("/data/gap");
}

export function getMapData() {
  return fetchJson("/data/map");
}

export function getPlannerRecommendations() {
  return fetchJson("/data/recommendations");
}

export function getPlannerEngine() {
  return fetchJson("/data/planner_engine");
}

export function runAgent(payload: {
  query: string;
  top_k?: number;
  enable_rag?: boolean;
  system_prompt?: string;
  metadata?: Record<string, unknown>;
}) {
  return fetchAgentJson("/agent/run", payload);
}

export function getActionGraph(payload: {
  actions: string[];
  dependencies?: string[];
}) {
  return fetchAgentJson("/agent/action_graph", payload);
}

export function getScenario(payload: { action_plan: Record<string, unknown> }) {
  return fetchAgentJson("/agent/scenario", payload);
}

export function getCausalImpact(payload: {
  baseline: number[];
  post: number[];
  metric?: string;
}) {
  return fetchAgentJson("/agent/causal_impact", payload);
}

export function getPolicyOptimize(payload: { constraints: Record<string, unknown> }) {
  return fetchAgentJson("/agent/policy_optimize", payload);
}

export function getRouting(payload: {
  origin: { lat: number; lng: number };
  destination: { lat: number; lng: number };
}) {
  return fetchAgentJson("/agent/routing", payload);
}

export function getRealtimeStatus() {
  return fetchAgentJson("/agent/realtime_status");
}

export function getProvenance(provenanceId: string) {
  return fetchAgentJson(`/agent/provenance/${provenanceId}`);
}

export function getHotspotReport(payload: {
  hotspot: Record<string, unknown>;
  demand?: Record<string, unknown>;
  supply?: Record<string, unknown>;
  gap?: Record<string, unknown>;
  recommendations?: Array<Record<string, unknown>>;
  baseline_kpis?: Record<string, unknown>;
}) {
  return fetchAgentJson("/agent/hotspot_report", payload);
}
