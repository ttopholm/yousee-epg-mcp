#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# YouSee EPG MCP Server — Installer til macOS og Linux
# Installerer Python, uv og konfigurerer Claude Desktop + Code
# ──────────────────────────────────────────────────────────────
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; }

echo ""
echo "══════════════════════════════════════════════"
echo "  YouSee EPG MCP Server — Installer"
echo "══════════════════════════════════════════════"
echo ""

# ─── 1. Tjek Python ──────────────────────────────────────────

PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        version=$("$cmd" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    error "Python 3.10 eller nyere blev ikke fundet."
    echo ""
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  Installer Python med Homebrew:"
        echo ""
        echo "    1. Åbn Terminal (søg efter 'Terminal' i Spotlight)"
        echo "    2. Installer Homebrew (hvis du ikke har det):"
        echo "       /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        echo "    3. Installer Python:"
        echo "       brew install python@3.12"
        echo ""
    else
        echo "  Installer Python med din package manager:"
        echo ""
        echo "    Ubuntu/Debian:  sudo apt update && sudo apt install python3"
        echo "    Fedora:         sudo dnf install python3"
        echo "    Arch:           sudo pacman -S python"
        echo ""
    fi
    echo "  Kør derefter dette script igen."
    exit 1
fi

info "Python fundet: $($PYTHON --version)"

# ─── 2. Installer uv ─────────────────────────────────────────

if command -v uv &>/dev/null; then
    info "uv er allerede installeret: $(uv --version)"
else
    warn "Installerer uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Tilføj uv til PATH for resten af scriptet
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    if command -v uv &>/dev/null; then
        info "uv installeret: $(uv --version)"
    else
        error "Kunne ikke installere uv. Prøv manuelt: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi
fi

# ─── 3. Verificer at uvx virker ──────────────────────────────

if ! command -v uvx &>/dev/null; then
    # uvx er en del af uv, men tjek alligevel
    warn "uvx ikke fundet i PATH — prøver med fuld sti"
    UVX="$HOME/.local/bin/uvx"
    if [ ! -f "$UVX" ]; then
        UVX="$HOME/.cargo/bin/uvx"
    fi
    if [ ! -f "$UVX" ]; then
        error "uvx blev ikke fundet. Genstart din terminal og kør scriptet igen."
        exit 1
    fi
else
    UVX="uvx"
fi

info "uvx er klar"

# ─── 4. Konfigurer Claude Desktop ────────────────────────────

configure_claude_desktop() {
    local config_dir config_file

    if [[ "$OSTYPE" == "darwin"* ]]; then
        config_dir="$HOME/Library/Application Support/Claude"
    else
        config_dir="$HOME/.config/Claude"
    fi
    config_file="$config_dir/claude_desktop_config.json"

    if [ ! -d "$config_dir" ]; then
        warn "Claude Desktop ser ikke ud til at være installeret (mappen $config_dir findes ikke)"
        echo "  Download Claude Desktop fra: https://claude.ai/download"
        echo "  Kør dette script igen efter installation."
        return
    fi

    # Brug Python til at redigere JSON sikkert
    $PYTHON -c "
import json, os, sys

config_file = '$config_file'
uvx_path = os.popen('which uvx').read().strip()
if not uvx_path:
    uvx_path = os.path.expanduser('~/.local/bin/uvx')
server_entry = {
    'command': uvx_path,
    'args': ['yousee-epg-mcp']
}

# Læs eksisterende config eller start fra scratch
if os.path.exists(config_file):
    with open(config_file, 'r') as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError:
            config = {}
else:
    config = {}

# Tilføj mcpServers hvis det ikke findes
if 'mcpServers' not in config:
    config['mcpServers'] = {}

# Tjek om den allerede er konfigureret
if 'yousee-epg' in config['mcpServers']:
    print('ALREADY_EXISTS')
    sys.exit(0)

config['mcpServers']['yousee-epg'] = server_entry

with open(config_file, 'w') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

print('CONFIGURED')
"
    local result=$?
    if [ $result -eq 0 ]; then
        local output
        output=$($PYTHON -c "
import json, os
config_file = '$config_file'
if os.path.exists(config_file):
    with open(config_file, 'r') as f:
        config = json.load(f)
    if 'yousee-epg' in config.get('mcpServers', {}):
        print('OK')
")
        if [ "$output" = "OK" ]; then
            info "Claude Desktop konfigureret"
            warn "Genstart Claude Desktop for at aktivere serveren"
        fi
    else
        error "Kunne ikke konfigurere Claude Desktop"
    fi
}

configure_claude_desktop

# ─── 5. Konfigurer Claude Code ───────────────────────────────

if command -v claude &>/dev/null; then
    UVX_FULL=$(which uvx 2>/dev/null || echo "$HOME/.local/bin/uvx")
    claude mcp add yousee-epg -- "$UVX_FULL" yousee-epg-mcp 2>/dev/null && \
        info "Claude Code konfigureret" || \
        warn "Claude Code: serveren er muligvis allerede tilføjet"
else
    warn "Claude Code er ikke installeret — spring over"
    echo "  Installer fra: https://docs.anthropic.com/en/docs/claude-code/overview"
fi

# ─── Færdig ───────────────────────────────────────────────────

echo ""
echo "══════════════════════════════════════════════"
echo "  Installation færdig!"
echo "══════════════════════════════════════════════"
echo ""
echo "  Prøv at spørge Claude:"
echo "    • \"Hvad kører på DR1 lige nu?\""
echo "    • \"Hvad er der i TV i aften?\""
echo "    • \"Er der sport på TV i dag?\""
echo ""
