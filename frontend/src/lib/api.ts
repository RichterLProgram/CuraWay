const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:5000";

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
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
