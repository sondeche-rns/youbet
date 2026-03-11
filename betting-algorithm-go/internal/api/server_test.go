// Package api_test contains integration tests for the HTTP server.
// Each test uses httptest.NewServer so no real network calls are made;
// external API errors (Odds API, scraping) are handled gracefully by the
// handlers and result in 200 with empty/fallback data.
package api_test

import (
	"bytes"
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"

	"bet4me/betting-algorithm-go/internal/algorithm"
	"bet4me/betting-algorithm-go/internal/api"
	"bet4me/betting-algorithm-go/internal/backtest"
	"bet4me/betting-algorithm-go/internal/data"
	"bet4me/betting-algorithm-go/internal/jackpot"
)

// newHandler wires up all dependencies with a temp data directory and
// returns the chi handler ready for httptest use.
func newHandler(t *testing.T) http.Handler {
	t.Helper()
	dataDir := t.TempDir()
	for _, sub := range []string{"final", "backtests", "jackpots", "jackpot_predictions", "jackpot_results"} {
		if err := os.MkdirAll(dataDir+"/"+sub, 0755); err != nil {
			t.Fatalf("mkdir %s: %v", sub, err)
		}
	}

	logger := slog.New(slog.NewTextHandler(io.Discard, nil))
	engine := algorithm.NewPredictionEngine("football", true, false)
	collector := data.NewHistoricalDataCollector(dataDir, nil, logger)
	fetcher := data.NewLiveFixturesFetcher("", "", nil, logger)
	sources, _ := data.NewDataSourcesManager("")
	backtester := backtest.NewBacktestEngine(engine, dataDir, logger)
	jFetcher := jackpot.NewJackpotFetcher(dataDir, nil, logger)
	jAnalyzer := jackpot.NewJackpotAnalyzer(engine, dataDir, logger)

	srv := api.NewServer(engine, collector, fetcher, sources, backtester, jFetcher, jAnalyzer, dataDir, logger)
	return srv.Handler()
}

// get issues a GET request and returns the response.
func get(t *testing.T, ts *httptest.Server, path string) *http.Response {
	t.Helper()
	resp, err := ts.Client().Get(ts.URL + path)
	if err != nil {
		t.Fatalf("GET %s: %v", path, err)
	}
	return resp
}

// post issues a POST request with a JSON body and returns the response.
func post(t *testing.T, ts *httptest.Server, path string, body any) *http.Response {
	t.Helper()
	b, err := json.Marshal(body)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}
	resp, err := ts.Client().Post(ts.URL+path, "application/json", bytes.NewReader(b))
	if err != nil {
		t.Fatalf("POST %s: %v", path, err)
	}
	return resp
}

// decodeJSON reads the response body into v and closes it.
func decodeJSON(t *testing.T, resp *http.Response, v any) {
	t.Helper()
	defer resp.Body.Close()
	if err := json.NewDecoder(resp.Body).Decode(v); err != nil {
		t.Fatalf("decode JSON: %v", err)
	}
}

// assertStatus fails if the response status code does not match expected.
func assertStatus(t *testing.T, resp *http.Response, expected int) {
	t.Helper()
	if resp.StatusCode != expected {
		body, _ := io.ReadAll(resp.Body)
		resp.Body.Close()
		t.Fatalf("expected status %d, got %d: %s", expected, resp.StatusCode, string(body))
	}
}

// assertJSON fails if the Content-Type is not application/json.
func assertJSON(t *testing.T, resp *http.Response) {
	t.Helper()
	ct := resp.Header.Get("Content-Type")
	if !strings.HasPrefix(ct, "application/json") {
		t.Fatalf("expected Content-Type application/json, got %q", ct)
	}
}

// ─────────────────────────────────────────────
// Dashboard
// ─────────────────────────────────────────────

func TestGetDashboardStats(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	resp := get(t, ts, "/api/dashboard/stats")
	assertStatus(t, resp, http.StatusOK)
	assertJSON(t, resp)

	var result map[string]any
	decodeJSON(t, resp, &result)

	for _, key := range []string{"overall_accuracy", "roi", "total_predictions", "win_streak", "current_bankroll", "total_pnl"} {
		if _, ok := result[key]; !ok {
			t.Errorf("missing key %q in dashboard stats", key)
		}
	}
}

func TestGetUpcoming(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	resp := get(t, ts, "/api/dashboard/upcoming")
	assertStatus(t, resp, http.StatusOK)
	assertJSON(t, resp)

	var result []any
	decodeJSON(t, resp, &result)
	// May be empty if no API key — just check it's a list
	_ = result
}

func TestGetRecentResults(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	resp := get(t, ts, "/api/dashboard/recent")
	assertStatus(t, resp, http.StatusOK)
	assertJSON(t, resp)
}

// ─────────────────────────────────────────────
// Predictions
// ─────────────────────────────────────────────

func TestPredictMatch(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	body := map[string]any{
		"home_team":   "Arsenal",
		"away_team":   "Chelsea",
		"competition": "Premier League",
	}
	resp := post(t, ts, "/api/predict", body)
	assertStatus(t, resp, http.StatusOK)
	assertJSON(t, resp)

	var result map[string]any
	decodeJSON(t, resp, &result)

	for _, key := range []string{"homeWinProb", "drawProb", "awayWinProb", "confidence"} {
		if _, ok := result[key]; !ok {
			t.Errorf("prediction missing key %q", key)
		}
	}
}

func TestPredictMatch_BadJSON(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	resp, err := ts.Client().Post(ts.URL+"/api/predict", "application/json", strings.NewReader("not-json"))
	if err != nil {
		t.Fatal(err)
	}
	assertStatus(t, resp, http.StatusBadRequest)
}

// ─────────────────────────────────────────────
// Fixtures
// ─────────────────────────────────────────────

func TestGetUpcomingFixtures(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	// No API key — expect internal error or empty result; either 200 or 500 is fine
	resp := get(t, ts, "/api/fixtures/upcoming?sport=soccer_epl&days=7")
	// Handler may return 500 without an API key — just check JSON
	assertJSON(t, resp)
	io.Copy(io.Discard, resp.Body)
	resp.Body.Close()
}

func TestGetCurrentSeason(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	resp := get(t, ts, "/api/fixtures/current-season?league=E0")
	// May fail without network — just validate it returns JSON
	assertJSON(t, resp)
	io.Copy(io.Discard, resp.Body)
	resp.Body.Close()
}

func TestGetAvailableSports(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	resp := get(t, ts, "/api/fixtures/available-sports")
	assertJSON(t, resp)
	io.Copy(io.Discard, resp.Body)
	resp.Body.Close()
}

func TestGetAPIQuota_NoKey(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	resp := get(t, ts, "/api/fixtures/quota")
	assertStatus(t, resp, http.StatusBadRequest)
	assertJSON(t, resp)
	io.Copy(io.Discard, resp.Body)
	resp.Body.Close()
}

func TestGetLiveOdds_NotFound(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	body := map[string]any{"home_team": "Arsenal", "away_team": "Chelsea", "sport": "soccer_epl"}
	resp := post(t, ts, "/api/fixtures/live-odds", body)
	assertStatus(t, resp, http.StatusNotFound)
	io.Copy(io.Discard, resp.Body)
	resp.Body.Close()
}

// ─────────────────────────────────────────────
// Data collection
// ─────────────────────────────────────────────

func TestGetCollectionStatus(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	resp := get(t, ts, "/api/data/status")
	assertStatus(t, resp, http.StatusOK)
	assertJSON(t, resp)

	var result map[string]any
	decodeJSON(t, resp, &result)
	// Should have Running field (false initially)
	if _, ok := result["running"]; !ok {
		t.Error("missing running field in collection status")
	}
}

func TestGetHistoricalData_NoFile(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	resp := get(t, ts, "/api/data/historical")
	assertStatus(t, resp, http.StatusOK)
	assertJSON(t, resp)

	var result map[string]any
	decodeJSON(t, resp, &result)
	exists, _ := result["exists"].(bool)
	if exists {
		t.Error("expected exists=false when no CSV")
	}
}

func TestGetDataSources(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	resp := get(t, ts, "/api/data/sources")
	assertStatus(t, resp, http.StatusOK)
	assertJSON(t, resp)

	var result map[string]any
	decodeJSON(t, resp, &result)
	for _, key := range []string{"sources", "default_config"} {
		if _, ok := result[key]; !ok {
			t.Errorf("missing key %q in data sources", key)
		}
	}
}

func TestGetAvailableLeagues(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	resp := get(t, ts, "/api/data/leagues")
	assertStatus(t, resp, http.StatusOK)
	assertJSON(t, resp)
	io.Copy(io.Discard, resp.Body)
	resp.Body.Close()
}

func TestGetAvailableSeasons(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	resp := get(t, ts, "/api/data/seasons")
	assertStatus(t, resp, http.StatusOK)
	assertJSON(t, resp)
	io.Copy(io.Discard, resp.Body)
	resp.Body.Close()
}

func TestStartDataCollection(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	body := map[string]any{
		"sport":   "football",
		"seasons": []string{"2324"},
	}
	resp := post(t, ts, "/api/data/collect", body)
	assertStatus(t, resp, http.StatusOK)
	assertJSON(t, resp)

	var result map[string]any
	decodeJSON(t, resp, &result)
	if _, ok := result["message"]; !ok {
		t.Error("missing message field")
	}
}

func TestStartDataCollection_AlreadyRunning(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	body := map[string]any{"sport": "football", "seasons": []string{"2324"}}
	// First call starts collection
	resp1 := post(t, ts, "/api/data/collect", body)
	io.Copy(io.Discard, resp1.Body)
	resp1.Body.Close()

	// Second call while goroutine may still be running — could get 400 if still running
	// Just ensure it returns valid JSON either way
	resp2 := post(t, ts, "/api/data/collect", body)
	assertJSON(t, resp2)
	io.Copy(io.Discard, resp2.Body)
	resp2.Body.Close()
}

// ─────────────────────────────────────────────
// Backtest
// ─────────────────────────────────────────────

func TestRunBacktest(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	body := map[string]any{
		"sport":            "football",
		"initial_bankroll": 1000,
		"kelly_fraction":   0.25,
		"max_stake_pct":    5.0,
	}
	resp := post(t, ts, "/api/backtest/run", body)
	assertStatus(t, resp, http.StatusOK)
	assertJSON(t, resp)

	var result map[string]any
	decodeJSON(t, resp, &result)
	if _, ok := result["results"]; !ok {
		t.Error("missing results field in backtest response")
	}
}

func TestGetBacktestResults_NoData(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	resp := get(t, ts, "/api/backtest/results")
	// 404 is expected when no backtest has been run yet
	assertStatus(t, resp, http.StatusNotFound)
	assertJSON(t, resp)
	io.Copy(io.Discard, resp.Body)
	resp.Body.Close()
}

func TestExportBacktest_NoData(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	resp := get(t, ts, "/api/backtest/export")
	assertStatus(t, resp, http.StatusNotFound)
	io.Copy(io.Discard, resp.Body)
	resp.Body.Close()
}

// ─────────────────────────────────────────────
// Performance
// ─────────────────────────────────────────────

func TestGetPerformanceSummary_NoData(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	resp := get(t, ts, "/api/performance/summary")
	// 404 when no backtest data
	assertStatus(t, resp, http.StatusNotFound)
	assertJSON(t, resp)
	io.Copy(io.Discard, resp.Body)
	resp.Body.Close()
}

func TestGetMonthlyPerformance(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	resp := get(t, ts, "/api/performance/monthly")
	assertStatus(t, resp, http.StatusOK)
	assertJSON(t, resp)

	var result []any
	decodeJSON(t, resp, &result)
	if len(result) == 0 {
		t.Error("expected at least one monthly entry")
	}
}

// ─────────────────────────────────────────────
// Config
// ─────────────────────────────────────────────

func TestGetWeights(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	resp := get(t, ts, "/api/config/weights")
	assertStatus(t, resp, http.StatusOK)
	assertJSON(t, resp)

	var weights map[string]float64
	decodeJSON(t, resp, &weights)
	if len(weights) == 0 {
		t.Error("expected non-empty weights map")
	}
}

func TestUpdateWeights(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	// First fetch current weights so we can re-send them (they already sum to 1).
	resp1 := get(t, ts, "/api/config/weights")
	var weights map[string]float64
	decodeJSON(t, resp1, &weights)

	resp2 := post(t, ts, "/api/config/weights", weights)
	assertStatus(t, resp2, http.StatusOK)
	assertJSON(t, resp2)

	var result map[string]string
	decodeJSON(t, resp2, &result)
	if result["message"] == "" {
		t.Error("expected message in update weights response")
	}
}

func TestUpdateWeights_InvalidSum(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	bad := map[string]float64{"home_advantage": 0.5, "form": 0.1} // sums to 0.6
	resp := post(t, ts, "/api/config/weights", bad)
	assertStatus(t, resp, http.StatusBadRequest)
	io.Copy(io.Discard, resp.Body)
	resp.Body.Close()
}

// ─────────────────────────────────────────────
// Jackpots
// ─────────────────────────────────────────────

func TestFetchJackpots(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	body := map[string]any{"providers": []string{"sportpesa"}}
	resp := post(t, ts, "/api/jackpots/fetch", body)
	assertStatus(t, resp, http.StatusOK)
	assertJSON(t, resp)

	var result map[string]any
	decodeJSON(t, resp, &result)
	if _, ok := result["jackpots"]; !ok {
		t.Error("missing jackpots field")
	}
}

func TestGetJackpotHistory_Empty(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	resp := get(t, ts, "/api/jackpots/history")
	assertStatus(t, resp, http.StatusOK)
	assertJSON(t, resp)

	var result map[string]any
	decodeJSON(t, resp, &result)
	if _, ok := result["jackpots"]; !ok {
		t.Error("missing jackpots field")
	}
}

func TestGetJackpotPerformance_Empty(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	resp := get(t, ts, "/api/jackpots/performance")
	assertStatus(t, resp, http.StatusOK)
	assertJSON(t, resp)
	io.Copy(io.Discard, resp.Body)
	resp.Body.Close()
}

func TestAnalyzeJackpot(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	body := map[string]any{
		"provider":      "SportPesa",
		"type":          "Mega Jackpot",
		"matches_count": 3,
		"fetched_at":    "2024-01-15T12:00:00Z",
		"url":           "https://example.com",
		"matches": []map[string]any{
			{"match_number": 1, "home_team": "Arsenal", "away_team": "Chelsea", "competition": "Premier League", "date": "2024-01-20"},
			{"match_number": 2, "home_team": "Man City", "away_team": "Liverpool", "competition": "Premier League", "date": "2024-01-20"},
			{"match_number": 3, "home_team": "Tottenham", "away_team": "Everton", "competition": "Premier League", "date": "2024-01-20"},
		},
	}
	resp := post(t, ts, "/api/jackpots/analyze", body)
	assertStatus(t, resp, http.StatusOK)
	assertJSON(t, resp)

	var result map[string]any
	decodeJSON(t, resp, &result)
	if _, ok := result["analysis"]; !ok {
		t.Error("missing analysis field")
	}
}

func TestRecordJackpotResults_MissingID(t *testing.T) {
	ts := httptest.NewServer(newHandler(t))
	defer ts.Close()

	body := map[string]any{"results": []any{}}
	resp := post(t, ts, "/api/jackpots/results", body)
	assertStatus(t, resp, http.StatusBadRequest)
	io.Copy(io.Discard, resp.Body)
	resp.Body.Close()
}

// ─────────────────────────────────────────────
// Benchmarks
// ─────────────────────────────────────────────

func BenchmarkPredictMatch(b *testing.B) {
	dataDir := b.TempDir()
	for _, sub := range []string{"final", "backtests", "jackpots", "jackpot_predictions", "jackpot_results"} {
		_ = os.MkdirAll(dataDir+"/"+sub, 0755)
	}
	logger := slog.New(slog.NewTextHandler(io.Discard, nil))
	engine := algorithm.NewPredictionEngine("football", true, false)
	collector := data.NewHistoricalDataCollector(dataDir, nil, logger)
	fetcher := data.NewLiveFixturesFetcher("", "", nil, logger)
	sources, _ := data.NewDataSourcesManager("")
	backtester := backtest.NewBacktestEngine(engine, dataDir, logger)
	jFetcher := jackpot.NewJackpotFetcher(dataDir, nil, logger)
	jAnalyzer := jackpot.NewJackpotAnalyzer(engine, dataDir, logger)
	srv := api.NewServer(engine, collector, fetcher, sources, backtester, jFetcher, jAnalyzer, dataDir, logger)
	ts := httptest.NewServer(srv.Handler())
	defer ts.Close()

	body := map[string]any{"home_team": "Arsenal", "away_team": "Chelsea", "competition": "Premier League"}
	bodyBytes, _ := json.Marshal(body)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		resp, err := ts.Client().Post(ts.URL+"/api/predict", "application/json", bytes.NewReader(bodyBytes))
		if err != nil {
			b.Fatal(err)
		}
		io.Copy(io.Discard, resp.Body)
		resp.Body.Close()
	}
}
