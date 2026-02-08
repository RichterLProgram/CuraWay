export interface DemandPoint {
  id: string;
  lat: number;
  lng: number;
  intensity: number;
  diagnosis: string;
  urgency: number;
  region: string;
  date: string;
}

export interface Facility {
  id: string;
  name: string;
  lat: number;
  lng: number;
  type: string;
  capabilities: string[];
  coverage: number;
  beds: number;
  staff: number;
  region: string;
}

export interface Desert {
  id: string;
  region_name: string;
  lat: number;
  lng: number;
  gap_score: number;
  population_affected: number;
  missing_capabilities: string[];
  nearest_facility_km: number;
}

export interface Recommendation {
  id: string;
  region: string;
  action: string;
  capability_needed: string;
  estimated_impact: string;
  roi: string;
  priority: "critical" | "high" | "medium" | "low";
  lives_saved_per_year: number;
}

export interface DemandData {
  total_count: number;
  points: DemandPoint[];
  top_diagnoses: { name: string; count: number }[];
}

export interface SupplyData {
  total_count: number;
  avg_coverage: number;
  facilities: Facility[];
  top_capabilities: { name: string; count: number }[];
}

export interface GapAnalysis {
  deserts: Desert[];
  total_population_underserved: number;
  avg_gap_score: number;
}

export interface MapData {
  demand_points: { lat: number; lng: number; intensity: number }[];
  supply_points: { lat: number; lng: number; coverage: number }[];
}

export interface PlannerRecommendations {
  recommendations: Recommendation[];
}

export interface PlannerHotspot {
  region: string;
  gap_score: number;
  population_affected: number;
  lat: number;
  lng: number;
}

export interface PlannerActionPlan {
  region: string;
  priority: "low" | "medium" | "high" | "critical";
  confidence: "low" | "medium" | "high";
  estimated_cost: string;
  capex_cost: string;
  opex_cost: string;
  impact: string;
  actions: string[];
  timeline: string[];
  dependencies: string[];
  risks: string[];
}

export interface SimulationPreset {
  coverage_delta: number;
  underserved_delta: number;
  roi_window: string;
  demand_impact: { month: string; baseline: number; simulated: number }[];
  coverage_shift: { region: string; baseline: number; simulated: number }[];
  cost_curve: { cost: number; impact: number };
}

export interface PlannerEngineResponse {
  summary: string;
  hotspots: PlannerHotspot[];
  action_plan: PlannerActionPlan;
  simulation_presets: {
    Low: SimulationPreset;
    Balanced: SimulationPreset;
    Aggressive: SimulationPreset;
  };
}
