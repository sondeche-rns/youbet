package domain

import (
	"errors"
	"fmt"
	"time"
)

// FactorResult is the standardized output for all prediction factors.
//
// Provides a consistent interface for factor calculations with metadata
// for debugging, calibration, and explanation.
type FactorResult struct {
	Name        string         `json:"name"`        // Factor identifier (e.g., "h2hAnomaly")
	Value       float64        `json:"value"`        // -1.0 to 1.0 (0.5 = neutral, >0.5 favors home)
	Weight      float64        `json:"weight"`       // Actual weight (may be 0.0 if inactive)
	Triggered   bool           `json:"triggered"`    // Whether this conditional factor is active
	Confidence  int            `json:"confidence"`   // 0-100, data quality/completeness score
	Explanation string         `json:"explanation"`  // Human-readable explanation
	Metadata    map[string]any `json:"metadata"`     // Additional factor-specific data
}

// Validate checks that the FactorResult fields are within valid ranges.
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

// NewInactiveFactorResult creates an inactive factor result with minimal data.
func NewInactiveFactorResult(name, explanation string) FactorResult {
	return FactorResult{
		Name:        name,
		Value:       0.5,
		Weight:      0.0,
		Triggered:   false,
		Confidence:  0,
		Explanation: explanation,
		Metadata:    make(map[string]any),
	}
}

// ManagerInfo tracks manager tenure and results for calculating new manager bounce.
type ManagerInfo struct {
	Name            string   `json:"name"`
	AppointmentDate string   `json:"appointmentDate"` // ISO format YYYY-MM-DD
	GamesManaged    int      `json:"gamesManaged"`
	Results         []string `json:"results"`  // ["W", "D", "L", ...] most recent last
	IsInterim       bool     `json:"isInterim"`
}

// Validate checks that ManagerInfo fields are valid.
func (m *ManagerInfo) Validate() error {
	if m.GamesManaged < 0 {
		return fmt.Errorf("gamesManaged must be non-negative, got %d", m.GamesManaged)
	}
	for _, r := range m.Results {
		if r != "W" && r != "D" && r != "L" {
			return fmt.Errorf("invalid result %q, must be W/D/L", r)
		}
	}
	return nil
}

// WinRate calculates the win rate from results.
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

// H2HResult represents a single head-to-head match result.
type H2HResult struct {
	Date      string `json:"date"`
	HomeTeam  string `json:"homeTeam"`
	AwayTeam  string `json:"awayTeam"`
	HomeScore int    `json:"homeScore"`
	AwayScore int    `json:"awayScore"`
}

// H2HRecord tracks historical head-to-head data between two teams.
type H2HRecord struct {
	HomeTeam                 string      `json:"homeTeam"`
	AwayTeam                 string      `json:"awayTeam"`
	Results                  []H2HResult `json:"results"`
	WeakerTeamUnbeatenStreak int         `json:"weakerTeamUnbeatenStreak"`
	AnomalyTriggered         bool        `json:"anomalyTriggered"`
}

// TotalMatches returns the number of H2H matches.
func (h *H2HRecord) TotalMatches() int {
	return len(h.Results)
}

// HomeWins returns the number of home wins in H2H.
func (h *H2HRecord) HomeWins() int {
	count := 0
	for _, r := range h.Results {
		if r.HomeScore > r.AwayScore {
			count++
		}
	}
	return count
}

// Draws returns the number of draws in H2H.
func (h *H2HRecord) Draws() int {
	count := 0
	for _, r := range h.Results {
		if r.HomeScore == r.AwayScore {
			count++
		}
	}
	return count
}

// AwayWins returns the number of away wins in H2H.
func (h *H2HRecord) AwayWins() int {
	count := 0
	for _, r := range h.Results {
		if r.HomeScore < r.AwayScore {
			count++
		}
	}
	return count
}

// WinRate returns win rate from the specified perspective.
func (h *H2HRecord) WinRate(perspective string) float64 {
	if h.TotalMatches() == 0 {
		return 0.0
	}
	if perspective == "home" {
		return float64(h.HomeWins()) / float64(h.TotalMatches())
	}
	return float64(h.AwayWins()) / float64(h.TotalMatches())
}

// MatchContext encapsulates all contextual data needed for advanced factor calculation.
type MatchContext struct {
	HomeDefensiveStyle DefensiveStyle `json:"homeDefensiveStyle"`
	AwayDefensiveStyle DefensiveStyle `json:"awayDefensiveStyle"`

	HomeManagerInfo *ManagerInfo `json:"homeManagerInfo,omitempty"`
	AwayManagerInfo *ManagerInfo `json:"awayManagerInfo,omitempty"`

	HomeLeaguePosition int `json:"homeLeaguePosition"`
	AwayLeaguePosition int `json:"awayLeaguePosition"`

	HomeRecentForm []string `json:"homeRecentForm"` // ["W", "D", "L", ...]
	AwayRecentForm []string `json:"awayRecentForm"`

	H2HRecord *H2HRecord `json:"h2hRecord,omitempty"`

	HomeSeasonStats map[string]any `json:"homeSeasonStats,omitempty"`
	AwaySeasonStats map[string]any `json:"awaySeasonStats,omitempty"`
}

// Validate checks that MatchContext fields are valid.
func (c *MatchContext) Validate() error {
	for _, form := range [][]string{c.HomeRecentForm, c.AwayRecentForm} {
		for _, r := range form {
			if r != "W" && r != "D" && r != "L" {
				return fmt.Errorf("invalid form result %q, must be W/D/L", r)
			}
		}
	}
	if c.HomeLeaguePosition < 1 || c.AwayLeaguePosition < 1 {
		return errors.New("league positions must be >= 1")
	}
	return nil
}

// RecentWins counts recent wins for a team in the last n games.
func (c *MatchContext) RecentWins(team string, lastN int) int {
	var form []string
	if team == "home" {
		form = c.HomeRecentForm
	} else {
		form = c.AwayRecentForm
	}
	start := len(form) - lastN
	if start < 0 {
		start = 0
	}
	wins := 0
	for _, r := range form[start:] {
		if r == "W" {
			wins++
		}
	}
	return wins
}

// IsRelegationThreatened checks if a team is in the bottom 3 (positions 18-20).
func (c *MatchContext) IsRelegationThreatened(team string) bool {
	pos := c.HomeLeaguePosition
	if team == "away" {
		pos = c.AwayLeaguePosition
	}
	return pos >= 18
}

// NewNeutralContext creates a neutral match context with minimal data.
func NewNeutralContext() *MatchContext {
	return &MatchContext{
		HomeDefensiveStyle: DefensiveStyleBalanced,
		AwayDefensiveStyle: DefensiveStyleBalanced,
		HomeLeaguePosition: 10,
		AwayLeaguePosition: 10,
		HomeRecentForm:     []string{"D", "D", "D", "D", "D"},
		AwayRecentForm:     []string{"D", "D", "D", "D", "D"},
	}
}

// BetRecord represents a single bet for the performance tracker.
type BetRecord struct {
	Stake        float64   `json:"stake"`
	Odds         float64   `json:"odds"`
	Won          bool      `json:"won"`
	PnL          float64   `json:"pnl"`
	Timestamp    time.Time `json:"timestamp"`
	BankrollAfter float64  `json:"bankroll_after"`
}

// MatchData holds the input data for a prediction request.
type MatchData struct {
	HomeTeam    string  `json:"home_team"`
	AwayTeam    string  `json:"away_team"`
	HomeOdds    float64 `json:"home_odds,omitempty"`
	DrawOdds    float64 `json:"draw_odds,omitempty"`
	AwayOdds    float64 `json:"away_odds,omitempty"`
	Competition string  `json:"competition,omitempty"`
	Date        string  `json:"date,omitempty"`
}

// Probabilities holds the three-way match probabilities.
type Probabilities struct {
	Home float64 `json:"homeWinProb"`
	Draw float64 `json:"drawProb"`
	Away float64 `json:"awayWinProb"`
}

// PredictionResult is the full output of a match prediction.
type PredictionResult struct {
	HomeTeam       string                   `json:"homeTeam"`
	AwayTeam       string                   `json:"awayTeam"`
	Probabilities  Probabilities            `json:"probabilities"`
	Confidence     float64                  `json:"confidence"`
	Recommendation *BetRecommendation       `json:"recommendation"`
	Factors        map[string]*FactorResult `json:"factors"`
	ExpectedGoals  ExpectedGoals            `json:"expectedGoals"`
	Timestamp      string                   `json:"timestamp"`
}

// BetRecommendation holds the final betting suggestion.
type BetRecommendation struct {
	Outcome         string  `json:"outcome"`
	Probability     float64 `json:"probability"`
	Recommendation  string  `json:"recommendation"`
	StakePercentage float64 `json:"stakePercentage"`
	ExpectedValue   float64 `json:"expectedValue"`
	KellyStake      float64 `json:"kellyStake"`
}

// ExpectedGoals holds the expected goals for home and away teams.
type ExpectedGoals struct {
	Home float64 `json:"home"`
	Away float64 `json:"away"`
}
