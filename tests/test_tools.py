from datetime import datetime, timedelta, timezone
import asyncio
import time

import httpx
import pytest
import respx

from yousee_epg.server import (
    _channel_names,
    _programs_cache,
    _revalidating,
    _cleanup_old_dates,
    _warmup,
    _CacheEntry,
    _get_channels_cached,
    _get_programs_cached,
    PROGRAMS_TTL,
    CHANNELS_TTL,
    yousee_channels,
    yousee_genre,
    yousee_now_playing,
    yousee_prime_time,
    yousee_program_details,
    yousee_programs,
    yousee_movies,
    yousee_search,
    yousee_timeslot,
    yousee_upcoming,
)
import yousee_epg.server as _server

# Minimal channel list for _ensure_channel_names
_EMPTY_CHANNELS_RESPONSE = {"channels": [{"id": 1, "long_name": "DR1", "name": "DR1"}]}


@pytest.fixture(autouse=True)
def mock_api():
    """Activate respx mocking for all tests."""
    _channel_names.clear()
    _programs_cache.clear()
    _revalidating.clear()
    _server._channels_cache = None
    with respx.mock(base_url="https://secure.yousee.tv/epg/v2", assert_all_called=False) as mock:
        yield mock


class TestYouseeChannels:
    async def test_returns_filtered_channels(self, mock_api, sample_api_channels):
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=sample_api_channels)
        )
        result = await yousee_channels()
        assert len(result) == 1
        assert result[0]["id"] == 2
        assert result[0]["name"] == "TV 2"
        assert result[0]["logo"] == "https://example.com/tv2.svg"

    async def test_skips_channels_without_id(self, mock_api):
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json={"channels": [{"name": "No ID"}]})
        )
        result = await yousee_channels()
        assert result == []


class TestYouseePrograms:
    async def test_returns_programs(self, mock_api, sample_api_programs):
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_EMPTY_CHANNELS_RESPONSE)
        )
        mock_api.get("/channels/2/2026-03-18").mock(
            return_value=httpx.Response(200, json=sample_api_programs)
        )
        result = await yousee_programs("2", "2026-03-18")
        assert len(result) == 1
        assert result[0]["title"] == "Vild med dans"

    async def test_defaults_to_today(self, mock_api, sample_api_programs):
        today = datetime.now().strftime("%Y-%m-%d")
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_EMPTY_CHANNELS_RESPONSE)
        )
        mock_api.get(f"/channels/1/{today}").mock(
            return_value=httpx.Response(200, json=sample_api_programs)
        )
        result = await yousee_programs("1")
        assert len(result) == 1


class TestYouseeSearch:
    async def test_finds_by_title(self, mock_api, sample_program):
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json={"channels": [{"id": 1}]})
        )
        mock_api.get(url__regex=r"/channels/1/\d{4}-\d{2}-\d{2}").mock(
            return_value=httpx.Response(200, json={"programs": [sample_program]})
        )
        result = await yousee_search("Vild med dans", days=1)
        assert any(r.get("title") == "Vild med dans" for r in result)

    async def test_no_results(self, mock_api):
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json={"channels": [{"id": 1}]})
        )
        mock_api.get(url__regex=r"/channels/1/\d{4}-\d{2}-\d{2}").mock(
            return_value=httpx.Response(200, json={"programs": []})
        )
        result = await yousee_search("xyznonexistent", days=1)
        assert result[0].get("info") is not None


class TestYouseeNowPlaying:
    async def test_finds_current_program(self, mock_api):
        now = datetime.now(timezone.utc)
        program = {
            "title": "Live now",
            "channelName": "DR1",
            "channelId": "1",
            "begin": (now.replace(hour=0, minute=0)).isoformat(),
            "end": (now.replace(hour=23, minute=59)).isoformat(),
        }
        date = now.strftime("%Y-%m-%d")
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_EMPTY_CHANNELS_RESPONSE)
        )
        mock_api.get(f"/channels/1/{date}").mock(
            return_value=httpx.Response(200, json={"programs": [program]})
        )
        result = await yousee_now_playing("1")
        assert len(result) == 1
        assert result[0]["title"] == "Live now"

    async def test_no_current_program(self, mock_api):
        now = datetime.now(timezone.utc)
        date = now.strftime("%Y-%m-%d")
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_EMPTY_CHANNELS_RESPONSE)
        )
        mock_api.get(url__regex=r"/channels/\d+/" + date).mock(
            return_value=httpx.Response(200, json={"programs": []})
        )
        result = await yousee_now_playing("999")
        assert result[0].get("info") is not None


class TestYouseePrimeTime:
    async def test_finds_primetime_programs(self, mock_api):
        program = {
            "title": "Aftenshowet",
            "channelName": "DR1",
            "channelId": "1",
            "begin": "2026-03-18T18:00:00+00:00",
            "end": "2026-03-18T19:30:00+00:00",
        }
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_EMPTY_CHANNELS_RESPONSE)
        )
        mock_api.get(url__regex=r"/channels/\d+/2026-03-18").mock(
            return_value=httpx.Response(200, json={"programs": [program]})
        )
        result = await yousee_prime_time("2026-03-18")
        assert any(r.get("title") == "Aftenshowet" for r in result)

    async def test_no_primetime_programs(self, mock_api):
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_EMPTY_CHANNELS_RESPONSE)
        )
        mock_api.get(url__regex=r"/channels/\d+/2026-03-18").mock(
            return_value=httpx.Response(200, json={"programs": []})
        )
        result = await yousee_prime_time("2026-03-18")
        assert result[0].get("info") is not None


class TestYouseeGenre:
    async def test_finds_by_genre(self, mock_api):
        program = {
            "title": "Fodbold",
            "channelName": "TV 2 Sport",
            "channelId": "7",
            "begin": "2026-03-18T20:00:00+01:00",
            "end": "2026-03-18T22:00:00+01:00",
            "genreName": "Sport",
            "subGenreName": "Fodbold",
        }
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_EMPTY_CHANNELS_RESPONSE)
        )
        mock_api.get(url__regex=r"/channels/\d+/2026-03-18").mock(
            return_value=httpx.Response(200, json={"programs": [program]})
        )
        result = await yousee_genre("Sport", "2026-03-18")
        assert any(r.get("title") == "Fodbold" for r in result)

    async def test_no_genre_results(self, mock_api):
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_EMPTY_CHANNELS_RESPONSE)
        )
        mock_api.get(url__regex=r"/channels/\d+/2026-03-18").mock(
            return_value=httpx.Response(200, json={"programs": []})
        )
        result = await yousee_genre("Opera", "2026-03-18")
        assert result[0].get("info") is not None


class TestYouseeMovies:
    async def test_finds_movies(self, mock_api):
        now = datetime.now(timezone.utc)
        movie = {
            "title": "The Matrix",
            "channelName": "TV 2",
            "channelId": "2",
            "begin": (now + timedelta(hours=1)).isoformat(),
            "end": (now + timedelta(hours=3)).isoformat(),
            "genreName": "Film",
        }
        non_movie = {
            "title": "Nyheder",
            "channelName": "DR1",
            "channelId": "1",
            "begin": (now + timedelta(hours=1)).isoformat(),
            "end": (now + timedelta(hours=2)).isoformat(),
            "genreName": "Nyheder",
        }
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_EMPTY_CHANNELS_RESPONSE)
        )
        mock_api.get(url__regex=r"/channels/\d+/\d{4}-\d{2}-\d{2}").mock(
            return_value=httpx.Response(200, json={"programs": [movie, non_movie]})
        )
        result = await yousee_movies()
        assert all(r.get("genre", "").lower() == "film" for r in result)
        assert any(r["title"] == "The Matrix" for r in result)

    async def test_excludes_past_movies(self, mock_api):
        now = datetime.now(timezone.utc)
        past_movie = {
            "title": "Old Movie",
            "channelId": "1",
            "begin": (now - timedelta(hours=4)).isoformat(),
            "end": (now - timedelta(hours=2)).isoformat(),
            "genreName": "Film",
        }
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_EMPTY_CHANNELS_RESPONSE)
        )
        mock_api.get(url__regex=r"/channels/\d+/\d{4}-\d{2}-\d{2}").mock(
            return_value=httpx.Response(200, json={"programs": [past_movie]})
        )
        result = await yousee_movies()
        assert result[0].get("info") is not None

    async def test_no_movies_found(self, mock_api):
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_EMPTY_CHANNELS_RESPONSE)
        )
        mock_api.get(url__regex=r"/channels/\d+/\d{4}-\d{2}-\d{2}").mock(
            return_value=httpx.Response(200, json={"programs": []})
        )
        result = await yousee_movies()
        assert result[0].get("info") is not None


class TestYouseeTimeslot:
    async def test_finds_programs_at_time(self, mock_api):
        program = {
            "title": "Aftenshowet",
            "channelName": "DR1",
            "channelId": "1",
            "begin": "2026-03-18T19:00:00+01:00",
            "end": "2026-03-18T20:30:00+01:00",
        }
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_EMPTY_CHANNELS_RESPONSE)
        )
        mock_api.get(url__regex=r"/channels/\d+/2026-03-18").mock(
            return_value=httpx.Response(200, json={"programs": [program]})
        )
        result = await yousee_timeslot("20:00", "2026-03-18")
        assert any(r["title"] == "Aftenshowet" for r in result)

    async def test_no_programs_at_time(self, mock_api):
        program = {
            "title": "Morgen-TV",
            "channelId": "1",
            "begin": "2026-03-18T06:00:00+01:00",
            "end": "2026-03-18T09:00:00+01:00",
        }
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_EMPTY_CHANNELS_RESPONSE)
        )
        mock_api.get(url__regex=r"/channels/\d+/2026-03-18").mock(
            return_value=httpx.Response(200, json={"programs": [program]})
        )
        result = await yousee_timeslot("22:00", "2026-03-18")
        assert result[0].get("info") is not None


class TestYouseeProgramDetails:
    async def test_finds_program_by_title(self, mock_api, sample_program):
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_EMPTY_CHANNELS_RESPONSE)
        )
        mock_api.get(url__regex=r"/channels/\d+/\d{4}-\d{2}-\d{2}").mock(
            return_value=httpx.Response(200, json={"programs": [sample_program]})
        )
        result = await yousee_program_details("Vild med dans")
        assert result["title"] == "Vild med dans"
        # Full description — not truncated to 300 chars
        assert len(result.get("description", "")) > 300
        # All cast members — not truncated to 5
        assert len(result.get("cast", [])) == 6

    async def test_finds_with_channel_id(self, mock_api, sample_program):
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_EMPTY_CHANNELS_RESPONSE)
        )
        mock_api.get(url__regex=r"/channels/2/\d{4}-\d{2}-\d{2}").mock(
            return_value=httpx.Response(200, json={"programs": [sample_program]})
        )
        result = await yousee_program_details("Vild med dans", channel_id="2")
        assert result["title"] == "Vild med dans"

    async def test_not_found(self, mock_api):
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_EMPTY_CHANNELS_RESPONSE)
        )
        mock_api.get(url__regex=r"/channels/\d+/\d{4}-\d{2}-\d{2}").mock(
            return_value=httpx.Response(200, json={"programs": []})
        )
        result = await yousee_program_details("Nonexistent")
        assert result.get("info") is not None


class TestYouseeUpcoming:
    async def test_returns_upcoming_programs(self, mock_api):
        now = datetime.now(timezone.utc)
        programs = [
            {
                "title": f"Show {i}",
                "channelId": "1",
                "begin": (now + timedelta(hours=i)).isoformat(),
                "end": (now + timedelta(hours=i + 1)).isoformat(),
            }
            for i in range(1, 7)
        ]
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_EMPTY_CHANNELS_RESPONSE)
        )
        date = now.strftime("%Y-%m-%d")
        mock_api.get(f"/channels/1/{date}").mock(
            return_value=httpx.Response(200, json={"programs": programs})
        )
        result = await yousee_upcoming("1")
        assert len(result) == 5  # default limit
        assert result[0]["title"] == "Show 1"

    async def test_respects_limit(self, mock_api):
        now = datetime.now(timezone.utc)
        programs = [
            {
                "title": f"Show {i}",
                "channelId": "1",
                "begin": (now + timedelta(hours=i)).isoformat(),
                "end": (now + timedelta(hours=i + 1)).isoformat(),
            }
            for i in range(1, 7)
        ]
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_EMPTY_CHANNELS_RESPONSE)
        )
        date = now.strftime("%Y-%m-%d")
        mock_api.get(f"/channels/1/{date}").mock(
            return_value=httpx.Response(200, json={"programs": programs})
        )
        result = await yousee_upcoming("1", limit=2)
        assert len(result) == 2

    async def test_excludes_finished_programs(self, mock_api):
        now = datetime.now(timezone.utc)
        past = {
            "title": "Old show",
            "channelId": "1",
            "begin": (now - timedelta(hours=3)).isoformat(),
            "end": (now - timedelta(hours=1)).isoformat(),
        }
        future = {
            "title": "Next show",
            "channelId": "1",
            "begin": (now + timedelta(hours=1)).isoformat(),
            "end": (now + timedelta(hours=2)).isoformat(),
        }
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_EMPTY_CHANNELS_RESPONSE)
        )
        date = now.strftime("%Y-%m-%d")
        mock_api.get(f"/channels/1/{date}").mock(
            return_value=httpx.Response(200, json={"programs": [past, future]})
        )
        result = await yousee_upcoming("1")
        assert len(result) == 1
        assert result[0]["title"] == "Next show"

    async def test_no_upcoming(self, mock_api):
        now = datetime.now(timezone.utc)
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json=_EMPTY_CHANNELS_RESPONSE)
        )
        date = now.strftime("%Y-%m-%d")
        mock_api.get(f"/channels/1/{date}").mock(
            return_value=httpx.Response(200, json={"programs": []})
        )
        result = await yousee_upcoming("1")
        assert result[0].get("info") is not None


class TestStaleWhileRevalidate:
    async def test_returns_stale_programs_and_revalidates(self, mock_api):
        """Expired cache returnerer stale data og opdaterer i baggrunden."""
        # Præfyld cache med gammel entry
        old_prog = [{"title": "Old", "channelId": "1"}]
        _programs_cache[("1", "2026-03-18")] = _CacheEntry(
            data=old_prog, ts=time.monotonic() - PROGRAMS_TTL - 10
        )
        new_prog = [{"title": "New", "channelId": "1"}]
        mock_api.get("/channels/1/2026-03-18").mock(
            return_value=httpx.Response(200, json={"programs": new_prog})
        )

        # Skal returnere stale data med det samme
        result = await _get_programs_cached("1", "2026-03-18")
        assert result[0]["title"] == "Old"

        # Vent på baggrunds-task
        await asyncio.sleep(0.1)

        # Nu skal cachen være opdateret
        result2 = await _get_programs_cached("1", "2026-03-18")
        assert result2[0]["title"] == "New"

    async def test_returns_stale_channels_and_revalidates(self, mock_api):
        """Expired kanalliste returnerer stale data og opdaterer i baggrunden."""
        old_channels = [{"id": 1, "name": "Old DR1"}]
        _server._channels_cache = _CacheEntry(
            data=old_channels, ts=time.monotonic() - CHANNELS_TTL - 10
        )
        new_channels = [{"id": 1, "name": "New DR1"}]
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json={"channels": new_channels})
        )

        result = await _get_channels_cached()
        assert result[0]["name"] == "Old DR1"

        await asyncio.sleep(0.1)

        result2 = await _get_channels_cached()
        assert result2[0]["name"] == "New DR1"

    async def test_revalidation_error_keeps_stale_data(self, mock_api):
        """Fejl under revalidering beholder stale data."""
        old_prog = [{"title": "Stale", "channelId": "1"}]
        _programs_cache[("1", "2026-03-18")] = _CacheEntry(
            data=old_prog, ts=time.monotonic() - PROGRAMS_TTL - 10
        )
        mock_api.get("/channels/1/2026-03-18").mock(
            return_value=httpx.Response(500)
        )

        result = await _get_programs_cached("1", "2026-03-18")
        assert result[0]["title"] == "Stale"

        await asyncio.sleep(0.1)

        # Stadig stale data efter fejl
        entry = _programs_cache[("1", "2026-03-18")]
        assert entry.data[0]["title"] == "Stale"


class TestCleanupOldDates:
    def test_removes_old_dates(self):
        """Fjerner cache-entries for datoer ældre end i dag."""
        today = datetime.now().strftime("%Y-%m-%d")
        _programs_cache[("1", "2020-01-01")] = _CacheEntry(data=[])
        _programs_cache[("2", "2020-06-15")] = _CacheEntry(data=[])
        _programs_cache[("1", today)] = _CacheEntry(data=[{"title": "Today"}])

        removed = _cleanup_old_dates()
        assert removed == 2
        assert ("1", today) in _programs_cache
        assert ("1", "2020-01-01") not in _programs_cache

    def test_no_old_dates(self):
        """Ingen gamle datoer at fjerne."""
        today = datetime.now().strftime("%Y-%m-%d")
        _programs_cache[("1", today)] = _CacheEntry(data=[])
        removed = _cleanup_old_dates()
        assert removed == 0


class TestWarmup:
    async def test_warmup_populates_cache(self, mock_api):
        """Warmup fylder cache med kanaler og programmer for populære kanaler."""
        channels = [{"id": cid, "long_name": f"Kanal {cid}", "name": f"K{cid}"} for cid in [1, 2, 3]]
        mock_api.get("/channels").mock(
            return_value=httpx.Response(200, json={"channels": channels})
        )
        today = datetime.now().strftime("%Y-%m-%d")
        mock_api.get(url__regex=r"/channels/\d+/" + today).mock(
            return_value=httpx.Response(200, json={"programs": [{"title": "Test", "channelId": "1"}]})
        )

        await _warmup()

        # Kanalliste skal være cachet
        assert _server._channels_cache is not None
        # Kanalnavne skal være cachet
        assert len(_channel_names) == 3
        assert _channel_names[1] == "Kanal 1"

    async def test_warmup_survives_api_error(self, mock_api):
        """Warmup fejler gracefully ved API-fejl."""
        mock_api.get("/channels").mock(
            return_value=httpx.Response(500)
        )
        # Skal ikke kaste exception
        await _warmup()
        assert _server._channels_cache is None
