package context

import (
	"encoding/json"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"strings"
	"time"

	"bet4me/betting-algorithm-go/internal/domain"
)

// MatchContextBuilder builds MatchContext from various data sources.
//
// Handles missing data gracefully with defaults and caching for performance.
type MatchContextBuilder struct {
	historicalData   []HistoricalMatch
	h2hCache         map[string]*domain.H2HRecord
	seasonStatsCache map[string]map[string]interface{}
	managerDB        map[string]*domain.ManagerInfo
}

// NewMatchContextBuilder creates a new context builder.
func NewMatchContextBuilder(historicalData []HistoricalMatch) *MatchContextBuilder {
	builder := &MatchContextBuilder{
		historicalData:   historicalData,
		h2hCache:         make(map[string]*domain.H2HRecord),
		seasonStatsCache: make(map[string]map[string]interface{}),
		managerDB:        make(map[string]*domain.ManagerInfo),
	}

	// Load manager database if available
	builder.loadManagerDatabase()

	return builder
}

// loadManagerDatabase loads manager database from JSON file.
func (b *MatchContextBuilder) loadManagerDatabase() {
	// Try to find managers.json in data directory
	managersFile := filepath.Join("data", "managers.json")

	// Check if file exists
	if _, err := os.Stat(managersFile); os.IsNotExist(err) {
		// Try alternate path
		managersFile = filepath.Join("..", "data", "managers.json")
		if _, err := os.Stat(managersFile); os.IsNotExist(err) {
			return
		}
	}

	data, err := os.ReadFile(managersFile)
	if err != nil {
		return
	}

	var managersData map[string]map[string]interface{}
	if err := json.Unmarshal(data, &managersData); err != nil {
		return
	}

	// Convert to ManagerInfo objects
	for team, info := range managersData {
		appointmentDate, _ := info["appointmentDate"].(string)
		manager, _ := info["manager"].(string)
		isInterim, _ := info["isInterim"].(bool)

		resultsRaw, _ := info["results"].([]interface{})
		results := make([]string, 0, len(resultsRaw))
		for _, r := range resultsRaw {
			if rs, ok := r.(string); ok {
				results = append(results, rs)
			}
		}

		gamesManaged := calculateGamesManaged(appointmentDate)

		b.managerDB[team] = &domain.ManagerInfo{
			Name:            manager,
			AppointmentDate: appointmentDate,
			GamesManaged:    gamesManaged,
			Results:         results,
			IsInterim:       isInterim,
		}
	}
}

// calculateGamesManaged estimates games managed since appointment.
//
// Rough estimate: ~1 game per week since appointment.
func calculateGamesManaged(appointmentDateStr string) int {
	appointmentDate, err := time.Parse("2006-01-02", appointmentDateStr)
	if err != nil {
		return 50 // Default to established manager
	}

	weeksElapsed := time.Since(appointmentDate).Hours() / 24 / 7
	// Estimate: ~38 games per season, ~40 weeks/season = ~1 game/week
	return int(weeksElapsed)
}

// BuildContext builds complete MatchContext from individual match fields.
// Parameters mirror the relevant fields of algorithm.MatchData without
// creating an import cycle between the algorithm and context packages.
func (b *MatchContextBuilder) BuildContext(
	homeTeam, awayTeam string,
	homePossession, awayPossession float64,
	homePos, awayPos int,
	homeFormStr, awayFormStr string,
) *domain.MatchContext {
	if homeTeam == "" || awayTeam == "" {
		// Missing basic data, return neutral context
		return domain.NewNeutralContext()
	}

	// Derive defensive styles from possession
	homeStyle := classifyDefensiveStyle(homePossession)
	awayStyle := classifyDefensiveStyle(awayPossession)

	// Build manager info (with fallback)
	homeManager := b.getManagerInfo(homeTeam)
	awayManager := b.getManagerInfo(awayTeam)

	// Get recent form
	homeForm := parseForm(homeFormStr)
	awayForm := parseForm(awayFormStr)

	// Build H2H record (with fallback)
	h2h := b.getH2HRecord(homeTeam, awayTeam, homePos, awayPos)

	// Calculate season stats (from historical data)
	homeSeasonStats := b.calculateSeasonStats(homeTeam, "home")
	awaySeasonStats := b.calculateSeasonStats(awayTeam, "away")

	return &domain.MatchContext{
		HomeDefensiveStyle: homeStyle,
		AwayDefensiveStyle: awayStyle,
		HomeManagerInfo:    homeManager,
		AwayManagerInfo:    awayManager,
		HomeLeaguePosition: homePos,
		AwayLeaguePosition: awayPos,
		HomeRecentForm:     homeForm,
		AwayRecentForm:     awayForm,
		H2HRecord:          h2h,
		HomeSeasonStats:    homeSeasonStats,
		AwaySeasonStats:    awaySeasonStats,
	}
}

// classifyDefensiveStyle classifies defensive style from average possession.
func classifyDefensiveStyle(avgPossession float64) domain.DefensiveStyle {
	if avgPossession > 55 {
		return domain.DefensiveStyleHighPress
	} else if avgPossession >= 45 {
		return domain.DefensiveStyleBalanced
	}
	return domain.DefensiveStyleLowBlock
}

// parseForm parses form string into list.
func parseForm(formStr string) []string {
	if formStr == "" {
		return []string{"D", "D", "D", "D", "D"}
	}

	// Convert to list, filter to only W/D/L
	results := []string{}
	for _, c := range strings.ToUpper(formStr) {
		if c == 'W' || c == 'D' || c == 'L' {
			results = append(results, string(c))
		}
	}

	if len(results) == 0 {
		return []string{"D", "D", "D", "D", "D"}
	}

	return results
}

// getManagerInfo gets manager info for team.
func (b *MatchContextBuilder) getManagerInfo(team string) *domain.ManagerInfo {
	return b.managerDB[team]
}

// getH2HRecord gets H2H record from historical data.
func (b *MatchContextBuilder) getH2HRecord(homeTeam, awayTeam string, homePos, awayPos int) *domain.H2HRecord {
	cacheKey := fmt.Sprintf("%s_%s", homeTeam, awayTeam)
	if cached, ok := b.h2hCache[cacheKey]; ok {
		return cached
	}

	if len(b.historicalData) == 0 {
		return nil
	}

	// Filter matches involving both teams (either venue)
	var h2hMatches []HistoricalMatch
	for _, m := range b.historicalData {
		if (m.HomeTeam == homeTeam && m.AwayTeam == awayTeam) ||
			(m.HomeTeam == awayTeam && m.AwayTeam == homeTeam) {
			h2hMatches = append(h2hMatches, m)
		}
	}

	record := BuildH2HRecordFromMatches(h2hMatches, homeTeam, awayTeam, homePos, awayPos)
	if record != nil {
		b.h2hCache[cacheKey] = record
	}
	return record
}

// SetHistoricalData updates the historical dataset used for context building.
// Call this after data collection completes to refresh H2H and season stats.
func (b *MatchContextBuilder) SetHistoricalData(matches []HistoricalMatch) {
	b.historicalData = matches
	// Invalidate caches so next BuildContext calls use new data
	b.h2hCache = make(map[string]*domain.H2HRecord)
	b.seasonStatsCache = make(map[string]map[string]interface{})
}

// calculateWeakerTeamStreak calculates consecutive unbeaten streak for weaker team in H2H.
func calculateWeakerTeamStreak(
	results []domain.H2HResult,
	homeTeam, awayTeam string,
	homePos, awayPos int,
) int {
	// Determine weaker team (higher position number = weaker)
	weakerIsHome := homePos > awayPos
	weakerTeam := awayTeam
	if weakerIsHome {
		weakerTeam = homeTeam
	}

	// Count consecutive games from most recent where weaker team didn't lose
	streak := 0
	for i := len(results) - 1; i >= 0; i-- {
		result := results[i]

		// Determine if weaker team was home or away in this H2H match
		if result.HomeTeam == weakerTeam {
			// Weaker team was home
			if result.HomeScore >= result.AwayScore {
				streak++ // Win or draw
			} else {
				break // Loss
			}
		} else {
			// Weaker team was away
			if result.AwayScore >= result.HomeScore {
				streak++ // Win or draw
			} else {
				break // Loss
			}
		}
	}

	return streak
}

// calculateSeasonStats calculates season-level statistics for team.
func (b *MatchContextBuilder) calculateSeasonStats(team string, perspective string) map[string]interface{} {
	cacheKey := fmt.Sprintf("%s_%s", team, perspective)
	if cached, ok := b.seasonStatsCache[cacheKey]; ok {
		return cached
	}

	if len(b.historicalData) == 0 {
		return nil
	}

	// Filter matches involving this team
	var teamMatches []HistoricalMatch
	for _, m := range b.historicalData {
		if m.HomeTeam == team || m.AwayTeam == team {
			teamMatches = append(teamMatches, m)
		}
	}

	stats := CalculateSeasonStatsFromMatches(teamMatches, team, perspective)
	if stats != nil {
		b.seasonStatsCache[cacheKey] = stats
	}
	return stats
}

// ClearCaches clears all caches (useful for testing or when data updated).
func (b *MatchContextBuilder) ClearCaches() {
	b.h2hCache = make(map[string]*domain.H2HRecord)
	b.seasonStatsCache = make(map[string]map[string]interface{})
}

// UpdateManagerInfo updates manager information for a team.
func (b *MatchContextBuilder) UpdateManagerInfo(team string, managerInfo *domain.ManagerInfo) {
	b.managerDB[team] = managerInfo
}

// HistoricalMatch represents a single match record for processing.
//
// This is used when converting historical data into structured records
// for H2H and season stats calculations.
type HistoricalMatch struct {
	Date         string
	HomeTeam     string
	AwayTeam     string
	HomeGoals    int
	AwayGoals    int
	HomePossession float64
	AwayPossession float64
	Competition  string
	Season       string
}

// BuildH2HRecordFromMatches builds H2H record from a slice of historical matches.
//
// This is a helper method for when you have structured match data available.
func BuildH2HRecordFromMatches(
	matches []HistoricalMatch,
	homeTeam, awayTeam string,
	homePos, awayPos int,
) *domain.H2HRecord {
	if len(matches) < 3 {
		return nil // Insufficient data
	}

	// Build results list (limit to last 10 H2H matches)
	results := make([]domain.H2HResult, 0, len(matches))
	for _, match := range matches {
		if len(results) >= 10 {
			break
		}

		results = append(results, domain.H2HResult{
			Date:      match.Date,
			HomeScore: match.HomeGoals,
			AwayScore: match.AwayGoals,
			HomeTeam:  match.HomeTeam,
			AwayTeam:  match.AwayTeam,
		})
	}

	// Calculate anomaly (weaker team unbeaten streak)
	weakerTeamStreak := calculateWeakerTeamStreak(results, homeTeam, awayTeam, homePos, awayPos)
	anomalyTriggered := weakerTeamStreak >= 3

	return &domain.H2HRecord{
		HomeTeam:                homeTeam,
		AwayTeam:                awayTeam,
		Results:                 results,
		WeakerTeamUnbeatenStreak: weakerTeamStreak,
		AnomalyTriggered:        anomalyTriggered,
	}
}

// CalculateSeasonStatsFromMatches calculates season stats from a slice of historical matches.
//
// This is a helper method for when you have structured match data available.
func CalculateSeasonStatsFromMatches(
	matches []HistoricalMatch,
	team string,
	perspective string,
) map[string]interface{} {
	if len(matches) < 5 {
		return nil // Need minimum sample size
	}

	// Separate home and away matches
	homeMatches := []HistoricalMatch{}
	awayMatches := []HistoricalMatch{}

	for _, match := range matches {
		if match.HomeTeam == team {
			homeMatches = append(homeMatches, match)
		} else if match.AwayTeam == team {
			awayMatches = append(awayMatches, match)
		}
	}

	// Calculate possession average
	var avgPossession float64
	if len(homeMatches) > 0 && len(awayMatches) > 0 {
		homePossSum := 0.0
		for _, m := range homeMatches {
			homePossSum += m.HomePossession
		}
		homePossAvg := homePossSum / float64(len(homeMatches))

		awayPossSum := 0.0
		for _, m := range awayMatches {
			awayPossSum += m.AwayPossession
		}
		awayPossAvg := awayPossSum / float64(len(awayMatches))

		avgPossession = (homePossAvg + awayPossAvg) / 2
	} else {
		avgPossession = 50.0
	}

	// Calculate away-specific stats
	awayDraws := 0
	totalAwayGames := len(awayMatches)

	for _, match := range awayMatches {
		if match.HomeGoals == match.AwayGoals {
			awayDraws++
		}
	}

	awayDrawRate := 0.25
	if totalAwayGames > 0 {
		awayDrawRate = float64(awayDraws) / float64(totalAwayGames)
	}

	// Calculate goals per game
	homeGoals := 0
	awayGoals := 0

	for _, m := range homeMatches {
		homeGoals += m.HomeGoals
	}
	for _, m := range awayMatches {
		awayGoals += m.AwayGoals
	}

	totalGames := len(matches)
	goalsPerGame := 1.2
	if totalGames > 0 {
		goalsPerGame = float64(homeGoals+awayGoals) / float64(totalGames)
	}

	return map[string]interface{}{
		"avgPossession":  avgPossession,
		"awayDraws":      awayDraws,
		"totalAwayGames": totalAwayGames,
		"awayDrawRate":   awayDrawRate,
		"goalsPerGame":   goalsPerGame,
		"homeGames":      len(homeMatches),
		"awayGames":      len(awayMatches),
		"totalGames":     totalGames,
	}
}

// Helper function to clamp values
func clamp(value, min, max float64) float64 {
	return math.Max(min, math.Min(max, value))
}
