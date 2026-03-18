import pytest


@pytest.fixture
def sample_program():
    """A full program dict as returned by the YouSee API."""
    return {
        "title": "Vild med dans",
        "channelName": "TV 2",
        "channelId": "2",
        "begin": "2026-03-18T19:00:00+01:00",
        "end": "2026-03-18T21:00:00+01:00",
        "description": "Danmarks største dansesatsning " * 20,
        "genreName": "Underholdning",
        "subGenreName": "Show",
        "ageRating": 0,
        "isSeries": True,
        "seriesName": "Vild med dans",
        "episodeId": "S22E05",
        "cast": ["person1", "person2", "person3", "person4", "person5", "person6"],
        "productionYear": 2026,
    }


@pytest.fixture
def sample_channel():
    """A channel dict as returned by the YouSee API."""
    return {
        "id": 2,
        "long_name": "TV 2",
        "name": "TV2",
        "logoSvg": "https://example.com/tv2.svg",
        "logoPng400": "https://example.com/tv2.png",
    }


@pytest.fixture
def sample_api_programs(sample_program):
    """API response wrapping programs in a dict."""
    return {"programs": [sample_program]}


@pytest.fixture
def sample_api_channels(sample_channel):
    """API response wrapping channels in a dict."""
    return {"channels": [sample_channel]}
