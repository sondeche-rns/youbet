"""Tests for JackpotSource interface — issue #3"""
import logging
import pytest
from pathlib import Path
from src.jackpot_source import SampleDataSource
from src.jackpot_analyzer import JackpotAnalyzer


@pytest.fixture
def sample_mega_payload():
    return SampleDataSource("sportpesa", "mega").fetch()


@pytest.fixture
def live_mega_payload():
    payload = SampleDataSource("sportpesa", "mega").fetch()
    payload["source_type"] = "live"
    return payload


class TestSampleDataSource:
    def test_fetch_returns_sample_source_type(self):
        source = SampleDataSource("sportpesa", "mega")
        payload = source.fetch()
        assert payload["source_type"] == "sample"

    def test_sportpesa_mega_has_17_matches_with_required_fields(self):
        payload = SampleDataSource("sportpesa", "mega").fetch()
        assert payload["matches_count"] == 17
        assert len(payload["matches"]) == 17
        for m in payload["matches"]:
            assert "home_team" in m and "away_team" in m and "match_number" in m

    def test_betika_sample_has_15_matches_and_sample_source_type(self):
        payload = SampleDataSource("betika", "jackpot").fetch()
        assert payload["source_type"] == "sample"
        assert payload["provider"] == "Betika"
        assert payload["matches_count"] == 15
        assert len(payload["matches"]) == 15


class TestJackpotAnalyzerSourceAwareness:
    def test_skips_persistence_for_sample_data(self, tmp_path, sample_mega_payload):
        analyzer = JackpotAnalyzer(predictions_dir=tmp_path)
        analyzer.analyze_jackpot(sample_mega_payload)
        assert list(tmp_path.iterdir()) == []

    def test_emits_warning_for_sample_data(self, tmp_path, sample_mega_payload, caplog):
        analyzer = JackpotAnalyzer(predictions_dir=tmp_path)
        with caplog.at_level(logging.WARNING, logger="src.jackpot_analyzer"):
            analyzer.analyze_jackpot(sample_mega_payload)
        assert any("sample" in rec.message.lower() for rec in caplog.records)

    def test_persists_predictions_for_live_data(self, tmp_path, live_mega_payload):
        analyzer = JackpotAnalyzer(predictions_dir=tmp_path)
        analyzer.analyze_jackpot(live_mega_payload)
        json_files = list(tmp_path.glob("*.json"))
        assert len(json_files) == 1
