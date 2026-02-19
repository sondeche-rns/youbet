# 🚀 Quick Start: Selenium Jackpot Scraping

Get up and running with live jackpot data in 5 minutes!

## Step 1: Install Dependencies (2 minutes)

```bash
cd betting-algorithm
pip install -r requirements.txt
```

This installs everything you need including:
- `selenium` - Browser automation
- `webdriver-manager` - Automatic ChromeDriver management
- `pytest` - Testing framework

## Step 2: Test Without Selenium (30 seconds)

First, verify the system works with sample data:

```bash
cd betting-algorithm/src
python jackpot_fetcher.py
```

**Expected Output:**
```
======================================================================
Fetching SportPesa Mega Jackpot...
======================================================================
Selenium disabled, using sample data
✅ Fetched 17 matches from SportPesa Mega Jackpot
💰 Prize: Unknown
📊 Data Source: sample

SportPesa - Mega Jackpot
Matches: 17
Data Source: sample
First 3 matches:
  1. Arsenal vs Chelsea
  2. Man City vs Liverpool
  3. Tottenham vs Man United
```

✅ If you see this, the basic system works!

## Step 3: Install Chrome & Dependencies (1 minute)

### Ubuntu/WSL (Recommended - Automated)
```bash
cd betting-algorithm
chmod +x fix_selenium.sh
./fix_selenium.sh
```

This script installs:
- Chromium browser
- All required system libraries (libnss3, libgconf, etc.)
- Clears ChromeDriver cache
- Tests that Selenium is working

### Ubuntu/WSL (Manual)
```bash
sudo apt update
# MINIMAL required packages (only these 5 are required)
sudo apt install -y chromium-browser libnss3 libglib2.0-0 libfontconfig1 libgbm1

# Optional but recommended
sudo apt install -y fonts-liberation xdg-utils libxss1
```

### macOS
```bash
brew install chromium
```

### Windows
Download from: https://www.google.com/chrome/

**Note:** `webdriver-manager` will automatically download ChromeDriver!

## Step 4: Test With Selenium (2 minutes)

Now test with live scraping:

```bash
cd betting-algorithm
python -c "from src.jackpot_fetcher import JackpotFetcher; fetcher = JackpotFetcher(use_selenium=True); result = fetcher.fetch_sportpesa_mega_jackpot(); print(f'Data source: {result[\"data_source\"]}')"
```

**Expected Output:**
```
======================================================================
Fetching SportPesa Mega Jackpot...
======================================================================
✅ Chrome WebDriver initialized successfully
🌐 Fetching: https://www.ke.sportpesa.com/en/mega-jackpot-pro
✅ Page loaded successfully (125384 bytes)
[DEBUG] Found 17 elements with selector: div.jackpot-match
[DEBUG] Extracted match 1: Arsenal vs Chelsea
...
✅ Fetched 17 matches from SportPesa Mega Jackpot
💰 Prize: KSh 100,000,000
📊 Data Source: selenium
Data source: selenium
```

✅ If you see `Data source: selenium`, you're getting live data!

## Step 5: Run Tests (1 minute)

Verify everything works:

```bash
cd betting-algorithm
pytest tests/test_jackpot_fetcher.py -v
```

**Expected:**
```
============================== 30 passed in 5.23s ==============================
```

✅ All tests passing = everything is working!

## 🎯 Usage in Your Code

### Basic Example
```python
from src.jackpot_fetcher import JackpotFetcher

# Create fetcher with Selenium
fetcher = JackpotFetcher(use_selenium=True)

# Fetch all jackpots
jackpots = fetcher.get_all_current_jackpots()

# Display results
for jackpot in jackpots:
    print(f"\n{jackpot['provider']} - {jackpot['type']}")
    print(f"Prize: {jackpot.get('prize_amount', 'Unknown')}")
    print(f"Matches: {len(jackpot['matches'])}")
    print(f"Data Source: {jackpot['data_source']}")

    # First 3 matches
    for match in jackpot['matches'][:3]:
        print(f"  {match['match_number']}. {match['home_team']} vs {match['away_team']}")
```

### Integrate with Analyzer
```python
from src.jackpot_fetcher import JackpotFetcher
from src.jackpot_analyzer import JackpotAnalyzer

# Fetch jackpots
fetcher = JackpotFetcher(use_selenium=True)
jackpots = fetcher.get_all_current_jackpots()

# Analyze with AI
analyzer = JackpotAnalyzer()
for jackpot in jackpots:
    analysis = analyzer.analyze_jackpot(jackpot)

    # Display predictions
    print(f"\n{jackpot['provider']} - {jackpot['type']}")
    print(f"Average Confidence: {analysis['average_confidence']*100:.1f}%")
    print(f"High Confidence Picks: {analysis['high_confidence_count']}")
```

## 🔧 Configuration Options

### Use Sample Data (No Selenium)
```python
fetcher = JackpotFetcher(use_selenium=False)
# Always returns sample data
```

### Custom Timeout
```python
fetcher = JackpotFetcher(timeout=60)
# Wait up to 60 seconds for page load
```

### Non-Headless (See Browser)
```python
fetcher = JackpotFetcher(headless=False)
# Opens visible browser window (useful for debugging)
```

## 🎉 Success Checklist

- ✅ Dependencies installed (`pip install -r requirements.txt`)
- ✅ Chrome/Chromium installed
- ✅ Sample data test works
- ✅ Selenium test works (shows `data_source: selenium`)
- ✅ All tests pass (30 tests)
- ✅ Can fetch and analyze jackpots

## ❓ Troubleshooting

### "ChromeDriver exited. Status code was: 127"
**This is the most common error!** It means ChromeDriver is missing system libraries.

**Quick Fix:**
```bash
cd betting-algorithm
./fix_selenium.sh
```

**Manual Fix (Minimal - only 5 packages required):**
```bash
sudo apt install -y chromium-browser libnss3 libglib2.0-0 libfontconfig1 libgbm1
```

See [SELENIUM_TROUBLESHOOTING.md](./SELENIUM_TROUBLESHOOTING.md) for detailed solutions.

### "Selenium not available"
```bash
pip install selenium webdriver-manager
```

### "Chrome driver not found"
```bash
# Let webdriver-manager handle it automatically, or:
sudo apt install chromium-browser
```

### "Permission denied"
```bash
sudo chmod +x /usr/bin/chromedriver
```

### Still returns sample data with Selenium
1. Check logs for specific errors
2. Try increasing timeout: `JackpotFetcher(timeout=60)`
3. Run non-headless to see what's happening: `JackpotFetcher(headless=False)`
4. See detailed troubleshooting: [SELENIUM_TROUBLESHOOTING.md](./SELENIUM_TROUBLESHOOTING.md)

## 📚 More Information

- **Detailed Guide**: [JACKPOT_SCRAPING_NOTE.md](./JACKPOT_SCRAPING_NOTE.md)
- **Setup Guide**: [SELENIUM_SETUP_GUIDE.md](./SELENIUM_SETUP_GUIDE.md)
- **Implementation Details**: [IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)
- **Test Documentation**: [betting-algorithm/tests/README.md](./betting-algorithm/tests/README.md)

## 🎯 Next Steps

1. ✅ Get live jackpot data
2. ✅ Analyze with AI predictions
3. ✅ Review recommendations
4. ✅ Track performance over time

**You're ready to start fetching live jackpot data!** 🚀
