import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
ODDS_API_KEY = os.getenv('ODDS_API_KEY', '')
API_FOOTBALL_KEY = os.getenv('API_FOOTBALL_KEY', '')

# Algorithm Configuration
DEFAULT_SPORT = os.getenv('DEFAULT_SPORT', 'football')
INITIAL_BANKROLL = float(os.getenv('INITIAL_BANKROLL', 1000))
MAX_BET_PERCENTAGE = float(os.getenv('MAX_BET_PERCENTAGE', 5))
KELLY_FRACTION = float(os.getenv('KELLY_FRACTION', 0.25))

# Football Weights
FOOTBALL_WEIGHTS = {
    'expectedGoals': 0.20,
    'advancedStats': 0.15,
    'teamStrength': 0.12,
    'tacticalMatchup': 0.12,
    'currentForm': 0.10,
    'playerImpact': 0.10,
    'restAndFatigue': 0.08,
    'motivation': 0.06,
    'homeAdvantage': 0.05,
    'externalFactors': 0.02
}

# Football Weights V2 - Enhanced with contextual factors + team quality gap
# V3 update: Added teamQualityGap factor, rebalanced weights
# NOTE: All defined weights (including conditional h2hAnomaly) must sum to ~1.0.
# At runtime, only active factors are used and renormalized dynamically.
FOOTBALL_WEIGHTS_V2 = {
    # Original factors (rebalanced to include quality gap)
    'expectedGoals': 0.12,       # Primary data signal
    'advancedStats': 0.07,       # PPDA, possession, shot accuracy
    'teamStrength': 0.07,        # Elo-based team strength
    'tacticalMatchup': 0.06,     # Formation/style compatibility
    'currentForm': 0.05,         # Recent 5-game form
    'playerImpact': 0.05,        # Key player availability
    'restAndFatigue': 0.04,      # Rest days, fixture congestion
    'motivation': 0.03,          # Title race, relegation battle
    'homeAdvantage': 0.02,       # Base home boost (dampened by quality gap)
    'externalFactors': 0.01,     # Weather, travel

    # NEW: Team Quality Gap - anchors predictions to fundamental quality differences
    'teamQualityGap': 0.10,      # Combines Elo, position, star rating

    # Contextual factors
    'h2hHistorical': 0.04,       # Base H2H weight
    'h2hAnomaly': 0.12,          # Conditional: replaces h2hHistorical (3x weight)
    'possessionQuality': 0.07,   # xG efficiency per possession
    'managerMomentum': 0.04,     # New manager bounce
    'relegationMotivation': 0.04,# Bottom-3 defensive motivation
    'counterAttackEfficiency': 0.04,  # Low-possession counter threat
    'awayDrawFrequency': 0.03,   # Historical away draw patterns
}
# Sum = 1.00 (all weights including conditional h2hAnomaly)

# Conditional factor rules
CONDITIONAL_FACTORS = {
    'h2hAnomaly': {
        'replaces': 'h2hHistorical',
        'weight_multiplier': 3.0,
        'trigger_condition': 'weaker_team_unbeaten_streak >= 3'
    },
    'managerMomentum': {
        'decay_formula': 'baseBoost * (0.85 ^ gamesManaged)',
        'base_boost': 0.08,
        'interim_multiplier': 0.7,
        'min_threshold': 0.01
    }
}

# Weight normalization mode
WEIGHT_NORMALIZATION_MODE = 'dynamic'  # 'dynamic' or 'static'

# =============================================================================
# EPL Team Database (Updated: Feb 2026, GW25)
# Update this periodically with current season data
# =============================================================================
PREMIER_LEAGUE_TEAMS = {
    'Arsenal': {
        'elo': 1800, 'position': 1, 'form': 'WWDWW', 'stars': 5,
        'home_xg_avg': 2.2, 'away_xg_avg': 1.8, 'style': 'attacking',
        'aliases': ['Arsenal FC'],
    },
    'Manchester City': {
        'elo': 1760, 'position': 2, 'form': 'WLWWW', 'stars': 5,
        'home_xg_avg': 2.3, 'away_xg_avg': 1.9, 'style': 'attacking',
        'aliases': ['Man City', 'Man. City'],
    },
    'Aston Villa': {
        'elo': 1720, 'position': 3, 'form': 'WWDWL', 'stars': 4,
        'home_xg_avg': 1.8, 'away_xg_avg': 1.4, 'style': 'balanced',
        'aliases': ['Villa', 'Aston Villa FC'],
    },
    'Manchester United': {
        'elo': 1700, 'position': 4, 'form': 'WDWWD', 'stars': 4,
        'home_xg_avg': 1.7, 'away_xg_avg': 1.3, 'style': 'balanced',
        'aliases': ['Man United', 'Man Utd', 'Man. United'],
    },
    'Chelsea': {
        'elo': 1690, 'position': 5, 'form': 'WWDLW', 'stars': 4,
        'home_xg_avg': 1.9, 'away_xg_avg': 1.5, 'style': 'attacking',
        'aliases': ['Chelsea FC'],
    },
    'Liverpool': {
        'elo': 1680, 'position': 6, 'form': 'WDLWW', 'stars': 5,
        'home_xg_avg': 1.8, 'away_xg_avg': 1.5, 'style': 'attacking',
        'aliases': ['Liverpool FC'],
    },
    'Brentford': {
        'elo': 1640, 'position': 7, 'form': 'WLLWW', 'stars': 3,
        'home_xg_avg': 1.6, 'away_xg_avg': 1.2, 'style': 'attacking',
        'aliases': ['Brentford FC'],
    },
    'Everton': {
        'elo': 1610, 'position': 8, 'form': 'DWDWL', 'stars': 3,
        'home_xg_avg': 1.4, 'away_xg_avg': 1.0, 'style': 'defensive',
        'aliases': ['Everton FC'],
    },
    'Bournemouth': {
        'elo': 1610, 'position': 9, 'form': 'DDDWW', 'stars': 3,
        'home_xg_avg': 1.5, 'away_xg_avg': 1.1, 'style': 'balanced',
        'aliases': ['AFC Bournemouth', 'Bournemouth FC'],
    },
    'Newcastle': {
        'elo': 1610, 'position': 10, 'form': 'WLWDW', 'stars': 4,
        'home_xg_avg': 1.6, 'away_xg_avg': 1.2, 'style': 'balanced',
        'aliases': ['Newcastle United', 'Newcastle Utd'],
    },
    'Sunderland': {
        'elo': 1590, 'position': 11, 'form': 'DWDWL', 'stars': 3,
        'home_xg_avg': 1.3, 'away_xg_avg': 1.0, 'style': 'defensive',
        'aliases': ['Sunderland AFC'],
    },
    'Fulham': {
        'elo': 1570, 'position': 12, 'form': 'WLWLD', 'stars': 3,
        'home_xg_avg': 1.4, 'away_xg_avg': 1.1, 'style': 'balanced',
        'aliases': ['Fulham FC'],
    },
    'Crystal Palace': {
        'elo': 1550, 'position': 13, 'form': 'DWDLW', 'stars': 3,
        'home_xg_avg': 1.3, 'away_xg_avg': 1.0, 'style': 'balanced',
        'aliases': ['C. Palace', 'Palace'],
    },
    'Brighton': {
        'elo': 1540, 'position': 14, 'form': 'DLDWD', 'stars': 3,
        'home_xg_avg': 1.5, 'away_xg_avg': 1.2, 'style': 'attacking',
        'aliases': ['Brighton & Hove Albion', 'Brighton and Hove Albion', 'Brighton FC'],
    },
    'Leeds United': {
        'elo': 1520, 'position': 15, 'form': 'DLLWD', 'stars': 3,
        'home_xg_avg': 1.3, 'away_xg_avg': 0.9, 'style': 'balanced',
        'aliases': ['Leeds', 'Leeds Utd'],
    },
    'Tottenham': {
        'elo': 1510, 'position': 16, 'form': 'LLDLW', 'stars': 4,
        'home_xg_avg': 1.4, 'away_xg_avg': 1.1, 'style': 'balanced',
        'aliases': ['Tottenham Hotspur', 'Spurs', 'Tottenham FC'],
    },
    'Nottingham': {
        'elo': 1470, 'position': 17, 'form': 'DLLDW', 'stars': 3,
        'home_xg_avg': 1.2, 'away_xg_avg': 0.8, 'style': 'defensive',
        'aliases': ['Nottingham Forest', 'Nott\'m Forest', 'Nottm Forest'],
    },
    'West Ham': {
        'elo': 1440, 'position': 18, 'form': 'WDLLL', 'stars': 3,
        'home_xg_avg': 1.1, 'away_xg_avg': 0.9, 'style': 'defensive',
        'aliases': ['West Ham United', 'West Ham Utd'],
    },
    'Burnley': {
        'elo': 1380, 'position': 19, 'form': 'LLLLD', 'stars': 2,
        'home_xg_avg': 1.0, 'away_xg_avg': 0.8, 'style': 'defensive',
        'aliases': ['Burnley FC'],
    },
    'Wolverhampton': {
        'elo': 1320, 'position': 20, 'form': 'LLDLL', 'stars': 2,
        'home_xg_avg': 0.9, 'away_xg_avg': 0.7, 'style': 'defensive',
        'aliases': ['Wolverhampton Wanderers', 'Wolves', 'Wolverhampton W.'],
    },
}

def lookup_team(team_name: str) -> dict:
    """Look up team data by name or alias. Returns None if not found."""
    name_lower = team_name.strip().lower()
    for canonical_name, data in PREMIER_LEAGUE_TEAMS.items():
        if canonical_name.lower() == name_lower:
            return {**data, 'canonical_name': canonical_name}
        for alias in data.get('aliases', []):
            if alias.lower() == name_lower:
                return {**data, 'canonical_name': canonical_name}
    return None
