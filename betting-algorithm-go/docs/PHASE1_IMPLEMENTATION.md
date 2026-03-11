# Phase 1: Foundation — Implementation Reference

> **Status:** Complete
> **Branch:** `feature/golang-refactor`
> **Packages created:** `internal/domain`, `internal/util`, `internal/storage`
> **Python source files ported:** `models.py` · `config.py` · `utils.py`

---

## Table of Contents

1. [Overview](#overview)
2. [Package Structure](#package-structure)
3. [File-by-File Reference](#file-by-file-reference)
   - [domain/models.go — Core Domain Types](#domainmodelsgo--core-domain-types)
   - [domain/enums.go — Enumerations](#domainenumsgo--enumerations)
   - [domain/config.go — Configuration & Team Data](#domainconfiggo--configuration--team-data)
   - [util/kelly.go — Betting Math](#utilkellygo--betting-math)
   - [util/performance.go — Performance Tracker](#utilperformancego--performance-tracker)
   - [util/teams.go — Team Name Normalization](#utilteamsgo--team-name-normalization)
   - [storage/csv.go — CSV Storage](#storagecsvgo--csv-storage)
   - [storage/json.go — JSON Storage](#storagejsongo--json-storage)
4. [Key Design Decisions](#key-design-decisions)
5. [Go vs Python Differences](#go-vs-python-differences)
6. [Testing Strategy](#testing-strategy)

---

## Overview

Phase 1 establishes the entire foundation layer: domain types, utility functions, and file I/O. No external HTTP calls or prediction logic are included — this phase is purely about data structures, math helpers, and persistence primitives.

**Key principle**: All types defined here have **no dependencies on other internal packages**. This makes them importable from any phase without creating import cycles.

---

## Package Structure

```
betting-algorithm-go/
├── internal/
│   ├── domain/
│   │   ├── models.go       Core structs: FactorResult, MatchContext, H2HRecord, ManagerInfo, etc.
│   │   ├── enums.go        String enums: DefensiveStyle, Outcome, Recommendation, PlayStyle
│   │   ├── config.go       AppConfig, WeightMaps, TeamData, PremierLeagueTeams, LookupTeam
│   │   └── models_test.go  Validation tests for FactorResult, MatchContext, ManagerInfo
│   │
│   ├── util/
│   │   ├── kelly.go          Kelly Criterion, EV, implied probability, Sharpe ratio, odds formats
│   │   ├── kelly_test.go     Unit tests for all math functions
│   │   ├── performance.go    PerformanceTracker struct with AddBet/GetSummary
│   │   ├── performance_test.go
│   │   ├── teams.go          NormalizeTeamName alias map
│   │   └── teams_test.go
│   │
│   └── storage/
│       ├── csv.go          MatchRecord (30 fields), CSVStore read/write
│       ├── json.go         JSONStore, ManagerEntry, PredictionRecord, DataSourcesConfig
│       └── storage_test.go
```

---

## File-by-File Reference

### `domain/models.go` — Core Domain Types

**Location:** `internal/domain/models.go` (~290 lines)

#### Types

| Type | Python equivalent | Purpose |
|------|------------------|---------|
| `FactorResult` | `FactorResult` dataclass | Standardized output for all prediction factors |
| `ManagerInfo` | `ManagerInfo` dataclass | Manager tenure and results for new-manager-bounce factor |
| `H2HResult` | dict in list | Single head-to-head match result |
| `H2HRecord` | `H2HRecord` dataclass | Aggregated H2H history between two teams |
| `MatchContext` | `MatchContext` dataclass | All contextual data needed for V2 factor calculation |
| `BetRecord` | `BetRecord` dataclass | Single bet for performance tracking |
| `MatchData` | dict / request body | Input data for a prediction request |
| `Probabilities` | tuple | Three-way (home/draw/away) probabilities |
| `PredictionResult` | `PredictionResult` | Full output of a match prediction |
| `BetRecommendation` | dict | Final betting suggestion with Kelly/EV |
| `ExpectedGoals` | tuple | Expected goals for home and away |

#### `FactorResult`

```go
type FactorResult struct {
    Name        string         `json:"name"`
    Value       float64        `json:"value"`       // -1.0 to 1.0 (0.5 = neutral)
    Weight      float64        `json:"weight"`      // 0.0 if inactive
    Triggered   bool           `json:"triggered"`   // false for inactive conditional factors
    Confidence  int            `json:"confidence"`  // 0–100 data quality score
    Explanation string         `json:"explanation"`
    Metadata    map[string]any `json:"metadata"`
}
```

`Validate()` checks `Value ∈ [-1, 1]`, `Confidence ∈ [0, 100]`, `Weight >= 0`, auto-initialises nil `Metadata`.

Constructor `NewInactiveFactorResult(name, explanation)` creates a neutral, zero-weight, untriggered result.

#### `MatchContext`

```go
type MatchContext struct {
    HomeDefensiveStyle DefensiveStyle
    AwayDefensiveStyle DefensiveStyle
    HomeManagerInfo    *ManagerInfo
    AwayManagerInfo    *ManagerInfo
    HomeLeaguePosition int
    AwayLeaguePosition int
    HomeRecentForm     []string  // ["W", "D", "L", ...]
    AwayRecentForm     []string
    H2HRecord          *H2HRecord
    HomeSeasonStats    map[string]any
    AwaySeasonStats    map[string]any
}
```

`Validate()` checks all form results are `"W"/"D"/"L"` and league positions are `>= 1`.

`NewNeutralContext()` returns a balanced context: both teams at position 10, `DefensiveStyleBalanced`, five draws for form.

Helper methods: `RecentWins(team, lastN)`, `IsRelegationThreatened(team)` (position >= 18).

#### `H2HRecord`

Convenience methods on `H2HRecord`: `TotalMatches()`, `HomeWins()`, `Draws()`, `AwayWins()`, `WinRate(perspective)`.

#### `ManagerInfo`

`WinRate()` returns fraction of wins from `Results`. `Validate()` checks `GamesManaged >= 0` and all results are `"W"/"D"/"L"`.

---

### `domain/enums.go` — Enumerations

**Location:** `internal/domain/enums.go` (~73 lines)

Go uses typed `string` constants instead of Python `Enum`. Each enum has a `ValidXxx` map and `Validate() error` method.

| Enum type | Constants |
|-----------|-----------|
| `DefensiveStyle` | `high_press`, `balanced`, `low_block`, `counter_attack` |
| `Outcome` | `W`, `D`, `L` |
| `Recommendation` | `HOME`, `DRAW`, `AWAY`, `SKIP` |
| `PlayStyle` | `attacking`, `balanced`, `defensive` |

---

### `domain/config.go` — Configuration & Team Data

**Location:** `internal/domain/config.go` (~262 lines)

#### `AppConfig` + `LoadAppConfig`

Reads from environment variables with defaults:

| Env var | Default | Field |
|---------|---------|-------|
| `ODDS_API_KEY` | `""` | `OddsAPIKey` |
| `API_FOOTBALL_KEY` | `""` | `APIFootballKey` |
| `DEFAULT_SPORT` | `"football"` | `DefaultSport` |
| `INITIAL_BANKROLL` | `1000` | `InitialBankroll` |
| `MAX_BET_PERCENTAGE` | `5` | `MaxBetPercentage` |
| `KELLY_FRACTION` | `0.25` | `KellyFraction` |
| `PORT` | `"5000"` | `Port` |

#### Weight Maps

| Map | Description |
|-----|-------------|
| `FootballWeights` | V1 weights — 10 factors summing to 1.0 |
| `FootballWeightsV2` | V2/V3 weights — 17 factors including contextual; active factors renormalized at runtime |

V2 key weights: `expectedGoals: 0.12`, `h2hAnomaly: 0.12` (conditional), `teamQualityGap: 0.10`, `advancedStats: 0.07`, `possessionQuality: 0.07`.

#### `ConditionalFactors`

Package-level struct with two rules:

- `H2HAnomaly`: replaces `h2hHistorical`, `WeightMultiplier: 3.0`, triggers when `weaker_team_unbeaten_streak >= 3`
- `ManagerMomentum`: decay formula `baseBoost * (0.85 ^ gamesManaged)`, `BaseBoost: 0.08`, `InterimMultiplier: 0.7`

#### `TeamData` and `PremierLeagueTeams`

Static team database for 20 EPL teams. Each entry has `Elo int`, `Position int`, `Form string`, `Stars int`, `HomeXGAvg float64`, `AwayXGAvg float64`, `Style PlayStyle`, `Aliases []string`.

`LookupTeam(teamName string) (*TeamData, string)` performs case-insensitive lookup against canonical names and all aliases. Returns `nil, ""` if not found.

---

### `util/kelly.go` — Betting Math

**Location:** `internal/util/kelly.go` (~131 lines)

| Function | Signature | Notes |
|----------|-----------|-------|
| `CalculateKellyStake` | `(probability, odds, fraction, maxStake float64) float64` | Returns 0 if `probability <= 0`, `>= 1`, or `odds <= 1`; applies fractional Kelly then caps at `maxStake` |
| `CalculateImpliedProbability` | `(decimalOdds float64) float64` | `1 / odds`; returns 0 if odds <= 0 |
| `CalculateExpectedValue` | `(probability, odds float64) float64` | `(p * odds) - 1`; positive = edge |
| `CalculateROI` | `(initial, final float64) float64` | Percentage; returns 0 if initial <= 0 |
| `CalculateSharpeRatio` | `(returns []float64, riskFreeRate float64) float64` | Annualized (252 days); returns 0 if < 2 returns or zero std dev |
| `NormalizeOddsFormat` | `(odds float64, formatType string) float64` | Converts `"decimal"`, `"american"`, `"fractional"` to decimal |
| `DecimalToAmerican` | `(decimalOdds float64) int` | Standard conversion |
| `AmericanToDecimal` | `(americanOdds int) float64` | Standard conversion |
| `ValidateOdds` | `(odds float64) bool` | `odds ∈ [1.01, 1000]` |
| `ValidateProbability` | `(prob float64) bool` | `prob ∈ (0, 1)` exclusive |
| `ValidateStake` | `(stake, bankroll, maxPct float64) bool` | `stake > 0` and `<= bankroll * maxPct` |

Kelly formula:
```
b = odds - 1 (net odds)
kelly = (b*p - q) / b
stake = max(0, kelly * fraction) capped at maxStake
```

---

### `util/performance.go` — Performance Tracker

**Location:** `internal/util/performance.go` (~220 lines)

#### `PerformanceTracker`

Tracks cumulative betting performance with an equity curve.

```go
tracker := util.NewPerformanceTracker(initialBankroll)
tracker.AddBet(stake, odds, won, pnlOverride, timestampOverride)
summary := tracker.GetSummary()   // returns PerformanceSummary
tracker.Reset()
```

Fields tracked: `Bankroll`, `Wins`, `Losses`, `TotalStaked`, `TotalWon`, `TotalLost`, `CurrentStreak`, `LongestWinStreak`, `LongestLossStreak`, `EquityCurve []float64`, `Timestamps []time.Time`.

#### `PerformanceSummary`

| Field | Computation |
|-------|------------|
| `WinRate` | `wins / totalBets * 100` |
| `ROI` | `(bankroll - initial) / initial * 100` |
| `ProfitFactor` | `totalWon / max(totalLost, 0.01)` |
| `SharpeRatio` | Annualized from equity curve returns |
| `MaxDrawdown` | Peak-to-trough % from equity curve |
| `AvgOdds` | Mean of all bet odds |

Streak tracking: positive `CurrentStreak` = win streak, negative = loss streak. Resets on direction change.

---

### `util/teams.go` — Team Name Normalization

**Location:** `internal/util/teams.go` (~40 lines)

`NormalizeTeamName(name string) string` maps common alternative names to canonical forms via a hardcoded `teamNameMap`. Covers EPL, La Liga, Serie A, and Bundesliga aliases.

Example mappings: `"Man City" → "Manchester City"`, `"Spurs" → "Tottenham"`, `"Inter Milan" → "Inter"`, `"Borussia Dortmund" → "Dortmund"`.

Returns the input unchanged if no alias is found.

---

### `storage/csv.go` — CSV Storage

**Location:** `internal/storage/csv.go` (~214 lines)

#### `MatchRecord`

30-field struct representing one row from the historical dataset. All 30 fields are defined here from the start so Phase 3 data enrichment can write directly without schema changes.

```
Fields 1–14:  Date, Season, HomeTeam, AwayTeam, goals, odds, shots (from source)
Fields 15–16: HomeXG, AwayXG (Phase 3 Step 2)
Fields 17–18: HomeElo, AwayElo (Phase 3 Step 3)
Fields 19–20: HomeForm, AwayForm (Phase 3 Step 4)
Fields 21–24: RestDays, GamesLast7 (Phase 3 Step 5)
Fields 25–28: Possession, PPDA (Phase 3 Step 6)
Fields 29–30: HomePosition, AwayPosition (Phase 3 Step 7)
```

#### `CSVStore`

| Method | Description |
|--------|-------------|
| `NewCSVStore(dataDir)` | Constructor |
| `ReadHistoricalData(filePath)` | Reads CSV, builds header index, parses rows into `[]MatchRecord` |
| `WriteHistoricalData(filePath, matches)` | Creates file with fixed 30-column header, writes all rows |

`ReadHistoricalData` uses `getColInt` which handles float-formatted ints (e.g. `"1500.0"` from some CSV sources).

---

### `storage/json.go` — JSON Storage

**Location:** `internal/storage/json.go` (~140 lines)

#### `JSONStore`

Generic JSON persistence with `os.MkdirAll` for directory creation.

| Method | Description |
|--------|-------------|
| `NewJSONStore(dataDir)` | Constructor |
| `Save(filePath, v any)` | Creates dirs, `json.MarshalIndent`, writes file |
| `Load(filePath, v any)` | `os.ReadFile` + `json.Unmarshal` into pointer |
| `Exists(filePath)` | `os.Stat` check |
| `LoadManagers(filePath)` | Loads `[]ManagerEntry` from `managers.json` |
| `LoadDataSources(filePath)` | Loads `*DataSourcesConfig` from `data_sources.json` |
| `SavePrediction(filePath, PredictionRecord)` | Typed save wrapper |
| `LoadPrediction(filePath)` | Typed load wrapper |
| `ListFiles(dir, pattern)` | `filepath.Glob` for file discovery |

#### Typed records

| Type | Purpose |
|------|---------|
| `ManagerEntry` | One entry from `managers.json` |
| `DataSource` | One source from `data_sources.json` |
| `DataSourcesConfig` | Top-level wrapper `{"sources": [...]}` |
| `PredictionRecord` | Saved prediction with `homeWinProb`/`drawProb`/`awayWinProb` keys (camelCase — matches frontend) |

---

## Key Design Decisions

### No dependency on `encoding/json` struct tags for DB queries
All persistence is file-based CSV/JSON. Types carry JSON tags purely for HTTP response serialization (Phase 5) and file storage — not for any ORM or DB layer.

### `MatchRecord` defined in `storage`, not `domain`
`MatchRecord` is a storage-layer concern (CSV rows), not a domain concept. Domain types (`MatchData`, `MatchContext`) are higher-level. This separation means the algorithm package imports `domain` only, and only the data pipeline imports `storage`.

### Validation methods instead of `__post_init__`
Python dataclasses use `__post_init__` for validation. Go uses explicit `Validate() error` methods — callers decide when to validate (usually on construction or before use).

### `FootballWeightsV2` includes conditional `h2hAnomaly` at full weight
The weight map includes `h2hAnomaly: 0.12` even though it is conditional. At runtime the algorithm only activates it when triggered and renormalizes — having it in the map makes the intent explicit.

---

## Go vs Python Differences

| Concern | Python | Go |
|---------|--------|----|
| **Enums** | `class DefensiveStyle(str, Enum)` | `type DefensiveStyle string` + const block |
| **Dataclasses** | `@dataclass` with `__post_init__` | Plain struct + `Validate() error` method |
| **Default dict** | `field(default_factory=dict)` | Explicit `make(map[string]any)` in constructor |
| **Optional fields** | `Optional[ManagerInfo] = None` | Pointer `*ManagerInfo` (nil = absent) |
| **Config loading** | `os.getenv(key, default)` | `os.Getenv` + fallback function `getEnv(key, fallback)` |
| **Type safety** | Runtime errors on wrong types | Compile-time errors — no `isinstance` checks needed |
| **CSV parsing** | `pandas.read_csv()` | `encoding/csv` with typed struct parsing |
| **JSON save** | `json.dump(f, indent=2)` | `json.MarshalIndent` + `os.WriteFile` |

---

## Testing Strategy

### `domain/models_test.go`

| Test | Assertion |
|------|-----------|
| `TestFactorResultValidate_Valid` | No error for value=0.5, confidence=80, weight=0.1 |
| `TestFactorResultValidate_OutOfRange` | Error for value=1.5 |
| `TestNewInactiveFactorResult` | Value=0.5, Weight=0.0, Triggered=false |
| `TestMatchContextValidate_Valid` | No error for valid context |
| `TestMatchContextValidate_InvalidForm` | Error for form result "X" |
| `TestMatchContextValidate_InvalidPosition` | Error for position=0 |
| `TestNewNeutralContext` | Position=10, five "D" forms, Balanced style |
| `TestManagerInfoValidate` | Error for gamesManaged=-1 or result="X" |
| `TestManagerInfoWinRate` | 2W/1D/1L → 0.5 |
| `TestH2HRecord_Methods` | TotalMatches/HomeWins/Draws/AwayWins counts |

### `util/kelly_test.go`

| Test | Assertion |
|------|-----------|
| `TestCalculateKellyStake` | Positive edge returns stake; negative edge returns 0 |
| `TestCalculateKellyStake_EdgeCases` | prob=0 → 0; odds=1.0 → 0 |
| `TestCalculateImpliedProbability` | 2.0 → 0.5; 0 → 0 |
| `TestCalculateExpectedValue` | Positive/negative edge |
| `TestCalculateROI` | (1000, 1100) → 10.0% |
| `TestCalculateSharpeRatio` | Consistent gains → positive Sharpe; < 2 returns → 0 |
| `TestNormalizeOddsFormat` | American +150 → 2.5; fractional 3/2 → 2.5 |

### `util/performance_test.go`

| Test | Assertion |
|------|-----------|
| `TestNewPerformanceTracker` | Bankroll = initial; equity curve has one entry |
| `TestAddBet_Win` | Bankroll increases; Wins=1; streak=1 |
| `TestAddBet_Loss` | Bankroll decreases; Losses=1; streak=-1 |
| `TestGetSummary` | WinRate, ROI, ProfitFactor computed correctly |
| `TestReset` | Tracker returns to initial state |

### `util/teams_test.go`

| Test | Assertion |
|------|-----------|
| `TestNormalizeTeamName_Known` | "Man City" → "Manchester City" |
| `TestNormalizeTeamName_Unknown` | "Scunthorpe" → "Scunthorpe" |
