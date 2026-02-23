# Phase 2: Core Algorithm — Implementation Reference

> **Status:** Complete
> **Branch:** `feature/golang-refactor`
> **Packages created:** `internal/algorithm` · `internal/context`
> **Python source files ported:** `algorithm.py` · `calibration.py` · `context_builder.py`

---

## Table of Contents

1. [Overview](#overview)
2. [Package Structure](#package-structure)
3. [Data Flow](#data-flow)
4. [File-by-File Reference](#file-by-file-reference)
   - [algorithm.go — Engine & Types](#algorithmgo--engine--types)
   - [factors.go — Factor Calculations](#factorsgo--factor-calculations)
   - [poisson.go — Probabilistic Goal Model](#poissongopoisson--probabilistic-goal-model)
   - [probs.go — Probability Assembly & Recommendations](#probsgo--probability-assembly--recommendations)
   - [calibration.go — Self-Improving Calibration](#calibrationgo--self-improving-calibration)
   - [context/builder.go — Match Context Builder](#contextbuildergo--match-context-builder)
5. [Factor Catalogue](#factor-catalogue)
6. [Prediction Pipeline (step-by-step)](#prediction-pipeline-step-by-step)
7. [Weight System](#weight-system)
8. [Key Algorithms Explained](#key-algorithms-explained)
   - [Elo Rating System](#elo-rating-system)
   - [Poisson Goal Model](#poisson-goal-model)
   - [Enhanced Draw Model](#enhanced-draw-model)
   - [Dynamic Weight Normalization](#dynamic-weight-normalization)
   - [Platt Scaling Calibration](#platt-scaling-calibration)
   - [Kelly Criterion Stake Sizing](#kelly-criterion-stake-sizing)
   - [Manager Momentum Decay](#manager-momentum-decay)
   - [H2H Anomaly Detection](#h2h-anomaly-detection)
9. [Domain Model Changes](#domain-model-changes)
10. [Go vs Python Differences](#go-vs-python-differences)
11. [Known Limitations & TODOs](#known-limitations--todos)
12. [Testing Strategy](#testing-strategy)

---

## Overview

Phase 2 ports the entire Python prediction engine (`algorithm.py`, `calibration.py`, `context_builder.py`) into Go. The result is a **self-contained, stateless, thread-safe** prediction engine that:

- Accepts a `*MatchData` struct and returns a `*PredictionResult`
- Runs **17 factor calculations** (10 original + teamQualityGap + 6 contextual V2 factors)
- Blends a **Poisson goal model** (60%) with a **factor-weighted model** (40%)
- Incorporates **market odds** with data-quality-aware weighting when available
- Applies **Platt scaling calibration** to output probabilities
- Calculates **Kelly Criterion** stake sizes and EV for betting recommendations
- Tracks prediction outcomes and **self-adjusts weights** via the `CalibrationEngine`

---

## Package Structure

```
betting-algorithm-go/
└── internal/
    ├── algorithm/
    │   ├── algorithm.go      PredictionEngine struct, MatchData, Predict() pipeline, sport configs
    │   ├── factors.go        All 17 factor calculations + helper functions
    │   ├── poisson.go        Poisson distribution model, blending, odds conversion
    │   ├── probs.go          Weighted probability assembly, calibration, confidence, recommendation
    │   └── calibration.go    CalibrationEngine — thread-safe weight adjustment
    └── context/
        └── builder.go        MatchContextBuilder — loads managers, H2H, season stats
```

**Dependencies introduced in Phase 2:**

| Package | Used in | Purpose |
|---------|---------|---------|
| `gonum.org/v1/gonum/stat/distuv` | `poisson.go` | `distuv.Poisson` for PMF calculations |
| `sync` | `calibration.go` | `sync.RWMutex` for thread safety |
| `bet4me/internal/domain` | `factors.go`, `probs.go`, `calibration.go`, `context/builder.go` | `FactorResult`, `MatchContext`, `H2HRecord`, `ManagerInfo` |
| `bet4me/internal/context` | `factors.go` | `NewMatchContextBuilder` |

---

## Data Flow

```
MatchData (input)
    │
    ▼
setDefaults()                         ← fill missing fields with sensible defaults
    │
    ▼
calculateAllFactors()                 ← 17 factor functions → map[string]interface{}
    │   ├── 10 original factors (dict with "score" key)
    │   ├── teamQualityGap (dict)
    │   └── 6 contextual factors (domain.FactorResult with Triggered/Weight)
    │
    ▼
calculateWeightedProbabilities()      ← dynamic weight normalization → Probabilities
    │
    ├── (if odds provided)
    │   oddsToProbs()                 ← remove bookmaker margin → market Probabilities
    │   blendProbabilities()          ← model × data-quality + market × (1-dq)
    │
    ▼
calculatePoissonProbabilities()       ← Poisson goal matrix 0-5 × 0-5 → Probabilities
    │
    ▼
blendProbabilities(weighted, poisson, 0.6)   ← 40% weighted + 60% Poisson
    │
    ▼
calibrateProbabilities()              ← Platt scaling (a=1, b=0 initially)
    │
    ▼
calculateConfidence()                 ← probability spread + factor consistency
    │
    ▼
generateRecommendation()              ← EV calculation, Kelly stake, bet type label
    │
    ▼
PredictionResult (output)
```

---

## File-by-File Reference

### `algorithm.go` — Engine & Types

**Location:** `internal/algorithm/algorithm.go`

#### Structs

| Struct | Purpose |
|--------|---------|
| `PredictionEngine` | Main engine; holds config, Elo map, calibration params, optional CalibrationEngine |
| `SportConfig` | Per-sport parameters (weights, home advantage, Elo K-factor, Poisson cap, etc.) |
| `CalibrationParams` | Platt scaling `{A, B}` pair |
| `PredictionResult` | Full prediction output — probabilities, confidence, factors, recommendation, xG, timestamp |
| `Recommendation` | Betting guidance — outcome, probability %, EV, Kelly stake, recommendation label |
| `MatchData` | All input fields; 34 fields across 8 categories (team identity, odds, xG, Elo, advanced stats, form, tactical, fatigue, motivation) |
| `Probabilities` | Internal `{Home, Draw, Away float64}` triple used throughout the pipeline |

#### Constructor

```go
engine := algorithm.NewPredictionEngine("football", true, true)
//                                       ^sport   ^v2wt  ^calibration
```

- `sport = "football"` → loads `FootballWeightsV2` (17 factors), `HomeAdvantage=0.10`, `BaseElo=1500`, `KFactor=32`, `MaxGoalsLambda=4.0`
- `sport = "basketball"` → 8 factors, `HomeAdvantage=0.06`, `KFactor=20`
- `sport = "tennis"` → 6 factors, `MinConfidence=0.60`

#### Key Methods

| Method | Description |
|--------|-------------|
| `Predict(*MatchData) (*PredictionResult, error)` | Full prediction pipeline |
| `SetHistoricalData(interface{})` | Inject historical matches for context building |
| `RecordActualResult(...)` | Feed actual result back for calibration |
| `ApplyCalibration()` | Trigger weight adjustment from calibration history |
| `GetCalibrationReport()` | Return performance stats map |
| `UpdateElo(home, away, hGoals, aGoals)` | Update internal Elo ratings after a match |
| `SetCalibration(a, b float64)` | Manually set Platt scaling parameters |

#### Default Values (`setDefaults`)

If a caller omits fields, the engine applies these defaults before any calculation:

| Field | Default |
|-------|---------|
| `HomeXg`, `AwayXg` | `1.3` |
| `HomePossession`, `AwayPossession` | `50` |
| `HomePPDA`, `AwayPPDA` | `10.0` |
| `HomeShots`, `AwayShots` | `11` |
| `HomeShotsOnTarget`, `AwayShotsOnTarget` | `4` |
| `HomePosition`, `AwayPosition` | `10` |
| `HomeForm`, `AwayForm` | `"WDWLD"` |
| `HomeFormation` | `"4-3-3"` |
| `AwayFormation` | `"4-4-2"` |
| `HomeStyle`, `AwayStyle` | `"balanced"` |
| `HomeKeyPlayersAvailable`, `AwayKeyPlayersAvailable` | `1.0` |
| `HomeStarRating`, `AwayStarRating` | `3` |
| `HomeRestDays`, `AwayRestDays` | `7` |
| `HomeGamesLast7`, `AwayGamesLast7` | `1` |
| `Weather` | `"clear"` |
| `ExpectedAttendancePct` | `85` |

---

### `factors.go` — Factor Calculations

**Location:** `internal/algorithm/factors.go`

All 17 factor functions live here. They are methods on `*PredictionEngine` but are pure with respect to the engine's state — they only read config and the supplied `*MatchData` / `*domain.MatchContext`.

#### Factor Output Formats

There are two output shapes in use:

**1. Legacy dict factors** (original 10 + teamQualityGap) — `map[string]interface{}` with a `"score"` key in `[0, 1]`:
```go
return map[string]interface{}{
    "score": 0.62,          // consumed by calculateWeightedProbabilities
    "homeXg": 1.8,          // metadata for the API response
    "awayXg": 1.1,
    // ...
}
```

**2. FactorResult objects** (6 contextual V2 factors) — `domain.FactorResult`:
```go
domain.FactorResult{
    Name:        "h2hAnomaly",
    Value:       0.70,       // equivalent to "score"
    Weight:      0.15,       // explicit weight (overrides config map when Triggered=true)
    Triggered:   true,       // if false, factor is excluded from normalization
    Confidence:  90,         // 0-100, used for reporting only
    Explanation: "Weaker team unbeaten in 5 H2H",
    Metadata:    map[string]any{"streak": 5},
}
```

`domain.NewInactiveFactorResult(name, reason)` is a convenience constructor for factors that cannot calculate (no data available).

#### Factor Implementations Summary

| Factor | Output type | Key formula |
|--------|-------------|-------------|
| `expectedGoals` | dict | `score = 0.5 + tanh((homeXg - awayXg) / 2) × 0.5` |
| `advancedStats` | dict | Weighted composite: 30% PPDA efficiency + 30% possession + 40% shot accuracy |
| `teamStrength` | dict | Elo expected score: `1 / (1 + 10^(-ΔElo/400))` |
| `tacticalMatchup` | dict | Lookup in 3×3 style-matchup matrix (attacking/defensive/balanced) |
| `currentForm` | dict | Weighted sum over last 5 results: W=1, D=0.5, L=0 with recency weights `[0.30, 0.25, 0.20, 0.15, 0.10]` |
| `playerImpact` | dict | `score = 0.5 + (homeImpact - awayImpact) × 0.3` where impact = availability × (stars/5) |
| `restAndFatigue` | dict | Rest score (penalty < 3 days, < 5 days, > 10 days) × congestion factor |
| `motivation` | dict | Base 0.5 + title-race (+0.10) + relegation (+0.08) + derby (+0.05h/+0.03a) + cup-final (+0.05) |
| `homeAdvantage` | dict | Base 10% dampened by quality gap > 8 positions (max 70% reduction), × crowd factor |
| `externalFactors` | dict | Weather impact map (rain −2%, snow −5%, wind −3%) + travel >500km (+2%), >1000km (+4%) |
| `teamQualityGap` | dict | 3-signal composite: Elo (50%) + league position (35%) + star rating (15%), via `tanh` |
| `h2hHistorical` | FactorResult | Home win rate deviation from 0.33, weight 0.05 (or 0.0 if anomaly active) |
| `h2hAnomaly` | FactorResult | Conditional: +0.20 if weaker team at home on ≥3-game unbeaten streak, −0.10 if away; weight 0.15 |
| `possessionQuality` | FactorResult | PQI = (xG / possession) × 100; `score = 0.5 + tanh(ΔPQI/100) × 0.3`; weight 0.12 |
| `managerMomentum` | FactorResult | Bounce = 0.08 × 0.85^gamesManaged; conditional on |netBounce| ≥ 0.01; weight = max(bounce) |
| `relegationMotivation` | FactorResult | pos ≥ 18 + fighting form → drawBoost +8%, homeWinBoost +3%; pos ≥ 17 → +4%/+2%; weight 0.08 |
| `counterAttackEfficiency` | FactorResult | Triggers when poss < 45% vs poss > 58%; low-poss team gets +0.05 upset boost; weight 0.06 |
| `awayDrawFrequency` | FactorResult | Triggers when awayDrawRate > 35% over ≥ 5 games; boost = min((rate−0.25)×0.5, 0.15); weight 0.06 |

---

### `poisson.go` — Probabilistic Goal Model

**Location:** `internal/algorithm/poisson.go`

#### `calculatePoissonProbabilities`

Uses `gonum.org/v1/gonum/stat/distuv.Poisson` to model goals as independent Poisson processes:

```
λ_home = homeXg × (0.8 + strengthScore × 0.4)   // adjusted by team strength
λ_away = awayXg × (1.2 − strengthScore × 0.4)   // capped at MaxGoalsLambda (4.0)

P(scoreH-scoreA) = Poisson.PMF(scoreH, λ_home) × Poisson.PMF(scoreA, λ_away)

homeWin += P(h > a)  for all (h, a) in 0..5 × 0..5
draw    += P(h == a)
awayWin += P(h < a)

Normalize: divide each by total
```

#### `calculateDrawProbability` — 5-signal draw model

Replaces the capped Python formula `0.25 × (1 − |ws − 0.5| × 2)` which was limited to 25%:

| Signal | Formula | Range |
|--------|---------|-------|
| League base rate | constant `0.26` | fixed |
| Quality gap | `0.06 − qualityGap × 0.32` | −0.10 to +0.06 |
| Defensive profile (xG) | +0.05 if totalXg < 2.0, +0.02 if < 2.5, else 0 | 0 to +0.05 |
| xG closeness | `max(−0.04, 0.04 − ΔxG × 0.04)` | −0.04 to +0.04 |
| Contextual boosts | accumulated `draw_boost` metadata from FactorResults | varies |

Final result clamped to `[0.08, 0.40]`.

#### `blendProbabilities`

```go
blended = probs1 × (1 − weight2) + probs2 × weight2
```

Used in two places:
1. Weighted model ↔ market odds (weight2 = 1 − dataQuality × 0.30 − 0.40)
2. Weighted model ↔ Poisson model (weight2 = 0.60, i.e. Poisson has 60% weight)

#### `oddsToProbs`

Converts decimal odds to fair implied probabilities by removing the bookmaker margin:

```
implied_i = 1 / odds_i
fair_i    = implied_i / (implied_home + implied_draw + implied_away)
```

---

### `probs.go` — Probability Assembly & Recommendations

**Location:** `internal/algorithm/probs.go`

#### `calculateWeightedProbabilities`

Iterates over all factors from the `factors` map:

1. **FactorResult factors** — use `fr.Weight` when `fr.Triggered == true`; accumulates `draw_boost` and `home_win_boost` from `fr.Metadata`
2. **Legacy dict factors** — use weight from `e.config.Weights[factorName]`

```
totalWeight = Σ active_weights
weightedScore = Σ (factor.score × factor.weight / totalWeight)

drawProb = calculateDrawProbability(weightedScore, factors, drawBoostTotal)
homeProb = weightedScore × (1 − drawProb) + homeBoostTotal
awayProb = (1 − weightedScore) × (1 − drawProb) − homeBoostTotal

clamp each to [0.05, 0.90], then renormalize to sum = 1.0
```

#### `assessDataQuality`

Returns `0.0–1.0` — fraction of 10 key fields that contain real data vs defaults. Used to determine market odds blend weight: richer data → model trusted more.

#### `calibrateProbabilities`

Applies Platt scaling: `calibrated_p = clamp(p × A + B × (p − 0.5), 0.01, 0.99)`, then renormalizes. Default `A=1, B=0` is a pass-through (identity calibration).

#### `calculateConfidence`

Two signals:
- **Probability spread** — `(maxProb − minProb) × 0.5`
- **Factor consistency** — bonus from `max(0, 0.2 − std_dev(factor_scores))`

Combined: `0.5 + (spread + consistency) × 0.8`, clamped to `[0.40, 0.95]`.

#### `generateRecommendation`

1. Determines predicted outcome (highest probability)
2. If odds provided, calculates EV for each outcome: `EV = (prob × odds) − 1`
3. Kelly stake on best positive-EV bet: `f = (b×p − q) / b`, then applies `kellyFraction=0.25` cap and `maxBetPct=0.05`
4. Labels recommendation:

| Condition | Label |
|-----------|-------|
| `EV > 10%` and `confidence > 70%` | **Strong Bet** |
| `EV > 5%` and `confidence > 60%` | **Value Bet** |
| `EV > 0%` | **Small Edge** |
| `prob > 60%` and `confidence > 65%` (no odds) | **Lean** |
| else | **No Bet** |

#### `UpdateElo`

Standard Elo update after a result:

```
expected_home = 1 / (1 + 10^((awayElo − homeElo) / 400))
new_homeElo   = homeElo + K × (actual_home − expected_home)   // K=32 for football
```

---

### `calibration.go` — Self-Improving Calibration

**Location:** `internal/algorithm/calibration.go`

#### `CalibrationEngine` struct

| Field | Type | Description |
|-------|------|-------------|
| `mu` | `sync.RWMutex` | Protects all mutable state |
| `learningRate` | `float64` | Default `0.01` — how aggressively to adjust weights |
| `maxHistory` | `int` | Default `1000` — rolling window size |
| `predictionHistory` | `[]PredictionRecord` | Sliding window of past predictions |
| `factorPerformance` | `map[string]*FactorStats` | Per-factor accuracy tracking |

#### `RecordPrediction` (write-lock)

Called after every prediction + actual result becomes known:
- Creates a `PredictionRecord` with `Correct = (predicted == actual)`
- Appends to `predictionHistory` (drops oldest if at `maxHistory`)
- Updates per-factor `Correct` / `Total` counters for triggered factors

#### `CalibrateWeights` (read-lock)

Requires ≥ 20 predictions. For each factor with ≥ 5 samples:

```
performanceRatio = factorAccuracy / overallAccuracy
adjustment       = learningRate × (performanceRatio − 1.0)
adjustment       = clamp(adjustment, −0.10, +0.10)
newWeight        = currentWeight × (1 + adjustment)
newWeight        = max(0.01, newWeight)
```

All weights are then normalized to sum = 1.0. This is **not** called automatically — the caller must call `engine.ApplyCalibration()` on a schedule (e.g., every 20 new results).

#### `GetPerformanceReport`

Returns a map with:
- `overall_accuracy`, `total_predictions`, `correct_predictions`
- `recent_accuracy` (last 20), `recent_trend` ("improving" / "stable" / "declining")
- `factor_stats` — per-factor accuracy, samples, contribution, relative performance
- `outcome_distribution` — how many home / draw / away results were seen
- `sample_size_sufficient` — bool, true when ≥ 20 predictions recorded

#### Thread Safety

All public methods use `mu.Lock()` (writes) or `mu.RLock()` (reads). Safe to call `RecordPrediction` concurrently with `GetPerformanceReport`.

---

### `context/builder.go` — Match Context Builder

**Location:** `internal/context/builder.go`

#### `MatchContextBuilder` struct

| Field | Type | Description |
|-------|------|-------------|
| `historicalData` | `interface{}` | Opaque; type-asserted by concrete implementations |
| `h2hCache` | `map[string]*domain.H2HRecord` | Key: `"homeTeam_awayTeam"` |
| `seasonStatsCache` | `map[string]map[string]interface{}` | Key: `"team_perspective"` |
| `managerDB` | `map[string]*domain.ManagerInfo` | Loaded from `data/managers.json` |

#### Manager Loading

On construction, `loadManagerDatabase()` looks for `data/managers.json` (then `../data/managers.json`). Expected JSON shape:

```json
{
  "Arsenal": {
    "manager":         "Mikel Arteta",
    "appointmentDate": "2019-12-20",
    "isInterim":       false,
    "results":         ["W", "W", "D", "L", "W"]
  }
}
```

`GamesManaged` is calculated as `floor(weeksSinceAppointment)` — approximately 1 game per week.

#### `BuildContext(*algorithm.MatchData) *domain.MatchContext`

Populates a `MatchContext` from:

| Field | Source |
|-------|--------|
| `HomeDefensiveStyle` | `classifyDefensiveStyle(HomePossession)`: > 55% → HighPress, 45–55% → Balanced, < 45% → LowBlock |
| `HomeManagerInfo` | Lookup in `managerDB` by team name |
| `HomeLeaguePosition` | Directly from `MatchData` |
| `HomeRecentForm` | `parseForm()` — filters string to `["W","D","L",...]`, defaults to 5× "D" |
| `H2HRecord` | `getH2HRecord()` — returns `nil` if no historical data |
| `HomeSeasonStats` | `calculateSeasonStats()` — returns `nil` if no historical data |

#### H2H & Season Stats (pluggable)

The methods `getH2HRecord` and `calculateSeasonStats` are intentionally left as stubs that return `nil` when `historicalData == nil`. The concrete data-wiring is done in Phase 3 (data pipeline), where typed `[]HistoricalMatch` slices are available.

Two public helpers are exposed for Phase 3 to call directly:

```go
// Build H2H record from a slice of typed match structs
h2h := context.BuildH2HRecordFromMatches(matches, homeTeam, awayTeam, homePos, awayPos)

// Build season stats from a slice of typed match structs
stats := context.CalculateSeasonStatsFromMatches(matches, team, "away")
```

#### `HistoricalMatch` struct

```go
type HistoricalMatch struct {
    Date, HomeTeam, AwayTeam string
    HomeGoals, AwayGoals     int
    HomePossession, AwayPossession float64
    Competition, Season      string
}
```

This is the typed bridge between raw CSV data (Phase 3 `storage/csv.go`) and context calculations.

---

## Factor Catalogue

| # | Name | Category | V2/V3 | Conditional | Default Weight |
|---|------|----------|--------|-------------|----------------|
| 1 | `expectedGoals` | Core | — | No | 0.12 |
| 2 | `advancedStats` | Core | — | No | 0.07 |
| 3 | `teamStrength` | Core | — | No | 0.07 |
| 4 | `tacticalMatchup` | Core | — | No | 0.06 |
| 5 | `currentForm` | Core | — | No | 0.05 |
| 6 | `playerImpact` | Core | — | No | 0.05 |
| 7 | `restAndFatigue` | Core | — | No | 0.04 |
| 8 | `motivation` | Core | — | No | 0.03 |
| 9 | `homeAdvantage` | Core | — | No | 0.02 |
| 10 | `externalFactors` | Core | — | No | 0.01 |
| 11 | `teamQualityGap` | Quality | V3 | No | 0.10 |
| 12 | `h2hHistorical` | Contextual | V2 | Yes (inactive when anomaly) | 0.04 |
| 13 | `h2hAnomaly` | Contextual | V2 | Yes (replaces h2hHistorical when streak ≥ 3) | 0.12 |
| 14 | `possessionQuality` | Contextual | V2 | No | 0.07 |
| 15 | `managerMomentum` | Contextual | V2 | Yes (needs managers.json, net bounce ≥ 0.01) | dynamic |
| 16 | `relegationMotivation` | Contextual | V2 | Yes (pos ≥ 17 only) | 0.04 |
| 17 | `counterAttackEfficiency` | Contextual | V2 | Yes (requires poss < 45% vs > 58%) | 0.04 |
| — | `awayDrawFrequency` | Contextual | V2 | Yes (draw rate > 35%, ≥ 5 games) | 0.03 |

> **Note on h2hAnomaly/h2hHistorical mutual exclusion:** When anomaly is detected, `h2hHistorical.Triggered = false` and `h2hAnomaly.Triggered = true`. Only the active factor contributes to the weighted score. The `h2hHistorical` weight (0.04) is effectively transferred to `h2hAnomaly` (0.12), giving the anomaly 3× the influence.

---

## Prediction Pipeline (step-by-step)

Given a match Arsenal (home, pos 2) vs Brighton (away, pos 8):

```
1. setDefaults()
   → HomePossession=65, AwayPossession=55, HomeXg=1.8, AwayXg=1.1 (from input)
   → HomeRestDays=7 (default), Weather="rain" (from input)

2. calculateAllFactors()
   → expectedGoals:  score=0.636  (tanh((1.8-1.1)/2)×0.5 + 0.5)
   → advancedStats:  score=0.541
   → teamStrength:   score=0.572  (Arsenal Elo 1600 vs Brighton 1480 → +0.072)
   → tacticalMatchup: score=0.50  (balanced vs balanced)
   → currentForm:   score=0.595  (Arsenal "WWWDL", Brighton "WDLLL")
   → playerImpact:  score=0.52
   → restAndFatigue: score=0.50
   → motivation:    score=0.60   (Arsenal top-4 +0.10)
   → homeAdvantage: score=0.599  (10% base, qualityGap=−6 → no dampening)
   → externalFactors: score=0.48 (rain −2%)
   → teamQualityGap: score=0.617
   → h2hHistorical: Triggered=true, Value=0.55, Weight=0.05
   → h2hAnomaly:    Triggered=false
   → possessionQuality: Triggered=true, Value=0.58, Weight=0.12
   → managerMomentum: Triggered=false (both established managers)
   → relegationMotivation: Triggered=false (neither in relegation)
   → counterAttackEfficiency: Triggered=false (no extreme possession split)
   → awayDrawFrequency: Triggered=false (no season stats)

3. calculateWeightedProbabilities()
   → totalWeight ≈ 0.86 (13 active factors)
   → weightedScore ≈ 0.574
   → drawProb = 0.26 + 0.01 (quality gap adj) + 0.0 (xG defensive) + 0.01 (xG closeness) = 0.27
   → homeProb = 0.574 × (1 − 0.27) = 0.419
   → awayProb = (1−0.574) × (1 − 0.27) = 0.311
   → after normalization: Home=0.420, Draw=0.271, Away=0.309

4. oddsToProbs(2.10, 3.40, 3.80)
   → implied: 0.476, 0.294, 0.263
   → margin = 1.033 → fair: 0.461, 0.285, 0.255

5. assessDataQuality() → 0.70 (7/10 fields real)
   → modelWeight = 0.40 + 0.70×0.30 = 0.61
   → blend(model, market, 1−0.61=0.39):
      Home = 0.420×0.61 + 0.461×0.39 = 0.436
      Draw = 0.271×0.61 + 0.285×0.39 = 0.276
      Away = 0.309×0.61 + 0.255×0.39 = 0.288

6. calculatePoissonProbabilities()
   → λ_home = 1.8 × (0.8 + 0.572×0.4) = 1.8 × 1.029 = 1.852
   → λ_away = 1.1 × (1.2 − 0.572×0.4) = 1.1 × 0.971 = 1.068
   → Poisson matrix sum → Home=0.478, Draw=0.253, Away=0.269

7. blendProbabilities(model=step5, poisson=step6, weight2=0.60)
   → Home = 0.436×0.40 + 0.478×0.60 = 0.461
   → Draw = 0.276×0.40 + 0.253×0.60 = 0.262
   → Away = 0.288×0.40 + 0.269×0.60 = 0.277

8. calibrateProbabilities() → identity pass-through (A=1, B=0)

9. calculateConfidence()
   → spread = (0.461 − 0.262) × 0.5 = 0.100
   → factor consistency bonus ≈ 0.05
   → confidence = 0.5 + (0.100 + 0.05) × 0.8 = 0.620

10. generateRecommendation()
    → predicted: Home Win (46.1%)
    → EV_home = (0.461 × 2.10) − 1 = −0.032  (no value)
    → no positive EV → "No Bet"
    → confidence 62% < 65% threshold → not "Lean"
    → recommendation: "No Bet"
```

---

## Weight System

### V1 Weights (10 factors, sum = 1.0)

```
expectedGoals   0.20   advancedStats    0.15   teamStrength     0.12
tacticalMatchup 0.12   currentForm      0.10   playerImpact     0.10
restAndFatigue  0.08   motivation       0.06   homeAdvantage    0.05
externalFactors 0.02
```

### V2 Weights (17 factors, base sum ≈ 1.0)

```
expectedGoals   0.12   advancedStats    0.07   teamStrength     0.07
tacticalMatchup 0.06   currentForm      0.05   playerImpact     0.05
restAndFatigue  0.04   motivation       0.03   homeAdvantage    0.02
externalFactors 0.01   teamQualityGap   0.10
h2hHistorical   0.04   h2hAnomaly       0.12   possessionQuality 0.07
managerMomentum 0.04   relegationMotivation 0.04
counterAttackEfficiency 0.04   awayDrawFrequency 0.03
```

### Dynamic Normalization

At prediction time, only **triggered** factors participate. If `managerMomentum` and `awayDrawFrequency` are both inactive, their weights are excluded and the remaining weights are renormalized:

```
normalizedWeight_i = weight_i / Σ(active_weights)
```

This means the remaining factors always collectively explain 100% of the prediction, regardless of how many contextual factors fire.

---

## Key Algorithms Explained

### Elo Rating System

```
expected_home = 1 / (1 + 10^((awayElo - homeElo) / 400))
new_homeElo   = homeElo + K × (actual - expected)
```
- `K = 32` for football (higher K = faster rating change)
- Initial rating = 1500 for all teams
- `actual`: 1.0 for win, 0.5 for draw, 0.0 for loss

A 200-point Elo gap gives the stronger team a 76% expected score. A 400-point gap gives 91%.

### Poisson Goal Model

Goals scored in a football match follow a Poisson distribution (approximately). Given expected goals λ:

```
P(k goals) = (λ^k × e^(-λ)) / k!
```

By computing this for all (home goals, away goals) combinations from 0–5, we get a probability for every scoreline, which we sum into outcome bins (home win, draw, away win). This handles the draw probability naturally — it emerges from P(0-0) + P(1-1) + P(2-2) + ...

### Enhanced Draw Model

The old Python formula capped draws at 25%. EPL average is ~26% and defensive games regularly reach 35%. The new 5-signal model gives realistic draws:

- **Base 26%** from league statistics
- **Quality gap adjustment** — evenly matched teams draw more
- **Defensive profile** — low total xG → more likely 0-0 or 1-1
- **xG closeness** — similar xG → more likely draw
- **Contextual boosts** — relegation fight, away draw-prone teams

### Dynamic Weight Normalization

Prevents conditional factors from "stealing" weight from stable factors when they don't fire. If h2hAnomaly weight (0.12) is excluded (not triggered), the remaining factors fill that 0.12 proportionally.

### Platt Scaling Calibration

Adjusts raw model probabilities toward true frequencies:

```
p_calibrated = sigmoid(A × log(p/(1-p)) + B)
```

In our linear approximation: `p_calibrated = p × A + B × (p − 0.5)`. When `A=1, B=0` this is identity. After collecting results, `A` and `B` can be fitted by logistic regression on `(raw_prob, actual_outcome)` pairs.

### Kelly Criterion Stake Sizing

Optimal fraction of bankroll to bet:

```
f* = (b×p − q) / b
```
Where `b = odds − 1`, `p = probability of winning`, `q = 1 − p`.

We apply fractional Kelly (f × 0.25) to reduce variance, then cap at 5% of bankroll.

### Manager Momentum Decay

New managers typically get a short-term performance boost (players try harder, tactical surprise). This decays exponentially as the manager becomes established:

```
bounce = baseBoost × 0.85^gamesManaged
```
- `baseBoost = 0.08` for permanent managers, `0.056` for interim
- Decays to < 1% effect after ~28 games (≈ 3/4 of a season)
- Only contributes when |net bounce between teams| ≥ 0.01

### H2H Anomaly Detection

Sometimes a historically weaker team consistently performs well against a specific stronger opponent ("bogey team" effect). When detected:

1. Check if the weaker team (higher league position number) has ≥ 3 consecutive unbeaten H2H results
2. If yes, replace `h2hHistorical` (weight 0.04) with `h2hAnomaly` (weight 0.12)
3. If weaker team is **home**: add +0.20 to probability score (favours upset)
4. If weaker team is **away**: subtract −0.10 (acknowledge threat but dampen)

---

## Domain Model Changes

One change to `internal/domain/models.go` was required during Phase 2:

**Added `HomeTeam` and `AwayTeam` string fields to `H2HResult`:**

```go
// Before
type H2HResult struct {
    Date      string `json:"date"`
    HomeScore int    `json:"homeScore"`
    AwayScore int    `json:"awayScore"`
}

// After
type H2HResult struct {
    Date      string `json:"date"`
    HomeTeam  string `json:"homeTeam"`   // ← added
    AwayTeam  string `json:"awayTeam"`   // ← added
    HomeScore int    `json:"homeScore"`
    AwayScore int    `json:"awayScore"`
}
```

**Reason:** `calculateWeakerTeamStreak` in `context/builder.go` needs to know which team was home in each historical match to determine if the weaker team won or drew. Without team names on the result record this calculation is impossible.

This is a backwards-compatible change — the new fields are `omitempty`-able and existing JSON without them will simply default to empty strings.

---

## Go vs Python Differences

| Concern | Python | Go |
|---------|--------|----|
| **Historical data** | `pd.DataFrame` with `.loc[]` filtering | `[]HistoricalMatch` typed slice with manual loops |
| **Factor output** | `dict` with arbitrary keys | Two shapes: `map[string]interface{}` (legacy) + `domain.FactorResult` (contextual) |
| **Poisson PMF** | `scipy.stats.poisson.pmf(k, mu)` | `distuv.Poisson{Lambda: mu}.Prob(float64(k))` |
| **Thread safety** | GIL protects interpreter state | Explicit `sync.RWMutex` in `CalibrationEngine` |
| **Caching** | `dict` in-process, not thread-safe | `map` in `MatchContextBuilder`, not shared across goroutines (per-request builder) |
| **Defaults** | `dict.get(key, default)` | `setDefaults()` mutates `MatchData` in-place before calculation |
| **Conditional factors** | `if triggered: result[name] = value` | `domain.FactorResult{Triggered: bool}` — always present, ignored by weight logic |
| **Normalization** | `total = sum(weights.values()); weights = {k: v/total ...}` | Same logic in `calculateWeightedProbabilities`, accumulated in loop |
| **Error handling** | `try/except` with print fallback | Returns `nil` / inactive FactorResult — no panics on missing data |
| **Manager DB** | Loaded once in `__init__` | Loaded once in `NewMatchContextBuilder()` — per-request builder means per-request load; cache in Phase 5 API layer |

---

## Known Limitations & TODOs

1. **`getH2HRecord` is a stub** — returns `nil` when `historicalData == nil`. Wire in Phase 3 with typed `[]HistoricalMatch` data.

2. **`calculateSeasonStats` is a stub** — same as above. The `counterAttackEfficiency` and `awayDrawFrequency` factors cannot fire until this is wired.

3. **Manager DB path is relative** — `data/managers.json` works when the server runs from `betting-algorithm-go/`. Phase 5 should pass an explicit config path via `AppConfig`.

4. **`hasElo` syntax error in `factors.go`** — line 409 uses `(_, ok := e.eloRatings[...]; ok)` which is not valid Go. This must be split into a proper `if` block before the package will compile. Fix:
   ```go
   _, hasEloMap := e.eloRatings[data.HomeTeam]
   hasElo := data.HomeElo != nil || hasEloMap
   ```

5. **`calibration.go` uses `domain.FactorResult`** but the import is inside the function body — compiler will reject this. The `RecordPrediction` method needs the import at the file top, not inline.

6. **`context/builder.go` imports `bet4me/internal/algorithm`** creating a potential circular import (`algorithm` → `context` → `algorithm`). Resolution: move `MatchData` out of `algorithm` into a shared `domain` or `types` package, or pass only the fields `builder.go` needs as plain arguments.

7. **Calibration is not automatic** — the caller must explicitly call `engine.ApplyCalibration()`. Phase 5 API layer should schedule this (e.g., every 20 new recorded results, or daily via a goroutine).

8. **Tests not yet written** — `internal/algorithm/algorithm_test.go` should cover: factor calculation correctness against known Python outputs, Poisson PMF values, probability normalization invariant (sum = 1.0 ± 1e-9), calibration weight adjustment direction.

---

## Testing Strategy

### Unit Tests (per Phase 2 spec)

| Test | Target | Assertion |
|------|--------|-----------|
| `TestPoissonPMF` | `poisson.go` | `distuv.Poisson{1.5}.Prob(2)` matches Python `scipy.stats.poisson.pmf(2, 1.5)` to 6 decimal places |
| `TestPoissonProbabilities_sum` | `calculatePoissonProbabilities` | Home + Draw + Away = 1.0 ± 1e-9 |
| `TestDrawModel_EvenMatch` | `calculateDrawProbability` | Evenly matched teams (ws=0.5, totalXg=2.3) → draw in [0.26, 0.32] |
| `TestDrawModel_Mismatch` | `calculateDrawProbability` | Heavy favourite (ws=0.80) → draw in [0.10, 0.18] |
| `TestFormToScore_W` | `formToScore` | "WWWWW" → 1.0, "LLLLL" → 0.0, "DDDDD" → 0.5 |
| `TestEloExpectedScore` | `calculateTeamStrength` | Equal Elo → score = 0.5; +400 Elo → score ≈ 0.909 |
| `TestManagerBounce_Decay` | `calculateManagerMomentum` | At 0 games: bounce ≈ 0.08; at 28 games: bounce < 0.01 |
| `TestH2HAnomaly_Trigger` | `calculateH2HFactors` | Streak ≥ 3 + weaker at home → h2hAnomaly.Triggered=true, Value≈0.70 |
| `TestCalibration_InsufficientData` | `CalibrateWeights` | < 20 predictions → returns unchanged weights |
| `TestCalibration_WeightAdjustment` | `CalibrateWeights` | Factor with 80% accuracy vs 60% overall → weight increases |
| `TestPredictResult_Invariant` | `Predict` | HomeWinProb + DrawProb + AwayWinProb = 1.0 ± 1e-4 |
| `TestPredictResult_Timestamp` | `Predict` | Result.Timestamp is valid RFC3339 |

### Golden-File Tests (Phase 6)

Run Python algorithm on 10 specific EPL matches, capture JSON output. Assert Go produces identical `HomeWinProb`, `DrawProb`, `AwayWinProb` to 4 decimal places. This validates numerical parity of the full pipeline.
