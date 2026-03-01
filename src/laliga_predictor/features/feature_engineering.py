"""
Feature engineering for La Liga match prediction.

Builds pre-match features from historical data for ML models.
CRITICAL: All features use only data strictly BEFORE the match date
to prevent data leakage.
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd

from ..config import get_settings

logger = logging.getLogger(__name__)

# Derby pairs (teams from the same city/region)
DERBIES: set[frozenset[str]] = {
    frozenset({"Real Madrid", "Atletico Madrid"}),
    frozenset({"Real Madrid", "Getafe"}),
    frozenset({"Barcelona", "Espanyol"}),
    frozenset({"Sevilla", "Real Betis"}),
    frozenset({"Athletic Club", "Real Sociedad"}),
    frozenset({"Valencia", "Levante"}),
    frozenset({"Deportivo La Coruna", "Celta Vigo"}),
}

# ESPN advanced stats to compute rolling averages for
ESPN_ROLLING_STATS: list[str] = [
    "possession",
    "passes_cmp_pct",
    "tackles_won",
    "interceptions",
    "clearances",
    "crosses_cmp_pct",
    "long_balls_cmp_pct",
    "saves",
    "blocked_shots",
    "offsides",
]


class MatchFeatureBuilder:
    """Builds pre-match feature vectors from historical data.

    All features are computed using data strictly before the match date
    to prevent data leakage.

    Args:
        matches_df: All completed matches (from data_loader.load_all_matches)
        advanced_stats_df: ESPN/FBref stats (from data_loader.load_advanced_stats)
        standings_df: League standings per matchweek (from data_loader.load_standings)
        rolling_windows: Window sizes for rolling averages (default: [3, 5, 10])
    """

    def __init__(
        self,
        matches_df: pd.DataFrame,
        advanced_stats_df: pd.DataFrame,
        standings_df: pd.DataFrame,
        rolling_windows: Optional[list[int]] = None,
    ) -> None:
        settings = get_settings()
        self.windows = rolling_windows or [
            int(w) for w in settings.ROLLING_WINDOWS.split(",")
        ]

        # Sort by date for correct temporal ordering
        self.matches = matches_df.sort_values("match_date").reset_index(drop=True)
        self.advanced = advanced_stats_df.sort_values("match_date").reset_index(drop=True)
        self.standings = standings_df

        # Build team-perspective match history for efficient lookups
        self._team_history = self._build_team_history()
        self._team_advanced = self._build_team_advanced_history()

        # Precompute standings lookup: (season_code, team_id, match_week) -> row
        self._standings_lookup = self._build_standings_lookup()

        # Precompute ELO ratings for all teams
        self._elo_history = self._compute_elo_ratings()

    def _build_team_history(self) -> pd.DataFrame:
        """Build a per-team match history with stats from each team's perspective."""
        rows = []
        for _, m in self.matches.iterrows():
            # Home team perspective
            rows.append({
                "match_date": m["match_date"],
                "match_id": m["match_id"],
                "season_code": m["season_code"],
                "team_id": m["home_team_id"],
                "opponent_id": m["away_team_id"],
                "is_home": True,
                "goals_scored": m["home_score"],
                "goals_conceded": m["away_score"],
                "result": m["result"],
                "points": 3 if m["result"] == "H" else (1 if m["result"] == "D" else 0),
                "win": 1 if m["result"] == "H" else 0,
                "draw": 1 if m["result"] == "D" else 0,
                "clean_sheet": 1 if m["away_score"] == 0 else 0,
                "shots": m.get("home_shots"),
                "shots_on_target": m.get("home_shots_on_target"),
                "corners": m.get("home_corners"),
                "fouls": m.get("home_fouls"),
                "yellow_cards": _safe_add(m.get("home_yellow_cards"), 0),
                "red_cards": _safe_add(m.get("home_red_cards"), 0),
                "total_cards": _safe_add(
                    m.get("home_yellow_cards"), m.get("home_red_cards")
                ),
            })
            # Away team perspective
            rows.append({
                "match_date": m["match_date"],
                "match_id": m["match_id"],
                "season_code": m["season_code"],
                "team_id": m["away_team_id"],
                "opponent_id": m["home_team_id"],
                "is_home": False,
                "goals_scored": m["away_score"],
                "goals_conceded": m["home_score"],
                "result": m["result"],
                "points": 3 if m["result"] == "A" else (1 if m["result"] == "D" else 0),
                "win": 1 if m["result"] == "A" else 0,
                "draw": 1 if m["result"] == "D" else 0,
                "clean_sheet": 1 if m["home_score"] == 0 else 0,
                "shots": m.get("away_shots"),
                "shots_on_target": m.get("away_shots_on_target"),
                "corners": m.get("away_corners"),
                "fouls": m.get("away_fouls"),
                "yellow_cards": _safe_add(m.get("away_yellow_cards"), 0),
                "red_cards": _safe_add(m.get("away_red_cards"), 0),
                "total_cards": _safe_add(
                    m.get("away_yellow_cards"), m.get("away_red_cards")
                ),
            })

        df = pd.DataFrame(rows).sort_values("match_date").reset_index(drop=True)
        return df

    def _build_team_advanced_history(self) -> pd.DataFrame:
        """Build per-team advanced stats keyed by (team_id, match_date)."""
        return self.advanced.sort_values("match_date").reset_index(drop=True)

    def _build_standings_lookup(self) -> dict:
        """Build standings lookup: (season_code, team_id) -> sorted list of (week, row)."""
        lookup: dict[tuple[str, int], list[tuple[int, pd.Series]]] = {}
        for _, row in self.standings.iterrows():
            key = (row["season_code"], row["team_id"])
            if key not in lookup:
                lookup[key] = []
            lookup[key].append((int(row["match_week"]), row))

        # Sort each list by match_week
        for key in lookup:
            lookup[key].sort(key=lambda x: x[0])

        return lookup

    def _compute_elo_ratings(
        self, k: float = 20.0, home_adv: float = 50.0, initial: float = 1500.0
    ) -> dict[int, list[tuple[pd.Timestamp, float]]]:
        """Compute ELO ratings for all teams, match by match.

        Returns dict: team_id -> [(match_date, elo_before_match), ...]
        sorted by match_date. Each entry records the rating BEFORE that match.
        """
        elo: dict[int, float] = {}
        history: dict[int, list[tuple[pd.Timestamp, float]]] = {}

        for _, m in self.matches.iterrows():
            h_id = m["home_team_id"]
            a_id = m["away_team_id"]
            date = m["match_date"]

            h_elo = elo.get(h_id, initial)
            a_elo = elo.get(a_id, initial)

            # Record pre-match ratings
            history.setdefault(h_id, []).append((date, h_elo))
            history.setdefault(a_id, []).append((date, a_elo))

            # Expected scores (with home advantage)
            exp_h = 1.0 / (1.0 + 10 ** ((a_elo - (h_elo + home_adv)) / 400.0))
            exp_a = 1.0 - exp_h

            # Actual scores
            result = m["result"]
            if result == "H":
                s_h, s_a = 1.0, 0.0
            elif result == "A":
                s_h, s_a = 0.0, 1.0
            else:
                s_h, s_a = 0.5, 0.5

            # Update ratings
            elo[h_id] = h_elo + k * (s_h - exp_h)
            elo[a_id] = a_elo + k * (s_a - exp_a)

        return history

    def _elo_features(
        self, home_id: int, away_id: int, cutoff: pd.Timestamp
    ) -> dict:
        """ELO rating features for a match."""
        h_elo = self._get_latest_elo(home_id, cutoff)
        a_elo = self._get_latest_elo(away_id, cutoff)

        if h_elo is not None and a_elo is not None:
            diff = h_elo - a_elo
            exp_home = 1.0 / (1.0 + 10 ** (-diff / 400.0))
        else:
            diff = None
            exp_home = None

        return {
            "h_elo": h_elo,
            "a_elo": a_elo,
            "elo_diff": diff,
            "elo_expected_home": exp_home,
        }

    def _get_latest_elo(self, team_id: int, cutoff: pd.Timestamp) -> Optional[float]:
        """Get the most recent ELO rating before cutoff."""
        entries = self._elo_history.get(team_id, [])
        latest = None
        for date, elo in entries:
            if date < cutoff:
                latest = elo
            else:
                break
        return latest

    def _streak_features(self, team_hist: pd.DataFrame, prefix: str) -> dict:
        """Compute current streak features (counted backwards from most recent)."""
        if len(team_hist) == 0:
            return {
                f"{prefix}_win_streak": 0,
                f"{prefix}_unbeaten_streak": 0,
                f"{prefix}_scoring_streak": 0,
                f"{prefix}_clean_sheet_streak": 0,
            }

        win_streak = 0
        for i in range(len(team_hist) - 1, -1, -1):
            if team_hist.iloc[i]["win"] == 1:
                win_streak += 1
            else:
                break

        unbeaten_streak = 0
        for i in range(len(team_hist) - 1, -1, -1):
            row = team_hist.iloc[i]
            if row["win"] == 1 or row["draw"] == 1:
                unbeaten_streak += 1
            else:
                break

        scoring_streak = 0
        for i in range(len(team_hist) - 1, -1, -1):
            if team_hist.iloc[i]["goals_scored"] > 0:
                scoring_streak += 1
            else:
                break

        clean_sheet_streak = 0
        for i in range(len(team_hist) - 1, -1, -1):
            if team_hist.iloc[i]["clean_sheet"] == 1:
                clean_sheet_streak += 1
            else:
                break

        return {
            f"{prefix}_win_streak": win_streak,
            f"{prefix}_unbeaten_streak": unbeaten_streak,
            f"{prefix}_scoring_streak": scoring_streak,
            f"{prefix}_clean_sheet_streak": clean_sheet_streak,
        }

    def _ema_features(
        self, team_hist: pd.DataFrame, prefix: str, alpha: float = 0.3
    ) -> dict:
        """Exponential moving average features (more weight on recent matches)."""
        if len(team_hist) < 2:
            return {
                f"{prefix}_ema_goals": None,
                f"{prefix}_ema_points": None,
                f"{prefix}_ema_conceded": None,
            }

        goals_ema = team_hist["goals_scored"].ewm(alpha=alpha, adjust=False).mean().iloc[-1]
        points_ema = team_hist["points"].ewm(alpha=alpha, adjust=False).mean().iloc[-1]
        conceded_ema = team_hist["goals_conceded"].ewm(alpha=alpha, adjust=False).mean().iloc[-1]

        return {
            f"{prefix}_ema_goals": float(goals_ema),
            f"{prefix}_ema_points": float(points_ema),
            f"{prefix}_ema_conceded": float(conceded_ema),
        }

    def _difference_features(
        self, home_hist: pd.DataFrame, away_hist: pd.DataFrame, n: int = 5
    ) -> dict:
        """Direct differences between home and away team's recent form."""
        h_last = home_hist.tail(n)
        a_last = away_hist.tail(n)

        h_win_rate = h_last["win"].mean() if len(h_last) > 0 else 0
        a_win_rate = a_last["win"].mean() if len(a_last) > 0 else 0
        h_goals = h_last["goals_scored"].mean() if len(h_last) > 0 else 0
        a_goals = a_last["goals_scored"].mean() if len(a_last) > 0 else 0
        h_conc = h_last["goals_conceded"].mean() if len(h_last) > 0 else 0
        a_conc = a_last["goals_conceded"].mean() if len(a_last) > 0 else 0

        return {
            "diff_win_rate_5": h_win_rate - a_win_rate,
            "diff_goals_5": h_goals - a_goals,
            "diff_conceded_5": h_conc - a_conc,
        }

    def _total_goals_features(
        self, home_hist: pd.DataFrame, away_hist: pd.DataFrame, n: int = 5
    ) -> dict:
        """Total goals features useful for over/under prediction."""
        h_last = home_hist.tail(n)
        a_last = away_hist.tail(n)

        h_total = None
        a_total = None
        combined = None

        if len(h_last) > 0:
            h_total = float((h_last["goals_scored"] + h_last["goals_conceded"]).mean())
        if len(a_last) > 0:
            a_total = float((a_last["goals_scored"] + a_last["goals_conceded"]).mean())
        if h_total is not None and a_total is not None:
            combined = (h_total + a_total) / 2

        return {
            "h_avg_total_goals_5": h_total,
            "a_avg_total_goals_5": a_total,
            "avg_combined_total_goals_5": combined,
        }

    def _draw_likelihood_features(
        self, home_hist: pd.DataFrame, away_hist: pd.DataFrame, n: int = 5
    ) -> dict:
        """Features that indicate draw likelihood."""
        h_last = home_hist.tail(n)
        a_last = away_hist.tail(n)

        # Defensive similarity: |avg_conceded_h - avg_conceded_a|
        if len(h_last) > 0 and len(a_last) > 0:
            h_conc = h_last["goals_conceded"].mean()
            a_conc = a_last["goals_conceded"].mean()
            defensive_sim = 1.0 / (1.0 + abs(h_conc - a_conc))

            # Goals diff closeness: how close are their scoring rates
            h_goals = h_last["goals_scored"].mean()
            a_goals = a_last["goals_scored"].mean()
            goals_closeness = 1.0 / (1.0 + abs(h_goals - a_goals))

            # Form similarity: how similar are their point rates
            h_pts = h_last["points"].mean()
            a_pts = a_last["points"].mean()
            form_sim = 1.0 / (1.0 + abs(h_pts - a_pts))
        else:
            defensive_sim = None
            goals_closeness = None
            form_sim = None

        return {
            "defensive_similarity_5": defensive_sim,
            "goals_diff_closeness_5": goals_closeness,
            "form_similarity_5": form_sim,
        }

    def build_dataset(self) -> pd.DataFrame:
        """Build complete feature matrix for all matches.

        Returns DataFrame where each row is a match with:
        - Feature columns (prefixed h_ for home, a_ for away)
        - Target columns: result, total_goals, total_cards
        - Metadata: match_id, match_date, season_code, home_team, away_team
        """
        logger.info(f"Building features for {len(self.matches)} matches...")

        feature_rows = []
        for idx, match in self.matches.iterrows():
            features = self._build_features_for_match(match)
            if features is not None:
                feature_rows.append(features)

            if (idx + 1) % 500 == 0:
                logger.info(f"  Progress: {idx + 1}/{len(self.matches)} matches")

        df = pd.DataFrame(feature_rows)
        logger.info(
            f"Built {len(df)} feature rows with {len(df.columns)} columns "
            f"({len(df.columns) - 7} features + 7 metadata/targets)"
        )
        return df

    def build_features_for_prediction(
        self,
        home_team_id: int,
        away_team_id: int,
        match_date: pd.Timestamp,
        season_code: str,
        home_team: str = "",
        away_team: str = "",
    ) -> Optional[dict]:
        """Build features for a future match (prediction mode).

        Same as _build_features_for_match but accepts raw parameters
        instead of a match row.
        """
        mock_row = pd.Series({
            "match_id": -1,
            "match_date": match_date,
            "season_code": season_code,
            "home_team": home_team,
            "away_team": away_team,
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "home_score": None,
            "away_score": None,
            "result": None,
            "home_yellow_cards": None,
            "away_yellow_cards": None,
            "home_red_cards": None,
            "away_red_cards": None,
        })
        return self._build_features_for_match(mock_row, include_targets=False)

    def _build_features_for_match(
        self, match: pd.Series, include_targets: bool = True
    ) -> Optional[dict]:
        """Compute all pre-match features for a single match.

        CRITICAL: Only uses data with match_date < this match's date.
        """
        cutoff = match["match_date"]
        home_id = match["home_team_id"]
        away_id = match["away_team_id"]
        season = match["season_code"]

        features: dict = {
            "match_id": match["match_id"],
            "match_date": cutoff,
            "season_code": season,
            "home_team": match.get("home_team", ""),
            "away_team": match.get("away_team", ""),
        }

        # Filter historical data (STRICTLY before match date)
        hist = self._team_history[self._team_history["match_date"] < cutoff]
        adv_hist = self._team_advanced[self._team_advanced["match_date"] < cutoff]

        home_hist = hist[hist["team_id"] == home_id]
        away_hist = hist[hist["team_id"] == away_id]

        # Skip matches with insufficient history (first few matchweeks)
        if len(home_hist) < 1 or len(away_hist) < 1:
            return None

        # --- A. Rolling form features ---
        for window in self.windows:
            features.update(
                self._rolling_form(home_hist, f"h", window)
            )
            features.update(
                self._rolling_form(away_hist, f"a", window)
            )

        # --- B. Home/away specific form ---
        home_at_home = home_hist[home_hist["is_home"]]
        away_at_away = away_hist[~away_hist["is_home"]]
        features.update(self._venue_form(home_at_home, "h_home", 5))
        features.update(self._venue_form(away_at_away, "a_away", 5))

        # --- C. ESPN advanced stats rolling ---
        home_adv = adv_hist[adv_hist["team_id"] == home_id]
        away_adv = adv_hist[adv_hist["team_id"] == away_id]
        features.update(self._advanced_rolling(home_adv, "h", 5))
        features.update(self._advanced_rolling(away_adv, "a", 5))

        # --- D. Head-to-head ---
        features.update(self._head_to_head(hist, home_id, away_id, 6))

        # --- E. Standings features ---
        features.update(
            self._standings_features(season, home_id, away_id, cutoff)
        )

        # --- F. Contextual features ---
        features.update(self._contextual_features(match, home_hist, away_hist))

        # --- G. ELO rating features ---
        features.update(self._elo_features(home_id, away_id, cutoff))

        # --- H. Streak features ---
        features.update(self._streak_features(home_hist, "h"))
        features.update(self._streak_features(away_hist, "a"))

        # --- I. EMA features ---
        features.update(self._ema_features(home_hist, "h"))
        features.update(self._ema_features(away_hist, "a"))

        # --- J. Difference features ---
        features.update(self._difference_features(home_hist, away_hist))

        # --- K. Total goals features (for O/U) ---
        features.update(self._total_goals_features(home_hist, away_hist))

        # --- L. Draw-likelihood features ---
        features.update(self._draw_likelihood_features(home_hist, away_hist))

        # --- M. H2H draw rate ---
        h2h_matches = features.get("h2h_total_matches", 0)
        h2h_draws = features.get("h2h_draws", 0)
        features["h2h_draw_rate"] = (
            h2h_draws / h2h_matches if h2h_matches > 0 else None
        )

        # --- Targets ---
        if include_targets:
            features["target_result"] = match.get("result")
            features["target_total_goals"] = _safe_add(
                match.get("home_score"), match.get("away_score")
            )
            features["target_total_cards"] = _safe_add(
                _safe_add(match.get("home_yellow_cards"), match.get("away_yellow_cards")),
                _safe_add(match.get("home_red_cards"), match.get("away_red_cards")),
            )

        return features

    # ================================================================
    # Feature computation helpers
    # ================================================================

    def _rolling_form(self, team_hist: pd.DataFrame, prefix: str, n: int) -> dict:
        """Compute rolling form features over last N matches."""
        last_n = team_hist.tail(n)
        count = len(last_n)

        if count == 0:
            return {
                f"{prefix}_win_rate_{n}": None,
                f"{prefix}_draw_rate_{n}": None,
                f"{prefix}_avg_goals_scored_{n}": None,
                f"{prefix}_avg_goals_conceded_{n}": None,
                f"{prefix}_avg_shots_{n}": None,
                f"{prefix}_avg_sot_{n}": None,
                f"{prefix}_avg_corners_{n}": None,
                f"{prefix}_avg_fouls_{n}": None,
                f"{prefix}_avg_cards_{n}": None,
                f"{prefix}_clean_sheets_{n}": None,
                f"{prefix}_points_{n}": None,
            }

        return {
            f"{prefix}_win_rate_{n}": last_n["win"].mean(),
            f"{prefix}_draw_rate_{n}": last_n["draw"].mean(),
            f"{prefix}_avg_goals_scored_{n}": last_n["goals_scored"].mean(),
            f"{prefix}_avg_goals_conceded_{n}": last_n["goals_conceded"].mean(),
            f"{prefix}_avg_shots_{n}": _safe_mean(last_n["shots"]),
            f"{prefix}_avg_sot_{n}": _safe_mean(last_n["shots_on_target"]),
            f"{prefix}_avg_corners_{n}": _safe_mean(last_n["corners"]),
            f"{prefix}_avg_fouls_{n}": _safe_mean(last_n["fouls"]),
            f"{prefix}_avg_cards_{n}": _safe_mean(last_n["total_cards"]),
            f"{prefix}_clean_sheets_{n}": last_n["clean_sheet"].sum() / count,
            f"{prefix}_points_{n}": last_n["points"].sum(),
        }

    def _venue_form(self, venue_hist: pd.DataFrame, prefix: str, n: int) -> dict:
        """Form when playing at specific venue (home or away)."""
        last_n = venue_hist.tail(n)
        count = len(last_n)

        if count == 0:
            return {
                f"{prefix}_win_rate_5": None,
                f"{prefix}_avg_goals_5": None,
                f"{prefix}_avg_conceded_5": None,
                f"{prefix}_avg_cards_5": None,
                f"{prefix}_points_5": None,
                f"{prefix}_matches_available": 0,
            }

        return {
            f"{prefix}_win_rate_5": last_n["win"].mean(),
            f"{prefix}_avg_goals_5": last_n["goals_scored"].mean(),
            f"{prefix}_avg_conceded_5": last_n["goals_conceded"].mean(),
            f"{prefix}_avg_cards_5": _safe_mean(last_n["total_cards"]),
            f"{prefix}_points_5": last_n["points"].sum(),
            f"{prefix}_matches_available": count,
        }

    def _advanced_rolling(
        self, adv_hist: pd.DataFrame, prefix: str, n: int
    ) -> dict:
        """Rolling averages of ESPN advanced stats over last N matches."""
        last_n = adv_hist.tail(n)
        result = {}

        for stat in ESPN_ROLLING_STATS:
            col_name = f"{prefix}_avg_{stat}_5"
            if len(last_n) == 0 or stat not in last_n.columns:
                result[col_name] = None
            else:
                result[col_name] = _safe_mean(last_n[stat])

        return result

    def _head_to_head(
        self,
        all_hist: pd.DataFrame,
        home_id: int,
        away_id: int,
        n: int,
    ) -> dict:
        """Head-to-head record between two teams (last N meetings)."""
        # Find matches where these two teams played each other
        h2h = all_hist[
            (all_hist["team_id"] == home_id) & (all_hist["opponent_id"] == away_id)
        ].tail(n)

        total = len(h2h)
        if total == 0:
            return {
                "h2h_home_wins": 0,
                "h2h_away_wins": 0,
                "h2h_draws": 0,
                "h2h_home_avg_goals": None,
                "h2h_away_avg_goals": None,
                "h2h_total_matches": 0,
            }

        # Get the away team's perspective for the same matches
        h2h_away = all_hist[
            (all_hist["team_id"] == away_id) & (all_hist["opponent_id"] == home_id)
        ].tail(n)

        return {
            "h2h_home_wins": h2h["win"].sum(),
            "h2h_away_wins": h2h_away["win"].sum() if len(h2h_away) > 0 else 0,
            "h2h_draws": h2h["draw"].sum(),
            "h2h_home_avg_goals": h2h["goals_scored"].mean(),
            "h2h_away_avg_goals": (
                h2h_away["goals_scored"].mean() if len(h2h_away) > 0 else None
            ),
            "h2h_total_matches": total,
        }

    def _standings_features(
        self,
        season_code: str,
        home_id: int,
        away_id: int,
        cutoff: pd.Timestamp,
    ) -> dict:
        """League standing features BEFORE the match."""
        home_standing = self._get_latest_standing(season_code, home_id)
        away_standing = self._get_latest_standing(season_code, away_id)

        h_pos = home_standing["position"] if home_standing is not None else None
        a_pos = away_standing["position"] if away_standing is not None else None
        h_pts = home_standing["points"] if home_standing is not None else None
        a_pts = away_standing["points"] if away_standing is not None else None
        h_gd = home_standing["goal_difference"] if home_standing is not None else None
        a_gd = away_standing["goal_difference"] if away_standing is not None else None

        return {
            "h_league_position": h_pos,
            "a_league_position": a_pos,
            "h_league_points": h_pts,
            "a_league_points": a_pts,
            "h_league_gd": h_gd,
            "a_league_gd": a_gd,
            "position_diff": _safe_sub(h_pos, a_pos),
            "points_diff": _safe_sub(h_pts, a_pts),
        }

    def _get_latest_standing(
        self, season_code: str, team_id: int
    ) -> Optional[pd.Series]:
        """Get the most recent standing for a team in a season."""
        key = (season_code, team_id)
        entries = self._standings_lookup.get(key, [])
        if not entries:
            return None
        # Return last available matchweek
        return entries[-1][1]

    def _contextual_features(
        self,
        match: pd.Series,
        home_hist: pd.DataFrame,
        away_hist: pd.DataFrame,
    ) -> dict:
        """Contextual and derived features."""
        cutoff = match["match_date"]

        # Days since last match (rest)
        h_rest = None
        a_rest = None
        if len(home_hist) > 0:
            last_home = home_hist.iloc[-1]["match_date"]
            h_rest = (cutoff - last_home).days
        if len(away_hist) > 0:
            last_away = away_hist.iloc[-1]["match_date"]
            a_rest = (cutoff - last_away).days

        rest_adv = _safe_sub(h_rest, a_rest)

        # Derby flag
        home_name = match.get("home_team", "")
        away_name = match.get("away_team", "")
        is_derby = frozenset({home_name, away_name}) in DERBIES

        # Matchweek estimation (approximate from match count in season)
        season_matches = self.matches[
            self.matches["season_code"] == match["season_code"]
        ]
        matches_before = season_matches[
            season_matches["match_date"] <= cutoff
        ]
        # ~10 matches per matchweek in La Liga (20 teams, 10 games per week)
        match_week = max(1, len(matches_before) // 10 + 1)

        return {
            "h_days_rest": h_rest,
            "a_days_rest": a_rest,
            "rest_advantage": rest_adv,
            "match_week": match_week,
            "is_early_season": 1 if match_week <= 10 else 0,
            "is_late_season": 1 if match_week >= 30 else 0,
            "is_derby": 1 if is_derby else 0,
        }


# ================================================================
# Utility functions
# ================================================================


def _safe_add(a: object, b: object) -> Optional[float]:
    """Safe addition handling None/NaN values."""
    if a is None or b is None:
        return None
    try:
        va = float(a)
        vb = float(b)
        if np.isnan(va) or np.isnan(vb):
            return None
        return va + vb
    except (ValueError, TypeError):
        return None


def _safe_sub(a: object, b: object) -> Optional[float]:
    """Safe subtraction handling None/NaN values."""
    if a is None or b is None:
        return None
    try:
        va = float(a)
        vb = float(b)
        if np.isnan(va) or np.isnan(vb):
            return None
        return va - vb
    except (ValueError, TypeError):
        return None


def _safe_mean(series: pd.Series) -> Optional[float]:
    """Mean of a series, returning None if all NaN."""
    valid = series.dropna()
    if len(valid) == 0:
        return None
    return float(valid.mean())


# ================================================================
# CLI entry point
# ================================================================


def main() -> None:
    """Build features and save to parquet."""
    import argparse

    from .data_loader import load_all_data
    from .feature_store import save_features

    parser = argparse.ArgumentParser(description="Build ML features from database")
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output parquet path (default: data/processed/features.parquet)",
    )
    parser.add_argument(
        "--windows",
        type=str,
        default=None,
        help="Rolling window sizes, comma-separated (default: from config)",
    )

    args = parser.parse_args()
    settings = get_settings()

    output = args.output or str(settings.FEATURE_CACHE_DIR / "features.parquet")
    windows = (
        [int(w) for w in args.windows.split(",")]
        if args.windows
        else None
    )

    logger.info("Loading data from database...")
    matches, advanced, standings = load_all_data()

    logger.info("Building features...")
    builder = MatchFeatureBuilder(matches, advanced, standings, rolling_windows=windows)
    df = builder.build_dataset()

    save_features(df, output)
    logger.info(f"Features saved to {output}")

    # Print summary
    feature_cols = [c for c in df.columns if c not in {
        "match_id", "match_date", "season_code", "home_team", "away_team",
        "target_result", "target_total_goals", "target_total_cards",
    }]
    logger.info(f"Summary: {len(df)} matches, {len(feature_cols)} features")
    logger.info(f"Seasons: {sorted(df['season_code'].unique())}")
    logger.info(f"Null percentage: {df[feature_cols].isnull().mean().mean():.1%}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    main()
