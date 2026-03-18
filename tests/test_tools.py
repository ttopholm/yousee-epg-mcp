from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx

from yousee_epg.server import (
    _channel_names,
    yousee_channels,
    yousee_genre,
    yousee_now_playing,
    yousee_prime_time,
    yousee_programs,
    yousee_movies,
    yousee_search,
)

# Minimal channel list for _ensure_channel_names
_EMPTY_CHANNELS_RESPONSE = {"channels": [{"id": 1, "long_name": "DR1", "name": "DR1"}]}


@pytest.fixture(autouse=True)
def mock_api():
    """Activate respx mocking for all tests."""
    _channel_names.clear()
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
