# 🎨 Frontend Carousel Jackpot Implementation

Complete guide for the SportPesa carousel jackpot feature in the Angular frontend.

## Overview

The frontend now supports **automatic carousel navigation** for SportPesa jackpots, displaying all available jackpots with visual indicators for data source and live/sample data.

## Features Implemented

### ✅ 1. Enhanced Backend Integration
- **Endpoint**: `/api/jackpots/fetch`
- **Method**: Automatically uses `EnhancedJackpotFetcher` for SportPesa
- **Fallback**: Gracefully falls back to standard fetcher if enhanced fails
- **Response**: Includes `enhanced_used` flag and `data_source` for each jackpot

### ✅ 2. Visual Indicators

#### Live Data Badge
```
┌──────────────────────────────────┐
│ SportPesa    [Live Data]  KSH 116M│
│ Mega Jackpot Pro 17              │
│                                  │
│ 17 Matches  |  17 Fetched        │
│ 🌐 Live from Carousel            │
└──────────────────────────────────┘
```

#### Sample Data Badge
```
┌──────────────────────────────────┐
│ SportPesa [Sample Data] KSH 25M  │
│ Midweek Jackpot 13               │
│                                  │
│ 13 Matches  |  13 Fetched        │
│ 📝 Sample Data                   │
└──────────────────────────────────┘
```

### ✅ 3. Carousel Info Banner

When enhanced fetcher is used:
```
┌────────────────────────────────────────────────┐
│ 🎰 Carousel Navigation Active                 │
│                                                │
│ Automatically discovered 3 jackpot(s) from     │
│ SportPesa carousel                             │
└────────────────────────────────────────────────┘
```

## Frontend Changes

### 1. Updated Interface

```typescript
interface JackpotData {
  provider: string;
  type: string;
  matches_count: number;
  prize_amount?: string;
  fetched_at: string;
  url: string;
  matches: JackpotMatch[];
  is_sample_data?: boolean;
  data_source?: string; // NEW: 'selenium', 'sample', 'sample_fallback'
}
```

### 2. New Component Properties

```typescript
export class JackpotComponent {
  usedEnhancedFetcher = false; // NEW: Tracks if carousel was used
  // ... existing properties
}
```

### 3. Enhanced Fetch Function

```typescript
async fetchJackpots() {
  // ... fetch logic
  this.usedEnhancedFetcher = response.enhanced_used || false;
  // ... rest of logic
}
```

### 4. Data Source Labels

```typescript
getDataSourceLabel(dataSource: string): string {
  const labels: { [key: string]: string } = {
    'selenium': 'Live from Carousel',
    'sample': 'Sample Data',
    'sample_fallback': 'Fallback Data'
  };
  return labels[dataSource] || dataSource;
}
```

## Backend Changes

### Updated `/api/jackpots/fetch` Endpoint

```python
@app.route('/api/jackpots/fetch', methods=['POST'])
def fetch_jackpots():
    # Try enhanced fetcher for SportPesa
    if provider_lower == 'sportpesa':
        if enhanced_available and use_enhanced:
            enhanced_fetcher = EnhancedJackpotFetcher(use_selenium=True)
            sportpesa_jackpots = enhanced_fetcher.fetch_all_sportpesa_jackpots()
            # Returns ALL jackpots from carousel automatically
```

**Response Format:**
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

## Visual Design

### Color Coding

| Badge Type | Color | Border | Background |
|-----------|-------|--------|-----------|
| **Live Data** | Green (#10b981) | Green | Green gradient (5% opacity) |
| **Sample Data** | Yellow (#fbbf24) | Yellow | Yellow gradient (5% opacity) |

### CSS Classes

```scss
.live-badge {
  background: #10b981;
  color: white;
  // Indicates live Selenium data
}

.sample-badge {
  background: #fbbf24;
  color: #78350f;
  // Indicates sample/test data
}

.data-source-indicator {
  // Shows icon and label at bottom of card
  border-top: 1px solid var(--border);
}

.info-banner {
  // Blue/green gradient banner
  // Shows when carousel navigation is active
}
```

## User Flow

### Step 1: Fetch Jackpots
```
User clicks "📡 Fetch Jackpots"
    ↓
Frontend sends POST to /api/jackpots/fetch
    ↓
Backend attempts Enhanced Fetcher (carousel)
    ↓
If successful: Returns all carousel jackpots
If fails: Falls back to standard fetcher
    ↓
Frontend displays jackpots with badges
```

### Step 2: Visual Feedback

**Enhanced Fetcher Success:**
```
🎰 Carousel Navigation Active
Automatically discovered 3 jackpot(s) from SportPesa carousel

[Card: Mega Jackpot Pro 17]    [Live Data]  KSH 116M
[Card: Midweek Jackpot 13]     [Live Data]  KSH 25M
[Card: Mini Jackpot 10]        [Live Data]  KSH 5M
```

**Fallback to Sample Data:**
```
⚠️ Using Sample Data
The betting sites use JavaScript rendering...

[Card: Mega Jackpot]          [Sample Data]  Unknown
[Card: Midweek Jackpot]       [Sample Data]  Unknown
```

### Step 3: Selection & Analysis

User can click any jackpot card to:
1. Select it (card highlights)
2. Click "🤖 Analyze This" button
3. View AI predictions

## Error Handling

### Scenario 1: Enhanced Fetcher Not Available
```typescript
if (!enhanced_available) {
  // Falls back to standard fetcher
  // No error shown to user
  console.log("Enhanced fetcher not available, using standard fetcher");
}
```

### Scenario 2: Enhanced Fetcher Fails
```typescript
try {
  sportpesa_jackpots = enhanced_fetcher.fetch_all_sportpesa_jackpots();
} catch (e) {
  // Falls back to standard fetcher
  // Warning added to response
  warnings.append("Enhanced carousel navigation failed, using standard fetcher");
}
```

### Scenario 3: Selenium Not Working
```python
# Enhanced fetcher automatically falls back to sample data
jackpot_data['data_source'] = 'sample_fallback'
```

## Testing

### Test 1: With Selenium Working
```bash
cd betting-algorithm
./fix_selenium.sh  # Fix dependencies

# Start backend
python app.py

# Start frontend
cd ../betting-frontend
npm start

# Navigate to Jackpot page
# Click "Fetch Jackpots"
# Should see:
# - "Carousel Navigation Active" banner
# - "Live Data" badges
# - Data source: "Live from Carousel"
```

### Test 2: Without Selenium
```bash
# Don't install Selenium

# Start backend
python app.py

# Frontend shows:
# - "Using Sample Data" warning
# - "Sample Data" badges
# - Data source: "Sample Data"
```

### Test 3: Mixed Data Sources
```bash
# Selenium partially working
# Some jackpots from carousel, some fallback

# Frontend shows:
# - Mixed badges (some Live, some Sample)
# - Individual data source indicators
```

## Configuration

### Enable/Disable Enhanced Fetcher

**Frontend Request:**
```typescript
// In api.service.ts
fetchJackpots(providers: string[], useEnhanced = true) {
  return this.http.post('/api/jackpots/fetch', {
    providers,
    use_enhanced: useEnhanced  // Control enhanced fetcher
  });
}
```

**Backend Handling:**
```python
use_enhanced = data.get('use_enhanced', True)  # Default: enabled

if enhanced_available and use_enhanced:
    # Use carousel navigation
else:
    # Use standard fetcher
```

## Troubleshooting

### Issue: "Carousel Navigation Active" but showing sample data

**Cause:** Selenium is not working properly

**Solution:**
```bash
cd betting-algorithm
./fix_selenium.sh
```

**Check:**
```bash
# Test Selenium directly
python betting-algorithm/src/jackpot_fetcher_enhanced.py
```

### Issue: Only seeing 2 jackpots instead of 3+

**Cause:** Enhanced fetcher might not be detecting all carousel slides

**Debug:**
1. Run enhanced fetcher in non-headless mode:
   ```python
   fetcher = EnhancedJackpotFetcher(use_selenium=True, headless=False)
   ```
2. Check browser DevTools for carousel selectors
3. Update selectors in `_find_carousel_indicators()`

### Issue: Frontend not showing new badges

**Cause:** Cache or old version

**Solution:**
```bash
cd betting-frontend
npm start  # Restart dev server
# Hard refresh browser (Ctrl+Shift+R)
```

## Future Enhancements

### 1. Manual Carousel Navigation
Add buttons to frontend to navigate carousel manually:
```
← Previous Jackpot  |  Next Jackpot →
```

### 2. Auto-Refresh
Periodically fetch jackpots to keep data fresh:
```typescript
setInterval(() => this.fetchJackpots(), 5 * 60 * 1000); // Every 5 min
```

### 3. Jackpot Comparison
Side-by-side comparison of multiple jackpots:
```
[Mega Jackpot]  vs  [Midweek Jackpot]
17 matches          13 matches
Avg confidence      Avg confidence
75%                 82%
```

### 4. Carousel Preview
Show thumbnails of all available jackpots:
```
• • • (3 jackpots available)
```

## Summary

The frontend carousel implementation provides:

✅ **Automatic Discovery** - All carousel jackpots fetched automatically
✅ **Visual Feedback** - Clear badges showing data source
✅ **Info Banner** - Notifies when carousel navigation is active
✅ **Fallback Handling** - Graceful degradation to sample data
✅ **Error Recovery** - Multiple levels of fallback
✅ **User-Friendly** - Clear indicators of live vs sample data

**Result:** Users can now see ALL SportPesa jackpots from the carousel with proper visual indicators! 🎰
