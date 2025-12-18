"""
Web scraper module for collecting LaLiga match data from FBRef.

This module provides functionality to scrape match statistics, team data,
and historical results from the FBRef website.
"""

import logging
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config import get_settings

logger = logging.getLogger(__name__)


class FBRefScraper:
    """
    Scraper for FBRef football statistics website.

    This class handles web scraping of LaLiga match data with proper
    rate limiting, error handling, and retry logic.

    Attributes:
        base_url: Base URL for FBRef
        delay: Delay between requests in seconds
        session: Requests session with retry logic
    """

    def __init__(self, base_url: Optional[str] = None, delay: Optional[int] = None):
        """
        Initialize the FBRef scraper.

        Args:
            base_url: Base URL for FBRef (default from settings)
            delay: Delay between requests in seconds (default from settings)
        """
        settings = get_settings()
        self.base_url = base_url or settings.FBREF_BASE_URL
        self.delay = delay if delay is not None else settings.SCRAPING_DELAY
        self.session = self._create_session()
        self.last_request_time = 0.0

        logger.info(
            f"Initialized FBRefScraper with base_url={self.base_url}, delay={self.delay}s"
        )

    def _create_session(self) -> requests.Session:
        """
        Create a requests session with retry logic.

        Returns:
            Configured requests session
        """
        settings = get_settings()
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=settings.MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set headers
        session.headers.update(
            {
                "User-Agent": settings.get_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )

        return session

    def _rate_limit(self) -> None:
        """
        Implement rate limiting between requests.

        Ensures that requests are spaced out by the configured delay.
        """
        if self.delay > 0:
            current_time = time.time()
            time_since_last_request = current_time - self.last_request_time

            if time_since_last_request < self.delay:
                sleep_time = self.delay - time_since_last_request
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)

            self.last_request_time = time.time()

    def _fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """
        Fetch and parse a web page.

        Args:
            url: URL to fetch

        Returns:
            BeautifulSoup object or None if request failed

        Raises:
            requests.RequestException: If request fails after retries
        """
        settings = get_settings()
        self._rate_limit()

        try:
            logger.info(f"Fetching URL: {url}")
            response = self.session.get(url, timeout=settings.REQUEST_TIMEOUT)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "lxml")
            logger.debug(f"Successfully fetched and parsed {url}")
            return soup

        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            raise

    def get_season_matches(self, season: str) -> List[Dict[str, Any]]:
        """
        Get all matches for a specific LaLiga season.

        Args:
            season: Season string (e.g., "2023-2024")

        Returns:
            List of match dictionaries containing match data

        Example:
            >>> scraper = FBRefScraper()
            >>> matches = scraper.get_season_matches("2023-2024")
            >>> print(len(matches))
            380
        """
        logger.info(f"Fetching matches for season {season}")

        # Construct URL for LaLiga season
        # Format: /en/comps/12/2023-2024/2023-2024-La-Liga-Stats
        season_url = urljoin(
            self.base_url,
            f"comps/12/{season}/{season}-La-Liga-Stats",
        )

        soup = self._fetch_page(season_url)
        if not soup:
            logger.warning(f"Failed to fetch season page for {season}")
            return []

        matches = self._parse_season_matches(soup, season)
        logger.info(f"Found {len(matches)} matches for season {season}")
        return matches

    def _parse_season_matches(
        self, soup: BeautifulSoup, season: str
    ) -> List[Dict[str, Any]]:
        """
        Parse match data from season page.

        Args:
            soup: BeautifulSoup object of season page
            season: Season string

        Returns:
            List of match dictionaries
        """
        matches = []

        # Find the scores and fixtures table
        # This is a simplified version - you'll need to adapt to actual HTML structure
        table = soup.find("table", {"id": "sched_2023-2024_12_1"})
        if not table or not isinstance(table, Tag):
            logger.warning("Could not find matches table")
            return matches

        tbody = table.find("tbody")
        if not tbody or not isinstance(tbody, Tag):
            return matches

        rows = tbody.find_all("tr")

        for row in rows:
            try:
                match_data = self._parse_match_row(row, season)
                if match_data:
                    matches.append(match_data)
            except Exception as e:
                logger.error(f"Error parsing match row: {e}")
                continue

        return matches

    def _parse_match_row(self, row: Tag, season: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single match row from the table.

        Args:
            row: BeautifulSoup Tag representing a table row
            season: Season string

        Returns:
            Dictionary with match data or None if parsing fails
        """
        # Skip header rows
        if row.get("class") and "thead" in row.get("class", []):
            return None

        cells = row.find_all("td")
        if len(cells) < 8:
            return None

        try:
            # Extract basic match information
            # Note: You'll need to adjust these based on actual HTML structure
            match_data = {
                "season": season,
                "date": self._safe_extract_text(cells[1]),
                "home_team": self._safe_extract_text(cells[3]),
                "away_team": self._safe_extract_text(cells[5]),
                "score": self._safe_extract_text(cells[4]),
            }

            # Parse score
            if match_data["score"] and "–" in match_data["score"]:
                home_score, away_score = match_data["score"].split("–")
                match_data["home_score"] = int(home_score.strip())
                match_data["away_score"] = int(away_score.strip())

                # Determine result
                if match_data["home_score"] > match_data["away_score"]:
                    match_data["result"] = "victoria_local"
                elif match_data["home_score"] < match_data["away_score"]:
                    match_data["result"] = "victoria_visitante"
                else:
                    match_data["result"] = "empate"
            else:
                match_data["home_score"] = None
                match_data["away_score"] = None
                match_data["result"] = None

            return match_data

        except (ValueError, IndexError, AttributeError) as e:
            logger.debug(f"Could not parse match row: {e}")
            return None

    def _safe_extract_text(self, element: Optional[Tag]) -> Optional[str]:
        """
        Safely extract text from a BeautifulSoup element.

        Args:
            element: BeautifulSoup Tag or None

        Returns:
            Extracted text or None
        """
        if element is None:
            return None
        text = element.get_text(strip=True)
        return text if text else None

    def get_team_stats(self, team_url: str) -> Dict[str, Any]:
        """
        Get detailed statistics for a specific team.

        Args:
            team_url: Relative URL for the team page

        Returns:
            Dictionary containing team statistics

        Example:
            >>> scraper = FBRefScraper()
            >>> stats = scraper.get_team_stats("/en/squads/...")
            >>> print(stats['team_name'])
        """
        full_url = urljoin(self.base_url, team_url)
        soup = self._fetch_page(full_url)

        if not soup:
            logger.warning(f"Failed to fetch team page: {team_url}")
            return {}

        # Parse team statistics
        # This is a placeholder - implement based on actual HTML structure
        team_stats = {
            "team_name": self._safe_extract_text(soup.find("h1")),
            # Add more stats as needed
        }

        return team_stats

    def close(self) -> None:
        """Close the requests session."""
        self.session.close()
        logger.info("Scraper session closed")

    def __enter__(self) -> "FBRefScraper":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()


def main() -> None:
    """
    Main function for command-line usage.

    Example:
        python -m src.laliga_predictor.data.scraper
    """
    import argparse

    parser = argparse.ArgumentParser(description="Scrape LaLiga match data from FBRef")
    parser.add_argument(
        "--season",
        type=str,
        default="2023-2024",
        help="Season to scrape (e.g., 2023-2024)",
    )
    args = parser.parse_args()

    logger.info(f"Starting scraper for season {args.season}")

    with FBRefScraper() as scraper:
        matches = scraper.get_season_matches(args.season)
        logger.info(f"Successfully scraped {len(matches)} matches")

        # Print sample data
        if matches:
            logger.info("Sample match data:")
            logger.info(matches[0])


if __name__ == "__main__":
    main()
