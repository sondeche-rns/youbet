package data

import (
	"encoding/csv"
	"fmt"
	"log/slog"
	"math"
	"math/rand/v2"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"bet4me/betting-algorithm-go/internal/storage"
)

// ProgressCallback is called to report pipeline progress.
type ProgressCallback func(step string, current, total int)

// CollectionStatus tracks the state of a background data collection.
type CollectionStatus struct {
	Running   bool   `json:"running"`
	Progress  int    `json:"progress"`
	Step      string `json:"step"`
	Error     string `json:"error,omitempty"`
	Completed bool   `json:"completed"`
}

// HistoricalDataCollector collects and enriches historical match data.
type HistoricalDataCollector struct {
	outputDir  string
	csvStore   *storage.CSVStore
	httpClient *http.Client
	logger     *slog.Logger

	matches    []storage.MatchRecord
	eloRatings map[string]float64
}

// NewHistoricalDataCollector creates a new collector.
func NewHistoricalDataCollector(outputDir string, httpClient *http.Client, logger *slog.Logger) *HistoricalDataCollector {
	if httpClient == nil {
		httpClient = &http.Client{Timeout: 30 * time.Second}
	}
	if logger == nil {
		logger = slog.Default()
	}
	return &HistoricalDataCollector{
		outputDir:  outputDir,
		csvStore:   storage.NewCSVStore(outputDir),
		httpClient: httpClient,
		logger:     logger,
		eloRatings: make(map[string]float64),
	}
}

// CollectAllData runs the 7-step data collection pipeline.
func (c *HistoricalDataCollector) CollectAllData(seasons, leagues []string, callback ProgressCallback) ([]storage.MatchRecord, error) {
	if len(seasons) == 0 {
		seasons = []string{"2324", "2223", "2122", "2021", "1920"}
	}
	if len(leagues) == 0 {
		leagues = []string{"E0"}
	}

	type step struct {
		name string
		fn   func() error
	}

	steps := []step{
		{"Fetching match results & odds...", func() error { return c.collectFootballDataUK(seasons, leagues) }},
		{"Adding expected goals (xG)...", func() error { return c.addXGData() }},
		{"Calculating Elo ratings...", func() error { return c.calculateEloRatings() }},
		{"Computing team form...", func() error { return c.calculateTeamForm() }},
		{"Analyzing rest & congestion...", func() error { return c.calculateRestCongestion() }},
		{"Adding advanced stats...", func() error { return c.addAdvancedStats() }},
		{"Calculating league positions...", func() error { return c.calculateLeaguePositions() }},
	}

	for i, s := range steps {
		if callback != nil {
			callback(s.name, i, len(steps))
		}
		c.logger.Info(fmt.Sprintf("Step %d/%d: %s", i+1, len(steps), s.name))

		if err := s.fn(); err != nil {
			return nil, fmt.Errorf("step %d (%s): %w", i+1, s.name, err)
		}

		c.logger.Info(fmt.Sprintf("  -> %d matches processed", len(c.matches)))
	}

	// Save final dataset
	if err := c.saveFinalDataset(); err != nil {
		return nil, fmt.Errorf("saving final dataset: %w", err)
	}

	return c.matches, nil
}

// collectFootballDataUK fetches match results and odds from football-data.co.uk.
func (c *HistoricalDataCollector) collectFootballDataUK(seasons, leagues []string) error {
	baseURL := "https://www.football-data.co.uk/mmz4281"
	var allMatches []storage.MatchRecord

	for _, season := range seasons {
		for _, league := range leagues {
			url := fmt.Sprintf("%s/%s/%s.csv", baseURL, season, league)

			matches, err := c.fetchAndParseCSV(url, season)
			if err != nil {
				c.logger.Warn("Could not fetch season/league", "season", season, "league", league, "error", err)
				continue
			}

			c.logger.Info(fmt.Sprintf("    Fetched %d matches from %s %s", len(matches), season, league))
			allMatches = append(allMatches, matches...)

			// Be nice to the server
			time.Sleep(500 * time.Millisecond)
		}
	}

	if len(allMatches) == 0 {
		c.logger.Warn("No data fetched, generating sample matches")
		allMatches = c.generateSampleMatches()
	}

	c.matches = allMatches
	return nil
}

// fetchAndParseCSV fetches a CSV URL and parses it into MatchRecords.
func (c *HistoricalDataCollector) fetchAndParseCSV(url, season string) ([]storage.MatchRecord, error) {
	resp, err := c.httpClient.Get(url)
	if err != nil {
		return nil, fmt.Errorf("fetching %s: %w", url, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("HTTP %d for %s", resp.StatusCode, url)
	}

	reader := csv.NewReader(resp.Body)
	reader.LazyQuotes = true
	reader.FieldsPerRecord = -1 // Allow variable fields

	records, err := reader.ReadAll()
	if err != nil {
		return nil, fmt.Errorf("parsing CSV: %w", err)
	}

	if len(records) < 2 {
		return nil, fmt.Errorf("CSV has no data rows")
	}

	// Build header index
	header := records[0]
	idx := make(map[string]int, len(header))
	for i, h := range header {
		idx[strings.TrimSpace(h)] = i
	}

	// Column mapping from football-data.co.uk
	colMap := map[string]string{
		"HomeTeam": "home_team",
		"AwayTeam": "away_team",
		"FTHG":     "home_goals",
		"FTAG":     "away_goals",
		"FTR":      "result",
		"B365H":    "home_odds",
		"B365D":    "draw_odds",
		"B365A":    "away_odds",
		"HS":       "home_shots",
		"AS":       "away_shots",
		"HST":      "home_shots_on_target",
		"AST":      "away_shots_on_target",
	}

	// Build mapped index
	mappedIdx := make(map[string]int)
	for raw, mapped := range colMap {
		if i, ok := idx[raw]; ok {
			mappedIdx[mapped] = i
		}
	}
	if i, ok := idx["Date"]; ok {
		mappedIdx["Date"] = i
	}

	seasonLabel := fmt.Sprintf("20%s-%s", season[:2], season[2:])

	var matches []storage.MatchRecord
	for matchID, row := range records[1:] {
		m := storage.MatchRecord{
			Season:  seasonLabel,
			MatchID: matchID,
		}

		m.Date = getCSVCol(row, mappedIdx, "Date")
		m.HomeTeam = getCSVCol(row, mappedIdx, "home_team")
		m.AwayTeam = getCSVCol(row, mappedIdx, "away_team")

		// Skip rows with no team names
		if m.HomeTeam == "" || m.AwayTeam == "" {
			continue
		}

		m.HomeGoals = getCSVColInt(row, mappedIdx, "home_goals")
		m.AwayGoals = getCSVColInt(row, mappedIdx, "away_goals")

		m.HomeOdds = getCSVColFloat(row, mappedIdx, "home_odds", 2.5)
		m.DrawOdds = getCSVColFloat(row, mappedIdx, "draw_odds", 2.5)
		m.AwayOdds = getCSVColFloat(row, mappedIdx, "away_odds", 2.5)

		m.HomeShots = getCSVColIntDefault(row, mappedIdx, "home_shots", 12)
		m.AwayShots = getCSVColIntDefault(row, mappedIdx, "away_shots", 12)
		m.HomeShotsOnTarget = getCSVColIntDefault(row, mappedIdx, "home_shots_on_target", 5)
		m.AwayShotsOnTarget = getCSVColIntDefault(row, mappedIdx, "away_shots_on_target", 5)

		matches = append(matches, m)
	}

	return matches, nil
}

// addXGData calculates estimated xG based on shots data.
func (c *HistoricalDataCollector) addXGData() error {
	for i := range c.matches {
		m := &c.matches[i]
		if m.HomeShots > 0 && m.HomeShotsOnTarget > 0 {
			m.HomeXG = float64(m.HomeShots)*0.08 + float64(m.HomeShotsOnTarget)*0.22
			m.AwayXG = float64(m.AwayShots)*0.08 + float64(m.AwayShotsOnTarget)*0.22
		} else {
			m.HomeXG = float64(m.HomeGoals) + (rand.Float64() - 0.5)
			m.AwayXG = float64(m.AwayGoals) + (rand.Float64() - 0.5)
		}
		m.HomeXG = clamp(m.HomeXG, 0, 5)
		m.AwayXG = clamp(m.AwayXG, 0, 5)
	}
	return nil
}

// calculateEloRatings computes dynamic Elo ratings for each team.
func (c *HistoricalDataCollector) calculateEloRatings() error {
	sortMatchesByDate(c.matches)

	const baseElo = 1500.0
	const kFactor = 32.0
	c.eloRatings = make(map[string]float64)

	for i := range c.matches {
		m := &c.matches[i]
		home := m.HomeTeam
		away := m.AwayTeam

		homeElo := getOrDefault(c.eloRatings, home, baseElo)
		awayElo := getOrDefault(c.eloRatings, away, baseElo)

		m.HomeElo = homeElo
		m.AwayElo = awayElo

		// Expected scores
		expHome := 1.0 / (1.0 + math.Pow(10, (awayElo-homeElo)/400))
		expAway := 1.0 - expHome

		// Actual outcome
		var actualHome, actualAway float64
		if m.HomeGoals > m.AwayGoals {
			actualHome, actualAway = 1, 0
		} else if m.HomeGoals < m.AwayGoals {
			actualHome, actualAway = 0, 1
		} else {
			actualHome, actualAway = 0.5, 0.5
		}

		c.eloRatings[home] = homeElo + kFactor*(actualHome-expHome)
		c.eloRatings[away] = awayElo + kFactor*(actualAway-expAway)
	}

	return nil
}

// calculateTeamForm tracks last 5 results for each team.
func (c *HistoricalDataCollector) calculateTeamForm() error {
	sortMatchesByDate(c.matches)

	teamResults := make(map[string][]string)

	for i := range c.matches {
		m := &c.matches[i]
		home := m.HomeTeam
		away := m.AwayTeam

		// Get current form (before match)
		homeForm := lastN(teamResults[home], 5)
		awayForm := lastN(teamResults[away], 5)

		if homeForm == "" {
			homeForm = "DDDDD"
		}
		if awayForm == "" {
			awayForm = "DDDDD"
		}

		m.HomeForm = homeForm
		m.AwayForm = awayForm

		// Determine result
		var homeResult, awayResult string
		if m.HomeGoals > m.AwayGoals {
			homeResult, awayResult = "W", "L"
		} else if m.HomeGoals < m.AwayGoals {
			homeResult, awayResult = "L", "W"
		} else {
			homeResult, awayResult = "D", "D"
		}

		teamResults[home] = append(teamResults[home], homeResult)
		teamResults[away] = append(teamResults[away], awayResult)
	}

	return nil
}

// calculateRestCongestion computes rest days and fixture congestion.
func (c *HistoricalDataCollector) calculateRestCongestion() error {
	sortMatchesByDate(c.matches)

	teamLastMatch := make(map[string]time.Time)
	teamRecentGames := make(map[string][]time.Time)

	for i := range c.matches {
		m := &c.matches[i]
		home := m.HomeTeam
		away := m.AwayTeam

		matchDate := parseDate(m.Date)
		if matchDate.IsZero() {
			m.HomeRestDays = 7
			m.AwayRestDays = 7
			m.HomeGamesLast7 = 1
			m.AwayGamesLast7 = 1
			continue
		}

		// Rest days
		if last, ok := teamLastMatch[home]; ok {
			days := int(matchDate.Sub(last).Hours() / 24)
			m.HomeRestDays = clampInt(days, 1, 30)
		} else {
			m.HomeRestDays = 7
		}

		if last, ok := teamLastMatch[away]; ok {
			days := int(matchDate.Sub(last).Hours() / 24)
			m.AwayRestDays = clampInt(days, 1, 30)
		} else {
			m.AwayRestDays = 7
		}

		// Congestion (games in last 7 days)
		weekAgo := matchDate.AddDate(0, 0, -7)

		homeGames := 0
		for _, d := range teamRecentGames[home] {
			if d.After(weekAgo) {
				homeGames++
			}
		}
		m.HomeGamesLast7 = homeGames + 1

		awayGames := 0
		for _, d := range teamRecentGames[away] {
			if d.After(weekAgo) {
				awayGames++
			}
		}
		m.AwayGamesLast7 = awayGames + 1

		// Update tracking
		teamLastMatch[home] = matchDate
		teamLastMatch[away] = matchDate

		teamRecentGames[home] = append(teamRecentGames[home], matchDate)
		teamRecentGames[away] = append(teamRecentGames[away], matchDate)

		// Prune old entries (keep last 30 days)
		monthAgo := matchDate.AddDate(0, 0, -30)
		teamRecentGames[home] = filterDatesAfter(teamRecentGames[home], monthAgo)
		teamRecentGames[away] = filterDatesAfter(teamRecentGames[away], monthAgo)
	}

	return nil
}

// addAdvancedStats calculates possession estimates and PPDA.
func (c *HistoricalDataCollector) addAdvancedStats() error {
	for i := range c.matches {
		m := &c.matches[i]

		totalShots := float64(m.HomeShots + m.AwayShots)
		if totalShots == 0 {
			totalShots = 24
		}

		m.HomePossession = clamp(float64(m.HomeShots)/totalShots*100, 30, 70)
		m.AwayPossession = 100 - m.HomePossession

		// Estimate PPDA
		m.HomePPDA = clamp(15-(m.HomePossession-50)*0.15+(rand.Float64()*4-2), 5, 20)
		m.AwayPPDA = clamp(15-(m.AwayPossession-50)*0.15+(rand.Float64()*4-2), 5, 20)
	}
	return nil
}

// calculateLeaguePositions computes league positions at time of each match.
func (c *HistoricalDataCollector) calculateLeaguePositions() error {
	// Group matches by season
	seasonMatches := make(map[string][]int) // season -> indices
	for i := range c.matches {
		season := c.matches[i].Season
		seasonMatches[season] = append(seasonMatches[season], i)
	}

	for _, indices := range seasonMatches {
		// Sort indices by date
		sort.Slice(indices, func(a, b int) bool {
			return c.matches[indices[a]].Date < c.matches[indices[b]].Date
		})

		teamPoints := make(map[string]int)

		for _, idx := range indices {
			m := &c.matches[idx]
			home := m.HomeTeam
			away := m.AwayTeam

			// Initialize teams
			if _, ok := teamPoints[home]; !ok {
				teamPoints[home] = 0
			}
			if _, ok := teamPoints[away]; !ok {
				teamPoints[away] = 0
			}

			// Calculate positions before match
			positions := calculatePositions(teamPoints)
			m.HomePosition = getPositionOrDefault(positions, home, 10)
			m.AwayPosition = getPositionOrDefault(positions, away, 10)

			// Update points after match
			if m.HomeGoals > m.AwayGoals {
				teamPoints[home] += 3
			} else if m.HomeGoals < m.AwayGoals {
				teamPoints[away] += 3
			} else {
				teamPoints[home] += 1
				teamPoints[away] += 1
			}
		}
	}

	return nil
}

// saveFinalDataset saves the processed dataset to CSV.
func (c *HistoricalDataCollector) saveFinalDataset() error {
	filePath := filepath.Join(c.outputDir, "final", "historical_dataset.csv")
	if err := os.MkdirAll(filepath.Dir(filePath), 0o755); err != nil {
		return fmt.Errorf("creating output directory: %w", err)
	}
	if err := c.csvStore.WriteHistoricalData(filePath, c.matches); err != nil {
		return err
	}

	c.logger.Info("Dataset saved",
		"path", filePath,
		"total_matches", len(c.matches),
	)
	return nil
}

// GetDataSummary returns a summary of collected data.
func (c *HistoricalDataCollector) GetDataSummary() map[string]any {
	if len(c.matches) == 0 {
		return map[string]any{"error": "No data collected"}
	}

	seasons := make(map[string]bool)
	teams := make(map[string]bool)
	var minDate, maxDate string

	for _, m := range c.matches {
		seasons[m.Season] = true
		teams[m.HomeTeam] = true
		teams[m.AwayTeam] = true
		if minDate == "" || m.Date < minDate {
			minDate = m.Date
		}
		if maxDate == "" || m.Date > maxDate {
			maxDate = m.Date
		}
	}

	seasonList := make([]string, 0, len(seasons))
	for s := range seasons {
		seasonList = append(seasonList, s)
	}

	return map[string]any{
		"total_matches": len(c.matches),
		"date_range": map[string]string{
			"start": minDate,
			"end":   maxDate,
		},
		"seasons": seasonList,
		"teams":   len(teams),
	}
}

// generateSampleMatches creates sample data when no real data is available.
func (c *HistoricalDataCollector) generateSampleMatches() []storage.MatchRecord {
	teams := []string{
		"Arsenal", "Chelsea", "Liverpool", "Man City", "Man United",
		"Tottenham", "Everton", "West Ham", "Newcastle", "Brighton",
		"Aston Villa", "Crystal Palace", "Fulham", "Wolves", "Leicester",
		"Bournemouth", "Brentford", "Nottm Forest", "Luton", "Burnley",
	}

	startDate := time.Date(2023, 8, 1, 0, 0, 0, 0, time.UTC)
	var matches []storage.MatchRecord

	src := rand.NewPCG(42, 0)
	rng := rand.New(src)

	for i := 0; i < 380; i++ {
		home := teams[i%20]
		away := teams[(i+1+i/20)%20]
		if home == away {
			away = teams[(i+2)%20]
		}

		matchDate := startDate.AddDate(0, 0, (i/10)*7+i%10%3)

		matches = append(matches, storage.MatchRecord{
			Date:              matchDate.Format("02/01/2006"),
			Season:            "2023-24",
			HomeTeam:          home,
			AwayTeam:          away,
			HomeGoals:         poissonSample(rng, 1.5),
			AwayGoals:         poissonSample(rng, 1.2),
			HomeOdds:          roundTo(1.5+rng.Float64()*2.5, 2),
			DrawOdds:          roundTo(3.0+rng.Float64()*1.0, 2),
			AwayOdds:          roundTo(1.8+rng.Float64()*3.2, 2),
			HomeShots:         8 + rng.IntN(10),
			AwayShots:         6 + rng.IntN(9),
			HomeShotsOnTarget: 2 + rng.IntN(5),
			AwayShotsOnTarget: 1 + rng.IntN(5),
			MatchID:           i,
		})
	}

	return matches
}

// --- Helpers ---

func clamp(v, lo, hi float64) float64 {
	if v < lo {
		return lo
	}
	if v > hi {
		return hi
	}
	return v
}

func clampInt(v, lo, hi int) int {
	if v < lo {
		return lo
	}
	if v > hi {
		return hi
	}
	return v
}

func getOrDefault(m map[string]float64, key string, def float64) float64 {
	if v, ok := m[key]; ok {
		return v
	}
	return def
}

func lastN(results []string, n int) string {
	if len(results) == 0 {
		return ""
	}
	start := len(results) - n
	if start < 0 {
		start = 0
	}
	return strings.Join(results[start:], "")
}

func parseDate(s string) time.Time {
	formats := []string{
		"02/01/2006",
		"2006-01-02",
		"02/01/06",
		"2006-01-02T15:04:05Z",
	}
	for _, f := range formats {
		if t, err := time.Parse(f, s); err == nil {
			return t
		}
	}
	return time.Time{}
}

func filterDatesAfter(dates []time.Time, after time.Time) []time.Time {
	var filtered []time.Time
	for _, d := range dates {
		if d.After(after) {
			filtered = append(filtered, d)
		}
	}
	return filtered
}

func sortMatchesByDate(matches []storage.MatchRecord) {
	sort.Slice(matches, func(i, j int) bool {
		ti := parseDate(matches[i].Date)
		tj := parseDate(matches[j].Date)
		return ti.Before(tj)
	})
}

func calculatePositions(teamPoints map[string]int) map[string]int {
	type tp struct {
		team   string
		points int
	}
	var sorted []tp
	for t, p := range teamPoints {
		sorted = append(sorted, tp{t, p})
	}
	sort.Slice(sorted, func(i, j int) bool {
		return sorted[i].points > sorted[j].points
	})
	positions := make(map[string]int, len(sorted))
	for i, t := range sorted {
		positions[t.team] = i + 1
	}
	return positions
}

func getPositionOrDefault(positions map[string]int, team string, def int) int {
	if p, ok := positions[team]; ok {
		return p
	}
	return def
}

func getCSVCol(row []string, idx map[string]int, col string) string {
	i, ok := idx[col]
	if !ok || i >= len(row) {
		return ""
	}
	return strings.TrimSpace(row[i])
}

func getCSVColInt(row []string, idx map[string]int, col string) int {
	s := getCSVCol(row, idx, col)
	if s == "" {
		return 0
	}
	var v float64
	fmt.Sscanf(s, "%f", &v)
	return int(v)
}

func getCSVColIntDefault(row []string, idx map[string]int, col string, def int) int {
	s := getCSVCol(row, idx, col)
	if s == "" {
		return def
	}
	var v float64
	if _, err := fmt.Sscanf(s, "%f", &v); err != nil {
		return def
	}
	return int(v)
}

func getCSVColFloat(row []string, idx map[string]int, col string, def float64) float64 {
	s := getCSVCol(row, idx, col)
	if s == "" {
		return def
	}
	var v float64
	if _, err := fmt.Sscanf(s, "%f", &v); err != nil {
		return def
	}
	return v
}

func poissonSample(rng *rand.Rand, lambda float64) int {
	L := math.Exp(-lambda)
	k := 0
	p := 1.0
	for {
		k++
		p *= rng.Float64()
		if p < L {
			break
		}
	}
	return k - 1
}

func roundTo(v float64, decimals int) float64 {
	pow := math.Pow(10, float64(decimals))
	return math.Round(v*pow) / pow
}
