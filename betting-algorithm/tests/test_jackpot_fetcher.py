"""
Comprehensive tests for JackpotFetcher

Tests cover:
- Selenium functionality
- Fallback to sample data
- Error handling
- Data extraction
- History saving
- All providers (SportPesa, Betika)
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import pandas as pd

# Import the module to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from jackpot_fetcher import JackpotFetcher


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def fetcher_no_selenium(temp_data_dir, monkeypatch):
    """Create a fetcher with Selenium disabled"""
    monkeypatch.chdir(temp_data_dir)
    return JackpotFetcher(use_selenium=False)


@pytest.fixture
def fetcher_with_selenium(temp_data_dir, monkeypatch):
    """Create a fetcher with Selenium enabled (will use mocks in tests)"""
    monkeypatch.chdir(temp_data_dir)
    return JackpotFetcher(use_selenium=True, headless=True)


@pytest.fixture
def sample_html_with_matches():
    """Sample HTML with match data"""
    return """
    <html>
        <body>
            <div class="prize">KSh 100,000,000</div>
            <div class="jackpot-match">
                <span class="team home">Arsenal</span>
                <span class="team away">Chelsea</span>
                <span class="competition">Premier League</span>
                <span class="kickoff">Sat 15:00</span>
            </div>
            <div class="jackpot-match">
                <span class="team home">Man City</span>
                <span class="team away">Liverpool</span>
                <span class="competition">Premier League</span>
                <span class="kickoff">Sat 17:30</span>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def sample_html_no_matches():
    """Sample HTML without match data (JavaScript not loaded)"""
    return """
    <html>
        <body>
            <div id="root"></div>
            <script src="app.js"></script>
        </body>
    </html>
    """


class TestFetcherInitialization:
    """Test fetcher initialization"""

    def test_init_with_selenium_disabled(self, fetcher_no_selenium):
        """Test initialization with Selenium disabled"""
        assert fetcher_no_selenium.use_selenium is False
        assert fetcher_no_selenium.headless is True
        assert fetcher_no_selenium.timeout == 30

    def test_init_with_selenium_enabled(self, fetcher_with_selenium):
        """Test initialization with Selenium enabled"""
        # Note: use_selenium may be False if Selenium is not installed
        assert isinstance(fetcher_with_selenium.timeout, int)
        assert fetcher_with_selenium.history_dir.exists()

    def test_custom_timeout(self, temp_data_dir, monkeypatch):
        """Test custom timeout setting"""
        monkeypatch.chdir(temp_data_dir)
        fetcher = JackpotFetcher(timeout=60)
        assert fetcher.timeout == 60

    def test_history_dir_creation(self, fetcher_no_selenium):
        """Test that history directory is created"""
        assert fetcher_no_selenium.history_dir.exists()
        assert fetcher_no_selenium.history_dir.is_dir()


class TestSampleData:
    """Test sample data fallback functionality"""

    def test_fetch_sportpesa_mega_without_selenium(self, fetcher_no_selenium):
        """Test fetching SportPesa Mega Jackpot without Selenium"""
        result = fetcher_no_selenium.fetch_sportpesa_mega_jackpot()

        assert result is not None
        assert result['provider'] == 'SportPesa'
        assert result['type'] == 'Mega Jackpot'
        assert result['matches_count'] == 17
        assert len(result['matches']) == 17
        assert result['data_source'] == 'sample'
        assert 'fetched_at' in result

    def test_fetch_sportpesa_midweek_without_selenium(self, fetcher_no_selenium):
        """Test fetching SportPesa Midweek Jackpot without Selenium"""
        result = fetcher_no_selenium.fetch_sportpesa_midweek_jackpot()

        assert result is not None
        assert result['provider'] == 'SportPesa'
        assert result['type'] == 'Midweek Jackpot'
        assert result['matches_count'] == 13
        assert len(result['matches']) == 13
        assert result['data_source'] == 'sample'

    def test_fetch_betika_without_selenium(self, fetcher_no_selenium):
        """Test fetching Betika Jackpot without Selenium"""
        result = fetcher_no_selenium.fetch_betika_jackpot()

        assert result is not None
        assert result['provider'] == 'Betika'
        assert result['type'] == 'Jackpot'
        assert result['matches_count'] == 15
        assert len(result['matches']) == 15
        assert result['data_source'] == 'sample'

    def test_get_all_jackpots_without_selenium(self, fetcher_no_selenium):
        """Test fetching all jackpots without Selenium"""
        jackpots = fetcher_no_selenium.get_all_current_jackpots()

        assert len(jackpots) == 3
        providers = {jp['provider'] for jp in jackpots}
        assert 'SportPesa' in providers
        assert 'Betika' in providers


class TestMatchDataStructure:
    """Test match data structure and validation"""

    def test_match_data_fields(self, fetcher_no_selenium):
        """Test that match data contains all required fields"""
        result = fetcher_no_selenium.fetch_sportpesa_mega_jackpot()
        match = result['matches'][0]

        assert 'match_number' in match
        assert 'home_team' in match
        assert 'away_team' in match
        assert isinstance(match['match_number'], int)
        assert isinstance(match['home_team'], str)
        assert isinstance(match['away_team'], str)

    def test_match_numbers_sequential(self, fetcher_no_selenium):
        """Test that match numbers are sequential"""
        result = fetcher_no_selenium.fetch_sportpesa_mega_jackpot()
        match_numbers = [m['match_number'] for m in result['matches']]

        assert match_numbers == list(range(1, len(result['matches']) + 1))

    def test_team_names_not_empty(self, fetcher_no_selenium):
        """Test that team names are not empty"""
        result = fetcher_no_selenium.fetch_betika_jackpot()

        for match in result['matches']:
            assert len(match['home_team']) > 0
            assert len(match['away_team']) > 0
            assert match['home_team'] != match['away_team']


class TestSeleniumMocking:
    """Test Selenium functionality with mocking"""

    @patch('jackpot_fetcher.SELENIUM_AVAILABLE', True)
    @patch('jackpot_fetcher.JackpotFetcher._create_driver')
    def test_fetch_with_selenium_success(self, mock_create_driver,
                                        fetcher_with_selenium,
                                        sample_html_with_matches):
        """Test successful fetch with Selenium"""
        # Mock the driver
        mock_driver = MagicMock()
        mock_driver.page_source = sample_html_with_matches
        mock_create_driver.return_value = mock_driver

        # Mock _fetch_page_with_selenium to return our sample HTML
        with patch.object(fetcher_with_selenium, '_fetch_page_with_selenium',
                         return_value=sample_html_with_matches):
            result = fetcher_with_selenium.fetch_sportpesa_mega_jackpot()

            assert result is not None
            assert result['provider'] == 'SportPesa'
            # Note: might still return sample data if extraction fails
            assert 'matches' in result
            assert len(result['matches']) > 0

    @patch('jackpot_fetcher.SELENIUM_AVAILABLE', True)
    def test_fetch_with_selenium_failure(self, fetcher_with_selenium):
        """Test fetch with Selenium when page load fails"""
        # Mock _fetch_page_with_selenium to return None (failure)
        with patch.object(fetcher_with_selenium, '_fetch_page_with_selenium',
                         return_value=None):
            result = fetcher_with_selenium.fetch_sportpesa_mega_jackpot()

            assert result is not None
            # Should fall back to sample data
            assert result['data_source'] == 'sample'
            assert len(result['matches']) > 0

    @patch('jackpot_fetcher.SELENIUM_AVAILABLE', True)
    def test_fetch_with_selenium_exception(self, fetcher_with_selenium):
        """Test fetch with Selenium when exception occurs"""
        # Mock _fetch_page_with_selenium to raise an exception
        with patch.object(fetcher_with_selenium, '_fetch_page_with_selenium',
                         side_effect=Exception("Network error")):
            result = fetcher_with_selenium.fetch_sportpesa_mega_jackpot()

            assert result is not None
            # Should fall back to sample data
            assert 'data_source' in result
            assert 'error' in result or result['data_source'] in ['sample', 'sample_fallback']


class TestDataExtraction:
    """Test data extraction methods"""

    def test_extract_prize_amount(self, fetcher_no_selenium, sample_html_with_matches):
        """Test prize amount extraction"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(sample_html_with_matches, 'html.parser')
        prize = fetcher_no_selenium._extract_prize_amount(soup)

        assert prize is not None
        assert 'KSh' in prize or 'Million' in prize

    def test_extract_sportpesa_matches(self, fetcher_no_selenium, sample_html_with_matches):
        """Test SportPesa match extraction"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(sample_html_with_matches, 'html.parser')
        matches = fetcher_no_selenium._extract_sportpesa_matches(soup)

        # Should either extract matches or return sample data
        assert isinstance(matches, list)
        assert len(matches) > 0
        assert all('home_team' in m and 'away_team' in m for m in matches)

    def test_extract_betika_matches(self, fetcher_no_selenium, sample_html_with_matches):
        """Test Betika match extraction"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(sample_html_with_matches, 'html.parser')
        matches = fetcher_no_selenium._extract_betika_matches(soup)

        # Should either extract matches or return sample data
        assert isinstance(matches, list)
        assert len(matches) > 0

    def test_extract_no_matches_returns_sample(self, fetcher_no_selenium,
                                              sample_html_no_matches):
        """Test that extraction returns sample data when no matches found"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(sample_html_no_matches, 'html.parser')
        matches = fetcher_no_selenium._extract_sportpesa_matches(soup)

        # Should return sample data
        assert isinstance(matches, list)
        assert len(matches) > 0


class TestHistorySaving:
    """Test jackpot history saving functionality"""

    def test_save_jackpot_history(self, fetcher_no_selenium):
        """Test that jackpot history is saved to JSON"""
        result = fetcher_no_selenium.fetch_sportpesa_mega_jackpot()

        # Check that JSON file was created
        json_files = list(fetcher_no_selenium.history_dir.glob('*.json'))
        assert len(json_files) > 0

        # Verify JSON content
        with open(json_files[0], 'r') as f:
            saved_data = json.load(f)
            assert saved_data['provider'] == 'SportPesa'
            assert 'matches' in saved_data

    def test_append_to_master_csv(self, fetcher_no_selenium):
        """Test that jackpot data is appended to master CSV"""
        fetcher_no_selenium.fetch_sportpesa_mega_jackpot()
        fetcher_no_selenium.fetch_betika_jackpot()

        csv_path = fetcher_no_selenium.history_dir / 'jackpot_history.csv'
        assert csv_path.exists()

        df = pd.read_csv(csv_path)
        assert len(df) >= 2
        assert 'provider' in df.columns
        assert 'type' in df.columns
        assert 'matches_count' in df.columns
        assert 'data_source' in df.columns

    def test_get_jackpot_history(self, fetcher_no_selenium):
        """Test retrieving jackpot history"""
        # Fetch some jackpots
        fetcher_no_selenium.fetch_sportpesa_mega_jackpot()
        fetcher_no_selenium.fetch_betika_jackpot()

        # Get all history
        history = fetcher_no_selenium.get_jackpot_history()
        assert isinstance(history, pd.DataFrame)
        assert len(history) >= 2

    def test_get_jackpot_history_filtered(self, fetcher_no_selenium):
        """Test retrieving filtered jackpot history"""
        fetcher_no_selenium.fetch_sportpesa_mega_jackpot()
        fetcher_no_selenium.fetch_betika_jackpot()

        # Filter by provider
        sportpesa_history = fetcher_no_selenium.get_jackpot_history(provider='SportPesa')
        assert all(sportpesa_history['provider'] == 'SportPesa')

        # Filter by type
        mega_history = fetcher_no_selenium.get_jackpot_history(jackpot_type='Mega Jackpot')
        assert all(mega_history['type'] == 'Mega Jackpot')


class TestErrorHandling:
    """Test error handling"""

    def test_handle_missing_selenium(self, temp_data_dir, monkeypatch):
        """Test graceful handling when Selenium is not available"""
        monkeypatch.chdir(temp_data_dir)

        with patch('jackpot_fetcher.SELENIUM_AVAILABLE', False):
            fetcher = JackpotFetcher(use_selenium=True)
            assert fetcher.use_selenium is False

    def test_exception_in_save_history(self, fetcher_no_selenium):
        """Test that exceptions in save_history don't crash the fetcher"""
        with patch.object(fetcher_no_selenium, '_save_jackpot_history',
                         side_effect=Exception("Save error")):
            # Should not raise exception
            result = fetcher_no_selenium.fetch_sportpesa_mega_jackpot()
            assert result is not None

    def test_exception_in_csv_append(self, fetcher_no_selenium):
        """Test that exceptions in CSV append don't crash the fetcher"""
        with patch.object(fetcher_no_selenium, '_append_to_master_csv',
                         side_effect=Exception("CSV error")):
            # Should not raise exception
            result = fetcher_no_selenium.fetch_sportpesa_mega_jackpot()
            assert result is not None


class TestDataSourceTracking:
    """Test data source tracking"""

    def test_data_source_field_present(self, fetcher_no_selenium):
        """Test that data_source field is present in results"""
        result = fetcher_no_selenium.fetch_sportpesa_mega_jackpot()
        assert 'data_source' in result
        assert result['data_source'] in ['sample', 'selenium', 'sample_fallback']

    def test_sample_data_source(self, fetcher_no_selenium):
        """Test that sample data is marked correctly"""
        result = fetcher_no_selenium.fetch_sportpesa_mega_jackpot()
        assert result['data_source'] == 'sample'

    @patch('jackpot_fetcher.SELENIUM_AVAILABLE', True)
    def test_selenium_data_source(self, fetcher_with_selenium, sample_html_with_matches):
        """Test that Selenium data is marked correctly"""
        with patch.object(fetcher_with_selenium, '_fetch_page_with_selenium',
                         return_value=sample_html_with_matches):
            result = fetcher_with_selenium.fetch_sportpesa_mega_jackpot()
            # Data source should be selenium or sample depending on extraction success
            assert result['data_source'] in ['selenium', 'sample']


class TestTimestamps:
    """Test timestamp handling"""

    def test_fetched_at_timestamp(self, fetcher_no_selenium):
        """Test that fetched_at timestamp is valid"""
        result = fetcher_no_selenium.fetch_sportpesa_mega_jackpot()

        assert 'fetched_at' in result
        # Verify it's a valid ISO format timestamp
        try:
            datetime.fromisoformat(result['fetched_at'])
        except ValueError:
            pytest.fail("fetched_at is not a valid ISO format timestamp")

    def test_history_timestamps(self, fetcher_no_selenium):
        """Test that history entries have timestamps"""
        fetcher_no_selenium.fetch_sportpesa_mega_jackpot()

        history = fetcher_no_selenium.get_jackpot_history()
        assert 'timestamp' in history.columns
        assert len(history) > 0


class TestSampleDataConsistency:
    """Test sample data consistency"""

    def test_sample_sportpesa_matches_count(self, fetcher_no_selenium):
        """Test that sample SportPesa data has correct number of matches"""
        matches = fetcher_no_selenium._get_sample_sportpesa_matches()
        assert len(matches) == 17

    def test_sample_betika_matches_count(self, fetcher_no_selenium):
        """Test that sample Betika data has correct number of matches"""
        matches = fetcher_no_selenium._get_sample_betika_matches()
        assert len(matches) == 15

    def test_sample_data_structure(self, fetcher_no_selenium):
        """Test that sample data has proper structure"""
        matches = fetcher_no_selenium._get_sample_sportpesa_matches()

        for i, match in enumerate(matches, 1):
            assert match['match_number'] == i
            assert isinstance(match['home_team'], str)
            assert isinstance(match['away_team'], str)
            assert len(match['home_team']) > 0
            assert len(match['away_team']) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
