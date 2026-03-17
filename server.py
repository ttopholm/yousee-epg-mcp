"""
YouSee EPG MCP Server
=====================
MCP-server til YouSee's TV-guide via FastMCP.

API:
  GET https://secure.yousee.tv/epg/v2/channels
  GET https://secure.yousee.tv/epg/v2/channels/:channelid/:date  (±7 dage)
"""

from datetime import datetime, timedelta
import asyncio
from fastmcp import FastMCP
import httpx

mcp = FastMCP(
    "yousee-epg",
    instructions="YouSee TV-guide. Brug yousee_channels til at finde kanal-ID'er, "
    "yousee_programs til at hente programmer for en kanal, "
    "og yousee_search til at søge efter et program på tværs af kanaler.",
)

BASE_URL = "https://secure.yousee.tv/epg/v2"
_client = httpx.AsyncClient(base_url=BASE_URL, timeout=15)


async def _get(path: str) -> dict | list:
    """GET request til YouSee EPG API."""
    resp = await _client.get(f"/{path}")
    resp.raise_for_status()
    return resp.json()


def _extract_list(data, *keys) -> list:
    """Hjælper til at finde en liste i API-svaret."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in keys:
            if k in data and isinstance(data[k], list):
                return data[k]
    return []


@mcp.tool()
async def yousee_channels() -> list:
    """Hent alle tilgængelige YouSee TV-kanaler med ID og navn."""
    data = await _get("channels")
    return _extract_list(data, "channels", "data", "result") or data


@mcp.tool()
async def yousee_programs(channel_id: str, date: str | None = None) -> list:
    """Hent programoversigt for en kanal på en dato (±7 dage fra i dag).

    Args:
        channel_id: Kanal-ID fra yousee_channels.
        date: Dato i YYYY-MM-DD format. Standard er i dag.
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    data = await _get(f"channels/{channel_id}/{date}")
    return _extract_list(data, "programs", "data", "result", "entries") or data


@mcp.tool()
async def yousee_search(query: str, days: int = 3) -> list[dict]:
    """Søg efter et TV-program på tværs af alle YouSee-kanaler.

    Args:
        query: Programnavn eller nøgleord at søge efter.
        days: Antal dage frem at søge (1-7, standard 3).
    """
    days = min(max(days, 1), 7)
    channels = await yousee_channels()
    if not channels:
        return [{"error": "Kunne ikke hente kanaler"}]

    query_lower = query.lower()
    today = datetime.now()
    sem = asyncio.Semaphore(10)

    async def _fetch_and_filter(ch_id: str, ch_name: str, date: str) -> list[dict]:
        async with sem:
            try:
                programs = await yousee_programs(ch_id, date)
            except Exception:
                return []
        hits = []
        for prog in programs if isinstance(programs, list) else []:
            title = prog.get("title", "") or ""
            desc = prog.get("description", "") or prog.get("desc", "") or ""
            if query_lower in title.lower() or query_lower in desc.lower():
                hits.append({
                    "title": title,
                    "description": desc[:300],
                    "channel": ch_name,
                    "channel_id": ch_id,
                    "date": date,
                    "begin": prog.get("begin") or prog.get("start") or prog.get("startTime") or "",
                    "end": prog.get("end") or prog.get("stop") or prog.get("endTime") or "",
                    "category": prog.get("category") or prog.get("genre") or "",
                })
        return hits

    tasks = []
    for day_offset in range(days):
        date = (today + timedelta(days=day_offset)).strftime("%Y-%m-%d")
        for ch in channels:
            ch_id = ch.get("id") or ch.get("channel_id") or ch.get("channelId")
            ch_name = ch.get("name") or ch.get("title") or str(ch_id)
            if not ch_id:
                continue
            tasks.append(_fetch_and_filter(str(ch_id), ch_name, date))

    all_hits = await asyncio.gather(*tasks)
    results = [hit for hits in all_hits for hit in hits]

    return results or [{"info": f"Ingen programmer fundet for '{query}' i de næste {days} dage."}]


def main():
    """Kør som stdio MCP-server (Claude Code)."""
    mcp.run()


def main_http():
    """Kør som HTTP MCP-server (ChatGPT, remote klienter)."""
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    import sys
    if "--http" in sys.argv:
        main_http()
    else:
        main()
