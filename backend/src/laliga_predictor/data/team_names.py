"""
Team name normalization across data sources.

Maps variant team names from FBref and MatchHistory (Football-Data.co.uk)
to canonical team names used in the database.

Covers all La Liga teams from 2017-2018 to 2024-2025 seasons,
including promoted/relegated teams.
"""

# Canonical name -> { source: source_name }
# Add new teams here as they appear in the data sources.
TEAM_NAME_MAP: dict[str, dict[str, str]] = {
    # --- Current La Liga teams (2024-2025) ---
    "Athletic Club": {
        "fbref": "Athletic Club",
        "match_history": "Ath Bilbao",
        "espn": "Athletic Club",
    },
    "Atletico Madrid": {
        "fbref": "Atlético Madrid",
        "match_history": "Ath Madrid",
        "espn": "Atlético Madrid",
    },
    "Barcelona": {
        "fbref": "Barcelona",
        "match_history": "Barcelona",
        "espn": "Barcelona",
    },
    "Real Betis": {
        "fbref": "Real Betis",
        "match_history": "Betis",
        "espn": "Real Betis",
    },
    "Celta Vigo": {
        "fbref": "Celta Vigo",
        "match_history": "Celta",
        "espn": "Celta Vigo",
    },
    "Deportivo Alaves": {
        "fbref": "Deportivo Alavés",
        "match_history": "Alaves",
        "espn": "Alavés",
    },
    "Espanyol": {
        "fbref": "Espanyol",
        "match_history": "Espanol",
        "espn": "Espanyol",
    },
    "Getafe": {
        "fbref": "Getafe",
        "match_history": "Getafe",
        "espn": "Getafe",
    },
    "Girona": {
        "fbref": "Girona",
        "match_history": "Girona",
        "espn": "Girona",
    },
    "Las Palmas": {
        "fbref": "Las Palmas",
        "match_history": "Las Palmas",
        "espn": "Las Palmas",
    },
    "Leganes": {
        "fbref": "Leganés",
        "match_history": "Leganes",
        "espn": "Leganés",
    },
    "Mallorca": {
        "fbref": "Mallorca",
        "match_history": "Mallorca",
        "espn": "Mallorca",
    },
    "Osasuna": {
        "fbref": "Osasuna",
        "match_history": "Osasuna",
        "espn": "Osasuna",
    },
    "Rayo Vallecano": {
        "fbref": "Rayo Vallecano",
        "match_history": "Vallecano",
        "espn": "Rayo Vallecano",
    },
    "Real Madrid": {
        "fbref": "Real Madrid",
        "match_history": "Real Madrid",
        "espn": "Real Madrid",
    },
    "Real Sociedad": {
        "fbref": "Real Sociedad",
        "match_history": "Sociedad",
        "espn": "Real Sociedad",
    },
    "Real Valladolid": {
        "fbref": "Real Valladolid",
        "match_history": "Valladolid",
        "espn": "Real Valladolid",
    },
    "Sevilla": {
        "fbref": "Sevilla",
        "match_history": "Sevilla",
        "espn": "Sevilla",
    },
    "Valencia": {
        "fbref": "Valencia",
        "match_history": "Valencia",
        "espn": "Valencia",
    },
    "Villarreal": {
        "fbref": "Villarreal",
        "match_history": "Villarreal",
        "espn": "Villarreal",
    },
    # --- Relegated / promoted teams (2017-2024) ---
    "Almeria": {
        "fbref": "Almería",
        "match_history": "Almeria",
        "espn": "Almería",
    },
    "Cadiz": {
        "fbref": "Cádiz",
        "match_history": "Cadiz",
        "espn": "Cádiz",
    },
    "Eibar": {
        "fbref": "Eibar",
        "match_history": "Eibar",
        "espn": "Eibar",
    },
    "Elche": {
        "fbref": "Elche",
        "match_history": "Elche",
        "espn": "Elche",
    },
    "Granada": {
        "fbref": "Granada",
        "match_history": "Granada",
        "espn": "Granada",
    },
    "Huesca": {
        "fbref": "Huesca",
        "match_history": "Huesca",
        "espn": "Huesca",
    },
    "Levante": {
        "fbref": "Levante",
        "match_history": "Levante",
        "espn": "Levante",
    },
    "Deportivo La Coruna": {
        "fbref": "Deportivo La Coruña",
        "match_history": "La Coruna",
        "espn": "Deportivo La Coruña",
    },
    "Malaga": {
        "fbref": "Málaga",
        "match_history": "Malaga",
        "espn": "Málaga",
    },
    "Real Oviedo": {
        "fbref": "Real Oviedo",
        "match_history": "Oviedo",
        "espn": "Real Oviedo",
    },
    "Racing Santander": {
        "fbref": "Racing Santander",
        "match_history": "Santander",
    },
}

# Cache for reverse lookups
_reverse_cache: dict[str, dict[str, str]] = {}


def build_reverse_lookup(source: str) -> dict[str, str]:
    """Build source_name -> canonical_name lookup for a given source.

    Args:
        source: Data source identifier ('fbref' or 'match_history')

    Returns:
        Dictionary mapping source-specific names to canonical names.
    """
    if source in _reverse_cache:
        return _reverse_cache[source]

    lookup: dict[str, str] = {}
    for canonical, sources in TEAM_NAME_MAP.items():
        if source in sources:
            lookup[sources[source]] = canonical
    _reverse_cache[source] = lookup
    return lookup


def normalize_team_name(name: str, source: str) -> str:
    """Convert a source-specific team name to canonical name.

    Args:
        name: Team name as it appears in the source data.
        source: Data source identifier ('fbref' or 'match_history').

    Returns:
        Canonical team name.

    Raises:
        KeyError: If the team name is not found in the mapping.
    """
    lookup = build_reverse_lookup(source)

    if name in lookup:
        return lookup[name]

    # Try case-insensitive and stripped match
    name_clean = name.strip()
    for source_name, canonical in lookup.items():
        if source_name.lower() == name_clean.lower():
            return canonical

    raise KeyError(
        f"Unknown team name '{name}' for source '{source}'. "
        f"Add it to TEAM_NAME_MAP in team_names.py"
    )


def get_all_canonical_names() -> list[str]:
    """Return all canonical team names."""
    return list(TEAM_NAME_MAP.keys())
