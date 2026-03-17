# ──────────────────────────────────────────────────────────────
# YouSee EPG MCP Server — Installer til Windows
# Installerer Python, uv og konfigurerer Claude Desktop + Code
# ──────────────────────────────────────────────────────────────

$ErrorActionPreference = "Stop"

function Write-Info($msg)  { Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn($msg)  { Write-Host "[!]  $msg" -ForegroundColor Yellow }
function Write-Err($msg)   { Write-Host "[X]  $msg" -ForegroundColor Red }

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  YouSee EPG MCP Server - Installer" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# --- 1. Tjek Python -----------------------------------------------------------

$python = $null
foreach ($cmd in @("python", "python3")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -ge 3 -and $minor -ge 10) {
                $python = $cmd
                break
            }
        }
    } catch {}
}

if (-not $python) {
    Write-Err "Python 3.10 eller nyere blev ikke fundet."
    Write-Host ""
    Write-Host "  Installer Python paa en af disse maader:" -ForegroundColor White
    Write-Host ""
    Write-Host "  Mulighed 1 - Via winget (anbefalet):" -ForegroundColor White
    Write-Host "    winget install Python.Python.3.12" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Mulighed 2 - Download manuelt:" -ForegroundColor White
    Write-Host "    https://www.python.org/downloads/" -ForegroundColor Gray
    Write-Host "    VIGTIGT: Saat flueben ved 'Add Python to PATH' under installationen!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Genstart PowerShell og koer dette script igen efter installation."
    exit 1
}

Write-Info "Python fundet: $(& $python --version 2>&1)"

# --- 2. Installer uv ----------------------------------------------------------

$uvPath = $null
try {
    $uvVer = uv --version 2>&1
    $uvPath = "uv"
    Write-Info "uv er allerede installeret: $uvVer"
} catch {
    Write-Warn "Installerer uv..."
    try {
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
        # Opdater PATH saa uv kan findes
        $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
        $uvVer = uv --version 2>&1
        $uvPath = "uv"
        Write-Info "uv installeret: $uvVer"
    } catch {
        Write-Err "Kunne ikke installere uv. Proev manuelt: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    }
}

# --- 3. Verificer uvx ---------------------------------------------------------

try {
    $null = uvx --version 2>&1
    Write-Info "uvx er klar"
} catch {
    Write-Err "uvx blev ikke fundet. Genstart PowerShell og koer scriptet igen."
    exit 1
}

# --- 4. Konfigurer Claude Desktop ---------------------------------------------

$configDir = "$env:APPDATA\Claude"
$configFile = "$configDir\claude_desktop_config.json"

if (Test-Path $configDir) {
    $config = @{}
    if (Test-Path $configFile) {
        try {
            $config = Get-Content $configFile -Raw | ConvertFrom-Json -AsHashtable
        } catch {
            $config = @{}
        }
    }

    if (-not $config.ContainsKey("mcpServers")) {
        $config["mcpServers"] = @{}
    }

    if ($config["mcpServers"].ContainsKey("yousee-epg")) {
        Write-Info "Claude Desktop: yousee-epg er allerede konfigureret"
    } else {
        $config["mcpServers"]["yousee-epg"] = @{
            command = "uvx"
            args = @("yousee-epg-mcp")
        }
        $config | ConvertTo-Json -Depth 10 | Set-Content $configFile -Encoding UTF8
        Write-Info "Claude Desktop konfigureret"
        Write-Warn "Genstart Claude Desktop for at aktivere serveren"
    }
} else {
    Write-Warn "Claude Desktop ser ikke ud til at vaere installeret"
    Write-Host "  Download fra: https://claude.ai/download" -ForegroundColor Gray
}

# --- 5. Konfigurer Claude Code ------------------------------------------------

try {
    $null = Get-Command claude -ErrorAction Stop
    claude mcp add yousee-epg -- uvx yousee-epg-mcp 2>$null
    Write-Info "Claude Code konfigureret"
} catch {
    Write-Warn "Claude Code er ikke installeret - springer over"
    Write-Host "  Installer fra: https://docs.anthropic.com/en/docs/claude-code/overview" -ForegroundColor Gray
}

# --- Faerdig -------------------------------------------------------------------

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Installation faerdig!" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Proev at spoerge Claude:" -ForegroundColor White
Write-Host "    - 'Hvad koerer paa DR1 lige nu?'" -ForegroundColor Gray
Write-Host "    - 'Hvad er der i TV i aften?'" -ForegroundColor Gray
Write-Host "    - 'Er der sport paa TV i dag?'" -ForegroundColor Gray
Write-Host ""
