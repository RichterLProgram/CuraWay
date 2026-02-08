# Load .env and start Agent API
$envFile = "C:\Users\Linus\Desktop\HACKNATION1STPLACE\backend\.env"

if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^([^=#]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
            Write-Host "Set: $name"
        }
    }
}

Write-Host "`nStarting Agent API with environment variables loaded..."
cd "C:\Users\Linus\Desktop\HACKNATION1STPLACE\backend"
python -m uvicorn agent_api.main:app --reload --port 8000
