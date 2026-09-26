Write-Host "Starting PrepPilot FastAPI Backend Server on http://127.0.0.1:8000 ..." -ForegroundColor Green
Set-Location -Path $PSScriptRoot
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
