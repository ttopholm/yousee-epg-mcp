from datetime import datetime

from yousee_epg.server import _extract_list, _parse_time, _summarize_program


class TestExtractList:
    def test_list_input_returned_as_is(self):
        data = [1, 2, 3]
        assert _extract_list(data, "key") == [1, 2, 3]

    def test_dict_with_matching_key(self):
        data = {"programs": [{"title": "Test"}]}
        assert _extract_list(data, "programs") == [{"title": "Test"}]

    def test_dict_first_matching_key_wins(self):
        data = {"data": [1], "result": [2]}
        assert _extract_list(data, "data", "result") == [1]

    def test_dict_no_matching_key(self):
        data = {"other": [1, 2]}
        assert _extract_list(data, "programs") == []

    def test_dict_key_exists_but_not_list(self):
        data = {"programs": "not a list"}
        assert _extract_list(data, "programs") == []

    def test_empty_dict(self):
        assert _extract_list({}, "key") == []

    def test_empty_list(self):
        assert _extract_list([], "key") == []


class TestSummarizeProgram:
    def test_full_data(self, sample_program):
        result = _summarize_program(sample_program)
        assert result["title"] == "Vild med dans"
        assert result["channel"] == "TV 2"
        assert result["channel_id"] == "2"
        assert result["genre"] == "Underholdning"
        assert result["is_series"] is True
        assert result["series_name"] == "Vild med dans"
        assert result["year"] == 2026

    def test_description_truncated_at_300(self, sample_program):
        result = _summarize_program(sample_program)
        assert len(result["description"]) <= 300

    def test_cast_truncated_at_5(self, sample_program):
        result = _summarize_program(sample_program)
        assert len(result["cast"]) == 5

    def test_missing_fields_use_defaults(self):
        result = _summarize_program({})
        assert result["title"] == ""
        assert result["channel"] == ""
        assert result["description"] == ""
        assert result["age_rating"] == 0
        assert result["is_series"] is False
        assert result["cast"] == []

    def test_none_description(self):
        result = _summarize_program({"description": None})
        assert result["description"] == ""


class TestParseTime:
    def test_valid_iso(self):
        result = _parse_time("2026-03-18T19:00:00+01:00")
        assert isinstance(result, datetime)
        assert result.hour == 19

    def test_empty_string(self):
        assert _parse_time("") is None

    def test_none(self):
        assert _parse_time(None) is None

    def test_invalid_string(self):
        assert _parse_time("not-a-date") is None
