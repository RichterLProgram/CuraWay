import { useRef, useEffect, useState, useCallback } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { HealthGridData } from "@/hooks/use-health-grid-data";

interface InteractiveMapProps {
  activeTab: string;
  data?: HealthGridData;
  isLoading?: boolean;
  height?: number;
  className?: string;
  focusLat?: number | null;
  focusLng?: number | null;
  focusZoom?: number;
  onModeChange?: (mode: "demand" | "supply" | "gap") => void;
}

const InteractiveMap = ({
  activeTab,
  data,
  isLoading = false,
  height = 480,
  className,
  focusLat = null,
  focusLng = null,
  focusZoom = 8,
  onModeChange,
}: InteractiveMapProps) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const layersRef = useRef<Record<string, L.LayerGroup>>({});

  const [showDemand, setShowDemand] = useState(true);
  const [showSupply, setShowSupply] = useState(true);
  const [showDeserts, setShowDeserts] = useState(false);

  // Init map
  const clearLayers = useCallback(() => {
    const map = mapInstanceRef.current;
    if (!map) return;
    Object.values(layersRef.current).forEach((layer) => {
      if (map.hasLayer(layer)) {
        map.removeLayer(layer);
      }
    });
    layersRef.current = {};
  }, []);

  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;

    const map = L.map(mapRef.current, {
      zoomControl: false,
      attributionControl: false,
    }).setView([7.9465, -1.0232], 7);

    mapInstanceRef.current = map;

    // Dark CARTO tiles — shows city names, roads, borders
    L.tileLayer(
      "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
      { maxZoom: 19 }
    ).addTo(map);

    // Zoom control top-right
    L.control.zoom({ position: "topright" }).addTo(map);

    // Attribution bottom-right
    L.control.attribution({ position: "bottomright", prefix: "© CARTO · OSM" }).addTo(map);

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!mapInstanceRef.current || !data) return;
    const map = mapInstanceRef.current;
    clearLayers();

    // ── Demand layer ──
    const demandGroup = L.layerGroup();
    data.map.demand_points.forEach((p) => {
      // Outer glow
      L.circleMarker([p.lat, p.lng], {
        radius: 16 + p.intensity * 20,
        fillColor: "#ef4444",
        color: "transparent",
        fillOpacity: 0.12 + p.intensity * 0.08,
        interactive: false,
      }).addTo(demandGroup);

      // Core dot
      const marker = L.circleMarker([p.lat, p.lng], {
        radius: 5 + p.intensity * 6,
        fillColor: "#ef4444",
        color: "#ef4444",
        weight: 1,
        fillOpacity: 0.75 + p.intensity * 0.2,
      }).addTo(demandGroup);

      marker.bindPopup(
        `<div style="font-family:'Space Grotesk',sans-serif;min-width:140px">
          <div style="font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px">Demand Point</div>
          <div style="font-weight:600;margin-bottom:6px">Intensity: ${(p.intensity * 100).toFixed(0)}%</div>
        </div>`,
        { className: "dark-popup" }
      );
    });
    layersRef.current.demand = demandGroup;
    demandGroup.addTo(map);

    // ── Supply layer ──
    const supplyGroup = L.layerGroup();
    data.supply.facilities.forEach((f) => {
      // Coverage ring
      L.circleMarker([f.lat, f.lng], {
        radius: 12 + (f.coverage / 100) * 16,
        fillColor: "#10b981",
        color: "rgba(16,185,129,0.6)",
        fillOpacity: 0.08,
        interactive: false,
      }).addTo(supplyGroup);

      const marker = L.circleMarker([f.lat, f.lng], {
        radius: 5,
        fillColor: "#10b981",
        color: "#0f172a",
        weight: 1.5,
        fillOpacity: 0.95,
      }).addTo(supplyGroup);
      L.circleMarker([f.lat, f.lng], {
        radius: 2.5,
        fillColor: "#ffffff",
        color: "transparent",
        fillOpacity: 0.9,
        interactive: false,
      }).addTo(supplyGroup);

      marker.bindPopup(
        `<div style="font-family:'Space Grotesk',sans-serif;min-width:180px">
          <div style="font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px">${f.type}</div>
          <div style="font-weight:700;font-size:14px;margin-bottom:6px">${f.name}</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;font-size:12px">
            <div><span style="color:#94a3b8">Coverage</span><br/><strong style="color:#10b981">${f.coverage}%</strong></div>
            <div><span style="color:#94a3b8">Beds</span><br/><strong>${f.beds}</strong></div>
            <div><span style="color:#94a3b8">Staff</span><br/><strong>${f.staff}</strong></div>
            <div><span style="color:#94a3b8">Region</span><br/><strong>${f.region}</strong></div>
          </div>
          <div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap;font-size:10px">
            <a href="https://www.google.com/maps?q=${f.lat},${f.lng}" target="_blank" rel="noreferrer" style="color:#10b981;text-decoration:none;border:1px solid rgba(16,185,129,0.3);padding:2px 6px;border-radius:6px">Google Maps</a>
            <a href="https://www.openstreetmap.org/?mlat=${f.lat}&mlon=${f.lng}#map=16/${f.lat}/${f.lng}" target="_blank" rel="noreferrer" style="color:#94a3b8;text-decoration:none;border:1px solid rgba(148,163,184,0.3);padding:2px 6px;border-radius:6px">OSM</a>
            <a href="https://www.google.com/maps/@${f.lat},${f.lng},18z/data=!3m1!1e3" target="_blank" rel="noreferrer" style="color:#f59e0b;text-decoration:none;border:1px solid rgba(245,158,11,0.3);padding:2px 6px;border-radius:6px">Satellite</a>
          </div>
          <div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:3px">
            ${f.capabilities.map((c) => `<span style="background:rgba(16,185,129,0.15);color:#10b981;padding:2px 6px;border-radius:4px;font-size:10px">${c}</span>`).join("")}
          </div>
        </div>`,
        { className: "dark-popup" }
      );
    });
    layersRef.current.supply = supplyGroup;
    supplyGroup.addTo(map);

    // ── Desert layer ──
    const desertGroup = L.layerGroup();
    data.gap.deserts.forEach((d) => {
      // Warning pulse ring
      L.circleMarker([d.lat, d.lng], {
        radius: 26,
        fillColor: "#f59e0b",
        color: "#f59e0b",
        weight: 2,
        fillOpacity: 0.1,
        dashArray: "3 6",
        interactive: false,
      }).addTo(desertGroup);

      const marker = L.marker([d.lat, d.lng], {
        icon: L.divIcon({
          html: `<div style="width:30px;height:30px;background:#f59e0b;border-radius:6px;transform:rotate(45deg);display:flex;align-items:center;justify-content:center;box-shadow:0 0 18px rgba(245,158,11,0.5)"><span style="transform:rotate(-45deg);font-weight:800;font-size:14px;color:#0b0f1a">!</span></div>`,
          className: "",
          iconSize: [30, 30],
          iconAnchor: [15, 15],
        }),
      }).addTo(desertGroup);

      marker.bindPopup(
        `<div style="font-family:'Space Grotesk',sans-serif;min-width:180px">
          <div style="font-size:11px;color:#f59e0b;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px">Medical Desert</div>
          <div style="font-weight:700;font-size:14px;margin-bottom:6px">${d.region_name}</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;font-size:12px">
            <div><span style="color:#94a3b8">Gap Score</span><br/><strong style="color:#f59e0b">${(d.gap_score * 100).toFixed(0)}%</strong></div>
            <div><span style="color:#94a3b8">Population</span><br/><strong>${d.population_affected.toLocaleString()}</strong></div>
            <div style="grid-column:span 2"><span style="color:#94a3b8">Nearest Facility</span><br/><strong>${d.nearest_facility_km} km</strong></div>
          </div>
          <div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap;font-size:10px">
            <a href="https://www.google.com/maps?q=${d.lat},${d.lng}" target="_blank" rel="noreferrer" style="color:#f59e0b;text-decoration:none;border:1px solid rgba(245,158,11,0.3);padding:2px 6px;border-radius:6px">Google Maps</a>
            <a href="https://www.openstreetmap.org/?mlat=${d.lat}&mlon=${d.lng}#map=8/${d.lat}/${d.lng}" target="_blank" rel="noreferrer" style="color:#94a3b8;text-decoration:none;border:1px solid rgba(148,163,184,0.3);padding:2px 6px;border-radius:6px">OSM</a>
            <a href="https://www.google.com/maps/@${d.lat},${d.lng},10z/data=!3m1!1e3" target="_blank" rel="noreferrer" style="color:#f59e0b;text-decoration:none;border:1px solid rgba(245,158,11,0.3);padding:2px 6px;border-radius:6px">Satellite</a>
          </div>
          <div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:3px">
            ${d.missing_capabilities.map((c) => `<span style="background:rgba(245,158,11,0.15);color:#f59e0b;padding:2px 6px;border-radius:4px;font-size:10px">${c}</span>`).join("")}
          </div>
        </div>`,
        { className: "dark-popup" }
      );
    });
    layersRef.current.deserts = desertGroup;
  }, [clearLayers, data]);

  // Toggle layers
  const toggleLayer = useCallback((key: string, show: boolean) => {
    const map = mapInstanceRef.current;
    const layer = layersRef.current[key];
    if (!map || !layer) return;
    if (show && !map.hasLayer(layer)) layer.addTo(map);
    if (!show && map.hasLayer(layer)) map.removeLayer(layer);
  }, []);

  useEffect(() => {
    toggleLayer("demand", showDemand);
  }, [showDemand, toggleLayer]);

  useEffect(() => {
    toggleLayer("supply", showSupply);
  }, [showSupply, toggleLayer]);

  useEffect(() => {
    toggleLayer("deserts", showDeserts);
  }, [showDeserts, toggleLayer]);

  // Sync layers with active tab
  useEffect(() => {
    setShowDemand(activeTab === "demand");
    setShowSupply(activeTab === "supply");
    setShowDeserts(activeTab === "gap");
  }, [activeTab]);

  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || focusLat == null || focusLng == null) return;
    map.flyTo([focusLat, focusLng], focusZoom, {
      animate: true,
      duration: 1.2,
    });
  }, [focusLat, focusLng, focusZoom]);

  return (
    <div className={className}>
      <div
        className="relative rounded-2xl overflow-hidden border border-border/50"
        style={{ height }}
      >
        <div ref={mapRef} className="w-full h-full" />
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/70 text-xs text-muted-foreground">
            Loading map layers...
          </div>
        )}

        {/* Layer toggles */}
        <div className="absolute top-3 left-3 z-[1000] flex flex-col gap-2">
          {[
            { key: "demand", label: "Demand", dot: "pulse-dot-red", checked: showDemand, set: setShowDemand },
            { key: "supply", label: "Supply", dot: "pulse-dot-green", checked: showSupply, set: setShowSupply },
            { key: "deserts", label: "Gaps", dot: "pulse-dot-yellow", checked: showDeserts, set: setShowDeserts },
          ].map((l) => (
            <button
              key={l.key}
              onClick={() => onModeChange?.(l.key === "deserts" ? "gap" : (l.key as "demand" | "supply"))}
              className={`flex items-center gap-2 text-[10px] uppercase tracking-[0.25em] cursor-pointer select-none glass rounded-full px-3 py-2 transition-all hover:scale-[1.02] ${
                activeTab === (l.key === "deserts" ? "gap" : l.key)
                  ? "text-foreground"
                  : "text-muted-foreground"
              }`}
            >
              <span className={`pulse-dot ${l.dot}`} />
              <span>{l.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default InteractiveMap;
