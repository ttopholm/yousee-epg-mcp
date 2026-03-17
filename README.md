# YouSee EPG MCP Server 📺

Se hvad der kører i TV via Claude eller ChatGPT. Denne MCP-server giver AI-assistenter adgang til YouSee's TV-guide, så du kan stille spørgsmål som:

- *"Hvornår sendes Vild med dans?"*
- *"Hvad kører på DR1 i aften?"*
- *"Er der fodbold på TV i denne uge?"*

## Tools

| Tool | Beskrivelse |
|------|-------------|
| `yousee_channels` | Alle tilgængelige TV-kanaler |
| `yousee_programs` | Programmer for en kanal på en dato (±7 dage) |
| `yousee_search` | Søg efter et program på tværs af alle kanaler |

---

## Installation

```bash
pip install git+https://github.com/ttopholm/yousee-epg-mcp.git
```

Eller lokalt:

```bash
cd yousee-epg-mcp
pip install .
```

---

## Brug med Claude Code

```bash
claude mcp add yousee-epg -- yousee-epg
```

Færdig! Start Claude Code og stil dine TV-spørgsmål.

---

## Brug med ChatGPT

ChatGPT kræver en MCP-server der kører over HTTP og er tilgængelig fra internettet.

### Trin 1: Start serveren

```bash
yousee-epg-http
```

Serveren starter på `http://localhost:8000`. MCP-endpointet er `http://localhost:8000/mcp`.

### Trin 2: Gør serveren tilgængelig fra internettet

Serveren skal kunne nås udefra. Her er et par muligheder:

**Mulighed A: Cloudflare Tunnel (anbefalet, gratis)**

```bash
# Installer cloudflared: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
cloudflared tunnel --url http://localhost:8000
```

Du får en URL som `https://xxxx-xxxx.trycloudflare.com`.

**Mulighed B: ngrok**

```bash
ngrok http 8000
```

Du får en URL som `https://xxxx.ngrok-free.app`.

**Mulighed C: Kør på en server**

Deploy serveren på en VPS, f.eks. via Docker, og brug din offentlige IP/domæne.

### Trin 3: Tilslut i ChatGPT

1. Åbn ChatGPT → **Indstillinger** → **Connectors** → **Advanced Settings**
2. Slå **Developer Mode** til
3. Tilføj en ny connector med din URL + `/mcp`, f.eks.:
   ```
   https://xxxx-xxxx.trycloudflare.com/mcp
   ```
4. Start en ny chat, klik **"Add sources"** og vælg din connector
5. Spørg om TV-programmet!

> **Bemærk:** Developer Mode kræver ChatGPT Plus eller Pro.

---

## API

Bruger YouSee's offentlige EPG:

- `GET https://secure.yousee.tv/epg/v2/channels`
- `GET https://secure.yousee.tv/epg/v2/channels/:id/:dato`

Ingen API-nøgle påkrævet. Data tilgængelig ±7 dage fra i dag.
