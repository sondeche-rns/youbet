# Go Implementation V2 — Sync with Python Develop Branch

## Overview

This document describes the V2 implementation plan that brings the Go codebase (`feature/golang-refactor`) in sync with the Python codebase in the `develop` branch. A detailed diff confirmed the Python source files are **identical** between branches — the only file-level differences were data output files (jackpot JSON/CSV). However, 2 critical methods in the Go context builder were left as stubs, permanently disabling 4 of the 18 algorithm factors regardless of available data.

---

## Problem: Disabled Algorithm Factors

The following factors were **always inactive** because the context builder stubs returned `nil`:

| Factor | Weight | Reason Inactive |
|---|---|---|
| `h2hHistorical` | 0.04 | `getH2HRecord()` always returned `nil` |
| `h2hAnomaly` | 0.12 (conditional) | `getH2HRecord()` always returned `nil` |
| `awayDrawFrequency` | 0.03 | `calculateSeasonStats()` always returned `nil` |
| `counterAttackEfficiency` | 0.04 | Fell back to single-match possession, no season average |

### Root Cause

`MatchContextBuilder.historicalData` was typed as `interface{}` and never populated. The helper functions `BuildH2HRecordFromMatches()` and `CalculateSeasonStatsFromMatches()` already existed in `context/builder.go` but were never called from `getH2HRecord()` / `calculateSeasonStats()`.

Additionally, the Python `app.py` has 28 HTTP endpoints (including `GET /` HTML) vs the Go server's 27.

---

## Implementation Phases

### Phase 1 — Fix Context Builder Stubs ✅ COMPLETE
**Files:** `betting-algorithm-go/internal/context/builder.go`

**Changes made:**

1. Changed field type from `interface{}` to concrete type:
   ```go
   // Before:
   historicalData interface{}
   // After:
   historicalData []HistoricalMatch
   ```

2. Updated `NewMatchContextBuilder` signature to accept `[]HistoricalMatch`.

3. Implemented `getH2HRecord()` — replaces the stub:
   - Filters `b.historicalData` for matches involving both teams (either venue)
   - Calls the existing `BuildH2HRecordFromMatches()` helper
   - Caches result in `b.h2hCache`

4. Implemented `calculateSeasonStats()` — replaces the stub:
   - Filters `b.historicalData` for all matches involving the team
   - Calls the existing `CalculateSeasonStatsFromMatches()` helper
   - Caches result in `b.seasonStatsCache`

5. Added `SetHistoricalData(matches []HistoricalMatch)` method:
   - Updates the historical dataset
   - Invalidates both caches so next `BuildContext()` calls use fresh data
   - Used for post-collection refresh

**Existing helpers reused (no new code needed for logic):**
- `BuildH2HRecordFromMatches()` — line 311 of `context/builder.go`
- `CalculateSeasonStatsFromMatches()` — line 350 of `context/builder.go`

---

### Phase 2 — Add Data Bridge (MatchRecord → HistoricalMatch)
**Files:** `betting-algorithm-go/internal/algorithm/algorithm.go`, `betting-algorithm-go/internal/context/builder.go`

**Changes required:**

1. Update `algorithm.go` to use typed `historicalData` field (eliminates `interface{}`):
   ```go
   // Add import:
   "bet4me/betting-algorithm-go/internal/context"

   // Change field:
   historicalData []context.HistoricalMatch

   // Update method:
   func (e *PredictionEngine) SetHistoricalData(data []context.HistoricalMatch)
   ```

2. Add bridge conversion function (in `context/builder.go` or `cmd/server/main.go`):
   ```go
   // Converts storage.MatchRecord rows into context.HistoricalMatch for the builder
   func MatchRecordsToHistoricalMatches(records []storage.MatchRecord) []HistoricalMatch {
       matches := make([]HistoricalMatch, 0, len(records))
       for _, r := range records {
           matches = append(matches, HistoricalMatch{
               Date:           r.Date,
               HomeTeam:       r.HomeTeam,
               AwayTeam:       r.AwayTeam,
               HomeGoals:      r.HomeGoals,
               AwayGoals:      r.AwayGoals,
               HomePossession: r.HomePossession,
               AwayPossession: r.AwayPossession,
               Competition:    "Premier League", // not stored in MatchRecord
               Season:         r.Season,
           })
       }
       return matches
   }
   ```

**Field mapping between `storage.MatchRecord` and `context.HistoricalMatch`:**

| MatchRecord field | HistoricalMatch field |
|---|---|
| `HomeTeam` | `HomeTeam` |
| `AwayTeam` | `AwayTeam` |
| `HomeGoals` | `HomeGoals` |
| `AwayGoals` | `AwayGoals` |
| `HomePossession` | `HomePossession` |
| `AwayPossession` | `AwayPossession` |
| `Date` | `Date` |
| `Season` | `Season` |
| *(not in MatchRecord)* | `Competition` → default `"Premier League"` |

---

### Phase 3 — Wire Server to Feed Context Builder
**Files:** `betting-algorithm-go/cmd/server/main.go`, `betting-algorithm-go/internal/api/server.go`

**Changes required:**

#### `cmd/server/main.go` — startup loading:
```go
// After creating CSVStore, attempt to load existing historical data
store := storage.NewCSVStore("data")
historicalPath := filepath.Join("data", "final", "historical_dataset.csv")
var historicalMatches []context.HistoricalMatch

if records, err := store.ReadHistoricalData(historicalPath); err == nil {
    historicalMatches = context.MatchRecordsToHistoricalMatches(records)
    log.Printf("Loaded %d historical matches for context building", len(historicalMatches))
}

// Pass to context builder (and engine)
contextBuilder := context.NewMatchContextBuilder(historicalMatches)
engine := algorithm.NewPredictionEngine("football", domain.FootballWeightsV2)
engine.SetHistoricalData(historicalMatches)
```

#### `internal/api/server.go` — post-collection refresh:
1. Add `contextBuilder *context.MatchContextBuilder` and `csvStore *storage.CSVStore` fields to `Server` struct.
2. In the `startDataCollection` background goroutine, after collection completes:
   ```go
   // Refresh context builder with newly collected data
   if records, err := s.csvStore.ReadHistoricalData(historicalPath); err == nil {
       matches := context.MatchRecordsToHistoricalMatches(records)
       s.contextBuilder.SetHistoricalData(matches)
       s.engine.SetHistoricalData(matches)
   }
   ```

> **Note:** The prediction engine calls `context.NewMatchContextBuilder(e.historicalData)` per-request in `calculateAllFactors`. After this phase, `e.historicalData` holds the typed `[]context.HistoricalMatch` slice, so the per-request context builder is automatically populated.

---

### Phase 4 — Add Missing `GET /` Endpoint
**Files:** `betting-algorithm-go/internal/api/server.go`

**Change required:**

Python Flask serves the Angular frontend via `GET /`. The Go server is missing this endpoint (27 routes vs Python's 28).

```go
// Add at end of route registration, gated by env var for dev compatibility:
if os.Getenv("SERVE_STATIC") == "true" {
    distPath := filepath.Join("..", "betting-frontend", "dist", "betting-frontend")
    fileServer := http.FileServer(http.Dir(distPath))
    r.Get("/*", func(w http.ResponseWriter, r *http.Request) {
        // SPA fallback: serve index.html for unmatched routes
        if _, err := os.Stat(filepath.Join(distPath, r.URL.Path)); os.IsNotExist(err) {
            http.ServeFile(w, r, filepath.Join(distPath, "index.html"))
            return
        }
        fileServer.ServeHTTP(w, r)
    })
}
```

Set `SERVE_STATIC=true` in production `.env`. Dev mode continues using Angular's `ng serve` proxy.

---

### Phase 5 — Tests & Validation
**Files:** `betting-algorithm-go/internal/context/builder_test.go`

**New test cases required:**

```go
// TestGetH2HRecord_WithData — verifies H2H record is built from historical data
// TestGetH2HRecord_AnomalyTrigger — verifies anomaly fires when weaker team streak >= 3
// TestGetH2HRecord_InsufficientData — verifies nil when < 3 H2H matches
// TestCalculateSeasonStats_WithData — verifies away draw rate calculation
// TestBuildContext_PopulatesH2HAndSeasonStats — integration: full BuildContext call
// TestSetHistoricalData_InvalidatesCaches — verifies cache is cleared on data update
```

**Fixture setup for tests:**
```go
func makeHistoricalMatches() []HistoricalMatch {
    return []HistoricalMatch{
        {Date: "2024-01-10", HomeTeam: "Arsenal", AwayTeam: "Chelsea",
         HomeGoals: 2, AwayGoals: 1, HomePossession: 58, AwayPossession: 42},
        // ... 9 more matches covering H2H and season data
    }
}
```

**Manual validation steps:**
```bash
cd betting-algorithm-go

# 1. Build — must compile cleanly
go build ./...

# 2. Run context tests
go test ./internal/context/... -v

# 3. Run all tests
go test ./...

# 4. Start server and trigger data collection
./betting-algorithm-go &
curl -X POST http://localhost:5000/api/data/collect \
  -H "Content-Type: application/json" \
  -d '{"sport":"soccer_epl","seasons":["2324"]}'

# 5. After collection, predict a match and verify factors are active
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"home_team":"Arsenal","away_team":"Chelsea"}'

# Expected: h2hHistorical.triggered=true (or h2hAnomaly if streak >= 3)
# Expected: awayDrawFrequency.triggered=true (if away draw rate > 35%)
```

---

## Summary of Changes per Phase

| Phase | Status | Files Changed | Scope |
|---|---|---|---|
| 1 | ✅ Complete | `context/builder.go` | Implement stubs using existing helpers, add SetHistoricalData |
| 2 | 🔄 Pending | `algorithm/algorithm.go`, `context/builder.go` | Type bridge, remove interface{} |
| 3 | 🔄 Pending | `cmd/server/main.go`, `api/server.go` | Startup load + post-collection refresh |
| 4 | 🔄 Pending | `api/server.go` | Add `GET /` static file endpoint |
| 5 | 🔄 Pending | `context/builder_test.go` | Unit + integration tests |

Each phase is independently deployable and testable. Phases 1–3 are highest priority as they restore algorithmic correctness. Phase 4 is convenience for production deployment. Phase 5 validates correctness.

---

## Architecture: Data Flow After V2

```
Server Startup
    │
    ▼
CSVStore.ReadHistoricalData()
    │
    ▼
context.MatchRecordsToHistoricalMatches()  ← Bridge (Phase 2)
    │
    ├──→ context.NewMatchContextBuilder(matches)  ← Now populated (Phase 1)
    │
    └──→ engine.SetHistoricalData(matches)
              │
              ▼
         Per-request: calculateAllFactors()
              │
              ├──→ contextBuilder.BuildContext()
              │         ├── getH2HRecord() → queries historicalData ✅
              │         └── calculateSeasonStats() → queries historicalData ✅
              │
              ├──→ calculateH2HFactors(ctx) → h2hHistorical / h2hAnomaly ACTIVE ✅
              ├──→ calculateAwayDrawFrequency(ctx) → ACTIVE when rate > 35% ✅
              └──→ calculateCounterAttackEfficiency(ctx) → uses season avg possession ✅

POST /api/data/collect (background)
    │
    └──→ On complete: contextBuilder.SetHistoricalData() + engine.SetHistoricalData()
              (cache invalidated, subsequent predictions use new data)
```
