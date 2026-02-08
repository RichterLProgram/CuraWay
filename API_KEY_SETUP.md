# 🔑 OpenAI API Key Setup

## Warum brauchen Sie einen API Key?

Die AI ist **essentiell** für die Challenge und generiert:
- ✅ **Personalisierte Take Action Reports** für jeden Hotspot
- ✅ **Intelligente Empfehlungen** basierend auf regionalen Daten
- ✅ **Evidenzbasierte Vorschläge** durch RAG (Retrieval Augmented Generation)
- ✅ **Dynamische Simulationen** für verschiedene Szenarien

**Ohne API Key:** Reports sind alle gleich (Fallback-Modus)  
**Mit API Key:** Jeder Report ist einzigartig und datengetrieben!

---

## 📝 Schritt-für-Schritt Anleitung

### 1. OpenAI API Key erhalten

1. Gehen Sie zu: **https://platform.openai.com/api-keys**
2. Loggen Sie sich ein (oder erstellen Sie einen Account)
3. Klicken Sie auf **"Create new secret key"**
4. Kopieren Sie den Key (beginnt mit `sk-...`)

⚠️ **Wichtig:** Der Key wird nur EINMAL angezeigt!

### 2. API Key in .env Datei eintragen

Öffnen Sie die Datei:
```
backend/.env
```

Ersetzen Sie diese Zeile:
```env
OPENAI_API_KEY=sk-your-key-here
```

Mit Ihrem echten Key:
```env
OPENAI_API_KEY=sk-proj-abc123...
```

### 3. Backend neu starten

**PowerShell:**
```powershell
# Im backend Ordner
cd backend

# Flask API starten
python -m flask --app api.server run --port 5000 --debug

# In neuem Terminal: Agent API starten
python -m uvicorn agent_api.main:app --reload --port 8000
```

### 4. Testen

Öffnen Sie die Konsole im Browser (F12) und überprüfen Sie:
- ✅ Keine 500 Errors mehr bei `/agent/run`
- ✅ Take Action Reports sind unterschiedlich
- ✅ AI generiert personalisierte Empfehlungen

---

## 🎯 Erweiterte Konfiguration (Optional)

In der `.env` Datei können Sie auch anpassen:

```env
# Modell ändern (Standard: gpt-4o-mini ist günstig & schnell)
OPENAI_MODEL=gpt-4o

# Kreativität der AI (0.0 = deterministisch, 2.0 = sehr kreativ)
LLM_TEMPERATURE=0.5

# RAG deaktivieren (nicht empfohlen)
RAG_DISABLED=false
```

---

## 💰 Kosten

- **gpt-4o-mini** (empfohlen): ~$0.15 per 1M tokens
- **gpt-4o**: ~$2.50 per 1M tokens
- Ein Report generiert ca. 1000-3000 tokens
- **Kosten pro Report:** $0.0002 - $0.0005 (weniger als 1 Cent!)

---

## 🔒 Sicherheit

✅ Die `.env` Datei ist in `.gitignore` und wird NICHT committet  
✅ Teilen Sie Ihren API Key niemals öffentlich  
✅ Löschen Sie den Key bei platform.openai.com wenn kompromittiert  

---

## ❌ Troubleshooting

### Problem: "OPENAI_API_KEY is not set"

**Lösung:**
1. Überprüfen Sie, ob `.env` Datei existiert
2. Überprüfen Sie, ob der Key korrekt ist (beginnt mit `sk-`)
3. Backend neu starten (wichtig!)

### Problem: "Invalid API key"

**Lösung:**
1. Key auf https://platform.openai.com/api-keys überprüfen
2. Neuen Key erstellen wenn nötig
3. Sicherstellen dass keine Leerzeichen im Key sind

### Problem: "Rate limit exceeded"

**Lösung:**
1. Warten Sie 1-2 Minuten
2. Guthaben auf OpenAI Account überprüfen
3. Eventuell auf gpt-4o-mini downgraden

---

## 📚 Weitere Ressourcen

- OpenAI API Dokumentation: https://platform.openai.com/docs
- Preise: https://openai.com/api/pricing/
- Rate Limits: https://platform.openai.com/docs/guides/rate-limits

---

Viel Erfolg bei der Challenge! 🚀
