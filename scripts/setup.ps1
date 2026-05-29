# setup.ps1 — One-shot bootstrap for Local Pilot
# Installs Python, uv, Ollama, creates venv, pulls model, and launches the app

$ErrorActionPreference = "Continue"
$WorkspaceRoot = Resolve-Path "$PSScriptRoot\.."

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta
Write-Host "  ✦  Local Pilot — Setup                         " -ForegroundColor White
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Magenta
Write-Host ""

# ── Step 1: Check Python ─────────────────────────────────────────────────
Write-Host "[1/5] Checking Python..." -ForegroundColor Cyan

# Refresh PATH to pick up newly installed Python
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

$PythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($PythonCmd) {
    $PythonVersion = & python --version 2>&1
    Write-Host "  ✓ $PythonVersion" -ForegroundColor Green
} else {
    Write-Host "  ✗ Python not found. Installing via winget..." -ForegroundColor Yellow
    winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements --silent
    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    $PythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $PythonCmd) {
        Write-Host "  ✗ Python installation failed. Please install manually." -ForegroundColor Red
        exit 1
    }
    Write-Host "  ✓ Python installed!" -ForegroundColor Green
}

# ── Step 2: Install uv ──────────────────────────────────────────────────
Write-Host "[2/5] Checking uv..." -ForegroundColor Cyan

$UvCmd = Get-Command uv -ErrorAction SilentlyContinue
if ($UvCmd) {
    Write-Host "  ✓ uv is already installed" -ForegroundColor Green
} else {
    Write-Host "  Installing uv..." -ForegroundColor Yellow
    python -m pip install --quiet uv
    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    Write-Host "  ✓ uv installed!" -ForegroundColor Green
}

# ── Step 3: Create venv & install dependencies ──────────────────────────
Write-Host "[3/5] Setting up Python environment..." -ForegroundColor Cyan

Push-Location $WorkspaceRoot
try {
    uv sync
    Write-Host "  ✓ Dependencies installed!" -ForegroundColor Green
} catch {
    Write-Host "  ✗ uv sync failed: $_" -ForegroundColor Red
}
Pop-Location

# ── Step 4: Check/Install Ollama ─────────────────────────────────────────
Write-Host "[4/5] Checking Ollama..." -ForegroundColor Cyan

$OllamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
if ($OllamaCmd) {
    Write-Host "  ✓ Ollama is already installed" -ForegroundColor Green
} else {
    Write-Host "  Installing Ollama via winget..." -ForegroundColor Yellow
    winget install Ollama.Ollama --accept-package-agreements --accept-source-agreements --silent
    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    Start-Sleep -Seconds 2
    $OllamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
    if (-not $OllamaCmd) {
        Write-Host "  ⚠ Ollama may require a restart to be on PATH. Trying default location..." -ForegroundColor Yellow
        $DefaultOllama = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
        if (Test-Path $DefaultOllama) {
            $env:Path += ";$env:LOCALAPPDATA\Programs\Ollama"
        }
    }
    Write-Host "  ✓ Ollama installed!" -ForegroundColor Green
}

# Start Ollama serve in background if not already running
Write-Host "[5/5] Starting Ollama and pulling best model..." -ForegroundColor Cyan

try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "  ✓ Ollama server is already running" -ForegroundColor Green
} catch {
    Write-Host "  Starting Ollama server..." -ForegroundColor Yellow
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

# Detect GPU and pull the best model
# (The Python app does this automatically too, but let's warm up the model)
Write-Host "  Detecting hardware and pulling optimal model..." -ForegroundColor Yellow

$GpuInfo = Get-CimInstance Win32_VideoController | Where-Object { $_.Name -notmatch "Intel" } | Select-Object -First 1
$VramBytes = if ($GpuInfo) { $GpuInfo.AdapterRAM } else { 0 }
$VramGB = [math]::Round($VramBytes / 1GB, 1)

if ($VramGB -ge 10) {
    $Model = "qwen2.5:14b"
} elseif ($VramGB -ge 5) {
    $Model = "qwen2.5:7b"
} elseif ($VramGB -ge 3) {
    $Model = "phi3:3.8b"
} else {
    $Model = "qwen2.5:1.5b"
}

Write-Host "  GPU: $($GpuInfo.Name) (~${VramGB}GB VRAM)" -ForegroundColor Gray
Write-Host "  Selected model: $Model" -ForegroundColor White

# Check if model already exists
$ExistingModels = ollama list 2>&1
if ($ExistingModels -match $Model.Split(":")[0]) {
    Write-Host "  ✓ Model $Model is already downloaded" -ForegroundColor Green
} else {
    Write-Host "  Pulling $Model (this may take a few minutes)..." -ForegroundColor Yellow
    ollama pull $Model
    Write-Host "  ✓ Model $Model ready!" -ForegroundColor Green
}

# ── Done! ────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "  ✦  Setup Complete!                              " -ForegroundColor White
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host ""
Write-Host "To launch Local Pilot:" -ForegroundColor Cyan
Write-Host "  python main.py                         (direct launch)" -ForegroundColor White
Write-Host '  python main.py "C:\path\to\file.txt"   (with file context)' -ForegroundColor White
Write-Host ""
Write-Host "To register the right-click context menu:" -ForegroundColor Cyan
Write-Host '  powershell -ExecutionPolicy Bypass -File .\scripts\register-context-menu.ps1' -ForegroundColor White
Write-Host ""
