# Automated Installer for Dual-Model AI Router
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "    Installing Dual-Model AI Router (Windows)     " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Install Python dependencies
Write-Host "[1/3] Installing Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error installing Python dependencies. Make sure Python and pip are installed." -ForegroundColor Red
    exit 1
}

# 2. Setup the global 'ai' alias
Write-Host "`n[2/3] Setting up the 'ai' command..." -ForegroundColor Yellow
$pythonScripts = (python -c "import sysconfig; print(sysconfig.get_path('scripts'))")
if (-not (Test-Path $pythonScripts)) {
    New-Item -ItemType Directory -Force -Path $pythonScripts | Out-Null
}

$installDir = $PSScriptRoot
$cmdPath = Join-Path $pythonScripts "ai.cmd"

# Create a batch wrapper that points exactly to where the user cloned the repo
$cmdContent = "@echo off`npython `"$installDir\router.py`" %*"
Set-Content -Path $cmdPath -Value $cmdContent
Write-Host "  -> Created global 'ai' command mapped to $installDir\router.py" -ForegroundColor Green

# 3. API Key Setup
Write-Host "`n[3/3] OpenRouter API Key Setup" -ForegroundColor Yellow
$currentKey = [Environment]::GetEnvironmentVariable("OPENROUTER_API_KEY", "User")
if (-not $currentKey) {
    Write-Host "You need an OpenRouter API key to use the free Laguna/Nemotron models."
    Write-Host "Get one at: https://openrouter.ai/keys"
    $key = Read-Host "Paste your OpenRouter API Key here (or press Enter to skip)"
    if ($key) {
        [Environment]::SetEnvironmentVariable("OPENROUTER_API_KEY", $key, "User")
        Write-Host "  -> API Key saved permanently to your Windows user account!" -ForegroundColor Green
    }
} else {
    Write-Host "  -> OPENROUTER_API_KEY is already set." -ForegroundColor Green
}

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host " Installation Complete! " -ForegroundColor Green
Write-Host " Please close this terminal and open a new one. " -ForegroundColor White
Write-Host " Then, type 'ai' to launch your assistant. " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
