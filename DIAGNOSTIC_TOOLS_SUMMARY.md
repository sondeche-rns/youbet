# 🔧 Diagnostic Tools for SportPesa Jackpot Issues

## Overview

Created comprehensive diagnostic tools to identify and fix issues with SportPesa jackpot fetching.

## New Files Created

### 1. `test_jackpot_fetch.py` - Quick Diagnostic Test

**Purpose:** Fast test to check if jackpot fetching is working

**Usage:**
```bash
cd betting-algorithm
python3 test_jackpot_fetch.py --headless
```

**What it does:**
- ✅ Checks if Selenium is available
- ✅ Tests enhanced fetcher
- ✅ Shows what data is returned (live vs sample)
- ✅ Saves results to `debug/test_jackpot_results.json`
- ✅ Provides immediate feedback

**Output:**
```
✅ Fetched 2 jackpot(s)

Jackpot 1: SportPesa - Mega Jackpot Pro 17
Data Source: selenium  ← This is what you want to see
Is Sample Data: False

✅ SUCCESS: Getting live data from SportPesa!
```

---

### 2. `diagnose_sportpesa.py` - Detailed Diagnostic

**Purpose:** Deep inspection of SportPesa page structure

**Usage:**
```bash
cd betting-algorithm
python3 diagnose_sportpesa.py
```

**What it does:**
- 🌐 Loads SportPesa page with Selenium
- 🔍 Tests ALL CSS selectors (carousel, matches, titles, prizes)
- 💾 Saves full page HTML to `debug/sportpesa_page.html`
- 📸 Takes screenshot to `debug/sportpesa_screenshot.png`
- 📊 Lists all CSS classes used on page
- ⚠️ Detects Cloudflare/bot detection
- 💡 Provides specific recommendations

**Output:**
```
4️⃣ Testing Carousel Indicators...
✅ Found 3 indicators: div.carousel-indicators button

5️⃣ Testing Next Button...
✅ Found 1 next button(s): button.carousel-control-next

6️⃣ Testing Jackpot Title...
✅ Found title: 'MEGA JACKPOT PRO 17'

8️⃣ Testing Match Elements...
✅ Found 17 match elements: div.jackpot-match
```

**Files generated:**
- `debug/sportpesa_page.html` - Full HTML for manual inspection
- `debug/sportpesa_screenshot.png` - Screenshot of loaded page
- `debug/test_jackpot_results.json` - Structured results

---

### 3. `DEBUGGING_SPORTPESA.md` - Complete Guide

**Purpose:** Step-by-step troubleshooting guide

**Contents:**
1. **Quick Diagnosis** - Run tests and interpret results
2. **Common Issues** - Specific problems and solutions
3. **Manual Inspection** - How to examine HTML/screenshots
4. **Testing Changes** - Verify fixes work
5. **Success Checklist** - Confirm everything working

**Key sections:**

#### Issue 1: All Jackpots Show "Sample Data"
→ Fix Selenium dependencies with `./fix_selenium.sh`

#### Issue 2: No Matches Found
→ Update CSS selectors in `jackpot_fetcher_enhanced.py`

#### Issue 3: Carousel Not Detected
→ Add new indicator/button selectors

#### Issue 4: Cloudflare/Bot Detection
→ Update Chrome options to appear more like real browser

#### Issue 5: Wrong Prize Amount
→ Update regex patterns for prize extraction

---

## Workflow to Fix SportPesa Issues

### Step 1: Identify the Problem

```bash
cd betting-algorithm
python3 test_jackpot_fetch.py --headless
```

**Look for:**
- ❌ "Data Source: sample" → Selenium not scraping
- ❌ "Actual Matches: 0" → Match selectors wrong
- ❌ "Found 1 jackpot" → Carousel not detected

### Step 2: Run Detailed Diagnostic

```bash
python3 diagnose_sportpesa.py
```

**Check output for:**
- ⚠️ Warnings about missing elements
- ⚠️ Cloudflare/bot detection alerts
- 📊 CSS classes found on page

### Step 3: Inspect Files

```bash
# View HTML
code debug/sportpesa_page.html
# Or: explorer.exe debug/sportpesa_page.html (Windows/WSL)

# View screenshot
explorer.exe debug/sportpesa_screenshot.png
```

**Search HTML for:**
1. Team names → Find match container selectors
2. "jackpot" → Find title element
3. "KSH" or "million" → Find prize element
4. "carousel" or "slide" → Find carousel controls

### Step 4: Update Selectors

Edit `src/jackpot_fetcher_enhanced.py`:

```python
# Line 168-176: Carousel indicators
selectors = [
    'div.carousel-indicators button',  # Bootstrap
    'div.your-new-selector',           # Add yours
]

# Line 198-206: Next button
next_selectors = [
    'button.carousel-control-next',
    'button.your-new-selector',        # Add yours
]

# Line 339-345: Match elements
selectors = [
    'div.jackpot-match',
    'div.your-match-selector',         # Add yours
]
```

### Step 5: Test Changes

```bash
# Test enhanced fetcher directly
python3 src/jackpot_fetcher_enhanced.py

# Or use quick test
python3 test_jackpot_fetch.py --headless
```

### Step 6: Verify End-to-End

```bash
# Backend
python3 app.py &

# Test API
curl -X POST http://localhost:5001/api/jackpots/fetch \
  -H "Content-Type: application/json" \
  -d '{"providers": ["sportpesa"]}'

# Frontend
cd ../betting-frontend
npm start
# Visit http://localhost:4200 → Jackpot page → "Fetch Jackpots"
```

---

## Common Scenarios

### Scenario 1: Selenium Not Working

**Symptoms:**
```
Data Source: sample
Is Sample Data: True
```

**Fix:**
```bash
./fix_selenium.sh
chromium-browser --version  # Verify installed
python3 test_jackpot_fetch.py --headless
```

---

### Scenario 2: Page Structure Changed

**Symptoms:**
```
⚠️  No match elements found
⚠️  No carousel indicators found
```

**Fix:**
1. Run `python3 diagnose_sportpesa.py`
2. Open `debug/sportpesa_page.html`
3. Find new selectors
4. Update `jackpot_fetcher_enhanced.py`
5. Test with `python3 test_jackpot_fetch.py`

---

### Scenario 3: Bot Detection Active

**Symptoms:**
```
⚠️  Cloudflare protection detected
Page loads but no content
```

**Fix:**

Update `jackpot_fetcher_enhanced.py` line 69-80:

```python
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

# More realistic user agent
chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
```

Increase wait times (lines 115, 128):
```python
time.sleep(10)  # Instead of 5
```

---

## Success Indicators

When everything is working:

✅ **Test Output:**
```
✅ Fetched 2+ jackpot(s)
Data Source: selenium
Actual Matches: 17, 13 (or similar)
✅ SUCCESS: Getting live data from SportPesa!
```

✅ **Frontend Display:**
- "🎰 Carousel Navigation Active" banner
- Green "Live Data" badges
- "🌐 Live from Carousel" indicators
- Multiple jackpots visible

✅ **Backend Logs:**
```
🎰 Using Enhanced Fetcher for SportPesa
📊 Found 3 jackpot(s) in carousel
✅ Enhanced fetcher found 3 SportPesa jackpot(s)
```

---

## Quick Command Reference

```bash
# Quick test
python3 test_jackpot_fetch.py --headless

# Detailed diagnostic
python3 diagnose_sportpesa.py

# Fix Selenium
./fix_selenium.sh

# Test enhanced fetcher
python3 src/jackpot_fetcher_enhanced.py

# View debug files
ls -lh debug/
code debug/sportpesa_page.html
explorer.exe debug/sportpesa_screenshot.png

# Test backend API
python3 app.py &
curl -X POST http://localhost:5001/api/jackpots/fetch \
  -H "Content-Type: application/json" \
  -d '{"providers": ["sportpesa"]}'
```

---

## Documentation Links

- [DEBUGGING_SPORTPESA.md](DEBUGGING_SPORTPESA.md) - Full troubleshooting guide
- [CAROUSEL_JACKPOT_GUIDE.md](CAROUSEL_JACKPOT_GUIDE.md) - How carousel navigation works
- [FRONTEND_CAROUSEL_GUIDE.md](FRONTEND_CAROUSEL_GUIDE.md) - Frontend implementation
- [QUICK_START_SELENIUM.md](QUICK_START_SELENIUM.md) - Selenium setup
- [SELENIUM_TROUBLESHOOTING.md](SELENIUM_TROUBLESHOOTING.md) - Selenium-specific issues

---

## Next Steps

1. **Run the quick test** to see current status:
   ```bash
   cd betting-algorithm
   python3 test_jackpot_fetch.py --headless
   ```

2. **If showing sample data**, run diagnostic:
   ```bash
   python3 diagnose_sportpesa.py
   ```

3. **Review findings** in debug files

4. **Update selectors** if needed in `jackpot_fetcher_enhanced.py`

5. **Test and verify** changes work

---

**💡 Pro Tip:** Run `diagnose_sportpesa.py` periodically (weekly/monthly) to catch when SportPesa updates their website before it breaks production.
