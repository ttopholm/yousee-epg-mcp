# YouSee EPG MCP Server 📺

Se hvad der kører i TV via Claude eller ChatGPT. MCP-server til YouSee's danske TV-guide.

## Tools

| Tool | Beskrivelse |
|------|-------------|
| `yousee_channels` | Alle tilgængelige TV-kanaler med ID og logo |
| `yousee_programs` | Programoversigt for en kanal på en dato (±7 dage) |
| `yousee_search` | Søg efter et program på tværs af alle kanaler |
| `yousee_now_playing` | Hvad kører lige nu (populære kanaler eller specifik kanal) |
| `yousee_prime_time` | Hvad kører i aften kl. 19-22 på de store kanaler |
| `yousee_genre` | Find programmer efter genre (Sport, Film, Nyheder, Serier, Børn) |

## Installation

```bash
pip install git+https://github.com/ttopholm/yousee-epg-mcp.git
```

## Brug med Claude Code

```bash
claude mcp add yousee-epg -- yousee-epg
```

## Brug med ChatGPT

```bash
yousee-epg-http                              # Start HTTP-server på port 8000
cloudflared tunnel --url http://localhost:8000  # Gør den tilgængelig
```

Tilføj URL + `/mcp` som connector i ChatGPT (kræver Developer Mode + Plus/Pro).

## Eksempler

- *"Hvad kører på DR1 lige nu?"*
- *"Hvornår sendes Vild med dans?"*
- *"Hvad er der i TV i aften?"*
- *"Er der sport på TV i dag?"*
- *"Vis mig film på TV i morgen"*

## API

Bruger YouSee's offentlige EPG — ingen nøgle påkrævet, ±7 dage.
