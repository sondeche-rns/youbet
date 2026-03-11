package jackpot

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"strconv"
	"time"

	"bet4me/betting-algorithm-go/internal/algorithm"
	"bet4me/betting-algorithm-go/internal/domain"
)

// MatchPrediction holds the algorithm's output for one jackpot match.
type MatchPrediction struct {
	MatchNumber    int     `json:"match_number"`
	HomeTeam       string  `json:"home_team"`
	AwayTeam       string  `json:"away_team"`
	Prediction     string  `json:"prediction"`   // "Home" | "Draw" | "Away"
	Confidence     float64 `json:"confidence"`
	HomeProb       float64 `json:"home_prob"`
	DrawProb       float64 `json:"draw_prob"`
	AwayProb       float64 `json:"away_prob"`
	Recommendation string  `json:"recommendation"`
	// Populated when results are recorded
	ActualResult string `json:"actual_result,omitempty"`
	Correct      *bool  `json:"correct,omitempty"`
	Error        string `json:"error,omitempty"`
}

// BettingCombination represents one betting strategy derived from the predictions.
type BettingCombination struct {
	Strategy           string   `json:"strategy"`
	Description        string   `json:"description"`
	Picks              []string `json:"picks,omitempty"`
	PredictedAccuracy  float64  `json:"predicted_accuracy,omitempty"`
	HighConfidencePicks []string `json:"high_confidence_picks,omitempty"`
	DrawCandidates     []string `json:"draw_candidates,omitempty"`
}

// JackpotAnalysis is the complete analysis output for one jackpot.
type JackpotAnalysis struct {
	JackpotID               string               `json:"jackpot_id"`
	Provider                string               `json:"provider"`
	Type                    string               `json:"type"`
	PrizeAmount             string               `json:"prize_amount,omitempty"`
	TotalMatches            int                  `json:"total_matches"`
	AnalyzedAt              string               `json:"analyzed_at"`
	Predictions             []MatchPrediction    `json:"predictions"`
	HighConfidenceCount     int                  `json:"high_confidence_count"`
	LowConfidenceCount      int                  `json:"low_confidence_count"`
	HighConfidencePicks     []MatchPrediction    `json:"high_confidence_picks"`
	LowConfidencePicks      []MatchPrediction    `json:"low_confidence_picks"`
	AverageConfidence       float64              `json:"average_confidence"`
	RecommendedCombinations []BettingCombination `json:"recommended_combinations"`
}

// ResultEntry records the actual outcome for one jackpot match.
type ResultEntry struct {
	MatchNumber  int    `json:"match_number"`
	ActualResult string `json:"actual_result"` // "Home" | "Draw" | "Away"
}

// JackpotResult is saved after actual results are known.
type JackpotResult struct {
	JackpotID              string            `json:"jackpot_id"`
	Provider               string            `json:"provider"`
	Type                   string            `json:"type"`
	RecordedAt             string            `json:"recorded_at"`
	TotalMatches           int               `json:"total_matches"`
	CorrectPredictions     int               `json:"correct_predictions"`
	Accuracy               float64           `json:"accuracy"`
	PredictionsWithResults []MatchPrediction `json:"predictions_with_results"`
}

// ProviderStats holds per-provider performance summary.
type ProviderStats struct {
	Count           int     `json:"count"`
	AverageAccuracy float64 `json:"average_accuracy"`
}

// PerformanceStats summarises all historical jackpot prediction performance.
type PerformanceStats struct {
	TotalJackpots   int                      `json:"total_jackpots"`
	AverageAccuracy float64                  `json:"average_accuracy"`
	BestAccuracy    float64                  `json:"best_accuracy"`
	WorstAccuracy   float64                  `json:"worst_accuracy"`
	ByProvider      map[string]ProviderStats `json:"by_provider"`
}

// JackpotAnalyzer generates predictions for jackpot matches and tracks performance.
type JackpotAnalyzer struct {
	engine         *algorithm.PredictionEngine
	predictionsDir string
	resultsDir     string
	logger         *slog.Logger
}

// NewJackpotAnalyzer creates a new JackpotAnalyzer.
//
//   - engine  fully-initialised PredictionEngine
//   - dataDir base data directory; sub-dirs jackpot_predictions/ and jackpot_results/ are created automatically
//   - logger  optional; defaults to slog.Default()
func NewJackpotAnalyzer(engine *algorithm.PredictionEngine, dataDir string, logger *slog.Logger) *JackpotAnalyzer {
	if logger == nil {
		logger = slog.Default()
	}
	return &JackpotAnalyzer{
		engine:         engine,
		predictionsDir: filepath.Join(dataDir, "jackpot_predictions"),
		resultsDir:     filepath.Join(dataDir, "jackpot_results"),
		logger:         logger,
	}
}

// AnalyzeJackpot runs predictions for every match in jackpotData and returns
// a full JackpotAnalysis with confidence buckets and betting combinations.
func (a *JackpotAnalyzer) AnalyzeJackpot(data *JackpotData) (*JackpotAnalysis, error) {
	a.logger.Info("Analyzing jackpot",
		"provider", data.Provider,
		"type", data.Type,
		"matches", len(data.Matches))

	now := time.Now()
	analysis := &JackpotAnalysis{
		JackpotID:   fmt.Sprintf("%s_%s_%s", data.Provider, data.Type, now.Format("20060102_150405")),
		Provider:    data.Provider,
		Type:        data.Type,
		PrizeAmount: data.PrizeAmount,
		AnalyzedAt:  now.Format(time.RFC3339),
	}

	var highConf, lowConf []MatchPrediction

	for _, m := range data.Matches {
		matchData := a.enrichMatchData(m)

		result, err := a.engine.Predict(&matchData)
		if err != nil {
			a.logger.Warn("Prediction failed", "match", m.MatchNumber,
				"home", m.HomeTeam, "away", m.AwayTeam, "error", err)
			analysis.Predictions = append(analysis.Predictions, MatchPrediction{
				MatchNumber: m.MatchNumber,
				HomeTeam:    m.HomeTeam,
				AwayTeam:    m.AwayTeam,
				Prediction:  "Error",
				Error:       err.Error(),
			})
			continue
		}

		pred := buildMatchPrediction(m, result)
		analysis.Predictions = append(analysis.Predictions, pred)

		if pred.Confidence > 0.75 {
			highConf = append(highConf, pred)
		} else if pred.Confidence < 0.55 {
			lowConf = append(lowConf, pred)
		}
	}

	analysis.TotalMatches = len(analysis.Predictions)
	analysis.HighConfidenceCount = len(highConf)
	analysis.LowConfidenceCount = len(lowConf)
	analysis.HighConfidencePicks = highConf
	analysis.LowConfidencePicks = lowConf
	analysis.AverageConfidence = averageConfidence(analysis.Predictions)
	analysis.RecommendedCombinations = a.generateCombinations(analysis.Predictions)

	if err := a.savePredictions(analysis); err != nil {
		a.logger.Warn("Could not save jackpot predictions", "error", err)
	}

	a.logger.Info("Jackpot analysis complete",
		"jackpot_id", analysis.JackpotID,
		"avg_confidence", fmt.Sprintf("%.1f%%", analysis.AverageConfidence*100),
		"high_conf", analysis.HighConfidenceCount,
		"low_conf", analysis.LowConfidenceCount)

	return analysis, nil
}

// RecordJackpotResults records actual match outcomes for a previously analyzed
// jackpot, computes accuracy, saves results JSON + master CSV, and returns the
// full result record.
func (a *JackpotAnalyzer) RecordJackpotResults(jackpotID string, results []ResultEntry) (*JackpotResult, error) {
	predFile := filepath.Join(a.predictionsDir, jackpotID+".json")
	raw, err := os.ReadFile(predFile)
	if err != nil {
		return nil, fmt.Errorf("reading predictions for %s: %w", jackpotID, err)
	}

	var analysis JackpotAnalysis
	if err := json.Unmarshal(raw, &analysis); err != nil {
		return nil, fmt.Errorf("parsing predictions JSON: %w", err)
	}

	// Build result lookup keyed by match number
	resultMap := make(map[int]string, len(results))
	for _, r := range results {
		resultMap[r.MatchNumber] = r.ActualResult
	}

	correct := 0
	for i := range analysis.Predictions {
		p := &analysis.Predictions[i]
		actual, ok := resultMap[p.MatchNumber]
		if !ok {
			continue
		}
		p.ActualResult = actual
		isCorrect := p.Prediction == actual
		p.Correct = &isCorrect
		if isCorrect {
			correct++
		}
	}

	total := len(results)
	accuracy := 0.0
	if total > 0 {
		accuracy = float64(correct) / float64(total)
	}

	jr := &JackpotResult{
		JackpotID:              jackpotID,
		Provider:               analysis.Provider,
		Type:                   analysis.Type,
		RecordedAt:             time.Now().Format(time.RFC3339),
		TotalMatches:           total,
		CorrectPredictions:     correct,
		Accuracy:               accuracy,
		PredictionsWithResults: analysis.Predictions,
	}

	resultFile := filepath.Join(a.resultsDir, jackpotID+"_results.json")
	if err := a.writeJSON(resultFile, jr); err != nil {
		return nil, fmt.Errorf("saving results: %w", err)
	}

	if err := a.appendToResultsCSV(jr); err != nil {
		a.logger.Warn("Could not append to results CSV", "error", err)
	}

	a.logger.Info("Results recorded",
		"jackpot_id", jackpotID,
		"correct", correct,
		"total", total,
		"accuracy", fmt.Sprintf("%.1f%%", accuracy*100))

	return jr, nil
}

// GetPerformanceStats reads the master results CSV and returns aggregated stats.
// Returns nil if no results have been recorded yet.
func (a *JackpotAnalyzer) GetPerformanceStats() (*PerformanceStats, error) {
	csvPath := filepath.Join(a.resultsDir, "jackpot_results_summary.csv")
	f, err := os.Open(csvPath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, fmt.Errorf("opening results CSV: %w", err)
	}
	defer f.Close()

	r := csv.NewReader(f)
	records, err := r.ReadAll()
	if err != nil {
		return nil, fmt.Errorf("reading results CSV: %w", err)
	}
	if len(records) < 2 {
		return nil, nil
	}

	header := records[0]
	idx := make(map[string]int, len(header))
	for i, h := range header {
		idx[h] = i
	}

	stats := &PerformanceStats{
		ByProvider:   make(map[string]ProviderStats),
		BestAccuracy: -1,
	}

	var totalAccuracy float64
	for _, rec := range records[1:] {
		if len(rec) < len(header) {
			continue
		}
		acc, _ := strconv.ParseFloat(safeGet(rec, idx, "accuracy"), 64)
		provider := safeGet(rec, idx, "provider")

		stats.TotalJackpots++
		totalAccuracy += acc

		if acc > stats.BestAccuracy {
			stats.BestAccuracy = acc
		}
		if stats.WorstAccuracy == 0 || acc < stats.WorstAccuracy {
			stats.WorstAccuracy = acc
		}

		ps := stats.ByProvider[provider]
		ps.Count++
		ps.AverageAccuracy += acc
		stats.ByProvider[provider] = ps
	}

	if stats.TotalJackpots > 0 {
		stats.AverageAccuracy = totalAccuracy / float64(stats.TotalJackpots)
		for k, ps := range stats.ByProvider {
			ps.AverageAccuracy /= float64(ps.Count)
			stats.ByProvider[k] = ps
		}
	}

	return stats, nil
}

// ─── private helpers ──────────────────────────────────────────────────────────

// enrichMatchData converts a raw JackpotMatch into a MatchData struct,
// looking up team stats from the domain.PremierLeagueTeams database.
// Falls back to neutral defaults for unknown teams.
func (a *JackpotAnalyzer) enrichMatchData(m JackpotMatch) algorithm.MatchData {
	md := algorithm.MatchData{
		HomeTeam:    m.HomeTeam,
		AwayTeam:    m.AwayTeam,
		Competition: m.Competition,
		Date:        m.Kickoff,
	}

	if homeData, _ := domain.LookupTeam(m.HomeTeam); homeData != nil {
		homeElo := float64(homeData.Elo)
		md.HomeElo = &homeElo
		md.HomePosition = homeData.Position
		md.HomeForm = homeData.Form
		md.HomeStarRating = homeData.Stars
		md.HomeXg = homeData.HomeXGAvg
		md.HomeStyle = string(homeData.Style)
	}

	if awayData, _ := domain.LookupTeam(m.AwayTeam); awayData != nil {
		awayElo := float64(awayData.Elo)
		md.AwayElo = &awayElo
		md.AwayPosition = awayData.Position
		md.AwayForm = awayData.Form
		md.AwayStarRating = awayData.Stars
		md.AwayXg = awayData.AwayXGAvg
		md.AwayStyle = string(awayData.Style)
	}

	// Pass through odds if provided by the jackpot source
	if m.HomeOdds > 0 {
		v := m.HomeOdds
		md.HomeOdds = &v
	}
	if m.DrawOdds > 0 {
		v := m.DrawOdds
		md.DrawOdds = &v
	}
	if m.AwayOdds > 0 {
		v := m.AwayOdds
		md.AwayOdds = &v
	}

	return md
}

// generateCombinations produces three betting strategies from a set of predictions:
//  1. Main Prediction — all matches with the highest-probability outcome
//  2. Conservative — high-confidence picks (>70%) only
//  3. Draw Value — matches where draw probability exceeds 30%
func (a *JackpotAnalyzer) generateCombinations(predictions []MatchPrediction) []BettingCombination {
	var combos []BettingCombination

	if len(predictions) == 0 {
		return combos
	}

	// Strategy 1: Main prediction (all matches)
	var mainPicks []string
	var mainAccSum float64
	for _, p := range predictions {
		mainPicks = append(mainPicks, fmt.Sprintf("%d: %s", p.MatchNumber, p.Prediction))
		best := max3(p.HomeProb, p.DrawProb, p.AwayProb)
		mainAccSum += best
	}
	combos = append(combos, BettingCombination{
		Strategy:          "Main Prediction",
		Description:       "All matches with highest probability outcome",
		Picks:             mainPicks,
		PredictedAccuracy: mainAccSum / float64(len(predictions)),
	})

	// Strategy 2: Conservative (high-confidence only)
	var highConf []MatchPrediction
	for _, p := range predictions {
		if p.Confidence > 0.70 {
			highConf = append(highConf, p)
		}
	}
	if len(highConf) > 0 {
		var confPicks []string
		var confSum float64
		for _, p := range highConf {
			confPicks = append(confPicks, fmt.Sprintf("%d: %s", p.MatchNumber, p.Prediction))
			confSum += max3(p.HomeProb, p.DrawProb, p.AwayProb)
		}
		combos = append(combos, BettingCombination{
			Strategy:           "Conservative",
			Description:        fmt.Sprintf("%d high confidence picks, others doubled", len(highConf)),
			HighConfidencePicks: confPicks,
			PredictedAccuracy:  confSum / float64(len(highConf)),
		})
	}

	// Strategy 3: Draw value (draw prob > 30%)
	var drawCandidates []string
	for _, p := range predictions {
		if p.DrawProb > 0.30 {
			drawCandidates = append(drawCandidates,
				fmt.Sprintf("%d: %s vs %s (%.1f%%)",
					p.MatchNumber, p.HomeTeam, p.AwayTeam, p.DrawProb*100))
		}
	}
	if len(drawCandidates) > 0 {
		combos = append(combos, BettingCombination{
			Strategy:       "Draw Value",
			Description:    fmt.Sprintf("%d matches with draw probability >30%%", len(drawCandidates)),
			DrawCandidates: drawCandidates,
		})
	}

	return combos
}

// savePredictions writes the analysis JSON and a companion CSV to predictionsDir.
func (a *JackpotAnalyzer) savePredictions(analysis *JackpotAnalysis) error {
	if err := os.MkdirAll(a.predictionsDir, 0o755); err != nil {
		return fmt.Errorf("creating predictions dir: %w", err)
	}

	jsonPath := filepath.Join(a.predictionsDir, analysis.JackpotID+".json")
	if err := a.writeJSON(jsonPath, analysis); err != nil {
		return err
	}

	return a.savePredictionsCSV(analysis)
}

// savePredictionsCSV writes the flat predictions slice as a CSV file.
func (a *JackpotAnalyzer) savePredictionsCSV(analysis *JackpotAnalysis) error {
	csvPath := filepath.Join(a.predictionsDir, analysis.JackpotID+".csv")
	f, err := os.Create(csvPath)
	if err != nil {
		return fmt.Errorf("creating predictions CSV: %w", err)
	}
	defer f.Close()

	w := csv.NewWriter(f)
	if err := w.Write([]string{
		"match_number", "home_team", "away_team",
		"prediction", "confidence", "home_prob", "draw_prob", "away_prob", "recommendation",
	}); err != nil {
		return err
	}

	for _, p := range analysis.Predictions {
		if err := w.Write([]string{
			strconv.Itoa(p.MatchNumber),
			p.HomeTeam,
			p.AwayTeam,
			p.Prediction,
			strconv.FormatFloat(p.Confidence, 'f', 4, 64),
			strconv.FormatFloat(p.HomeProb, 'f', 4, 64),
			strconv.FormatFloat(p.DrawProb, 'f', 4, 64),
			strconv.FormatFloat(p.AwayProb, 'f', 4, 64),
			p.Recommendation,
		}); err != nil {
			return err
		}
	}
	w.Flush()
	return w.Error()
}

// appendToResultsCSV appends one summary row to the master results CSV.
func (a *JackpotAnalyzer) appendToResultsCSV(jr *JackpotResult) error {
	if err := os.MkdirAll(a.resultsDir, 0o755); err != nil {
		return fmt.Errorf("creating results dir: %w", err)
	}

	csvPath := filepath.Join(a.resultsDir, "jackpot_results_summary.csv")
	needsHeader := true
	if _, err := os.Stat(csvPath); err == nil {
		needsHeader = false
	}

	f, err := os.OpenFile(csvPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0o644)
	if err != nil {
		return fmt.Errorf("opening results CSV: %w", err)
	}
	defer f.Close()

	w := csv.NewWriter(f)
	if needsHeader {
		if err := w.Write([]string{
			"timestamp", "jackpot_id", "provider", "type",
			"total_matches", "correct", "accuracy",
		}); err != nil {
			return err
		}
	}
	if err := w.Write([]string{
		jr.RecordedAt,
		jr.JackpotID,
		jr.Provider,
		jr.Type,
		strconv.Itoa(jr.TotalMatches),
		strconv.Itoa(jr.CorrectPredictions),
		strconv.FormatFloat(jr.Accuracy, 'f', 4, 64),
	}); err != nil {
		return err
	}
	w.Flush()
	return w.Error()
}

// writeJSON marshals v as indented JSON to path, creating parent dirs as needed.
func (a *JackpotAnalyzer) writeJSON(path string, v any) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return fmt.Errorf("creating dir for %s: %w", path, err)
	}
	raw, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return fmt.Errorf("marshaling JSON: %w", err)
	}
	if err := os.WriteFile(path, raw, 0o644); err != nil {
		return fmt.Errorf("writing %s: %w", path, err)
	}
	return nil
}

// ─── pure helpers ─────────────────────────────────────────────────────────────

// buildMatchPrediction converts an algorithm result into a MatchPrediction.
func buildMatchPrediction(m JackpotMatch, r *algorithm.PredictionResult) MatchPrediction {
	// Determine the most likely outcome label
	prediction := "Home"
	best := r.HomeWinProb
	if r.DrawProb > best {
		prediction = "Draw"
		best = r.DrawProb
	}
	if r.AwayWinProb > best {
		prediction = "Away"
	}

	rec := ""
	if r.Recommendation != nil {
		rec = r.Recommendation.Recommendation
	}

	return MatchPrediction{
		MatchNumber:    m.MatchNumber,
		HomeTeam:       m.HomeTeam,
		AwayTeam:       m.AwayTeam,
		Prediction:     prediction,
		Confidence:     r.Confidence,
		HomeProb:       r.HomeWinProb,
		DrawProb:       r.DrawProb,
		AwayProb:       r.AwayWinProb,
		Recommendation: rec,
	}
}

// averageConfidence computes the mean confidence across all predictions.
func averageConfidence(preds []MatchPrediction) float64 {
	if len(preds) == 0 {
		return 0
	}
	var sum float64
	for _, p := range preds {
		sum += p.Confidence
	}
	return sum / float64(len(preds))
}

// max3 returns the largest of three float64 values.
func max3(a, b, c float64) float64 {
	m := a
	if b > m {
		m = b
	}
	if c > m {
		m = c
	}
	return m
}
