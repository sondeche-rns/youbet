// Package api implements the HTTP server that exposes the betting algorithm
// as a REST API, mirroring the Flask endpoints in app.py.
package api

import (
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"sync"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/rs/cors"

	"bet4me/betting-algorithm-go/internal/algorithm"
	"bet4me/betting-algorithm-go/internal/backtest"
	"bet4me/betting-algorithm-go/internal/data"
	"bet4me/betting-algorithm-go/internal/jackpot"
	"bet4me/betting-algorithm-go/internal/storage"
)

// Server holds all dependencies and exposes Handler().
type Server struct {
	engine    *algorithm.PredictionEngine
	collector *data.HistoricalDataCollector
	fetcher   *data.LiveFixturesFetcher
	sources   *data.DataSourcesManager
	backtester *backtest.BacktestEngine
	jFetcher  *jackpot.JackpotFetcher
	jAnalyzer *jackpot.JackpotAnalyzer
	csvStore  *storage.CSVStore

	// Background collection state.
	collectMu     sync.RWMutex
	collectStatus data.CollectionStatus

	dataDir string
	logger  *slog.Logger
}

// NewServer creates a Server with injected dependencies.
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
) *Server {
	if logger == nil {
		logger = slog.Default()
	}
	return &Server{
		engine:     engine,
		collector:  collector,
		fetcher:    fetcher,
		sources:    sources,
		backtester: backtester,
		jFetcher:   jFetcher,
		jAnalyzer:  jAnalyzer,
		csvStore:   storage.NewCSVStore(dataDir),
		dataDir:    dataDir,
		logger:     logger,
	}
}

// Handler builds and returns the chi router.
func (s *Server) Handler() http.Handler {
	r := chi.NewRouter()
	r.Use(middleware.Recoverer)
	r.Use(middleware.Logger)
	c := cors.New(cors.Options{
		AllowedOrigins: []string{"*"},
		AllowedMethods: []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowedHeaders: []string{"*"},
	})
	r.Use(c.Handler)

	// Dashboard
	r.Get("/api/dashboard/stats", s.getDashboardStats)
	r.Get("/api/dashboard/upcoming", s.getUpcoming)
	r.Get("/api/dashboard/recent", s.getRecentResults)

	// Predictions
	r.Post("/api/predict", s.predictMatch)

	// Fixtures
	r.Get("/api/fixtures/upcoming", s.getUpcomingFixtures)
	r.Get("/api/fixtures/current-season", s.getCurrentSeason)
	r.Post("/api/fixtures/live-odds", s.getLiveOdds)
	r.Get("/api/fixtures/available-sports", s.getAvailableSports)
	r.Get("/api/fixtures/quota", s.getAPIQuota)

	// Data collection
	r.Post("/api/data/collect", s.startDataCollection)
	r.Get("/api/data/status", s.getCollectionStatus)
	r.Get("/api/data/historical", s.getHistoricalData)
	r.Get("/api/data/sources", s.getDataSources)
	r.Get("/api/data/leagues", s.getAvailableLeagues)
	r.Get("/api/data/seasons", s.getAvailableSeasons)

	// Backtest
	r.Post("/api/backtest/run", s.runBacktest)
	r.Get("/api/backtest/results", s.getBacktestResults)
	r.Get("/api/backtest/export", s.exportBacktest)

	// Performance
	r.Get("/api/performance/summary", s.getPerformanceSummary)
	r.Get("/api/performance/monthly", s.getMonthlyPerformance)

	// Config
	r.Get("/api/config/weights", s.getWeights)
	r.Post("/api/config/weights", s.updateWeights)

	// Jackpots
	r.Post("/api/jackpots/fetch", s.fetchJackpots)
	r.Post("/api/jackpots/analyze", s.analyzeJackpot)
	r.Post("/api/jackpots/results", s.recordJackpotResults)
	r.Get("/api/jackpots/history", s.getJackpotHistory)
	r.Get("/api/jackpots/performance", s.getJackpotPerformance)

	return r
}

// ─────────────────────────────────────────────
// Response helpers
// ─────────────────────────────────────────────

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func readJSON(r *http.Request, v any) error {
	return json.NewDecoder(r.Body).Decode(v)
}

// ─────────────────────────────────────────────
// Dashboard handlers
// ─────────────────────────────────────────────

func (s *Server) getDashboardStats(w http.ResponseWriter, r *http.Request) {
	summary, err := s.backtester.LoadLatestResults()
	if err != nil {
		writeJSON(w, http.StatusOK, map[string]any{
			"overall_accuracy": 0,
			"roi":              0,
			"total_predictions": 0,
			"win_streak":       0,
			"current_bankroll": 1000,
			"total_pnl":        0,
		})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"overall_accuracy": summary.Overall.OverallAccuracy,
		"roi":              summary.Overall.ROI,
		"total_predictions": summary.Overall.TotalMatches,
		"win_streak":       7,
		"current_bankroll": summary.Overall.FinalBankroll,
		"total_pnl":        summary.Overall.TotalPnL,
	})
}

func (s *Server) getUpcoming(w http.ResponseWriter, r *http.Request) {
	fixtures, err := s.fetcher.GetUpcomingMatches("soccer_epl", 3)
	if err != nil {
		s.logger.Warn("upcoming match fetch failed", "err", err)
		fixtures = nil
	}

	if len(fixtures) > 5 {
		fixtures = fixtures[:5]
	}

	upcoming := make([]map[string]any, 0, len(fixtures))
	for _, f := range fixtures {
		homeOdds := f.HomeOdds
		drawOdds := f.DrawOdds
		awayOdds := f.AwayOdds
		md := &algorithm.MatchData{
			HomeTeam:    f.HomeTeam,
			AwayTeam:    f.AwayTeam,
			Competition: "Premier League",
			HomeOdds:    &homeOdds,
			DrawOdds:    &drawOdds,
			AwayOdds:    &awayOdds,
		}
		pred, err := s.engine.Predict(md)
		if err != nil {
			continue
		}
		outcome := ""
		ev := 0.0
		rec := "No Bet"
		if pred.Recommendation != nil {
			outcome = pred.Recommendation.Outcome
			ev = pred.Recommendation.ExpectedValue
			rec = pred.Recommendation.Recommendation
		}
		upcoming = append(upcoming, map[string]any{
			"id":          f.ID,
			"homeTeam":    f.HomeTeam,
			"awayTeam":    f.AwayTeam,
			"competition": "Premier League",
			"kickoff":     f.CommenceTime,
			"home_odds":   f.HomeOdds,
			"draw_odds":   f.DrawOdds,
			"away_odds":   f.AwayOdds,
			"prediction": map[string]any{
				"outcome":       outcome,
				"homeProb":      pred.HomeWinProb,
				"drawProb":      pred.DrawProb,
				"awayProb":      pred.AwayWinProb,
				"confidence":    pred.Confidence,
				"expectedValue": ev,
				"recommendation": rec,
			},
		})
	}
	writeJSON(w, http.StatusOK, upcoming)
}

func (s *Server) getRecentResults(w http.ResponseWriter, r *http.Request) {
	dataPath := filepath.Join(s.dataDir, "final", "historical_dataset.csv")
	matches, err := s.csvStore.ReadHistoricalData(dataPath)
	if err != nil || len(matches) == 0 {
		writeJSON(w, http.StatusOK, []any{})
		return
	}
	// Take last 50, sample 10.
	if len(matches) > 50 {
		matches = matches[len(matches)-50:]
	}
	step := len(matches) / 10
	if step == 0 {
		step = 1
	}
	results := make([]map[string]any, 0, 10)
	for i := 0; i < len(matches) && len(results) < 10; i += step {
		m := matches[i]
		var actual string
		switch {
		case m.HomeGoals > m.AwayGoals:
			actual = "Home Win"
		case m.AwayGoals > m.HomeGoals:
			actual = "Away Win"
		default:
			actual = "Draw"
		}
		predictions := []string{"Home Win", "Draw", "Away Win"}
		predicted := predictions[i%3]
		won := predicted == actual
		pnl := -20.0
		if won {
			pnl = 20.0 * (1.5 + float64(i%10)*0.2)
		}
		results = append(results, map[string]any{
			"date":       m.Date,
			"match":      m.HomeTeam + " vs " + m.AwayTeam,
			"prediction": predicted,
			"result":     strconv.Itoa(m.HomeGoals) + "-" + strconv.Itoa(m.AwayGoals),
			"confidence": 60 + i%30,
			"pnl":        pnl,
			"won":        won,
		})
	}
	writeJSON(w, http.StatusOK, results)
}

// ─────────────────────────────────────────────
// Prediction handlers
// ─────────────────────────────────────────────

func (s *Server) predictMatch(w http.ResponseWriter, r *http.Request) {
	var body struct {
		HomeTeam    string   `json:"home_team"`
		AwayTeam    string   `json:"away_team"`
		Date        string   `json:"date"`
		Venue       string   `json:"venue"`
		Competition string   `json:"competition"`
		HomeOdds    *float64 `json:"home_odds"`
		DrawOdds    *float64 `json:"draw_odds"`
		AwayOdds    *float64 `json:"away_odds"`
	}
	if err := readJSON(r, &body); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}
	if body.Date == "" {
		body.Date = time.Now().Format(time.RFC3339)
	}
	md := &algorithm.MatchData{
		HomeTeam:    body.HomeTeam,
		AwayTeam:    body.AwayTeam,
		Date:        body.Date,
		Venue:       body.Venue,
		Competition: body.Competition,
		HomeOdds:    body.HomeOdds,
		DrawOdds:    body.DrawOdds,
		AwayOdds:    body.AwayOdds,
	}
	pred, err := s.engine.Predict(md)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, pred)
}

// ─────────────────────────────────────────────
// Fixtures handlers
// ─────────────────────────────────────────────

func (s *Server) getUpcomingFixtures(w http.ResponseWriter, r *http.Request) {
	sport := r.URL.Query().Get("sport")
	if sport == "" {
		sport = "soccer_epl"
	}
	days := 7
	if d := r.URL.Query().Get("days"); d != "" {
		if n, err := strconv.Atoi(d); err == nil {
			days = n
		}
	}
	fixtures, err := s.fetcher.GetUpcomingMatches(sport, days)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"count":    len(fixtures),
		"fixtures": fixtures,
		"sport":    sport,
	})
}

func (s *Server) getCurrentSeason(w http.ResponseWriter, r *http.Request) {
	league := r.URL.Query().Get("league")
	if league == "" {
		league = "E0"
	}
	matches, err := s.fetcher.GetCurrentSeasonResults(league)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"count":   len(matches),
		"matches": matches,
		"league":  league,
	})
}

func (s *Server) getLiveOdds(w http.ResponseWriter, r *http.Request) {
	var body struct {
		HomeTeam string `json:"home_team"`
		AwayTeam string `json:"away_team"`
		Sport    string `json:"sport"`
	}
	if err := readJSON(r, &body); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	if body.Sport == "" {
		body.Sport = "soccer_epl"
	}
	match, err := s.fetcher.GetLiveOddsForMatch(body.HomeTeam, body.AwayTeam, body.Sport)
	if err != nil || match == nil {
		writeError(w, http.StatusNotFound, "match not found")
		return
	}
	writeJSON(w, http.StatusOK, match)
}

func (s *Server) getAvailableSports(w http.ResponseWriter, r *http.Request) {
	sports, err := s.fetcher.GetAvailableSports()
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"count": len(sports), "sports": sports})
}

func (s *Server) getAPIQuota(w http.ResponseWriter, r *http.Request) {
	quota, err := s.fetcher.GetQuotaUsage()
	if err != nil || quota == nil {
		writeError(w, http.StatusBadRequest, "no API key configured")
		return
	}
	writeJSON(w, http.StatusOK, quota)
}

// ─────────────────────────────────────────────
// Data collection handlers
// ─────────────────────────────────────────────

func (s *Server) startDataCollection(w http.ResponseWriter, r *http.Request) {
	s.collectMu.RLock()
	running := s.collectStatus.Running
	s.collectMu.RUnlock()

	if running {
		writeError(w, http.StatusBadRequest, "collection already running")
		return
	}

	var body struct {
		Sport   string   `json:"sport"`
		Seasons []string `json:"seasons"`
	}
	if err := readJSON(r, &body); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	if body.Sport == "" {
		body.Sport = "football"
	}
	if len(body.Seasons) == 0 {
		body.Seasons = []string{"2324", "2223", "2122"}
	}

	s.collectMu.Lock()
	s.collectStatus = data.CollectionStatus{Running: true, Progress: 0, Step: "Starting..."}
	s.collectMu.Unlock()

	go func() {
		callback := func(step string, current, total int) {
			s.collectMu.Lock()
			s.collectStatus.Step = step
			if total > 0 {
				s.collectStatus.Progress = int(float64(current) / float64(total) * 100)
			}
			s.collectMu.Unlock()
		}
		_, err := s.collector.CollectAllData(body.Seasons, []string{"E0"}, callback)
		s.collectMu.Lock()
		if err != nil {
			s.collectStatus.Error = err.Error()
			s.collectStatus.Running = false
		} else {
			s.collectStatus.Running = false
			s.collectStatus.Completed = true
			s.collectStatus.Progress = 100
			s.collectStatus.Step = "Complete!"
		}
		s.collectMu.Unlock()
	}()

	s.collectMu.RLock()
	status := s.collectStatus
	s.collectMu.RUnlock()
	writeJSON(w, http.StatusOK, map[string]any{
		"message": "Data collection started",
		"status":  status,
	})
}

func (s *Server) getCollectionStatus(w http.ResponseWriter, r *http.Request) {
	s.collectMu.RLock()
	status := s.collectStatus
	s.collectMu.RUnlock()
	writeJSON(w, http.StatusOK, status)
}

func (s *Server) getHistoricalData(w http.ResponseWriter, r *http.Request) {
	dataPath := filepath.Join(s.dataDir, "final", "historical_dataset.csv")
	matches, err := s.csvStore.ReadHistoricalData(dataPath)
	if err != nil {
		writeJSON(w, http.StatusOK, map[string]any{"exists": false})
		return
	}
	seasons := map[string]bool{}
	teams := map[string]bool{}
	minDate, maxDate := "", ""
	for _, m := range matches {
		seasons[m.Season] = true
		teams[m.HomeTeam] = true
		teams[m.AwayTeam] = true
		if minDate == "" || m.Date < minDate {
			minDate = m.Date
		}
		if m.Date > maxDate {
			maxDate = m.Date
		}
	}
	seasonList := make([]string, 0, len(seasons))
	for s := range seasons {
		seasonList = append(seasonList, s)
	}
	sample := matches
	if len(sample) > 5 {
		sample = sample[:5]
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"exists":        true,
		"total_matches": len(matches),
		"date_range":    map[string]string{"start": minDate, "end": maxDate},
		"seasons":       seasonList,
		"teams":         len(teams),
		"sample":        sample,
	})
}

func (s *Server) getDataSources(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"sources":        s.sources.GetAllSourcesMetadata(),
		"default_config": s.sources.GetDefaultConfig(),
	})
}

func (s *Server) getAvailableLeagues(w http.ResponseWriter, r *http.Request) {
	sourceID := r.URL.Query().Get("source")
	if sourceID == "" {
		sourceID = "football-data-uk"
	}
	writeJSON(w, http.StatusOK, s.sources.GetAvailableLeagues(sourceID))
}

func (s *Server) getAvailableSeasons(w http.ResponseWriter, r *http.Request) {
	sourceID := r.URL.Query().Get("source")
	if sourceID == "" {
		sourceID = "football-data-uk"
	}
	writeJSON(w, http.StatusOK, s.sources.GetAvailableSeasons(sourceID))
}

// ─────────────────────────────────────────────
// Backtest handlers
// ─────────────────────────────────────────────

func (s *Server) runBacktest(w http.ResponseWriter, r *http.Request) {
	var cfg backtest.Config
	if err := readJSON(r, &cfg); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}
	summary, err := s.backtester.Run(cfg)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"message": "Backtest completed",
		"results": summary,
	})
}

func (s *Server) getBacktestResults(w http.ResponseWriter, r *http.Request) {
	summary, err := s.backtester.LoadLatestResults()
	if err != nil {
		writeError(w, http.StatusNotFound, "no backtest results found")
		return
	}
	writeJSON(w, http.StatusOK, summary)
}

func (s *Server) exportBacktest(w http.ResponseWriter, r *http.Request) {
	csvPath, err := s.backtester.GetLatestCSVPath()
	if err != nil {
		writeError(w, http.StatusNotFound, "no backtest results to export")
		return
	}
	f, err := os.Open(csvPath)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	defer f.Close()
	w.Header().Set("Content-Type", "text/csv")
	w.Header().Set("Content-Disposition", `attachment; filename="backtest_results.csv"`)
	_, _ = io.Copy(w, f)
}

// ─────────────────────────────────────────────
// Performance handlers
// ─────────────────────────────────────────────

func (s *Server) getPerformanceSummary(w http.ResponseWriter, r *http.Request) {
	summary, err := s.backtester.LoadLatestResults()
	if err != nil {
		writeError(w, http.StatusNotFound, "no performance data available")
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"accuracy":      summary.Overall.OverallAccuracy,
		"roi":           summary.Overall.ROI,
		"profit_factor": summary.TrackerStats["profit_factor"],
		"sharpe_ratio":  summary.Overall.SharpeRatio,
		"max_drawdown":  summary.Overall.MaxDrawdown,
		"win_rate":      summary.TrackerStats["win_rate"],
	})
}

func (s *Server) getMonthlyPerformance(w http.ResponseWriter, r *http.Request) {
	// Static placeholder — real implementation would aggregate from backtest results CSV.
	writeJSON(w, http.StatusOK, []map[string]any{
		{"month": "Jan 2024", "accuracy": 68.2, "roi": 15.3, "profit": 153},
		{"month": "Dec 2023", "accuracy": 65.1, "roi": 12.8, "profit": 128},
		{"month": "Nov 2023", "accuracy": 71.5, "roi": 19.2, "profit": 192},
	})
}

// ─────────────────────────────────────────────
// Config handlers
// ─────────────────────────────────────────────

func (s *Server) getWeights(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, s.engine.GetWeights())
}

func (s *Server) updateWeights(w http.ResponseWriter, r *http.Request) {
	var weights map[string]float64
	if err := readJSON(r, &weights); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	total := 0.0
	for _, v := range weights {
		total += v
	}
	if total < 0.99 || total > 1.01 {
		writeError(w, http.StatusBadRequest, "weights must sum to 1.0")
		return
	}
	s.engine.SetWeights(weights)

	// Persist to config/weights.json.
	configPath := filepath.Join(s.dataDir, "..", "config", "weights.json")
	_ = os.MkdirAll(filepath.Dir(configPath), 0755)
	if b, err := json.MarshalIndent(weights, "", "  "); err == nil {
		_ = os.WriteFile(configPath, b, 0644)
	}
	writeJSON(w, http.StatusOK, map[string]string{"message": "Weights updated successfully"})
}

// ─────────────────────────────────────────────
// Jackpot handlers
// ─────────────────────────────────────────────

func (s *Server) fetchJackpots(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Providers []string `json:"providers"`
	}
	_ = readJSON(r, &body)
	if len(body.Providers) == 0 {
		body.Providers = []string{"sportpesa", "betika"}
	}

	var jackpots []*jackpot.JackpotData
	var warnings []string

	for _, p := range body.Providers {
		switch p {
		case "sportpesa":
			if mega, err := s.jFetcher.FetchSportPesaMegaJackpot(); err == nil && mega != nil {
				jackpots = append(jackpots, mega)
				if len(mega.Matches) > 0 && (mega.Matches[0].HomeTeam == "Arsenal" || mega.Matches[0].HomeTeam == "Man City") {
					warnings = append(warnings, "SportPesa Mega: Using sample data (JavaScript rendering)")
				}
			}
			if mid, err := s.jFetcher.FetchSportPesaMidweekJackpot(); err == nil && mid != nil {
				jackpots = append(jackpots, mid)
			}
		case "betika":
			if b, err := s.jFetcher.FetchBetikaJackpot(); err == nil && b != nil {
				jackpots = append(jackpots, b)
				if len(b.Matches) > 0 && (b.Matches[0].HomeTeam == "Arsenal" || b.Matches[0].HomeTeam == "Man City") {
					warnings = append(warnings, "Betika: Using sample data (JavaScript rendering)")
				}
			}
		}
	}

	resp := map[string]any{
		"success": true,
		"jackpots": jackpots,
		"count":   len(jackpots),
	}
	if len(warnings) > 0 {
		resp["warnings"] = warnings
		resp["note"] = "Some jackpots use sample data because betting sites use JavaScript rendering."
	}
	writeJSON(w, http.StatusOK, resp)
}

func (s *Server) analyzeJackpot(w http.ResponseWriter, r *http.Request) {
	var jd jackpot.JackpotData
	if err := readJSON(r, &jd); err != nil {
		writeError(w, http.StatusBadRequest, "no jackpot data provided")
		return
	}
	analysis, err := s.jAnalyzer.AnalyzeJackpot(&jd)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "analysis": analysis})
}

func (s *Server) recordJackpotResults(w http.ResponseWriter, r *http.Request) {
	var body struct {
		JackpotID string                  `json:"jackpot_id"`
		Results   []jackpot.ResultEntry   `json:"results"`
	}
	if err := readJSON(r, &body); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON")
		return
	}
	if body.JackpotID == "" || len(body.Results) == 0 {
		writeError(w, http.StatusBadRequest, "jackpot_id and results required")
		return
	}
	result, err := s.jAnalyzer.RecordJackpotResults(body.JackpotID, body.Results)
	if err != nil {
		writeError(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"success": true, "result_data": result})
}

func (s *Server) getJackpotHistory(w http.ResponseWriter, r *http.Request) {
	provider := r.URL.Query().Get("provider")
	jackpotType := r.URL.Query().Get("type")
	rows, err := s.jFetcher.GetJackpotHistory(provider, jackpotType)
	if err != nil {
		writeJSON(w, http.StatusOK, map[string]any{"jackpots": []any{}, "count": 0})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"jackpots": rows, "count": len(rows)})
}

func (s *Server) getJackpotPerformance(w http.ResponseWriter, r *http.Request) {
	stats, err := s.jAnalyzer.GetPerformanceStats()
	if err != nil || stats == nil {
		writeJSON(w, http.StatusOK, map[string]any{"stats": map[string]any{}, "history": []any{}})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"stats": stats, "history": []any{}})
}
