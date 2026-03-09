# Phase 3: Data Pipeline — Implementation Reference

> **Status:** Complete
> **Branch:** `feature/jackpot-selenium`
> **Packages created:** `internal/data`
> **Packages modified:** `internal/storage`
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
   - [storage/csv.go — Extended MatchRecord](#storagecsvgoextended-matchrecord)
5. [The 7-Step Enrichment Pipeline](#the-7-step-enrichment-pipeline)
6. [MatchRecord Field Reference](#matchrecord-field-reference)
7. [External Data Sources](#external-data-sources)
8. [Configuration: data_sources.json](#configuration-data_sourcesjson)
9. [Key Algorithms Explained](#key-algorithms-explained)
   - [xG Estimation from Shot Data](#xg-estimation-from-shot-data)
   - [Elo Sequential Update](#elo-sequential-update)
   - [Form String Construction](#form-string-construction)
   - [Rest & Congestion Calculation](#rest--congestion-calculation)
   - [Possession Estimation from Shot Share](#possession-estimation-from-shot-share)
   - [PPDA Estimation](#ppda-estimation)
   - [League Position Tracking](#league-position-tracking)
   - [Poisson Sample (Sample Data)](#poisson-sample-sample-data)
10. [Error Handling & Fallback Strategy](#error-handling--fallback-strategy)
11. [Thread Safety & Async Collection](#thread-safety--async-collection)
12. [Go vs Python Differences](#go-vs-python-differences)
13. [Storage Changes (csv.go)](#storage-changes-csvgo)
14. [Known Limitations & TODOs](#known-limitations--todos)
15. [Testing Strategy](#testing-strategy)

---

## Overview

Phase 3 ports the entire Python data pipeline (`data_collector.py`, `data_sources_manager.py`, `live_fixtures_fetcher.py`) into Go. The result is a **self-contained, context-cancellable, asynchronous data collection system** that:

- Fetches raw match CSVs from football-data.co.uk for configurable seasons and leagues
- Enriches each match record through a **7-step sequential pipeline** (xG → Elo → Form → Rest → Advanced Stats → Positions)
- Saves the final enriched dataset to `data/final/historical_dataset.csv`
- Reports real-time progress via a thread-safe `CollectionStatus` struct
- Provides a config-driven `DataSourcesManager` for discovering leagues, seasons, and URL patterns
- Provides a `LiveFixturesFetcher` for pulling upcoming matches and live odds from The Odds API

The enriched data directly feeds Phase 2's `context/builder.go` methods (`BuildH2HRecordFromMatches`, `CalculateSeasonStatsFromMatches`) which power the contextual V2 prediction factors.

---

## Package Structure

```
betting-algorithm-go/
├── internal/
│   ├── data/
│   │   ├── collector.go     HistoricalDataCollector — async 7-step pipeline + sample data
│   │   ├── sources.go       DataSourcesManager — loads & queries data_sources.json config
│   │   └── fixtures.go      LiveFixturesFetcher — The Odds API + football-data.co.uk current season
│   └── storage/
│       └── csv.go           MatchRecord (extended) + CSVStore read/write (MODIFIED)
└── config/
    └── data_sources.json    (lives in betting-algorithm/config/ — searched by candidate paths)
```

**Dependencies introduced in Phase 3:**

| Package | Used in | Purpose |
|---------|---------|---------|
| `context` | `collector.go` | `context.Context` for cancellation |
| `encoding/csv` | `collector.go`, `fixtures.go` | Parse CSV streams from HTTP responses |
| `encoding/json` | `sources.go`, `fixtures.go` | Parse `data_sources.json` and Odds API responses |
| `log/slog` | `collector.go`, `fixtures.go` | Structured logging (stdlib, Go 1.21+) |
| `math/rand` | `collector.go` | Poisson sample for synthetic data generation |
| `net/http` | `collector.go`, `fixtures.go` | HTTP client with configurable timeouts |
| `sync` | `collector.go` | `sync.RWMutex` in `CollectionStatus` |
| `github.com/bet4me/betting-algorithm-go/internal/storage` | `collector.go` | `storage.MatchRecord`, `storage.CSVStore` |

No new external dependencies were added. `go.mod` remains at Go 1.23.6 with no `require` entries.

---

## Data Flow

```
StartCollection(ctx, seasons, leagues)
    │
    └─► goroutine: runPipelineReturning()
            │
            ├── Step 1: fetchFootballDataUK()
            │       ├── for each (season, league): GET football-data.co.uk/{season}/{league}.csv
            │       ├── parseFootballDataCSV() — map column names, fill defaults
            │       └── fallback: generateSampleMatches() if zero records fetched
            │
            ├── Step 2: addXGData()
            │       └── HomeXG = shots×0.08 + shotsOnTarget×0.22  (capped [0,5])
            │
            ├── Step 3: calculateEloRatings()
            │       ├── sort records by Date ascending
            │       ├── for each match: snapshot HomeElo/AwayElo BEFORE update
            │       └── update ratings with K=32 after result
            │
            ├── Step 4: calculateTeamForm()
            │       ├── maintain rolling results per team
            │       └── HomeForm/AwayForm = last 5 results as "WWDLD" string (before this match)
            │
            ├── Step 5: calculateRestCongestion()
            │       ├── RestDaysH/A = days since last match (default 7 if first match)
            │       └── HomeCongestion/AwayCongestion = games in last 7 days + 1
            │
            ├── Step 6: addAdvancedStats()
            │       ├── HomePossession = homeShots / totalShots × 100, clamped [30,70]
            │       └── HomePPDA = 15 − (possession−50)×0.15 + noise, clamped [5,20]
            │
            ├── Step 7: calculateLeaguePositions()
            │       ├── group records by season
            │       ├── sort by date within each season
            │       └── snapshot league position BEFORE awarding points for this match
            │
            └── store.WriteHistoricalData("final/historical_dataset.csv", records)

CollectionStatus.Read() ← polled by API layer for progress (0–100%)
```

---

## File-by-File Reference

### `collector.go` — Historical Data Pipeline

**Location:** `internal/data/collector.go`

#### Types

| Type | Purpose |
|------|---------|
| `CollectionStatus` | Thread-safe progress tracker. Fields: `Running bool`, `Progress int` (0–100), `Step string`, `Error string`, `Completed bool` |
| `HistoricalDataCollector` | Main pipeline runner. Holds `store *storage.CSVStore`, `httpClient *http.Client`, `eloRatings map[string]float64` |

#### `CollectionStatus` methods

| Method | Description |
|--------|-------------|
| `set(step, progress)` | Write-locked update during pipeline execution |
| `finish(err)` | Write-locked; sets `Running=false`, `Completed=true`, populates `Error` if non-nil |
| `Read() CollectionStatus` | Read-locked snapshot safe to call from any goroutine |

#### `HistoricalDataCollector` constructor

```go
collector := data.NewHistoricalDataCollector(store)
// store = storage.NewCSVStore("./data")
// httpClient timeout = 30s
// eloRatings = empty map (populated in Step 3, retained for Phase 5 use)
```

#### Public methods

| Method | Returns | Description |
|--------|---------|-------------|
| `StartCollection(ctx, seasons, leagues)` | `*CollectionStatus` | Launches pipeline as goroutine; `seasons`/`leagues` default to `["2425","2324","2223","2122","2021"]` / `["E0"]` |
| `CollectSync(ctx, seasons, leagues)` | `([]storage.MatchRecord, error)` | Synchronous variant; same pipeline, returns all records |
| `GetDataSummary(records)` | `map[string]interface{}` | Returns `total_matches`, `teams` count, `seasons` list, `date_range` |

#### Pipeline implementation

The 7 steps are defined as a slice of `{name string, fn func([]MatchRecord)([]MatchRecord, error)}`:

```go
steps := []struct{...}{
    {"Fetching match results & odds...",    fetchFootballDataUK},
    {"Adding expected goals (xG)...",       addXGData},
    {"Calculating Elo ratings...",          calculateEloRatings},
    {"Computing team form...",              calculateTeamForm},
    {"Analyzing rest & congestion...",      calculateRestCongestion},
    {"Adding advanced stats...",            addAdvancedStats},
    {"Calculating league positions...",     calculateLeaguePositions},
}
```

Progress is reported as `(stepIndex × 100) / 7` at the start of each step. Context cancellation is checked before every step via `select { case <-ctx.Done(): }`.

#### `parseFootballDataCSV`

Maps football-data.co.uk column names to `storage.MatchRecord` fields:

| Source columns | MatchRecord field |
|----------------|-------------------|
| `Date` | `Date` |
| `HomeTeam` | `HomeTeam` |
| `AwayTeam` | `AwayTeam` |
| `FTHG`, `HG` | `HomeGoals` |
| `FTAG`, `AG` | `AwayGoals` |
| `B365H`, `PSH`, `BWH` | `HomeOdds` (first non-empty wins) |
| `B365D`, `PSD`, `BWD` | `DrawOdds` |
| `B365A`, `PSA`, `BWA` | `AwayOdds` |
| `HS` | `HomeShots` |
| `AS` | `AwayShots` |
| `HST` | `HomeShotsOnTarget` |
| `AST` | `AwayShotsOnTarget` |
| `FTR` | `Result` |

Default values applied when zero (absent from source):

| Field | Default |
|-------|---------|
| HomeOdds | 2.5 |
| DrawOdds | 3.3 |
| AwayOdds | 2.8 |
| HomeShots / AwayShots | 12 |
| HomeShotsOnTarget / AwayShotsOnTarget | 5 |

Season label is formatted as `"20" + season[:2] + "-" + season[2:]`, e.g. `"2324"` → `"2023-24"`.

#### `generateSampleMatches` (fallback)

Generates 380 synthetic EPL-like matches when no real data is fetched. Uses a seeded `rand.New(rand.NewSource(42))` for reproducibility. Goals are sampled with `poissonSample(rng, 1.5)` (home) and `poissonSample(rng, 1.2)` (away). Matches span 2023-08-01 onwards, formatted `DD/MM/YYYY`.

---

### `sources.go` — Data Sources Manager

**Location:** `internal/data/sources.go`

#### Types

| Type | JSON source | Purpose |
|------|-------------|---------|
| `LeagueInfo` | `sources[n].leagues[n]` | Code, Name, Country, Tier |
| `SeasonInfo` | `sources[n].seasons[n]` | Code (e.g. "2324"), Label, StartYear, EndYear |
| `DataSource` | `sources[n]` | Full source record including URLPattern, ColumnMapping, RateLimitSecs |
| `DefaultConfig` | `default_config` | DefaultSport, DefaultLeagues, DefaultSeasons, CacheDirectory, RetryAttempts |
| `DataSourcesManager` | — | Query interface over loaded config |

#### Constructor: `NewDataSourcesManager(configPath string)`

If `configPath == ""`, searches these paths in order:

```
./config/data_sources.json
../config/data_sources.json
../../config/data_sources.json
../../betting-algorithm/config/data_sources.json
```

The fourth path handles the case where the Go project is run from inside `betting-algorithm-go/` and the config lives in the sibling Python project directory.

Returns an error if no path yields a readable file or if JSON parsing fails.

#### Public methods

| Method | Returns | Description |
|--------|---------|-------------|
| `GetEnabledSources()` | `[]DataSource` | All sources with `enabled == true` |
| `GetSourceByID(id)` | `*DataSource` | Pointer into config slice; nil if not found |
| `GetAvailableLeagues(sourceID)` | `[]LeagueInfo` | All leagues; defaults to `"football-data-uk"` |
| `GetAvailableSeasons(sourceID)` | `[]SeasonInfo` | All seasons; newest-first as per config |
| `GetDefaultConfig()` | `DefaultConfig` | Top-level defaults from JSON |
| `GetURLPattern(sourceID)` | `string` | Raw pattern string, e.g. `"{base_url}/{season}/{league}.csv"` |
| `GetColumnMapping(sourceID)` | `map[string]string` | Source column → internal name map |
| `GetLeaguesByCountry(country, sourceID)` | `[]LeagueInfo` | Case-insensitive country filter |
| `GetTopTierLeagues(sourceID)` | `[]LeagueInfo` | Only leagues with `tier == 1` |
| `GetRecentSeasons(count, sourceID)` | `[]SeasonInfo` | First N seasons (newest first) |
| `FormatURL(sourceID, season, league)` | `string` | Substitutes `{base_url}`, `{season}`, `{league}` into pattern |
| `GetSourceMetadata(sourceID)` | `map[string]interface{}` | id, name, description, type, enabled, requires_api_key, sports |
| `GetAllSourcesMetadata()` | `[]map[string]interface{}` | Metadata for every configured source |

#### `FormatURL` example

```go
mgr, _ := data.NewDataSourcesManager("")
url := mgr.FormatURL("football-data-uk", "2324", "E0")
// → "https://www.football-data.co.uk/mmz4281/2324/E0.csv"
```

---

### `fixtures.go` — Live Fixtures Fetcher

**Location:** `internal/data/fixtures.go`

#### Types

| Type | Purpose |
|------|---------|
| `UpcomingMatch` | Normalized fixture with best available odds. Fields: `ID`, `Sport`, `CommenceTime`, `HomeTeam`, `AwayTeam`, `HomeOdds`, `DrawOdds`, `AwayOdds`, `Bookmakers` (count), `Source`, `League`, `Season` |
| `QuotaUsage` | Response-header fields from Odds API: `RequestsRemaining`, `RequestsUsed`, `RequestsLimit` |
| `LiveFixturesFetcher` | Main fetcher; holds `oddsAPIKey`, `apiFootballKey` (both from env), `httpClient` (15s timeout) |

#### Constructor

```go
fetcher := data.NewLiveFixturesFetcher()
// Reads ODDS_API_KEY and API_FOOTBALL_KEY from environment
// http.Client timeout = 15s
```

#### Public methods

| Method | Returns | Description |
|--------|---------|-------------|
| `GetUpcomingMatches(sport, daysAhead)` | `([]UpcomingMatch, error)` | Fetches from Odds API; filters to `now < matchTime < now + daysAhead days`; returns nil if no API key or no matches |
| `GetCurrentSeasonResults(league)` | `([]UpcomingMatch, error)` | Fetches completed matches from football-data.co.uk for the current season; filters by league code and non-zero homeOdds |
| `GetLiveOddsForMatch(home, away, sport)` | `*UpcomingMatch` | Fuzzy team-name match over next 30 days; returns nil if not found |
| `GetAvailableSports()` | `([]map[string]interface{}, error)` | Lists sports from `/v4/sports`; returns nil if no API key |
| `GetQuotaUsage()` | `(*QuotaUsage, error)` | Reads `x-requests-remaining/used/limit` headers; returns nil if no API key |

#### The Odds API request (internal `fetchFromOddsAPI`)

```
GET https://api.the-odds-api.com/v4/sports/{sport}/odds
  ?apiKey=<ODDS_API_KEY>
  &regions=uk,eu
  &markets=h2h
  &oddsFormat=decimal
```

Wire types used for JSON decoding:
- `oddsAPIEvent` → `{id, commence_time, home_team, away_team, bookmakers[]}`
- `oddsAPIBookmaker` → `{key, markets[]}`
- `oddsAPIMarket` → `{key, outcomes[]}`
- `oddsAPIOutcome` → `{name, price}`

`extractBestOdds` scans all bookmakers for the `h2h` market and returns the **maximum price** for each outcome — this is best-odds selection rather than average.

#### Football-Data.co.uk current season (internal `fetchFromFootballDataUK`)

Downloads 6 leagues for the auto-computed current season code:
`["E0", "E1", "SP1", "D1", "I1", "F1"]`

`currentSeasonCode()` logic:
```go
year := time.Now().Year()
if time.Now().Month() < 8 {   // before August → still previous season
    year--
}
return year[2:] + (year+1)[2:]   // e.g. 2024-25 → "2425"
```

#### Time parsing (`parseMatchTime`)

Handles three formats, tried in order:
1. **ISO 8601** with `T` separator or `+`/`Z` suffix — parsed with `time.RFC3339` after replacing trailing `Z` with `+00:00`
2. **DD/MM/YYYY** — e.g. `"25/02/2024"` from football-data.co.uk
3. **DD/MM/YY** — e.g. `"25/02/24"` from older football-data files

All results returned in UTC.

#### Team name normalization (`normalizeTeamName`)

```go
strings.ToLower(strings.ReplaceAll(name, " ", ""))
// "Man City" → "manchestercity" (not expected to match, just compares consistently)
// "Arsenal"  → "arsenal"
```

Used only for fuzzy match in `GetLiveOddsForMatch`.

---

### `storage/csv.go` — Extended MatchRecord

**Location:** `internal/storage/csv.go`

**This file was modified during Phase 3** to add 11 new fields required by the enrichment pipeline.

#### Fields added to `MatchRecord`

| Field | Type | JSON key | Populated by |
|-------|------|----------|-------------|
| `HomeShots` | `int` | `home_shots` | Step 1 (raw from CSV, `HS` column) |
| `AwayShots` | `int` | `away_shots` | Step 1 (`AS`) |
| `HomeShotsOnTarget` | `int` | `home_shots_on_target` | Step 1 (`HST`) |
| `AwayShotsOnTarget` | `int` | `away_shots_on_target` | Step 1 (`AST`) |
| `HomeXG` | `float64` | `home_xg` | Step 2 |
| `AwayXG` | `float64` | `away_xg` | Step 2 |
| `HomeElo` | `float64` | `home_elo` | Step 3 (rating **before** match) |
| `AwayElo` | `float64` | `away_elo` | Step 3 |
| `HomeCongestion` | `int` | `home_games_last_7` | Step 5 |
| `AwayCongestion` | `int` | `away_games_last_7` | Step 5 |
| `HomePossession` | `float64` | `home_possession` | Step 6 |
| `AwayPossession` | `float64` | `away_possession` | Step 6 |
| `HomePPDA` | `float64` | `home_ppda` | Step 6 |
| `AwayPPDA` | `float64` | `away_ppda` | Step 6 |

These join the existing fields that were already present before Phase 3:

| Existing field | Type | Notes |
|---------------|------|-------|
| `Date`, `HomeTeam`, `AwayTeam` | `string` | Core identity |
| `HomeGoals`, `AwayGoals` | `int` | Final score |
| `Result` | `string` | `"H"`, `"D"`, `"A"` |
| `Season`, `League` | `string` | |
| `HomeOdds`, `DrawOdds`, `AwayOdds` | `float64` | Market odds |
| `HomeForm`, `AwayForm` | `string` | e.g. `"WWDLD"` |
| `RestDaysH`, `RestDaysA` | `int` | |
| `HomePos`, `AwayPos` | `int` | League position before match |

**Total fields in MatchRecord: 31**

#### CSV column header (31 columns)

```
Date, HomeTeam, AwayTeam, HomeGoals, AwayGoals, Result, Season, League,
HomeOdds, DrawOdds, AwayOdds,
HomeShots, AwayShots, HomeShotsOnTarget, AwayShotsOnTarget,
HomeXG, AwayXG,
HomeElo, AwayElo,
HomeForm, AwayForm,
RestDaysHome, RestDaysAway, HomeCongestion, AwayCongestion,
HomePossession, AwayPossession, HomePPDA, AwayPPDA,
HomePosition, AwayPosition
```

#### `getColInt` fix

`getColInt` in `storage/csv.go` was updated to parse float-encoded integer strings (e.g. `"2.0"` instead of `"2"`) which appear in some football-data.co.uk files:

```go
// Try float parse first to handle "2.0" style values
if f, err := strconv.ParseFloat(s, 64); err == nil {
    return int(f)
}
v, _ := strconv.Atoi(s)
return v
```

---

## The 7-Step Enrichment Pipeline

### Step 1 — Fetch (football-data.co.uk)

- Downloads `{base}/{season}/{league}.csv` for each (season, league) pair
- Pauses 500ms between requests to avoid overloading the server
- Falls back to 380 Poisson-sampled synthetic matches if all downloads fail
- Columns mapped via `colMap` (see `parseFootballDataCSV` in collector.go)

### Step 2 — xG Estimation

```
HomeXG = clip(homeShots × 0.08 + homeShotsOnTarget × 0.22, 0, 5)
AwayXG = clip(awayShots × 0.08 + awayShotsOnTarget × 0.22, 0, 5)
```

Shot weight: 8% (total shots) + 22% (on target) = 30% if all shots on target, 8% if none.
Falls back to `actualGoals ± U(0,1) − 0.5` if both shot counts are zero.

### Step 3 — Elo Ratings

- Records are sorted ascending by `Date` before processing
- Starting rating: 1500 for all teams
- K-factor: 32 (same as Phase 2 engine)
- `HomeElo` / `AwayElo` on each record captures the team's rating **before** the match result is applied
- Final rating map is saved to `c.eloRatings` for potential reuse in Phase 5 API initialization

```
expected_home = 1 / (1 + 10^((awayElo − homeElo) / 400))
new_homeElo   = homeElo + 32 × (actual − expected)
actual: W=1.0, D=0.5, L=0.0
```

### Step 4 — Team Form

- Maintains `teamResults map[string][]string` with running per-team result history
- `HomeForm` = concatenated last 5 results **before** this match
- Defaults to `"DDDDD"` for teams with fewer than 5 prior results
- Result appended after form is recorded, so form correctly represents pre-match state

### Step 5 — Rest & Congestion

- `RestDaysH` = days since the home team's last match (clamped to `[1, 30]`; default 7 for first match)
- `HomeCongestion` = number of matches in the 7 days before this match **plus 1** (this match)
- Date parsing attempts formats: `DD/MM/YYYY`, `YYYY-MM-DD`, `DD/MM/YY`, `MM/DD/YYYY`
- A `pruneOld` function trims the recent-games list to only keep entries within 30 days, preventing unbounded memory growth

### Step 6 — Advanced Stats (Estimated)

Possession estimated from shot share:
```
homePoss = clip(homeShots / totalShots × 100, 30, 70)
awayPoss = 100 − homePoss
```

PPDA (Passes Allowed Per Defensive Action) estimated inversely from possession:
```
HomePPDA = clip(15 − (homePoss − 50) × 0.15 + noise, 5, 20)
```
- High possession (60%) → lower PPDA (≈ 13.5) → more pressing
- Low possession (40%) → higher PPDA (≈ 16.5) → less pressing
- Noise is uniform `[-2, +2]` seeded with `rand.NewSource(42)` for reproducibility

> **Note:** These are statistical estimates, not real PPDA data. Phase 6 or a future FBref integration should replace these with actual metrics.

### Step 7 — League Positions

- Records are grouped by `Season` string, then sorted by `Date` within each season
- `HomePos` = 1-based rank by points **before** this match is played
- Rank computed by `rankOf(points, team)`: counts how many teams have strictly more points
- Points awarded after the position is recorded:
  - Win: +3 for winning team
  - Draw: +1 for both teams
  - Loss: +0

---

## MatchRecord Field Reference

| # | Field | Type | Set in step | Notes |
|---|-------|------|-------------|-------|
| 1 | `Date` | string | 1 | DD/MM/YYYY or YYYY-MM-DD |
| 2 | `HomeTeam` | string | 1 | Team name from source |
| 3 | `AwayTeam` | string | 1 | |
| 4 | `HomeGoals` | int | 1 | Final score |
| 5 | `AwayGoals` | int | 1 | |
| 6 | `Result` | string | 1 | "H" / "D" / "A" |
| 7 | `Season` | string | 1 | e.g. "2023-24" |
| 8 | `League` | string | 1 | e.g. "E0" |
| 9 | `HomeOdds` | float64 | 1 | Best of B365H / PSH / BWH |
| 10 | `DrawOdds` | float64 | 1 | |
| 11 | `AwayOdds` | float64 | 1 | |
| 12 | `HomeShots` | int | 1 | Raw from HS column |
| 13 | `AwayShots` | int | 1 | Raw from AS column |
| 14 | `HomeShotsOnTarget` | int | 1 | Raw from HST |
| 15 | `AwayShotsOnTarget` | int | 1 | Raw from AST |
| 16 | `HomeXG` | float64 | 2 | Estimated from shots |
| 17 | `AwayXG` | float64 | 2 | |
| 18 | `HomeElo` | float64 | 3 | Rating **before** match |
| 19 | `AwayElo` | float64 | 3 | |
| 20 | `HomeForm` | string | 4 | Last 5 results e.g. "WWDLD" |
| 21 | `AwayForm` | string | 4 | |
| 22 | `RestDaysH` | int | 5 | Days since last match |
| 23 | `RestDaysA` | int | 5 | |
| 24 | `HomeCongestion` | int | 5 | Games in last 7 days (incl. this) |
| 25 | `AwayCongestion` | int | 5 | |
| 26 | `HomePossession` | float64 | 6 | Estimated [30, 70] |
| 27 | `AwayPossession` | float64 | 6 | |
| 28 | `HomePPDA` | float64 | 6 | Estimated [5, 20] |
| 29 | `AwayPPDA` | float64 | 6 | |
| 30 | `HomePos` | int | 7 | League position before match |
| 31 | `AwayPos` | int | 7 | |

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
| Limitation | No upcoming fixtures — completed results only |

**Supported leagues (19 total):**

| Code | League | Country | Tier |
|------|--------|---------|------|
| E0 | Premier League | England | 1 |
| E1 | Championship | England | 2 |
| E2 | League One | England | 3 |
| E3 | League Two | England | 4 |
| SC0 | Scottish Premiership | Scotland | 1 |
| SC1 | Scottish Championship | Scotland | 2 |
| D1 | Bundesliga | Germany | 1 |
| D2 | 2. Bundesliga | Germany | 2 |
| SP1 | La Liga | Spain | 1 |
| SP2 | Segunda División | Spain | 2 |
| I1 | Serie A | Italy | 1 |
| I2 | Serie B | Italy | 2 |
| F1 | Ligue 1 | France | 1 |
| F2 | Ligue 2 | France | 2 |
| N1 | Eredivisie | Netherlands | 1 |
| B1 | Jupiler Pro League | Belgium | 1 |
| P1 | Primeira Liga | Portugal | 1 |
| T1 | Süper Lig | Turkey | 1 |
| G1 | Super League | Greece | 1 |

**Available seasons (8 total, newest first):**

| Code | Label |
|------|-------|
| 2425 | 2024-25 |
| 2324 | 2023-24 |
| 2223 | 2022-23 |
| 2122 | 2021-22 |
| 2021 | 2020-21 |
| 1920 | 2019-20 |
| 1819 | 2018-19 |
| 1718 | 2017-18 |

### The Odds API

| Property | Value |
|----------|-------|
| Base URL | `https://api.the-odds-api.com/v4` |
| Auth | `ODDS_API_KEY` environment variable |
| Rate limit | 500 requests/month (free tier) |
| Regions | `uk,eu` |
| Market | `h2h` (1X2 decimal odds) |
| Quota headers | `x-requests-remaining`, `x-requests-used`, `x-requests-limit` |
| Data type | Upcoming fixtures with live bookmaker odds |

**Supported sport keys (examples):**

| Key | League |
|-----|--------|
| `soccer_epl` | Premier League |
| `soccer_spain_la_liga` | La Liga |
| `soccer_germany_bundesliga` | Bundesliga |
| `soccer_italy_serie_a` | Serie A |
| `soccer_france_ligue_one` | Ligue 1 |

---

## Configuration: data_sources.json

Located at `betting-algorithm/config/data_sources.json`. The Go `DataSourcesManager` searches four candidate paths at startup.

**Top-level structure:**

```json
{
  "sources": [ DataSource, ... ],
  "default_config": {
    "default_sport": "football",
    "default_leagues": ["E0"],
    "default_seasons": ["2324", "2223", "2122"],
    "enable_caching": true,
    "cache_directory": "./data/cache",
    "retry_attempts": 3,
    "retry_delay_seconds": 2
  }
}
```

**Configured sources (5 total):**

| ID | Type | Enabled | Auth |
|----|------|---------|------|
| `football-data-uk` | csv | ✓ | None |
| `fbref` | scraper | ✗ | None (future) |
| `api-football` | api | ✗ | `API_FOOTBALL_KEY` |
| `the-odds-api` | api | ✓ | `ODDS_API_KEY` |
| `custom-csv` | file | ✓ | None |

**Column mapping for `football-data-uk`:**

```json
{
  "HomeTeam": "home_team",
  "AwayTeam": "away_team",
  "FTHG": "home_goals",
  "FTAG": "away_goals",
  "FTR": "result",
  "B365H": "home_odds",
  "B365D": "draw_odds",
  "B365A": "away_odds",
  "Date": "Date"
}
```

---

## Key Algorithms Explained

### xG Estimation from Shot Data

Expected goals are not provided by football-data.co.uk. We approximate using a linear model:

```
xG = shots × 0.08 + shotsOnTarget × 0.22
```

This weights shots on target approximately 2.75× more heavily than off-target shots.
For context, a typical match:
- 12 shots, 5 on target → xG ≈ 0.96 + 1.10 = 2.06 (reasonable for an average EPL match)
- 20 shots, 3 on target → xG ≈ 1.60 + 0.66 = 2.26 (high-volume, low-accuracy attack)

Values are clamped to `[0, 5]` as Poisson λ above 5 produces implausible result distributions.

### Elo Sequential Update

Records must be sorted by date before Elo calculation, since each team's rating depends on all prior results. The pipeline sorts a copy of the slice (`sorted := make([]MatchRecord, len(records))`), processes in chronological order, then returns the sorted-and-enriched slice as the new canonical order.

The `eloRatings` map persists on the `HistoricalDataCollector` after `CollectSync` completes. Phase 5 can seed the `PredictionEngine.eloRatings` map from these final ratings rather than starting at 1500 for all teams.

### Form String Construction

Form strings are constructed in chronological order, which means the **oldest** result is at index 0 and the **most recent** is at the end. The string `"WWDLD"` means:
- 5 games ago: Win
- 4 games ago: Win
- 3 games ago: Draw
- 2 games ago: Loss
- Last game: Draw

Phase 2's `formToScore` function and Phase 2's `parseForm` in `context/builder.go` both read form strings left-to-right (oldest to most recent), which is consistent with this format.

### Rest & Congestion Calculation

The pipeline maintains two maps per team:
- `lastMatch map[string]time.Time` — date of last played match
- `recentGames map[string][]time.Time` — dates of all matches within the past 30 days

`pruneOld` is called after each match to remove entries older than 30 days, keeping the list O(1) in steady-state rather than growing indefinitely.

The `+1` in `HomeCongestion = homeGames + 1` accounts for the current match itself. A team playing 2 games in 7 days (today + 6 days ago) would have `congestion = 2`.

### Possession Estimation from Shot Share

Real possession data is not available from football-data.co.uk. Shot share (shots / total shots) is a reasonable proxy:
- Teams with higher shot volume tend to have more possession
- Clamping to [30, 70] prevents extreme values from single high-shot-difference games

This is a known approximation. The `possessionQuality` factor in Phase 2 will produce estimates, not true metrics.

### PPDA Estimation

PPDA (Passes Allowed Per Defensive Action) measures how aggressively a team presses. Lower PPDA = more pressing. The estimation formula:

```
PPDA = 15 − (possession − 50) × 0.15 + noise
      clamped to [5, 20]
```

At 50% possession: PPDA = 15 (mid-table pressing)
At 60% possession: PPDA = 13.5 (higher possession team presses more)
At 40% possession: PPDA = 16.5 (lower possession = less pressing = more defensive)

Noise `[-2, +2]` adds variance so all teams don't have identical PPDA for the same possession figure.

### League Position Tracking

Positions are calculated per season by iterating matches in chronological order within each season group. For each match:
1. Record home and away positions using current points
2. Award points based on match result

`rankOf(points, team)` = count of teams with **strictly more** points + 1. This correctly places tied teams at the same rank (e.g., three teams on 10 points all get rank 5 if four teams have more).

### Poisson Sample (Sample Data)

Used only in `generateSampleMatches` to produce realistic goal counts:

```go
func poissonSample(rng *rand.Rand, lambda float64) int {
    L := math.Exp(-lambda)   // e^(-λ)
    p := 1.0
    k := 0
    for p > L {
        p *= rng.Float64()   // multiply uniform samples
        k++
    }
    return k - 1
}
```

This is the Knuth inversion method for Poisson sampling. Expected value = lambda; correct distribution for integer goal counts.

---

## Error Handling & Fallback Strategy

| Failure scenario | Behaviour |
|-----------------|-----------|
| HTTP timeout on `fetchFootballDataUK` | Logged as warning; that season/league is skipped; collection continues |
| All seasons/leagues fail | `generateSampleMatches()` used as fallback (380 synthetic EPL matches) |
| `os.ReadFile` fails for all config paths | `NewDataSourcesManager` returns error; caller should handle gracefully |
| Odds API key missing | `GetUpcomingMatches` silently returns nil, nil (not an error) |
| Odds API HTTP non-200 | Error returned with status code and body excerpt |
| Date parse failure in Step 5 | Record gets `RestDaysH/A = 7` (sensible default) and processing continues |
| Step N failure | Pipeline returns error wrapped as `"step N (name): underlying error"` |
| Save failure after Step 7 | Logged as warning; records still returned to caller (non-fatal) |
| Context cancelled | Returns `ctx.Err()` wrapped in `"step N"` prefix immediately |

The save-failure non-fatal design means `CollectSync` always returns what data was collected even if the disk write fails — important for in-memory use cases.

---

## Thread Safety & Async Collection

### `CollectionStatus`

Uses `sync.RWMutex` for all field access:
- `set(step, progress)` → write lock (called from pipeline goroutine)
- `finish(err)` → write lock (called from pipeline goroutine)
- `Read()` → read lock (called from API handler / polling goroutine)

The `Read()` method returns a **value copy**, not a pointer, preventing data races on the caller side.

### `StartCollection` goroutine

```go
status := &CollectionStatus{Running: true}
go func() {
    err := c.runPipeline(ctx, status, seasons, leagues)
    status.finish(err)
}()
return status
```

The caller receives `*CollectionStatus` immediately and can poll `status.Read()` at any interval. The context passed in controls cancellation from outside.

### `HistoricalDataCollector` concurrency

`HistoricalDataCollector` is **not safe for concurrent use across multiple `StartCollection` calls** — they would both write to `c.eloRatings`. If multiple concurrent collections are needed, create separate instances with `NewHistoricalDataCollector`.

---

## Go vs Python Differences

| Concern | Python | Go |
|---------|--------|----|
| **DataFrame** | `pd.DataFrame` with `.loc[]`, `.apply()` | `[]storage.MatchRecord` typed slice with manual for-loops |
| **HTTP** | `requests.get(url)` | `http.NewRequestWithContext(ctx, ...)` with explicit context cancellation |
| **Date parsing** | `datetime.strptime(s, fmt)` with try/except | Sequential format attempts; returns `time.Time{}` on all failures |
| **Poisson sample** | `numpy.random.poisson(lambda)` | Knuth inversion method using `math/rand` |
| **Async** | `asyncio` or `threading.Thread` | `go func()` goroutine + `sync.RWMutex` status |
| **Config loading** | `json.load(open(path))` | `os.ReadFile(path)` + `json.Unmarshal` with candidate path search |
| **Odds extraction** | `max(...)` on list comprehension | Imperative max-tracking loop over `oddsAPIEvent.Bookmakers` |
| **Rate limiting** | `time.sleep(0.5)` | `time.Sleep(500 * time.Millisecond)` between requests |
| **Logging** | `print(f"...")` | `slog.Info(...)` / `slog.Warn(...)` (structured, goes to stderr) |
| **Default seasons** | `['2324', '2223', '2122']` | `[]string{"2425", "2324", "2223", "2122", "2021"}` (5 seasons default) |
| **Season label** | `f"20{s[:2]}-{s[2:]}"` | `"20" + season[:2] + "-" + season[2:]` (string slicing) |
| **xG formula** | `shots * 0.08 + sot * 0.22` | Same, with `clip()` wrapper |
| **Elo update** | Dict mutation in place | Sort copy, mutate copy, return copy |
| **pandas NA check** | `pd.notna(row['Date'])` | `home == "" ` check after `strings.TrimSpace()` |

---

## Storage Changes (csv.go)

Summary of changes made to `internal/storage/csv.go` during Phase 3:

**Added 11 new fields to `MatchRecord`** (see [Fields added](#fields-added-to-matchrecord) above).

**Updated `WriteHistoricalData` header slice** — from 20 columns to 31 columns. The 11 new columns are:
`HomeShots`, `AwayShots`, `HomeShotsOnTarget`, `AwayShotsOnTarget`, `HomeXG`, `AwayXG`, `HomeElo`, `AwayElo`, `HomeCongestion`, `AwayCongestion`, `HomePossession`, `AwayPossession`, `HomePPDA`, `AwayPPDA`.

**Updated `WriteHistoricalData` row serialization** — added `strconv.Itoa(r.HomeShots)`, `formatFloat(r.HomeXG)`, etc. for all 11 new fields.

**Updated `parseMatchCSV`** — added `getColInt`/`getColFloat` calls for all 11 new column names.

**Updated `getColInt`** — added `strconv.ParseFloat` fallback before `strconv.Atoi` to handle float-encoded integer columns (e.g. `"2.0"` instead of `"2"`).

The changes are **backwards-compatible**: existing CSV files without the new columns will parse with zero values for those fields (xG=0, Elo=0, etc.) which the Phase 2 algorithm handles gracefully through its `setDefaults()` step.

---

## Known Limitations & TODOs

1. **xG and possession are estimates, not real data.** The `possessionQuality` and `counterAttackEfficiency` Phase 2 factors use these values. Accuracy will improve if FBref scraping (source `fbref`, currently disabled) is implemented in a future phase.

2. **PPDA is estimated with noise.** The `+/-2` uniform noise means PPDA values will differ on every fresh collection run if a different rand seed is used. Currently seeded at 42 for reproducibility, but this should be documented so future maintainers don't change it and invalidate cached datasets.

3. **`eloRatings` on collector not thread-safe.** If `StartCollection` is called twice concurrently, both goroutines will write to `c.eloRatings`. Phase 5 should either use one collector per request, or add a mutex around `c.eloRatings`.

4. **Season label format inconsistency.** `parseFootballDataCSV` writes `Season` as `"2023-24"` (hyphenated), but football-data.co.uk uses `"2324"` as the season code. Code downstream that groups by season must handle both formats.

5. **`GetCurrentSeasonResults` returns `UpcomingMatch` not `storage.MatchRecord`.** This creates a type mismatch when the caller wants to feed the data into the collection pipeline. A future refactor should either return `MatchRecord` or add a conversion function.

6. **No retry logic in `fetchCSVURL`.** The `DefaultConfig.retry_attempts = 3` field from `data_sources.json` is not yet wired up. Failed requests are silently skipped. Phase 5 should implement exponential backoff.

7. **`DataSourcesManager.FormatURL` is not used by `collector.go`.** The collector hardcodes the football-data.co.uk URL pattern rather than calling `FormatURL`. These should be unified in a future refactor to use `DataSourcesManager` as the single source of truth for URLs.

8. **No caching layer.** The `enable_caching` and `cache_directory` fields from `DefaultConfig` are parsed but never used. Phase 5 should implement a simple file-based cache: if `data/cache/{season}_{league}.csv` exists and is less than 24 hours old, skip the HTTP fetch.

---

## Testing Strategy

### Unit Tests (Phase 3 spec)

| Test | Target | Assertion |
|------|--------|-----------|
| `TestXGEstimation_TypicalMatch` | `addXGData` | 12 shots, 5 SOT → HomeXG ≈ 2.06 |
| `TestXGEstimation_ZeroShots` | `addXGData` | Both shot counts zero → falls back to goals ± noise; result in [0, 5] |
| `TestEloUpdate_Draw` | `calculateEloRatings` | Equal teams, draw → both Elo unchanged (within float precision) |
| `TestEloUpdate_Upset` | `calculateEloRatings` | Lower-rated team wins → their Elo increases by more than K/2 |
| `TestFormString_FirstMatch` | `calculateTeamForm` | First match for a team → form = "DDDDD" |
| `TestFormString_FiveResults` | `calculateTeamForm` | Exactly 5 results → form = those 5 (not truncated) |
| `TestFormString_MoreThanFive` | `calculateTeamForm` | 8 results → form = last 5 only |
| `TestRestDays_FirstMatch` | `calculateRestCongestion` | No prior match → RestDaysH = 7 |
| `TestRestDays_ThreeDays` | `calculateRestCongestion` | Last match 3 days ago → RestDaysH = 3 |
| `TestCongestion_WeeklyCount` | `calculateRestCongestion` | 2 matches in last 7 days → Congestion = 3 (2 + this match) |
| `TestPossessionEstimate_EvenShots` | `addAdvancedStats` | Home = 12 shots, Away = 12 shots → HomePossession = 50 |
| `TestPossessionEstimate_Clamped` | `addAdvancedStats` | Extreme shot ratio → possession clamped to [30, 70] |
| `TestLeaguePosition_AfterWin` | `calculateLeaguePositions` | Team wins → position improves before next match |
| `TestLeaguePosition_SeasonIsolation` | `calculateLeaguePositions` | Different seasons don't share points tables |
| `TestFormatURL` | `DataSourcesManager.FormatURL` | `("football-data-uk", "2324", "E0")` → correct URL |
| `TestGetTopTierLeagues` | `DataSourcesManager` | Returns only leagues with tier=1 |
| `TestGetRecentSeasons` | `DataSourcesManager` | count=3 → first 3 from config (newest first) |
| `TestPoissonSample` | `poissonSample` | λ=2.0, n=10000 samples → mean in [1.8, 2.2] |
| `TestParseMatchTime_ISO` | `parseMatchTime` | `"2024-02-11T15:00:00Z"` → correct UTC time |
| `TestParseMatchTime_DDMMYYYY` | `parseMatchTime` | `"11/02/2024"` → 2024-02-11 UTC |
| `TestCurrentSeasonCode_August` | `currentSeasonCode` | Month = August → code = current year pair |
| `TestCurrentSeasonCode_March` | `currentSeasonCode` | Month = March → code = previous year pair |
| `TestCollectSync_SampleFallback` | `CollectSync` | With offline HTTP (mock) → returns 380 sample records |
| `TestCollectionStatus_Concurrent` | `CollectionStatus` | Concurrent Read + set → no data race (run with `-race`) |

### Integration Tests (Phase 6)

- Run `CollectSync` with real HTTP against football-data.co.uk for season `"2324"`, league `"E0"`
- Assert: ≥ 360 records, HomeElo populated for all, HomeForm length ≤ 5 for all, HomePossession in [30, 70] for all
- Assert: `WriteHistoricalData` produces a valid CSV that `ReadHistoricalData` round-trips without loss
