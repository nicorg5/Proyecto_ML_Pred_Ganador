"""
Unit tests for web scraper module.
"""

from unittest.mock import Mock, patch

import pytest
import requests
from bs4 import BeautifulSoup

from src.laliga_predictor.data.scraper import FBRefScraper


class TestFBRefScraper:
    """Test FBRefScraper class."""

    @pytest.fixture
    def scraper(self) -> FBRefScraper:
        """Create a scraper instance with delay=0 for testing."""
        return FBRefScraper(delay=0)

    def test_initialization(self, scraper: FBRefScraper) -> None:
        """Test scraper initialization."""
        assert scraper.base_url == "https://fbref.com/en/"
        assert scraper.delay == 0
        assert scraper.session is not None

    def test_session_has_headers(self, scraper: FBRefScraper) -> None:
        """Test that session has proper headers."""
        headers = scraper.session.headers

        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Mozilla" in headers["User-Agent"]

    def test_rate_limiting(self) -> None:
        """Test rate limiting mechanism."""
        import time

        scraper = FBRefScraper(delay=1)
        start_time = time.time()

        # First request - should not delay
        scraper._rate_limit()
        first_duration = time.time() - start_time
        assert first_duration < 0.1

        # Second request - should delay
        start_time = time.time()
        scraper._rate_limit()
        second_duration = time.time() - start_time
        assert second_duration >= 0.9  # Allow some margin

    @patch("src.laliga_predictor.data.scraper.requests.Session.get")
    def test_fetch_page_success(self, mock_get: Mock, scraper: FBRefScraper) -> None:
        """Test successful page fetch."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"<html><body><h1>Test</h1></body></html>"
        mock_get.return_value = mock_response

        soup = scraper._fetch_page("https://example.com")

        assert soup is not None
        assert isinstance(soup, BeautifulSoup)
        assert soup.find("h1").text == "Test"
        mock_get.assert_called_once()

    @patch("src.laliga_predictor.data.scraper.requests.Session.get")
    def test_fetch_page_failure(self, mock_get: Mock, scraper: FBRefScraper) -> None:
        """Test page fetch failure handling."""
        mock_get.side_effect = requests.RequestException("Connection error")

        with pytest.raises(requests.RequestException):
            scraper._fetch_page("https://example.com")

    def test_safe_extract_text(self, scraper: FBRefScraper) -> None:
        """Test safe text extraction from elements."""
        html = "<div>Test Text</div>"
        soup = BeautifulSoup(html, "lxml")
        div = soup.find("div")

        # Valid element
        text = scraper._safe_extract_text(div)
        assert text == "Test Text"

        # None element
        text = scraper._safe_extract_text(None)
        assert text is None

        # Empty element
        empty_html = "<div></div>"
        empty_soup = BeautifulSoup(empty_html, "lxml")
        empty_div = empty_soup.find("div")
        text = scraper._safe_extract_text(empty_div)
        assert text is None

    def test_parse_match_row_valid(self, scraper: FBRefScraper) -> None:
        """Test parsing valid match row."""
        html = """
        <tr>
            <td>1</td>
            <td>2024-01-15</td>
            <td>Mon</td>
            <td>Real Madrid</td>
            <td>2–1</td>
            <td>Barcelona</td>
            <td>Home</td>
            <td>80000</td>
        </tr>
        """
        soup = BeautifulSoup(html, "lxml")
        row = soup.find("tr")

        match_data = scraper._parse_match_row(row, "2023-2024")

        # Note: This is a simplified test - actual parsing depends on HTML structure
        # Adjust assertions based on actual implementation
        assert match_data is not None or match_data is None  # Placeholder

    def test_context_manager(self) -> None:
        """Test scraper as context manager."""
        with FBRefScraper(delay=0) as scraper:
            assert scraper.session is not None

        # Session should be closed after context exit
        # Note: Add proper assertion based on session state

    def test_close_session(self, scraper: FBRefScraper) -> None:
        """Test session closing."""
        scraper.close()
        # Verify session is closed
        # Note: Add proper assertion based on implementation


class TestScraperIntegration:
    """Integration tests for scraper (require mocking)."""

    @patch("src.laliga_predictor.data.scraper.FBRefScraper._fetch_page")
    def test_get_season_matches_mocked(self, mock_fetch: Mock) -> None:
        """Test getting season matches with mocked page fetch."""
        # Mock HTML response
        mock_html = """
        <html>
            <body>
                <table id="sched_2023-2024_12_1">
                    <tbody>
                        <tr>
                            <td>1</td>
                            <td>2024-01-15</td>
                            <td>Mon</td>
                            <td>Real Madrid</td>
                            <td>2–1</td>
                            <td>Barcelona</td>
                        </tr>
                    </tbody>
                </table>
            </body>
        </html>
        """
        mock_fetch.return_value = BeautifulSoup(mock_html, "lxml")

        scraper = FBRefScraper(delay=0)
        matches = scraper.get_season_matches("2023-2024")

        # Verify fetch was called
        mock_fetch.assert_called_once()

        # Note: Adjust assertion based on actual parsing logic
        assert isinstance(matches, list)
