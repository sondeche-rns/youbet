# 🔧 Selenium Troubleshooting Guide

## Common Issue: ChromeDriver Status Code 127

### Symptom
```
ERROR: ❌ Failed to create Chrome driver: Message: Service /home/prototypus/.wdm/drivers/chromedriver/linux64/114.0.5735.90/chromedriver unexpectedly exited. Status code was: 127
```

### Cause
Status code 127 means "command not found" - ChromeDriver needs additional system libraries that are missing.

### Solution: Install Missing Dependencies

#### Ubuntu/WSL (Recommended)

**For Ubuntu 22.04+ / 24.04+ (Modern versions):**
```bash
# Update package list
sudo apt update

# Install Chrome/Chromium and MINIMAL required dependencies
sudo apt install -y \
    chromium-browser \
    libnss3 \
    libglib2.0-0 \
    libfontconfig1 \
    libgbm1

# Optional but recommended for better compatibility
sudo apt install -y \
    fonts-liberation \
    xdg-utils \
    libxss1

# Verify installation
chromium-browser --version
```

**For Ubuntu 20.04 and older:**
```bash
sudo apt update
sudo apt install -y \
    chromium-browser \
    libnss3 \
    libglib2.0-0 \
    libfontconfig1

# Verify installation
chromium-browser --version
```

**Note:** Packages like `libgconf-2-4`, `libpango1.0-0`, and `chromium-chromedriver` are deprecated in Ubuntu 24.04+.

#### Alternative: Install Chrome Stable
```bash
# Download Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb

# Install
sudo apt install -y ./google-chrome-stable_current_amd64.deb

# Install additional dependencies
sudo apt install -y \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    libxss1 \
    libappindicator3-1

# Clean up
rm google-chrome-stable_current_amd64.deb
```

### Verify Fix

After installing dependencies, test the fetcher:

```bash
cd betting-algorithm/src
python3 jackpot_fetcher.py
```

**Expected output:**
```
✅ Chrome WebDriver initialized successfully
🌐 Fetching: https://www.ke.sportpesa.com/en/mega-jackpot-pro
✅ Page loaded successfully
```

---

## Other Common Issues

### Issue: "Chrome binary not found"

**Solution:**
```bash
# Check if Chrome is installed
which chromium-browser || which google-chrome

# If not found, install:
sudo apt install chromium-browser
```

### Issue: "Permission denied on chromedriver"

**Solution:**
```bash
# Make chromedriver executable
chmod +x ~/.wdm/drivers/chromedriver/*/chromedriver

# Or for system-wide:
sudo chmod +x /usr/bin/chromedriver
```

### Issue: ChromeDriver version mismatch

**Solution:**
```bash
# Clear webdriver-manager cache
rm -rf ~/.wdm

# Reinstall webdriver-manager
pip install --upgrade webdriver-manager

# Run fetcher again (will download correct version)
python3 src/jackpot_fetcher.py
```

### Issue: "Display not found" in WSL

**Solution:**
Ensure you're using headless mode (default):
```python
fetcher = JackpotFetcher(use_selenium=True, headless=True)
```

If you need to see the browser, install X server:
```bash
# Install X server (VcXsrv for Windows)
# Download from: https://sourceforge.net/projects/vcxsrv/

# Set DISPLAY variable
export DISPLAY=:0
```

### Issue: Network timeout

**Solution:**
Increase timeout:
```python
fetcher = JackpotFetcher(use_selenium=True, timeout=60)
```

### Issue: Still getting sample data

**Possible causes:**
1. Website structure changed
2. Network/firewall blocking
3. Website detecting automation

**Debug steps:**
```python
# 1. Run in non-headless mode to see what's happening
fetcher = JackpotFetcher(use_selenium=True, headless=False)

# 2. Check logs carefully
import logging
logging.basicConfig(level=logging.DEBUG)

# 3. Test page load manually
from selenium import webdriver
driver = webdriver.Chrome()
driver.get('https://www.ke.sportpesa.com/en/mega-jackpot-pro')
# Inspect page manually
```

---

## Complete System Check

Run this comprehensive check:

```bash
#!/bin/bash
echo "=== Selenium Setup Check ==="

echo -n "1. Python installed: "
python3 --version || echo "❌ NOT FOUND"

echo -n "2. Pip installed: "
pip3 --version || echo "❌ NOT FOUND"

echo -n "3. Chrome/Chromium installed: "
chromium-browser --version 2>/dev/null || google-chrome --version 2>/dev/null || echo "❌ NOT FOUND"

echo -n "4. ChromeDriver installed: "
chromedriver --version 2>/dev/null || echo "⚠️ Not in PATH (OK if using webdriver-manager)"

echo "5. Python packages:"
pip3 list | grep -E "selenium|webdriver-manager|beautifulsoup4|pytest" || echo "❌ Some packages missing"

echo -n "6. Dependencies installed: "
dpkg -l | grep -q libnss3 && echo "✅ libnss3 found" || echo "❌ libnss3 missing"

echo ""
echo "=== Test Selenium ==="
cd betting-algorithm
python3 -c "from src.jackpot_fetcher import JackpotFetcher; f = JackpotFetcher(use_selenium=True); r = f.fetch_sportpesa_mega_jackpot(); print(f'✅ Success! Data source: {r[\"data_source\"]}')" 2>&1 | tail -5
```

Save as `check_selenium.sh` and run:
```bash
chmod +x check_selenium.sh
./check_selenium.sh
```

---

## Working Configuration Examples

### Minimal Working Setup (Ubuntu/WSL)
```bash
# 1. System packages
sudo apt update
sudo apt install -y chromium-browser libnss3 libgconf-2-4

# 2. Python packages
cd betting-algorithm
pip install -r requirements.txt

# 3. Test
python3 src/jackpot_fetcher.py
```

### Advanced Setup (With All Dependencies)
```bash
# 1. Full system packages
sudo apt update
sudo apt install -y \
    chromium-browser \
    chromium-chromedriver \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    libxss1 \
    libappindicator3-1 \
    libindicator7 \
    libpango1.0-0 \
    fonts-liberation \
    xdg-utils \
    libgbm1 \
    libasound2

# 2. Python packages
cd betting-algorithm
pip install -r requirements.txt

# 3. Verify
python3 -c "from selenium import webdriver; from selenium.webdriver.chrome.service import Service; from webdriver_manager.chrome import ChromeDriverManager; driver = webdriver.Chrome(service=Service(ChromeDriverManager().install())); print('✅ Selenium works!'); driver.quit()"
```

---

## Fallback: Use Sample Data

If you can't get Selenium working, the system still works with sample data:

```python
from src.jackpot_fetcher import JackpotFetcher

# Use sample data only
fetcher = JackpotFetcher(use_selenium=False)
jackpots = fetcher.get_all_current_jackpots()

# Everything works, just uses sample matches instead of live data
```

---

## Platform-Specific Notes

### WSL (Windows Subsystem for Linux)
- ✅ Headless mode works perfectly
- ⚠️ Non-headless requires X server
- ✅ Best for automation

### Ubuntu Native
- ✅ Both headless and non-headless work
- ✅ Easiest setup

### macOS
```bash
# Install via Homebrew
brew install chromium

# Python packages
pip install -r requirements.txt
```

### Docker
```dockerfile
FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    libnss3 \
    libgconf-2-4 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Set headless by default
ENV SELENIUM_HEADLESS=true
```

---

## Quick Fix Commands

### Reset Everything
```bash
# Clear caches
rm -rf ~/.wdm
pip cache purge

# Reinstall
pip uninstall selenium webdriver-manager -y
pip install selenium webdriver-manager

# Reinstall Chrome
sudo apt remove chromium-browser -y
sudo apt autoremove -y
sudo apt install chromium-browser -y
```

### Force Update ChromeDriver
```bash
# Clear old versions
rm -rf ~/.wdm/drivers/chromedriver

# Let webdriver-manager download fresh
python3 -c "from webdriver_manager.chrome import ChromeDriverManager; ChromeDriverManager().install()"
```

---

## Still Having Issues?

### 1. Check Logs
```bash
cd betting-algorithm
python3 src/jackpot_fetcher.py 2>&1 | tee selenium_debug.log
# Review selenium_debug.log for detailed errors
```

### 2. Test Minimal Selenium
```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

try:
    driver = webdriver.Chrome(options=options)
    driver.get('https://www.google.com')
    print(f"✅ Page title: {driver.title}")
    driver.quit()
    print("✅ Selenium is working!")
except Exception as e:
    print(f"❌ Error: {e}")
```

### 3. Contact Support
If still not working, provide:
- OS version: `lsb_release -a`
- Chrome version: `chromium-browser --version`
- Python version: `python3 --version`
- Error logs from step 1

---

## Success Indicators

✅ **Working correctly:**
```
INFO: ✅ Chrome WebDriver initialized successfully
INFO: 🌐 Fetching: https://www.ke.sportpesa.com/en/mega-jackpot-pro
INFO: ✅ Page loaded successfully (125384 bytes)
INFO: 📊 Data Source: selenium
```

❌ **Not working (using fallback):**
```
ERROR: ❌ Failed to create Chrome driver
WARNING: Failed to fetch page with Selenium, using sample data
INFO: [INFO] Using sample SportPesa Mega Jackpot data (17 matches)
INFO: 📊 Data Source: sample
```

The system still works even when Selenium fails - it just uses sample data instead of live data.
