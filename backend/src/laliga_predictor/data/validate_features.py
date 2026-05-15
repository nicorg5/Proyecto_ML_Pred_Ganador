"""
Simple feature validation without Great Expectations.

Validates features.parquet before training models.
Exit code 0 if all checks pass, 1 if any fail.
"""

import sys
from pathlib import Path

import pandas as pd

# Required columns for features
REQUIRED_COLUMNS = {
    "match_id",
    "match_date",
    "home_team",
    "away_team",
    "season_code",
    "target_result",
    "target_total_goals",
    "target_total_cards",
}


def validate_features(features_path: str = "data/processed/features.parquet") -> bool:
    """Validate features.parquet file.

    Args:
        features_path: Path to features.parquet

    Returns:
        True if all validations pass, False otherwise
    """
    print(f"🔍 Validating {features_path}...")

    # Check file exists
    if not Path(features_path).exists():
        print(f"❌ File does not exist: {features_path}")
        return False

    # Load features
    try:
        df = pd.read_parquet(features_path)
    except Exception as e:
        print(f"❌ Failed to load parquet: {e}")
        return False

    errors = []

    # Validation 1: Required columns exist
    missing_cols = REQUIRED_COLUMNS - set(df.columns)
    if missing_cols:
        errors.append(f"Missing required columns: {missing_cols}")

    # Validation 2: DataFrame not empty
    if df.empty:
        errors.append("DataFrame is empty")
        print("❌ Validation FAILED:")
        for error in errors:
            print(f"   - {error}")
        return False

    # Validation 3: Column count reasonable (140-160 features expected)
    n_cols = len(df.columns)
    if not (135 <= n_cols <= 160):
        errors.append(f"Expected 135-160 columns, got {n_cols}")

    # Validation 4: No nulls in critical columns
    critical_cols = ["target_result", "home_team", "away_team", "match_date"]
    for col in critical_cols:
        if col in df.columns:
            null_count = df[col].isnull().sum()
            if null_count > 0:
                errors.append(f"{col} has {null_count} null values")

    # Validation 5: Result values valid
    if "target_result" in df.columns:
        valid_results = {"H", "D", "A"}
        invalid = set(df["target_result"].dropna().unique()) - valid_results
        if invalid:
            errors.append(f"Invalid result values: {invalid}")

    # Validation 6: Target values reasonable
    if "target_total_goals" in df.columns:
        max_goals = df["target_total_goals"].max()
        min_goals = df["target_total_goals"].min()
        if min_goals < 0 or max_goals > 15:
            errors.append(f"target_total_goals has unrealistic range: [{min_goals}, {max_goals}]")

    if "target_total_cards" in df.columns:
        max_cards = df["target_total_cards"].max()
        min_cards = df["target_total_cards"].min()
        if min_cards < 0 or max_cards > 20:
            errors.append(f"target_total_cards has unrealistic range: [{min_cards}, {max_cards}]")

    # Validation 7: Win/rate columns in [0, 1]
    rate_cols = [c for c in df.columns if "win_rate" in c or "draw_rate" in c]
    for col in rate_cols:
        min_val = df[col].min()
        max_val = df[col].max()
        if min_val < 0 or max_val > 1:
            errors.append(f"{col} has values outside [0, 1]: [{min_val}, {max_val}]")

    # Validation 8: League positions in [1, 20]
    position_cols = [c for c in df.columns if "league_position" in c]
    for col in position_cols:
        min_val = df[col].min()
        max_val = df[col].max()
        if min_val < 1 or max_val > 20:
            errors.append(f"{col} has values outside [1, 20]: [{min_val}, {max_val}]")

    # Validation 9: At least 300 rows (3+ seasons with ~100+ matches each)
    if len(df) < 300:
        errors.append(f"Too few rows: {len(df)} < 300")

    # Validation 10: Seasons cover expected range
    if "season_code" in df.columns:
        seasons = set(df["season_code"].unique())
        # Expect at least 7-8 seasons: 1718 to 2526
        if len(seasons) < 7:
            errors.append(f"Too few unique seasons: {len(seasons)} < 7")

    # Print results
    if errors:
        print("❌ Validation FAILED:")
        for error in errors:
            print(f"   - {error}")
        return False

    # Success
    print("✅ Validation PASSED")
    print(f"   - {len(df)} rows")
    print(f"   - {len(df.columns)} columns")
    if "season_code" in df.columns:
        print(f"   - {len(df['season_code'].unique())} seasons")
    print("   - All critical checks passed")
    return True


if __name__ == "__main__":
    features_path = sys.argv[1] if len(sys.argv) > 1 else "data/processed/features.parquet"
    success = validate_features(features_path)
    sys.exit(0 if success else 1)
