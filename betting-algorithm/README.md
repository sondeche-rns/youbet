# Professional Sports Betting Algorithm

A sophisticated sports prediction algorithm using advanced statistics, machine learning, and market intelligence. Currently focused on football (soccer) with Premier League team data and jackpot prediction support.

## Features

- **17-factor prediction model** (V3) with dynamically normalized weights
- **Team quality gap factor** anchoring predictions to fundamental Elo/position/squad differences
- **Multi-signal draw model** replacing the old 25%-capped formula (now supports 8-40% range)
- **EPL team database** with Elo ratings, league positions, form, xG averages, and star ratings
- **Jackpot prediction** via `JackpotAnalyzer` with automatic data enrichment
- **Expected Goals (xG)** integration with Poisson distribution blending
- **Kelly Criterion** staking system for value betting mode
- **Probability calibration** via Platt scaling
- **Smart market odds weighting** that trusts bookmaker odds more when model data is sparse
- **Home advantage dampening** when the away team is significantly stronger

## Algorithm Versions

| Version | Factors | Key Improvement |
|---------|---------|-----------------|
| V1 | 10 | Base algorithm with xG, Elo, form, tactical matchup |
| V2 | 16 | Added 6 contextual factors (H2H anomaly, possession quality, manager momentum, relegation motivation, counter-attack, away draw frequency) |
| **V3** | **17** | **Added team quality gap, fixed draw model, eliminated home-biased defaults, data enrichment, smart market weighting** |

## V3 Improvements (Feb 2026)

V3 addressed critical issues where the algorithm always picked the home team due to home-biased default values, and capped draw probability at 25%.

| Change | Impact |
|--------|--------|
| EPL team database with Elo/position/form lookup | Predictions now use real team data instead of generic defaults |
| Multi-signal draw probability model | Draw can reach 35%+ for evenly-matched defensive games (was capped at 25%) |
| Neutral defaults | Unknown teams get 50/50 instead of home-biased predictions |
| Team quality gap factor (10% weight) | Prevents picking massive underdogs (e.g., bottom team over top-4) |
| Home advantage dampening | Reduced home boost when away team is 8+ positions higher |
| Data-quality-aware market blending | Trusts bookmaker odds more when detailed stats are unavailable |

**Validation result**: 2/5 correct on Feb 11 EPL matches improved to 3/5, with draw detection dramatically improved (22% to 33%).

## Quick Start

### 1. Install Dependencies
```bash
cd betting-algorithm
pip install -r requirements.txt
```

### 2. Configure API Keys
```bash
cp .env.example .env
# Edit .env with your API keys (ODDS_API_KEY, API_FOOTBALL_KEY)
```

### 3. Run Prediction
```python
from src.algorithm import ProfessionalBettingAlgorithm

algo = ProfessionalBettingAlgorithm('football')
prediction = algo.predict_match({
    'homeTeam': 'Sunderland',
    'awayTeam': 'Liverpool',
    'home_xg': 1.3, 'away_xg': 1.5,
    'home_elo': 1590, 'away_elo': 1680,
    'home_position': 11, 'away_position': 6,
    'homeStarRating': 3, 'awayStarRating': 5,
    'homeOdds': 4.30, 'drawOdds': 3.80, 'awayOdds': 1.80,
    'competition': 'Premier League',
})
print(f"Home: {prediction['homeWinProb']:.1%}")
print(f"Draw: {prediction['drawProb']:.1%}")
print(f"Away: {prediction['awayWinProb']:.1%}")
print(f"Pick: {prediction['recommendation']['outcome']}")
```

### 4. Run Jackpot Analysis
```python
from src.jackpot_analyzer import JackpotAnalyzer

analyzer = JackpotAnalyzer()
analysis = analyzer.analyze_jackpot({
    'provider': 'SportPesa',
    'type': 'Midweek Jackpot',
    'matches': [
        {'match_number': 1, 'home_team': 'Arsenal', 'away_team': 'Chelsea'},
        {'match_number': 2, 'home_team': 'Man City', 'away_team': 'Liverpool'},
    ]
})
```
The `JackpotAnalyzer` automatically enriches match data from the EPL team database before predicting.

### 5. Run Tests
```bash
# All tests
python -m pytest tests/ -v

# V3 improvement tests only
python -m pytest tests/test_v3_improvements.py -v
```

## Project Structure

```
betting-algorithm/
├── src/
│   ├── algorithm.py          # Main 17-factor prediction algorithm
│   ├── config.py             # Weights, EPL team database, configuration
│   ├── models.py             # FactorResult, MatchContext dataclasses
│   ├── context_builder.py    # H2H and season stats context builder
│   ├── calibration.py        # Self-improving weight calibration engine
│   └── jackpot_analyzer.py   # Jackpot prediction with data enrichment
├── data/
│   ├── jackpots/             # Fetched jackpot data (SportPesa, Betika)
│   ├── jackpot_predictions/  # Saved prediction results
│   └── managers.json         # Premier League manager database
├── tests/
│   ├── test_v3_improvements.py     # V3 validation tests (17 factors, draw model)
│   ├── test_contextual_factors.py  # Unit tests for contextual factors
│   └── test_integration_v2.py      # Integration tests
└── results/                  # Backtest and prediction results
```

## Maintaining the Team Database

The EPL team database in `src/config.py` (`PREMIER_LEAGUE_TEAMS`) should be updated periodically with current season data:

```python
# In src/config.py
PREMIER_LEAGUE_TEAMS = {
    'Liverpool': {
        'elo': 1680,            # Update from clubelo.com or similar
        'position': 6,          # Current league position
        'form': 'WDLWW',        # Last 5 results (most recent first)
        'stars': 5,              # Squad quality (1-5)
        'home_xg_avg': 1.8,     # Season home xG average
        'away_xg_avg': 1.5,     # Season away xG average
        'style': 'attacking',   # attacking / balanced / defensive
        'aliases': ['Liverpool FC'],
    },
    # ... all 20 teams
}
```

Update frequency: every 2-4 gameweeks, or before major jackpot rounds.

## Documentation

- **[Weights Documentation](WEIGHTS_DOCUMENTATION.md)** - Factor weights and rationale
- **[Data Integration Guide](DATA_INTEGRATION_GUIDE.md)** - API connections and data collection
- **[Implementation Summary](IMPLEMENTATION_SUMMARY.md)** - Architecture and roadmap

## Disclaimer

This software is for educational and research purposes only. Sports betting involves risk. Only bet what you can afford to lose. Past performance does not guarantee future results.

## License

MIT License - See LICENSE file for details
