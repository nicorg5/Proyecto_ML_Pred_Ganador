"""
API Football client for fetching LaLiga match data.

This module provides a clean interface to interact with the API-Football API.
Documentation: https://www.api-football.com/documentation-v3
"""

import logging
import time
from typing import Any

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..config import get_settings

logger = logging.getLogger(__name__)


class APIFootballClient:
    """
    Client for API-Football (api-sports.io).

    This client handles authentication, rate limiting, and error handling
    for all API requests.

    Attributes:
        base_url: Base URL for API endpoints
        headers: Authentication headers
        session: Requests session for connection pooling
    """

    def __init__(self, api_key: str | None = None):
        """
        Initialize the API Football client.

        Args:
            api_key: API key (default: from settings)
        """
        settings = get_settings()
        self.settings = settings

        self.api_key = api_key or settings.API_FOOTBALL_KEY
        self.base_url = settings.API_FOOTBALL_BASE_URL
        self.league_id = settings.LALIGA_LEAGUE_ID

        # Set up session
        self.session = requests.Session()
        self.session.headers.update(settings.get_api_headers())

        # Rate limiting
        self.last_request_time = 0.0
        self.min_request_interval = (
            7.0  # 7 seconds between requests (10 req/min limit = 6s min + 1s safety margin)
        )

        logger.info(f"Initialized API Football client for league {self.league_id}")

    def _rate_limit(self) -> None:
        """Implement rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    @retry(
        retry=retry_if_exception_type(requests.RequestException),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def _make_request(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Make a request to the API with retry logic.

        Args:
            endpoint: API endpoint (e.g., '/fixtures')
            params: Query parameters

        Returns:
            API response as dictionary

        Raises:
            requests.RequestException: If request fails after retries
        """
        self._rate_limit()

        url = f"{self.base_url}{endpoint}"
        logger.info(f"Requesting: {endpoint} with params: {params}")

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.settings.API_REQUEST_TIMEOUT,
            )
            response.raise_for_status()

            data = response.json()

            # Check API response structure
            if "errors" in data and data["errors"]:
                logger.error(f"API errors: {data['errors']}")
                raise ValueError(f"API returned errors: {data['errors']}")

            # Log rate limit info
            if "requests" in data.get("parameters", {}):
                remaining = (
                    data.get("parameters", {}).get("requests", {}).get("remaining", "unknown")
                )
                logger.info(f"API requests remaining today: {remaining}")

            return data

        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise

    def get_seasons(self) -> list[int]:
        """
        Get available seasons for LaLiga.

        Returns:
            List of season years (e.g., [2023, 2022, 2021])

        Example:
            >>> client = APIFootballClient()
            >>> seasons = client.get_seasons()
            >>> print(seasons[:5])
            [2024, 2023, 2022, 2021, 2020]
        """
        endpoint = "/leagues/seasons"
        response = self._make_request(endpoint)

        seasons = response.get("response", [])
        logger.info(f"Found {len(seasons)} available seasons")

        return sorted(seasons, reverse=True)

    def get_fixtures_by_season(
        self, season: int, status: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Get all fixtures for a specific LaLiga season.

        Args:
            season: Season year (e.g., 2023 for 2023-2024 season)
            status: Filter by status ('FT' for finished, 'NS' for not started, etc.)

        Returns:
            List of fixture dictionaries

        Example:
            >>> client = APIFootballClient()
            >>> fixtures = client.get_fixtures_by_season(2023, status='FT')
            >>> print(f"Found {len(fixtures)} finished matches")
        """
        params = {
            "league": self.league_id,
            "season": season,
        }

        if status:
            params["status"] = status

        endpoint = "/fixtures"
        response = self._make_request(endpoint, params)

        fixtures = response.get("response", [])
        logger.info(f"Found {len(fixtures)} fixtures for season {season}")

        return fixtures

    def get_fixture_statistics(self, fixture_id: int) -> dict[str, Any]:
        """
        Get detailed statistics for a specific fixture.

        Args:
            fixture_id: Fixture ID from API

        Returns:
            Dictionary with detailed match statistics

        Example:
            >>> client = APIFootballClient()
            >>> stats = client.get_fixture_statistics(1234567)
            >>> print(stats['statistics'])
        """
        endpoint = "/fixtures/statistics"
        params = {"fixture": fixture_id}

        response = self._make_request(endpoint, params)

        return response.get("response", {})

    def get_standings(self, season: int) -> list[dict[str, Any]]:
        """
        Get league standings for a specific season.

        Args:
            season: Season year

        Returns:
            List of team standings

        Example:
            >>> client = APIFootballClient()
            >>> standings = client.get_standings(2023)
            >>> for team in standings[:3]:
            ...     print(f"{team['rank']}. {team['team']['name']} - {team['points']} pts")
        """
        endpoint = "/standings"
        params = {
            "league": self.league_id,
            "season": season,
        }

        response = self._make_request(endpoint, params)

        # Extract standings from nested structure
        standings_data = response.get("response", [])
        if standings_data and len(standings_data) > 0:
            league_data = standings_data[0].get("league", {})
            standings = league_data.get("standings", [[]])[0]
            logger.info(f"Found {len(standings)} teams in standings")
            return standings

        return []

    def get_teams(self, season: int) -> list[dict[str, Any]]:
        """
        Get all teams in LaLiga for a specific season.

        Args:
            season: Season year

        Returns:
            List of team dictionaries

        Example:
            >>> client = APIFootballClient()
            >>> teams = client.get_teams(2023)
            >>> print([team['team']['name'] for team in teams])
        """
        endpoint = "/teams"
        params = {
            "league": self.league_id,
            "season": season,
        }

        response = self._make_request(endpoint, params)

        teams = response.get("response", [])
        logger.info(f"Found {len(teams)} teams for season {season}")

        return teams

    def get_h2h(self, team1_id: int, team2_id: int, last: int = 10) -> list[dict[str, Any]]:
        """
        Get head-to-head matches between two teams.

        Args:
            team1_id: First team ID
            team2_id: Second team ID
            last: Number of last matches to retrieve

        Returns:
            List of h2h fixtures

        Example:
            >>> client = APIFootballClient()
            >>> h2h = client.get_h2h(530, 529, last=5)  # Real Madrid vs Barcelona
            >>> print(f"Last 5 El Clásico matches: {len(h2h)}")
        """
        endpoint = "/fixtures/headtohead"
        params = {
            "h2h": f"{team1_id}-{team2_id}",
            "last": last,
        }

        response = self._make_request(endpoint, params)

        h2h_matches = response.get("response", [])
        logger.info(f"Found {len(h2h_matches)} h2h matches")

        return h2h_matches

    def close(self) -> None:
        """Close the requests session."""
        self.session.close()
        logger.info("API Football client session closed")

    def __enter__(self) -> "APIFootballClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()


def main() -> None:
    """Example usage of API Football client."""

    # This will fail if API key is not set
    try:
        with APIFootballClient() as client:
            # Get available seasons
            logger.info("Fetching available seasons...")
            seasons = client.get_seasons()
            logger.info(f"Available seasons: {seasons[:5]}")

            # Get teams for valid season (free plan: 2022-2024)
            if seasons:
                # Use 2024 instead of latest (free plan limitation)
                valid_season = 2024 if 2024 in seasons else seasons[0]
                logger.info(f"\nFetching teams for season {valid_season}...")
                teams = client.get_teams(valid_season)
                logger.info(f"Teams count: {len(teams)}")

                if teams:
                    # Print first 3 teams
                    logger.info("\nFirst 3 teams:")
                    for team in teams[:3]:
                        logger.info(f"  - {team['team']['name']} (ID: {team['team']['id']})")

    except ValueError as e:
        logger.error(f"\nAPI Configuration Error: {e}")
        logger.info("\nTo fix this:")
        logger.info("1. Register at https://www.api-football.com/")
        logger.info("2. Get your free API key (100 requests/day)")
        logger.info("3. Add it to your .env file: API_FOOTBALL_KEY=your_key_here")


if __name__ == "__main__":
    main()
