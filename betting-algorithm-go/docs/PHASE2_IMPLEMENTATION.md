# Phase 2: Core Algorithm — Implementation Reference

> **Status:** Complete
> **Branch:** `feature/golang-refactor`
> **Packages created:** `internal/algorithm`, `internal/context`
> **Python source files ported:** `algorithm.py` · `calibration.py` · `context_builder.py`

---

## Table of Contents

1. [Overview](#overview)
2. [Package Structure](#package-structure)
3. [Data Flow](#data-flow)
4. [File-by-File Reference](#file-by-file-reference)
   - [algorithm/algorithm.go — Prediction Engine](#algorithmalgorithmgo--prediction-engine)
   - [algorithm/factors.go — Factor Calculations](#algorithmfactorsgo--factor-calculations)
   - [algorithm/poisson.go — Poisson Goal Model](#algorithmpoissongopoisson-goal-model)
   - [algorithm/calibration.go — Self-Improving Calibration](#algorithmcalibrationgo--self-improving-calibration)
   - [algorithm/probs.go — Probability Blending](#algorithmprobsgo--probability-blending)
   - [context/builder.go — Match Context Builder](#contextbuildergo--match-context-builder)
5. [The 17-Factor Model](#the-17-factor-model)
6. [Probability Pipeline](#probability-pipeline)
7. [Import Cycle Resolution](#import-cycle-resolution)
8. [Go vs Python Differences](#go-vs-python-differences)
9. [Known Limitations & TODOs](#known-limitations--todos)
10. [Testing Strategy](#testing-strategy)

---

## Overview

Phase 2 ports the core prediction logic. It builds on Phase 1 domain types and produces `PredictionResult` objects from `MatchData` inputs.

The prediction pipeline has three stages:
1. **Factor calculation** — 17 weighted factors (10 original + 7 V2 contextual) produce per-factor scores
2. **Probability generation** — Poisson goal model + factor-weighted blending produce `homeWinProb / drawProb / awayWinProb`
3. **Recommendation** — Kelly Criterion applied to best-value outcome

The `context` package builds `MatchContext` from raw match fields and feeds it to contextual factors. It is a separate package from `algorithm` to avoid import cycles.

---

## Package Structure

```
betting-algorithm-go/
├── internal/
│   ├── algorithm/
│   │   ├── algorithm.go       PredictionEngine, MatchData, SportConfig, NewPredictionEngine, Predict
│   │   ├── factors.go         All 17 factor calculation methods on PredictionEngine
│   │   ├── poisson.go         Poisson PMF via gonum/stat/distuv, goal matrix (0–5 × 0–5)
│   │   ├── calibration.go     CalibrationEngine — thread-safe weight adjustment
│   │   └── probs.go           blendProbabilities, normalizeWeights, buildRecommendation
│   │
│   └── context/
│       └── builder.go         MatchContextBuilder — loads managers.json, builds H2H + season stats
```

---

## Data Flow

```
Predict(data *MatchData)
        │
        ├── calculateAllFactors(data)
        │       ├── context.NewMatchContextBuilder(historicalData)
        │       │       └── loadManagerDatabase() ← data/managers.json
        │       │
        │       ├── BuildContext(homeTeam, awayTeam, possession, positions, form)
        │       │       ├── classifyDefensiveStyle(possession)
        │       │       ├── getManagerInfo(team) ← managerDB
        │       │       ├── parseForm(formStr) → []string{"W","D",...}
        │       │       ├── getH2HRecord(home, away, positions)
        │       │       └── calculateSeasonStats(team, venue)
        │       │
        │       ├── Original 10 factors: expectedGoals, advancedStats, teamStrength,
        │       │   tacticalMatchup, currentForm, playerImpact, restAndFatigue,
        │       │   motivation, homeAdvantage, externalFactors
        │       │
        │       └── V2/V3 factors: teamQualityGap, h2hHistorical, h2hAnomaly,
        │           possessionQuality, managerMomentum, relegationMotivation,
        │           counterAttackEfficiency, awayDrawFrequency
        │
        ├── calculatePoissonProbabilities(data, factors)
        │       └── distuv.Poisson{Lambda: homeXg/awayXg}.Prob(goals) × 6×6 scoreline matrix
        │
        ├── blendProbabilities(factorProbs, poissonProbs, dataQuality)
        │
        └── buildRecommendation(probs, odds) ← Kelly Criterion
```

---

## File-by-File Reference

### `algorithm/algorithm.go` — Prediction Engine

**Location:** `internal/algorithm/algorithm.go` (~350 lines)

#### Types

| Type | Purpose |
|------|---------|
| `PredictionEngine` | Core struct holding weights, Elo ratings, calibration engine, historical data |
| `SportConfig` | Per-sport parameters: weights, home advantage, base Elo, K-factor, thresholds |
| `CalibrationParams` | Platt scaling parameters `A` and `B` |
| `PredictionResult` | Full prediction output with probabilities, factors, recommendation, expected goals |
| `Recommendation` | Betting suggestion with outcome, Kelly stake, EV, confidence, per-outcome EVs |
| `MatchData` | All input fields for a match — see field groups below |

#### `MatchData` field groups

| Group | Fields |
|-------|--------|
| Identity | `HomeTeam`, `AwayTeam`, `Date`, `Venue`, `Competition` |
| Odds | `HomeOdds *float64`, `DrawOdds *float64`, `AwayOdds *float64` |
| Expected Goals | `HomeXg float64`, `AwayXg float64` |
| Elo | `HomeElo *float64`, `AwayElo *float64` |
| Advanced Stats | `HomePPDA`, `AwayPPDA`, `HomePossession`, `AwayPossession`, `HomeShots`, `HomeShotsOnTarget`, `AwayShots`, `AwayShotsOnTarget` |
| Form/Position | `HomePosition`, `AwayPosition`, `HomeForm`, `AwayForm` |
| Tactical | `HomeFormation`, `AwayFormation`, `HomeStyle`, `AwayStyle` |
| Player Impact | `HomeKeyPlayersAvailable`, `AwayKeyPlayersAvailable`, `HomeStarRating`, `AwayStarRating` |
| Rest/Fatigue | `HomeRestDays`, `AwayRestDays`, `HomeGamesLast7`, `AwayGamesLast7` |
| Context | `IsDerby`, `IsNeutralVenue`, `Weather`, `AwayTravelDistance`, `ExpectedAttendancePct` |

#### `NewPredictionEngine` constructor

```go
engine := algorithm.NewPredictionEngine(sport, useV2Weights, enableCalibration)
// sport: "football" | "basketball" | "tennis" | default→football
// useV2Weights: true loads domain.FootballWeightsV2 (17 factors)
// enableCalibration: true creates CalibrationEngine(learningRate=0.01, maxHistory=1000)
```

`loadSportConfig` returns a `SportConfig` per sport:

| Sport | HomeAdvantage | BaseElo | KFactor | DrawThreshold | MaxGoalsLambda |
|-------|--------------|---------|---------|---------------|----------------|
| football | 0.10 | 1500 | 32 | 0.25 | 4.0 |
| basketball | 0.06 | 1500 | 20 | — | — |
| tennis | — | — | — | — | — |

#### Other public methods

| Method | Description |
|--------|-------------|
| `SetHistoricalData(data interface{})` | Passes historical match data to `historicalData` for context building |
| `RecordActualResult(matchID, actual, predicted, probs, factors)` | Delegates to `calibrationEngine.RecordPrediction` if calibration is enabled |
| `GetWeights() map[string]float64` | Returns copy of current weight map |
| `SetWeights(w map[string]float64)` | Replaces weight map (used by `/api/config/weights` endpoint) |

---

### `algorithm/factors.go` — Factor Calculations

**Location:** `internal/algorithm/factors.go` (~450 lines)

All factor methods are on `*PredictionEngine` and return `map[string]interface{}`. Each map always contains a `"score"` key (float64, 0–1, where 0.5 = neutral) used for probability blending.

#### Entry point

`calculateAllFactors(data *MatchData) map[string]interface{}` — calls all 17 factors and returns a combined map. Builds `MatchContext` via `context.NewMatchContextBuilder` before computing contextual factors.

#### Original 10 factors

| Factor key | Method | Score computation |
|------------|--------|-------------------|
| `expectedGoals` | `calculateExpectedGoals` | `0.5 + tanh(xgDiff/2) * 0.5` |
| `advancedStats` | `calculateAdvancedStats` | `0.5 + (homeScore - awayScore) * 0.5` where each score = PPDA(0.3) + possession(0.3) + shotAccuracy(0.4) |
| `teamStrength` | `calculateTeamStrength` | Elo win expectancy `1 / (1 + 10^(-eloDiff/400))` |
| `tacticalMatchup` | `analyzeTacticalMatchup` | Lookup in 3×3 style-matchup matrix (`attacking/defensive/balanced`); default 0.52 |
| `currentForm` | `calculateCurrentForm` | `0.5 + (homeFormScore - awayFormScore) * 0.5`; form string → score via `formToScore` helper |
| `playerImpact` | `calculatePlayerImpact` | Combines star rating and key-player availability into a single 0–1 score |
| `restAndFatigue` | `calculateRestFatigue` | Normalizes rest days and recent game count into fatigue advantage |
| `motivation` | `calculateMotivation` | Derby boost (`IsDerby`), neutral venue adjustment, attendance effect |
| `homeAdvantage` | `calculateHomeAdvantage` | `config.HomeAdvantage` (0.10 for football) adjusted for neutral venue |
| `externalFactors` | `calculateExternalFactors` | Weather, travel distance adjustments |

#### V2/V3 factors

| Factor key | Method | Notes |
|------------|--------|-------|
| `teamQualityGap` | `calculateTeamQualityGap` | Star-rating gap between teams |
| `h2hHistorical` | `calculateH2HFactors` (returns both) | H2H win rate from `MatchContext.H2HRecord` |
| `h2hAnomaly` | `calculateH2HFactors` | Active when `WeakerTeamUnbeatenStreak >= 3`; replaces h2hHistorical at 3× weight |
| `possessionQuality` | `calculatePossessionQuality` | Combines possession %, defensive style, and season PPDA |
| `managerMomentum` | `calculateManagerMomentum` | New-manager bounce: `baseBoost * (0.85 ^ gamesManaged)`; reduced by `InterimMultiplier` if interim |
| `relegationMotivation` | `calculateRelegationMotivation` | Extra motivation boost for teams in positions 18–20 |
| `counterAttackEfficiency` | `calculateCounterAttackEfficiency` | Rewards low-possession teams with high shot efficiency |
| `awayDrawFrequency` | `calculateAwayDrawFrequency` | Boosts draw probability for away teams with historically flat results |

#### Helper functions

| Function | Purpose |
|----------|---------|
| `formToScore(formStr string) float64` | Parses "WWDLD": W=1.0, D=0.5, L=0.0; averages last 5 |
| `min(a, b int) int` | Go 1.21 built-in used for form string slicing |

---

### `algorithm/poisson.go` — Poisson Goal Model

**Location:** `internal/algorithm/poisson.go` (~80 lines)

Uses `gonum.org/v1/gonum/stat/distuv.Poisson` for PMF calculation.

#### `calculatePoissonProbabilities`

```
homeXg, awayXg ← factors["expectedGoals"].homeXg / awayXg
                  (default 1.3 if missing)

strengthFactor ← factors["teamStrength"].score
                 (default 0.5 if missing)

homeXg *= (0.8 + strengthFactor * 0.4)
awayXg *= (1.2 - strengthFactor * 0.4)

Both capped at config.MaxGoalsLambda (4.0 for football)

For homeGoals in [0,5], awayGoals in [0,5]:
    prob = Poisson(homeXg).PMF(homeGoals) × Poisson(awayXg).PMF(awayGoals)
    homeWinProb += prob  if homeGoals > awayGoals
    drawProb    += prob  if homeGoals == awayGoals
    awayWinProb += prob  if homeGoals < awayGoals
```

The 6×6 scoreline matrix (0–0 through 5–5) captures ~95% of actual match outcomes. Residual probability from higher scores is absorbed into the three outcome probabilities without explicit normalization — they already sum very close to 1.0.

---

### `algorithm/calibration.go` — Self-Improving Calibration

**Location:** `internal/algorithm/calibration.go` (~150 lines)

#### `CalibrationEngine`

Thread-safe weight-adjustment system using `sync.RWMutex`.

```go
engine := algorithm.NewCalibrationEngine(learningRate=0.01, maxHistory=1000)
```

| Method | Description |
|--------|-------------|
| `RecordPrediction(matchID, predicted, actual, probs, factors)` | Thread-safe: acquires write lock; appends to `predictionHistory` (FIFO, capped at `maxHistory`); marks each factor's contribution as correct/incorrect |
| `CalibrateWeights(currentWeights) map[string]float64` | Read-locks history; for each factor with >= 20 samples, adjusts weight by `learningRate * (factorAccuracy - overallAccuracy)`; caps adjustment at ±10% of original weight |
| `GetReport() map[string]interface{}` | Returns per-factor accuracy, overall accuracy, and total predictions |

Calibration guards:
- **Minimum samples**: 20 predictions per factor before adjustment
- **Max adjustment**: ±10% of current weight per calibration cycle
- **No overfitting**: learning rate 0.01 means slow, stable drift

#### `FactorStats`

```go
type FactorStats struct {
    Correct      int
    Total        int
    Accuracy     float64
    Contribution float64
}
```

---

### `algorithm/probs.go` — Probability Blending

**Location:** `internal/algorithm/probs.go` (~120 lines)

#### `blendProbabilities`

Combines factor-derived probabilities with Poisson probabilities weighted by data quality:

```
factorProbs = aggregateFactorProbabilities(factors, weights)
              (weighted sum of each factor's score, normalized)

blend = factorProbs * (1 - dataQuality) + poissonProbs * dataQuality
        where dataQuality ∈ [0, 1] (higher = trust Poisson more)

Final probabilities renormalized to sum to 1.0
```

#### `normalizeWeights`

Filters to only active factors (weight > 0, triggered if conditional), then divides each weight by sum so the active set sums to 1.0. This is the dynamic renormalization described in `domain/config.go`.

#### `buildRecommendation`

Applies Kelly Criterion to each outcome (home/draw/away) if odds are provided:

```
For each outcome:
    impliedProb = 1 / odds
    ev = (predictedProb * odds) - 1
    kelly = util.CalculateKellyStake(predictedProb, odds, 0.25, 0.05)

Recommendation: outcome with highest EV where EV > 0
If no positive EV outcome → recommendation = "SKIP"
```

---

### `context/builder.go` — Match Context Builder

**Location:** `internal/context/builder.go` (~300 lines)

#### `MatchContextBuilder`

```go
builder := context.NewMatchContextBuilder(historicalData)
ctx := builder.BuildContext(homeTeam, awayTeam, homePoss, awayPoss, homePos, awayPos, homeFormStr, awayFormStr)
```

Constructor calls `loadManagerDatabase()` which looks for `data/managers.json` then `../data/managers.json`. Silent on failure (returns empty manager DB).

#### `BuildContext` signature

Takes individual match fields rather than a `MatchData` struct to avoid importing `algorithm` from `context` (which would create an import cycle — see [Import Cycle Resolution](#import-cycle-resolution)).

#### Internal methods

| Method | Returns | Description |
|--------|---------|-------------|
| `classifyDefensiveStyle(possession float64)` | `DefensiveStyle` | > 55% → HighPress; 45–55% → Balanced; < 45% → LowBlock |
| `parseForm(formStr string)` | `[]string` | Filters to W/D/L characters; defaults to five "D"s if empty |
| `getManagerInfo(team string)` | `*ManagerInfo` | Lookup in `managerDB`; nil if team not found |
| `getH2HRecord(home, away, homePos, awayPos)` | `*H2HRecord` | Returns nil (placeholder — full impl requires historical data query) |
| `calculateSeasonStats(team, venue)` | `map[string]any` | Returns empty map (placeholder — populated when historical data is set) |
| `calculateGamesManaged(appointmentDate string)` | `int` | `weeks since appointment`; defaults 50 for invalid dates |
| `calculateWeakerTeamStreak(results, home, away, homePos, awayPos)` | `int` | Counts consecutive unbeaten H2H games for the team at higher position number |

#### H2H cache

```go
b.h2hCache[fmt.Sprintf("%s_%s", homeTeam, awayTeam)]
```

Caches computed `*H2HRecord` per team pair for the lifetime of the builder instance.

---

## The 17-Factor Model

| # | Factor | V1 weight | V2 weight | Type |
|---|--------|-----------|-----------|------|
| 1 | expectedGoals | 0.20 | 0.12 | Always active |
| 2 | advancedStats | 0.15 | 0.07 | Always active |
| 3 | teamStrength (Elo) | 0.12 | 0.07 | Always active |
| 4 | tacticalMatchup | 0.12 | 0.06 | Always active |
| 5 | currentForm | 0.10 | 0.05 | Always active |
| 6 | playerImpact | 0.10 | 0.05 | Always active |
| 7 | restAndFatigue | 0.08 | 0.04 | Always active |
| 8 | motivation | 0.06 | 0.03 | Always active |
| 9 | homeAdvantage | 0.05 | 0.02 | Always active |
| 10 | externalFactors | 0.02 | 0.01 | Always active |
| 11 | teamQualityGap | — | 0.10 | Always active (V3) |
| 12 | h2hHistorical | — | 0.04 | Active when H2H data available |
| 13 | h2hAnomaly | — | 0.12 | **Conditional**: triggers when weaker team unbeaten ≥ 3; replaces h2hHistorical |
| 14 | possessionQuality | — | 0.07 | Active when possession data available |
| 15 | managerMomentum | — | 0.04 | Active when manager data loaded |
| 16 | relegationMotivation | — | 0.04 | Active for positions 18–20 |
| 17 | counterAttackEfficiency | — | 0.04 | Active for low-possession teams |
| *(18)* | awayDrawFrequency | — | 0.03 | Modifies draw probability directly |

Active factors are renormalized at runtime so their weights always sum to 1.0.

---

## Probability Pipeline

```
MatchData
    │
    ▼
calculateAllFactors() → factors map[string]interface{}
    │                        (each factor has "score" ∈ [0,1])
    │
    ├─► calculatePoissonProbabilities()
    │       └─► poissonProbs {Home, Draw, Away}
    │
    ├─► blendProbabilities(factorProbs, poissonProbs, dataQuality)
    │       └─► blendedProbs (normalized to sum 1.0)
    │
    └─► buildRecommendation(blendedProbs, odds)
            └─► *Recommendation (SKIP if no positive EV)
```

---

## Import Cycle Resolution

A potential import cycle existed:
```
algorithm → context (to use BuildContext)
context → algorithm (to reference MatchData)
```

**Solution**: `BuildContext` accepts individual primitive parameters (`homeTeam string`, `possession float64`, etc.) rather than `*algorithm.MatchData`. This means `context` imports only `domain` and never `algorithm`.

```go
// context/builder.go — no algorithm import
func (b *MatchContextBuilder) BuildContext(
    homeTeam, awayTeam string,
    homePossession, awayPossession float64,
    homePos, awayPos int,
    homeFormStr, awayFormStr string,
) *domain.MatchContext
```

`factors.go` (in `algorithm`) calls `context.NewMatchContextBuilder` and passes the relevant `MatchData` fields individually.

---

## Go vs Python Differences

| Concern | Python | Go |
|---------|--------|----|
| **Factor output** | Returns `FactorResult` dataclass | Returns `map[string]interface{}` with `"score"` key |
| **Poisson PMF** | `scipy.stats.poisson.pmf(k, lambda)` | `distuv.Poisson{Lambda: λ}.Prob(k)` from gonum |
| **Weight normalization** | In-place dict update | Returns new `map[string]float64` |
| **Calibration thread safety** | Python GIL | `sync.RWMutex` on prediction history |
| **Import cycle** | Not a concern (dynamic imports) | Resolved by passing primitives instead of `MatchData` struct |
| **Optional odds** | `Optional[float] = None` | `*float64` pointer (nil = absent) |
| **Multi-sport config** | Separate config dicts | `SportConfig` struct returned by `loadSportConfig` switch |
| **Calibration params** | Platt scaling in `calibration.py` | `CalibrationParams{A, B}` in engine; Platt sigmoid available but calibration is primarily weight-based |

---

## Known Limitations & TODOs

1. **H2H history not queried from historical data.** `getH2HRecord` returns nil when historical data is set. A real implementation needs to filter `[]storage.MatchRecord` for matches between the two teams (requires type assertion on `b.historicalData`).

2. **Season stats are empty placeholders.** `calculateSeasonStats` always returns an empty map. Contextual factors that depend on `HomeSeasonStats` / `AwaySeasonStats` fall back to neutral values.

3. **Factor output is `map[string]interface{}` not `domain.FactorResult`.** This is a temporary inconsistency. Phase 5 API serialization converts this map to `FactorResult`-shaped JSON for the frontend. Refactoring to return `*domain.FactorResult` from each factor function would improve type safety.

4. **`formToScore` uses a simple average.** The Python version applied recency weighting (most recent game weighted higher). The Go version averages all available results equally.

5. **`calculateManagerMomentum` uses `gamesManaged` estimated from appointment date.** The actual `GamesManaged` field from `managers.json` is not used in the decay formula if `calculateGamesManaged` is called separately.

6. **Calibration does not persist.** `predictionHistory` and `factorPerformance` are in-memory only. Restoring calibration state after server restart requires serializing and loading the `CalibrationEngine` to/from JSON (not yet implemented).

---

## Testing Strategy

### `algorithm/algorithm_test.go`

| Test | Assertion |
|------|-----------|
| `TestNewPredictionEngine_Football` | Config has correct home advantage, Elo base, weights |
| `TestNewPredictionEngine_V2Weights` | `useV2Weights=true` loads 17-factor weight map |
| `TestPredict_BasicMatch` | Returns result with probabilities summing to ~1.0 |
| `TestPredict_ProbabilitiesSum` | `Home + Draw + Away` = 1.0 ± 1e-9 |
| `TestPredict_WithOdds` | Recommendation is non-nil when odds provided |
| `TestPredict_NoOdds` | Recommendation may be SKIP |
| `TestGetSetWeights` | `SetWeights` then `GetWeights` returns same map |
| `TestCalibration_RecordAndCalibrateWeights` | After 25 correct predictions for one factor, that factor's weight increases |
| `TestPoissonProbabilities_Sum` | Probabilities from Poisson model sum to ≤ 1.0 |
| `TestContextBuilder_NeutralContext` | Empty team names return neutral context |
| `TestContextBuilder_DefensiveStyle` | possession=60 → HighPress; 50 → Balanced; 40 → LowBlock |
| `TestFormToScore` | "WWWWW" → 1.0; "LLLLL" → 0.0; "DDDDD" → 0.5 |
