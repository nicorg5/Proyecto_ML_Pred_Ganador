"""
Predict all matches for a La Liga matchday (jornada).

Shows predictions vs actual results for played matches,
and predictions for upcoming matches.

Usage:
    uv run python -m src.laliga_predictor.models.predict_jornada --jornada 24
    uv run python -m src.laliga_predictor.models.predict_jornada --jornada 24 --season 2526
"""

import argparse
import logging
import warnings
from typing import Optional

import psycopg2

from ..config import get_settings
from ..features.data_loader import load_all_data
from ..features.feature_engineering import MatchFeatureBuilder
from .predict import load_trained_models, predict_match

logger = logging.getLogger(__name__)


def get_jornada_matches(
    season_code: str, jornada: int
) -> list[dict]:
    """Fetch matches for a specific jornada from the database.

    Matches are assigned to jornadas by ordering them by date
    and grouping in batches of 10 (20 teams -> 10 matches per matchday).

    Returns list of dicts with match info, ordered by date.
    """
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.SD_DB_HOST,
        port=settings.SD_DB_PORT,
        database=settings.SD_DB_NAME,
        user=settings.SD_DB_USER,
        password=settings.SD_DB_PASSWORD,
    )

    try:
        cur = conn.cursor()
        cur.execute(
            """
            WITH numbered AS (
                SELECT
                    m.id,
                    m.match_date,
                    ht.canonical_name AS home_team,
                    at.canonical_name AS away_team,
                    m.home_score,
                    m.away_score,
                    m.result,
                    m.home_yellow_cards,
                    m.away_yellow_cards,
                    m.home_red_cards,
                    m.away_red_cards,
                    NTILE(%s) OVER (ORDER BY m.match_date, m.id) AS jornada
                FROM matches m
                JOIN seasons s ON m.season_id = s.id
                JOIN teams ht ON m.home_team_id = ht.id
                JOIN teams at ON m.away_team_id = at.id
                WHERE s.season_code = %s
            )
            SELECT home_team, away_team, match_date::date,
                   home_score, away_score, result,
                   home_yellow_cards, away_yellow_cards,
                   home_red_cards, away_red_cards
            FROM numbered
            WHERE jornada = %s
            ORDER BY match_date, home_team
            """,
            (_get_total_jornadas(season_code, conn), season_code, jornada),
        )

        rows = cur.fetchall()
        matches = []
        for r in rows:
            total_cards = None
            if r[6] is not None and r[7] is not None:
                total_cards = (r[6] or 0) + (r[7] or 0) + (r[8] or 0) + (r[9] or 0)

            total_goals = None
            if r[3] is not None and r[4] is not None:
                total_goals = r[3] + r[4]

            matches.append({
                "home_team": r[0],
                "away_team": r[1],
                "match_date": str(r[2]),
                "home_score": r[3],
                "away_score": r[4],
                "result": r[5],
                "total_goals": total_goals,
                "total_cards": total_cards,
                "played": r[3] is not None,
            })
        return matches
    finally:
        conn.close()


def _get_total_jornadas(season_code: str, conn) -> int:
    """Calculate total jornadas for a season based on match count.

    La Liga: 20 teams -> 38 jornadas (380 matches).
    If season is incomplete, estimate from available matches.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) FROM matches m
        JOIN seasons s ON m.season_id = s.id
        WHERE s.season_code = %s
        """,
        (season_code,),
    )
    total_matches = cur.fetchone()[0]

    if total_matches == 0:
        return 38

    # 10 matches per jornada in La Liga (20 teams)
    # Use ceiling to handle incomplete last jornada
    return max(1, -(-total_matches // 10))  # ceiling division


def get_latest_jornada(season_code: str) -> int:
    """Get the latest jornada number that has at least 1 match."""
    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.SD_DB_HOST,
        port=settings.SD_DB_PORT,
        database=settings.SD_DB_NAME,
        user=settings.SD_DB_USER,
        password=settings.SD_DB_PASSWORD,
    )
    try:
        total = _get_total_jornadas(season_code, conn)
        return total
    finally:
        conn.close()


def _get_ou_prob(pred: dict, category: str, line: str) -> Optional[float]:
    """Extract over probability from prediction dict."""
    ou = pred.get("predictions", {}).get(f"{category}_over_under", {})
    entry = ou.get(line, {})
    return entry.get("over_prob")


def predict_jornada(
    jornada: int,
    season_code: str = "2526",
    models: Optional[dict] = None,
    builder: Optional[MatchFeatureBuilder] = None,
) -> dict:
    """Predict all matches for a jornada.

    Returns dict with predictions, results, and accuracy summary.
    """
    matches = get_jornada_matches(season_code, jornada)

    if not matches:
        raise ValueError(
            f"No matches found for jornada {jornada} in season {season_code}"
        )

    if models is None:
        models = load_trained_models()

    if builder is None:
        all_matches, advanced, standings = load_all_data()
        builder = MatchFeatureBuilder(all_matches, advanced, standings)

    results = []
    aciertos_winner = 0
    total_played = 0

    for match in matches:
        row = {
            "home_team": match["home_team"],
            "away_team": match["away_team"],
            "match_date": match["match_date"],
            "played": match["played"],
        }

        # Predict
        try:
            pred = predict_match(
                match["home_team"],
                match["away_team"],
                match["match_date"],
                models=models,
                builder=builder,
            )
            w = pred["predictions"]["winner"]
            row["pred_result"] = w["predicted_result"]
            row["home_prob"] = w["home_win_prob"]
            row["draw_prob"] = w["draw_prob"]
            row["away_prob"] = w["away_win_prob"]

            # Goals over/under probabilities
            row["goals_ou"] = pred["predictions"].get("goals_over_under", {})
            # Cards over/under probabilities
            row["cards_ou"] = pred["predictions"].get("cards_over_under", {})

        except Exception as e:
            row["pred_result"] = "ERR"
            row["error"] = str(e)

        # Actual result (if played)
        if match["played"]:
            row["real_result"] = match["result"]
            row["real_score"] = f"{match['home_score']}-{match['away_score']}"
            row["real_goals"] = match["total_goals"]
            row["real_cards"] = match["total_cards"]
            total_played += 1
            if row.get("pred_result") == match["result"]:
                row["hit"] = True
                aciertos_winner += 1
            else:
                row["hit"] = False

        results.append(row)

    return {
        "jornada": jornada,
        "season": season_code,
        "matches": results,
        "played": total_played,
        "hits": aciertos_winner,
        "accuracy": (
            round(aciertos_winner / total_played * 100, 1) if total_played > 0 else None
        ),
        "pending": len(matches) - total_played,
    }


def _fmt_ou(ou_dict: dict, line: str, real_value: Optional[int]) -> str:
    """Format over/under probability for display.

    Returns something like 'O2.5 68% ✓' or 'U2.5 55% ✗'.
    """
    entry = ou_dict.get(line, {})
    over_p = entry.get("over_prob")
    if over_p is None:
        return "?"

    line_f = float(line)
    # Prediction side
    if over_p >= 0.5:
        side = "O"
        prob = over_p
    else:
        side = "U"
        prob = 1 - over_p

    text = f"{side}{line} {prob:.0%}"

    # Check vs actual
    if real_value is not None:
        actual_over = real_value > line_f
        pred_over = over_p >= 0.5
        hit = "✓" if actual_over == pred_over else "✗"
        text += f" {hit}"

    return text


def print_jornada_report(data: dict) -> None:
    """Print formatted jornada prediction report."""
    jornada = data["jornada"]
    season = data["season"]

    print()
    print("=" * 105)
    print(f"  LA LIGA {season} - JORNADA {jornada}")
    print("=" * 105)

    # Played matches
    played = [m for m in data["matches"] if m.get("played")]
    pending = [m for m in data["matches"] if not m.get("played")]

    if played:
        print()
        print(f"  JUGADOS ({len(played)} partidos)")
        print("-" * 105)
        print(
            f"  {'':>2} | {'Local':>20} {'Res':^5} {'Visitante':<20}"
            f" | {'Pred':^4} | {'H':>4} {'D':>4} {'A':>4}"
            f" | {'Goles O/U':^12} | {'Tarj O/U':^12}"
        )
        print("-" * 105)

        goals_hits = 0
        cards_hits = 0
        goals_total = 0
        cards_total = 0

        for m in played:
            hit = "OK" if m.get("hit") else " X"
            score = m.get("real_score", "?-?")
            pred = m.get("pred_result", "?")
            h_p = f"{m.get('home_prob', 0):.0%}" if "home_prob" in m else "?"
            d_p = f"{m.get('draw_prob', 0):.0%}" if "draw_prob" in m else "?"
            a_p = f"{m.get('away_prob', 0):.0%}" if "away_prob" in m else "?"

            # Goals: show O/U 2.5 as primary line
            goals_ou = m.get("goals_ou", {})
            real_goals = m.get("real_goals")
            if goals_ou:
                goals_str = _fmt_ou(goals_ou, "2.5", real_goals)
                # Track accuracy
                entry_25 = goals_ou.get("2.5", {})
                if entry_25 and real_goals is not None:
                    pred_over = entry_25.get("over_prob", 0.5) >= 0.5
                    actual_over = real_goals > 2.5
                    if pred_over == actual_over:
                        goals_hits += 1
                    goals_total += 1
            else:
                goals_str = "?"

            # Cards: show O/U 4.5 as primary line
            cards_ou = m.get("cards_ou", {})
            real_cards = m.get("real_cards")
            if cards_ou:
                cards_str = _fmt_ou(cards_ou, "4.5", real_cards)
                entry_45 = cards_ou.get("4.5", {})
                if entry_45 and real_cards is not None:
                    pred_over = entry_45.get("over_prob", 0.5) >= 0.5
                    actual_over = real_cards > 4.5
                    if pred_over == actual_over:
                        cards_hits += 1
                    cards_total += 1
            else:
                cards_str = "?"

            print(
                f"  {hit:>2} | {m['home_team']:>20} {score:^5} {m['away_team']:<20}"
                f" | {pred:^4} | {h_p:>4} {d_p:>4} {a_p:>4}"
                f" | {goals_str:^12} | {cards_str:^12}"
            )

        print("-" * 105)
        print(
            f"  Aciertos ganador: {data['hits']}/{data['played']}"
            f" ({data['accuracy']:.0f}%)"
        )
        if goals_total > 0:
            print(
                f"  Aciertos goles O/U 2.5: {goals_hits}/{goals_total}"
                f" ({goals_hits / goals_total * 100:.0f}%)"
            )
        if cards_total > 0:
            print(
                f"  Aciertos tarjetas O/U 4.5: {cards_hits}/{cards_total}"
                f" ({cards_hits / cards_total * 100:.0f}%)"
            )

    if pending:
        print()
        print(f"  POR JUGAR ({len(pending)} partidos)")
        print("-" * 105)
        print(
            f"  {'Fecha':<12} | {'Local':>20} {'vs':^4} {'Visitante':<20}"
            f" | {'Pred':^4} | {'H':>4} {'D':>4} {'A':>4}"
            f" | {'Goles':^16} | {'Tarjetas':^16}"
        )
        print("-" * 105)

        for m in pending:
            pred = m.get("pred_result", "?")
            h_p = f"{m.get('home_prob', 0):.0%}" if "home_prob" in m else "?"
            d_p = f"{m.get('draw_prob', 0):.0%}" if "draw_prob" in m else "?"
            a_p = f"{m.get('away_prob', 0):.0%}" if "away_prob" in m else "?"

            goals_ou = m.get("goals_ou", {})
            cards_ou = m.get("cards_ou", {})

            if goals_ou:
                parts = []
                for line in ["1.5", "2.5", "3.5"]:
                    parts.append(_fmt_ou(goals_ou, line, None))
                goals_str = " ".join(parts)
            else:
                goals_str = "?"

            if cards_ou:
                parts = []
                for line in ["3.5", "4.5", "5.5"]:
                    parts.append(_fmt_ou(cards_ou, line, None))
                cards_str = " ".join(parts)
            else:
                cards_str = "?"

            print(
                f"  {m['match_date']:<12} | {m['home_team']:>20} {'vs':^4} {m['away_team']:<20}"
                f" | {pred:^4} | {h_p:>4} {d_p:>4} {a_p:>4}"
                f" | {goals_str:<16} | {cards_str:<16}"
            )

    print()
    print("=" * 105)
    summary_parts = []
    if data["played"]:
        summary_parts.append(f"Jugados: {data['played']} (ganador: {data['accuracy']:.0f}%)")
    if data["pending"]:
        summary_parts.append(f"Pendientes: {data['pending']}")
    print(f"  {' | '.join(summary_parts)}")
    print("=" * 105)
    print()


def main() -> None:
    """CLI entry point."""
    warnings.filterwarnings("ignore")

    parser = argparse.ArgumentParser(
        description="Predict all matches for a La Liga matchday"
    )
    parser.add_argument(
        "--jornada", "-j",
        type=int,
        default=None,
        help="Matchday number (default: latest available)",
    )
    parser.add_argument(
        "--season", "-s",
        type=str,
        default="2526",
        help="Season code (default: 2526)",
    )

    args = parser.parse_args()

    jornada = args.jornada
    if jornada is None:
        jornada = get_latest_jornada(args.season)
        print(f"Auto-detected latest jornada: {jornada}")

    data = predict_jornada(jornada, args.season)
    print_jornada_report(data)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    main()