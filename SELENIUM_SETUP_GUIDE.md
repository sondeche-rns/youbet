# 🚀 Selenium Setup Guide for Jackpot Scraping

Quick guide to get Selenium working for live jackpot data scraping.

## Prerequisites

- Python 3.8+
- Chrome or Chromium browser

## Installation Steps

### 1. Install Python Dependencies

```bash
cd betting-algorithm
pip install -r requirements.txt
```

This installs:
- `selenium>=4.16.0`
- `webdriver-manager>=4.0.1`
- `pytest>=7.4.0`
- All other required packages

### 2. Install Chrome/Chromium

#### Windows (WSL)
```bash
# Install Chromium
sudo apt update
sudo apt install chromium-browser chromium-chromedriver

# Or just let webdriver-manager handle it automatically
# It will download ChromeDriver when needed
```

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install chromium-browser chromium-chromedriver
```

#### macOS
```bash
brew install chromium
```

### 3. Verify Installation

```bash
cd betting-algorithm/src
python jackpot_fetcher.py
```

You should see:
```
======================================================================
Fetching SportPesa Mega Jackpot...
======================================================================
✅ Chrome WebDriver initialized successfully
🌐 Fetching: https://www.ke.sportpesa.com/en/mega-jackpot-pro
✅ Page loaded successfully
```

## Running Tests

```bash
cd betting-algorithm
pytest tests/test_jackpot_fetcher.py -v
```

Expected output:
```
tests/test_jackpot_fetcher.py::TestFetcherInitialization::test_init_with_selenium_disabled PASSED
tests/test_jackpot_fetcher.py::TestSampleData::test_fetch_sportpesa_mega_without_selenium PASSED
...
============================== 30 passed in 5.23s ==============================
```

## Troubleshooting

### Issue: ChromeDriver version mismatch

**Solution:** `webdriver-manager` handles this automatically. If you installed chromedriver manually, uninstall it:
```bash
sudo apt remove chromium-chromedriver
pip install --upgrade webdriver-manager
```

### Issue: Chrome not found in WSL

**Solution:** Install Chromium:
```bash
sudo apt install chromium-browser
```

Or use the Windows Chrome installation from WSL:
```python
# In your code, specify Chrome path
from selenium.webdriver.chrome.service import Service
service = Service('/mnt/c/Program Files/Google/Chrome/Application/chrome.exe')
```

### Issue: Permission denied

**Solution:** Fix permissions:
```bash
sudo chmod +x /usr/bin/chromedriver
```

### Issue: Headless mode not working

**Solution:** Try non-headless mode for debugging:
```python
fetcher = JackpotFetcher(use_selenium=True, headless=False)
```

## Configuration Options

### Basic Usage
```python
from jackpot_fetcher import JackpotFetcher

# Default (Selenium enabled, headless)
fetcher = JackpotFetcher()

# Custom configuration
fetcher = JackpotFetcher(
    use_selenium=True,   # Enable Selenium
    headless=True,       # Run in background
    timeout=30           # 30 second timeout
)
```

### Advanced Configuration
```python
# Disable Selenium (use sample data only)
fetcher = JackpotFetcher(use_selenium=False)

# Longer timeout for slow connections
fetcher = JackpotFetcher(timeout=60)

# Non-headless for debugging
fetcher = JackpotFetcher(headless=False)
```

## Performance Tips

1. **Use headless mode** for production (faster)
2. **Cache results** - don't fetch more than once per 5 minutes
3. **Set appropriate timeout** based on your connection
4. **Monitor logs** to identify issues early

## Security Notes

- The fetcher uses a realistic User-Agent
- Built-in delays prevent rate limiting
- No authentication credentials stored
- All data is public information

## Next Steps

1. ✅ Verify installation
2. ✅ Run tests
3. ✅ Test live scraping
4. ✅ Integrate with your application

See [JACKPOT_SCRAPING_NOTE.md](./JACKPOT_SCRAPING_NOTE.md) for detailed usage examples.
