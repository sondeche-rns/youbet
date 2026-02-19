# Bet4Me

A sports betting prediction platform combining a multi-factor algorithm, analytics backend, and Angular frontend.

## Project Structure

```
bet4me/
├── betting-algorithm/       # Core prediction engine (Python)
├── betting-analytics-platform/  # Analytics backend (Flask)
├── betting-frontend/        # Web UI (Angular 19)
└── create_project.py        # Project scaffolding script
```

## Betting Algorithm

The core of the system — a 17-factor football prediction model (V3) with:

- Expected Goals (xG), Elo ratings, tactical matchup analysis
- Team quality gap factor preventing unrealistic upset picks
- Multi-signal draw model (8-40% range, replaces old 25%-cap)
- EPL team database with Elo, positions, form, xG averages
- Jackpot prediction with automatic data enrichment
- Poisson distribution blending and Kelly Criterion staking
- Smart market odds weighting based on data quality

See [betting-algorithm/README.md](betting-algorithm/README.md) for full documentation.

## Frontend

Angular 19 dashboard with:

- Match predictions with factor breakdowns
- Jackpot analysis and multi-bet strategies
- Historical backtesting
- Data collection management
- Algorithm settings configuration

## Quick Start

### Algorithm
```bash
cd betting-algorithm
pip install -r requirements.txt
cp .env.example .env  # Add API keys

# Run tests
python -m pytest tests/ -v

# Run prediction
python -c "
from src.algorithm import ProfessionalBettingAlgorithm
algo = ProfessionalBettingAlgorithm('football')
p = algo.predict_match({'homeTeam': 'Arsenal', 'awayTeam': 'Chelsea', 'competition': 'Premier League'})
print(f\"H:{p['homeWinProb']:.1%} D:{p['drawProb']:.1%} A:{p['awayWinProb']:.1%}\")
"
```

### Frontend
```bash
cd betting-frontend
npm install
ng serve
```

## Branches

| Branch | Purpose |
|--------|---------|
| `main` | Stable release |
| `develop` | Integration branch |
| `feature/autosetup` | Algorithm V2/V3 improvements, jackpot system |
| `feature/betslip` | Betslip and UI features |

## Tech Stack

- **Algorithm**: Python 3.12, NumPy, Pandas, SciPy, Scikit-learn
- **Backend**: Flask, BeautifulSoup (scraping), Soccerdata, Selenium
- **Frontend**: Angular 19, TypeScript, Angular Material, Chart.js
- **Data**: football-data.co.uk, API-Football, The Odds API

## Jackpot Features

### SportPesa Carousel Navigation

The system automatically discovers and fetches **all available SportPesa jackpots** from their carousel interface:

- **Carousel Navigation**: Automatically detects and navigates through all jackpot slides
- **Live Data Scraping**: Uses Selenium to extract real-time jackpot data
- **Visual Indicators**: Frontend displays data source (Live vs Sample) with color-coded badges
- **Graceful Fallback**: Falls back to sample data if Selenium unavailable

**Setup:**
```bash
cd betting-algorithm
./fix_selenium.sh  # Install Selenium dependencies
python3 test_jackpot_fetch.py --headless  # Test if working
```

**Documentation:**
- [Quick Start - Selenium Setup](QUICK_START_SELENIUM.md)
- [Carousel Navigation Guide](CAROUSEL_JACKPOT_GUIDE.md)
- [Frontend Implementation](FRONTEND_CAROUSEL_GUIDE.md)
- [Troubleshooting Guide](DEBUGGING_SPORTPESA.md)

### Troubleshooting Jackpot Fetching

If SportPesa jackpots aren't being retrieved correctly:

```bash
cd betting-algorithm

# 1. Quick diagnostic
python3 test_jackpot_fetch.py --headless

# 2. Detailed diagnostic (saves HTML + screenshot)
python3 diagnose_sportpesa.py

# 3. Fix Selenium dependencies
./fix_selenium.sh

# 4. Check results
python3 src/jackpot_fetcher_enhanced.py
```

**Expected output when working:**
```
✅ Fetched 2 jackpot(s)
Data Source: selenium
✅ SUCCESS: Getting live data from SportPesa!
```

See [DEBUGGING_SPORTPESA.md](DEBUGGING_SPORTPESA.md) for detailed troubleshooting steps.

## Disclaimer

This software is for educational and research purposes only. Sports betting involves risk. Only bet what you can afford to lose. Past performance does not guarantee future results.
