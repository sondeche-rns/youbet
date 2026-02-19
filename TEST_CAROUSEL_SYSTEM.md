# 🧪 End-to-End Carousel System Test

Complete testing guide for the SportPesa carousel jackpot feature.

## Test 1: Backend Carousel Fetcher

Test that the enhanced fetcher can navigate the carousel and retrieve all jackpots.

```bash
cd betting-algorithm

# Test enhanced fetcher directly
python src/jackpot_fetcher_enhanced.py
```

**Expected Output:**
```
======================================================================
ENHANCED JACKPOT FETCHER TEST - CAROUSEL NAVIGATION
======================================================================

🌐 Fetching SportPesa jackpots from: https://www.ke.sportpesa.com/en/mega-jackpot-pro
📊 Found 3 jackpot(s) in carousel

🎰 Processing jackpot 1/3
✅ Extracted: Mega Jackpot Pro 17 with 17 matches

🎰 Processing jackpot 2/3
✅ Extracted: Midweek Jackpot 13 with 13 matches

🎰 Processing jackpot 3/3
✅ Extracted: Mini Jackpot 10 with 10 matches

✅ Successfully extracted 3 jackpot(s)
```

✅ **Pass Criteria**: Should discover 2+ jackpots with unique match counts

## Test 2: Backend API Endpoint

Test that the Flask API endpoint uses the enhanced fetcher.

```bash
# Terminal 1: Start backend
cd betting-algorithm
python app.py

# Terminal 2: Test API
curl -X POST http://localhost:5001/api/jackpots/fetch \
  -H "Content-Type: application/json" \
  -d '{"providers": ["SportPesa"], "use_enhanced": true}'
```

**Expected Response:**
```json
{
  "success": true,
  "enhanced_used": true,
  "jackpots": [
    {
      "provider": "SportPesa",
      "type": "Mega Jackpot Pro 17",
      "matches_count": 17,
      "prize_amount": "KSH 116,478,633",
      "data_source": "selenium",
      "is_sample_data": false,
      "matches": [...]
    },
    {
      "provider": "SportPesa",
      "type": "Midweek Jackpot 13",
      "matches_count": 13,
      "prize_amount": "KSH 25,000,000",
      "data_source": "selenium",
      "is_sample_data": false,
      "matches": [...]
    }
  ],
  "count": 2
}
```

✅ **Pass Criteria**:
- `enhanced_used: true`
- `data_source: "selenium"` for each jackpot
- `is_sample_data: false`
- Multiple jackpots with different match counts

## Test 3: Frontend Display

Test that the Angular frontend displays carousel data correctly.

```bash
# Terminal 1: Backend
cd betting-algorithm
python app.py

# Terminal 2: Frontend
cd betting-frontend
npm start
```

**Steps:**
1. Navigate to `http://localhost:4200`
2. Go to Jackpot page
3. Click **"📡 Fetch Jackpots"** button
4. Wait for data to load

**Expected UI:**

```
┌────────────────────────────────────────────────┐
│ 🎰 Carousel Navigation Active                 │
│                                                │
│ Automatically discovered 3 jackpot(s) from     │
│ SportPesa carousel                             │
└────────────────────────────────────────────────┘

┌──────────────────────────────────┐
│ SportPesa    [Live Data]  KSH 116M│
│ Mega Jackpot Pro 17              │
│                                  │
│ 17 Matches  |  17 Fetched        │
│ 🌐 Live from Carousel            │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│ SportPesa    [Live Data]  KSH 25M │
│ Midweek Jackpot 13               │
│                                  │
│ 13 Matches  |  13 Fetched        │
│ 🌐 Live from Carousel            │
└──────────────────────────────────┘
```

✅ **Pass Criteria**:
- Info banner shows "Carousel Navigation Active"
- Multiple jackpot cards displayed
- Green "Live Data" badges visible
- Data source shows "🌐 Live from Carousel"
- Each jackpot has unique match count

## Test 4: Fallback Behavior

Test that the system gracefully falls back to sample data if Selenium fails.

```bash
# Temporarily disable Selenium by renaming chromedriver
sudo mv /usr/bin/chromium-browser /usr/bin/chromium-browser.backup

# Restart backend
cd betting-algorithm
python app.py

# In frontend, click "Fetch Jackpots"
```

**Expected UI:**

```
⚠️ Using Sample Data
The betting sites use JavaScript rendering...

┌──────────────────────────────────┐
│ SportPesa [Sample Data]  Unknown │
│ Mega Jackpot                     │
│                                  │
│ 17 Matches  |  17 Fetched        │
│ 📝 Sample Data                   │
└──────────────────────────────────┘
```

✅ **Pass Criteria**:
- Warning banner shows "Using Sample Data"
- Yellow "Sample Data" badges visible
- Data source shows "📝 Sample Data"
- System still works (doesn't crash)

**Restore Selenium:**
```bash
sudo mv /usr/bin/chromium-browser.backup /usr/bin/chromium-browser
```

## Test 5: Mixed Data Sources

Test behavior when some jackpots load from Selenium and some from sample data.

This would happen if Selenium partially fails or times out on some jackpots.

✅ **Pass Criteria**:
- Each jackpot shows its own data source badge
- Some cards have green "Live Data" badges
- Some cards have yellow "Sample Data" badges
- All jackpots still displayed correctly

## Test 6: Jackpot Selection & Analysis

Test the full user workflow including analysis.

```bash
# Backend and frontend running
```

**Steps:**
1. Fetch jackpots (should see carousel navigation banner)
2. Click on a jackpot card (should highlight)
3. Click **"🤖 Analyze This"** button
4. Review AI predictions

✅ **Pass Criteria**:
- Selected jackpot highlights correctly
- Analysis shows predictions for all matches
- Confidence scores displayed
- Recommendations provided

## Test 7: Browser DevTools Check

Verify API communication.

**Steps:**
1. Open browser DevTools (F12)
2. Go to Network tab
3. Click "Fetch Jackpots"
4. Find POST request to `/api/jackpots/fetch`
5. Check response JSON

✅ **Pass Criteria**:
- Request payload includes `"use_enhanced": true`
- Response includes `"enhanced_used": true`
- Response includes multiple jackpots
- Each jackpot has `"data_source": "selenium"`

## Test 8: Performance Test

Measure fetch time for carousel navigation.

```bash
# Time the enhanced fetcher
time python src/jackpot_fetcher_enhanced.py
```

✅ **Pass Criteria**:
- Completes in under 60 seconds
- Successfully fetches all jackpots
- No timeout errors

## Troubleshooting Common Issues

### Issue: "Enhanced fetcher not available"
**Solution:**
```bash
cd betting-algorithm
python -c "from src.jackpot_fetcher_enhanced import EnhancedJackpotFetcher; print('Enhanced fetcher available')"
```

### Issue: Shows "Sample Data" instead of "Live Data"
**Solution:**
```bash
cd betting-algorithm
./fix_selenium.sh
```

### Issue: Frontend not showing carousel banner
**Solution:**
```bash
cd betting-frontend
npm start  # Restart dev server
# Hard refresh browser (Ctrl+Shift+R)
```

### Issue: API returns `enhanced_used: false`
**Check:**
1. Backend logs for errors
2. Selenium installation: `chromium-browser --version`
3. ChromeDriver: `chromedriver --version`
4. Request payload includes `use_enhanced: true`

## Quick Health Check

Run all checks in sequence:

```bash
# 1. Check Selenium
chromium-browser --version

# 2. Test enhanced fetcher
cd betting-algorithm
python -c "from src.jackpot_fetcher_enhanced import EnhancedJackpotFetcher; f = EnhancedJackpotFetcher(use_selenium=True); print('OK')"

# 3. Start backend
python app.py &
sleep 5

# 4. Test API
curl -X POST http://localhost:5001/api/jackpots/fetch \
  -H "Content-Type: application/json" \
  -d '{"providers": ["SportPesa"], "use_enhanced": true}' | grep -o '"enhanced_used":[^,]*'

# 5. Start frontend
cd ../betting-frontend
npm start
```

Expected final line: `"enhanced_used":true`

## Success Checklist

- [ ] Enhanced fetcher discovers multiple jackpots
- [ ] API endpoint returns `enhanced_used: true`
- [ ] Frontend shows "Carousel Navigation Active" banner
- [ ] Jackpot cards show green "Live Data" badges
- [ ] Data source shows "🌐 Live from Carousel"
- [ ] Multiple jackpots with different match counts displayed
- [ ] Fallback to sample data works if Selenium unavailable
- [ ] Jackpot selection and analysis workflow functions
- [ ] Browser DevTools confirms proper API communication
- [ ] All operations complete without errors

## 🎉 All Tests Passed?

Your SportPesa carousel jackpot system is fully operational! You can now:

1. ✅ Automatically discover ALL SportPesa jackpots
2. ✅ Navigate carousel programmatically
3. ✅ Extract unique matches for each jackpot type
4. ✅ Display all jackpots with visual data source indicators
5. ✅ Analyze any jackpot with AI predictions
6. ✅ Handle errors gracefully with fallback data

**Happy betting analysis! 🎰**
