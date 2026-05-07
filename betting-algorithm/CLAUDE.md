# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies (use venv)
source venv/bin/activate
pip install -r requirements.txt

# Run Flask backend
python app.py          # http://localhost:5000

# Run tests
pytest tests/          # all tests
pytest tests/test_algorithm.py::TestAlgorithm::test_initialization  # single test

# Collect historical data
python src/data_collector.py

# Run backtest
python src/backtest.py

# Validate algorithm v2
python validate_v2.py
```

## Architecture

This is a **Flask REST API** backend for a sports betting analytics platform. The frontend (`templates/index.html`) talks to the Python algorithm via `/api/*` endpoints in `app.py`.

### Prediction pipeline (`src/algorithm.py`)

`ProfessionalBettingAlgorithm.predict_match()` is the core entry point:

1. **Factor calculation** — `_calculate_all_factors()` computes 17 factors split into two groups:
   - *Legacy factors* (10): return plain `dict` with a `score` key — weighted by `FOOTBALL_WEIGHTS_V2` in `config.py`
   - *Contextual factors* (7, v2.0+): return `FactorResult` dataclass from `models.py` — each carries its own dynamic `weight` and a `triggered` boolean (inactive factors contribute zero weight)
2. **Weighted probability** — `_calculate_weighted_probabilities()` normalizes only *active* factor weights at runtime (not a static sum), then derives home/draw/away probabilities via the enhanced draw model in `_calculate_draw_probability()`
3. **Blending** — if market odds are present, model output is blended with bookmaker-implied probs based on `_assess_data_quality()`. Football additionally blends with a Poisson scoreline model (60% Poisson, 40% weighted)
4. **Calibration & recommendation** — Platt scaling then Kelly Criterion staking

### Key source files

| File | Role |
|------|------|
| `src/algorithm.py` | Core `ProfessionalBettingAlgorithm` class |
| `src/config.py` | `FOOTBALL_WEIGHTS_V2`, EPL team database, `lookup_team()` |
| `src/models.py` | `FactorResult`, `MatchContext`, `H2HRecord`, `ManagerInfo` dataclasses |
| `src/context_builder.py` | `MatchContextBuilder` — builds `MatchContext` from historical data + managers.json |
| `src/live_fixtures_fetcher.py` | Fetches upcoming fixtures and live odds (The Odds API, API-Football) |
| `src/jackpot_fetcher.py` | Scrapes SportPesa/Betika jackpot matches (falls back to sample data — JS-rendered sites) |
| `src/jackpot_analyzer.py` | Runs algorithm over jackpot matches; enriches raw team names via `lookup_team()` |
| `src/data_collector.py` | Downloads historical CSV data from football-data.co.uk |
| `src/backtest.py` | Backtesting engine; results written to `results/backtests/` |
| `src/calibration.py` | `CalibrationEngine` — self-improving weight adjustment via recorded prediction history |
| `app.py` | Flask app; jackpot imports are **lazy** (inside endpoint functions) to prevent startup failure |

### Factor weights (V2)

Defined in `FOOTBALL_WEIGHTS_V2` (`config.py`). `h2hAnomaly` and `h2hHistorical` are **mutually exclusive** — when anomaly is triggered (weaker team unbeaten ≥3 H2H games), anomaly takes 0.12 weight and historical drops to 0. All active weights are renormalized dynamically.

### Data flow

- Historical match data: `data/final/historical_dataset.csv` (output of `data_collector.py`)
- Manager database: `data/managers.json`
- Backtest results: `results/backtests/backtest_*.json`
- Jackpot predictions/results: `data/jackpot_predictions/`, `data/jackpot_results/`
- Data source config: `config/data_sources.json`

### Environment variables

Copy `.env.example` to `.env`. Key vars:

| Variable | Purpose |
|----------|---------|
| `ODDS_API_KEY` | The Odds API (live odds, 500 req/month free) |
| `API_FOOTBALL_KEY` | API-Football (live fixtures, 100 req/day free) |
| `KELLY_FRACTION` | Fractional Kelly multiplier (default 0.25) |
| `MAX_BET_PERCENTAGE` | Max stake as % of bankroll (default 5) |

### Team lookup

`config.py` contains `PREMIER_LEAGUE_TEAMS` dict with Elo, position, form, xG, style, and aliases for all 20 EPL teams (updated GW25, Feb 2026). Use `lookup_team(name)` for canonical name resolution — it handles aliases like "Man City", "Spurs", etc.
