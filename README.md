# YouSee EPG MCP Server 📺

Se hvad der kører i TV via Claude eller ChatGPT. MCP-server til YouSee's danske TV-guide.

## Hurtig installation (Claude Code)

```bash
claude mcp add yousee-epg -- uvx yousee-epg-mcp
```

Det var det! Spørg nu Claude ting som *"Hvad kører på DR1 i aften?"*

## Claude Desktop

Åbn **Settings → Developer → Edit Config** og tilføj `yousee-epg` under `mcpServers`:

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

Genstart Claude Desktop, og serveren er klar.

## Tools

| Tool | Beskrivelse |
|------|-------------|
| `yousee_channels` | Alle tilgængelige TV-kanaler med ID og logo |
| `yousee_programs` | Programoversigt for en kanal på en dato (±7 dage) |
| `yousee_search` | Søg efter et program på tværs af alle kanaler |
| `yousee_now_playing` | Hvad kører lige nu |
| `yousee_prime_time` | Hvad kører i aften kl. 19-22 på de store kanaler |
| `yousee_genre` | Find programmer efter genre (Sport, Film, Nyheder, Serier, Børn) |

## Eksempler

- *"Hvad kører på DR1 lige nu?"*
- *"Hvornår sendes Vild med dans?"*
- *"Hvad er der i TV i aften?"*
- *"Er der sport på TV i dag?"*
- *"Vis mig film på TV i morgen"*

## ChatGPT

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

## Docker

```bash
docker build -t yousee-epg-mcp .
docker run -p 8000:8000 yousee-epg-mcp
```

## API

Bruger YouSee's offentlige EPG — ingen nøgle påkrævet, ±7 dage.

- `GET https://secure.yousee.tv/epg/v2/channels`
- `GET https://secure.yousee.tv/epg/v2/channels/:id/:dato`

## Release

Ny version publiceres automatisk til PyPI ved git tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

## Licens

MIT
