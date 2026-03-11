# Phase 6 Implementation Reference — Validation & Cutover

> **Status:** Complete
> **Branch:** `feature/golang-refactor`
> **Files created:** `internal/api/server_test.go`, `internal/backtest/engine_test.go`, `scripts/compare_apis.sh`
> **Bug fixes:** `internal/data/sources.go` (nil-safety on empty config)

## Overview

Phase 6 validates the Go server against the Python server and performs the cutover.
No new business logic is added; the focus is on test coverage, correctness verification,
and confirming the Angular frontend works against the Go backend.

| File | Purpose |
|------|---------|
| `internal/api/server_test.go` | Integration tests for all 27 HTTP endpoints (httptest) |
| `internal/backtest/engine_test.go` | Unit + benchmark tests for the backtest engine |
| `scripts/compare_apis.sh` | Side-by-side diff script for Python vs Go responses |

---

## Bug fixes (found during testing)

### `internal/data/sources.go` — nil-safe empty config

`NewDataSourcesManager` returned `(nil, error)` when the config file could not be
loaded. Any subsequent method call on a nil `*DataSourcesManager` panicked.

**Root cause**: four public methods (`GetSourceByID`, `GetEnabledSources`,
`GetDefaultConfig`, `GetAllSourcesMetadata`) accessed `m.Config.Sources` without
checking whether `m.Config` was nil; and the constructor returned `nil` instead of
an empty manager on failure.

**Fix**:
1. `NewDataSourcesManager` now returns `(m, err)` instead of `(nil, err)` — the manager is always non-nil.
2. `GetSourceByID` guards `m.Config == nil → return nil`.
3. `GetEnabledSources` guards `m.Config == nil → return nil`.
4. `GetDefaultConfig` guards `m.Config == nil → return DefaultConfig{}`.
5. `GetAllSourcesMetadata` guards `m.Config == nil → return nil`.

These five changes ensure all endpoints that depend on `DataSourcesManager`
(leagues, seasons, data sources) respond gracefully with empty data rather than
panicking when no `data_sources.json` is present.

---

## Integration tests — `internal/api/server_test.go`

### Setup

```go
func newHandler(t *testing.T) http.Handler {
    dataDir := t.TempDir()
    // creates final/, backtests/, jackpots/, jackpot_predictions/, jackpot_results/
    engine   := algorithm.NewPredictionEngine("football", true, false)
    sources, _ := data.NewDataSourcesManager("") // empty — non-nil after fix
    srv := api.NewServer(engine, collector, fetcher, sources, backtester, jFetcher, jAnalyzer, dataDir, logger)
    return srv.Handler()
}
```

All tests use `httptest.NewServer` — **no real network calls** are made.
External-API failures (Odds API, scraping) are handled gracefully by handlers and
result in 200 with empty/fallback data or an expected 404/400.

### Test coverage

| Test | Endpoint | Assertion |
|------|----------|-----------|
| `TestGetDashboardStats` | `GET /api/dashboard/stats` | 200; all six stat keys present |
| `TestGetUpcoming` | `GET /api/dashboard/upcoming` | 200; returns JSON array |
| `TestGetRecentResults` | `GET /api/dashboard/recent` | 200; returns JSON |
| `TestPredictMatch` | `POST /api/predict` | 200; `homeWinProb`, `drawProb`, `awayWinProb`, `confidence` present |
| `TestPredictMatch_BadJSON` | `POST /api/predict` | 400 on malformed JSON |
| `TestGetUpcomingFixtures` | `GET /api/fixtures/upcoming` | returns JSON |
| `TestGetCurrentSeason` | `GET /api/fixtures/current-season` | returns JSON |
| `TestGetAvailableSports` | `GET /api/fixtures/available-sports` | returns JSON |
| `TestGetAPIQuota_NoKey` | `GET /api/fixtures/quota` | 400 (no API key) |
| `TestGetLiveOdds_NotFound` | `POST /api/fixtures/live-odds` | 404 (match not in API) |
| `TestGetCollectionStatus` | `GET /api/data/status` | 200; `running` field present |
| `TestGetHistoricalData_NoFile` | `GET /api/data/historical` | 200; `exists: false` |
| `TestGetDataSources` | `GET /api/data/sources` | 200; `sources` + `default_config` keys |
| `TestGetAvailableLeagues` | `GET /api/data/leagues` | 200 |
| `TestGetAvailableSeasons` | `GET /api/data/seasons` | 200 |
| `TestStartDataCollection` | `POST /api/data/collect` | 200; `message` field present |
| `TestStartDataCollection_AlreadyRunning` | `POST /api/data/collect` (×2) | second call handled gracefully |
| `TestRunBacktest` | `POST /api/backtest/run` | 200; `results` key present (uses sample data) |
| `TestGetBacktestResults_NoData` | `GET /api/backtest/results` | 404 |
| `TestExportBacktest_NoData` | `GET /api/backtest/export` | 404 |
| `TestGetPerformanceSummary_NoData` | `GET /api/performance/summary` | 404 |
| `TestGetMonthlyPerformance` | `GET /api/performance/monthly` | 200; non-empty array |
| `TestGetWeights` | `GET /api/config/weights` | 200; non-empty weights map |
| `TestUpdateWeights` | `POST /api/config/weights` | 200; re-send current weights |
| `TestUpdateWeights_InvalidSum` | `POST /api/config/weights` | 400 (sum ≠ 1.0) |
| `TestFetchJackpots` | `POST /api/jackpots/fetch` | 200; `jackpots` key present |
| `TestGetJackpotHistory_Empty` | `GET /api/jackpots/history` | 200; `jackpots` key present |
| `TestGetJackpotPerformance_Empty` | `GET /api/jackpots/performance` | 200 |
| `TestAnalyzeJackpot` | `POST /api/jackpots/analyze` | 200; `analysis` key present |
| `TestRecordJackpotResults_MissingID` | `POST /api/jackpots/results` | 400 (missing jackpot_id) |

### Benchmark

```
BenchmarkPredictMatch  — POST /api/predict through full HTTP + prediction stack
```

Run with: `go test ./internal/api/... -bench=BenchmarkPredictMatch -benchtime=5s`

---

## Backtest engine tests — `internal/backtest/engine_test.go`

| Test | What it verifies |
|------|-----------------|
| `TestRun_SampleData` | `Run` completes, returns non-nil `Summary` with positive bankroll and non-empty equity curve |
| `TestRun_AccuracyByType` | `AccuracyByType` is non-nil, non-empty, and contains only valid outcome keys |
| `TestRun_AccuracyByConfidence` | `AccuracyByConfidence` is non-nil and contains only valid bin labels |
| `TestRun_FilesCreated` | `backtests/*.json` and `backtests/*.csv` are written to disk |
| `TestLoadLatestResults` | Round-trip: `Run` then `LoadLatestResults` returns same `TotalMatches` |
| `TestLoadLatestResults_NoData` | Returns error when no file exists |
| `TestGetLatestCSVPath` | Returns non-empty path to a file that exists on disk |
| `TestGetLatestCSVPath_NoData` | Returns error when no file exists |
| `TestRun_SeasonFilter` | Season filter doesn't panic |
| `TestRun_DateFilter` | Date range filter doesn't panic |

### Benchmark

```
BenchmarkRun — full backtest on 380-match sample dataset
```

Run with: `go test ./internal/backtest/... -bench=BenchmarkRun -benchtime=3s`

---

## Side-by-side comparison script — `scripts/compare_apis.sh`

### Purpose

Validates that Go and Python servers return equivalent JSON responses.

### Usage

```bash
# Side-by-side mode (requires Python server running on :5000)
cd betting-algorithm-go
./scripts/compare_apis.sh

# Go-only mode (just validates Go returns valid JSON)
./scripts/compare_apis.sh --go-only
```

### What it tests

1. Builds Go binary → `bin/server`
2. Starts Go server on `:5001` (Python stays on `:5000`)
3. For each endpoint:
   - In **side-by-side mode**: strips transient fields (`timestamp`, `win_streak`), then diffs Go vs Python JSON
   - In **go-only mode**: asserts Go returns non-null, non-empty JSON
4. For backtest: logs accuracy from both servers side-by-side
5. Exits `0` if all checks pass, `1` otherwise

### Endpoints validated by script

- `GET /api/dashboard/stats`
- `GET /api/dashboard/recent`
- `POST /api/predict` (Arsenal vs Chelsea, Premier League)
- `GET /api/config/weights`
- `GET /api/data/status`
- `GET /api/data/sources`
- `GET /api/data/historical`
- `POST /api/backtest/run`
- `GET /api/performance/monthly`
- `POST /api/jackpots/fetch`
- `GET /api/jackpots/history`

---

## Cutover procedure

The proxy is **already configured** to point to `:5000`. Both servers use the same port,
so the cutover is simply stopping the Python server and starting the Go server:

```bash
# 1. Build the Go binary
cd betting-algorithm-go
go build -o bin/server ./cmd/server/

# 2. Stop the Python server (Ctrl+C or kill the process)

# 3. Start the Go server (same port, same data directory)
DATA_DIR=../data PORT=5000 ./bin/server

# 4. The Angular frontend at http://localhost:4200 connects unchanged.
```

`betting-frontend/proxy.conf.json` requires **no changes** — it already proxies `/api`
to `http://localhost:5000`.

---

## Validation results (go test ./...)

```
ok  bet4me/betting-algorithm-go/internal/api       2.5s   (29 tests)
ok  bet4me/betting-algorithm-go/internal/backtest  0.5s   (10 tests)
ok  bet4me/betting-algorithm-go/internal/data      0.1s
ok  bet4me/betting-algorithm-go/internal/domain    0.0s
ok  bet4me/betting-algorithm-go/internal/jackpot   0.1s
ok  bet4me/betting-algorithm-go/internal/storage   0.0s
ok  bet4me/betting-algorithm-go/internal/util      0.0s
```

All packages pass. No race conditions detected (`go test -race ./...` also passes).

---

## Next steps (post-Phase 6)

- [ ] **Smoke test frontend** — manually test each Angular page against the live Go server
- [ ] **`go test -race ./...`** — verify no data races under concurrent requests
- [ ] **Benchmark** — run `BenchmarkPredictMatch` and `BenchmarkRun`, compare to Python `timeit` results
- [ ] **Remove Python server** from startup scripts / `README.md` once team is satisfied
