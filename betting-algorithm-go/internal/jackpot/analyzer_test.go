package jackpot

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"bet4me/betting-algorithm-go/internal/algorithm"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// ─── JackpotFetcher tests ─────────────────────────────────────────────────────

func TestSampleSportPesaMatches(t *testing.T) {
	matches := sampleSportPesaMatches()
	assert.Len(t, matches, 17, "Mega Jackpot must have 17 matches")

	for i, m := range matches {
		assert.Equal(t, i+1, m.MatchNumber, "match_number must be sequential")
		assert.NotEmpty(t, m.HomeTeam, "home_team must not be empty")
		assert.NotEmpty(t, m.AwayTeam, "away_team must not be empty")
		assert.NotEmpty(t, m.Competition, "competition must not be empty")
		assert.NotEmpty(t, m.Kickoff, "kickoff must not be empty")
	}
}

func TestSampleSportPesaMidweekMatches(t *testing.T) {
	matches := sampleSportPesaMidweekMatches()
	assert.Len(t, matches, 13, "Midweek Jackpot must have 13 matches")

	for i, m := range matches {
		assert.Equal(t, i+1, m.MatchNumber)
		assert.NotEmpty(t, m.HomeTeam)
		assert.NotEmpty(t, m.AwayTeam)
	}
}

func TestSampleBetikaMatches(t *testing.T) {
	matches := sampleBetikaMatches()
	assert.Len(t, matches, 15, "Betika Jackpot must have 15 matches")

	for i, m := range matches {
		assert.Equal(t, i+1, m.MatchNumber)
		assert.NotEmpty(t, m.HomeTeam)
		assert.NotEmpty(t, m.AwayTeam)
	}
}

func TestNewJackpotFetcher_Defaults(t *testing.T) {
	dir := t.TempDir()
	f := NewJackpotFetcher(dir, nil, nil)
	require.NotNil(t, f)
	assert.Equal(t, filepath.Join(dir, "jackpots"), f.historyDir)
	assert.NotNil(t, f.httpClient)
	assert.NotNil(t, f.logger)
}

func TestExtractPrizeAmount_Patterns(t *testing.T) {
	f := NewJackpotFetcher(t.TempDir(), nil, nil)

	cases := []struct {
		html     string
		wantSome bool
	}{
		{`Prize Pool: KSh 100,000,000 jackpot`, true},
		{`Win 50 Million today`, true},
		{`Prize: 5000000 to winner`, true},
		{`No prize info here`, false},
	}

	for _, tc := range cases {
		got := f.extractPrizeAmount([]byte(tc.html))
		if tc.wantSome {
			assert.NotEmpty(t, got, "expected prize in: %q", tc.html)
		} else {
			assert.Empty(t, got, "expected no prize in: %q", tc.html)
		}
	}
}

func TestGetJackpotHistory_Empty(t *testing.T) {
	f := NewJackpotFetcher(t.TempDir(), nil, nil)
	rows, err := f.GetJackpotHistory("", "")
	require.NoError(t, err)
	assert.Nil(t, rows)
}

func TestSaveAndGetJackpotHistory(t *testing.T) {
	dir := t.TempDir()
	f := NewJackpotFetcher(dir, nil, nil)

	data := &JackpotData{
		Provider:     "SportPesa",
		Type:         "Mega Jackpot",
		MatchesCount: 17,
		FetchedAt:    "2026-03-09T10:00:00Z",
		URL:          "https://example.com",
		PrizeAmount:  "KSh 500,000,000",
		Matches:      sampleSportPesaMatches(),
	}

	require.NoError(t, f.saveJackpotHistory(data))

	rows, err := f.GetJackpotHistory("", "")
	require.NoError(t, err)
	require.Len(t, rows, 1)
	assert.Equal(t, "SportPesa", rows[0].Provider)
	assert.Equal(t, "Mega Jackpot", rows[0].Type)
	assert.Equal(t, "KSh 500,000,000", rows[0].PrizeAmount)
}

func TestGetJackpotHistory_ProviderFilter(t *testing.T) {
	dir := t.TempDir()
	f := NewJackpotFetcher(dir, nil, nil)

	for _, provider := range []string{"SportPesa", "Betika"} {
		data := &JackpotData{
			Provider:  provider,
			Type:      "Jackpot",
			FetchedAt: "2026-03-09T10:00:00Z",
			URL:       "https://example.com",
		}
		require.NoError(t, f.saveJackpotHistory(data))
	}

	rows, err := f.GetJackpotHistory("Betika", "")
	require.NoError(t, err)
	require.Len(t, rows, 1)
	assert.Equal(t, "Betika", rows[0].Provider)
}

// ─── JackpotAnalyzer tests ────────────────────────────────────────────────────

func TestNewJackpotAnalyzer_Defaults(t *testing.T) {
	dir := t.TempDir()
	engine := algorithm.NewPredictionEngine("football", false, false)
	a := NewJackpotAnalyzer(engine, dir, nil)
	require.NotNil(t, a)
	assert.Equal(t, filepath.Join(dir, "jackpot_predictions"), a.predictionsDir)
	assert.Equal(t, filepath.Join(dir, "jackpot_results"), a.resultsDir)
}

func TestAnalyzeJackpot_SampleData(t *testing.T) {
	dir := t.TempDir()
	engine := algorithm.NewPredictionEngine("football", true, false)
	a := NewJackpotAnalyzer(engine, dir, nil)

	data := &JackpotData{
		Provider:     "SportPesa",
		Type:         "Test Jackpot",
		PrizeAmount:  "KSh 100,000,000",
		FetchedAt:    "2026-03-09T10:00:00Z",
		URL:          "https://example.com",
		Matches: []JackpotMatch{
			{1, "Arsenal", "Chelsea", "Sat 15:00", "Premier League", 0, 0, 0},
			{2, "Man City", "Liverpool", "Sat 17:30", "Premier League", 0, 0, 0},
			{3, "Tottenham", "Man United", "Sat 15:00", "Premier League", 0, 0, 0},
		},
	}
	data.MatchesCount = len(data.Matches)

	analysis, err := a.AnalyzeJackpot(data)
	require.NoError(t, err)
	require.NotNil(t, analysis)

	assert.Equal(t, "SportPesa", analysis.Provider)
	assert.Equal(t, "Test Jackpot", analysis.Type)
	assert.Equal(t, 3, analysis.TotalMatches)
	assert.Len(t, analysis.Predictions, 3)
	assert.NotEmpty(t, analysis.JackpotID)
	assert.NotEmpty(t, analysis.AnalyzedAt)
}

func TestAnalyzeJackpot_PredictionStructure(t *testing.T) {
	dir := t.TempDir()
	engine := algorithm.NewPredictionEngine("football", true, false)
	a := NewJackpotAnalyzer(engine, dir, nil)

	data := &JackpotData{
		Provider:  "Test",
		Type:      "Jackpot",
		FetchedAt: "2026-03-09T10:00:00Z",
		URL:       "https://example.com",
		Matches: []JackpotMatch{
			{1, "Arsenal", "Chelsea", "Sat 15:00", "Premier League", 0, 0, 0},
		},
	}
	data.MatchesCount = 1

	analysis, err := a.AnalyzeJackpot(data)
	require.NoError(t, err)
	require.Len(t, analysis.Predictions, 1)

	p := analysis.Predictions[0]
	assert.Equal(t, 1, p.MatchNumber)
	assert.Equal(t, "Arsenal", p.HomeTeam)
	assert.Equal(t, "Chelsea", p.AwayTeam)
	assert.Contains(t, []string{"Home", "Draw", "Away"}, p.Prediction)
	assert.GreaterOrEqual(t, p.Confidence, 0.0)
	assert.LessOrEqual(t, p.Confidence, 1.0)

	// Probabilities must sum to ~1
	sum := p.HomeProb + p.DrawProb + p.AwayProb
	assert.InDelta(t, 1.0, sum, 0.01, "probabilities should sum to 1")
}

func TestAnalyzeJackpot_SavesToDisk(t *testing.T) {
	dir := t.TempDir()
	engine := algorithm.NewPredictionEngine("football", false, false)
	a := NewJackpotAnalyzer(engine, dir, nil)

	data := &JackpotData{
		Provider:  "Betika",
		Type:      "Jackpot",
		FetchedAt: "2026-03-09T10:00:00Z",
		URL:       "https://example.com",
		Matches: []JackpotMatch{
			{1, "Arsenal", "Liverpool", "Sat 15:00", "Premier League", 0, 0, 0},
		},
	}
	data.MatchesCount = 1

	analysis, err := a.AnalyzeJackpot(data)
	require.NoError(t, err)

	// JSON file should exist
	jsonPath := filepath.Join(dir, "jackpot_predictions", analysis.JackpotID+".json")
	assert.FileExists(t, jsonPath)

	// CSV file should exist
	csvPath := filepath.Join(dir, "jackpot_predictions", analysis.JackpotID+".csv")
	assert.FileExists(t, csvPath)
}

func TestAnalyzeJackpot_AverageConfidence(t *testing.T) {
	dir := t.TempDir()
	engine := algorithm.NewPredictionEngine("football", true, false)
	a := NewJackpotAnalyzer(engine, dir, nil)

	matches := sampleSportPesaMatches()[:5]
	data := &JackpotData{
		Provider:     "SportPesa",
		Type:         "Test",
		FetchedAt:    "2026-03-09T10:00:00Z",
		URL:          "https://example.com",
		Matches:      matches,
		MatchesCount: len(matches),
	}

	analysis, err := a.AnalyzeJackpot(data)
	require.NoError(t, err)

	assert.GreaterOrEqual(t, analysis.AverageConfidence, 0.0)
	assert.LessOrEqual(t, analysis.AverageConfidence, 1.0)
}

func TestGenerateCombinations_Empty(t *testing.T) {
	a := &JackpotAnalyzer{}
	combos := a.generateCombinations(nil)
	assert.Empty(t, combos)
}

func TestGenerateCombinations_MainPrediction(t *testing.T) {
	a := &JackpotAnalyzer{}
	preds := []MatchPrediction{
		{MatchNumber: 1, Prediction: "Home", Confidence: 0.80, HomeProb: 0.60, DrawProb: 0.25, AwayProb: 0.15},
		{MatchNumber: 2, Prediction: "Draw", Confidence: 0.50, HomeProb: 0.30, DrawProb: 0.40, AwayProb: 0.30},
	}

	combos := a.generateCombinations(preds)
	require.GreaterOrEqual(t, len(combos), 1)

	main := combos[0]
	assert.Equal(t, "Main Prediction", main.Strategy)
	assert.Len(t, main.Picks, 2)
}

func TestGenerateCombinations_ConservativeStrategy(t *testing.T) {
	a := &JackpotAnalyzer{}
	preds := []MatchPrediction{
		{MatchNumber: 1, Prediction: "Home", Confidence: 0.80, HomeProb: 0.70, DrawProb: 0.20, AwayProb: 0.10},
		{MatchNumber: 2, Prediction: "Away", Confidence: 0.50, HomeProb: 0.30, DrawProb: 0.30, AwayProb: 0.40},
	}

	combos := a.generateCombinations(preds)
	// Should have at least Main + Conservative
	assert.GreaterOrEqual(t, len(combos), 2)

	// Find conservative
	var found bool
	for _, c := range combos {
		if c.Strategy == "Conservative" {
			found = true
			assert.Len(t, c.HighConfidencePicks, 1, "only match 1 is high-confidence")
		}
	}
	assert.True(t, found, "Conservative strategy should be generated")
}

func TestGenerateCombinations_DrawValue(t *testing.T) {
	a := &JackpotAnalyzer{}
	preds := []MatchPrediction{
		{MatchNumber: 1, Prediction: "Draw", Confidence: 0.60, HomeTeam: "A", AwayTeam: "B", HomeProb: 0.30, DrawProb: 0.40, AwayProb: 0.30},
		{MatchNumber: 2, Prediction: "Home", Confidence: 0.70, HomeTeam: "C", AwayTeam: "D", HomeProb: 0.65, DrawProb: 0.20, AwayProb: 0.15},
	}

	combos := a.generateCombinations(preds)
	var found bool
	for _, c := range combos {
		if c.Strategy == "Draw Value" {
			found = true
			assert.Len(t, c.DrawCandidates, 1, "only match 1 draw prob > 30%")
		}
	}
	assert.True(t, found, "Draw Value strategy should be generated")
}

func TestRecordJackpotResults(t *testing.T) {
	dir := t.TempDir()
	engine := algorithm.NewPredictionEngine("football", true, false)
	a := NewJackpotAnalyzer(engine, dir, nil)

	// First, produce an analysis
	data := &JackpotData{
		Provider:     "SportPesa",
		Type:         "Test Jackpot",
		FetchedAt:    "2026-03-09T10:00:00Z",
		URL:          "https://example.com",
		Matches: []JackpotMatch{
			{1, "Arsenal", "Chelsea", "Sat 15:00", "Premier League", 0, 0, 0},
			{2, "Man City", "Liverpool", "Sat 17:30", "Premier League", 0, 0, 0},
		},
		MatchesCount: 2,
	}

	analysis, err := a.AnalyzeJackpot(data)
	require.NoError(t, err)

	// Record results — match 1 correct (use whatever the algorithm predicted)
	pred1 := analysis.Predictions[0].Prediction
	results := []ResultEntry{
		{MatchNumber: 1, ActualResult: pred1},  // correct
		{MatchNumber: 2, ActualResult: "Draw"},  // may or may not be correct
	}

	jr, err := a.RecordJackpotResults(analysis.JackpotID, results)
	require.NoError(t, err)
	require.NotNil(t, jr)

	assert.Equal(t, analysis.JackpotID, jr.JackpotID)
	assert.Equal(t, 2, jr.TotalMatches)
	assert.GreaterOrEqual(t, jr.CorrectPredictions, 1, "match 1 was deliberately correct")
	assert.GreaterOrEqual(t, jr.Accuracy, 0.0)
	assert.LessOrEqual(t, jr.Accuracy, 1.0)

	// Result file should be saved
	resultPath := filepath.Join(dir, "jackpot_results", analysis.JackpotID+"_results.json")
	assert.FileExists(t, resultPath)
}

func TestRecordJackpotResults_FileNotFound(t *testing.T) {
	dir := t.TempDir()
	engine := algorithm.NewPredictionEngine("football", false, false)
	a := NewJackpotAnalyzer(engine, dir, nil)

	_, err := a.RecordJackpotResults("nonexistent_id", nil)
	assert.Error(t, err)
}

func TestGetPerformanceStats_NoData(t *testing.T) {
	dir := t.TempDir()
	engine := algorithm.NewPredictionEngine("football", false, false)
	a := NewJackpotAnalyzer(engine, dir, nil)

	stats, err := a.GetPerformanceStats()
	require.NoError(t, err)
	assert.Nil(t, stats, "no data yet should return nil, not error")
}

func TestGetPerformanceStats_AfterResults(t *testing.T) {
	dir := t.TempDir()
	engine := algorithm.NewPredictionEngine("football", true, false)
	a := NewJackpotAnalyzer(engine, dir, nil)

	// Analyze and record results for two jackpots
	for i := 0; i < 2; i++ {
		data := &JackpotData{
			Provider:     "SportPesa",
			Type:         "Test",
			FetchedAt:    "2026-03-09T10:00:00Z",
			URL:          "https://example.com",
			Matches: []JackpotMatch{
				{1, "Arsenal", "Chelsea", "Sat 15:00", "Premier League", 0, 0, 0},
			},
			MatchesCount: 1,
		}

		analysis, err := a.AnalyzeJackpot(data)
		require.NoError(t, err)

		_, err = a.RecordJackpotResults(analysis.JackpotID, []ResultEntry{
			{MatchNumber: 1, ActualResult: analysis.Predictions[0].Prediction},
		})
		require.NoError(t, err)
	}

	stats, err := a.GetPerformanceStats()
	require.NoError(t, err)
	require.NotNil(t, stats)

	assert.Equal(t, 2, stats.TotalJackpots)
	assert.GreaterOrEqual(t, stats.AverageAccuracy, 0.0)
	assert.LessOrEqual(t, stats.AverageAccuracy, 1.0)
	assert.Contains(t, stats.ByProvider, "SportPesa")
	assert.Equal(t, 2, stats.ByProvider["SportPesa"].Count)
}

// ─── pure helper tests ────────────────────────────────────────────────────────

func TestBuildMatchPrediction_HomeWin(t *testing.T) {
	m := JackpotMatch{MatchNumber: 1, HomeTeam: "Arsenal", AwayTeam: "Chelsea"}
	homeOdds := 1.8
	r := &algorithm.PredictionResult{
		HomeTeam:    "Arsenal",
		AwayTeam:    "Chelsea",
		HomeWinProb: 0.55,
		DrawProb:    0.25,
		AwayWinProb: 0.20,
		Confidence:  0.72,
		Recommendation: &algorithm.Recommendation{
			Recommendation: "BET_HOME",
		},
	}
	_ = homeOdds
	p := buildMatchPrediction(m, r)
	assert.Equal(t, "Home", p.Prediction)
	assert.Equal(t, "BET_HOME", p.Recommendation)
	assert.InDelta(t, 0.55, p.HomeProb, 0.001)
}

func TestBuildMatchPrediction_Draw(t *testing.T) {
	m := JackpotMatch{MatchNumber: 2, HomeTeam: "A", AwayTeam: "B"}
	r := &algorithm.PredictionResult{
		HomeWinProb: 0.30,
		DrawProb:    0.45,
		AwayWinProb: 0.25,
		Confidence:  0.60,
	}
	p := buildMatchPrediction(m, r)
	assert.Equal(t, "Draw", p.Prediction)
}

func TestBuildMatchPrediction_Away(t *testing.T) {
	m := JackpotMatch{MatchNumber: 3, HomeTeam: "A", AwayTeam: "B"}
	r := &algorithm.PredictionResult{
		HomeWinProb: 0.25,
		DrawProb:    0.30,
		AwayWinProb: 0.45,
		Confidence:  0.65,
	}
	p := buildMatchPrediction(m, r)
	assert.Equal(t, "Away", p.Prediction)
}

func TestAverageConfidence(t *testing.T) {
	preds := []MatchPrediction{
		{Confidence: 0.60},
		{Confidence: 0.80},
		{Confidence: 0.70},
	}
	assert.InDelta(t, 0.70, averageConfidence(preds), 0.001)
	assert.Equal(t, 0.0, averageConfidence(nil))
}

func TestMax3(t *testing.T) {
	assert.Equal(t, 0.9, max3(0.5, 0.9, 0.3))
	assert.Equal(t, 0.9, max3(0.9, 0.3, 0.5))
	assert.Equal(t, 0.9, max3(0.3, 0.5, 0.9))
	assert.Equal(t, 0.5, max3(0.5, 0.5, 0.5))
}

func TestEnrichMatchData_KnownTeam(t *testing.T) {
	dir := t.TempDir()
	engine := algorithm.NewPredictionEngine("football", false, false)
	a := NewJackpotAnalyzer(engine, dir, nil)

	m := JackpotMatch{
		MatchNumber: 1, HomeTeam: "Arsenal", AwayTeam: "Chelsea",
		Kickoff: "Sat 15:00", Competition: "Premier League",
	}

	md := a.enrichMatchData(m)
	assert.Equal(t, "Arsenal", md.HomeTeam)
	assert.Equal(t, "Chelsea", md.AwayTeam)
	// Arsenal is in PremierLeagueTeams so Elo should be set
	require.NotNil(t, md.HomeElo)
	assert.Greater(t, *md.HomeElo, 0.0)
}

func TestEnrichMatchData_UnknownTeam(t *testing.T) {
	dir := t.TempDir()
	engine := algorithm.NewPredictionEngine("football", false, false)
	a := NewJackpotAnalyzer(engine, dir, nil)

	m := JackpotMatch{
		MatchNumber: 1, HomeTeam: "Unknown FC", AwayTeam: "Mystery United",
	}

	md := a.enrichMatchData(m)
	assert.Equal(t, "Unknown FC", md.HomeTeam)
	assert.Nil(t, md.HomeElo, "unknown team should have nil Elo")
}

func TestEnrichMatchData_OddsPassThrough(t *testing.T) {
	dir := t.TempDir()
	engine := algorithm.NewPredictionEngine("football", false, false)
	a := NewJackpotAnalyzer(engine, dir, nil)

	m := JackpotMatch{
		MatchNumber: 1, HomeTeam: "A", AwayTeam: "B",
		HomeOdds: 2.1, DrawOdds: 3.2, AwayOdds: 3.5,
	}

	md := a.enrichMatchData(m)
	require.NotNil(t, md.HomeOdds)
	assert.InDelta(t, 2.1, *md.HomeOdds, 0.001)
	require.NotNil(t, md.DrawOdds)
	assert.InDelta(t, 3.2, *md.DrawOdds, 0.001)
	require.NotNil(t, md.AwayOdds)
	assert.InDelta(t, 3.5, *md.AwayOdds, 0.001)
}

// TestAnalysisJSONRoundtrip verifies the analysis can be serialised and
// deserialised without data loss (important for RecordJackpotResults).
func TestAnalysisJSONRoundtrip(t *testing.T) {
	dir := t.TempDir()
	engine := algorithm.NewPredictionEngine("football", true, false)
	a := NewJackpotAnalyzer(engine, dir, nil)

	data := &JackpotData{
		Provider:     "Betika",
		Type:         "Jackpot",
		FetchedAt:    "2026-03-09T10:00:00Z",
		URL:          "https://example.com",
		Matches: []JackpotMatch{
			{1, "Man City", "Liverpool", "Sat 17:30", "Premier League", 0, 0, 0},
		},
		MatchesCount: 1,
	}

	original, err := a.AnalyzeJackpot(data)
	require.NoError(t, err)

	// Read back from disk
	jsonPath := filepath.Join(dir, "jackpot_predictions", original.JackpotID+".json")
	raw, err := os.ReadFile(jsonPath)
	require.NoError(t, err)

	var recovered JackpotAnalysis
	require.NoError(t, json.Unmarshal(raw, &recovered))

	assert.Equal(t, original.JackpotID, recovered.JackpotID)
	assert.Equal(t, original.Provider, recovered.Provider)
	assert.Equal(t, original.TotalMatches, recovered.TotalMatches)
	require.Len(t, recovered.Predictions, 1)
	assert.Equal(t, original.Predictions[0].Prediction, recovered.Predictions[0].Prediction)
}
