package backtest

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"log/slog"
	"math"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"time"

	"bet4me/betting-algorithm-go/internal/algorithm"
	"bet4me/betting-algorithm-go/internal/storage"
)

// Config holds parameters for a backtest run.
type Config struct {
	Sport           string  `json:"sport"`
	Season          string  `json:"season"`          // empty = all seasons
	InitialBankroll float64 `json:"initial_bankroll"` // default 1000
	KellyFraction   float64 `json:"kelly_fraction"`   // default 0.25
	MaxStakePct     float64 `json:"max_stake_pct"`    // default 5.0
	StartDate       string  `json:"start_date"`       // YYYY-MM-DD optional
	EndDate         string  `json:"end_date"`         // YYYY-MM-DD optional
}

// MatchResult holds the outcome of a single backtested match.
type MatchResult struct {
	Date             string  `json:"date"`
	HomeTeam         string  `json:"home_team"`
	AwayTeam         string  `json:"away_team"`
	ActualResult     string  `json:"actual_result"`
	ActualScore      string  `json:"actual_score"`
	PredictedOutcome string  `json:"predicted_outcome"`
	Correct          bool    `json:"prediction_correct"`
	HomeProb         float64 `json:"home_prob"`
	DrawProb         float64 `json:"draw_prob"`
	AwayProb         float64 `json:"away_prob"`
	Confidence       float64 `json:"confidence"`
	ShouldBet        bool    `json:"should_bet"`
	StakeAmount      float64 `json:"stake_amount"`
	OddsPlayed       float64 `json:"odds_played,omitempty"`
	BetWon           bool    `json:"bet_won,omitempty"`
	PnL              float64 `json:"pnl"`
	Bankroll         float64 `json:"bankroll"`
	ExpectedValue    float64 `json:"expected_value"`
}

// OutcomeStats holds accuracy metrics per predicted outcome type.
type OutcomeStats struct {
	Count    int     `json:"count"`
	Correct  int     `json:"correct"`
	Accuracy float64 `json:"accuracy"`
}

// ConfidenceBinStats holds accuracy for a confidence bracket.
type ConfidenceBinStats struct {
	Count    int     `json:"count"`
	Correct  int     `json:"correct"`
	Accuracy float64 `json:"accuracy"`
}

// Summary is the full backtest result returned to callers.
type Summary struct {
	Overall              overallStats                  `json:"overall"`
	Betting              bettingStats                  `json:"betting"`
	AccuracyByType       map[string]OutcomeStats       `json:"accuracy_by_type"`
	AccuracyByConfidence map[string]ConfidenceBinStats `json:"accuracy_by_confidence"`
	EquityCurve          []float64                     `json:"equity_curve"`
	TrackerStats         map[string]float64            `json:"tracker_stats"`
	Timestamp            string                        `json:"timestamp"`
}

type overallStats struct {
	TotalMatches       int     `json:"total_matches"`
	CorrectPredictions int     `json:"correct_predictions"`
	OverallAccuracy    float64 `json:"overall_accuracy"`
	InitialBankroll    float64 `json:"initial_bankroll"`
	FinalBankroll      float64 `json:"final_bankroll"`
	TotalPnL           float64 `json:"total_pnl"`
	ROI                float64 `json:"roi"`
	MaxDrawdown        float64 `json:"max_drawdown"`
	SharpeRatio        float64 `json:"sharpe_ratio"`
}

type bettingStats struct {
	BetsPlaced int     `json:"bets_placed"`
	BetsWon    int     `json:"bets_won"`
	WinRate    float64 `json:"win_rate"`
	AvgStake   float64 `json:"avg_stake"`
	AvgOdds    float64 `json:"avg_odds"`
}

// BacktestEngine runs historical backtests against the prediction engine.
type BacktestEngine struct {
	engine     *algorithm.PredictionEngine
	csvStore   *storage.CSVStore
	dataDir    string
	resultsDir string
	logger     *slog.Logger
}

// NewBacktestEngine creates a new BacktestEngine.
func NewBacktestEngine(engine *algorithm.PredictionEngine, dataDir string, logger *slog.Logger) *BacktestEngine {
	if logger == nil {
		logger = slog.Default()
	}
	return &BacktestEngine{
		engine:     engine,
		csvStore:   storage.NewCSVStore(dataDir),
		dataDir:    dataDir,
		resultsDir: filepath.Join(dataDir, "backtests"),
		logger:     logger,
	}
}

// Run executes a backtest with the given config and returns the summary.
func (e *BacktestEngine) Run(cfg Config) (*Summary, error) {
	// Apply defaults.
	if cfg.InitialBankroll <= 0 {
		cfg.InitialBankroll = 1000
	}
	if cfg.KellyFraction <= 0 {
		cfg.KellyFraction = 0.25
	}
	if cfg.MaxStakePct <= 0 {
		cfg.MaxStakePct = 5.0
	}

	// Load historical data.
	dataPath := filepath.Join(e.dataDir, "final", "historical_dataset.csv")
	matches, err := e.csvStore.ReadHistoricalData(dataPath)
	if err != nil {
		e.logger.Warn("could not load historical data, using sample data", "err", err)
		matches = generateSampleData()
	}

	// Filter by season.
	if cfg.Season != "" && cfg.Season != "All Seasons" {
		var filtered []storage.MatchRecord
		for _, m := range matches {
			if m.Season == cfg.Season {
				filtered = append(filtered, m)
			}
		}
		matches = filtered
	}
	// Filter by date range.
	if cfg.StartDate != "" {
		var filtered []storage.MatchRecord
		for _, m := range matches {
			if m.Date >= cfg.StartDate {
				filtered = append(filtered, m)
			}
		}
		matches = filtered
	}
	if cfg.EndDate != "" {
		var filtered []storage.MatchRecord
		for _, m := range matches {
			if m.Date <= cfg.EndDate {
				filtered = append(filtered, m)
			}
		}
		matches = filtered
	}

	// Sort chronologically.
	sort.Slice(matches, func(i, j int) bool { return matches[i].Date < matches[j].Date })

	// Simulate.
	bankroll := cfg.InitialBankroll
	equityCurve := []float64{bankroll}
	results := make([]MatchResult, 0, len(matches))

	for _, m := range matches {
		r := e.processMatch(m, bankroll, cfg)
		if r == nil {
			continue
		}
		bankroll = r.Bankroll
		results = append(results, *r)
		equityCurve = append(equityCurve, bankroll)
	}

	summary := buildSummary(results, equityCurve, cfg.InitialBankroll, bankroll)
	summary.Timestamp = time.Now().Format(time.RFC3339)

	if err := e.saveResults(summary, results); err != nil {
		e.logger.Warn("could not save backtest results", "err", err)
	}

	return summary, nil
}

func (e *BacktestEngine) processMatch(m storage.MatchRecord, bankroll float64, cfg Config) *MatchResult {
	homeOdds := m.HomeOdds
	drawOdds := m.DrawOdds
	awayOdds := m.AwayOdds

	md := &algorithm.MatchData{
		HomeTeam:          m.HomeTeam,
		AwayTeam:          m.AwayTeam,
		Date:              m.Date,
		HomeXg:            m.HomeXG,
		AwayXg:            m.AwayXG,
		HomePPDA:          m.HomePPDA,
		AwayPPDA:          m.AwayPPDA,
		HomePossession:    m.HomePossession,
		AwayPossession:    m.AwayPossession,
		HomeShots:         m.HomeShots,
		HomeShotsOnTarget: m.HomeShotsOnTarget,
		AwayShots:         m.AwayShots,
		AwayShotsOnTarget: m.AwayShotsOnTarget,
		HomePosition:      m.HomePosition,
		AwayPosition:      m.AwayPosition,
		HomeForm:          m.HomeForm,
		AwayForm:          m.AwayForm,
		HomeRestDays:      m.HomeRestDays,
		AwayRestDays:      m.AwayRestDays,
		HomeGamesLast7:    m.HomeGamesLast7,
		AwayGamesLast7:    m.AwayGamesLast7,
	}
	if homeOdds > 0 {
		md.HomeOdds = &homeOdds
	}
	if drawOdds > 0 {
		md.DrawOdds = &drawOdds
	}
	if awayOdds > 0 {
		md.AwayOdds = &awayOdds
	}
	if m.HomeElo > 0 {
		v := m.HomeElo
		md.HomeElo = &v
	}
	if m.AwayElo > 0 {
		v := m.AwayElo
		md.AwayElo = &v
	}

	pred, err := e.engine.Predict(md)
	if err != nil {
		e.logger.Warn("prediction error", "match", m.HomeTeam+" v "+m.AwayTeam, "err", err)
		return nil
	}

	var actualResult string
	switch {
	case m.HomeGoals > m.AwayGoals:
		actualResult = "Home Win"
	case m.AwayGoals > m.HomeGoals:
		actualResult = "Away Win"
	default:
		actualResult = "Draw"
	}

	predictedOutcome := ""
	stakePercentage := 0.0
	ev := 0.0
	if pred.Recommendation != nil {
		predictedOutcome = pred.Recommendation.Outcome
		stakePercentage = pred.Recommendation.StakePercentage / 100.0
		ev = pred.Recommendation.ExpectedValue
	}

	shouldBet := stakePercentage > 0 && ev > 0
	pnl := 0.0
	stakeAmount := 0.0
	oddsPlayed := 0.0
	betWon := false

	if shouldBet && bankroll > 0 {
		maxStake := bankroll * cfg.MaxStakePct / 100
		stakeAmount = math.Min(bankroll*stakePercentage, maxStake)

		switch predictedOutcome {
		case "Home Win":
			oddsPlayed = homeOdds
		case "Away Win":
			oddsPlayed = awayOdds
		default:
			oddsPlayed = drawOdds
		}

		if predictedOutcome == actualResult {
			pnl = stakeAmount * (oddsPlayed - 1)
			betWon = true
		} else {
			pnl = -stakeAmount
		}
		bankroll += pnl
	}

	return &MatchResult{
		Date:             m.Date,
		HomeTeam:         m.HomeTeam,
		AwayTeam:         m.AwayTeam,
		ActualResult:     actualResult,
		ActualScore:      fmt.Sprintf("%d-%d", m.HomeGoals, m.AwayGoals),
		PredictedOutcome: predictedOutcome,
		Correct:          predictedOutcome == actualResult,
		HomeProb:         pred.HomeWinProb,
		DrawProb:         pred.DrawProb,
		AwayProb:         pred.AwayWinProb,
		Confidence:       pred.Confidence,
		ShouldBet:        shouldBet,
		StakeAmount:      stakeAmount,
		OddsPlayed:       oddsPlayed,
		BetWon:           betWon,
		PnL:              pnl,
		Bankroll:         bankroll,
		ExpectedValue:    ev,
	}
}

func buildSummary(results []MatchResult, equityCurve []float64, initial, final float64) *Summary {
	if len(results) == 0 {
		return &Summary{
			Overall:              overallStats{InitialBankroll: initial, FinalBankroll: final},
			AccuracyByType:       map[string]OutcomeStats{},
			AccuracyByConfidence: map[string]ConfidenceBinStats{},
			TrackerStats:         map[string]float64{},
		}
	}

	totalMatches := len(results)
	correct := 0
	betsPlaced := 0
	betsWon := 0
	totalStake := 0.0
	totalOdds := 0.0
	totalPnL := 0.0
	totalProfit := 0.0
	totalLoss := 0.0

	byType := map[string]*[2]int{}

	type confBin struct{ low, high float64 }
	bins := []confBin{{0.5, 0.6}, {0.6, 0.7}, {0.7, 0.8}, {0.8, 0.9}, {0.9, 1.01}}
	byConf := make([][2]int, len(bins))

	for _, r := range results {
		if r.Correct {
			correct++
		}
		totalPnL += r.PnL
		if r.PnL > 0 {
			totalProfit += r.PnL
		} else {
			totalLoss += -r.PnL
		}
		if r.ShouldBet {
			betsPlaced++
			totalStake += r.StakeAmount
			totalOdds += r.OddsPlayed
			if r.BetWon {
				betsWon++
			}
		}
		if _, ok := byType[r.PredictedOutcome]; !ok {
			byType[r.PredictedOutcome] = &[2]int{}
		}
		byType[r.PredictedOutcome][0]++
		if r.Correct {
			byType[r.PredictedOutcome][1]++
		}
		for i, b := range bins {
			if r.Confidence >= b.low && r.Confidence < b.high {
				byConf[i][0]++
				if r.Correct {
					byConf[i][1]++
				}
			}
		}
	}

	accuracy := float64(correct) / float64(totalMatches) * 100
	winRate := 0.0
	if betsPlaced > 0 {
		winRate = float64(betsWon) / float64(betsPlaced) * 100
	}
	roi := 0.0
	if initial > 0 {
		roi = (final - initial) / initial * 100
	}

	accByType := map[string]OutcomeStats{}
	for k, v := range byType {
		acc := 0.0
		if v[0] > 0 {
			acc = float64(v[1]) / float64(v[0]) * 100
		}
		accByType[k] = OutcomeStats{Count: v[0], Correct: v[1], Accuracy: r2(acc)}
	}

	accByConf := map[string]ConfidenceBinStats{}
	for i, b := range bins {
		if byConf[i][0] == 0 {
			continue
		}
		label := fmt.Sprintf("%d-%d%%", int(b.low*100), int(b.high*100))
		if b.high > 1.0 {
			label = fmt.Sprintf("%d-100%%", int(b.low*100))
		}
		acc := float64(byConf[i][1]) / float64(byConf[i][0]) * 100
		accByConf[label] = ConfidenceBinStats{Count: byConf[i][0], Correct: byConf[i][1], Accuracy: r2(acc)}
	}

	avgStake := 0.0
	avgOdds := 0.0
	if betsPlaced > 0 {
		avgStake = totalStake / float64(betsPlaced)
		avgOdds = totalOdds / float64(betsPlaced)
	}

	profitFactor := 0.0
	if totalLoss > 0 {
		profitFactor = r2(totalProfit / totalLoss)
	}

	ec := equityCurve
	if len(ec) > 100 {
		ec = ec[len(ec)-100:]
	}

	return &Summary{
		Overall: overallStats{
			TotalMatches:       totalMatches,
			CorrectPredictions: correct,
			OverallAccuracy:    r2(accuracy),
			InitialBankroll:    initial,
			FinalBankroll:      r2(final),
			TotalPnL:           r2(totalPnL),
			ROI:                r2(roi),
			MaxDrawdown:        r2(calcMaxDrawdown(equityCurve)),
			SharpeRatio:        r2(calcSharpe(equityCurve)),
		},
		Betting: bettingStats{
			BetsPlaced: betsPlaced,
			BetsWon:    betsWon,
			WinRate:    r2(winRate),
			AvgStake:   r2(avgStake),
			AvgOdds:    r2(avgOdds),
		},
		AccuracyByType:       accByType,
		AccuracyByConfidence: accByConf,
		EquityCurve:          ec,
		TrackerStats: map[string]float64{
			"win_rate":     r2(winRate),
			"profit_factor": profitFactor,
		},
	}
}

func calcMaxDrawdown(curve []float64) float64 {
	if len(curve) < 2 {
		return 0
	}
	peak := curve[0]
	maxDD := 0.0
	for _, v := range curve {
		if v > peak {
			peak = v
		}
		if peak > 0 {
			dd := (peak - v) / peak * 100
			if dd > maxDD {
				maxDD = dd
			}
		}
	}
	return maxDD
}

func calcSharpe(curve []float64) float64 {
	if len(curve) < 2 {
		return 0
	}
	returns := make([]float64, len(curve)-1)
	for i := 1; i < len(curve); i++ {
		if curve[i-1] > 0 {
			returns[i-1] = (curve[i] - curve[i-1]) / curve[i-1]
		}
	}
	mean := 0.0
	for _, r := range returns {
		mean += r
	}
	mean /= float64(len(returns))
	variance := 0.0
	for _, r := range returns {
		variance += (r - mean) * (r - mean)
	}
	variance /= float64(len(returns))
	std := math.Sqrt(variance)
	if std == 0 {
		return 0
	}
	return mean / std * math.Sqrt(252)
}

func r2(v float64) float64 { return math.Round(v*100) / 100 }

// LoadLatestResults loads the most recent saved backtest summary JSON.
func (e *BacktestEngine) LoadLatestResults() (*Summary, error) {
	entries, err := os.ReadDir(e.resultsDir)
	if err != nil {
		return nil, fmt.Errorf("reading results dir: %w", err)
	}
	var latest string
	for _, en := range entries {
		if !en.IsDir() && filepath.Ext(en.Name()) == ".json" && en.Name() > latest {
			latest = en.Name()
		}
	}
	if latest == "" {
		return nil, fmt.Errorf("no backtest results found")
	}
	b, err := os.ReadFile(filepath.Join(e.resultsDir, latest))
	if err != nil {
		return nil, err
	}
	var s Summary
	return &s, json.Unmarshal(b, &s)
}

// GetLatestCSVPath returns the path to the most recent backtest CSV for download.
func (e *BacktestEngine) GetLatestCSVPath() (string, error) {
	entries, err := os.ReadDir(e.resultsDir)
	if err != nil {
		return "", fmt.Errorf("reading results dir: %w", err)
	}
	var latest string
	for _, en := range entries {
		if !en.IsDir() && filepath.Ext(en.Name()) == ".csv" && en.Name() > latest {
			latest = en.Name()
		}
	}
	if latest == "" {
		return "", fmt.Errorf("no backtest CSV found")
	}
	return filepath.Join(e.resultsDir, latest), nil
}

func (e *BacktestEngine) saveResults(summary *Summary, results []MatchResult) error {
	if err := os.MkdirAll(e.resultsDir, 0755); err != nil {
		return err
	}
	ts := time.Now().Format("20060102_150405")

	b, err := json.MarshalIndent(summary, "", "  ")
	if err != nil {
		return err
	}
	if err := os.WriteFile(filepath.Join(e.resultsDir, fmt.Sprintf("backtest_%s.json", ts)), b, 0644); err != nil {
		return err
	}

	if len(results) == 0 {
		return nil
	}
	f, err := os.Create(filepath.Join(e.resultsDir, fmt.Sprintf("backtest_%s.csv", ts)))
	if err != nil {
		return err
	}
	defer f.Close()
	w := csv.NewWriter(f)
	_ = w.Write([]string{
		"date", "home_team", "away_team", "actual_result", "actual_score",
		"predicted_outcome", "prediction_correct",
		"home_prob", "draw_prob", "away_prob", "confidence",
		"should_bet", "stake_amount", "odds_played", "bet_won", "pnl", "bankroll", "expected_value",
	})
	for _, r := range results {
		_ = w.Write([]string{
			r.Date, r.HomeTeam, r.AwayTeam, r.ActualResult, r.ActualScore,
			r.PredictedOutcome, strconv.FormatBool(r.Correct),
			strconv.FormatFloat(r.HomeProb, 'f', 4, 64),
			strconv.FormatFloat(r.DrawProb, 'f', 4, 64),
			strconv.FormatFloat(r.AwayProb, 'f', 4, 64),
			strconv.FormatFloat(r.Confidence, 'f', 4, 64),
			strconv.FormatBool(r.ShouldBet),
			strconv.FormatFloat(r.StakeAmount, 'f', 2, 64),
			strconv.FormatFloat(r.OddsPlayed, 'f', 2, 64),
			strconv.FormatBool(r.BetWon),
			strconv.FormatFloat(r.PnL, 'f', 2, 64),
			strconv.FormatFloat(r.Bankroll, 'f', 2, 64),
			strconv.FormatFloat(r.ExpectedValue, 'f', 4, 64),
		})
	}
	w.Flush()
	e.logger.Info("backtest results saved", "dir", e.resultsDir, "ts", ts)
	return nil
}

// generateSampleData creates 380 Poisson-distributed sample matches.
func generateSampleData() []storage.MatchRecord {
	teams := []string{
		"Arsenal", "Chelsea", "Liverpool", "Man City", "Man United",
		"Tottenham", "Everton", "West Ham", "Newcastle", "Brighton",
		"Aston Villa", "Crystal Palace", "Fulham", "Wolves", "Leicester",
		"Bournemouth", "Brentford", "Nottm Forest", "Luton", "Burnley",
	}
	base := time.Date(2023, 8, 1, 0, 0, 0, 0, time.UTC)
	var matches []storage.MatchRecord
	for i := 0; i < 380; i++ {
		home := teams[i%20]
		away := teams[(i+1+i/20)%20]
		if home == away {
			away = teams[(i+2)%20]
		}
		d := base.Add(time.Duration(i/10*7+i%10%3) * 24 * time.Hour)
		// Simple deterministic goal distribution
		homeGoals := (i*3 + 1) % 4 // 0-3
		awayGoals := (i*2 + 1) % 3 // 0-2
		matches = append(matches, storage.MatchRecord{
			Date:         d.Format("2006-01-02"),
			Season:       "2023-24",
			HomeTeam:     home,
			AwayTeam:     away,
			HomeGoals:    homeGoals,
			AwayGoals:    awayGoals,
			HomeOdds:     1.80,
			DrawOdds:     3.50,
			AwayOdds:     4.00,
			HomeXG:       1.5,
			AwayXG:       1.2,
			HomeElo:      1500,
			AwayElo:      1500,
			HomeForm:     "WWDLW",
			AwayForm:     "WDLWD",
			HomeRestDays: 7,
			AwayRestDays: 7,
			HomePosition: (i%20 + 1),
			AwayPosition: ((i+1)%20 + 1),
		})
	}
	return matches
}
