# 🔍 Debugging SportPesa Jackpot Fetching

If SportPesa jackpots aren't being retrieved correctly, use this guide to diagnose and fix the issue.

## Quick Diagnosis

### Step 1: Run Quick Test

```bash
cd betting-algorithm
python3 test_jackpot_fetch.py --headless
```

**What this does:**
- Tests if Selenium is working
- Fetches SportPesa jackpots
- Shows what data is returned
- Identifies if you're getting live vs sample data

**Expected output if working:**
```
✅ Fetched 2 jackpot(s)

Jackpot 1: SportPesa - Mega Jackpot Pro 17
Prize Amount: KSH 116,478,633
Match Count: 17
Actual Matches: 17
Data Source: selenium
Is Sample Data: False

✅ SUCCESS: Getting live data from SportPesa!
```

**If you see "Sample Data" instead:**
- Selenium isn't scraping the website successfully
- The page structure may have changed
- Anti-scraping measures may be active

### Step 2: Run Detailed Diagnostic

```bash
python3 diagnose_sportpesa.py
```

**What this does:**
- Loads SportPesa page with Selenium
- Tests all CSS selectors
- Saves HTML for inspection
- Takes screenshot
- Identifies what's missing

**Output files:**
- `debug/sportpesa_page.html` - Full page HTML
- `debug/sportpesa_screenshot.png` - Screenshot of page

## Common Issues & Solutions

### Issue 1: All Jackpots Show "Sample Data"

**Symptom:**
```
Data Source: sample
Is Sample Data: True
```

**Cause:** Selenium can't scrape the website

**Solution:**

```bash
# 1. Fix Selenium dependencies
cd betting-algorithm
./fix_selenium.sh

# 2. Test again
python3 test_jackpot_fetch.py --headless

# 3. If still failing, check Chromium
chromium-browser --version

# 4. Try non-headless mode to see the browser
python3 test_jackpot_fetch.py  # No --headless flag
```

### Issue 2: No Matches Found

**Symptom:**
```
✅ Fetched 1 jackpot(s)
Actual Matches: 0
⚠️  No matches found!
```

**Cause:** CSS selectors don't match current page structure

**Solution:**

1. Run diagnostic to inspect page:
   ```bash
   python3 diagnose_sportpesa.py
   ```

2. Check the output - look for:
   ```
   ⚠️  No match elements found with standard selectors
   ```

3. Open `debug/sportpesa_page.html` in a text editor

4. Search for match elements - look for patterns like:
   - `<div class="match-row">`
   - `<div class="fixture">`
   - Elements containing team names and "vs"

5. Update selectors in [jackpot_fetcher_enhanced.py](betting-algorithm/src/jackpot_fetcher_enhanced.py):

   **Lines 339-345** - Match selectors:
   ```python
   selectors = [
       'div.jackpot-match',
       'div.match-row',
       'div[class*="match"]',  # Add your new selector here
       'tr[class*="match"]',
       'li[class*="match"]'
   ]
   ```

### Issue 3: Carousel Not Detected

**Symptom:**
```
📊 Found 1 jackpot(s) in carousel
```

**Cause:** Carousel indicators not found

**Solution:**

1. Check diagnostic output:
   ```
   ⚠️  No carousel indicators found with standard selectors
   ```

2. Open `debug/sportpesa_page.html`

3. Search for carousel controls:
   - Dots/indicators at bottom of carousel
   - Next/previous arrows
   - Look for classes like: `carousel-indicators`, `slick-dots`, `indicator`

4. Update selectors in [jackpot_fetcher_enhanced.py](betting-algorithm/src/jackpot_fetcher_enhanced.py):

   **Lines 168-176** - Indicator selectors:
   ```python
   selectors = [
       'div.carousel-indicators button',
       'div.carousel-indicators li',
       # Add new selector based on what you found
   ]
   ```

   **Lines 198-206** - Next button selectors:
   ```python
   next_selectors = [
       'button.carousel-control-next',
       'button[data-slide="next"]',
       # Add new selector
   ]
   ```

### Issue 4: Cloudflare or Bot Detection

**Symptom from diagnostic:**
```
⚠️  Cloudflare protection detected
⚠️  Bot detection/CAPTCHA detected
```

**Solution:**

Update Chrome options in [jackpot_fetcher_enhanced.py](betting-algorithm/src/jackpot_fetcher_enhanced.py):

```python
# Lines 69-80 - Add these options:
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

# Add more realistic user agent
chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
```

Also increase wait times:
```python
# Line 115 - Increase wait time
time.sleep(10)  # Instead of 5

# Line 128 - Increase transition wait
time.sleep(5)  # Instead of 2
```

### Issue 5: Wrong Prize Amount

**Symptom:**
```
Prize Amount: None
```

**Cause:** Prize extraction regex doesn't match format

**Solution:**

1. Check diagnostic output for prize patterns found

2. Update [jackpot_fetcher_enhanced.py](betting-algorithm/src/jackpot_fetcher_enhanced.py) **Lines 313-318**:

   ```python
   prize_patterns = [
       r'KSH\s*([\d,]+)',
       r'Ksh\s*([\d,]+)',
       r'KES\s*([\d,]+)',
       # Add pattern based on actual format
   ]
   ```

## Manual Inspection

### Inspect Page HTML

```bash
# 1. Generate HTML file
cd betting-algorithm
python3 diagnose_sportpesa.py

# 2. Open in browser
# Windows with WSL:
explorer.exe debug/sportpesa_page.html

# Or use text editor:
code debug/sportpesa_page.html
```

**What to look for:**
1. Search for "jackpot" - find the title element
2. Search for team names - find match containers
3. Search for "KSH" or "million" - find prize element
4. Look for carousel controls (arrows, dots)

### View Screenshot

```bash
# Windows with WSL:
explorer.exe debug/sportpesa_screenshot.png
```

Check if:
- Page loaded correctly
- Jackpot content is visible
- Any error messages or CAPTCHAs

## Testing Changes

After making changes to `jackpot_fetcher_enhanced.py`:

```bash
# 1. Test the enhanced fetcher directly
python3 src/jackpot_fetcher_enhanced.py

# 2. Test via quick test script
python3 test_jackpot_fetch.py --headless

# 3. Test via backend API
python3 app.py &
curl -X POST http://localhost:5001/api/jackpots/fetch \
  -H "Content-Type: application/json" \
  -d '{"providers": ["sportpesa"], "use_enhanced": true}'

# 4. Test via frontend
cd ../betting-frontend
npm start
# Navigate to http://localhost:4200 and click "Fetch Jackpots"
```

## Getting Help

If you're still having issues:

1. **Check Selenium setup:**
   ```bash
   ./fix_selenium.sh
   chromium-browser --version
   ```

2. **Collect diagnostic info:**
   ```bash
   python3 diagnose_sportpesa.py > diagnostic_output.txt
   ```

3. **Review logs:**
   - Backend logs from `python3 app.py`
   - Browser console in frontend (F12 → Console)
   - Check `debug/` folder for HTML and screenshots

4. **Common selector patterns to try:**
   - `div[data-testid*="match"]`
   - `div[class*="fixture"]`
   - `article[class*="game"]`
   - `div[id*="match"]`

## Success Checklist

- [ ] `test_jackpot_fetch.py` shows "Live Data"
- [ ] Multiple jackpots detected (2+)
- [ ] All jackpots have matches (10+ matches each)
- [ ] Prize amounts are displayed
- [ ] Data source is "selenium" not "sample"
- [ ] Frontend shows "Carousel Navigation Active" banner
- [ ] Green "Live Data" badges visible

## Quick Reference Commands

```bash
# Full diagnostic
python3 diagnose_sportpesa.py

# Quick test
python3 test_jackpot_fetch.py --headless

# Run enhanced fetcher directly
python3 src/jackpot_fetcher_enhanced.py

# Fix Selenium
./fix_selenium.sh

# Check Chromium
chromium-browser --version

# Test backend API
python3 app.py &
curl -X POST http://localhost:5001/api/jackpots/fetch \
  -H "Content-Type: application/json" \
  -d '{"providers": ["sportpesa"]}'
```

---

**💡 Pro Tip:** Run `diagnose_sportpesa.py` whenever SportPesa updates their website to quickly identify what selectors need updating.
