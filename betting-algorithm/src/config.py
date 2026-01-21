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
