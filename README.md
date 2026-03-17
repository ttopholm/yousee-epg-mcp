# YouSee EPG MCP Server 📺

**[Dansk](#dansk)** | **[English](#english)**

---

## Dansk

Se hvad der kører i TV via Claude eller ChatGPT. MCP-server til YouSee's danske TV-guide.

### Installation

Installer-scriptet sætter alt op for dig: Python, uv og konfiguration af Claude Desktop + Claude Code.

#### macOS / Linux

Åbn **Terminal** og kør:

```bash
curl -fsSL https://raw.githubusercontent.com/ttopholm/yousee-epg-mcp/main/install.sh | bash
```

#### Windows

Åbn **PowerShell** og kør:

```powershell
irm https://raw.githubusercontent.com/ttopholm/yousee-epg-mcp/main/install.ps1 | iex
```

#### Manuel installation

<details>
<summary>Hvis du foretrækker at installere manuelt</summary>

**Claude Code:**

```bash
claude mcp add yousee-epg -- uvx yousee-epg-mcp
```

**Claude Desktop:**

Åbn **Settings → Developer → Edit Config** og tilføj:

```json
{
  "mcpServers": {
    "yousee-epg": {
      "command": "uvx",
      "args": ["yousee-epg-mcp"]
    }
  }
}
```

Genstart Claude Desktop bagefter.

</details>

### Tools

| Tool | Beskrivelse |
|------|-------------|
| `yousee_channels` | Alle tilgængelige TV-kanaler med ID og logo |
| `yousee_programs` | Programoversigt for en kanal på en dato (±7 dage) |
| `yousee_search` | Søg efter et program på tværs af alle kanaler |
| `yousee_now_playing` | Hvad kører lige nu |
| `yousee_prime_time` | Hvad kører i aften kl. 19-22 på de store kanaler |
| `yousee_genre` | Find programmer efter genre (Sport, Film, Nyheder, Serier, Børn) |

### Eksempler

- *"Hvad kører på DR1 lige nu?"*
- *"Hvornår sendes Vild med dans?"*
- *"Hvad er der i TV i aften?"*
- *"Er der sport på TV i dag?"*
- *"Vis mig film på TV i morgen"*

### ChatGPT

ChatGPT kræver en HTTP-server tilgængelig fra internettet:

```bash
pip install yousee-epg-mcp
yousee-epg-mcp-http
```

Gør den tilgængelig med f.eks. Cloudflare Tunnel:

```bash
cloudflared tunnel --url http://localhost:8000
```

Tilføj din URL + `/mcp` som connector i ChatGPT (kræver Developer Mode + Plus/Pro).

### Docker

```bash
docker build -t yousee-epg-mcp .
docker run -p 8000:8000 yousee-epg-mcp
```

### API

Bruger YouSee's offentlige EPG — ingen nøgle påkrævet, ±7 dage.

- `GET https://secure.yousee.tv/epg/v2/channels`
- `GET https://secure.yousee.tv/epg/v2/channels/:id/:dato`

### Release

Ny version publiceres automatisk til PyPI ved git tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

---

## English

Browse Danish TV listings via Claude or ChatGPT. MCP server for YouSee's TV guide.

### Installation

The install script handles everything: Python, uv, and configuration for Claude Desktop + Claude Code.

#### macOS / Linux

Open **Terminal** and run:

```bash
curl -fsSL https://raw.githubusercontent.com/ttopholm/yousee-epg-mcp/main/install.sh | bash
```

#### Windows

Open **PowerShell** and run:

```powershell
irm https://raw.githubusercontent.com/ttopholm/yousee-epg-mcp/main/install.ps1 | iex
```

#### Manual installation

<details>
<summary>If you prefer to install manually</summary>

**Claude Code:**

```bash
claude mcp add yousee-epg -- uvx yousee-epg-mcp
```

**Claude Desktop:**

Open **Settings → Developer → Edit Config** and add:

```json
{
  "mcpServers": {
    "yousee-epg": {
      "command": "uvx",
      "args": ["yousee-epg-mcp"]
    }
  }
}
```

Restart Claude Desktop afterwards.

</details>

### Tools

| Tool | Description |
|------|-------------|
| `yousee_channels` | All available TV channels with ID and logo |
| `yousee_programs` | Program schedule for a channel on a given date (±7 days) |
| `yousee_search` | Search for a program across all channels |
| `yousee_now_playing` | What's on right now |
| `yousee_prime_time` | Prime time shows (19:00–22:00) on major Danish channels |
| `yousee_genre` | Find programs by genre (Sports, Movies, News, Series, Kids) |

### Examples

- *"What's on DR1 right now?"*
- *"When is Vild med dans on?"*
- *"What's on TV tonight?"*
- *"Is there any sports on TV today?"*
- *"Show me movies on TV tomorrow"*

### ChatGPT

ChatGPT requires an HTTP server accessible from the internet:

```bash
pip install yousee-epg-mcp
yousee-epg-mcp-http
```

Expose it using e.g. Cloudflare Tunnel:

```bash
cloudflared tunnel --url http://localhost:8000
```

Add your URL + `/mcp` as a connector in ChatGPT (requires Developer Mode + Plus/Pro).

### Docker

```bash
docker build -t yousee-epg-mcp .
docker run -p 8000:8000 yousee-epg-mcp
```

### API

Uses YouSee's public EPG — no API key required, ±7 days.

- `GET https://secure.yousee.tv/epg/v2/channels`
- `GET https://secure.yousee.tv/epg/v2/channels/:id/:date`

### Release

New versions are published automatically to PyPI on git tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

## License / Licens

MIT
