# Bet4Me: Python to Go Conversion Plan

## Context

The Bet4Me codebase is a sports betting analytics platform currently written in Python (Flask backend, ~3000+ lines across 12 source files) with an Angular 19 frontend. The goal is to rewrite the entire Python backend in Go for better performance, type safety, concurrency, and single-binary deployment — while keeping the Angular frontend unchanged and maintaining full API compatibility.

---

## Key Decisions

- **Coexistence**: Create `betting-algorithm-go/` side-by-side with existing Python code — enables parallel validation and easy rollback
- **Storage**: Stay file-based (CSV/JSON) for 1:1 parity — repository pattern allows future DB migration without code changes
- **Port**: Go server runs on `:5000` (same as Flask) — no frontend config changes needed, just swap which server is running

## Technology Choices

| Concern | Choice | Why |
|---------|--------|-----|
| **HTTP Router** | `chi` (go-chi/chi/v5) | Stdlib-compatible, lightweight, middleware-friendly, enterprise-proven |
| **CORS** | `rs/cors` | Standard Go CORS middleware, works with chi |
| **Math/Stats** | `gonum` (gonum.org/v1/gonum) | Poisson distribution, matrix ops — Go's NumPy equivalent |
| **Web Scraping** | `goquery` (PuerkitoBio/goquery) | jQuery-like HTML parsing — Go's BeautifulSoup equivalent |
| **CSV Parsing** | `encoding/csv` (stdlib) | No need for a dataframe library; typed structs are sufficient |
| **JSON** | `encoding/json` (stdlib) | Standard, fast enough for this use case |
| **Config/Env** | `godotenv` + `envconfig` | Load .env files + struct-based env parsing |
| **Logging** | `log/slog` (stdlib, Go 1.21+) | Structured logging, stdlib, zero dependencies |
| **Testing** | `testing` + `testify` | Standard Go testing with assertion helpers |
| **Build** | `Makefile` + `go build` | Simple, reproducible builds |

---

## Go Project Structure

```
betting-algorithm-go/
├── cmd/
│   └── server/
│       └── main.go                  # Entry point: wire up deps, start HTTP server
│
├── internal/
│   ├── domain/                      # Core domain types (no external deps)
│   │   ├── models.go                # FactorResult, MatchContext, H2HRecord, ManagerInfo
│   │   ├── enums.go                 # DefensiveStyle, Outcome, Recommendation enums
│   │   └── config.go                # WeightConfig, TeamData, league constants
│   │
│   ├── algorithm/                   # Core prediction engine
│   │   ├── algorithm.go             # PredictionEngine — 16-factor model
│   │   ├── factors.go               # Individual factor calculation functions
│   │   ├── poisson.go               # Poisson goal distribution model
│   │   ├── calibration.go           # Platt scaling + self-improving calibration
│   │   └── algorithm_test.go        # Unit + integration tests
│   │
│   ├── context/                     # Match context building
│   │   ├── builder.go               # ContextBuilder — enriches match data
│   │   └── builder_test.go
│   │
│   ├── jackpot/                     # Jackpot analysis system
│   │   ├── analyzer.go              # JackpotAnalyzer — batch prediction + combinations
│   │   ├── fetcher.go               # Web scraping (SportPesa, Betika)
│   │   └── analyzer_test.go
│   │
│   ├── data/                        # Data collection & processing
│   │   ├── collector.go             # HistoricalDataCollector — CSV fetch + enrichment pipeline
│   │   ├── sources.go               # DataSourcesManager — config/data_sources.json loader
│   │   ├── fixtures.go              # LiveFixturesFetcher — Odds API integration
│   │   └── collector_test.go
│   │
│   ├── backtest/                    # Backtesting engine
│   │   ├── engine.go                # BacktestEngine — historical validation
│   │   └── engine_test.go
│   │
│   ├── util/                        # Shared utilities
│   │   ├── kelly.go                 # Kelly Criterion, EV, implied probability
│   │   ├── performance.go           # PerformanceTracker — ROI, Sharpe, drawdown
│   │   ├── teams.go                 # Team name normalization + alias mapping
│   │   └── kelly_test.go
│   │
│   ├── storage/                     # File-based persistence (repository pattern)
│   │   ├── csv.go                   # CSV read/write for historical data
│   │   ├── json.go                  # JSON read/write for predictions, results
│   │   └── storage_test.go
│   │
│   └── api/                         # HTTP handlers + middleware
│       ├── server.go                # Server struct, route registration, CORS, startup
│       ├── middleware.go            # Logging, recovery, request ID middleware
│       ├── dashboard.go             # GET /api/dashboard/*
│       ├── predict.go               # POST /api/predict
│       ├── fixtures.go              # GET/POST /api/fixtures/*
│       ├── data.go                  # POST /api/data/collect, GET /api/data/*
│       ├── backtest.go              # POST /api/backtest/run, GET /api/backtest/*
│       ├── performance.go           # GET /api/performance/*
│       ├── config.go                # GET/POST /api/config/weights
│       ├── jackpot.go               # POST /api/jackpots/*, GET /api/jackpots/*
│       └── responses.go             # Shared JSON response helpers + error types
│
├── config/
│   └── data_sources.json            # Copied from Python project
│
├── data/                            # Runtime data directory (same structure as Python)
│   ├── final/
│   ├── jackpots/
│   ├── jackpot_predictions/
│   └── managers.json
│
├── go.mod
├── go.sum
├── Makefile
├── .env.example
└── README.md
```

---

## API Contract Preservation

The Angular frontend expects specific JSON key names (mix of snake_case and camelCase). Go struct tags will handle this:

```go
// Example: Dashboard stats response uses snake_case
type DashboardStatsResponse struct {
    OverallAccuracy  float64 `json:"overall_accuracy"`
    ROI              float64 `json:"roi"`
    TotalPredictions int     `json:"total_predictions"`
    WinStreak        int     `json:"win_streak"`
    CurrentBankroll  float64 `json:"current_bankroll"`
    TotalPnl         float64 `json:"total_pnl"`
}

// Example: Prediction response uses camelCase
type PredictionResponse struct {
    HomeWinProb    float64            `json:"homeWinProb"`
    DrawProb       float64            `json:"drawProb"`
    AwayWinProb    float64            `json:"awayWinProb"`
    Confidence     float64            `json:"confidence"`
    Recommendation *RecommendationOut `json:"recommendation"`
    Factors        map[string]any     `json:"factors"`
}
```

**Key**: Each endpoint's JSON tags must exactly match what `api.service.ts` expects. The frontend `map()` transforms are the source of truth.

---

## Phased Migration Plan

### Phase 1: Foundation (domain + utilities) ✅ COMPLETED
**Files created**: `internal/domain/`, `internal/util/`, `internal/storage/`

1. Port `models.py` → `internal/domain/models.go` + `enums.go`
   - `FactorResult`, `MatchContext`, `H2HRecord`, `ManagerInfo` as Go structs
   - `DefensiveStyle` as Go string enum with `iota`
   - Validation methods (`Validate() error`) instead of `__post_init__`
   - Helper constructors: `NewNeutralContext()`, `NewInactiveFactorResult()`

2. Port `config.py` → `internal/domain/config.go`
   - Weight maps as `map[string]float64`
   - `PremierLeagueTeams` as `map[string]TeamData` struct
   - Conditional factor rules as config structs

3. Port `utils.py` → `internal/util/`
   - `kelly.go`: KellyStake, ImpliedProbability, ExpectedValue, ROI
   - `performance.go`: PerformanceTracker struct with AddBet/GetSummary
   - `teams.go`: NormalizeTeamName with alias map

4. Create `internal/storage/` — file I/O layer
   - `csv.go`: Read/write historical CSV data
   - `json.go`: Read/write prediction JSON, manager JSON, data_sources.json

**Tests**: Unit tests for all math functions, model validation, team normalization.

### Phase 2: Core Algorithm ✅ COMPLETED
**Files created**: `internal/algorithm/`, `internal/context/`

1. Port `algorithm.py` → `internal/algorithm/algorithm.go` + `factors.go` + `poisson.go`
   - `PredictionEngine` struct holding weights, config, calibration state
   - Each factor as a standalone function: `calcExpectedGoals(data MatchData) FactorResult`
   - `poisson.go`: Poisson PMF using `gonum/stat/distuv.Poisson`, goal matrix, score probabilities
   - Probability blending: `blendProbabilities(factorProbs, poissonProbs, dataQuality) Probabilities`
   - Dynamic weight normalization preserving the exact Python logic

2. Port `calibration.py` → `internal/algorithm/calibration.go`
   - `CalibrationEngine` struct with `RecordPrediction()`, `CalibrateWeights()`, `GetReport()`
   - Thread-safe with `sync.RWMutex` for concurrent access

3. Port `context_builder.py` → `internal/context/builder.go`
   - `ContextBuilder` struct that loads managers.json, builds H2H records
   - `BuildContext(homeTeam, awayTeam, matchData) (*MatchContext, error)`

**Tests**: Port `test_algorithm.py`, `test_integration_v2.py`, `test_contextual_factors.py`. Validate probability outputs match Python to 4 decimal places.

### Phase 3: Data Pipeline ✅ COMPLETED
**Files created**: `internal/data/`
**Reference**: `PHASE3_IMPLEMENTATION.md`

1. Port `data_collector.py` → `internal/data/collector.go`
   - Replace pandas DataFrame with `[]MatchRecord` typed slice
   - 7-step synchronous pipeline (fetch → xG → Elo → form → rest → advanced stats → positions)
   - Progress callbacks via `func(step string, current, total int)`
   - Sample data fallback (380 Poisson-sampled matches) when HTTP fails

2. Port `data_sources_manager.py` → `internal/data/sources.go`
   - Load `config/data_sources.json` into typed structs
   - `FormatURL`, `GetAvailableLeagues`, `GetAvailableSeasons`, etc.

3. Port `live_fixtures_fetcher.py` → `internal/data/fixtures.go`
   - HTTP client calls to The Odds API (`GetUpcomingMatches`, `GetLiveOddsForMatch`)
   - football-data.co.uk current-season fetch (`GetCurrentSeasonResults`)

### Phase 4: Jackpot System ✅ COMPLETED
**Files created**: `internal/jackpot/`
**Reference**: `PHASE4_IMPLEMENTATION.md`

1. Port `jackpot_fetcher.py` → `internal/jackpot/fetcher.go`
   - `regexp` on raw HTML (replaces BeautifulSoup CSS selectors — same fallback result)
   - SportPesa Mega (17), Midweek (13) + Betika (15) with curated sample data fallback
   - Saves timestamped JSON + master `jackpot_history.csv`

2. Port `jackpot_analyzer.py` → `internal/jackpot/analyzer.go`
   - Batch prediction using `PredictionEngine.Predict()`
   - `domain.LookupTeam()` for match enrichment
   - Combination generation (Main, Conservative >70%, Draw Value >30%)
   - Result recording + `PerformanceStats` aggregation
   - Saves `{id}.json`, `{id}.csv`, `{id}_results.json`, `jackpot_results_summary.csv`

### Phase 5: HTTP API + Backtest
**Files to create**: `internal/api/`, `internal/backtest/`, `cmd/server/`

1. Port `app.py` → `internal/api/` (one handler file per domain)
   - `chi` router with middleware (CORS, logging, recovery)
   - Each endpoint as a handler method on `Server` struct
   - JSON response helpers for consistent error/success formatting
   - Background data collection via goroutine + sync state

2. Port `backtest.py` → `internal/backtest/engine.go`
   - `BacktestEngine` with `Run(config) (*BacktestResults, error)`
   - CSV export via `encoding/csv`

3. Wire it all up in `cmd/server/main.go`
   - Load .env, create deps, inject into Server, listen on :5000

**Tests**: API integration tests using `httptest.NewServer`, verify JSON response shapes.

### Phase 6: Validation & Cutover
1. Run Python and Go servers side-by-side on different ports
2. Send identical requests, diff JSON responses
3. Run Angular frontend against Go backend, verify all pages work
4. Run Go backtest, compare metrics to Python backtest output
5. Update `proxy.conf.json` to point to Go server
6. Performance benchmark: Go should be 5-20x faster on prediction throughput

---

## Key Architectural Patterns

### Dependency Injection (manual)
```go
// cmd/server/main.go
engine := algorithm.NewPredictionEngine(weights, calibration)
collector := data.NewCollector(httpClient, storage)
analyzer := jackpot.NewAnalyzer(engine, fetcher, storage)
server := api.NewServer(engine, collector, analyzer, backtester)
server.ListenAndServe(":5000")
```

### Repository Pattern for Storage
```go
type PredictionStore interface {
    SavePrediction(id string, pred *Prediction) error
    LoadPrediction(id string) (*Prediction, error)
    ListPredictions() ([]*Prediction, error)
}
// Implemented by storage.JSONStore — swappable for Postgres later
```

### Concurrency for Data Collection
```go
type CollectionStatus struct {
    mu        sync.RWMutex
    Running   bool
    Progress  int
    Step      string
    Error     string
    Completed bool
}

func (c *Collector) StartCollection(ctx context.Context, sport string, seasons []string) {
    go func() {
        // ... pipeline steps, updating status via mutex
    }()
}
```

---

## Risk Areas & Mitigations

| Risk | Mitigation |
|------|-----------|
| **Numerical precision drift** (Poisson, Kelly) | Golden-file tests: run Python, capture outputs, assert Go matches to 4 decimals |
| **JSON key casing mismatch** | Integration tests comparing Go JSON output against recorded Python responses |
| **Pandas to slice processing correctness** | Port Python test data, validate Elo/form/position calculations step by step |
| **Web scraping fragility** (goquery vs BS4) | Keep sample data fallback, test scraper with cached HTML fixtures |
| **Missing Go equivalent for scipy** | gonum/stat/distuv has Poisson PMF — confirmed; no SciPy gap for our use case |

---

## Verification Plan

1. **Unit tests**: Every package gets `*_test.go` — math functions, model validation, factor calculations
2. **Golden-file tests**: Run Python algorithm on 10 real matches, capture JSON → assert Go produces identical output
3. **API contract tests**: Record Python HTTP responses → replay against Go server, diff JSON bodies
4. **Frontend smoke test**: Point Angular dev server at Go backend, manually test each page (dashboard, predictions, jackpot, backtest, settings)
5. **Backtest parity**: Run identical backtest on both, compare final accuracy/ROI/Sharpe within 0.1%
6. **Benchmark**: `go test -bench` on prediction throughput — target <1ms per match prediction

---

## Files to Modify (Existing)

- `betting-frontend/proxy.conf.json` — update port if Go server uses a different one (recommend keeping :5000)
- `.env` / `.env.example` — same variables, compatible with `godotenv`

## Out of Scope (Future)

- Database migration (PostgreSQL) — designed for via repository pattern, not implemented now
- Authentication — not in current Python version
- Docker/container — can add after Go server is working
- CI/CD pipeline — can add after validation complete
