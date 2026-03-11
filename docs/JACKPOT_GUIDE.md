# 🎰 Kenyan Jackpot System Guide

Complete guide for using the AI betting algorithm to predict and win Kenyan betting jackpots (SportPesa, Betika).

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Supported Jackpots](#supported-jackpots)
3. [How It Works](#how-it-works)
4. [Quick Start](#quick-start)
5. [API Usage](#api-usage)
6. [Data Collection & History](#data-collection--history)
7. [Performance Tracking](#performance-tracking)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The Jackpot System automatically:
- ✅ Fetches current jackpot matches from SportPesa and Betika
- ✅ Generates AI predictions for all matches
- ✅ Calculates optimal betting combinations
- ✅ Tracks historical performance
- ✅ Saves all data for algorithm refinement

### Why This Matters

Kenyan jackpots offer **multi-million shilling prizes** (KSh 100M+) for relatively small stakes (KSh 99). By:
1. Using AI predictions instead of gut feelings
2. Tracking historical performance
3. Refining the algorithm based on results
4. Using statistical analysis for combinations

You can significantly improve your chances of winning.

---

## Supported Jackpots

### SportPesa

| Jackpot | Matches | Prize (Typical) | Entry | Day |
|---------|---------|-----------------|-------|-----|
| **Mega Jackpot** | 17 | KSh 100M+ | KSh 99 | Saturday |
| **Midweek Jackpot** | 13 | KSh 30M+ | KSh 99 | Wednesday |

**Bonus Structure:**
- 17/17 correct: Full jackpot
- 16/17 correct: ~KSh 500K bonus
- 15/17 correct: ~KSh 100K bonus
- 12-14/17: Smaller bonuses

### Betika

| Jackpot | Matches | Prize (Typical) | Entry | Day |
|---------|---------|-----------------|-------|-----|
| **Mega Jackpot** | 15 | KSh 100M+ | KSh 49 | Varies |
| **Mid-week Jackpot** | 13 | KSh 10M+ | KSh 49 | Wednesday |

---

## How It Works

### 1. Data Fetching (Web Scraping)

```
┌─────────────────┐
│ Betting Website │
│  (SportPesa)    │
└────────┬────────┘
         │
         │ Web Scraper
         ▼
┌─────────────────┐
│ Jackpot Fetcher │
│  - Team names   │
│  - Match dates  │
│  - Prize amount │
└────────┬────────┘
         │
         │ JSON Data
         ▼
   [Storage & Analysis]
```

### 2. AI Prediction

For each match, the algorithm:
1. Analyzes team strength (Elo ratings)
2. Calculates expected goals (Poisson model)
3. Considers form, home advantage, motivation
4. Blends market odds (if available)
5. Outputs probabilities: Home/Draw/Away

### 3. Combination Generation

Generates multiple betting strategies:
- **Main Prediction**: All matches (highest probability)
- **Conservative**: High-confidence picks only
- **Value Bets**: Focus on likely draws
- **Banker Bets**: Mix of sure picks + doubles

### 4. Historical Tracking

After each jackpot:
1. Record actual results
2. Calculate accuracy
3. Update performance stats
4. Refine algorithm based on errors

---

## Quick Start

### Step 1: Fetch Current Jackpots

```bash
cd betting-algorithm
python -c "
from src.jackpot_fetcher import JackpotFetcher

fetcher = JackpotFetcher()
jackpots = fetcher.get_all_current_jackpots()

print(f'Found {len(jackpots)} jackpots')
for jp in jackpots:
    print(f'{jp[\"provider\"]} - {jp[\"type\"]}: {len(jp[\"matches\"])} matches')
"
```

### Step 2: Generate Predictions

```bash
python -c "
from src.jackpot_fetcher import JackpotFetcher
from src.jackpot_analyzer import JackpotAnalyzer

# Fetch jackpots
fetcher = JackpotFetcher()
jackpots = fetcher.get_all_current_jackpots()

# Analyze first jackpot
analyzer = JackpotAnalyzer()
analysis = analyzer.analyze_jackpot(jackpots[0])

print(f'Average confidence: {analysis[\"average_confidence\"]*100:.1f}%')
print(f'High confidence picks: {analysis[\"high_confidence_count\"]}')
"
```

### Step 3: View Predictions

Check the generated files:
- **Predictions**: `data/jackpot_predictions/[jackpot_id].json`
- **CSV Format**: `data/jackpot_predictions/[jackpot_id].csv`

### Step 4: Record Results (After Matches)

```bash
python -c "
from src.jackpot_analyzer import JackpotAnalyzer

analyzer = JackpotAnalyzer()

# Example: Record results for a jackpot
results = [
    {'match_number': 1, 'actual_result': 'Home'},
    {'match_number': 2, 'actual_result': 'Draw'},
    {'match_number': 3, 'actual_result': 'Away'},
    # ... all matches
]

analyzer.record_jackpot_results('sportpesa_mega_jackpot_20260211_143022', results)
"
```

---

## API Usage

### Fetch Jackpots

```bash
curl -X POST http://localhost:5000/api/jackpots/fetch \
  -H "Content-Type: application/json" \
  -d '{"providers": ["sportpesa", "betika"]}'
```

**Response:**
```json
{
  "success": true,
  "jackpots": [
    {
      "provider": "SportPesa",
      "type": "Mega Jackpot",
      "matches_count": 17,
      "prize_amount": "KSh 111,367,995",
      "matches": [...]
    }
  ],
  "count": 2
}
```

### Analyze Jackpot

```bash
curl -X POST http://localhost:5000/api/jackpots/analyze \
  -H "Content-Type: application/json" \
  -d @jackpot_data.json
```

**Response:**
```json
{
  "success": true,
  "analysis": {
    "jackpot_id": "sportpesa_mega_jackpot_20260211_143022",
    "total_matches": 17,
    "average_confidence": 0.689,
    "high_confidence_count": 8,
    "predictions": [...],
    "recommended_combinations": [...]
  }
}
```

### Record Results

```bash
curl -X POST http://localhost:5000/api/jackpots/results \
  -H "Content-Type: application/json" \
  -d '{
    "jackpot_id": "sportpesa_mega_jackpot_20260211_143022",
    "results": [
      {"match_number": 1, "actual_result": "Home"},
      {"match_number": 2, "actual_result": "Draw"}
    ]
  }'
```

### Get Performance Stats

```bash
curl http://localhost:5000/api/jackpots/performance
```

**Response:**
```json
{
  "stats": {
    "total_jackpots": 12,
    "average_accuracy": 0.706,
    "best_accuracy": 0.824,
    "worst_accuracy": 0.588,
    "by_provider": {
      "SportPesa": {
        "count": 8,
        "avg_accuracy": 0.715
      },
      "Betika": {
        "count": 4,
        "avg_accuracy": 0.688
      }
    }
  }
}
```

---

## Data Collection & History

### Directory Structure

```
betting-algorithm/
├── data/
│   ├── jackpots/                    # Fetched jackpot data
│   │   ├── jackpot_history.csv      # Master CSV of all jackpots
│   │   ├── sportpesa_mega_*.json    # Individual jackpot files
│   │   └── betika_jackpot_*.json
│   │
│   ├── jackpot_predictions/         # AI predictions
│   │   ├── [jackpot_id].json        # Full analysis
│   │   └── [jackpot_id].csv         # Predictions in CSV
│   │
│   └── jackpot_results/             # Actual results
│       ├── jackpot_results_summary.csv
│       └── [jackpot_id]_results.json
```

### Viewing History

```python
from src.jackpot_fetcher import JackpotFetcher
import pandas as pd

fetcher = JackpotFetcher()

# Get all jackpot history
history = fetcher.get_jackpot_history()
print(history)

# Filter by provider
sportpesa_only = fetcher.get_jackpot_history(provider='SportPesa')

# Filter by type
mega_only = fetcher.get_jackpot_history(jackpot_type='Mega Jackpot')
```

---

## Performance Tracking

### View Overall Performance

```python
from src.jackpot_analyzer import JackpotAnalyzer

analyzer = JackpotAnalyzer()
stats_df = analyzer.get_performance_stats()

# Output:
# Total Jackpots Analyzed: 12
# Average Accuracy: 70.6%
# Best Performance: 82.4%
# Worst Performance: 58.8%
```

### Analyze Improvement Over Time

```python
import pandas as pd

results = pd.read_csv('data/jackpot_results/jackpot_results_summary.csv')
results['timestamp'] = pd.to_datetime(results['timestamp'])

# Plot accuracy over time
results.plot(x='timestamp', y='accuracy')

# Calculate rolling average
results['rolling_avg'] = results['accuracy'].rolling(5).mean()
```

---

## Best Practices

### 1. **Fetch Jackpots Early**
- SportPesa releases Mega Jackpot on Thursday (for Saturday)
- Midweek Jackpot released Monday (for Wednesday)
- Fetch as soon as available for maximum analysis time

### 2. **Use Multiple Strategies**
- Don't just bet the main prediction
- Consider high-confidence combinations
- Use "banker" strategy (mix sure picks + doubles on uncertain matches)

### 3. **Track Everything**
- Record ALL results, even if you didn't bet
- This data is gold for refining the algorithm
- Look for patterns in misses (e.g., always wrong on draws)

### 4. **Bankroll Management**
- Entry is cheap (KSh 99), but don't chase
- Set weekly limit (e.g., max 2 entries per week)
- Use multiple combinations, not multiple tickets of same picks

### 5. **Continuous Improvement**
- Review missed predictions weekly
- Look for systematic biases
- Adjust algorithm weights based on findings

### 6. **Combination Strategy Example**

For a 17-match jackpot with 8 high-confidence picks:

**Ticket 1** (Main):
- All 17 picks with highest probability

**Ticket 2** (Conservative):
- 8 high-confidence picks as single
- 9 low-confidence as doubles (Home/Draw or Away/Draw)
- Creates ~512 combinations

**Ticket 3** (Value):
- Focus on matches with draw >30%
- Use system bets

---

## Troubleshooting

### Issue: Web Scraping Fails

**Error:** `Could not fetch jackpot`

**Solutions:**
1. Check website is accessible: `curl https://www.ke.sportpesa.com`
2. Website HTML may have changed - update selectors in `jackpot_fetcher.py`
3. Use VPN if site blocks your IP
4. Check internet connection

### Issue: No Matches Extracted

**Error:** `Fetched 0 matches`

**Solutions:**
1. Jackpot may not be released yet (check website manually)
2. HTML structure changed - update `_extract_sportpesa_matches()` method
3. Enable debug mode to see raw HTML

### Issue: Low Prediction Accuracy

**Solutions:**
1. Check if you have enough historical data (run data collection)
2. Review algorithm weights - may need tuning for Kenyan leagues
3. Analyze which match types are failing (home/away/draw)
4. Consider integrating real-time form data

### Issue: API Key Errors (Future)

If sports data APIs are added:
1. Check `.env` file has correct API keys
2. Verify API quota hasn't been exceeded
3. Test API directly with curl

---

## Advanced Usage

### Custom Web Scraper

If you want to scrape other Kenyan betting sites:

```python
from src.jackpot_fetcher import JackpotFetcher
from bs4 import BeautifulSoup

class CustomFetcher(JackpotFetcher):
    def fetch_custom_site(self):
        url = "https://example-betting-site.com/jackpot"
        response = self.requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract matches using custom selectors
        matches = []
        # ... your extraction logic ...

        return {
            'provider': 'CustomSite',
            'type': 'Jackpot',
            'matches': matches
        }
```

### Integration with Mobile Apps

Create a simple API client:

```python
import requests

API_URL = "http://localhost:5000/api"

# Fetch and analyze in one go
response = requests.post(f"{API_URL}/jackpots/fetch")
jackpots = response.json()['jackpots']

for jp in jackpots:
    analysis = requests.post(
        f"{API_URL}/jackpots/analyze",
        json=jp
    ).json()['analysis']

    print(f"\n{jp['provider']} {jp['type']}")
    print(f"Avg Confidence: {analysis['average_confidence']*100:.1f}%")
```

---

## Legal & Ethical Considerations

1. **Terms of Service**: Web scraping may violate betting site ToS. Use responsibly.
2. **Personal Use**: This is for personal betting analytics, not commercial resale.
3. **Responsible Gambling**: Set limits. Gambling should be entertainment, not income.
4. **Age Restriction**: Must be 18+ to bet in Kenya.

---

## Next Steps

1. **Set up automated fetching**: Cron job to fetch jackpots twice weekly
2. **Add notifications**: SMS/Email when new jackpots are available
3. **Build mobile app**: React Native app for on-the-go analysis
4. **Integrate payment**: Auto-place bets via MPESA API (future)

---

## Support & Contributing

- **Issues**: Report bugs on GitHub
- **Improvements**: Submit PRs for better scraping or analysis
- **Data**: Share your jackpot results to improve the algorithm

---

**Good luck and bet responsibly!** 🍀
