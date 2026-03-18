"""
YouSee EPG MCP Server
=====================
MCP-server til YouSee's TV-guide via FastMCP.

API:
  GET https://secure.yousee.tv/epg/v2/channels
  GET https://secure.yousee.tv/epg/v2/channels/:channelid/:date  (±7 dage)
"""

from datetime import datetime, timedelta, timezone
import asyncio
from zoneinfo import ZoneInfo
from fastmcp import FastMCP
import httpx

DK_TZ = ZoneInfo("Europe/Copenhagen")

mcp = FastMCP(
    "yousee-epg",
    instructions=(
        "YouSee TV-guide for danske TV-kanaler. "
        "Brug yousee_channels til kanal-ID'er, "
        "yousee_programs til programoversigt for en kanal, "
        "yousee_search til at søge efter programmer, "
        "yousee_now_playing til hvad der kører lige nu, "
        "yousee_prime_time til aftenens programmer, "
        "yousee_genre til at finde programmer efter genre."
    ),
)

BASE_URL = "https://secure.yousee.tv/epg/v2"
_client = httpx.AsyncClient(base_url=BASE_URL, timeout=15)

# Populære danske kanaler til hurtig scanning
POPULAR_CHANNEL_IDS = [1, 2, 3, 4, 5, 7, 8, 9, 10, 17, 25, 26, 30, 79, 264]

# Cache: channel_id -> korrekt kanalnavn (dvbName/long_name)
_channel_names: dict[int, str] = {}


async def _ensure_channel_names() -> None:
    """Hent og cache kanalnavne hvis ikke allerede hentet."""
    if _channel_names:
        return
    data = await _get("channels")
    channels = _extract_list(data, "channels", "data", "result") or data
    for ch in channels:
        ch_id = ch.get("id")
        if ch_id:
            _channel_names[ch_id] = (
                ch.get("dvbName") or ch.get("long_name") or ch.get("name", "")
            )


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


def _format_dk_time(time_str: str) -> str:
    """Konverter ISO tidspunkt til dansk lokal tid."""
    dt = _parse_time(time_str)
    if not dt:
        return time_str
    return dt.astimezone(DK_TZ).isoformat()


def _summarize_program(prog: dict) -> dict:
    """Lav et kompakt summary af et program."""
    ch_id = prog.get("channelId", "")
    return {
        "title": prog.get("title", ""),
        "channel": _channel_names.get(ch_id) or prog.get("channelName", ""),
        "channel_id": ch_id,
        "begin": _format_dk_time(prog.get("begin", "")),
        "end": _format_dk_time(prog.get("end", "")),
        "description": (prog.get("description") or "")[:300],
        "genre": prog.get("genreName", ""),
        "sub_genre": prog.get("subGenreName", ""),
        "age_rating": prog.get("ageRating", 0),
        "is_series": prog.get("isSeries", False),
        "series_name": prog.get("seriesName", ""),
        "episode": prog.get("episodeId", ""),
        "cast": prog.get("cast", [])[:5],
        "year": prog.get("productionYear", ""),
    }


def _parse_time(time_str: str) -> datetime | None:
    """Parse ISO tidspunkt fra API."""
    if not time_str:
        return None
    try:
        return datetime.fromisoformat(time_str)
    except (ValueError, TypeError):
        return None


# ─── Tools ───────────────────────────────────────────────────────────────


@mcp.tool()
async def yousee_channels() -> list:
    """Hent alle tilgængelige YouSee TV-kanaler med ID og navn."""
    data = await _get("channels")
    channels = _extract_list(data, "channels", "data", "result") or data
    # Returner kun de mest nyttige felter
    return [
        {
            "id": ch.get("id"),
            "name": ch.get("long_name") or ch.get("name", ""),
            "logo": ch.get("logoSvg") or ch.get("logoPng400", ""),
        }
        for ch in channels
        if ch.get("id")
    ]


@mcp.tool()
async def yousee_programs(channel_id: str, date: str | None = None) -> list:
    """Hent programoversigt for en kanal på en dato (±7 dage fra i dag).

    Args:
        channel_id: Kanal-ID fra yousee_channels.
        date: Dato i YYYY-MM-DD format. Standard er i dag.
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    await _ensure_channel_names()
    data = await _get(f"channels/{channel_id}/{date}")
    programs = _extract_list(data, "programs", "data", "result", "entries") or data
    return [_summarize_program(p) for p in programs] if isinstance(programs, list) else programs


@mcp.tool()
async def yousee_search(query: str, days: int = 3) -> list[dict]:
    """Søg efter et TV-program på tværs af alle YouSee-kanaler.

    Args:
        query: Programnavn eller nøgleord at søge efter.
        days: Antal dage frem at søge (1-7, standard 3).
    """
    days = min(max(days, 1), 7)
    await _ensure_channel_names()
    channels = await _get("channels")
    channels = _extract_list(channels, "channels", "data", "result") or channels
    if not channels:
        return [{"error": "Kunne ikke hente kanaler"}]

    query_lower = query.lower()
    today = datetime.now()
    sem = asyncio.Semaphore(10)

    async def _fetch_and_filter(ch_id: str, date: str) -> list[dict]:
        async with sem:
            try:
                data = await _get(f"channels/{ch_id}/{date}")
                programs = _extract_list(data, "programs", "data", "result", "entries") or data
            except Exception:
                return []
        hits = []
        for prog in programs if isinstance(programs, list) else []:
            title = prog.get("title", "") or ""
            desc = prog.get("description", "") or ""
            series = prog.get("seriesName", "") or ""
            if query_lower in title.lower() or query_lower in desc.lower() or query_lower in series.lower():
                hits.append(_summarize_program(prog))
        return hits

    tasks = []
    for day_offset in range(days):
        date = (today + timedelta(days=day_offset)).strftime("%Y-%m-%d")
        for ch in channels:
            ch_id = ch.get("id")
            if not ch_id:
                continue
            tasks.append(_fetch_and_filter(str(ch_id), date))

    all_hits = await asyncio.gather(*tasks)
    results = [hit for hits in all_hits for hit in hits]

    return results or [{"info": f"Ingen programmer fundet for '{query}' i de næste {days} dage."}]


@mcp.tool()
async def yousee_now_playing(channel_id: str | None = None) -> list[dict]:
    """Se hvad der sendes lige nu på YouSee TV-kanaler.

    Args:
        channel_id: Valgfrit. Specifikt kanal-ID. Uden dette vises de mest populære kanaler.
    """
    await _ensure_channel_names()
    now = datetime.now(timezone.utc)
    date = now.strftime("%Y-%m-%d")
    sem = asyncio.Semaphore(10)

    if channel_id:
        target_ids = [channel_id]
    else:
        target_ids = [str(cid) for cid in POPULAR_CHANNEL_IDS]

    async def _get_current(ch_id: str) -> dict | None:
        async with sem:
            try:
                data = await _get(f"channels/{ch_id}/{date}")
                programs = _extract_list(data, "programs", "data", "result", "entries") or data
            except Exception:
                return None
        for prog in programs if isinstance(programs, list) else []:
            begin = _parse_time(prog.get("begin", ""))
            end = _parse_time(prog.get("end", ""))
            if begin and end and begin <= now <= end:
                return _summarize_program(prog)
        return None

    tasks = [_get_current(cid) for cid in target_ids]
    results = await asyncio.gather(*tasks)
    return [r for r in results if r is not None] or [{"info": "Ingen programmer fundet lige nu."}]


@mcp.tool()
async def yousee_prime_time(date: str | None = None) -> list[dict]:
    """Vis hvad der kører i prime time (kl. 19-22) på de populære danske kanaler.

    Args:
        date: Dato i YYYY-MM-DD format. Standard er i dag.
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    await _ensure_channel_names()

    # Prime time: 19:00-22:00 dansk tid
    prime_start_hour = 19
    prime_end_hour = 22

    sem = asyncio.Semaphore(10)

    async def _get_prime(ch_id: str) -> list[dict]:
        async with sem:
            try:
                data = await _get(f"channels/{ch_id}/{date}")
                programs = _extract_list(data, "programs", "data", "result", "entries") or data
            except Exception:
                return []
        hits = []
        for prog in programs if isinstance(programs, list) else []:
            begin = _parse_time(prog.get("begin", ""))
            end = _parse_time(prog.get("end", ""))
            if not begin or not end:
                continue
            # Konverter til dansk tid og tjek overlap med prime time
            begin_dk = begin.astimezone(DK_TZ)
            end_dk = end.astimezone(DK_TZ)
            if begin_dk.hour < prime_end_hour and end_dk.hour >= prime_start_hour:
                hits.append(_summarize_program(prog))
        return hits

    tasks = [_get_prime(str(cid)) for cid in POPULAR_CHANNEL_IDS]
    all_hits = await asyncio.gather(*tasks)
    results = [hit for hits in all_hits for hit in hits]

    return results or [{"info": f"Ingen prime time programmer fundet for {date}."}]


@mcp.tool()
async def yousee_genre(genre: str, date: str | None = None) -> list[dict]:
    """Find programmer efter genre på de populære kanaler.

    Args:
        genre: Genre at filtrere på, f.eks. "Sport", "Film", "Nyheder", "Serier", "Børn", "Fakta".
        date: Dato i YYYY-MM-DD format. Standard er i dag.
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    await _ensure_channel_names()

    genre_lower = genre.lower()
    sem = asyncio.Semaphore(10)

    async def _get_by_genre(ch_id: str) -> list[dict]:
        async with sem:
            try:
                data = await _get(f"channels/{ch_id}/{date}")
                programs = _extract_list(data, "programs", "data", "result", "entries") or data
            except Exception:
                return []
        hits = []
        for prog in programs if isinstance(programs, list) else []:
            g = (prog.get("genreName") or "").lower()
            sg = (prog.get("subGenreName") or "").lower()
            title = (prog.get("title") or "").lower()
            if genre_lower in g or genre_lower in sg or genre_lower in title:
                hits.append(_summarize_program(prog))
        return hits

    tasks = [_get_by_genre(str(cid)) for cid in POPULAR_CHANNEL_IDS]
    all_hits = await asyncio.gather(*tasks)
    results = [hit for hits in all_hits for hit in hits]

    return results or [{"info": f"Ingen '{genre}' programmer fundet på {date}."}]


@mcp.tool()
async def yousee_movies(date: str | None = None) -> list[dict]:
    """Find alle film på TV i dag på tværs af populære kanaler.

    Args:
        date: Dato i YYYY-MM-DD format. Standard er i dag.
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    await _ensure_channel_names()
    now = datetime.now(timezone.utc)
    sem = asyncio.Semaphore(10)

    async def _get_movies(ch_id: str) -> list[dict]:
        async with sem:
            try:
                data = await _get(f"channels/{ch_id}/{date}")
                programs = _extract_list(data, "programs", "data", "result", "entries") or data
            except Exception:
                return []
        hits = []
        for prog in programs if isinstance(programs, list) else []:
            genre = (prog.get("genreName") or "").lower()
            if "film" not in genre:
                continue
            end = _parse_time(prog.get("end", ""))
            if end and end < now:
                continue
            hits.append(_summarize_program(prog))
        return hits

    tasks = [_get_movies(str(cid)) for cid in POPULAR_CHANNEL_IDS]
    all_hits = await asyncio.gather(*tasks)
    results = [hit for hits in all_hits for hit in hits]
    results.sort(key=lambda p: p.get("begin", ""))

    return results or [{"info": f"Ingen film fundet på {date}."}]


# ─── Entry points ────────────────────────────────────────────────────────


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
