# Testing Guide - Hotspot Report Feature

## Voraussetzungen

### Backend Requirements
```bash
cd backend
pip install -r requirements.txt
```

### Umgebungsvariablen
Erstelle eine `.env` Datei im `backend` Ordner:

```bash
# OpenAI API (erforderlich für AI-Features)
OPENAI_API_KEY=sk-your-key-here

# Optional: Demo-Modus für Tests ohne API Key
AGENT_DEMO_MODE=false

# Optional: RAG aktivieren/deaktivieren
RAG_DISABLED=false

# Optional: LLM-Modell
OPENAI_MODEL=gpt-4o-mini

# Optional: Temperatur
LLM_TEMPERATURE=0.2
```

## Backend Services starten

### 1. FastAPI Agent Service (Port 8000)
```bash
cd backend
uvicorn agent_api.main:app --reload --port 8000
```

Teste mit: http://localhost:8000/docs

### 2. Flask Main API (Port 5000)
```bash
cd backend
python -m flask --app api.server run --port 5000
```

Teste mit: http://localhost:5000/health

## Frontend starten

```bash
cd frontend
npm install  # beim ersten Mal
npm run dev
```

Öffne: http://localhost:5173

## Test-Szenarien

### Test 1: Basis-Funktionalität (ohne AI)
1. Öffne http://localhost:5173
2. Klicke auf "Demo" Button
3. Warte bis die Karte geladen ist
4. **Erwartung:** Karte zeigt Hotspots in Ghana

### Test 2: Hotspot-Auswahl
1. Klicke auf einen Hotspot (rote Punkte auf der Karte)
2. **Erwartung:** Region wird in der Sidebar hervorgehoben
3. Überprüfe die Gap-Score und Population-Daten
4. **Erwartung:** Daten werden angezeigt

### Test 3: Take Action - AI-Bericht (Haupt-Feature)
1. Wähle einen Hotspot aus
2. Klicke auf "Take Action" Button (oben rechts)
3. **Erwartung:** 
   - Loading-Indikator erscheint
   - "Generiere AI-Bericht für [Region]..." wird angezeigt
4. Warte 5-15 Sekunden
5. **Erwartung:**
   - Action Drawer öffnet sich
   - Personalisierte Daten für die Region werden angezeigt:
     - Region Name
     - Priority (high/medium/low)
     - Cost Breakdown (Capex/Opex)
     - Recommended Actions (AI-generiert)
     - AI Confidence Score
     - Timeline
     - Dependencies
     - Risk Flags
     - Action Graph
     - Causal Impact Snapshot

### Test 4: Action Graph
1. Im Action Drawer nach unten scrollen
2. **Erwartung:** Action Graph zeigt Abhängigkeiten zwischen Aktionen
3. Critical Path wird angezeigt

### Test 5: Simulation
1. Im Action Drawer auf "Run Simulation" klicken
2. **Erwartung:** Neue Seite öffnet sich mit Simulation

### Test 6: PDF Export
1. Im Action Drawer auf "Export plan PDF" klicken
2. **Erwartung:** PDF-Download-Dialog (noch nicht implementiert, Button ist Placeholder)

## API-Tests

### Test Backend Direkt

#### 1. Health Check (FastAPI)
```bash
curl http://localhost:8000/health
```

**Erwartete Antwort:**
```json
{
  "status": "healthy",
  "service": "CancerCompass Agent API"
}
```

#### 2. Hotspot Report (Neue Route)
```bash
curl -X POST http://localhost:8000/agent/hotspot_report \
  -H "Content-Type: application/json" \
  -d '{
    "hotspot": {
      "region_name": "Greater Accra",
      "gap_score": 0.75,
      "population_affected": 120000,
      "missing_capabilities": ["Oncology", "Diagnostics"],
      "lat": 5.6037,
      "lng": -0.1870
    },
    "demand": {"total_count": 150},
    "supply": {"avg_coverage": 45},
    "gap": {"avg_gap_score": 0.6},
    "recommendations": [],
    "baseline_kpis": {
      "demand_total": 150,
      "avg_coverage": 45,
      "total_population_underserved": 200000,
      "avg_gap_score": 0.6
    }
  }'
```

**Erwartete Antwort:** JSON mit:
- `summary`: AI-generierte Zusammenfassung
- `action_plan`: Detaillierter Aktionsplan
- `simulation_presets`: Drei Szenarien (Low, Balanced, Aggressive)
- `agent_report`: AI-Analyse mit Citations

#### 3. Flask API Health Check
```bash
curl http://localhost:5000/health
```

**Erwartete Antwort:**
```json
{
  "status": "healthy",
  "service": "HealthGrid AI"
}
```

## Fehlerbehandlung testen

### Test 1: Ohne OpenAI API Key
1. Entferne `OPENAI_API_KEY` oder setze `AGENT_DEMO_MODE=true`
2. Starte Backend neu
3. Führe "Take Action" aus
4. **Erwartung:** Demo-Daten werden angezeigt (Fallback funktioniert)

### Test 2: Backend nicht erreichbar
1. Stoppe Backend
2. Klicke auf "Take Action"
3. **Erwartung:** Fehler-Meldung oder Loading-Zustand

### Test 3: RAG deaktiviert
1. Setze `RAG_DISABLED=true`
2. Führe "Take Action" aus
3. **Erwartung:** AI-Bericht ohne Citations

## Performance-Tests

### Messung der Response-Zeit
1. Öffne Browser DevTools (F12)
2. Gehe zu "Network" Tab
3. Klicke auf "Take Action"
4. Suche nach `/agent/hotspot_report` Request
5. **Erwartung:** Response-Zeit < 15 Sekunden

### Cache-Test
1. Führe "Take Action" für einen Hotspot aus
2. Schließe den Drawer
3. Klicke erneut auf "Take Action" für denselben Hotspot (innerhalb 5 Minuten)
4. **Erwartung:** Sofortige Antwort aus Cache (keine API-Anfrage)

## Browser-Kompatibilität

Teste in:
- ✅ Chrome/Edge (empfohlen)
- ✅ Firefox
- ✅ Safari

## Bekannte Probleme und Lösungen

### Problem: "OPENAI_API_KEY is not set"
**Lösung:** Setze die Umgebungsvariable oder aktiviere `AGENT_DEMO_MODE=true`

### Problem: Backend startet nicht
**Lösung:** Prüfe ob alle Dependencies installiert sind: `pip install -r requirements.txt`

### Problem: Port 8000 oder 5000 bereits belegt
**Lösung:** 
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Oder ändere den Port
uvicorn agent_api.main:app --reload --port 8001
```

### Problem: Frontend kann Backend nicht erreichen (CORS)
**Lösung:** Backend sollte CORS bereits aktiviert haben. Prüfe Console für Fehler.

### Problem: Loading-Indikator bleibt hängen
**Lösung:** 
1. Prüfe Backend-Logs
2. Prüfe Browser Console (F12)
3. Prüfe ob OpenAI API Key gültig ist

## Erfolgs-Kriterien

✅ Backend startet ohne Fehler  
✅ Frontend startet ohne Fehler  
✅ Hotspots werden auf der Karte angezeigt  
✅ "Take Action" öffnet Action Drawer  
✅ AI-Bericht wird generiert (oder Demo-Daten bei Fallback)  
✅ Simulation-Daten werden angezeigt  
✅ Action Graph zeigt Dependencies  
✅ Keine Console-Errors im Browser  
✅ Keine Python-Errors im Backend  

## Logs überprüfen

### Backend Logs
- Terminal wo Backend läuft
- FastAPI: Automatisches Logging
- Flask: Print-Statements

### Frontend Logs
- Browser Console (F12)
- Network Tab für API-Calls

### Trace Logs
- Backend: `backend/logs/traces/`
- Provenance: `backend/output/provenance/`

## Next Steps nach erfolgreichem Test

1. Füge mehr Test-Daten hinzu
2. Erweitere RAG mit mehr Dokumenten
3. Optimiere AI-Prompts
4. Implementiere PDF-Export
5. Füge mehr Simulation-Szenarien hinzu
6. Implementiere Benutzer-Authentifizierung
7. Deployment vorbereiten
