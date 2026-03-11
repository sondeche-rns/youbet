# Phase 5 Implementation Reference — HTTP API + Backtest

> **Status:** Complete
> **Branch:** `feature/golang-refactor`
> **Packages created:** `internal/backtest`, `internal/api`, `cmd/server`
> **Python source files ported:** `backtest.py` · `app.py`

## Overview

Phase 5 completes the Go port by implementing the HTTP API layer and backtesting engine,
making the Go server a drop-in replacement for the Flask server in `app.py`.

| File | Source | Purpose |
|------|--------|---------|
| `internal/backtest/engine.go` | `src/backtest.py` | Chronological simulation + metrics |
| `internal/api/server.go` | `app.py` | chi router + all 25 REST endpoints |
| `cmd/server/main.go` | `app.py` `__main__` block | Dependency wiring; listen on `:5000` |

**Bug fixes applied to pre-existing code** (import paths were wrong before Phase 5):

| File | Fix |
|------|-----|
| `internal/algorithm/algorithm.go` | `bet4me/internal/domain` → `bet4me/betting-algorithm-go/internal/domain` |
| `internal/algorithm/factors.go` | Same prefix fix + syntax error on line 414 (invalid multi-assignment in boolean) |
| `internal/algorithm/calibration.go` | Prefix fix |
| `internal/algorithm/probs.go` | Prefix fix + unused variable `awayBoostTotal` suppressed with `_ =` |
| `internal/context/builder.go` | Prefix fix + removed `algorithm` import (cycle); `BuildContext` now accepts plain parameters |

---

## Package: `internal/backtest`

### Types

```go
type Config struct {
    Sport           string  `json:"sport"`
    Season          string  `json:"season"`           // empty = all seasons
    InitialBankroll float64 `json:"initial_bankroll"` // default 1000
    KellyFraction   float64 `json:"kelly_fraction"`   // default 0.25
    MaxStakePct     float64 `json:"max_stake_pct"`    // default 5.0
    StartDate       string  `json:"start_date"`       // YYYY-MM-DD optional
    EndDate         string  `json:"end_date"`         // YYYY-MM-DD optional
}

type MatchResult struct {
    Date             string  `json:"date"`
    HomeTeam         string  `json:"home_team"`
    AwayTeam         string  `json:"away_team"`
    ActualResult     string  `json:"actual_result"`   // "Home Win" | "Draw" | "Away Win"
    ActualScore      string  `json:"actual_score"`    // "2-1"
    PredictedOutcome string  `json:"predicted_outcome"`
    Correct          bool    `json:"prediction_correct"`
    HomeProb         float64 `json:"home_prob"`
    DrawProb         float64 `json:"draw_prob"`
    AwayProb         float64 `json:"away_prob"`
    Confidence       float64 `json:"confidence"`
    ShouldBet        bool    `json:"should_bet"`
    StakeAmount      float64 `json:"stake_amount"`
    OddsPlayed       float64 `json:"odds_played,omitempty"`
    BetWon           bool    `json:"bet_won,omitempty"`
    PnL              float64 `json:"pnl"`
    Bankroll         float64 `json:"bankroll"`
    ExpectedValue    float64 `json:"expected_value"`
}

type Summary struct {
    Overall              overallStats                  `json:"overall"`
    Betting              bettingStats                  `json:"betting"`
    AccuracyByType       map[string]OutcomeStats       `json:"accuracy_by_type"`
    AccuracyByConfidence map[string]ConfidenceBinStats `json:"accuracy_by_confidence"`
    EquityCurve          []float64                     `json:"equity_curve"` // last 100 points
    TrackerStats         map[string]float64            `json:"tracker_stats"`
    Timestamp            string                        `json:"timestamp"`
}

// overallStats (nested in Summary)
// Fields: TotalMatches, CorrectPredictions, OverallAccuracy, InitialBankroll,
//         FinalBankroll, TotalPnL, ROI, MaxDrawdown, SharpeRatio

// bettingStats (nested in Summary)
// Fields: BetsPlaced, BetsWon, WinRate, AvgStake, AvgOdds
```

### Struct

```go
type BacktestEngine struct {
    engine     *algorithm.PredictionEngine
    csvStore   *storage.CSVStore
    dataDir    string
    resultsDir string // dataDir/backtests/
    logger     *slog.Logger
}
```

### Constructor

```go
func NewBacktestEngine(engine *algorithm.PredictionEngine, dataDir string, logger *slog.Logger) *BacktestEngine
// resultsDir = dataDir/backtests/
// logger defaults to slog.Default()
```

### Public methods

| Method | Returns | Description |
|--------|---------|-------------|
| `Run(cfg Config)` | `(*Summary, error)` | Loads CSV → filters → sorts → simulates; saves JSON + CSV |
| `LoadLatestResults()` | `(*Summary, error)` | Reads most recent `backtest_*.json` |
| `GetLatestCSVPath()` | `(string, error)` | Path to most recent `backtest_*.csv` for HTTP download |

### Simulation logic

1. Load `{dataDir}/final/historical_dataset.csv` via `storage.CSVStore`; fall back to 380 deterministic sample matches if missing.
2. Filter by `Season`, `StartDate`, `EndDate`.
3. Sort chronologically by `Date`.
4. For each match:
   - Build `algorithm.MatchData` from `storage.MatchRecord` fields.
   - Call `engine.Predict()`.
   - Determine `shouldBet`: `stakePercentage > 0 && expectedValue > 0`.
   - Stake = `min(bankroll × stakePercentage, bankroll × MaxStakePct / 100)`.
   - Update bankroll; append to equity curve.
5. `buildSummary` calculates: accuracy, win rate, ROI, max drawdown (peak-to-trough), annualised Sharpe ratio (×√252), profit factor, per-outcome and per-confidence-bin accuracy.

### Confidence bins

`50-60%`, `60-70%`, `70-80%`, `80-90%`, `90-100%`

### Output files

| Filename | Content |
|----------|---------|
| `backtests/backtest_{ts}.json` | Full `Summary` JSON |
| `backtests/backtest_{ts}.csv` | One row per `MatchResult` |

---

## Package: `internal/api`

### Struct

```go
type Server struct {
    engine     *algorithm.PredictionEngine
    collector  *data.HistoricalDataCollector
    fetcher    *data.LiveFixturesFetcher
    sources    *data.DataSourcesManager
    backtester *backtest.BacktestEngine
    jFetcher   *jackpot.JackpotFetcher
    jAnalyzer  *jackpot.JackpotAnalyzer
    csvStore   *storage.CSVStore

    collectMu     sync.RWMutex
    collectStatus data.CollectionStatus // background goroutine state

    dataDir string
    logger  *slog.Logger
}
```

### Constructor

```go
func NewServer(
    engine *algorithm.PredictionEngine,
    collector *data.HistoricalDataCollector,
    fetcher *data.LiveFixturesFetcher,
    sources *data.DataSourcesManager,
    backtester *backtest.BacktestEngine,
    jFetcher *jackpot.JackpotFetcher,
    jAnalyzer *jackpot.JackpotAnalyzer,
    dataDir string,
    logger *slog.Logger,
) *Server
```

### Handler

```go
func (s *Server) Handler() http.Handler // returns configured chi.Mux
```

Middleware stack: `chi/middleware.Recoverer`, `chi/middleware.Logger`, `rs/cors` (allow all origins).

### Route table

| Method | Path | Handler | Python equivalent |
|--------|------|---------|-------------------|
| GET | `/api/dashboard/stats` | `getDashboardStats` | `get_dashboard_stats` |
| GET | `/api/dashboard/upcoming` | `getUpcoming` | `get_upcoming_matches` |
| GET | `/api/dashboard/recent` | `getRecentResults` | `get_recent_results` |
| POST | `/api/predict` | `predictMatch` | `predict_match` |
| GET | `/api/fixtures/upcoming` | `getUpcomingFixtures` | `get_upcoming_fixtures` |
| GET | `/api/fixtures/current-season` | `getCurrentSeason` | `get_current_season` |
| POST | `/api/fixtures/live-odds` | `getLiveOdds` | `get_live_odds` |
| GET | `/api/fixtures/available-sports` | `getAvailableSports` | `get_available_sports` |
| GET | `/api/fixtures/quota` | `getAPIQuota` | `get_api_quota` |
| POST | `/api/data/collect` | `startDataCollection` | `start_data_collection` |
| GET | `/api/data/status` | `getCollectionStatus` | `get_collection_status` |
| GET | `/api/data/historical` | `getHistoricalData` | `get_historical_data` |
| GET | `/api/data/sources` | `getDataSources` | `get_data_sources` |
| GET | `/api/data/leagues` | `getAvailableLeagues` | `get_available_leagues` |
| GET | `/api/data/seasons` | `getAvailableSeasons` | `get_available_seasons` |
| POST | `/api/backtest/run` | `runBacktest` | `run_backtest` |
| GET | `/api/backtest/results` | `getBacktestResults` | `get_backtest_results` |
| GET | `/api/backtest/export` | `exportBacktest` | `export_backtest` |
| GET | `/api/performance/summary` | `getPerformanceSummary` | `get_performance_summary` |
| GET | `/api/performance/monthly` | `getMonthlyPerformance` | `get_monthly_performance` |
| GET | `/api/config/weights` | `getWeights` | `get_weights` |
| POST | `/api/config/weights` | `updateWeights` | `update_weights` |
| POST | `/api/jackpots/fetch` | `fetchJackpots` | `fetch_jackpots` |
| POST | `/api/jackpots/analyze` | `analyzeJackpot` | `analyze_jackpot` |
| POST | `/api/jackpots/results` | `recordJackpotResults` | `record_jackpot_results` |
| GET | `/api/jackpots/history` | `getJackpotHistory` | `get_jackpot_history` |
| GET | `/api/jackpots/performance` | `getJackpotPerformance` | `get_jackpot_performance` |

### Key design decisions

**Background collection**: `startDataCollection` launches a goroutine; state is shared via
`sync.RWMutex` + `data.CollectionStatus`. The goroutine updates `Step` and `Progress` via a `ProgressCallback`.

**Weights persistence**: `updateWeights` calls `engine.SetWeights()` (in-memory) and writes
`config/weights.json` on disk, matching Python's behaviour.

**Backtest export**: `exportBacktest` streams the CSV file directly via `io.Copy` rather than loading it all into memory.

**Response helpers** (package-private):
- `writeJSON(w, status, v)` — sets `Content-Type: application/json`, encodes v
- `writeError(w, status, msg)` — `{"error": msg}`
- `readJSON(r, v)` — decodes request body

---

## Package: `cmd/server`

### `main.go`

```
Load .env (godotenv, silent)
Resolve dataDir from DATA_DIR env or {exe}/../../data/
Create subdirectories: final/, backtests/, jackpots/, jackpot_predictions/, jackpot_results/
Build PredictionEngine (V2 weights, no calibration)
Build data.HistoricalDataCollector, data.LiveFixturesFetcher, data.DataSourcesManager
Build backtest.BacktestEngine
Build jackpot.JackpotFetcher, jackpot.JackpotAnalyzer
Build api.Server
http.ListenAndServe(0.0.0.0:{PORT}, server.Handler())
```

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_DIR` | `{exe}/../../data` | Path to data directory |
| `PORT` | `5000` | HTTP listen port |
| `ODDS_API_KEY` | — | The Odds API key for live fixtures |
| `API_FOOTBALL_KEY` | — | api-football.com key |

---

## Import cycle fix

The pre-existing code had `algorithm → context → algorithm` forming a cycle. Fixed by:

1. Removing the `algorithm` import from `internal/context/builder.go`.
2. Changing `BuildContext(*algorithm.MatchData)` → `BuildContext(homeTeam, awayTeam string, homePossession, awayPossession float64, homePos, awayPos int, homeFormStr, awayFormStr string)`.
3. Updating the call-site in `internal/algorithm/factors.go` to pass individual fields.

---

## Next Phase

**Phase 6**: Validation & Cutover — run Python and Go servers side-by-side, diff JSON
responses, smoke-test the Angular frontend against the Go backend, then update
`proxy.conf.json`.
