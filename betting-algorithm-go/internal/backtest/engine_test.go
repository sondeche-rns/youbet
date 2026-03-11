package backtest_test

import (
	"io"
	"log/slog"
	"os"
	"testing"

	"bet4me/betting-algorithm-go/internal/algorithm"
	"bet4me/betting-algorithm-go/internal/backtest"
)

func newEngine(t *testing.T) (*backtest.BacktestEngine, string) {
	t.Helper()
	dataDir := t.TempDir()
	for _, sub := range []string{"final", "backtests"} {
		if err := os.MkdirAll(dataDir+"/"+sub, 0755); err != nil {
			t.Fatalf("mkdir %s: %v", sub, err)
		}
	}
	logger := slog.New(slog.NewTextHandler(io.Discard, nil))
	engine := algorithm.NewPredictionEngine("football", true, false)
	return backtest.NewBacktestEngine(engine, dataDir, logger), dataDir
}

// TestRun_SampleData verifies that Run completes using the built-in sample data
// (no historical CSV present) and returns a valid Summary.
func TestRun_SampleData(t *testing.T) {
	be, _ := newEngine(t)

	cfg := backtest.Config{
		Sport:           "football",
		InitialBankroll: 1000,
		KellyFraction:   0.25,
		MaxStakePct:     5.0,
	}
	summary, err := be.Run(cfg)
	if err != nil {
		t.Fatalf("Run: %v", err)
	}
	if summary == nil {
		t.Fatal("Run returned nil summary")
	}

	// Basic sanity checks
	if summary.Overall.TotalMatches == 0 {
		t.Error("expected at least one match processed")
	}
	if summary.Overall.InitialBankroll != 1000 {
		t.Errorf("expected initial bankroll 1000, got %f", summary.Overall.InitialBankroll)
	}
	if summary.Overall.FinalBankroll <= 0 {
		t.Error("final bankroll should be positive")
	}
	if summary.Overall.OverallAccuracy < 0 || summary.Overall.OverallAccuracy > 100 {
		t.Errorf("accuracy %f out of [0,100]", summary.Overall.OverallAccuracy)
	}
	if len(summary.EquityCurve) == 0 {
		t.Error("expected non-empty equity curve")
	}
	if summary.Timestamp == "" {
		t.Error("expected non-empty timestamp")
	}
}

// TestRun_AccuracyByType verifies AccuracyByType is non-nil and only contains
// valid outcome keys. Keys are only added when predictions exist for that outcome,
// so not all three are guaranteed to appear in the sample dataset.
func TestRun_AccuracyByType(t *testing.T) {
	be, _ := newEngine(t)

	summary, err := be.Run(backtest.Config{InitialBankroll: 1000})
	if err != nil {
		t.Fatalf("Run: %v", err)
	}

	if summary.AccuracyByType == nil {
		t.Fatal("AccuracyByType map is nil")
	}
	if len(summary.AccuracyByType) == 0 {
		t.Error("AccuracyByType is empty; expected at least one outcome key")
	}
	valid := map[string]bool{"Home Win": true, "Draw": true, "Away Win": true}
	for k := range summary.AccuracyByType {
		if !valid[k] {
			t.Errorf("unexpected outcome key %q in AccuracyByType", k)
		}
	}
}

// TestRun_AccuracyByConfidence verifies AccuracyByConfidence is non-nil and contains
// only valid bin labels. Bins are only added when at least one match falls in that
// confidence range, so not all five are guaranteed to appear.
func TestRun_AccuracyByConfidence(t *testing.T) {
	be, _ := newEngine(t)

	summary, err := be.Run(backtest.Config{InitialBankroll: 1000})
	if err != nil {
		t.Fatalf("Run: %v", err)
	}

	if summary.AccuracyByConfidence == nil {
		t.Fatal("AccuracyByConfidence map is nil")
	}
	validBins := map[string]bool{
		"50-60%": true, "60-70%": true, "70-80%": true,
		"80-90%": true, "90-100%": true,
	}
	for k := range summary.AccuracyByConfidence {
		if !validBins[k] {
			t.Errorf("unexpected confidence bin %q in AccuracyByConfidence", k)
		}
	}
}

// TestRun_FilesCreated verifies that backtest JSON and CSV are saved to disk.
func TestRun_FilesCreated(t *testing.T) {
	be, dataDir := newEngine(t)

	_, err := be.Run(backtest.Config{InitialBankroll: 1000})
	if err != nil {
		t.Fatalf("Run: %v", err)
	}

	entries, err := os.ReadDir(dataDir + "/backtests")
	if err != nil {
		t.Fatalf("readdir backtests: %v", err)
	}

	var foundJSON, foundCSV bool
	for _, e := range entries {
		name := e.Name()
		if len(name) > 5 && name[len(name)-5:] == ".json" {
			foundJSON = true
		}
		if len(name) > 4 && name[len(name)-4:] == ".csv" {
			foundCSV = true
		}
	}
	if !foundJSON {
		t.Error("expected backtest JSON file in backtests/")
	}
	if !foundCSV {
		t.Error("expected backtest CSV file in backtests/")
	}
}

// TestLoadLatestResults verifies LoadLatestResults returns the summary from the most recent run.
func TestLoadLatestResults(t *testing.T) {
	be, _ := newEngine(t)

	original, err := be.Run(backtest.Config{InitialBankroll: 1000})
	if err != nil {
		t.Fatalf("Run: %v", err)
	}

	loaded, err := be.LoadLatestResults()
	if err != nil {
		t.Fatalf("LoadLatestResults: %v", err)
	}
	if loaded.Overall.TotalMatches != original.Overall.TotalMatches {
		t.Errorf("loaded TotalMatches %d != original %d", loaded.Overall.TotalMatches, original.Overall.TotalMatches)
	}
}

// TestLoadLatestResults_NoData verifies that LoadLatestResults returns an error when no file exists.
func TestLoadLatestResults_NoData(t *testing.T) {
	be, _ := newEngine(t)

	_, err := be.LoadLatestResults()
	if err == nil {
		t.Error("expected error when no backtest results exist")
	}
}

// TestGetLatestCSVPath verifies that the CSV path is returned after a run.
func TestGetLatestCSVPath(t *testing.T) {
	be, _ := newEngine(t)

	_, err := be.Run(backtest.Config{InitialBankroll: 1000})
	if err != nil {
		t.Fatalf("Run: %v", err)
	}

	csvPath, err := be.GetLatestCSVPath()
	if err != nil {
		t.Fatalf("GetLatestCSVPath: %v", err)
	}
	if csvPath == "" {
		t.Error("expected non-empty CSV path")
	}
	if _, err := os.Stat(csvPath); os.IsNotExist(err) {
		t.Errorf("CSV file does not exist at %s", csvPath)
	}
}

// TestGetLatestCSVPath_NoData verifies that GetLatestCSVPath errors when nothing exists.
func TestGetLatestCSVPath_NoData(t *testing.T) {
	be, _ := newEngine(t)

	_, err := be.GetLatestCSVPath()
	if err == nil {
		t.Error("expected error when no CSV exists")
	}
}

// TestRun_SeasonFilter verifies filtering by season doesn't panic.
func TestRun_SeasonFilter(t *testing.T) {
	be, _ := newEngine(t)

	cfg := backtest.Config{
		InitialBankroll: 1000,
		Season:          "2324",
	}
	_, err := be.Run(cfg)
	if err != nil {
		t.Fatalf("Run with season filter: %v", err)
	}
}

// TestRun_DateFilter verifies filtering by date range doesn't panic.
func TestRun_DateFilter(t *testing.T) {
	be, _ := newEngine(t)

	cfg := backtest.Config{
		InitialBankroll: 1000,
		StartDate:       "2023-08-01",
		EndDate:         "2024-05-31",
	}
	_, err := be.Run(cfg)
	if err != nil {
		t.Fatalf("Run with date filter: %v", err)
	}
}

// BenchmarkRun measures full backtest throughput on the 380-match sample dataset.
func BenchmarkRun(b *testing.B) {
	dataDir := b.TempDir()
	for _, sub := range []string{"final", "backtests"} {
		_ = os.MkdirAll(dataDir+"/"+sub, 0755)
	}
	logger := slog.New(slog.NewTextHandler(io.Discard, nil))
	engine := algorithm.NewPredictionEngine("football", true, false)
	be := backtest.NewBacktestEngine(engine, dataDir, logger)
	cfg := backtest.Config{InitialBankroll: 1000, KellyFraction: 0.25, MaxStakePct: 5.0}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		if _, err := be.Run(cfg); err != nil {
			b.Fatalf("Run: %v", err)
		}
	}
}
