"""
Script to explore FBRef data structure and available information.

This script helps us understand what data is available before designing the database.
"""

import logging
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.laliga_predictor.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def explore_seasons_page():
    """Explore the LaLiga seasons history page."""
    url = "https://fbref.com/en/comps/12/history/La-Liga-Seasons"

    settings = get_settings()
    headers = {
        'User-Agent': settings.get_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    try:
        logger.info(f"Fetching: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'lxml')

        # Find the main table with seasons
        table = soup.find('table', {'id': 'seasons'})

        if not table:
            logger.error("Could not find seasons table")
            return

        logger.info("\n" + "="*80)
        logger.info("AVAILABLE SEASONS")
        logger.info("="*80)

        headers_row = table.find('thead')
        if headers_row:
            headers = [th.get_text(strip=True) for th in headers_row.find_all('th')]
            logger.info(f"\nTable columns: {headers}")

        tbody = table.find('tbody')
        rows = tbody.find_all('tr') if tbody else []

        logger.info(f"\nTotal seasons available: {len(rows)}\n")

        seasons_info = []
        for i, row in enumerate(rows[:10]):  # Show first 10
            cells = row.find_all(['th', 'td'])
            season_data = {}

            for j, cell in enumerate(cells):
                # Get text
                text = cell.get_text(strip=True)

                # Check for links
                link = cell.find('a')
                if link:
                    href = link.get('href', '')
                    season_data[f'col_{j}'] = {'text': text, 'link': href}
                else:
                    season_data[f'col_{j}'] = {'text': text}

            seasons_info.append(season_data)

            # Print season info
            logger.info(f"Season {i+1}:")
            for key, value in season_data.items():
                if isinstance(value, dict):
                    if 'link' in value:
                        logger.info(f"  {key}: {value['text']} -> {value['link']}")
                    else:
                        logger.info(f"  {key}: {value['text']}")

        # Now explore a specific season to see available stats
        logger.info("\n" + "="*80)
        logger.info("EXPLORING SPECIFIC SEASON DATA")
        logger.info("="*80)

        # Get link to most recent season
        first_row = rows[0]
        season_link = first_row.find('a')
        if season_link:
            season_url = "https://fbref.com" + season_link.get('href')
            explore_season_page(season_url)

    except requests.RequestException as e:
        logger.error(f"Error fetching page: {e}")


def explore_season_page(url):
    """Explore a specific season page to see available data."""
    settings = get_settings()
    headers = {
        'User-Agent': settings.get_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }

    try:
        logger.info(f"\nFetching season page: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'lxml')

        # Find all tables available
        tables = soup.find_all('table')
        logger.info(f"\nTables found on season page: {len(tables)}")

        for i, table in enumerate(tables[:5]):  # First 5 tables
            table_id = table.get('id', 'no-id')
            caption = table.find('caption')
            caption_text = caption.get_text(strip=True) if caption else "No caption"

            logger.info(f"\nTable {i+1}:")
            logger.info(f"  ID: {table_id}")
            logger.info(f"  Caption: {caption_text}")

            # Get column headers
            thead = table.find('thead')
            if thead:
                headers = []
                for th in thead.find_all('th'):
                    header_text = th.get_text(strip=True)
                    if header_text:
                        headers.append(header_text)
                logger.info(f"  Columns ({len(headers)}): {', '.join(headers[:10])}")
                if len(headers) > 10:
                    logger.info(f"  ... and {len(headers) - 10} more columns")

        # Look for scores and fixtures table
        fixtures_table = soup.find('table', {'id': lambda x: x and 'sched' in x})
        if fixtures_table:
            logger.info("\n" + "="*80)
            logger.info("FIXTURES TABLE FOUND")
            logger.info("="*80)

            thead = fixtures_table.find('thead')
            if thead:
                headers = [th.get_text(strip=True) for th in thead.find_all('th')]
                logger.info(f"\nFixtures columns: {headers}")

            # Sample first match
            tbody = fixtures_table.find('tbody')
            if tbody:
                first_match = tbody.find('tr')
                if first_match:
                    cells = first_match.find_all(['th', 'td'])
                    logger.info(f"\nSample match data:")
                    for i, cell in enumerate(cells):
                        text = cell.get_text(strip=True)
                        logger.info(f"  Column {i}: {text}")

    except requests.RequestException as e:
        logger.error(f"Error fetching season page: {e}")


def main():
    """Main function."""
    logger.info("Starting FBRef exploration...")
    logger.info("This will help us understand what data is available\n")

    explore_seasons_page()

    logger.info("\n" + "="*80)
    logger.info("EXPLORATION COMPLETE")
    logger.info("="*80)


if __name__ == "__main__":
    main()
