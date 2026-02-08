import type { DemandData, SupplyData, GapAnalysis, MapData, PlannerRecommendations } from "@/types/healthgrid";

export const demandData: DemandData = {
  total_count: 1247,
  points: [
    { id: "d1", lat: 5.6037, lng: -0.1870, intensity: 0.9, diagnosis: "Malaria", urgency: 8, region: "Greater Accra", date: "2025-01-15" },
    { id: "d2", lat: 6.6885, lng: -1.6244, intensity: 0.85, diagnosis: "Respiratory Infection", urgency: 7, region: "Ashanti", date: "2025-01-14" },
    { id: "d3", lat: 7.3349, lng: -2.3279, intensity: 0.7, diagnosis: "Cardiovascular", urgency: 9, region: "Bono", date: "2025-01-13" },
    { id: "d4", lat: 9.4034, lng: -0.8488, intensity: 0.95, diagnosis: "Maternal Emergency", urgency: 10, region: "Northern", date: "2025-01-12" },
    { id: "d5", lat: 5.1054, lng: -1.2466, intensity: 0.6, diagnosis: "Diabetes", urgency: 5, region: "Central", date: "2025-01-11" },
    { id: "d6", lat: 6.0965, lng: 0.2621, intensity: 0.75, diagnosis: "Trauma", urgency: 8, region: "Volta", date: "2025-01-10" },
    { id: "d7", lat: 10.0601, lng: -2.5099, intensity: 0.88, diagnosis: "Malnutrition", urgency: 9, region: "Upper West", date: "2025-01-09" },
    { id: "d8", lat: 4.9016, lng: -1.7831, intensity: 0.55, diagnosis: "Hypertension", urgency: 4, region: "Western", date: "2025-01-08" },
  ],
  top_diagnoses: [
    { name: "Malaria", count: 342 },
    { name: "Respiratory Infection", count: 278 },
    { name: "Maternal Emergency", count: 195 },
    { name: "Cardiovascular", count: 167 },
    { name: "Trauma", count: 132 },
  ],
};

export const supplyData: SupplyData = {
  total_count: 89,
  avg_coverage: 62,
  facilities: [
    { id: "f1", name: "Korle Bu Teaching Hospital", lat: 5.5364, lng: -0.2280, type: "Teaching Hospital", capabilities: ["Surgery", "ICU", "Maternity", "Lab", "Imaging"], coverage: 92, beds: 1600, staff: 3200, region: "Greater Accra" },
    { id: "f2", name: "Komfo Anokye Teaching Hospital", lat: 6.6960, lng: -1.6163, type: "Teaching Hospital", capabilities: ["Surgery", "ICU", "Maternity", "Lab"], coverage: 88, beds: 1000, staff: 2400, region: "Ashanti" },
    { id: "f3", name: "Tamale Teaching Hospital", lat: 9.4075, lng: -0.8393, type: "Regional Hospital", capabilities: ["Surgery", "Maternity", "Lab"], coverage: 65, beds: 400, staff: 800, region: "Northern" },
    { id: "f4", name: "Cape Coast Teaching Hospital", lat: 5.1036, lng: -1.2546, type: "Teaching Hospital", capabilities: ["Surgery", "Maternity", "Lab", "Imaging"], coverage: 78, beds: 500, staff: 1100, region: "Central" },
    { id: "f5", name: "Ho Municipal Hospital", lat: 6.6003, lng: 0.4713, type: "Municipal Hospital", capabilities: ["Maternity", "Lab"], coverage: 45, beds: 120, staff: 250, region: "Volta" },
    { id: "f6", name: "Wa Regional Hospital", lat: 10.0560, lng: -2.5010, type: "Regional Hospital", capabilities: ["Maternity", "Lab"], coverage: 38, beds: 80, staff: 160, region: "Upper West" },
    { id: "f7", name: "Sunyani Regional Hospital", lat: 7.3349, lng: -2.3270, type: "Regional Hospital", capabilities: ["Surgery", "Maternity", "Lab"], coverage: 55, beds: 250, staff: 500, region: "Bono" },
    { id: "f8", name: "Sekondi-Takoradi Hospital", lat: 4.9340, lng: -1.7740, type: "Municipal Hospital", capabilities: ["Maternity", "Lab", "Imaging"], coverage: 60, beds: 200, staff: 400, region: "Western" },
  ],
  top_capabilities: [
    { name: "Maternity", count: 78 },
    { name: "Lab", count: 72 },
    { name: "Surgery", count: 34 },
    { name: "ICU", count: 12 },
    { name: "Imaging", count: 28 },
  ],
};

export const gapAnalysis: GapAnalysis = {
  deserts: [
    { id: "g1", region_name: "Afram Plains", lat: 7.15, lng: -0.75, gap_score: 0.89, population_affected: 245000, missing_capabilities: ["Surgery", "ICU", "Imaging"], nearest_facility_km: 87 },
    { id: "g2", region_name: "Ketu South", lat: 6.10, lng: 1.18, gap_score: 0.76, population_affected: 180000, missing_capabilities: ["Surgery", "ICU"], nearest_facility_km: 62 },
    { id: "g3", region_name: "Bole District", lat: 9.03, lng: -2.49, gap_score: 0.92, population_affected: 62000, missing_capabilities: ["Surgery", "ICU", "Imaging", "Maternity"], nearest_facility_km: 124 },
    { id: "g4", region_name: "Nkwanta South", lat: 7.50, lng: 0.50, gap_score: 0.81, population_affected: 117000, missing_capabilities: ["Surgery", "Lab", "Imaging"], nearest_facility_km: 95 },
    { id: "g5", region_name: "Sissala East", lat: 10.60, lng: -1.95, gap_score: 0.94, population_affected: 56000, missing_capabilities: ["Surgery", "ICU", "Imaging", "Lab", "Maternity"], nearest_facility_km: 142 },
  ],
  total_population_underserved: 660000,
  avg_gap_score: 0.864,
};

export const mapData: MapData = {
  demand_points: [
    { lat: 5.6037, lng: -0.1870, intensity: 0.9 },
    { lat: 5.55, lng: -0.22, intensity: 0.7 },
    { lat: 5.65, lng: -0.15, intensity: 0.8 },
    { lat: 6.6885, lng: -1.6244, intensity: 0.85 },
    { lat: 6.72, lng: -1.58, intensity: 0.6 },
    { lat: 6.65, lng: -1.65, intensity: 0.75 },
    { lat: 7.3349, lng: -2.3279, intensity: 0.7 },
    { lat: 9.4034, lng: -0.8488, intensity: 0.95 },
    { lat: 9.35, lng: -0.90, intensity: 0.8 },
    { lat: 5.1054, lng: -1.2466, intensity: 0.6 },
    { lat: 6.0965, lng: 0.2621, intensity: 0.75 },
    { lat: 10.0601, lng: -2.5099, intensity: 0.88 },
    { lat: 4.9016, lng: -1.7831, intensity: 0.55 },
    { lat: 7.15, lng: -0.75, intensity: 0.92 },
    { lat: 6.10, lng: 1.18, intensity: 0.65 },
    { lat: 9.03, lng: -2.49, intensity: 0.78 },
    { lat: 7.50, lng: 0.50, intensity: 0.71 },
    { lat: 10.60, lng: -1.95, intensity: 0.85 },
  ],
  supply_points: [
    { lat: 5.5364, lng: -0.2280, coverage: 92 },
    { lat: 6.6960, lng: -1.6163, coverage: 88 },
    { lat: 9.4075, lng: -0.8393, coverage: 65 },
    { lat: 5.1036, lng: -1.2546, coverage: 78 },
    { lat: 6.6003, lng: 0.4713, coverage: 45 },
    { lat: 10.0560, lng: -2.5010, coverage: 38 },
    { lat: 7.3349, lng: -2.3270, coverage: 55 },
    { lat: 4.9340, lng: -1.7740, coverage: 60 },
  ],
};

export const plannerRecommendations: PlannerRecommendations = {
  recommendations: [
    { id: "r1", region: "Sissala East", action: "Build Primary Health Facility", capability_needed: "Full-service clinic with surgery, ICU, lab", estimated_impact: "56,000 people gain access to emergency care", roi: "$2.1M over 5 years", priority: "critical", lives_saved_per_year: 34 },
    { id: "r2", region: "Bole District", action: "Deploy Mobile Surgical Unit", capability_needed: "Mobile surgery + maternity care", estimated_impact: "62,000 people within 30km radius", roi: "$890K over 3 years", priority: "critical", lives_saved_per_year: 28 },
    { id: "r3", region: "Afram Plains", action: "Build District Hospital", capability_needed: "Surgery, ICU, Imaging", estimated_impact: "245,000 people gain local access", roi: "$4.5M over 5 years", priority: "high", lives_saved_per_year: 52 },
    { id: "r4", region: "Nkwanta South", action: "Upgrade Health Center", capability_needed: "Add surgery & lab capabilities", estimated_impact: "117,000 people served locally", roi: "$1.8M over 4 years", priority: "high", lives_saved_per_year: 19 },
    { id: "r5", region: "Ketu South", action: "Deploy Telemedicine Hub", capability_needed: "Remote ICU consultation + imaging", estimated_impact: "180,000 people gain specialist access", roi: "$650K over 3 years", priority: "medium", lives_saved_per_year: 15 },
  ],
};
