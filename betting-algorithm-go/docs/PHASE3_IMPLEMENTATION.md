# Phase 3: Data Pipeline — Implementation Reference

> **Status:** Complete
> **Branch:** `feature/jackpot-selenium`
> **Packages created:** `internal/data`
> **Packages modified:** None (storage/csv.go already had all required fields from Phase 1)
> **Python source files ported:** `data_collector.py` · `data_sources_manager.py` · `live_fixtures_fetcher.py`

---

## Table of Contents

1. [Overview](#overview)
2. [Package Structure](#package-structure)
3. [Data Flow](#data-flow)
4. [File-by-File Reference](#file-by-file-reference)
   - [collector.go — Historical Data Pipeline](#collectorgocollector--historical-data-pipeline)
   - [sources.go — Data Sources Manager](#sourcesgosources--data-sources-manager)
   - [fixtures.go — Live Fixtures Fetcher](#fixturesgofixtures--live-fixtures-fetcher)
5. [MatchRecord Field Reference](#matchrecord-field-reference)
6. [The 7-Step Enrichment Pipeline](#the-7-step-enrichment-pipeline)
7. [External Data Sources](#external-data-sources)
8. [Configuration: data_sources.json](#configuration-data_sourcesjson)
9. [Key Algorithms Explained](#key-algorithms-explained)
10. [Error Handling & Fallback Strategy](#error-handling--fallback-strategy)
11. [Go vs Python Differences](#go-vs-python-differences)
12. [Known Limitations & TODOs](#known-limitations--todos)
13. [Testing Strategy](#testing-strategy)

---

## Overview

Phase 3 ports the entire Python data pipeline (`data_collector.py`, `data_sources_manager.py`, `live_fixtures_fetcher.py`) into Go. The result is a **synchronous data collection system** with progress callbacks that:

- Fetches raw match CSVs from football-data.co.uk for configurable seasons and leagues
- Enriches each match record through a **7-step sequential pipeline** (xG -> Elo -> Form -> Rest -> Advanced Stats -> Positions)
- Saves the final enriched dataset to `{outputDir}/final/historical_dataset.csv`
- Reports real-time progress via a `ProgressCallback` function
- Provides a config-driven `DataSourcesManager` for discovering leagues, seasons, and URL patterns
- Provides a `LiveFixturesFetcher` for pulling upcoming matches and live odds from The Odds API

The enriched data directly feeds Phase 2's `context/builder.go` methods (`BuildH2HRecordFromMatches`, `CalculateSeasonStatsFromMatches`) which power the contextual V2 prediction factors.

---

## Package Structure

```
betting-algorithm-go/
├── internal/
│   ├── data/
│   │   ├── collector.go          HistoricalDataCollector — synchronous 7-step pipeline + sample data
│   │   ├── collector_test.go     Tests for pipeline steps and helpers
│   │   ├── sources.go            DataSourcesManager — loads & queries data_sources.json config
│   │   └── fixtures.go           LiveFixturesFetcher — The Odds API + football-data.co.uk current season
│   └── storage/
│       └── csv.go                MatchRecord (30 fields, unchanged) + CSVStore read/write
└── config/
    └── data_sources.json         Copied from betting-algorithm/config/
```

**Dependencies used in Phase 3:**

| Package | Used in | Purpose |
|---------|---------|---------|
| `encoding/csv` | `collector.go`, `fixtures.go` | Parse CSV streams from HTTP responses |
| `encoding/json` | `sources.go`, `fixtures.go` | Parse `data_sources.json` and Odds API responses |
| `log/slog` | `collector.go`, `fixtures.go` | Structured logging (stdlib, Go 1.21+) |
| `math/rand/v2` | `collector.go` | Poisson sample + noise for synthetic data and estimates |
| `net/http` | `collector.go`, `fixtures.go` | HTTP client with configurable timeouts |
| `bet4me/betting-algorithm-go/internal/storage` | `collector.go` | `storage.MatchRecord`, `storage.CSVStore` |

No new external dependencies were added. `go.mod` remains at Go 1.22 with existing deps (chi, godotenv, rs/cors, testify, gonum).

---

## Data Flow

```
CollectAllData(seasons, leagues, callback)
        │
        ├── Step 1: collectFootballDataUK(seasons, leagues)
        │       ├── for each (season, league): GET football-data.co.uk/{season}/{league}.csv
        │       ├── fetchAndParseCSV() — map column names, fill defaults
        │       └── fallback: generateSampleMatches() if zero records fetched
        │
        ├── Step 2: addXGData()
        │       └── HomeXG = shots*0.08 + shotsOnTarget*0.22  (capped [0,5])
        │
        ├── Step 3: calculateEloRatings()
        │       ├── sort records by Date ascending
        │       ├── for each match: snapshot HomeElo/AwayElo BEFORE update
        │       └── update ratings with K=32 after result
        │
        ├── Step 4: calculateTeamForm()
        │       ├── sort records by Date ascending
        │       ├── maintain rolling results per team
        │       └── HomeForm/AwayForm = last 5 results as "WWDLD" string (before this match)
        │
        ├── Step 5: calculateRestCongestion()
        │       ├── sort records by Date ascending
        │       ├── HomeRestDays/AwayRestDays = days since last match (default 7 if first match)
        │       └── HomeGamesLast7/AwayGamesLast7 = games in last 7 days + 1
        │
        ├── Step 6: addAdvancedStats()
        │       ├── HomePossession = homeShots / totalShots * 100, clamped [30,70]
        │       └── HomePPDA = 15 - (possession-50)*0.15 + noise, clamped [5,20]
        │
        ├── Step 7: calculateLeaguePositions()
        │       ├── group records by season
        │       ├── sort by date within each season
        │       └── snapshot league position BEFORE awarding points for this match
        │
        └── saveFinalDataset() — writes to {outputDir}/final/historical_dataset.csv

callback(step, current, total)  ← called at start of each step
```

---

## File-by-File Reference

### `collector.go` — Historical Data Pipeline

**Location:** `internal/data/collector.go` (730 lines)

#### Types

| Type | Purpose |
|------|---------|
| `ProgressCallback` | `func(step string, current, total int)` — called before each pipeline step |
| `CollectionStatus` | Plain struct tracking collection state: `Running bool`, `Progress int`, `Step string`, `Error string`, `Completed bool` |
| `HistoricalDataCollector` | Main pipeline runner. Holds `outputDir string`, `csvStore *storage.CSVStore`, `httpClient *http.Client`, `logger *slog.Logger`, `matches []storage.MatchRecord`, `eloRatings map[string]float64` |

#### `HistoricalDataCollector` constructor

```go
collector := data.NewHistoricalDataCollector(outputDir, httpClient, logger)
// outputDir = base directory for output (e.g. "./data")
// httpClient = optional, defaults to &http.Client{Timeout: 30s}
// logger = optional, defaults to slog.Default()
// Creates a storage.CSVStore internally from outputDir
// eloRatings = empty map (populated in Step 3)
```

#### Public methods

| Method | Returns | Description |
|--------|---------|-------------|
| `CollectAllData(seasons, leagues, callback)` | `([]storage.MatchRecord, error)` | Runs the 7-step pipeline synchronously; `seasons` defaults to `["2324","2223","2122","2021","1920"]`, `leagues` defaults to `["E0"]` |
| `GetDataSummary()` | `map[string]any` | Returns `total_matches`, `teams` count, `seasons` list, `date_range`; returns `{"error": "No data collected"}` if no matches |

#### Pipeline implementation

The 7 steps are defined as a slice of `{name string, fn func() error}` closures that operate on `c.matches`:

```go
steps := []step{
    {"Fetching match results & odds...",    func() error { return c.collectFootballDataUK(seasons, leagues) }},
    {"Adding expected goals (xG)...",       func() error { return c.addXGData() }},
    {"Calculating Elo ratings...",          func() error { return c.calculateEloRatings() }},
    {"Computing team form...",              func() error { return c.calculateTeamForm() }},
    {"Analyzing rest & congestion...",      func() error { return c.calculateRestCongestion() }},
    {"Adding advanced stats...",            func() error { return c.addAdvancedStats() }},
    {"Calculating league positions...",     func() error { return c.calculateLeaguePositions() }},
}
```

Progress is reported via `callback(step.name, stepIndex, len(steps))` at the start of each step.

#### `fetchAndParseCSV`

Maps football-data.co.uk column names to `storage.MatchRecord` fields:

| Source columns | Mapped key | MatchRecord field |
|----------------|------------|-------------------|
| `Date` | `Date` | `Date` |
| `HomeTeam` | `home_team` | `HomeTeam` |
| `AwayTeam` | `away_team` | `AwayTeam` |
| `FTHG` | `home_goals` | `HomeGoals` |
| `FTAG` | `away_goals` | `AwayGoals` |
| `B365H` | `home_odds` | `HomeOdds` |
| `B365D` | `draw_odds` | `DrawOdds` |
| `B365A` | `away_odds` | `AwayOdds` |
| `HS` | `home_shots` | `HomeShots` |
| `AS` | `away_shots` | `AwayShots` |
| `HST` | `home_shots_on_target` | `HomeShotsOnTarget` |
| `AST` | `away_shots_on_target` | `AwayShotsOnTarget` |

Default values when column is absent or empty:

| Field | Default |
|-------|---------|
| HomeOdds, DrawOdds, AwayOdds | 2.5 |
| HomeShots / AwayShots | 12 |
| HomeShotsOnTarget / AwayShotsOnTarget | 5 |

Season label is formatted as `"20" + season[:2] + "-" + season[2:]`, e.g. `"2324"` -> `"2023-24"`.
`MatchID` is set to the row index (0-based).

#### `generateSampleMatches` (fallback)

Generates 380 synthetic EPL-like matches when no real data is fetched. Uses `rand.NewPCG(42, 0)` for reproducibility (Go 1.22 `math/rand/v2`). Goals are sampled with `poissonSample(rng, 1.5)` (home) and `poissonSample(rng, 1.2)` (away). Matches span 2023-08-01 onwards, formatted `DD/MM/YYYY`.

#### Helper functions (in collector.go)

| Function | Signature | Used by |
|----------|-----------|---------|
| `clamp` | `(v, lo, hi float64) float64` | Steps 2, 5, 6 |
| `clampInt` | `(v, lo, hi int) int` | Step 5 |
| `getOrDefault` | `(m map[string]float64, key string, def float64) float64` | Step 3 |
| `lastN` | `(results []string, n int) string` | Step 4 |
| `parseDate` | `(s string) time.Time` | Steps 3, 4, 5 |
| `filterDatesAfter` | `(dates []time.Time, after time.Time) []time.Time` | Step 5 |
| `sortMatchesByDate` | `(matches []storage.MatchRecord)` | Steps 3, 4, 5 |
| `calculatePositions` | `(teamPoints map[string]int) map[string]int` | Step 7 |
| `getPositionOrDefault` | `(positions map[string]int, team string, def int) int` | Step 7 |
| `getCSVCol` | `(row []string, idx map[string]int, col string) string` | Step 1, fixtures.go |
| `getCSVColInt` | `(row []string, idx map[string]int, col string) int` | Step 1 |
| `getCSVColIntDefault` | `(row []string, idx map[string]int, col string, def int) int` | Step 1 |
| `getCSVColFloat` | `(row []string, idx map[string]int, col string, def float64) float64` | Step 1, fixtures.go |
| `poissonSample` | `(rng *rand.Rand, lambda float64) int` | Sample data |
| `roundTo` | `(v float64, decimals int) float64` | Sample data |

---

### `sources.go` — Data Sources Manager

**Location:** `internal/data/sources.go` (240 lines)

#### Types

| Type | JSON source | Purpose |
|------|-------------|---------|
| `League` | `sources[n].leagues[n]` | `Code`, `Name`, `Country`, `Tier` |
| `Season` | `sources[n].seasons[n]` | `Code` (e.g. "2324"), `Label`, `Years` |
| `DataSource` | `sources[n]` | Full source record including `URLPattern`, `ColumnMapping`, `RateLimitSeconds` |
| `DefaultConfig` | `default_config` | `Seasons []string`, `Leagues []string` |
| `DataSourcesConfig` | top-level | `Sources []DataSource`, `DefaultConfig` |
| `DataSourcesManager` | — | Query interface over loaded config |

#### Constructor: `NewDataSourcesManager(configPath string)`

Requires an explicit `configPath` parameter pointing to the `data_sources.json` file. Returns an error if the file cannot be read or JSON parsing fails.

```go
mgr, err := data.NewDataSourcesManager("./config/data_sources.json")
```

#### Public methods

| Method | Returns | Description |
|--------|---------|-------------|
| `GetEnabledSources()` | `[]DataSource` | All sources with `Enabled == true` |
| `GetSourceByID(id)` | `*DataSource` | Pointer into config slice; nil if not found |
| `GetAvailableLeagues(sourceID)` | `[]League` | All leagues for the source |
| `GetAvailableSeasons(sourceID)` | `[]Season` | All seasons for the source |
| `GetDefaultConfig()` | `DefaultConfig` | Top-level defaults from JSON |
| `GetURLPattern(sourceID)` | `string` | Raw pattern string |
| `GetColumnMapping(sourceID)` | `map[string]string` | Source column -> internal name map |
| `GetLeaguesByCountry(country, sourceID)` | `[]League` | Case-insensitive country filter |
| `GetTopTierLeagues(sourceID)` | `[]League` | Only leagues with `Tier == 1` |
| `GetRecentSeasons(sourceID, count)` | `[]Season` | First N seasons from config |
| `FormatURL(sourceID, season, league)` | `string` | Substitutes `{base_url}`, `{season}`, `{league}` into pattern |
| `GetSourceMetadata(sourceID)` | `map[string]any` | id, name, description, type, enabled, requires_api_key, sports |
| `GetAllSourcesMetadata()` | `[]map[string]any` | Metadata for every configured source |
| `SaveConfig()` | `error` | Writes current config back to file |
| `EnableSource(sourceID)` | — | Sets `Enabled = true` on the source |
| `DisableSource(sourceID)` | — | Sets `Enabled = false` on the source |

#### `FormatURL` example

```go
mgr, _ := data.NewDataSourcesManager("./config/data_sources.json")
url := mgr.FormatURL("football-data-uk", "2324", "E0")
// -> "https://www.football-data.co.uk/mmz4281/2324/E0.csv"
```

---

### `fixtures.go` — Live Fixtures Fetcher

**Location:** `internal/data/fixtures.go` (416 lines)

#### Types

| Type | Purpose |
|------|---------|
| `FixtureMatch` | Normalized fixture with best available odds. Fields: `ID`, `Sport`, `CommenceTime`, `HomeTeam`, `AwayTeam`, `HomeOdds`, `DrawOdds`, `AwayOdds`, `Bookmakers` (count), `Source`, `League`, `Season`, `HomeGoals *int`, `AwayGoals *int` |
| `LiveFixturesFetcher` | Main fetcher; holds `oddsAPIKey`, `apiFootballKey`, `httpClient`, `logger` |
| `oddsAPIEvent` | Wire type for Odds API JSON: `{id, sport_key, commence_time, home_team, away_team, bookmakers[]}` |
| `oddsBookmaker` | `{key, title, markets[]}` |
| `oddsMarket` | `{key, outcomes[]}` |
| `oddsOutcome` | `{name, price}` |

#### Constructor

```go
fetcher := data.NewLiveFixturesFetcher(oddsAPIKey, apiFootballKey, httpClient, logger)
// oddsAPIKey = API key for The Odds API (empty string disables)
// apiFootballKey = API key for API-Football (currently unused)
// httpClient = optional, defaults to &http.Client{Timeout: 10s}
// logger = optional, defaults to slog.Default()
```

#### Public methods

| Method | Returns | Description |
|--------|---------|-------------|
| `GetUpcomingMatches(sport, daysAhead)` | `([]FixtureMatch, error)` | Fetches from Odds API; filters to `now < matchTime < now + daysAhead`; defaults: sport=`"soccer_epl"`, daysAhead=`7`; returns nil if no API key |
| `GetCurrentSeasonResults(league)` | `([]FixtureMatch, error)` | Fetches completed matches from football-data.co.uk for the current season; defaults league to `"E0"` |
| `GetLiveOddsForMatch(home, away, sport)` | `(*FixtureMatch, error)` | Fuzzy team-name match over next 30 days; returns nil if not found |
| `GetAvailableSports()` | `([]map[string]any, error)` | Lists sports from `/v4/sports`; returns nil if no API key |
| `GetQuotaUsage()` | `(map[string]string, error)` | Reads `x-requests-remaining/used/limit` headers; returns nil if no API key |

#### The Odds API request (internal `fetchFromOddsAPI`)

```
GET https://api.the-odds-api.com/v4/sports/{sport}/odds
  ?apiKey=<oddsAPIKey>
  &regions=uk,eu
  &markets=h2h
  &oddsFormat=decimal
```

`extractBestOdds` scans all bookmakers for the `h2h` market and returns the **maximum price** for each outcome (home, draw, away).

#### Football-Data.co.uk current season (internal `fetchFromFootballDataUK`)

Downloads CSV for a single league for the auto-computed current season code.

`currentSeasonCode` logic:
```go
if now.Month() >= 8 {   // August onwards -> current year pair
    seasonCode = fmt.Sprintf("%02d%02d", now.Year()%100, (now.Year()+1)%100)
} else {                 // before August -> previous year pair
    seasonCode = fmt.Sprintf("%02d%02d", (now.Year()-1)%100, now.Year()%100)
}
```

Uses `parseFootballDataCSV(body io.Reader, league, seasonCode)` which parses the CSV into `[]FixtureMatch` records, mapping `B365H`/`BWH` -> `HomeOdds`, `B365D`/`BWD` -> `DrawOdds`, `B365A`/`BWA` -> `AwayOdds`, and `FTHG`/`FTAG` -> `HomeGoals`/`AwayGoals` (as `*int` pointers, nil if absent).

#### Time parsing (`parseMatchTime` in fixtures.go)

Handles three formats, tried in order:
1. **ISO 8601** with `T`/`Z`/`+` — parsed with `time.RFC3339` and `"2006-01-02T15:04:05Z"`
2. **DD/MM/YYYY** — e.g. `"25/02/2024"` from football-data.co.uk
3. **DD/MM/YY** — e.g. `"25/02/24"` from older files

All results returned in UTC. Returns zero `time.Time` on failure.

#### Team name normalization (`normalizeTeamName`)

```go
strings.ToLower(strings.ReplaceAll(strings.TrimSpace(name), " ", ""))
// "Man City" -> "mancity"
// " Arsenal " -> "arsenal"
```

Used for fuzzy match in `GetLiveOddsForMatch`.

#### Helper functions unique to fixtures.go

| Function | Purpose |
|----------|---------|
| `csvColIntPtr` | Parses a CSV column as `*int` (nil if empty/invalid) |

Shared helpers from collector.go (same package): `getCSVCol`, `getCSVColFloat`.

---

## MatchRecord Field Reference

The `storage.MatchRecord` struct (defined in `internal/storage/csv.go`) has 30 fields. These fields were already present from Phase 1 — no modifications were needed.

| # | Field | Type | Set in step | Notes |
|---|-------|------|-------------|-------|
| 1 | `Date` | string | 1 | DD/MM/YYYY from source |
| 2 | `Season` | string | 1 | e.g. "2023-24" |
| 3 | `HomeTeam` | string | 1 | Team name from source |
| 4 | `AwayTeam` | string | 1 | |
| 5 | `HomeGoals` | int | 1 | Final score |
| 6 | `AwayGoals` | int | 1 | |
| 7 | `HomeOdds` | float64 | 1 | From B365H column (default 2.5) |
| 8 | `DrawOdds` | float64 | 1 | From B365D column (default 2.5) |
| 9 | `AwayOdds` | float64 | 1 | From B365A column (default 2.5) |
| 10 | `HomeShots` | int | 1 | From HS column (default 12) |
| 11 | `AwayShots` | int | 1 | From AS column (default 12) |
| 12 | `HomeShotsOnTarget` | int | 1 | From HST column (default 5) |
| 13 | `AwayShotsOnTarget` | int | 1 | From AST column (default 5) |
| 14 | `MatchID` | int | 1 | Row index (0-based) |
| 15 | `HomeXG` | float64 | 2 | Estimated from shots |
| 16 | `AwayXG` | float64 | 2 | |
| 17 | `HomeElo` | float64 | 3 | Rating **before** match |
| 18 | `AwayElo` | float64 | 3 | |
| 19 | `HomeForm` | string | 4 | Last 5 results e.g. "WWDLD" |
| 20 | `AwayForm` | string | 4 | |
| 21 | `HomeRestDays` | int | 5 | Days since last match [1, 30] |
| 22 | `AwayRestDays` | int | 5 | |
| 23 | `HomeGamesLast7` | int | 5 | Games in last 7 days (incl. this) |
| 24 | `AwayGamesLast7` | int | 5 | |
| 25 | `HomePossession` | float64 | 6 | Estimated [30, 70] |
| 26 | `AwayPossession` | float64 | 6 | |
| 27 | `HomePPDA` | float64 | 6 | Estimated [5, 20] |
| 28 | `AwayPPDA` | float64 | 6 | |
| 29 | `HomePosition` | int | 7 | League position before match |
| 30 | `AwayPosition` | int | 7 | |

---

## The 7-Step Enrichment Pipeline

### Step 1 — Fetch (football-data.co.uk)

- Downloads `{base}/{season}/{league}.csv` for each (season, league) pair
- Pauses 500ms between requests to avoid overloading the server
- Falls back to 380 Poisson-sampled synthetic matches if all downloads fail
- Columns mapped via `colMap` in `fetchAndParseCSV`
- Uses `csv.NewReader` with `LazyQuotes = true` and `FieldsPerRecord = -1`

### Step 2 — xG Estimation

```
If shots > 0 AND shotsOnTarget > 0:
    HomeXG = clamp(homeShots * 0.08 + homeShotsOnTarget * 0.22, 0, 5)
    AwayXG = clamp(awayShots * 0.08 + awayShotsOnTarget * 0.22, 0, 5)
Else:
    HomeXG = clamp(homeGoals + (rand.Float64() - 0.5), 0, 5)
    AwayXG = clamp(awayGoals + (rand.Float64() - 0.5), 0, 5)
```

The fallback uses global `rand.Float64()` (not seeded deterministically).

### Step 3 — Elo Ratings

- Records are sorted ascending by `Date` via `sortMatchesByDate` before processing
- Starting rating: 1500 for all teams
- K-factor: 32
- `HomeElo` / `AwayElo` on each record captures the team's rating **before** the match result is applied
- Final rating map is saved to `c.eloRatings` for potential reuse

```
expected_home = 1 / (1 + 10^((awayElo - homeElo) / 400))
new_homeElo   = homeElo + 32 * (actual - expected)
actual: W=1.0, D=0.5, L=0.0
```

### Step 4 — Team Form

- Sorts records by date, maintains `teamResults map[string][]string` with running per-team result history
- `HomeForm` = concatenated last 5 results **before** this match (via `lastN` helper)
- Defaults to `"DDDDD"` for teams with fewer than 5 prior results
- Result appended after form is recorded, so form correctly represents pre-match state

### Step 5 — Rest & Congestion

- Sorts records by date
- `HomeRestDays` = days since the home team's last match (clamped to `[1, 30]`; default 7 for first match or unparseable date)
- `HomeGamesLast7` = number of matches in the 7 days before this match **plus 1** (this match)
- Date parsing attempts formats: `DD/MM/YYYY`, `YYYY-MM-DD`, `DD/MM/YY`, `YYYY-MM-DDT15:04:05Z`
- `filterDatesAfter` trims the recent-games list to only keep entries within 30 days

### Step 6 — Advanced Stats (Estimated)

Possession estimated from shot share:
```
totalShots = homeShots + awayShots  (defaults to 24 if zero)
homePoss = clamp(homeShots / totalShots * 100, 30, 70)
awayPoss = 100 - homePoss
```

PPDA estimated inversely from possession:
```
HomePPDA = clamp(15 - (homePoss - 50) * 0.15 + (rand.Float64()*4 - 2), 5, 20)
```
- Noise is uniform `[-2, +2]` using global `rand.Float64()` (not deterministic across runs)

### Step 7 — League Positions

- Records grouped by `Season` string, indices sorted by `Date` within each season
- `HomePosition` / `AwayPosition` = 1-based sequential rank by points **before** this match
- `calculatePositions` sorts teams by points descending and assigns sequential ranks (rank 1, 2, 3...; ties get different ranks based on sort order)
- Default position is 10 if team not yet in the points table
- Points awarded after position recorded: Win +3, Draw +1, Loss +0

---

## External Data Sources

### football-data.co.uk

| Property | Value |
|----------|-------|
| Base URL | `https://www.football-data.co.uk/mmz4281` |
| URL pattern | `{base_url}/{season}/{league}.csv` |
| Season format | 4-digit e.g. `"2324"` for 2023-24 |
| Rate limit | 500ms between requests (polite crawling) |
| Auth required | No |
| Data type | Historical completed matches with odds and shot stats |

### The Odds API

| Property | Value |
|----------|-------|
| Base URL | `https://api.the-odds-api.com/v4` |
| Auth | `oddsAPIKey` passed to constructor |
| Regions | `uk,eu` |
| Market | `h2h` (1X2 decimal odds) |
| Quota headers | `x-requests-remaining`, `x-requests-used`, `x-requests-limit` |
| Data type | Upcoming fixtures with live bookmaker odds |

---

## Configuration: data_sources.json

Located at `betting-algorithm-go/config/data_sources.json` (copied from `betting-algorithm/config/`).

**Top-level structure:**

```json
{
  "sources": [ DataSource, ... ],
  "default_config": {
    "seasons": ["2324", "2223", "2122"],
    "leagues": ["E0"]
  }
}
```

**Each DataSource includes:**
- `id`, `name`, `enabled`, `type`, `description`
- `base_url`, `url_pattern`
- `rate_limit_seconds`, `timeout_seconds`
- `sports []string`
- `requires_api_key bool`
- `leagues []League` — each with `code`, `name`, `country`, `tier`
- `seasons []Season` — each with `code`, `label`, `years`
- `column_mapping map[string]string`

---

## Key Algorithms Explained

### xG Estimation from Shot Data

Expected goals are not provided by football-data.co.uk. We approximate using a linear model:

```
xG = shots * 0.08 + shotsOnTarget * 0.22
```

This weights shots on target approximately 2.75x more heavily than off-target shots. Values are clamped to `[0, 5]`.

### Elo Sequential Update

Records are sorted by date before processing. The `eloRatings` map persists on the `HistoricalDataCollector` after `CollectAllData` completes.

### Form String Construction

Form strings are constructed in chronological order: oldest result at index 0, most recent at the end. `"WWDLD"` means the last game was D, the game before was L, etc.

### Rest & Congestion Calculation

Maintains two maps per team:
- `teamLastMatch map[string]time.Time` — date of last played match
- `teamRecentGames map[string][]time.Time` — dates of matches within past 30 days

`filterDatesAfter` is called after each match to prune entries older than 30 days.

### Possession Estimation from Shot Share

Shot share is a reasonable proxy for possession. Clamping to [30, 70] prevents extreme values.

### PPDA Estimation

```
PPDA = 15 - (possession - 50) * 0.15 + noise[-2, +2]
       clamped to [5, 20]
```

At 50% possession: PPDA ~ 15 (mid-table pressing)
At 60% possession: PPDA ~ 13.5 (more pressing)
At 40% possession: PPDA ~ 16.5 (less pressing)

### Poisson Sample (Sample Data)

Knuth inversion method for Poisson sampling, used in `generateSampleMatches`:

```go
func poissonSample(rng *rand.Rand, lambda float64) int {
    L := math.Exp(-lambda)
    k := 0
    p := 1.0
    for {
        k++
        p *= rng.Float64()
        if p < L { break }
    }
    return k - 1
}
```

---

## Error Handling & Fallback Strategy

| Failure scenario | Behaviour |
|-----------------|-----------|
| HTTP timeout/error on `fetchAndParseCSV` | Logged as warning; that season/league is skipped; collection continues |
| All seasons/leagues fail | `generateSampleMatches()` used as fallback (380 synthetic EPL matches) |
| `os.ReadFile` fails for config path | `NewDataSourcesManager` returns error |
| Odds API key empty | `GetUpcomingMatches` returns nil, nil (not an error) |
| Odds API HTTP non-200 | Error returned with status code |
| Date parse failure in Step 5 | Record gets `HomeRestDays/AwayRestDays = 7`, `HomeGamesLast7/AwayGamesLast7 = 1` |
| Step N failure | Pipeline returns error wrapped as `"step N (name): underlying error"` |
| Save failure after Step 7 | Error returned — `saveFinalDataset` failure is fatal |

---

## Go vs Python Differences

| Concern | Python | Go |
|---------|--------|----|
| **DataFrame** | `pd.DataFrame` with `.loc[]`, `.apply()` | `[]storage.MatchRecord` typed slice with for-loops |
| **HTTP** | `requests.get(url)` | `http.Client.Get(url)` with timeout |
| **Date parsing** | `datetime.strptime(s, fmt)` with try/except | Sequential format attempts; returns `time.Time{}` on failure |
| **Poisson sample** | `numpy.random.poisson(lambda)` | Knuth inversion method using `math/rand/v2` |
| **Progress** | Callback / print | `ProgressCallback func(step string, current, total int)` |
| **Config loading** | `json.load(open(path))` | `os.ReadFile(path)` + `json.Unmarshal` |
| **Odds extraction** | `max(...)` on list comprehension | Imperative max-tracking loop over bookmakers |
| **Rate limiting** | `time.sleep(0.5)` | `time.Sleep(500 * time.Millisecond)` |
| **Logging** | `print(f"...")` | `slog.Info(...)` / `slog.Warn(...)` |
| **Default seasons** | `['2324', '2223', '2122']` | `["2324", "2223", "2122", "2021", "1920"]` (5 seasons) |
| **Random** | `random` / `numpy.random` | `math/rand/v2` with `rand.NewPCG(42, 0)` for sample data |

---

## Known Limitations & TODOs

1. **xG and possession are estimates, not real data.** Accuracy will improve if FBref scraping is implemented.

2. **PPDA noise is not deterministic.** Uses global `rand.Float64()`, so PPDA values will differ across runs. Only `generateSampleMatches` uses a seeded RNG.

3. **`calculatePositions` assigns sequential ranks, not tied ranks.** Teams with equal points get different positions depending on sort order.

4. **Season label format inconsistency.** `fetchAndParseCSV` writes `Season` as `"2023-24"` (hyphenated), but football-data.co.uk uses `"2324"` as the season code.

5. **`GetCurrentSeasonResults` returns `FixtureMatch`, not `storage.MatchRecord`.** A conversion function may be needed to feed this into the collection pipeline.

6. **No retry logic.** Failed HTTP requests are silently skipped.

7. **`DataSourcesManager.FormatURL` is not used by `collector.go`.** The collector hardcodes the football-data.co.uk URL pattern.

8. **No caching layer.** Config fields for caching are parsed but not used.

9. **`HistoricalDataCollector` is not safe for concurrent use.** Multiple concurrent calls to `CollectAllData` would both write to `c.matches` and `c.eloRatings`. Create separate instances if needed.

---

## Testing Strategy

### Unit Tests (collector_test.go)

| Test | Target | Assertion |
|------|--------|-----------|
| `TestGenerateSampleMatches` | `generateSampleMatches` | 380 matches, season "2023-24", non-empty distinct teams |
| `TestAddXGData` | `addXGData` | All xG values in [0, 5] |
| `TestCalculateEloRatings` | `calculateEloRatings` | All HomeElo/AwayElo > 0; eloRatings map populated |
| `TestCalculateTeamForm` | `calculateTeamForm` | Non-empty form strings; only W/D/L characters |
| `TestCalculateRestCongestion` | `calculateRestCongestion` | RestDays in [1, 30]; GamesLast7 >= 1 |
| `TestAddAdvancedStats` | `addAdvancedStats` | Possession in [30, 70]; HomePoss + AwayPoss = 100; PPDA in [5, 20] |
| `TestCalculateLeaguePositions` | `calculateLeaguePositions` | All positions >= 1 |
| `TestGetDataSummary_NoData` | `GetDataSummary` | Contains "error" key |
| `TestGetDataSummary_WithData` | `GetDataSummary` | total_matches=380, contains seasons/teams/date_range |
| `TestClamp` | `clamp` | Below/within/above range |
| `TestClampInt` | `clampInt` | Below/within/above range |
| `TestParseDate` | `parseDate` | DD/MM/YYYY, YYYY-MM-DD, invalid -> zero |
| `TestParseMatchTime` | `parseMatchTime` | ISO 8601, DD/MM/YYYY, empty -> zero |
| `TestNormalizeTeamName` | `normalizeTeamName` | Lowercased, spaces removed, trimmed |
| `TestExtractBestOdds` | `extractBestOdds` | Returns max odds across 2 bookmakers |
| `TestPoissonSample` | `poissonSample` | 100 samples all >= 0 |
