# Data Integration Guide

Complete guide to data sources and API integration.

## Free Data Sources

### Football
- **FBref** - xG and advanced statistics (FREE)
- **Football-Data.co.uk** - Historical odds (FREE)
- **Club Elo** - Team Elo ratings (FREE)
- **StatsBomb Open Data** - Event-level data (FREE)

### Basketball
- **Basketball-Reference** - NBA statistics (FREE)
- **NBA API** - Official NBA data (FREE)

### Tennis
- **Tennis Abstract** - Match results and Elo (FREE)
- **ATP/WTA** - Official statistics (FREE)

### Odds Data
- **The Odds API** - Live odds (500 requests/month FREE)
- **Football-Data.co.uk** - Historical odds (FREE)

## Quick Setup

1. Install dependencies:
```bash
pip install pandas requests beautifulsoup4 soccerdata
```

2. Run data collector:
```bash
python src/data_collector.py
```

For complete API integration guide, see the DATA_INTEGRATION_GUIDE artifact.
