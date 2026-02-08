"""
Soccerdata library client wrapper.

Provides clean interfaces to FBref, ESPN, and MatchHistory data sources
through the soccerdata Python library for La Liga data.

Note: The 2020-2021 season ("2021") requires special handling for ESPN
because the soccerdata library's date-based season resolution fails due
to the COVID-extended 2019-2020 season overlapping into July 2020.
"""

import json
import logging
from datetime import datetime as dt
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
import soccerdata as sd

from ..config import get_settings

logger = logging.getLogger(__name__)

LEAGUE = "ESP-La Liga"

# ESPN direct API constants (used for COVID season workaround)
_ESPN_API_BASE = "http://site.api.espn.com/apis/site/v2/sports/soccer"
_ESPN_LEAGUE_ID = "esp.1"
_COVID_SEASON = "2021"  # soccerdata maps this to wrong ESPN season
_COVID_START_DATE = "20200801"  # After COVID-extended 19-20 season ended


class SoccerdataClient:
    """Unified client for soccerdata library sources."""

    def __init__(self, seasons: Optional[list[str]] = None) -> None:
        settings = get_settings()

        if seasons is None:
            seasons = [s.strip() for s in settings.SD_SEASONS.split(",")]

        self.seasons = seasons
        self.league = LEAGUE

        self.data_dir = Path("data/external/soccerdata_cache")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"SoccerdataClient initialized for {self.league}, seasons: {self.seasons}")

    # ================================================================
    # FBref
    # ================================================================

    def _get_fbref(self, seasons: Optional[list[str]] = None) -> sd.FBref:
        """Create FBref reader instance."""
        s = seasons or self.seasons
        return sd.FBref(
            leagues=self.league,
            seasons=s,
            no_cache=False,
            no_store=False,
            data_dir=self.data_dir / "FBref",
        )

    def fetch_schedule(self, seasons: Optional[list[str]] = None) -> pd.DataFrame:
        """Fetch match schedule with xG from FBref.

        Returns columns: week, day, date, time, home_team, home_xg, score,
        away_xg, away_team, attendance, venue, referee, game_id, etc.
        """
        fbref = self._get_fbref(seasons)
        logger.info(f"Fetching FBref schedule for {seasons or self.seasons}...")
        df = fbref.read_schedule()
        logger.info(f"Fetched {len(df)} matches from FBref schedule")
        return df

    def fetch_team_match_stats(
        self, stat_type: str, seasons: Optional[list[str]] = None
    ) -> pd.DataFrame:
        """Fetch team match stats from FBref.

        Args:
            stat_type: One of 'schedule', 'keeper', 'shooting', 'passing',
                       'passing_types', 'goal_shot_creation', 'defense',
                       'possession', 'misc'.
            seasons: Override seasons list.

        Returns:
            DataFrame indexed by (league, season, team, game).
        """
        fbref = self._get_fbref(seasons)
        logger.info(f"Fetching FBref team_match_stats (stat_type={stat_type})...")
        df = fbref.read_team_match_stats(stat_type=stat_type)
        logger.info(f"Fetched {len(df)} rows for stat_type={stat_type}")
        return df

    def fetch_player_match_stats(
        self, stat_type: str = "summary", seasons: Optional[list[str]] = None
    ) -> pd.DataFrame:
        """Fetch player-level match stats from FBref."""
        fbref = self._get_fbref(seasons)
        logger.info(f"Fetching FBref player_match_stats (stat_type={stat_type})...")
        df = fbref.read_player_match_stats(stat_type=stat_type)
        logger.info(f"Fetched {len(df)} player-match rows")
        return df

    def fetch_shot_events(self, seasons: Optional[list[str]] = None) -> pd.DataFrame:
        """Fetch shot event data from FBref."""
        fbref = self._get_fbref(seasons)
        logger.info("Fetching FBref shot events...")
        df = fbref.read_shot_events()
        logger.info(f"Fetched {len(df)} shot events")
        return df

    def fetch_events(self, seasons: Optional[list[str]] = None) -> pd.DataFrame:
        """Fetch match events (goals, cards, subs) from FBref."""
        fbref = self._get_fbref(seasons)
        logger.info("Fetching FBref match events...")
        df = fbref.read_events()
        logger.info(f"Fetched {len(df)} events")
        return df

    # ================================================================
    # ESPN
    # ================================================================

    def _get_espn(self, seasons: Optional[list[str]] = None) -> sd.ESPN:
        """Create ESPN reader instance."""
        s = seasons or self.seasons
        return sd.ESPN(
            leagues=self.league,
            seasons=s,
            no_cache=False,
            no_store=False,
            data_dir=self.data_dir / "ESPN",
        )

    def fetch_espn_schedule(
        self, seasons: Optional[list[str]] = None
    ) -> pd.DataFrame:
        """Fetch match schedule from ESPN.

        Returns DataFrame with columns: date, home_team, away_team, game_id,
        league_id. Handles COVID-affected 2020-2021 season via direct API.
        """
        s = seasons or self.seasons

        # Split COVID season from regular seasons
        regular = [x for x in s if x != _COVID_SEASON]
        has_covid = _COVID_SEASON in s

        dfs = []
        if regular:
            espn = self._get_espn(regular)
            logger.info(f"Fetching ESPN schedule for {regular}...")
            df = espn.read_schedule()
            logger.info(f"Fetched {len(df)} matches from ESPN schedule (regular)")
            dfs.append(df)

        if has_covid:
            logger.info("Fetching ESPN schedule for 2020-21 (COVID workaround)...")
            df = self._fetch_espn_direct_schedule()
            logger.info(f"Fetched {len(df)} matches from ESPN (COVID 2020-21)")
            dfs.append(df)

        if not dfs:
            return pd.DataFrame()

        result = pd.concat(dfs).sort_index()
        logger.info(f"Fetched {len(result)} total ESPN schedule matches")
        return result

    def fetch_espn_matchsheet(
        self, match_id: int, seasons: Optional[list[str]] = None
    ) -> pd.DataFrame:
        """Fetch detailed matchsheet for a single ESPN match.

        Args:
            match_id: ESPN game_id (integer) from schedule.
            seasons: Override seasons list.

        Returns:
            DataFrame with per-team stats: possession_pct, total_shots,
            shots_on_target, fouls_committed, yellow_cards, red_cards,
            offsides, won_corners, saves, accurate_passes, total_passes,
            pass_pct, tackles, interceptions, clearances, etc.
        """
        s = seasons or self.seasons

        # Use direct API for COVID season
        if len(s) == 1 and s[0] == _COVID_SEASON:
            return self._fetch_espn_direct_matchsheet(match_id)

        espn = self._get_espn(s)
        logger.info(f"Fetching ESPN matchsheet for game {match_id}...")
        df = espn.read_matchsheet(match_id=match_id)
        logger.info(f"Fetched matchsheet: {len(df)} rows")
        return df

    # ----------------------------------------------------------------
    # ESPN direct API (COVID 2020-2021 workaround)
    # ----------------------------------------------------------------

    def _espn_cache_dir(self) -> Path:
        """Return cache directory for direct ESPN API calls."""
        d = self.data_dir / "ESPN" / "covid_2021"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _espn_api_get(self, url: str, cache_path: Path) -> dict:
        """Fetch JSON from ESPN API with file-based caching."""
        if cache_path.exists():
            return json.loads(cache_path.read_text())

        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        cache_path.write_text(json.dumps(data))
        return data

    def _fetch_espn_direct_schedule(self) -> pd.DataFrame:
        """Fetch ESPN 2020-2021 schedule via direct API.

        The soccerdata library incorrectly maps season '2021' to the
        2019-2020 season because the COVID-extended 19-20 season was
        still active on July 1, 2020 (soccerdata's default start date).
        """
        from soccerdata._common import make_game_id, standardize_colnames
        from soccerdata._config import TEAMNAME_REPLACEMENTS

        cache = self._espn_cache_dir()

        # Fetch calendar (list of match dates)
        cal_url = f"{_ESPN_API_BASE}/{_ESPN_LEAGUE_ID}/scoreboard?dates={_COVID_START_DATE}"
        cal_data = self._espn_api_get(cal_url, cache / "calendar.json")
        calendar = cal_data["leagues"][0]["calendar"]

        match_dates = [
            dt.strptime(d, "%Y-%m-%dT%H:%MZ").strftime("%Y%m%d")
            for d in calendar
        ]

        # Fetch scoreboard for each match date
        df_list = []
        for date_str in match_dates:
            url = f"{_ESPN_API_BASE}/{_ESPN_LEAGUE_ID}/scoreboard?dates={date_str}"
            data = self._espn_api_get(url, cache / f"scoreboard_{date_str}.json")

            for e in data.get("events", []):
                competitors = e.get("competitions", [{}])[0].get("competitors", [])
                if len(competitors) < 2:
                    continue
                df_list.append({
                    "league": LEAGUE,
                    "season": _COVID_SEASON,
                    "date": e["date"],
                    "home_team": competitors[0]["team"]["name"],
                    "away_team": competitors[1]["team"]["name"],
                    "game_id": int(e["id"]),
                    "league_id": _ESPN_LEAGUE_ID,
                })

        if not df_list:
            return pd.DataFrame()

        return (
            pd.DataFrame(df_list)
            .replace({"home_team": TEAMNAME_REPLACEMENTS, "away_team": TEAMNAME_REPLACEMENTS})
            .assign(date=lambda x: pd.to_datetime(x["date"]))
            .dropna(subset=["home_team", "away_team", "date"])
            .assign(game=lambda df: df.apply(make_game_id, axis=1))
            .set_index(["league", "season", "game"])
            .sort_index()
        )

    def _fetch_espn_direct_matchsheet(self, game_id: int) -> pd.DataFrame:
        """Fetch ESPN matchsheet via direct API for a COVID season game."""
        from soccerdata._common import standardize_colnames
        from soccerdata._config import TEAMNAME_REPLACEMENTS

        cache = self._espn_cache_dir()
        url = f"{_ESPN_API_BASE}/{_ESPN_LEAGUE_ID}/summary?event={game_id}"
        data = self._espn_api_get(url, cache / f"Summary_{game_id}.json")

        df_list = []
        for i in range(2):
            match_sheet: dict = {
                "league": LEAGUE,
                "season": _COVID_SEASON,
                "game": f"covid_{game_id}_{i}",
                "team": data["boxscore"]["form"][i]["team"]["displayName"],
                "is_home": (i == 0),
                "venue": (
                    data["gameInfo"]["venue"]["fullName"]
                    if "venue" in data.get("gameInfo", {})
                    else None
                ),
                "attendance": data.get("gameInfo", {}).get("attendance"),
            }
            if "statistics" in data.get("boxscore", {}).get("teams", [{}])[i]:
                for stat in data["boxscore"]["teams"][i]["statistics"]:
                    match_sheet[stat["name"]] = stat["displayValue"]
            df_list.append(match_sheet)

        return (
            pd.DataFrame(df_list)
            .replace({"team": TEAMNAME_REPLACEMENTS})
            .pipe(standardize_colnames)
            .set_index(["league", "season", "game", "team"])
            .sort_index()
        )

    # ================================================================
    # MatchHistory (Football-Data.co.uk)
    # ================================================================

    def _get_match_history(self, seasons: Optional[list[str]] = None) -> sd.MatchHistory:
        """Create MatchHistory reader instance."""
        s = seasons or self.seasons
        return sd.MatchHistory(
            leagues=self.league,
            seasons=s,
            no_cache=False,
            no_store=False,
            data_dir=self.data_dir / "MatchHistory",
        )

    def fetch_match_history_games(
        self, seasons: Optional[list[str]] = None
    ) -> pd.DataFrame:
        """Fetch historical match data from Football-Data.co.uk.

        Returns DataFrame with: FTHG, FTAG, FTR, HTHG, HTAG, HTR,
        HS, AS, HST, AST, HF, AF, HC, AC, HY, AY, HR, AR + betting odds.
        """
        mh = self._get_match_history(seasons)
        logger.info(f"Fetching MatchHistory games for {seasons or self.seasons}...")
        df = mh.read_games()
        logger.info(f"Fetched {len(df)} matches from MatchHistory")
        return df
