package data

import (
	"math/rand/v2"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestGenerateSampleMatches(t *testing.T) {
	c := NewHistoricalDataCollector("./testdata", nil, nil)
	matches := c.generateSampleMatches()

	assert.Len(t, matches, 380)
	assert.Equal(t, "2023-24", matches[0].Season)
	assert.NotEmpty(t, matches[0].HomeTeam)
	assert.NotEmpty(t, matches[0].AwayTeam)
	assert.NotEqual(t, matches[0].HomeTeam, matches[0].AwayTeam)
}

func TestAddXGData(t *testing.T) {
	c := NewHistoricalDataCollector("./testdata", nil, nil)
	c.matches = c.generateSampleMatches()

	err := c.addXGData()
	require.NoError(t, err)

	for _, m := range c.matches {
		assert.GreaterOrEqual(t, m.HomeXG, 0.0)
		assert.LessOrEqual(t, m.HomeXG, 5.0)
		assert.GreaterOrEqual(t, m.AwayXG, 0.0)
		assert.LessOrEqual(t, m.AwayXG, 5.0)
	}
}

func TestCalculateEloRatings(t *testing.T) {
	c := NewHistoricalDataCollector("./testdata", nil, nil)
	c.matches = c.generateSampleMatches()

	err := c.calculateEloRatings()
	require.NoError(t, err)

	// All matches should have Elo ratings set
	for _, m := range c.matches {
		assert.Greater(t, m.HomeElo, 0.0)
		assert.Greater(t, m.AwayElo, 0.0)
	}

	// Elo ratings should have been tracked
	assert.NotEmpty(t, c.eloRatings)
}

func TestCalculateTeamForm(t *testing.T) {
	c := NewHistoricalDataCollector("./testdata", nil, nil)
	c.matches = c.generateSampleMatches()

	err := c.calculateTeamForm()
	require.NoError(t, err)

	for _, m := range c.matches {
		assert.NotEmpty(t, m.HomeForm)
		assert.NotEmpty(t, m.AwayForm)
		// Form should only contain W, D, L
		for _, ch := range m.HomeForm {
			assert.Contains(t, "WDL", string(ch))
		}
	}
}

func TestCalculateRestCongestion(t *testing.T) {
	c := NewHistoricalDataCollector("./testdata", nil, nil)
	c.matches = c.generateSampleMatches()

	err := c.calculateRestCongestion()
	require.NoError(t, err)

	for _, m := range c.matches {
		assert.GreaterOrEqual(t, m.HomeRestDays, 1)
		assert.LessOrEqual(t, m.HomeRestDays, 30)
		assert.GreaterOrEqual(t, m.AwayRestDays, 1)
		assert.LessOrEqual(t, m.AwayRestDays, 30)
		assert.GreaterOrEqual(t, m.HomeGamesLast7, 1)
		assert.GreaterOrEqual(t, m.AwayGamesLast7, 1)
	}
}

func TestAddAdvancedStats(t *testing.T) {
	c := NewHistoricalDataCollector("./testdata", nil, nil)
	c.matches = c.generateSampleMatches()

	err := c.addAdvancedStats()
	require.NoError(t, err)

	for _, m := range c.matches {
		assert.GreaterOrEqual(t, m.HomePossession, 30.0)
		assert.LessOrEqual(t, m.HomePossession, 70.0)
		total := m.HomePossession + m.AwayPossession
		assert.InDelta(t, 100.0, total, 0.01)

		assert.GreaterOrEqual(t, m.HomePPDA, 5.0)
		assert.LessOrEqual(t, m.HomePPDA, 20.0)
		assert.GreaterOrEqual(t, m.AwayPPDA, 5.0)
		assert.LessOrEqual(t, m.AwayPPDA, 20.0)
	}
}

func TestCalculateLeaguePositions(t *testing.T) {
	c := NewHistoricalDataCollector("./testdata", nil, nil)
	c.matches = c.generateSampleMatches()

	err := c.calculateLeaguePositions()
	require.NoError(t, err)

	for _, m := range c.matches {
		assert.GreaterOrEqual(t, m.HomePosition, 1)
		assert.GreaterOrEqual(t, m.AwayPosition, 1)
	}
}

func TestGetDataSummary_NoData(t *testing.T) {
	c := NewHistoricalDataCollector("./testdata", nil, nil)
	summary := c.GetDataSummary()
	assert.Contains(t, summary, "error")
}

func TestGetDataSummary_WithData(t *testing.T) {
	c := NewHistoricalDataCollector("./testdata", nil, nil)
	c.matches = c.generateSampleMatches()

	summary := c.GetDataSummary()
	assert.Equal(t, 380, summary["total_matches"])
	assert.Contains(t, summary, "seasons")
	assert.Contains(t, summary, "teams")
	assert.Contains(t, summary, "date_range")
}

func TestClamp(t *testing.T) {
	assert.Equal(t, 5.0, clamp(3.0, 5.0, 10.0))
	assert.Equal(t, 7.0, clamp(7.0, 5.0, 10.0))
	assert.Equal(t, 10.0, clamp(15.0, 5.0, 10.0))
}

func TestClampInt(t *testing.T) {
	assert.Equal(t, 5, clampInt(3, 5, 10))
	assert.Equal(t, 7, clampInt(7, 5, 10))
	assert.Equal(t, 10, clampInt(15, 5, 10))
}

func TestParseDate(t *testing.T) {
	t1 := parseDate("15/08/2023")
	assert.False(t, t1.IsZero())
	assert.Equal(t, 2023, t1.Year())
	assert.Equal(t, 8, int(t1.Month()))

	t2 := parseDate("2023-08-15")
	assert.False(t, t2.IsZero())

	t3 := parseDate("invalid")
	assert.True(t, t3.IsZero())
}

func TestParseMatchTime(t *testing.T) {
	t1 := parseMatchTime("2024-02-11T15:00:00Z")
	assert.False(t, t1.IsZero())
	assert.Equal(t, 2024, t1.Year())

	t2 := parseMatchTime("15/08/2023")
	assert.False(t, t2.IsZero())

	t3 := parseMatchTime("")
	assert.True(t, t3.IsZero())
}

func TestNormalizeTeamName(t *testing.T) {
	assert.Equal(t, "manchestercity", normalizeTeamName("Manchester City"))
	assert.Equal(t, "arsenal", normalizeTeamName(" Arsenal "))
}

func TestExtractBestOdds(t *testing.T) {
	event := oddsAPIEvent{
		HomeTeam: "Arsenal",
		AwayTeam: "Chelsea",
		Bookmakers: []oddsBookmaker{
			{
				Markets: []oddsMarket{
					{
						Key: "h2h",
						Outcomes: []oddsOutcome{
							{Name: "Arsenal", Price: 1.5},
							{Name: "Draw", Price: 3.5},
							{Name: "Chelsea", Price: 5.0},
						},
					},
				},
			},
			{
				Markets: []oddsMarket{
					{
						Key: "h2h",
						Outcomes: []oddsOutcome{
							{Name: "Arsenal", Price: 1.6},
							{Name: "Draw", Price: 3.3},
							{Name: "Chelsea", Price: 4.8},
						},
					},
				},
			},
		},
	}

	home, draw, away := extractBestOdds(event)
	assert.Equal(t, 1.6, home)  // Best home odds
	assert.Equal(t, 3.5, draw)  // Best draw odds
	assert.Equal(t, 5.0, away)  // Best away odds
}

func TestPoissonSample(t *testing.T) {
	rng := rand.New(rand.NewPCG(42, 0))
	for i := 0; i < 100; i++ {
		v := poissonSample(rng, 1.5)
		assert.GreaterOrEqual(t, v, 0)
	}
}
