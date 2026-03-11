# Go Crash Course
## A Practical Guide for Experienced Developers
### Reference Implementation: bet4me Betting Algorithm

---

**Author:** Fortune 500 Go Engineer & Technical Lecturer
**Purpose:** Interview Preparation — Practical Go fluency in one document
**Codebase:** `github.com/bet4me/betting-algorithm-go`

---

> **How to use this guide:** Read top to bottom once. Then use the chapter
> headers to jump back to concepts during review. The Appendices are your
> quick-reference cards on interview day.

---

## Table of Contents

1. Why Go? The Philosophy
2. Packages, Imports & the Module System
3. Variables, Types & Zero Values
4. Structs: Go's Answer to Classes
5. Functions & Error Handling
6. Interfaces: Implicit Contracts
7. Slices, Maps & Closures
8. Concurrency: Goroutines & Mutexes
9. Methods & Receiver Types in Depth
10. Working with the Standard Library
11. Design Patterns in Go
12. Testing in Go
- Appendix A: Go Cheat Sheet
- Appendix B: Interview Q&A

---

# Chapter 1 — Why Go? The Philosophy

## 1.1 The Design Intent

Go was created at Google in 2009 by Robert Griesemer, Rob Pike, and Ken Thompson. The problem they solved: large engineering teams writing C++/Java were drowning in complexity — slow compilation, byzantine dependency management, verbose concurrency.

Go's answer was radical simplicity:

| Concern | Go's choice |
|---------|------------|
| Compilation | Sub-second, statically linked binaries |
| Type system | Static, but inferred (`x := 5`) |
| Memory | Garbage collected, no manual malloc/free |
| Concurrency | Goroutines (cheaper than threads) + channels |
| Dependency management | Go modules (`go.mod`) |
| Formatting | One style, enforced by `gofmt` — no debates |
| Object-oriented | No inheritance, only composition + interfaces |

**The golden rule of Go:** If you're fighting the language, you're wrong.

## 1.2 Go vs Languages You Know

```
Python  → Go gives you static types + 10–100× speed
Java    → Go gives you no boilerplate + 5× faster startup + no JVM
Node.js → Go gives you true parallelism + compiled safety
Rust    → Go gives you GC + simpler syntax (less control, more safety)
```

## 1.3 The bet4me Project — Your Reference Implementation

The codebase you'll learn from is a **production-grade sports betting prediction engine**. It covers every important Go concept through real code:

```
betting-algorithm-go/
├── go.mod                          ← Module definition
└── internal/                       ← Package visibility boundary
    ├── algorithm/
    │   ├── algorithm.go            ← PredictionEngine, 17-factor pipeline
    │   ├── calibration.go          ← Self-improving weights, concurrency
    │   ├── factors.go              ← 17 modular factor calculations
    │   ├── poisson.go              ← Poisson probability model
    │   └── probs.go                ← Probability math + Kelly Criterion
    ├── context/
    │   └── builder.go              ← Match context enrichment
    ├── data/
    │   ├── collector.go            ← 7-step data pipeline, goroutines
    │   ├── fixtures.go             ← HTTP + JSON API integration
    │   └── sources.go              ← Configuration management
    ├── domain/
    │   └── models.go               ← Core data structures (structs)
    ├── jackpot/
    │   ├── analyzer.go             ← Multi-match jackpot analysis
    │   └── fetcher.go              ← Web scraping
    ├── storage/
    │   └── csv.go                  ← CSV I/O with standard library
    └── util/
        ├── kelly.go                ← Kelly Criterion math
        ├── performance.go          ← Thread-safe bet tracking
        └── teams.go                ← Team name normalization
```

---

# Chapter 2 — Packages, Imports & the Module System

## 2.1 Every File Declares Its Package

The **first non-comment line** of every Go file must be a package declaration:

```go
// From betting-algorithm-go/internal/algorithm/algorithm.go

// Package algorithm implements the multi-factor sports betting prediction engine.
//
// The engine combines 17 weighted factors with a Poisson goal model and
// Platt-scaling calibration to produce match probabilities and
// Kelly-Criterion-based betting recommendations.
package algorithm
```

```go
// From internal/domain/models.go
package domain
```

```go
// From internal/storage/csv.go
package storage
```

> **Rule:** All `.go` files in the same directory must share the same package name.

## 2.2 The Module System (`go.mod`)

A module is a collection of packages. Every Go project has exactly one `go.mod` at its root:

```go
// betting-algorithm-go/go.mod
module github.com/bet4me/betting-algorithm-go

go 1.23.6
```

This defines:
- `module github.com/bet4me/betting-algorithm-go` — the module path (also the import prefix)
- `go 1.23.6` — the minimum Go version required

**Common `go` CLI commands:**

```bash
go mod init github.com/myorg/myproject  # Create a new module
go get github.com/some/package          # Add a dependency
go mod tidy                             # Remove unused deps, add missing ones
go build ./...                          # Build everything
go test ./...                           # Test everything
go run main.go                          # Run a program directly
```

## 2.3 Importing Packages

```go
// From internal/algorithm/algorithm.go

import (
    "fmt"       // Standard library — just the package name
    "math"
    "time"

    // Your own packages — full module path
    mctx "github.com/bet4me/betting-algorithm-go/internal/context"
    "github.com/bet4me/betting-algorithm-go/internal/domain"
)
```

Key import patterns:

```go
import "fmt"                    // Normal import
import m "math"                 // Alias: use as m.Sqrt(...)
import _ "some/package"         // Blank import: run init() only, suppress unused error
import . "fmt"                  // Dot import: use Println directly (rare, avoid)
```

## 2.4 The `internal/` Package Visibility Rule

This is one of Go's most important visibility mechanisms. A package inside an `internal/` directory **can only be imported by code rooted at the parent of that `internal/` directory**.

```
betting-algorithm-go/
├── internal/         ← Only code INSIDE betting-algorithm-go/ can import this
│   ├── domain/
│   ├── algorithm/
│   └── storage/
```

External libraries **cannot** import `internal/domain`. This enforces API boundaries — the ultimate Go encapsulation.

## 2.5 Exported vs Unexported Identifiers

Go uses **capitalization** for access control — no `public`/`private` keywords:

```go
// Exported (public) — starts with uppercase
type PredictionEngine struct { ... }
func NewPredictionEngine(...) *PredictionEngine { ... }

// Unexported (private to package) — starts with lowercase
type sportConfig struct { ... }
type calibParams struct { ... }
func cloneWeights(w map[string]float64) map[string]float64 { ... }
```

> From `algorithm.go`: `PredictionEngine` is exported (users of the package can use it).
> `sportConfig` is unexported (internal implementation detail).

---

# Chapter 3 — Variables, Types & Zero Values

## 3.1 Variable Declaration

Go has multiple syntaxes. Use `:=` inside functions (short declaration), `var` at package level:

```go
// Short declaration — most common inside functions
engine := NewPredictionEngine("football", true, false)
homeElo := 1500.0
correct := 0

// var — explicit type
var learningRate float64 = 0.01
var name string          // zero value: ""
var count int            // zero value: 0
var enabled bool         // zero value: false

// Multiple assignment
homeGoals, awayGoals := 2, 1

// Blank identifier — discard a value
result, _ := someFunc()  // ignore the error (rarely good practice)
```

## 3.2 Primitive Types

```go
// Integers
var i int     = 42        // platform-width (32 or 64 bit)
var i8 int8   = 127
var i64 int64 = 9_000_000_000
var u uint    = 255       // unsigned

// Floats
var f32 float32 = 3.14
var f64 float64 = 3.14159265358979  // default for floating point literals

// String — immutable, UTF-8
var s string = "Manchester City"

// Boolean
var b bool = true

// byte = uint8, rune = int32 (Unicode code point)
var ch byte = 'A'
var r rune  = '🏆'
```

From the bet4me codebase — spot every type in use:

```go
// internal/algorithm/algorithm.go
type sportConfig struct {
    homeAdvantage  float64   // 0.10 = 10%
    baseElo        float64   // 1500.0
    kFactor        float64   // 32
    drawThreshold  float64   // 0.25
    minConfidence  float64
    maxGoalsLambda float64
    weights        map[string]float64  // map with float64 values
}
```

## 3.3 Zero Values — Go's Null Safety

Every type has a **zero value** — the value a variable holds when declared but not initialized. Go never has uninitialized memory:

| Type | Zero value |
|------|-----------|
| `int`, `float64` | `0`, `0.0` |
| `string` | `""` |
| `bool` | `false` |
| `pointer`, `slice`, `map`, `channel`, `interface` | `nil` |
| `struct` | all fields at their zero values |

```go
// From algorithm.go — zero-value check for Elo ratings
func (e *PredictionEngine) UpdateElo(homeTeam, awayTeam string, homeGoals, awayGoals int) {
    homeElo := e.eloRatings[homeTeam]
    if homeElo == 0 {               // ← zero-value check: team not yet in map
        homeElo = e.config.baseElo  // default to 1500
    }
    awayElo := e.eloRatings[awayTeam]
    if awayElo == 0 {
        awayElo = e.config.baseElo
    }
    // ...
}
```

## 3.4 Constants and `iota`

Constants are computed at compile time. `iota` is an auto-incrementing counter used inside `const` blocks — Go's idiomatic enum:

```go
// From internal/domain/ — WeightNormalizationMode
type WeightNormalizationMode int

const (
    WeightNormDynamic WeightNormalizationMode = iota  // 0
    WeightNormStatic                                   // 1
)

// From internal/domain/ — DefensiveStyle
type DefensiveStyle string

const (
    DefensiveStyleHighPress    DefensiveStyle = "high_press"
    DefensiveStyleBalanced     DefensiveStyle = "balanced"
    DefensiveStyleLowBlock     DefensiveStyle = "low_block"
    DefensiveStyleCounterAttack DefensiveStyle = "counter_attack"
)
```

```go
// Using iota for bitmask flags (common pattern)
const (
    ReadPerm  = 1 << iota  // 1 (binary: 001)
    WritePerm               // 2 (binary: 010)
    ExecPerm                // 4 (binary: 100)
)
```

## 3.5 Type Conversions

Go **never** implicitly converts numeric types. You must be explicit:

```go
shots := 11           // int
sot   := 4            // int
accuracy := float64(sot) / float64(shots)  // explicit conversion

// From factors.go:
homeAccuracy := float64(homeSOT) / math.Max(float64(homeShots), 1)
```

---

# Chapter 4 — Structs: Go's Answer to Classes

## 4.1 Struct Definition

Go has no classes. Instead it has structs — named collections of fields:

```go
// From internal/domain/models.go

// FactorResult is the standardized output for all prediction factors.
type FactorResult struct {
    Name        string         `json:"name"`        // struct tags
    Value       float64        `json:"value"`
    Weight      float64        `json:"weight"`
    Triggered   bool           `json:"triggered"`
    Confidence  int            `json:"confidence"`
    Explanation string         `json:"explanation"`
    Metadata    map[string]any `json:"metadata"`
}
```

The backtick annotations after field types are **struct tags** — metadata used by packages like `encoding/json` and `encoding/csv` for serialization. `json:"name"` means: when marshaling to JSON, use the key `"name"` instead of `"Name"`.

## 4.2 Creating Struct Instances

```go
// Named field initialization (preferred — order-independent, self-documenting)
result := domain.FactorResult{
    Name:        "h2hAnomaly",
    Value:       0.65,
    Weight:      0.08,
    Triggered:   true,
    Confidence:  75,
    Explanation: "Weaker team unbeaten in last 4 H2H matches",
    Metadata:    map[string]any{"streak": 4},
}

// Positional initialization (fragile — avoid for structs with many fields)
cfg := sportConfig{0.10, 1500, 32, 0.25, 0.55, 4.0, nil}

// Zero value struct — all fields at zero values
var empty FactorResult

// Pointer to a new struct
p := &FactorResult{Name: "xg", Value: 0.55}
```

## 4.3 Struct Tags — JSON & CSV Serialization

```go
// From internal/storage/csv.go
type MatchRecord struct {
    Date      string  `json:"date"`
    HomeTeam  string  `json:"home_team"`
    HomeGoals int     `json:"home_goals"`
    HomeXG    float64 `json:"home_xg"`
    HomeOdds  float64 `json:"home_odds"`
    HomeForm  string  `json:"home_form"`
}
```

The JSON package uses these tags automatically:

```go
import "encoding/json"

rec := MatchRecord{HomeTeam: "Arsenal", HomeGoals: 2, HomeXG: 1.8}
b, _ := json.Marshal(rec)
// Output: {"date":"","home_team":"Arsenal","home_goals":2,"home_xg":1.8,...}

// omitempty — omit field from JSON if it's the zero value
type MatchContext struct {
    HomeManagerInfo *ManagerInfo `json:"homeManagerInfo,omitempty"`
}
```

## 4.4 The Constructor Pattern

Go has no constructors. The convention is a `NewXxx()` function that returns a pointer:

```go
// From internal/storage/csv.go
type CSVStore struct {
    DataDir string
}

// Constructor — validates, initializes, returns a pointer
func NewCSVStore(dataDir string) *CSVStore {
    return &CSVStore{DataDir: dataDir}
}

// Usage
store := storage.NewCSVStore("./data")
```

```go
// From internal/algorithm/algorithm.go
func NewPredictionEngine(sport string, useV2Weights bool, enableCalibration bool) *PredictionEngine {
    e := &PredictionEngine{
        sport:      sport,
        eloRatings: make(map[string]float64),  // always initialize maps!
        calib:      calibParams{a: 1.0, b: 0.0},
    }

    e.config = e.loadSportConfig(sport)
    if useV2Weights && sport == "football" {
        e.config.weights = cloneWeights(domain.FootballWeightsV2)
    }
    if enableCalibration {
        e.calibrationEngine = NewCalibrationEngine(0.01, 1000)
    }

    return e
}
```

> **Why return a pointer?** Structs are value types in Go — assignment copies them. Returning `*PredictionEngine` means callers share the same instance (and modifications are visible). For large structs or mutable state, always return pointers.

## 4.5 Struct Embedding (Composition over Inheritance)

Go has no inheritance. Instead, embed one struct inside another to reuse fields and methods:

```go
type Animal struct {
    Name string
}
func (a Animal) Speak() string { return a.Name + " speaks" }

type Dog struct {
    Animal               // Embedded struct — promotes all Animal fields/methods
    Breed string
}

d := Dog{Animal: Animal{Name: "Rex"}, Breed: "Labrador"}
fmt.Println(d.Name)     // d.Animal.Name — promoted
fmt.Println(d.Speak())  // d.Animal.Speak() — promoted
```

---

# Chapter 5 — Functions & Error Handling

## 5.1 Function Basics

```go
// Basic function
func add(a, b int) int {
    return a + b
}

// Multiple parameters of same type — shorthand
func addTwo(a, b int) int { return a + b }

// Multiple return values — Go's killer feature
func divide(a, b float64) (float64, error) {
    if b == 0 {
        return 0, fmt.Errorf("division by zero")
    }
    return a / b, nil
}
```

## 5.2 Multiple Return Values & Error Handling

Go functions **conventionally return `(value, error)`**. This forces callers to think about errors.

```go
// From internal/storage/csv.go
func (s *CSVStore) ReadHistoricalData(filename string) ([]MatchRecord, error) {
    path := s.DataDir + "/" + filename
    f, err := os.Open(path)
    if err != nil {
        return nil, fmt.Errorf("open %s: %w", path, err)  // wrap with context
    }
    defer f.Close()   // ← we'll explain defer below

    return parseMatchCSV(f)
}
```

Calling it:
```go
records, err := store.ReadHistoricalData("premier_league.csv")
if err != nil {
    log.Fatalf("failed to load data: %v", err)
}
// Use records safely here
```

**The `if err != nil` pattern is not a bug** — it's intentional. Go trades exception handling for explicit, local error handling. There are no try/catch blocks.

## 5.3 Error Wrapping with `%w`

```go
// %w wraps the original error so callers can inspect it
return nil, fmt.Errorf("open %s: %w", path, err)

// Caller can unwrap
if errors.Is(err, os.ErrNotExist) {
    // file doesn't exist
}

var pathErr *os.PathError
if errors.As(err, &pathErr) {
    fmt.Println("path:", pathErr.Path)
}
```

## 5.4 `defer` — Guaranteed Cleanup

`defer` schedules a function call to run **when the surrounding function returns**, regardless of how it returns (normal or error). It's Go's equivalent of `finally`:

```go
// From storage/csv.go
func (s *CSVStore) ReadHistoricalData(filename string) ([]MatchRecord, error) {
    f, err := os.Open(path)
    if err != nil {
        return nil, err
    }
    defer f.Close()   // ← guaranteed to run when ReadHistoricalData returns
    // ... rest of function
}

// From csv.go WriteHistoricalData
func (s *CSVStore) WriteHistoricalData(filename string, records []MatchRecord) error {
    f, err := os.Create(path)
    if err != nil {
        return err
    }
    defer f.Close()

    w := csv.NewWriter(f)
    defer w.Flush()  // multiple defers run in LIFO order (Flush before Close)

    // ... write data
    return nil
}
```

> **Defer is LIFO** (Last In, First Out). Multiple defers unwind in reverse order of declaration.

## 5.5 Input Validation

```go
// From internal/algorithm/algorithm.go
func (e *PredictionEngine) Predict(data *domain.MatchData) (*domain.PredictionResult, error) {
    if data == nil {
        return nil, fmt.Errorf("match data is required")
    }
    if data.HomeTeam == "" || data.AwayTeam == "" {
        return nil, fmt.Errorf("homeTeam and awayTeam are required")
    }
    // ... proceed safely
}
```

## 5.6 Named Return Values

Go allows naming return values — useful for documentation and `defer`-based cleanup:

```go
// Named returns — rarely needed but useful for complex functions
func computeStats(results []string) (wins, draws, losses int) {
    for _, r := range results {
        switch r {
        case "W":
            wins++
        case "D":
            draws++
        case "L":
            losses++
        }
    }
    return  // "naked return" — returns wins, draws, losses as-is
}
```

## 5.7 Variadic Functions

```go
// Accept any number of arguments
func sum(nums ...int) int {
    total := 0
    for _, n := range nums {
        total += n
    }
    return total
}

sum(1, 2, 3)         // 6
nums := []int{1, 2, 3}
sum(nums...)          // spread a slice into variadic args
```

From `storage/csv.go` — variadic column lookup:
```go
// getCol returns the first matching column value from a row.
// Multiple names handle different CSV formats (football-data.co.uk vs custom).
func getCol(row []string, idx map[string]int, names ...string) string {
    for _, name := range names {
        if i, ok := idx[name]; ok && i < len(row) {
            return strings.TrimSpace(row[i])
        }
    }
    return ""
}

// Called with multiple possible column names:
HomeTeam: getCol(row, colIdx, "HomeTeam", "home_team"),
HomeGoals: getColInt(row, colIdx, "HomeGoals", "home_goals", "FTHG"),
HomeOdds:  getColFloat(row, colIdx, "HomeOdds", "home_odds", "B365H", "PSH"),
```

---

# Chapter 6 — Interfaces: Implicit Contracts

## 6.1 What is a Go Interface?

An interface defines a **set of method signatures**. Any type that implements those methods **automatically satisfies** the interface — no `implements` keyword needed.

```go
// Define an interface
type Stringer interface {
    String() string  // any type with a String() string method satisfies this
}

// A type satisfies an interface just by having the right methods
type ManagerInfo struct {
    Name         string
    GamesManaged int
}

func (m *ManagerInfo) String() string {
    return fmt.Sprintf("%s (%d games)", m.Name, m.GamesManaged)
}

// ManagerInfo now satisfies fmt.Stringer — automatically
var s fmt.Stringer = &ManagerInfo{Name: "Pep Guardiola", GamesManaged: 42}
fmt.Println(s) // calls String() automatically
```

## 6.2 The `error` Interface

The built-in `error` type is just an interface:

```go
// This is the entire definition of the error interface in Go's standard library:
type error interface {
    Error() string
}
```

Any type with an `Error() string` method is an `error`. That's why you can create custom errors:

```go
// Custom error type
type ValidationError struct {
    Field   string
    Message string
}

func (e *ValidationError) Error() string {
    return fmt.Sprintf("validation failed on %s: %s", e.Field, e.Message)
}

// From domain/models.go — Validate() returns the built-in error interface
func (f *FactorResult) Validate() error {
    if f.Value < -1.0 || f.Value > 1.0 {
        return fmt.Errorf("FactorResult value %.4f out of range [-1.0, 1.0]", f.Value)
    }
    if f.Confidence < 0 || f.Confidence > 100 {
        return fmt.Errorf("confidence %d out of range [0, 100]", f.Confidence)
    }
    if f.Weight < 0 {
        return fmt.Errorf("weight %.4f must be non-negative", f.Weight)
    }
    if f.Metadata == nil {
        f.Metadata = make(map[string]any)
    }
    return nil
}
```

## 6.3 The Empty Interface: `any` / `interface{}`

`interface{}` (also written `any` in Go 1.18+) accepts **any type**. It's Go's escape hatch from the type system — use sparingly.

```go
// From domain/models.go — Metadata accepts any value
type FactorResult struct {
    Metadata map[string]any `json:"metadata"`   // any = interface{}
}

// From algorithm.go — factors map stores different types
type PredictionEngine struct {
    historicalData interface{}   // could be anything
}

func (e *PredictionEngine) calculateAllFactors(
    data *domain.MatchData,
    ctx *domain.MatchContext,
) map[string]interface{} {   // returns a map of mixed types
    factors := make(map[string]interface{}, 17)
    factors["expectedGoals"] = e.calculateExpectedGoals(data)  // map[string]interface{}
    factors["h2hAnomaly"]    = e.calculateH2HFactors(...)       // domain.FactorResult
    // ...
}
```

## 6.4 Type Assertions & Type Switches

To get a concrete value back out of an interface:

```go
// Type assertion — panics if wrong type
val := someInterface.(string)

// Safe type assertion — returns (value, ok bool)
if val, ok := someInterface.(string); ok {
    fmt.Println("it's a string:", val)
}

// Type switch — check multiple types
func describe(i interface{}) {
    switch v := i.(type) {
    case int:
        fmt.Printf("int: %d\n", v)
    case string:
        fmt.Printf("string: %s\n", v)
    case bool:
        fmt.Printf("bool: %t\n", v)
    default:
        fmt.Printf("unknown: %T\n", v)
    }
}
```

From `calibration.go` — type assertion in real code:

```go
// From internal/algorithm/calibration.go
// Reads a float64 from an interface{} map safely
if m, ok := toMap(raw); ok {
    triggered, _ := m["triggered"].(bool)   // ← safe type assertion, ignore ok
    if triggered || isLegacyFactor(raw) {
        stats.Total++
        if w, ok := m["weight"].(float64); ok {  // ← safe assertion, check ok
            stats.Contribution = w
        }
    }
}
```

From `algorithm.go` — type switch equivalent:

```go
// getFloat reads a float64 from a map[string]interface{}
func getFloat(m map[string]interface{}, key string, dflt float64) float64 {
    if m == nil {
        return dflt
    }
    if v, ok := m[key]; ok {
        switch val := v.(type) {   // ← type switch
        case float64:
            return val
        case int:
            return float64(val)
        }
    }
    return dflt
}
```

## 6.5 Interface Composition

Interfaces can embed other interfaces:

```go
// io.ReadWriter from standard library — composition
type Reader interface {
    Read(p []byte) (n int, err error)
}
type Writer interface {
    Write(p []byte) (n int, err error)
}
type ReadWriter interface {
    Reader   // embed Reader
    Writer   // embed Writer
}
```

---

# Chapter 7 — Slices, Maps & Closures

## 7.1 Slices

A slice is Go's dynamic array. It's a descriptor: `(pointer, length, capacity)`.

```go
// Create
nums := []int{1, 2, 3, 4, 5}          // literal
empty := make([]string, 0, 10)         // make(type, len, cap)
var nilSlice []int                      // nil slice — length 0, capacity 0

// Append
nums = append(nums, 6)                  // always reassign
nums = append(nums, 7, 8, 9)
more := []int{10, 11}
nums = append(nums, more...)            // spread

// Sub-slice (shares underlying array!)
first3 := nums[0:3]    // [1, 2, 3]
from2  := nums[2:]     // [3, 4, 5, ...]
upto3  := nums[:3]     // [1, 2, 3]

// Length and capacity
len(nums)   // current length
cap(nums)   // allocated capacity

// Iterate
for i, v := range nums {
    fmt.Println(i, v)
}
for _, v := range nums {    // ignore index
    fmt.Println(v)
}
```

From `domain/models.go` — slices in real structs:

```go
type MatchContext struct {
    HomeRecentForm []string `json:"homeRecentForm"`  // ["W", "D", "L", ...]
    AwayRecentForm []string `json:"awayRecentForm"`

    H2HResults []H2HResult  // slice of structs
}

// RecentWins — slice sub-slicing in real code
func (c *MatchContext) RecentWins(team string, lastN int) int {
    var form []string
    if team == "home" {
        form = c.HomeRecentForm
    } else {
        form = c.AwayRecentForm
    }
    start := len(form) - lastN   // calculate start index
    if start < 0 {
        start = 0
    }
    wins := 0
    for _, r := range form[start:] {  // sub-slice from start to end
        if r == "W" {
            wins++
        }
    }
    return wins
}
```

From `algorithm/calibration.go` — rolling history window:

```go
// Maintain rolling history — if over maxHistory, drop oldest
ce.history = append(ce.history, rec)
if len(ce.history) > ce.maxHistory {
    ce.history = ce.history[1:]   // drop first element — O(n) but simple
}
```

## 7.2 Maps

A map is a hash table: `map[KeyType]ValueType`.

```go
// Create — ALWAYS use make() for maps you'll write to
eloRatings := make(map[string]float64)
weights    := make(map[string]float64, 17)  // optional hint for initial capacity

// Literal initialization
tacticalScores := map[string]float64{
    "attacking": 0.45,
    "defensive": 0.35,
    "balanced":  0.30,
}

// Read
elo := eloRatings["Arsenal"]    // zero value (0.0) if key missing

// Comma-ok pattern — check if key exists
if elo, ok := eloRatings["Arsenal"]; ok {
    fmt.Println("Arsenal Elo:", elo)
} else {
    fmt.Println("Arsenal not found")
}

// Write
eloRatings["Arsenal"] = 1580.5

// Delete
delete(eloRatings, "Arsenal")

// Iterate (order NOT guaranteed)
for team, elo := range eloRatings {
    fmt.Printf("%s: %.1f\n", team, elo)
}
```

From `algorithm.go` — real map usage:

```go
type PredictionEngine struct {
    eloRatings map[string]float64  // field: team → Elo rating
}

func (e *PredictionEngine) UpdateElo(homeTeam, awayTeam string, homeGoals, awayGoals int) {
    homeElo := e.eloRatings[homeTeam]   // zero value if not found
    if homeElo == 0 {
        homeElo = e.config.baseElo
    }
    // ...
    e.eloRatings[homeTeam] = homeElo + k*(actualHome-expectedHome)  // update
    e.eloRatings[awayTeam] = awayElo + k*(actualAway-expectedAway)
}
```

> **CRITICAL:** Never use a nil map for writing — it panics. Always `make()` before writing.
> Reading from a nil map returns zero values (safe). Writing panics.

```go
var m map[string]int    // nil map
_ = m["key"]           // OK: returns 0
m["key"] = 1           // PANIC: assignment to entry in nil map
```

## 7.3 The `cloneWeights` Pattern

```go
// From algorithm.go — deep copy of a map (maps are reference types)
func cloneWeights(w map[string]float64) map[string]float64 {
    out := make(map[string]float64, len(w))
    for k, v := range w {
        out[k] = v
    }
    return out
}

// Why? Maps are reference types. This:
a := map[string]float64{"x": 1.0}
b := a          // b and a point to the SAME underlying map
b["x"] = 99    // also changes a["x"]!

// cloneWeights() creates an independent copy
b := cloneWeights(a)  // now b is independent
```

## 7.4 Closures

A closure is a function that **captures** variables from its surrounding scope:

```go
// Simple closure
counter := func() func() int {
    n := 0
    return func() int {
        n++
        return n
    }
}()

counter()  // 1
counter()  // 2
counter()  // 3

// From data/collector.go — goroutine with closure
func (c *HistoricalDataCollector) StartCollection(
    ctx context.Context,
    seasons, leagues []string,
) *CollectionStatus {
    status := &CollectionStatus{Running: true}

    go func() {   // ← anonymous function (closure) run as goroutine
        // Captures: ctx, seasons, leagues, status, c
        err := c.runPipeline(ctx, seasons, leagues, status)
        status.finish(err)  // captures status from outer scope
    }()

    return status  // return immediately — pipeline runs in background
}
```

---

# Chapter 8 — Concurrency: Goroutines & Mutexes

## 8.1 Goroutines

A goroutine is a **lightweight thread** managed by the Go runtime. Creating one costs ~2KB of stack (vs ~1MB for OS threads). You can have millions of goroutines.

```go
// Launch a goroutine with the `go` keyword
go someFunction()

// Anonymous goroutine (most common pattern)
go func() {
    // ... runs concurrently
}()

// From data/collector.go
func (c *HistoricalDataCollector) StartCollection(
    ctx context.Context,
    seasons, leagues []string,
) *CollectionStatus {
    status := &CollectionStatus{Running: true}

    go func() {
        err := c.runPipeline(ctx, seasons, leagues, status)
        status.finish(err)
    }()

    return status   // returns immediately; goroutine runs in background
}
```

## 8.2 The Race Condition Problem

When multiple goroutines access shared data, you get a **data race**:

```go
// DANGEROUS — race condition
var count int
go func() { count++ }()   // goroutine 1
go func() { count++ }()   // goroutine 2
// final count: could be 1 or 2, not guaranteed
```

## 8.3 `sync.Mutex` — Mutual Exclusion

A Mutex ensures only one goroutine accesses a resource at a time:

```go
import "sync"

type SafeCounter struct {
    mu    sync.Mutex  // zero value is valid (unlocked)
    count int
}

func (c *SafeCounter) Increment() {
    c.mu.Lock()         // acquire the lock
    defer c.mu.Unlock() // release when function returns (defer is perfect here)
    c.count++
}

func (c *SafeCounter) Value() int {
    c.mu.Lock()
    defer c.mu.Unlock()
    return c.count
}
```

## 8.4 `sync.RWMutex` — Read-Write Mutex

When reads are frequent and writes are rare, `RWMutex` allows **multiple concurrent readers** but only one writer at a time — much more efficient than a plain Mutex:

```go
// From internal/algorithm/calibration.go
type CalibrationEngine struct {
    mu           sync.RWMutex   // read-write mutex
    learningRate float64
    maxHistory   int
    history      []PredictionRecord
    factorPerf   map[string]*factorStats
}

// WRITE operation — exclusive lock
func (ce *CalibrationEngine) RecordPrediction(
    matchID string,
    // ...
) {
    // ... compute rec ...
    ce.mu.Lock()          // exclusive write lock
    defer ce.mu.Unlock()

    ce.history = append(ce.history, rec)   // safe to write
    // update factorPerf...
}

// READ operation — shared lock (multiple goroutines can hold this simultaneously)
func (ce *CalibrationEngine) CalibrateWeights(current map[string]float64) map[string]float64 {
    ce.mu.RLock()          // shared read lock
    defer ce.mu.RUnlock()

    if len(ce.history) < 20 {   // safe to read
        return current
    }
    // ... compute adjusted weights ...
}

// Another READ operation
func (ce *CalibrationEngine) GetPerformanceReport() map[string]interface{} {
    ce.mu.RLock()
    defer ce.mu.RUnlock()

    // ... read history and factorPerf ...
}
```

**Rule of thumb:**
- `mu.Lock()` / `mu.Unlock()` → writing (exclusive)
- `mu.RLock()` / `mu.RUnlock()` → reading (shared)

## 8.5 CollectionStatus — Real Concurrent State

From `data/collector.go` — a shared status object accessed by multiple goroutines:

```go
type CollectionStatus struct {
    mu        sync.RWMutex
    Running   bool   `json:"running"`
    Progress  int    `json:"progress"`
    Step      string `json:"step"`
    Error     string `json:"error,omitempty"`
    Completed bool   `json:"completed"`
}

// Write — called from background goroutine
func (s *CollectionStatus) set(step string, progress int) {
    s.mu.Lock()
    s.Step = step
    s.Progress = progress
    s.mu.Unlock()
}

// Write — called when goroutine finishes
func (s *CollectionStatus) finish(err error) {
    s.mu.Lock()
    defer s.mu.Unlock()
    s.Running = false
    s.Completed = true
    if err != nil {
        s.Error = err.Error()
    }
}

// Read — called from API handler goroutine
func (s *CollectionStatus) Read() CollectionStatus {
    s.mu.RLock()
    defer s.mu.RUnlock()
    return CollectionStatus{   // return a VALUE copy — safe to use without lock
        Running:   s.Running,
        Progress:  s.Progress,
        Step:      s.Step,
        Error:     s.Error,
        Completed: s.Completed,
    }
}
```

## 8.6 Channels — Brief Introduction

Channels are typed conduits for goroutine communication:

```go
ch := make(chan int)         // unbuffered channel
ch := make(chan string, 10)  // buffered channel (capacity 10)

// Send (blocks if channel is full/no receiver)
go func() { ch <- 42 }()

// Receive (blocks until something is sent)
val := <-ch

// Range over channel until closed
for v := range ch {
    fmt.Println(v)
}

// Close a channel (only sender should close)
close(ch)
```

> For the interview: **mutexes** are for protecting shared state; **channels** are for communicating between goroutines. Choose the simpler option.

---

# Chapter 9 — Methods & Receiver Types in Depth

## 9.1 Value Receiver vs Pointer Receiver

```go
// Value receiver — operates on a COPY
func (f FactorResult) String() string {
    return f.Name   // changes to f don't affect original
}

// Pointer receiver — operates on the ORIGINAL
func (f *FactorResult) Validate() error {
    if f.Metadata == nil {
        f.Metadata = make(map[string]any)  // modifies original
    }
    return nil
}
```

**When to use pointer receivers:**
1. The method **modifies** the receiver
2. The struct is **large** (avoid copying)
3. Consistency — if any method uses a pointer receiver, use pointer receivers everywhere for that type

**When to use value receivers:**
1. Small structs that don't need modification
2. Primitive-like types (`int`, `string` wrappers)

From `models.go`:

```go
// Value receiver — read-only computation, result is returned
func (m *ManagerInfo) WinRate() float64 {
    if len(m.Results) == 0 {
        return 0.0
    }
    wins := 0
    for _, r := range m.Results {
        if r == "W" {
            wins++
        }
    }
    return float64(wins) / float64(len(m.Results))
}

// Pointer receiver — reads shared struct data
func (h *H2HRecord) HomeWins() int {
    count := 0
    for _, r := range h.Results {
        if r.HomeScore > r.AwayScore {
            count++
        }
    }
    return count
}

// Pointer receiver — modifies struct
func (f *FactorResult) Validate() error {
    // ...
    if f.Metadata == nil {
        f.Metadata = make(map[string]any)  // mutation
    }
    return nil
}
```

## 9.2 The Full Prediction Pipeline — Method Chaining

Tracing `PredictionEngine.Predict()` shows how methods chain together in production Go:

```go
// From algorithm.go — the full prediction pipeline as method calls
func (e *PredictionEngine) Predict(data *domain.MatchData) (*domain.PredictionResult, error) {
    // Guard clause
    if data == nil {
        return nil, fmt.Errorf("match data is required")
    }

    // Step 1: Build context
    ctxBuilder := mctx.NewMatchContextBuilder(e.historicalData)   // constructor
    matchCtx := ctxBuilder.BuildContext(data)                      // method call

    // Step 2: Calculate all 17 factors
    factors := e.calculateAllFactors(data, matchCtx)              // method call

    // Step 3: Weighted probabilities
    rawProbs := e.calculateWeightedProbabilities(factors)         // method call

    // Step 4: Market odds blending (if available)
    if data.HomeOdds > 0 && data.DrawOdds > 0 && data.AwayOdds > 0 {
        marketProbs := oddsToProbs(data.HomeOdds, data.DrawOdds, data.AwayOdds)
        dataQuality := e.assessDataQuality(data)
        modelWeight := 0.40 + dataQuality*0.30
        rawProbs = blendProbabilities(marketProbs, rawProbs, modelWeight)
    }

    // Step 5: Poisson blend (football: 60% Poisson + 40% weighted factors)
    var blended domain.Probabilities
    if e.sport == "football" {
        poissonProbs := e.calculatePoissonProbabilities(data, factors)
        blended = blendProbabilities(rawProbs, poissonProbs, 0.60)
    } else {
        blended = rawProbs
    }

    // Step 6: Platt scaling calibration
    calibrated := e.calibrateProbabilities(blended)

    // Step 7: Confidence score
    confidence := e.calculateConfidence(factors, calibrated)

    // Step 8: Betting recommendation
    recommendation := e.generateRecommendation(
        calibrated, confidence, data.HomeOdds, data.DrawOdds, data.AwayOdds,
    )

    // Step 9: Build result
    return &domain.PredictionResult{
        HomeTeam: data.HomeTeam,
        AwayTeam: data.AwayTeam,
        Probabilities: domain.Probabilities{
            Home: round4(calibrated.Home),
            Draw: round4(calibrated.Draw),
            Away: round4(calibrated.Away),
        },
        Confidence:     round4(confidence),
        Recommendation: recommendation,
        Factors:        factors,
        Timestamp:      time.Now().Format(time.RFC3339),
    }, nil
}
```

## 9.3 Helper Functions (Package-Level)

Go functions don't have to be methods on a type. Package-level functions are fine and common:

```go
// From algorithm.go — package-level helpers
func round4(f float64) float64 { return math.Round(f*10000) / 10000 }
func round2(f float64) float64 { return math.Round(f*100) / 100 }

func cloneWeights(w map[string]float64) map[string]float64 {
    out := make(map[string]float64, len(w))
    for k, v := range w {
        out[k] = v
    }
    return out
}
```

---

# Chapter 10 — Working with the Standard Library

Go's standard library is rich and deliberately used in this project. Let's trace the most common packages.

## 10.1 `fmt` — Formatted I/O

```go
import "fmt"

// Print
fmt.Println("hello world")               // with newline
fmt.Printf("Elo: %.1f\n", 1542.3)        // formatted, %T = type, %v = any
fmt.Sprintf("match: %s vs %s", h, a)     // return string (don't print)
fmt.Fprintf(os.Stderr, "error: %v", err) // write to any io.Writer

// Error creation
err := fmt.Errorf("open %s: %w", path, originalErr)  // %w wraps for errors.Is()
```

## 10.2 `os` — Operating System Interface

```go
import "os"

// File I/O (from storage/csv.go)
f, err := os.Open("data.csv")     // open for reading
f, err := os.Create("out.csv")    // create/truncate for writing
defer f.Close()

// Directory creation (from storage/csv.go)
err = os.MkdirAll("data/exports", 0o755)  // create all directories, like mkdir -p

// File info
info, err := os.Stat("data.csv")
if os.IsNotExist(err) { ... }
```

## 10.3 `encoding/csv` — CSV Read/Write

From `storage/csv.go` — complete CSV round-trip:

```go
import "encoding/csv"

// READING
func parseMatchCSV(r io.Reader) ([]MatchRecord, error) {
    reader := csv.NewReader(r)
    reader.LazyQuotes = true       // tolerate messy CSV
    reader.TrimLeadingSpace = true

    header, err := reader.Read()   // read first row as header
    if err != nil {
        return nil, fmt.Errorf("read header: %w", err)
    }

    // Build column name → index map
    colIdx := make(map[string]int)
    for i, name := range header {
        colIdx[strings.TrimSpace(name)] = i
    }

    var records []MatchRecord
    for {
        row, err := reader.Read()
        if err == io.EOF {   // EOF is NOT an error — it means we're done
            break
        }
        if err != nil {
            return nil, fmt.Errorf("read row: %w", err)
        }
        // parse row into MatchRecord...
        records = append(records, rec)
    }
    return records, nil
}

// WRITING
func (s *CSVStore) WriteHistoricalData(filename string, records []MatchRecord) error {
    f, err := os.Create(path)
    if err != nil {
        return fmt.Errorf("create %s: %w", path, err)
    }
    defer f.Close()

    w := csv.NewWriter(f)
    defer w.Flush()   // flush buffered data to file

    header := []string{"Date", "HomeTeam", "AwayTeam", "HomeGoals", ...}
    if err := w.Write(header); err != nil {
        return fmt.Errorf("write header: %w", err)
    }

    for _, r := range records {
        row := []string{
            r.Date, r.HomeTeam, r.AwayTeam,
            strconv.Itoa(r.HomeGoals),     // int → string
            formatFloat(r.HomeOdds),        // float64 → string
        }
        if err := w.Write(row); err != nil {
            return fmt.Errorf("write row: %w", err)
        }
    }
    return nil
}
```

## 10.4 `encoding/json` — JSON Serialization

```go
import "encoding/json"

// Marshal (Go → JSON)
result := &PredictionResult{HomeTeam: "Arsenal", ...}
b, err := json.Marshal(result)
jsonStr := string(b)

// Marshal with pretty-print
b, err := json.MarshalIndent(result, "", "  ")

// Unmarshal (JSON → Go)
var data MatchData
err := json.Unmarshal([]byte(jsonStr), &data)  // note: pass pointer

// From data/fixtures.go — decode JSON API response
resp, err := http.Get(url)
defer resp.Body.Close()

var fixtures []FixtureResponse
err = json.NewDecoder(resp.Body).Decode(&fixtures)
```

## 10.5 `net/http` — HTTP Client

From `data/collector.go`:

```go
import "net/http"

// Create client with timeout (always set a timeout!)
httpClient := &http.Client{Timeout: 30 * time.Second}

// Simple GET request
resp, err := httpClient.Get(url)
if err != nil {
    return nil, fmt.Errorf("GET %s: %w", url, err)
}
defer resp.Body.Close()                  // always close the body

if resp.StatusCode != http.StatusOK {
    return nil, fmt.Errorf("unexpected status %d", resp.StatusCode)
}

// Read body
body, err := io.ReadAll(resp.Body)

// POST request
payload := strings.NewReader(`{"key": "value"}`)
resp, err := httpClient.Post(url, "application/json", payload)
```

## 10.6 `strconv` — String Conversions

```go
import "strconv"

// int ↔ string
s := strconv.Itoa(42)          // int → string: "42"
n, err := strconv.Atoi("42")  // string → int

// float64 ↔ string (from storage/csv.go)
s := strconv.FormatFloat(3.14, 'f', -1, 64)  // float → string
f, err := strconv.ParseFloat("3.14", 64)       // string → float64

// bool ↔ string
s := strconv.FormatBool(true)    // "true"
b, err := strconv.ParseBool("1") // "1","t","T","true","TRUE" → true
```

## 10.7 `strings` — String Utilities

```go
import "strings"

strings.TrimSpace("  hello  ")       // "hello"
strings.ToLower("ARSENAL")           // "arsenal"
strings.ToUpper("arsenal")           // "ARSENAL"
strings.Contains("hello", "ell")     // true
strings.HasPrefix("football", "foo") // true
strings.HasSuffix("football", "all") // true
strings.Split("W,D,L", ",")         // ["W", "D", "L"]
strings.Join([]string{"W","D"}, ",") // "W,D"
strings.Replace("a-b-c", "-", "_", -1) // "a_b_c" (-1 = all)
strings.LastIndex("a/b/c", "/")      // 3

// From storage/csv.go:
dir := path[:strings.LastIndex(path, "/")]  // extract directory
```

## 10.8 `math` — Mathematical Functions

```go
import "math"

math.Abs(-3.14)              // 3.14
math.Round(3.7)              // 4.0
math.Floor(3.7)              // 3.0
math.Ceil(3.2)               // 4.0
math.Sqrt(16.0)              // 4.0
math.Pow(2, 10)              // 1024.0
math.Log(math.E)             // 1.0
math.Tanh(1.0)               // 0.7616...
math.Max(3.0, 5.0)           // 5.0
math.Min(3.0, 5.0)           // 3.0
math.Exp(1.0)                // e = 2.718...
math.Pi                      // 3.14159265...
math.Inf(1)                  // +Infinity
math.IsNaN(math.NaN())       // true

// From factors.go — math in prediction logic
xgDiff := homeXG - awayXG
normalizedDiff := math.Tanh(xgDiff / 2)  // squash to [-1, 1]

// From algorithm.go — Elo formula
expectedHome := 1.0 / (1.0 + math.Pow(10, (awayElo-homeElo)/400))
```

## 10.9 `time` — Time & Duration

```go
import "time"

// Current time
now := time.Now()
ts := time.Now().Format(time.RFC3339)   // "2026-03-05T14:23:01Z"

// Duration constants
30 * time.Second
5 * time.Minute
24 * time.Hour

// From data/collector.go — HTTP client timeout
httpClient := &http.Client{Timeout: 30 * time.Second}

// From calibration.go — timestamping records
if timestamp == "" {
    timestamp = time.Now().Format(time.RFC3339)
}
```

---

# Chapter 11 — Design Patterns in Go

Go idioms produce recognizable patterns. Knowing them signals Go fluency in interviews.

## 11.1 Constructor Pattern (Factory)

Always initialize with a `NewXxx()` function that validates and sets defaults:

```go
// Pattern
func NewXxx(params ...) *Xxx {
    x := &Xxx{
        field: defaultValue,
        map_:  make(map[KeyT]ValT),
    }
    // ... configure
    return x
}

// From algorithm.go
func NewPredictionEngine(sport string, useV2Weights bool, enableCalibration bool) *PredictionEngine {
    e := &PredictionEngine{
        sport:      sport,
        eloRatings: make(map[string]float64),
        calib:      calibParams{a: 1.0, b: 0.0},
    }
    e.config = e.loadSportConfig(sport)
    if useV2Weights && sport == "football" {
        e.config.weights = cloneWeights(domain.FootballWeightsV2)
    }
    if enableCalibration {
        e.calibrationEngine = NewCalibrationEngine(0.01, 1000)
    }
    return e
}
```

## 11.2 Options/Configuration Pattern (switch-based)

When a type behaves differently based on sport/mode/config:

```go
// From algorithm.go
func (e *PredictionEngine) loadSportConfig(sport string) sportConfig {
    switch sport {
    case "basketball":
        return sportConfig{
            homeAdvantage: 0.06,
            baseElo:       1500,
            kFactor:       20,
            minConfidence: 0.55,
            weights: map[string]float64{
                "offensiveRating": 0.20,
                "defensiveRating": 0.18,
                // ...
            },
        }
    case "tennis":
        return sportConfig{
            minConfidence: 0.60,
            weights: map[string]float64{
                "surfacePerformance": 0.25,
                // ...
            },
        }
    default: // football
        return sportConfig{
            homeAdvantage:  0.10,
            baseElo:        1500,
            kFactor:        32,
            drawThreshold:  0.25,
            minConfidence:  0.55,
            maxGoalsLambda: 4.0,
            weights:        cloneWeights(domain.FootballWeightsV1),
        }
    }
}
```

## 11.3 Pipeline Pattern (Sequential Processing)

The 7-step data enrichment pipeline:

```go
// From data/collector.go — conceptual pipeline
func (c *HistoricalDataCollector) runPipeline(
    ctx context.Context,
    seasons, leagues []string,
    status *CollectionStatus,
) error {
    // Step 1: Fetch raw CSV data
    status.set("Fetching match data", 10)
    records, err := c.fetchRawData(ctx, seasons, leagues)
    if err != nil {
        return fmt.Errorf("step 1 fetch: %w", err)
    }

    // Step 2: Add xG estimates
    status.set("Calculating expected goals", 25)
    records = c.addExpectedGoals(records)

    // Step 3: Calculate Elo ratings
    status.set("Calculating Elo ratings", 40)
    records = c.calculateEloRatings(records)

    // Step 4: Calculate form strings
    status.set("Calculating form", 55)
    records = c.calculateForm(records)

    // Step 5: Rest and congestion
    status.set("Calculating rest/fatigue", 65)
    records = c.calculateRestCongestion(records)

    // Step 6: Advanced stats
    status.set("Calculating advanced stats", 78)
    records = c.calculateAdvancedStats(records)

    // Step 7: League positions
    status.set("Calculating league positions", 90)
    records = c.calculateLeaguePositions(records)

    // Store result
    status.set("Saving data", 95)
    return c.store.WriteHistoricalData("historical.csv", records)
}
```

## 11.4 Strategy Pattern (Pluggable Algorithms)

17 factor functions with the same signature — interchangeable strategies:

```go
// From factors.go — each factor follows the same pattern:
// takes *MatchData and/or *MatchContext, returns a result

func (e *PredictionEngine) calculateExpectedGoals(data *domain.MatchData) map[string]interface{}
func (e *PredictionEngine) calculateAdvancedStats(data *domain.MatchData) map[string]interface{}
func (e *PredictionEngine) calculateTeamStrength(data *domain.MatchData) map[string]interface{}
// ...

// All assembled in one place:
func (e *PredictionEngine) calculateAllFactors(
    data *domain.MatchData,
    ctx *domain.MatchContext,
) map[string]interface{} {
    factors := make(map[string]interface{}, 17)

    factors["expectedGoals"]          = e.calculateExpectedGoals(data)
    factors["advancedStats"]          = e.calculateAdvancedStats(data)
    factors["teamStrength"]           = e.calculateTeamStrength(data)
    factors["tacticalMatchup"]        = e.calculateTacticalMatchup(data)
    factors["currentForm"]            = e.calculateCurrentForm(data)
    factors["playerImpact"]           = e.calculatePlayerImpact(data)
    factors["restAndFatigue"]         = e.calculateRestFatigue(data)
    factors["motivation"]             = e.calculateMotivation(data)
    factors["homeAdvantage"]          = e.calculateHomeAdvantage(data)
    factors["externalFactors"]        = e.calculateExternalFactors(data)
    factors["teamQualityGap"]         = e.calculateTeamQualityGap(data)

    h2hHist, h2hAnom := e.calculateH2HFactors(data, ctx)
    factors["h2hHistorical"]          = h2hHist
    factors["h2hAnomaly"]             = h2hAnom
    factors["possessionQuality"]      = e.calculatePossessionQuality(data, ctx)
    factors["managerMomentum"]        = e.calculateManagerMomentum(data, ctx)
    factors["relegationMotivation"]   = e.calculateRelegationMotivation(data, ctx)
    factors["counterAttackEfficiency"]= e.calculateCounterAttackEfficiency(data, ctx)
    factors["awayDrawFrequency"]      = e.calculateAwayDrawFrequency(data, ctx)

    return factors
}
```

## 11.5 Repository Pattern (Data Access)

```go
// The CSVStore acts as a repository — abstracts data access
type CSVStore struct {
    DataDir string
}

func NewCSVStore(dataDir string) *CSVStore { ... }
func (s *CSVStore) ReadHistoricalData(filename string) ([]MatchRecord, error) { ... }
func (s *CSVStore) WriteHistoricalData(filename string, records []MatchRecord) error { ... }
func (s *CSVStore) Exists(filename string) bool { ... }

// Usage — caller doesn't care how data is stored
store := storage.NewCSVStore("./data")
records, err := store.ReadHistoricalData("epl_2425.csv")
```

## 11.6 Functional Options Pattern (Advanced)

A clean way to handle optional configuration without a large parameter list:

```go
// The functional options pattern (common in Go libraries)
type Option func(*PredictionEngine)

func WithCalibration(rate float64, maxHistory int) Option {
    return func(e *PredictionEngine) {
        e.calibrationEngine = NewCalibrationEngine(rate, maxHistory)
    }
}

func WithV2Weights() Option {
    return func(e *PredictionEngine) {
        e.config.weights = cloneWeights(domain.FootballWeightsV2)
    }
}

func NewEngine(sport string, opts ...Option) *PredictionEngine {
    e := &PredictionEngine{sport: sport, eloRatings: make(map[string]float64)}
    for _, opt := range opts {
        opt(e)  // apply each option
    }
    return e
}

// Usage
engine := NewEngine("football",
    WithCalibration(0.01, 1000),
    WithV2Weights(),
)
```

---

# Chapter 12 — Testing in Go

## 12.1 Test File Convention

Test files end in `_test.go`. Go automatically finds them during `go test`:

```
internal/domain/
├── models.go           ← production code
└── models_test.go      ← tests (same package: package domain)
```

## 12.2 Basic Test Function

```go
// models_test.go
package domain

import "testing"

func TestFactorResultValidate(t *testing.T) {
    // Arrange
    f := FactorResult{
        Name:       "expectedGoals",
        Value:      0.65,
        Weight:     0.12,
        Confidence: 80,
    }

    // Act
    err := f.Validate()

    // Assert
    if err != nil {
        t.Errorf("expected no error, got: %v", err)
    }
}

func TestFactorResultValidate_InvalidValue(t *testing.T) {
    f := FactorResult{Value: 1.5}  // out of range
    err := f.Validate()
    if err == nil {
        t.Error("expected error for value > 1.0, got nil")
    }
}
```

## 12.3 Table-Driven Tests

The canonical Go testing pattern — loop over test cases:

```go
func TestH2HRecordWinRate(t *testing.T) {
    tests := []struct {
        name        string
        results     []H2HResult
        perspective string
        want        float64
    }{
        {
            name: "home wins 2 of 4",
            results: []H2HResult{
                {HomeScore: 2, AwayScore: 1},  // home win
                {HomeScore: 0, AwayScore: 1},  // away win
                {HomeScore: 1, AwayScore: 0},  // home win
                {HomeScore: 1, AwayScore: 1},  // draw
            },
            perspective: "home",
            want:        0.5,
        },
        {
            name:        "empty results",
            results:     []H2HResult{},
            perspective: "home",
            want:        0.0,
        },
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            h := &H2HRecord{Results: tt.results}
            got := h.WinRate(tt.perspective)
            if got != tt.want {
                t.Errorf("WinRate() = %.2f, want %.2f", got, tt.want)
            }
        })
    }
}
```

## 12.4 Test Helpers & `t.Helper()`

```go
func assertNoError(t *testing.T, err error) {
    t.Helper()   // marks this as a helper — errors point to the caller, not here
    if err != nil {
        t.Fatalf("unexpected error: %v", err)
    }
}

func assertEqual(t *testing.T, got, want interface{}) {
    t.Helper()
    if got != want {
        t.Errorf("got %v, want %v", got, want)
    }
}
```

## 12.5 Running Tests

```bash
go test ./...                     # run all tests
go test ./internal/domain/...     # run domain package tests
go test -v ./...                  # verbose output
go test -run TestH2H ./...        # run tests matching regex
go test -count=1 ./...            # disable test caching
go test -race ./...               # enable data race detector (CRITICAL for concurrent code)
go test -cover ./...              # show test coverage
go test -bench=. ./...            # run benchmarks
```

> `go test -race` is mandatory before any code with goroutines goes to production.

## 12.6 Benchmarks

```go
func BenchmarkPredictionEngine(b *testing.B) {
    engine := NewPredictionEngine("football", true, false)
    data := &domain.MatchData{
        HomeTeam: "Arsenal",
        AwayTeam: "Chelsea",
        HomeXG:   1.8,
        AwayXG:   1.2,
    }

    b.ResetTimer()  // don't count setup time
    for i := 0; i < b.N; i++ {
        engine.Predict(data)  // b.N automatically chosen for reliable timing
    }
}
```

---

# Appendix A — Go Cheat Sheet

## Variable Declaration
```go
x := 42                    // short declaration (inside function)
var y float64 = 3.14       // explicit type
const Pi = 3.14159         // constant
```

## Control Flow
```go
// if
if x > 0 {
    // ...
} else if x < 0 {
    // ...
} else {
    // ...
}

// if with initialization
if err := doSomething(); err != nil {
    return err
}

// for (the only loop in Go)
for i := 0; i < 10; i++ { }           // C-style
for condition { }                      // while-style
for { }                                // infinite loop
for i, v := range slice { }           // range over slice
for k, v := range map_ { }            // range over map
for v := range channel { }            // range over channel

// switch (no fallthrough by default)
switch x {
case 1:
    // ...
case 2, 3:
    // ...
default:
    // ...
}
```

## Functions
```go
func name(a, b int) (int, error) {
    return a + b, nil
}

// Variadic
func sum(nums ...int) int {
    total := 0
    for _, n := range nums {
        total += n
    }
    return total
}

// Anonymous / closure
fn := func(x int) int { return x * 2 }
go func() { /* goroutine */ }()
```

## Structs & Methods
```go
type Point struct {
    X, Y float64
}

// Value receiver (read-only)
func (p Point) Distance() float64 {
    return math.Sqrt(p.X*p.X + p.Y*p.Y)
}

// Pointer receiver (modifies or large struct)
func (p *Point) Scale(factor float64) {
    p.X *= factor
    p.Y *= factor
}
```

## Interfaces
```go
type Writer interface {
    Write(data []byte) (int, error)
}

// Implement by having the method — no declaration needed
type MyWriter struct{}
func (w MyWriter) Write(data []byte) (int, error) { ... }
```

## Error Handling
```go
result, err := doSomething()
if err != nil {
    return fmt.Errorf("context: %w", err)
}
```

## Slices
```go
s := []int{1, 2, 3}
s = append(s, 4)
sub := s[1:3]          // [2, 3]
for i, v := range s { }
```

## Maps
```go
m := make(map[string]int)
m["key"] = 42
v, ok := m["key"]      // comma-ok
delete(m, "key")
for k, v := range m { }
```

## Goroutines & Sync
```go
go func() { ... }()    // launch goroutine

var mu sync.Mutex
mu.Lock()
defer mu.Unlock()

var rw sync.RWMutex
rw.RLock()             // multiple readers OK
defer rw.RUnlock()
```

## Defer
```go
defer f.Close()        // runs when function returns (LIFO order)
defer mu.Unlock()      // always unlock even on error
```

---

# Appendix B — Interview Q&A

---

**Q: What is the difference between a goroutine and a thread?**

A: An OS thread is managed by the operating system — each costs ~1MB of stack and requires a kernel context switch. A goroutine is managed by the Go runtime — it starts with ~2KB of stack (grows dynamically), and context switching happens in user space via cooperative/preemptive scheduling on a small pool of OS threads. You can run millions of goroutines; millions of threads would crash the system.

---

**Q: How does Go handle null/nil?**

A: Go has no `null` — it has `nil`, which only applies to pointer types, slices, maps, channels, functions, and interfaces. Every other type has a zero value (`0`, `""`, `false`, struct with all-zero fields). This prevents many null pointer exceptions. The zero value contract means every variable is always initialized, so you never use uninitialized memory.

---

**Q: Explain Go's interface system.**

A: Go interfaces are **implicitly satisfied** — if a type has all the methods an interface requires, it satisfies the interface without any declaration. There's no `implements` keyword. This is called structural typing (or duck typing with static checking). It enables decoupling: you can define an interface in the consuming package, and any existing type that happens to have the right methods works automatically — even from external libraries.

---

**Q: What is defer?**

A: `defer` schedules a function call to run at the end of the surrounding function, regardless of how the function returns (normal, panic, or error). Multiple defers run in LIFO order. Primary use: resource cleanup — `defer f.Close()`, `defer mu.Unlock()`, `defer resp.Body.Close()`. It prevents resource leaks even in error paths.

---

**Q: How does Go handle errors vs exceptions?**

A: Go has no exceptions. Functions return errors as explicit values — typically the last return value `(Result, error)`. Callers must explicitly handle or propagate errors: `if err != nil { return err }`. This makes error handling visible at every call site, which improves code clarity and prevents silent failures. The `panic`/`recover` mechanism exists but is reserved for truly unrecoverable situations (not for normal error flow).

---

**Q: What is the difference between a slice and an array?**

A: An array has a **fixed size** baked into its type: `[5]int` is different from `[6]int`. Arrays are value types — assigning copies all elements. A slice is a **dynamic view** over an underlying array: it has a pointer, length, and capacity. Slices are reference types — assigning a slice just copies the descriptor; the underlying data is shared. In practice, you almost always use slices in Go; arrays are rare.

---

**Q: When do you use a pointer receiver vs value receiver?**

A: **Pointer receiver** when the method modifies the receiver, the struct is large (avoid copying cost), or for consistency (if any method uses a pointer receiver, use pointer receivers everywhere for that type). **Value receiver** for small read-only types, or types that are inherently immutable values. If in doubt, use pointer receivers — they're safer and more consistent.

---

**Q: What is `make` vs `new`?**

A: `new(T)` allocates memory for type T, initializes it to its zero value, and returns a `*T`. `make(T, ...)` is specifically for slices, maps, and channels — it allocates AND initializes the internal data structures needed to use them. You almost never use `new` — use struct literals or `NewXxx()` constructors instead. You always use `make` for maps and channels before writing to them.

---

**Q: What is the `internal` package?**

A: A directory named `internal` creates a visibility boundary. Packages inside `internal/` can only be imported by code rooted at the parent directory. External projects cannot import your internal packages. The bet4me project uses `internal/` for all its packages — enforcing that external consumers can only use whatever is exported from the root or cmd packages.

---

**Q: How do you handle concurrency safely?**

A: Two main tools: (1) **Mutexes** (`sync.Mutex`, `sync.RWMutex`) for protecting shared state — any struct with mutable fields accessed by multiple goroutines needs a mutex, and methods acquire/release it with `Lock()`/`Unlock()`. (2) **Channels** for communication — pass data between goroutines without shared memory. The Go proverb: "Do not communicate by sharing memory; share memory by communicating." Use the simpler option: mutexes for state protection, channels for signaling or sending values.

---

**Q: What is the `context` package?**

A: `context.Context` is a standard way to carry deadlines, cancellation signals, and request-scoped values across API boundaries and goroutines. You pass it as the **first parameter** of any function that does I/O or could block. `context.WithTimeout(ctx, 30*time.Second)` creates a context that automatically cancels after 30 seconds, causing all downstream HTTP calls, database queries, etc. to abort. From `data/collector.go`: `StartCollection(ctx context.Context, ...)`.

---

**Q: What is the Kelly Criterion?**

A: (Bonus — relevant to this codebase) The Kelly Criterion is a formula for optimal bet sizing: `f = (b*p - q) / b` where `f` is the fraction of bankroll to bet, `b` is the net odds, `p` is the probability of winning, and `q = 1 - p`. Betting full Kelly maximizes long-run growth rate but is volatile; practitioners use fractional Kelly (e.g., 25% of Kelly) to reduce variance. The bet4me engine calculates Kelly stakes in `probs.go`.

---

*End of Go Crash Course — Good luck on Wednesday!*

---

> **Reference codebase:** `github.com/bet4me/betting-algorithm-go`
> **Go version:** 1.23.6
> **Document generated:** March 2026
