# ⚠️ Selenium Error 127 - QUICK FIX

## You're Seeing This Error:
```
ERROR: ❌ Failed to create Chrome driver: Message: Service /home/prototypus/.wdm/drivers/chromedriver/linux64/114.0.5735.90/chromedriver unexpectedly exited. Status code was: 127
```

## ✅ ONE-LINE FIX:

```bash
cd betting-algorithm && chmod +x fix_selenium.sh && ./fix_selenium.sh
```

This script will:
1. ✅ Install Chromium browser
2. ✅ Install all required system libraries (libnss3, libgconf, etc.)
3. ✅ Clear ChromeDriver cache
4. ✅ Reinstall Python packages
5. ✅ Test that Selenium is working

**Expected output:**
```
🔧 Fixing Selenium Dependencies...
==================================

📦 Updating package list...
📦 Installing Chromium and dependencies...
✅ Dependencies installed successfully

🔍 Verifying Chrome installation...
✅ Chrome installed: Chromium 114.0.5735.90

🧹 Clearing ChromeDriver cache...
✅ Cache cleared

📦 Installing Python dependencies...
✅ Python packages installed

🧪 Testing Selenium...
✅ Selenium is working correctly!
   Test page title: Google

🎉 Success! Selenium is working correctly.
```

---

## Alternative: Manual Fix

If the script doesn't work, run these commands manually:

```bash
# 1. Install MINIMAL required system dependencies (Ubuntu 22.04+/24.04+)
sudo apt update
sudo apt install -y \
    chromium-browser \
    libnss3 \
    libglib2.0-0 \
    libfontconfig1 \
    libgbm1

# Optional but recommended
sudo apt install -y fonts-liberation xdg-utils libxss1

# 2. Clear ChromeDriver cache
rm -rf ~/.wdm/drivers/chromedriver

# 3. Test again
cd betting-algorithm/src
python3 jackpot_fetcher.py
```

**Note:** Only 5 packages are actually required: `chromium-browser`, `libnss3`, `libglib2.0-0`, `libfontconfig1`, and `libgbm1`. Deprecated packages like `libgconf-2-4` are not needed in Ubuntu 24.04+.

---

## Why This Error Happens

**Status code 127** means "command not found" - ChromeDriver is downloaded but can't execute because it needs specific system libraries that aren't installed by default.

Common missing libraries:
- `libnss3` - Network Security Services
- `libgconf-2-4` - Configuration library
- `libfontconfig1` - Font configuration
- `libxss1` - X11 Screen Saver extension

---

## After the Fix

Once fixed, you should see:
```
✅ Chrome WebDriver initialized successfully
🌐 Fetching: https://www.ke.sportpesa.com/en/mega-jackpot-pro
✅ Page loaded successfully
📊 Data Source: selenium
```

Instead of:
```
ERROR: ❌ Failed to create Chrome driver
WARNING: Failed to fetch page with Selenium, using sample data
📊 Data Source: sample
```

---

## Still Not Working?

See detailed troubleshooting guide: [SELENIUM_TROUBLESHOOTING.md](./SELENIUM_TROUBLESHOOTING.md)

Or use sample data mode (no Selenium needed):
```python
from src.jackpot_fetcher import JackpotFetcher
fetcher = JackpotFetcher(use_selenium=False)  # Uses sample data
```

---

## System Requirements

- ✅ Ubuntu/WSL (any version)
- ✅ sudo access (for apt install)
- ✅ Internet connection
- ✅ ~200MB disk space for Chrome + dependencies

---

**Run the fix script now:**
```bash
cd betting-algorithm && ./fix_selenium.sh
```

Then test:
```bash
python3 src/jackpot_fetcher.py
```

🎉 **You should be getting live data!**
