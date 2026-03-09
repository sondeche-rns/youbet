# Phase 4 Implementation Reference — Jackpot System

## Overview

Phase 4 ports the Python jackpot subsystem to Go, creating the
`internal/jackpot/` package. Two files are created:

| File | Source | Purpose |
|------|--------|---------|
| `fetcher.go` | `jackpot_fetcher.py` | Scrape SportPesa / Betika; sample-data fallback |
| `analyzer.go` | `jackpot_analyzer.py` | Batch predictions + combination strategies + result tracking |

No new external dependencies are added; the package uses only Go stdlib and
internal packages (`internal/algorithm`, `internal/domain`).

---

## Package Structure

```
internal/jackpot/
├── fetcher.go          # JackpotFetcher, JackpotData, JackpotMatch, HistoryRow
└── analyzer.go         # JackpotAnalyzer, JackpotAnalysis, MatchPrediction, Combination
```

### Shared types

Both files live in `package jackpot`. Types are split by concern:

- **fetcher.go** owns data-acquisition types: `JackpotMatch`, `JackpotData`, `HistoryRow`
- **analyzer.go** owns prediction types: `MatchPrediction`, `Combination`,
  `JackpotAnalysis`, `JackpotResult`, `ResultInput`

Helper functions `buildCSVIndex` and `csvCol` are defined in `fetcher.go` and
reused by `analyzer.go` (same package).

---

## Data Flow

```
JackpotFetcher.FetchSportpesaMegaJackpot()
        │
        ├─ fetchPage() ──► HTTP GET (net/http)
        │        │
        │   [JS-rendered? No match elements]
        │        │
        ├─ extractMatchesFromHTML() ──► []JackpotMatch (usually empty)
        │        │ (empty)
        ├─ sampleSportpesaMatches() ──► []JackpotMatch (17 curated)
        │
        ├─ saveHistory() ──► {provider}_{type}_{ts}.json
        │                ──► jackpot_history.csv (append)
        └─► *JackpotData

JackpotAnalyzer.AnalyzeJackpot(*JackpotData)
        │
        ├─ for each JackpotMatch:
        │       enrichMatchData() ──► domain.LookupTeam() ──► *domain.MatchData
        │       engine.Predict()  ──► *domain.PredictionResult
        │       ──► MatchPrediction{Prediction, Confidence, HomeProb, DrawProb, AwayProb}
        │
        ├─ generateCombinations() ──► []Combination (Main / Conservative / Draw-Value)
        ├─ savePredictions()       ──► {jackpot_id}.json + {jackpot_id}.csv
        └─► *JackpotAnalysis

JackpotAnalyzer.RecordJackpotResults(jackpotID, []ResultInput)
        │
        ├─ load {jackpot_id}.json ──► JackpotAnalysis
        ├─ match results → predictions ──► Correct bool, ActualResult string
        ├─ compute Accuracy = correct / total
        ├─ save {jackpot_id}_results.json
        ├─ appendToResultsCSV() ──► jackpot_results_summary.csv (append)
        └─► *JackpotResult
```

---

## File-by-File Reference

### `internal/jackpot/fetcher.go`

**Package**: `jackpot`

**Types**:

```go
type JackpotMatch struct {
    MatchNumber int    `json:"match_number"`
    HomeTeam    string `json:"home_team"`
    AwayTeam    string `json:"away_team"`
    Kickoff     string `json:"kickoff,omitempty"`
    Competition string `json:"competition,omitempty"`
}

type JackpotData struct {
    Provider     string         `json:"provider"`
    Type         string         `json:"type"`
    MatchesCount int            `json:"matches_count"`
    FetchedAt    string         `json:"fetched_at"`    // RFC3339
    URL          string         `json:"url"`
    Matches      []JackpotMatch `json:"matches"`
    DataSource   string         `json:"data_source"`   // "http" | "sample"
    PrizeAmount  string         `json:"prize_amount,omitempty"`
    Error        string         `json:"error,omitempty"`
}

type HistoryRow struct {
    Timestamp    string
    Provider     string
    Type         string
    MatchesCount int
    PrizeAmount  string
    URL          string
    DataSource   string
}
```

**Struct**:

```go
type JackpotFetcher struct {
    httpClient *http.Client     // 30 s timeout
    dataDir    string           // default: "./data/jackpots"
    userAgent  string           // Chrome 120 UA string
}
```

**Constructor**:

```go
func NewJackpotFetcher(dataDir string) *JackpotFetcher
```

If `dataDir` is empty, defaults to `"./data/jackpots"`.

**Public methods**:

| Method | Description |
|--------|-------------|
| `FetchSportpesaMegaJackpot() *JackpotData` | Fetches SportPesa Mega (17 matches) |
| `FetchSportpesaMidweekJackpot() *JackpotData` | Fetches SportPesa Midweek (13 matches) |
| `FetchBetikaJackpot() *JackpotData` | Fetches Betika Jackpot (15 matches) |
| `GetAllCurrentJackpots() []*JackpotData` | Fetches all three; returns non-nil results |
| `GetJackpotHistory(provider, jackpotType string) ([]HistoryRow, error)` | Reads `jackpot_history.csv` with optional filters |

**Internal methods / functions**:

| Symbol | Description |
|--------|-------------|
| `fetchPage(url) (string, error)` | GET request with UA header; returns body string |
| `extractMatchesFromHTML(html) []JackpotMatch` | Regex scan for team-name pairs in HTML |
| `extractPrizeAmount(html) string` | Regex scan for KSh/prize amounts |
| `saveHistory(*JackpotData)` | Writes timestamped JSON + appends CSV row |
| `appendToMasterCSV(*JackpotData)` | Appends one row to `jackpot_history.csv` |
| `buildCSVIndex([]string) map[string]int` | Maps header names → column indices |
| `csvCol(row, idx, name) string` | Safe CSV column accessor |
| `sampleSportpesaMatches() []JackpotMatch` | 17 curated Premier League / European matches |
| `sampleBetikaMatches() []JackpotMatch` | 15 curated matches |

---

### `internal/jackpot/analyzer.go`

**Package**: `jackpot`

**Types**:

```go
type MatchPrediction struct {
    MatchNumber    int     `json:"match_number"`
    HomeTeam       string  `json:"home_team"`
    AwayTeam       string  `json:"away_team"`
    Prediction     string  `json:"prediction"`    // "Home" | "Draw" | "Away" | "Error"
    Confidence     float64 `json:"confidence"`
    HomeProb       float64 `json:"home_prob"`
    DrawProb       float64 `json:"draw_prob"`
    AwayProb       float64 `json:"away_prob"`
    Recommendation string  `json:"recommendation"`
    ActualResult   string  `json:"actual_result,omitempty"`
    Correct        *bool   `json:"correct,omitempty"`
    Error          string  `json:"error,omitempty"`
}

type Combination struct {
    Strategy            string   `json:"strategy"`
    Description         string   `json:"description"`
    Picks               []string `json:"picks,omitempty"`               // Main strategy
    PredictedAccuracy   float64  `json:"predicted_accuracy,omitempty"`
    HighConfidencePicks []string `json:"high_confidence_picks,omitempty"` // Conservative strategy
    DrawCandidates      []string `json:"draw_candidates,omitempty"`        // Draw-value strategy
}

type JackpotAnalysis struct {
    JackpotID               string            `json:"jackpot_id"`
    Provider                string            `json:"provider"`
    Type                    string            `json:"type"`
    PrizeAmount             string            `json:"prize_amount,omitempty"`
    TotalMatches            int               `json:"total_matches"`
    AnalyzedAt              string            `json:"analyzed_at"`
    Predictions             []MatchPrediction `json:"predictions"`
    HighConfidenceCount     int               `json:"high_confidence_count"`
    LowConfidenceCount      int               `json:"low_confidence_count"`
    HighConfidencePicks     []MatchPrediction `json:"high_confidence_picks"`
    LowConfidencePicks      []MatchPrediction `json:"low_confidence_picks"`
    AverageConfidence       float64           `json:"average_confidence"`
    RecommendedCombinations []Combination     `json:"recommended_combinations"`
}

type JackpotResult struct {
    JackpotID              string            `json:"jackpot_id"`
    Provider               string            `json:"provider"`
    Type                   string            `json:"type"`
    RecordedAt             string            `json:"recorded_at"`
    TotalMatches           int               `json:"total_matches"`
    CorrectPredictions     int               `json:"correct_predictions"`
    Accuracy               float64           `json:"accuracy"`
    PredictionsWithResults []MatchPrediction `json:"predictions_with_results"`
}

type ResultInput struct {
    MatchNumber  int    `json:"match_number"`
    ActualResult string `json:"actual_result"` // "Home" | "Draw" | "Away"
}
```

**Struct**:

```go
type JackpotAnalyzer struct {
    engine         *algorithm.PredictionEngine
    predictionsDir string   // default: "./data/jackpot_predictions"
    resultsDir     string   // default: "./data/jackpot_results"
}
```

**Constructor**:

```go
func NewJackpotAnalyzer(
    engine         *algorithm.PredictionEngine,
    predictionsDir string,
    resultsDir     string,
) *JackpotAnalyzer
```

**Public methods**:

| Method | Description |
|--------|-------------|
| `AnalyzeJackpot(*JackpotData) *JackpotAnalysis` | Predicts all matches; generates combinations; saves JSON + CSV |
| `RecordJackpotResults(jackpotID string, results []ResultInput) (*JackpotResult, error)` | Loads analysis, scores actual results, saves results |
| `GetPerformanceStats() ([]map[string]string, error)` | Reads `jackpot_results_summary.csv`; returns all rows |

**Internal functions**:

| Symbol | Description |
|--------|-------------|
| `predictMatch(JackpotMatch) MatchPrediction` | Calls engine.Predict; determines most likely outcome |
| `enrichMatchData(JackpotMatch) *domain.MatchData` | Builds MatchData from LookupTeam results |
| `generateCombinations([]MatchPrediction) []Combination` | Produces three strategies |
| `savePredictions(*JackpotAnalysis)` | Writes JSON + CSV to predictionsDir |
| `appendToResultsCSV(*JackpotResult)` | Appends summary row to jackpot_results_summary.csv |

---

## Key Algorithms

### Outcome Determination

The most likely outcome is determined by comparing the three probabilities
from `PredictionResult.Probabilities`:

```go
prediction := "Home"
if drawProb > homeProb && drawProb >= awayProb {
    prediction = "Draw"
} else if awayProb > homeProb && awayProb > drawProb {
    prediction = "Away"
}
```

Home wins ties (consistent with the Python `max(probs, key=...)` which returns
the first maximum in insertion order: `{'Home': ..., 'Draw': ..., 'Away': ...}`).

### Confidence Thresholds

| Threshold | Classification |
|-----------|---------------|
| `confidence > 0.75` | High-confidence pick |
| `0.55 ≤ confidence ≤ 0.75` | Normal |
| `confidence < 0.55` | Low-confidence pick |

### Combination Strategies

Three strategies are generated:

**1. Main Prediction** — all valid matches with their highest-probability outcome:

```
picks = ["1: Home", "2: Draw", ...]
predicted_accuracy = mean(max(homeProb, drawProb, awayProb)) over all matches
```

**2. Conservative** — only matches where `confidence > 0.70`:

```
high_confidence_picks = ["N: outcome", ...]
predicted_accuracy = mean(max_prob) over high-confidence matches only
description = "K high confidence picks, others doubled"
```

**3. Draw Value** — matches where `drawProb > 0.30`:

```
draw_candidates = ["N: TeamA vs TeamB (35.2%)", ...]
description = "K matches with draw probability >30%"
```

### Team Enrichment

`enrichMatchData` calls `domain.LookupTeam(name)` which searches
`domain.PremierLeagueTeams` by name and aliases (normalised, lowercased).
When a team is not found, zero values are left in `domain.MatchData`, and the
`PredictionEngine` applies its own defaults.

Fields mapped from `domain.TeamData` to `domain.MatchData`:

| TeamData field | MatchData field |
|----------------|----------------|
| `Elo` (int) | `HomeElo` / `AwayElo` (float64) |
| `Position` (int) | `HomePosition` / `AwayPosition` |
| `Form` (string) | `HomeForm` / `AwayForm` |
| `Stars` (int) | `HomeStarRating` / `AwayStarRating` |
| `HomeXGAvg` / `AwayXGAvg` (float64) | `HomeXG` / `AwayXG` |
| `Style` (PlayStyle) | `HomeStyle` / `AwayStyle` (string cast) |

### HTML Extraction (Static Fallback)

`extractMatchesFromHTML` applies a regex against raw HTML:

```go
var teamNameRe = regexp.MustCompile(
    `(?i)class="[^"]*(?:home|team)[^"]*"[^>]*>\s*([A-Z][A-Za-z\s'.]{2,29})\s*<`)
```

Because SportPesa and Betika use JavaScript rendering (SPA), the pre-render
HTML typically contains no match elements. The regex returns an empty slice,
and callers fall back to sample data. This mirrors the Python Selenium path
where `_extract_sportpesa_matches` also returns sample data when no elements
are found.

### Prize Amount Extraction

```go
var prizeAmountRe = regexp.MustCompile(
    `(?i)KSh?\s*[\d,]+(?:\.\d+)?(?:\s*(?:Million|Billion|M|B))?|[\d,]+\s*(?:Million|Billion)`)
```

Matches formats such as: `KSh 200,000,000`, `KSH 200 Million`, `200 Billion`.

### Jackpot ID Format

```
{Provider}{Type}_{YYYYMMDD_HHMMSS}
```

Example: `SportPesaMegaJackpot_20260224_153012`

Spaces in provider and type are stripped (not replaced), so:
- `"SportPesa"` + `"Mega Jackpot"` → `"SportPesaMegaJackpot_..."`
- `"Betika"` + `"Jackpot"` → `"BetikaJackpot_..."`

---

## File I/O Layout

```
data/
├── jackpots/
│   ├── jackpot_history.csv                    ← master fetch log
│   ├── sportpesa_mega_jackpot_20260224_...json
│   ├── sportpesa_midweek_jackpot_...json
│   └── betika_jackpot_...json
│
├── jackpot_predictions/
│   ├── SportPesaMegaJackpot_20260224_...json  ← full analysis
│   └── SportPesaMegaJackpot_20260224_....csv  ← tabular predictions
│
└── jackpot_results/
    ├── SportPesaMegaJackpot_20260224_..._results.json
    └── jackpot_results_summary.csv            ← master results log
```

### jackpot_history.csv columns

| Column | Description |
|--------|-------------|
| `timestamp` | RFC3339 fetch time |
| `provider` | "SportPesa" or "Betika" |
| `type` | "Mega Jackpot", "Midweek Jackpot", "Jackpot" |
| `matches_count` | Number of matches in this fetch |
| `prize_amount` | Extracted prize string (may be empty) |
| `url` | Source URL |
| `data_source` | "http" or "sample" |

### jackpot_results_summary.csv columns

| Column | Description |
|--------|-------------|
| `timestamp` | RFC3339 time results were recorded |
| `jackpot_id` | Matches the JSON filename stem |
| `provider` | Source bookmaker |
| `type` | Jackpot type |
| `total_matches` | Number of results provided |
| `correct` | Count of correct predictions |
| `accuracy` | float in [0, 1] |

### predictions CSV columns

| Column | Description |
|--------|-------------|
| `match_number` | 1-based index within the jackpot |
| `home_team` | Home team name |
| `away_team` | Away team name |
| `prediction` | "Home", "Draw", "Away", or "Error" |
| `confidence` | float64, 4 d.p. |
| `home_prob` | float64, 4 d.p. |
| `draw_prob` | float64, 4 d.p. |
| `away_prob` | float64, 4 d.p. |
| `recommendation` | String from PredictionEngine |

---

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| HTTP fetch failure (network, timeout, non-200) | `DataSource = "sample"`; sample data returned |
| HTML parsed but no match elements (JS-rendered) | `DataSource = "sample"`; sample data returned |
| `engine.Predict` returns error | `MatchPrediction.Prediction = "Error"`, error string stored; excluded from accuracy-based stats |
| `os.MkdirAll` failure (save) | Logged as warning; method continues |
| JSON write failure (save) | Logged as warning; caller still receives in-memory struct |
| CSV append failure | Logged as warning; silently skipped |
| `RecordJackpotResults` — predictions file not found | Returns `fmt.Errorf("load predictions %s: ...")` |
| Match number not found in predictions | Silently skipped |

---

## Go vs Python Comparison

| Aspect | Python | Go |
|--------|--------|----|
| Browser automation | Selenium + ChromeDriverManager | Not used (net/http only) |
| HTML parsing | BeautifulSoup CSS selectors | Regex on raw HTML string |
| JS rendering support | Yes (Selenium executes JS) | No (static fetch only) |
| Fallback mechanism | Same — sample data when no elements | Same |
| Data storage | pandas DataFrame → CSV | encoding/csv + stdlib |
| Algorithm dependency | `ProfessionalBettingAlgorithm` | `algorithm.PredictionEngine` |
| Team lookup | `config.lookup_team()` | `domain.LookupTeam()` |
| Match outcome | `max(probs.items(), key=lambda x: x[1])` | Explicit comparison chain |
| File paths | `pathlib.Path` | `path/filepath` |
| JSON serialization | `json.dump` | `encoding/json.MarshalIndent` |
| Logging | `logging` module | `log/slog` (stdlib) |
| Concurrency | Single-threaded | Single-threaded (same design) |
| Confidence thresholds | 0.75 high / 0.55 low | 0.75 high / 0.55 low |
| Conservative threshold | 0.70 | 0.70 |
| Draw-value threshold | 0.30 | 0.30 |

---

## Sample Data

### SportPesa Mega Jackpot (17 matches)

| # | Home | Away | Competition |
|---|------|------|-------------|
| 1 | Arsenal | Chelsea | Premier League |
| 2 | Man City | Liverpool | Premier League |
| 3 | Tottenham | Man United | Premier League |
| 4 | Real Madrid | Barcelona | La Liga |
| 5 | Bayern Munich | Dortmund | Bundesliga |
| 6 | Inter Milan | AC Milan | Serie A |
| 7 | PSG | Marseille | Ligue 1 |
| 8 | Juventus | Napoli | Serie A |
| 9 | Atletico Madrid | Sevilla | La Liga |
| 10 | Leicester | West Ham | Premier League |
| 11 | Newcastle | Aston Villa | Premier League |
| 12 | Brighton | Wolves | Premier League |
| 13 | Everton | Southampton | Premier League |
| 14 | Leeds United | Burnley | Championship |
| 15 | Sheffield United | Norwich | Championship |
| 16 | Brentford | Fulham | Premier League |
| 17 | Crystal Palace | Bournemouth | Premier League |

SportPesa Midweek uses matches 1–13 from the same list.

### Betika Jackpot (15 matches)

| # | Home | Away | Competition |
|---|------|------|-------------|
| 1 | Arsenal | Liverpool | Premier League |
| 2 | Man City | Chelsea | Premier League |
| 3 | Real Madrid | Atletico Madrid | La Liga |
| 4 | Barcelona | Sevilla | La Liga |
| 5 | Bayern Munich | RB Leipzig | Bundesliga |
| 6 | Inter Milan | Juventus | Serie A |
| 7 | PSG | Lyon | Ligue 1 |
| 8 | Tottenham | Newcastle | Premier League |
| 9 | Man United | West Ham | Premier League |
| 10 | Napoli | Roma | Serie A |
| 11 | Dortmund | Leverkusen | Bundesliga |
| 12 | Ajax | PSV | Eredivisie |
| 13 | Benfica | Porto | Primeira Liga |
| 14 | Celtic | Rangers | Scottish Premiership |
| 15 | Sporting CP | Braga | Primeira Liga |

---

## Dependencies

**New dependencies added**: None.

This phase uses only:
- `encoding/csv` — CSV read/write
- `encoding/json` — JSON marshal/unmarshal
- `fmt`, `io`, `log/slog`, `math`, `net/http`, `os`, `path/filepath` — stdlib
- `regexp`, `strings`, `time` — stdlib
- `github.com/bet4me/betting-algorithm-go/internal/algorithm` — internal
- `github.com/bet4me/betting-algorithm-go/internal/domain` — internal

The `goquery` library mentioned in `GO_IMPLEMENTATION.md` was evaluated and
deferred: because both SportPesa and Betika use JavaScript SPAs, even a full
DOM-parsing library returns no usable match data from the server-rendered
HTML. The regex-based extraction is equally effective (both paths reach sample
data) while avoiding an external dependency.

---

## Known Limitations

1. **No JavaScript execution** — The Go HTTP client fetches pre-render HTML.
   This is functionally identical to the Python path when Selenium times out
   or finds no elements (which is the common case). Both code paths return
   sample data.

2. **Sample data is static** — The curated match lists are hard-coded. In
   production they should be periodically refreshed to reflect the actual
   current jackpot fixtures once a scraping solution for JS-rendered content
   is available (e.g. `chromedp`).

3. **No headless browser** — A future upgrade to `github.com/chromedp/chromedp`
   would replicate Selenium's JavaScript execution capability, but adds a
   significant dependency. Designed as a drop-in replacement: the three Fetch*
   methods' signatures remain unchanged.

4. **Single-threaded fetch** — `GetAllCurrentJackpots` fetches the three
   jackpots sequentially. Each HTTP call has a 30 s timeout; the worst-case
   wall time is ~90 s. This can be parallelised with goroutines if needed.

5. **`GetPerformanceStats` returns strings** — The method returns
   `[]map[string]string` (raw CSV values) rather than parsed floats/ints.
   This keeps the implementation simple; callers parse the `"accuracy"` field
   as needed.

6. **`Correct *bool` is nil until `RecordJackpotResults` is called** — The
   pointer is used so `json:"correct,omitempty"` omits the field from initial
   prediction JSON output. Once results are recorded, `Correct` is set.

7. **Jackpot history CSV is append-only** — No deduplication: re-fetching
   the same jackpot creates a new JSON file and a new CSV row. Timestamp
   filenames avoid collisions at second granularity.

---

## Testing Strategy

Because the jackpot subsystem depends on network I/O and a running
`PredictionEngine`, the recommended test approach is:

### Unit tests (pure functions)

| Test | What to verify |
|------|---------------|
| `TestExtractMatchesFromHTML_Empty` | Returns empty slice for plain HTML with no match classes |
| `TestExtractMatchesFromHTML_Matches` | Parses synthetic HTML with `class="home-team"` elements |
| `TestExtractPrizeAmount` | Extracts "KSh 200,000,000" / "200 Million" from test strings |
| `TestGenerateCombinations_Main` | Picks array length equals valid prediction count |
| `TestGenerateCombinations_Conservative` | Only includes predictions where confidence > 0.70 |
| `TestGenerateCombinations_DrawValue` | Only includes predictions where drawProb > 0.30 |
| `TestGenerateCombinations_Empty` | Returns nil for empty predictions slice |
| `TestSampleSportpesaMatches` | Returns exactly 17 matches, all with non-empty team names |
| `TestSampleBetikaMatches` | Returns exactly 15 matches |
| `TestEnrichMatchData_KnownTeam` | Arsenal → Elo=1850, Form="WWWDW", etc. |
| `TestEnrichMatchData_UnknownTeam` | Unknown team → zero Elo, empty form, zero position |
| `TestBuildCSVIndex` | Maps header strings to correct indices |

### Integration tests (with engine)

| Test | What to verify |
|------|---------------|
| `TestAnalyzeJackpot_Sample` | `AnalyzeJackpot` on sample SportPesa data produces 17 predictions; each has valid probability sum ≈ 1.0 |
| `TestRecordJackpotResults` | After `AnalyzeJackpot`, `RecordJackpotResults` loads the saved file and returns correct Accuracy |

### Fetch tests (network-dependent, skipped in CI)

| Test | What to verify |
|------|---------------|
| `TestFetchSportpesaMegaJackpot_SampleFallback` | When HTTP fails/returns empty HTML, DataSource == "sample" and len(Matches) == 17 |
| `TestGetJackpotHistory_Empty` | Returns nil, nil when CSV file does not exist |

---

## Build Verification

```
$ go build ./...     # No output — clean build
$ go test ./...
?   github.com/bet4me/betting-algorithm-go/internal/algorithm  [no test files]
?   github.com/bet4me/betting-algorithm-go/internal/context    [no test files]
?   github.com/bet4me/betting-algorithm-go/internal/data       [no test files]
ok  github.com/bet4me/betting-algorithm-go/internal/domain     0.006s
?   github.com/bet4me/betting-algorithm-go/internal/jackpot    [no test files]
ok  github.com/bet4me/betting-algorithm-go/internal/storage    0.028s
ok  github.com/bet4me/betting-algorithm-go/internal/util       0.008s
```

All existing tests continue to pass. No external dependencies were added;
`go.mod` remains unchanged from Phase 3.

---

## Next Phase

**Phase 5**: Create `internal/backtest/`, `internal/api/`, and
`cmd/server/main.go`. This is the final implementation phase before
validation:

- `internal/backtest/engine.go` — port `backtest.py`
- `internal/api/server.go` + handlers — port `app.py` Flask routes
- `cmd/server/main.go` — wire all dependencies, start HTTP server on `:5000`

Remember to create `PHASE5_IMPLEMENTATION.md` at the end of Phase 5.
