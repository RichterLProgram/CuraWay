#!/usr/bin/env python3
"""Generate a minimal HTML report for NGO planners."""

import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
output_dir = root / "output"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    analyst_api = _load_json(output_dir / "analyst_api.json")
    pipeline_trace = _load_json(output_dir / "pipeline_trace.json")

    html = _build_html(analyst_api, pipeline_trace)
    output_dir.mkdir(exist_ok=True)
    (output_dir / "report.html").write_text(html, encoding="utf-8")
    print(f"Report written: {output_dir / 'report.html'}")


def _build_html(analyst_api: dict, pipeline_trace: dict) -> str:
    api_json = json.dumps(analyst_api, ensure_ascii=False)
    trace_json = json.dumps(pipeline_trace, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>CancerCompass Analyst Report</title>
  <link
    rel="stylesheet"
    href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
  />
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; color: #0f172a; }}
    header {{ padding: 20px 28px; background: #0f172a; color: #f8fafc; }}
    main {{ padding: 20px 28px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px; }}
    .card {{ border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px; background: #fff; }}
    #map {{ height: 360px; border-radius: 12px; border: 1px solid #e2e8f0; }}
    .tag {{ display: inline-block; padding: 4px 8px; border-radius: 999px; font-size: 12px; margin-right: 6px; }}
    .risk-high {{ background: #fee2e2; color: #b91c1c; }}
    .risk-medium {{ background: #fef3c7; color: #92400e; }}
    .risk-low {{ background: #dcfce7; color: #166534; }}
    ul {{ padding-left: 18px; }}
  </style>
</head>
<body>
  <header>
    <h1>CancerCompass Analyst Report</h1>
    <p>Medical desert insights, planner recommendations, and audit trace.</p>
  </header>
  <main>
    <section class="grid">
      <div class="card">
        <h3>Demand Points</h3>
        <p id="demandCount">0</p>
      </div>
      <div class="card">
        <h3>Regions Assessed</h3>
        <p id="regionCount">0</p>
      </div>
      <div class="card">
        <h3>Planner Items</h3>
        <p id="plannerCount">0</p>
      </div>
    </section>

    <section style="margin-top: 24px;">
      <h2>Map Overview</h2>
      <div id="map"></div>
    </section>

    <section style="margin-top: 24px;">
      <h2>Regional Risk</h2>
      <div id="riskList" class="grid"></div>
    </section>

    <section style="margin-top: 24px;">
      <h2>Planner Recommendations</h2>
      <div id="plannerList" class="grid"></div>
    </section>

    <section style="margin-top: 24px;">
      <h2>Audit Trace</h2>
      <div id="traceList" class="grid"></div>
    </section>
  </main>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const analystApi = {api_json};
    const pipelineTrace = {trace_json};

    const demandPoints = analystApi.pins || [];
    const heatmap = analystApi.heatmap || [];
    const planner = analystApi.planner || [];

    document.getElementById("demandCount").textContent = demandPoints.length;
    document.getElementById("regionCount").textContent = heatmap.length;
    document.getElementById("plannerCount").textContent = planner.length;

    const map = L.map("map").setView([7.9, -1.0], 6);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {{
      maxZoom: 18,
      attribution: "© OpenStreetMap contributors"
    }}).addTo(map);

    demandPoints.forEach((p) => {{
      const marker = L.circleMarker([p.latitude, p.longitude], {{
        radius: 6,
        color: "#1d4ed8",
        fillColor: "#3b82f6",
        fillOpacity: 0.8
      }}).addTo(map);
      marker.bindPopup(`<strong>${{p.label}}</strong><br/>${{p.note || ""}}`);
    }});

    const riskList = document.getElementById("riskList");
    heatmap.forEach((region) => {{
      const riskClass = region.risk_level === "high" ? "risk-high" : region.risk_level === "medium" ? "risk-medium" : "risk-low";
      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `
        <h3>${{region.region}}</h3>
        <span class="tag ${{riskClass}}">${{region.risk_level.toUpperCase()}}</span>
        <p>Coverage score: ${{region.coverage_score}}</p>
        <p>${{region.explanation}}</p>
      `;
      riskList.appendChild(card);
    }});

    const plannerList = document.getElementById("plannerList");
    planner.forEach((item) => {{
      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `
        <h3>${{item.region}}</h3>
        <p><strong>Priority:</strong> ${{item.priority}}</p>
        <p>${{item.summary}}</p>
        <p><strong>Actions:</strong></p>
        <ul>${{(item.actions || []).map((a) => `<li>${{a}}</li>`).join("")}}</ul>
        <p>${{item.impact_notes || ""}}</p>
      `;
      plannerList.appendChild(card);
    }});

    const traceList = document.getElementById("traceList");
    (pipelineTrace.steps || []).forEach((step) => {{
      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `
        <h3>${{step.step_name}}</h3>
        <pre>${{JSON.stringify(step.input_summary, null, 2)}}</pre>
        <pre>${{JSON.stringify(step.output_summary, null, 2)}}</pre>
      `;
      traceList.appendChild(card);
    }});
  </script>
</body>
</html>"""


if __name__ == "__main__":
    main()
