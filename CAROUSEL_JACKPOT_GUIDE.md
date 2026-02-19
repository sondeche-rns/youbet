# 🎰 SportPesa Carousel/Slideshow Jackpot Fetching

## The Problem

SportPesa uses a **carousel/slideshow interface** where multiple jackpots are displayed on a single page:

```
┌──────────────────────────────────────────┐
│  ←  MEGA JACKPOT PRO 17          →      │
│     KSH 116,478,633                     │
│                                          │
│  • • •  (carousel indicators)           │
└──────────────────────────────────────────┘
```

- **Navigation**: Click arrows (← →) to switch between jackpots
- **Indicators**: Dots show how many jackpots are available
- **Dynamic Loading**: Each jackpot's matches load when you navigate to it
- **Unique Matches**: Each jackpot type has different match combinations

## Two Implementations

### 1. Original Fetcher (Separate URLs)
**File**: `betting-algorithm/src/jackpot_fetcher.py`

**How it works:**
- Uses different URLs for each jackpot type
- `fetch_sportpesa_mega_jackpot()` - Goes to `/mega-jackpot-pro`
- `fetch_sportpesa_midweek_jackpot()` - Goes to `/jackpot`

**Pros:**
- ✅ Simple and straightforward
- ✅ Works if jackpots have separate pages

**Cons:**
- ❌ Might miss jackpots if they're only in the carousel
- ❌ Can't discover new jackpot types automatically

### 2. Enhanced Fetcher (Carousel Navigation)
**File**: `betting-algorithm/src/jackpot_fetcher_enhanced.py`

**How it works:**
1. Navigates to SportPesa jackpot page
2. Detects carousel indicators to count jackpots
3. Clicks through each slide
4. Extracts unique matches for each jackpot
5. Returns all jackpots found

**Pros:**
- ✅ Discovers ALL jackpots automatically
- ✅ Handles carousel/slideshow interfaces
- ✅ Extracts unique matches for each jackpot type
- ✅ Future-proof if new jackpot types are added

**Cons:**
- ⚠️ Slightly slower (navigates through carousel)
- ⚠️ More complex implementation

## Usage Comparison

### Original Fetcher
```python
from jackpot_fetcher import JackpotFetcher

fetcher = JackpotFetcher(use_selenium=True)

# Fetch each jackpot separately
mega = fetcher.fetch_sportpesa_mega_jackpot()
midweek = fetcher.fetch_sportpesa_midweek_jackpot()

jackpots = [mega, midweek]

# Result: 2 jackpots (manually specified)
```

### Enhanced Fetcher
```python
from jackpot_fetcher_enhanced import EnhancedJackpotFetcher

fetcher = EnhancedJackpotFetcher(use_selenium=True)

# Automatically fetch ALL jackpots from carousel
jackpots = fetcher.fetch_all_sportpesa_jackpots()

# Result: All jackpots found in carousel (could be 2, 3, or more!)
```

## Carousel Detection Features

The enhanced fetcher includes:

### 1. Carousel Indicator Detection
```python
# Finds dots/indicators to count jackpots
indicators = driver.find_elements(By.CSS_SELECTOR, 'div.carousel-indicators button')
num_jackpots = len(indicators)  # e.g., 3 jackpots available
```

### 2. Navigation Button Detection
```python
# Finds and clicks next arrow
next_button = driver.find_element(By.CSS_SELECTOR, 'button.carousel-control-next')
next_button.click()
```

### 3. Dynamic Data Extraction
```python
# Extracts data from each slide
for slide in range(num_jackpots):
    jackpot_data = extract_current_slide_data(driver)
    click_next_slide(driver)
    wait_for_transition()
```

## Output Example

### Original Fetcher Output
```json
[
  {
    "provider": "SportPesa",
    "type": "Mega Jackpot",
    "matches_count": 17,
    "prize_amount": "KSH 116,478,633",
    "matches": [...]
  },
  {
    "provider": "SportPesa",
    "type": "Midweek Jackpot",
    "matches_count": 13,
    "prize_amount": "KSH 25,000,000",
    "matches": [...]
  }
]
```

### Enhanced Fetcher Output
```json
[
  {
    "provider": "SportPesa",
    "type": "Mega Jackpot Pro 17",
    "matches_count": 17,
    "prize_amount": "KSH 116,478,633",
    "data_source": "selenium",
    "matches": [
      {
        "match_number": 1,
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "competition": "Premier League",
        "kickoff": "Sat 15:00"
      },
      ...
    ]
  },
  {
    "provider": "SportPesa",
    "type": "Midweek Jackpot 13",
    "matches_count": 13,
    "prize_amount": "KSH 25,000,000",
    "data_source": "selenium",
    "matches": [
      {
        "match_number": 1,
        "home_team": "Real Madrid",
        "away_team": "Barcelona",
        ...
      },
      ...
    ]
  },
  {
    "provider": "SportPesa",
    "type": "Mini Jackpot 10",
    "matches_count": 10,
    "prize_amount": "KSH 5,000,000",
    "data_source": "selenium",
    "matches": [...]
  }
]
```

Notice: Enhanced fetcher found a 3rd jackpot that wasn't explicitly coded!

## Implementation Details

### Carousel Selectors Used

The enhanced fetcher tries multiple selectors to ensure compatibility:

**Carousel Indicators:**
```python
selectors = [
    'div.carousel-indicators button',  # Bootstrap 5
    'div.carousel-indicators li',      # Bootstrap 4
    'div[class*="indicator"] button',  # Custom
    '.slick-dots li',                  # Slick carousel
    'ol.carousel-indicators li'        # Older Bootstrap
]
```

**Next Buttons:**
```python
next_selectors = [
    'button.carousel-control-next',          # Bootstrap
    'button[data-slide="next"]',            # Data attributes
    'div.slick-next',                        # Slick carousel
    'button[aria-label*="next" i]',         # Accessibility
    'div[class*="arrow"][class*="right"]'   # Custom arrows
]
```

## Testing

### Test Enhanced Fetcher
```bash
cd betting-algorithm/src
python jackpot_fetcher_enhanced.py
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

✅ Fetched 3 jackpot(s)
```

## Integration with Analyzer

Both fetchers work with the analyzer:

```python
from jackpot_fetcher_enhanced import EnhancedJackpotFetcher
from jackpot_analyzer import JackpotAnalyzer

# Fetch all jackpots
fetcher = EnhancedJackpotFetcher(use_selenium=True)
jackpots = fetcher.fetch_all_sportpesa_jackpots()

# Analyze each one
analyzer = JackpotAnalyzer()
for jackpot in jackpots:
    print(f"\nAnalyzing: {jackpot['type']}")
    analysis = analyzer.analyze_jackpot(jackpot)
    print(f"Average Confidence: {analysis['average_confidence']*100:.1f}%")
```

## Which One to Use?

### Use Original Fetcher If:
- ✅ You know exactly which jackpots you want
- ✅ You want simple, straightforward code
- ✅ The website has separate URLs for each jackpot

### Use Enhanced Fetcher If:
- ✅ You want to discover ALL available jackpots
- ✅ The website uses a carousel/slideshow interface
- ✅ You want future-proof automatic detection
- ✅ New jackpot types might be added

## Recommendation

**For SportPesa**: Use the **Enhanced Fetcher** because:
1. SportPesa uses a carousel interface (as shown in your screenshot)
2. It automatically finds all jackpots (no manual coding needed)
3. It extracts unique matches for each jackpot type
4. It's future-proof if SportPesa adds new jackpot types

## Migration Path

If you're currently using the original fetcher:

```python
# Before (Original)
from jackpot_fetcher import JackpotFetcher
fetcher = JackpotFetcher()
mega = fetcher.fetch_sportpesa_mega_jackpot()
midweek = fetcher.fetch_sportpesa_midweek_jackpot()
jackpots = [mega, midweek]

# After (Enhanced - drop-in replacement)
from jackpot_fetcher_enhanced import EnhancedJackpotFetcher
fetcher = EnhancedJackpotFetcher()
jackpots = fetcher.fetch_all_sportpesa_jackpots()
# Now you get ALL jackpots automatically!
```

## Troubleshooting

### "No carousel indicators found"
- Website might not use standard carousel library
- Manually adjust selectors in `_find_carousel_indicators()`
- Check browser DevTools for actual class names

### "Could not find next button"
- Check if arrows are visible when page loads
- Try non-headless mode to see the page
- Manually add the correct selector

### "Extracted 0 matches"
- Website HTML structure might have changed
- Update selectors in `_extract_matches()`
- Run in non-headless mode to debug

## Future Enhancements

Potential improvements:
1. **Smart waiting**: Wait for animations to complete
2. **Duplicate detection**: Skip if jackpot already fetched
3. **Parallel fetching**: Fetch multiple providers at once
4. **Auto-retry**: Retry failed extractions
5. **Screenshot capture**: Save images of each jackpot

---

**Bottom Line**: The Enhanced Fetcher is specifically designed for SportPesa's carousel interface and can automatically discover and extract all available jackpots with their unique match combinations!
