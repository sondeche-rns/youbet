// Package main wires all dependencies and starts the HTTP server on :5000,
// matching the Flask server in app.py.
package main

import (
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"path/filepath"

	"github.com/joho/godotenv"

	"bet4me/betting-algorithm-go/internal/algorithm"
	"bet4me/betting-algorithm-go/internal/api"
	"bet4me/betting-algorithm-go/internal/backtest"
	"bet4me/betting-algorithm-go/internal/data"
	"bet4me/betting-algorithm-go/internal/jackpot"
)

func main() {
	// ── Environment ─────────────────────────────────────────────────────────
	_ = godotenv.Load() // silently ignore missing .env

	logger := slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo}))

	// ── Resolve data directory ───────────────────────────────────────────────
	// Convention: data/ lives one level above cmd/server/ (i.e. next to go.mod).
	exe, _ := os.Executable()
	root := filepath.Join(filepath.Dir(exe), "..", "..")
	// Allow override via DATA_DIR env var.
	dataDir := os.Getenv("DATA_DIR")
	if dataDir == "" {
		dataDir = filepath.Join(root, "data")
	}
	dataDir, _ = filepath.Abs(dataDir)

	oddsAPIKey := os.Getenv("ODDS_API_KEY")
	apiFootballKey := os.Getenv("API_FOOTBALL_KEY")
	port := os.Getenv("PORT")
	if port == "" {
		port = "5000"
	}

	// ── Create required directories ──────────────────────────────────────────
	for _, dir := range []string{
		filepath.Join(dataDir, "final"),
		filepath.Join(dataDir, "backtests"),
		filepath.Join(dataDir, "jackpots"),
		filepath.Join(dataDir, "jackpot_predictions"),
		filepath.Join(dataDir, "jackpot_results"),
	} {
		if err := os.MkdirAll(dir, 0755); err != nil {
			logger.Warn("could not create directory", "dir", dir, "err", err)
		}
	}

	// ── Prediction engine ────────────────────────────────────────────────────
	engine := algorithm.NewPredictionEngine("football", true, false)

	// ── Data layer ───────────────────────────────────────────────────────────
	collector := data.NewHistoricalDataCollector(dataDir, nil, logger)
	fetcher := data.NewLiveFixturesFetcher(oddsAPIKey, apiFootballKey, nil, logger)

	configPath := filepath.Join(root, "config", "data_sources.json")
	sources, err := data.NewDataSourcesManager(configPath)
	if err != nil {
		logger.Warn("could not load data_sources.json, using empty manager", "err", err)
		// Create a minimal empty manager so handlers don't panic.
		sources, _ = data.NewDataSourcesManager("")
	}

	// ── Backtest engine ──────────────────────────────────────────────────────
	backtester := backtest.NewBacktestEngine(engine, dataDir, logger)

	// ── Jackpot layer ────────────────────────────────────────────────────────
	jFetcher := jackpot.NewJackpotFetcher(dataDir, nil, logger)
	jAnalyzer := jackpot.NewJackpotAnalyzer(engine, dataDir, logger)

	// ── HTTP server ──────────────────────────────────────────────────────────
	server := api.NewServer(engine, collector, fetcher, sources, backtester, jFetcher, jAnalyzer, dataDir, logger)

	addr := "0.0.0.0:" + port
	fmt.Println("======================================================================")
	fmt.Println("  SPORTS BETTING ANALYTICS PLATFORM — Go Server")
	fmt.Println("======================================================================")
	fmt.Printf("\n  Starting server on http://localhost:%s\n", port)
	fmt.Printf("  API: http://localhost:%s/api\n\n", port)
	fmt.Println("  Press CTRL+C to stop")
	fmt.Println()

	if err := http.ListenAndServe(addr, server.Handler()); err != nil {
		logger.Error("server error", "err", err)
		os.Exit(1)
	}
}
