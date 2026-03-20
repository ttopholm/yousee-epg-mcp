from datetime import datetime, timezone

import httpx
import pytest
import respx

from yousee_epg.server import (
    _channel_names,
    _programs_cache,
    _revalidating,
    resource_channels,
    resource_now_playing,
    resource_prime_time,
    prompt_tv_aften,
    prompt_find_program,
    prompt_film_i_aften,
)
import yousee_epg.server as _server

_CHANNELS_RESPONSE = {
    "channels": [
        {"id": 1, "long_name": "DR1", "name": "DR1", "logoSvg": "https://example.com/dr1.svg"},
        {"id": 2, "long_name": "TV 2", "name": "TV2", "logoSvg": "https://example.com/tv2.svg"},
    ]
}


@pytest.fixture(autouse=True)
def reset_caches():
    """Reset all caches between tests."""
    _channel_names.clear()
    _programs_cache.clear()
    _revalidating.clear()
    _server._channels_cache = None


@pytest.fixture(autouse=True)
def mock_api():
    with respx.mock(base_url="https://secure.yousee.tv/epg/v2", assert_all_called=False) as mock:
        yield mock


def _make_program(title, channel_name, channel_id, begin, end, genre="Underholdning", sub_genre=""):
    return {
        "title": title,
        "channelName": channel_name,
        "channelId": channel_id,
        "begin": begin,
        "end": end,
        "genreName": genre,
        "subGenreName": sub_genre,
        "description": f"Beskrivelse af {title}",
    }


# ─── Resources ────────────────────────────────────────────────────────────


class TestResourceChannels:
    async def test_returns_channel_list(self, mock_api):
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_CHANNELS_RESPONSE)
        )
        result = await resource_channels()
        assert "DR1 (ID: 1)" in result
        assert "TV 2 (ID: 2)" in result
        assert result.startswith("YouSee TV-kanaler:")

    async def test_single_channel(self, mock_api):
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json={"channels": [{"id": 1, "long_name": "DR1"}]})
        )
        result = await resource_channels()
        assert "YouSee TV-kanaler:" in result
        assert "DR1 (ID: 1)" in result


class TestResourceNowPlaying:
    async def test_returns_current_programs(self, mock_api):
        now = datetime.now(timezone.utc)
        program = _make_program(
            "Nyheder", "DR1", 1,
            now.replace(hour=0, minute=0).isoformat(),
            now.replace(hour=23, minute=59).isoformat(),
        )
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_CHANNELS_RESPONSE)
        )
        date = now.strftime("%Y-%m-%d")
        mock_api.get(url__regex=rf"/channels/\d+/{date}").mock(
            return_value=httpx.Response(200, json={"programs": [program]})
        )
        result = await resource_now_playing()
        assert "Lige nu på TV:" in result
        assert "Nyheder" in result

    async def test_no_programs(self, mock_api):
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_CHANNELS_RESPONSE)
        )
        now = datetime.now(timezone.utc)
        date = now.strftime("%Y-%m-%d")
        mock_api.get(url__regex=rf"/channels/\d+/{date}").mock(
            return_value=httpx.Response(200, json={"programs": []})
        )
        result = await resource_now_playing()
        assert "Ingen programmer" in result


class TestResourcePrimeTime:
    async def test_returns_primetime(self, mock_api):
        program = _make_program(
            "Aftenshowet", "DR1", 1,
            "2026-03-20T18:00:00+00:00",
            "2026-03-20T19:30:00+00:00",
        )
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_CHANNELS_RESPONSE)
        )
        mock_api.get(url__regex=r"/channels/\d+/2026-03-20").mock(
            return_value=httpx.Response(200, json={"programs": [program]})
        )
        result = await resource_prime_time("2026-03-20")
        assert "Prime time 2026-03-20:" in result
        assert "Aftenshowet" in result

    async def test_no_primetime(self, mock_api):
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_CHANNELS_RESPONSE)
        )
        mock_api.get(url__regex=r"/channels/\d+/2026-03-20").mock(
            return_value=httpx.Response(200, json={"programs": []})
        )
        result = await resource_prime_time("2026-03-20")
        assert "Ingen prime time" in result


# ─── Prompts ──────────────────────────────────────────────────────────────


class TestPromptTvAften:
    async def test_returns_recommendations(self, mock_api):
        program = _make_program(
            "Vild med dans", "TV 2", 2,
            "2026-03-20T18:00:00+00:00",
            "2026-03-20T20:00:00+00:00",
        )
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_CHANNELS_RESPONSE)
        )
        mock_api.get(url__regex=r"/channels/\d+/").mock(
            return_value=httpx.Response(200, json={"programs": [program]})
        )
        result = await prompt_tv_aften()
        assert "Vild med dans" in result
        assert "anbefal" in result.lower() or "vælge" in result.lower()

    async def test_no_programs(self, mock_api):
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_CHANNELS_RESPONSE)
        )
        mock_api.get(url__regex=r"/channels/\d+/").mock(
            return_value=httpx.Response(200, json={"programs": []})
        )
        result = await prompt_tv_aften()
        assert "ingen" in result.lower() or "Ingen" in result


class TestPromptFindProgram:
    async def test_finds_program(self, mock_api):
        program = _make_program(
            "Matador", "DR1", 1,
            "2026-03-20T20:00:00+01:00",
            "2026-03-20T21:00:00+01:00",
        )
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_CHANNELS_RESPONSE)
        )
        mock_api.get(url__regex=r"/channels/\d+/").mock(
            return_value=httpx.Response(200, json={"programs": [program]})
        )
        result = await prompt_find_program("Matador")
        assert "Matador" in result
        assert "Søgeresultater" in result

    async def test_no_results(self, mock_api):
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_CHANNELS_RESPONSE)
        )
        mock_api.get(url__regex=r"/channels/\d+/").mock(
            return_value=httpx.Response(200, json={"programs": []})
        )
        result = await prompt_find_program("xyznonexistent")
        assert "ikke fundet" in result.lower() or "Ingen" in result


class TestPromptFilmIAften:
    async def test_finds_movies(self, mock_api):
        now = datetime.now(timezone.utc)
        movie = _make_program(
            "Den skaldede frisør", "TV 2", 2,
            now.replace(hour=20, minute=0).isoformat(),
            now.replace(hour=22, minute=0).isoformat(),
            genre="Film",
        )
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_CHANNELS_RESPONSE)
        )
        mock_api.get(url__regex=r"/channels/\d+/").mock(
            return_value=httpx.Response(200, json={"programs": [movie]})
        )
        result = await prompt_film_i_aften()
        assert "Den skaldede frisør" in result
        assert "film" in result.lower()

    async def test_no_movies(self, mock_api):
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_CHANNELS_RESPONSE)
        )
        mock_api.get(url__regex=r"/channels/\d+/").mock(
            return_value=httpx.Response(200, json={"programs": []})
        )
        result = await prompt_film_i_aften()
        assert "ingen" in result.lower() or "Ingen" in result
