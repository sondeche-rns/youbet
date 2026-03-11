package context

import (
	"testing"
)

// makeH2HFixtures returns a slice of historical matches between Arsenal and Chelsea
// with Arsenal (position 2) as the weaker home team in the most recent matches,
// giving a 3-game unbeaten streak to trigger the anomaly.
func makeH2HFixtures() []HistoricalMatch {
	return []HistoricalMatch{
		{Date: "2022-08-13", HomeTeam: "Chelsea", AwayTeam: "Arsenal", HomeGoals: 2, AwayGoals: 1, HomePossession: 55, AwayPossession: 45, Season: "2223"},
		{Date: "2023-01-15", HomeTeam: "Arsenal", AwayTeam: "Chelsea", HomeGoals: 1, AwayGoals: 1, HomePossession: 52, AwayPossession: 48, Season: "2223"},
		{Date: "2023-04-04", HomeTeam: "Chelsea", AwayTeam: "Arsenal", HomeGoals: 0, AwayGoals: 2, HomePossession: 53, AwayPossession: 47, Season: "2223"},
		{Date: "2023-10-21", HomeTeam: "Arsenal", AwayTeam: "Chelsea", HomeGoals: 2, AwayGoals: 2, HomePossession: 54, AwayPossession: 46, Season: "2324"},
		// Last 3: Chelsea (away, weaker pos=10) unbeaten in these H2H
		{Date: "2024-01-20", HomeTeam: "Arsenal", AwayTeam: "Chelsea", HomeGoals: 0, AwayGoals: 1, HomePossession: 57, AwayPossession: 43, Season: "2324"},
		{Date: "2024-04-23", HomeTeam: "Arsenal", AwayTeam: "Chelsea", HomeGoals: 2, AwayGoals: 2, HomePossession: 56, AwayPossession: 44, Season: "2324"},
		{Date: "2024-08-18", HomeTeam: "Arsenal", AwayTeam: "Chelsea", HomeGoals: 1, AwayGoals: 1, HomePossession: 55, AwayPossession: 45, Season: "2425"},
	}
}

// makeSeasonFixtures returns matches that give Chelsea a high away draw rate.
func makeSeasonFixtures() []HistoricalMatch {
	return []HistoricalMatch{
		// Chelsea home matches
		{Date: "2024-08-18", HomeTeam: "Chelsea", AwayTeam: "Man City", HomeGoals: 1, AwayGoals: 0, HomePossession: 48, AwayPossession: 52, Season: "2425"},
		{Date: "2024-09-01", HomeTeam: "Chelsea", AwayTeam: "Liverpool", HomeGoals: 2, AwayGoals: 1, HomePossession: 47, AwayPossession: 53, Season: "2425"},
		// Chelsea away matches — 3 draws out of 5 = 60% away draw rate
		{Date: "2024-09-15", HomeTeam: "Arsenal", AwayTeam: "Chelsea", HomeGoals: 1, AwayGoals: 1, HomePossession: 55, AwayPossession: 45, Season: "2425"},
		{Date: "2024-09-28", HomeTeam: "Tottenham", AwayTeam: "Chelsea", HomeGoals: 2, AwayGoals: 2, HomePossession: 52, AwayPossession: 48, Season: "2425"},
		{Date: "2024-10-05", HomeTeam: "Man Utd", AwayTeam: "Chelsea", HomeGoals: 0, AwayGoals: 1, HomePossession: 50, AwayPossession: 50, Season: "2425"},
		{Date: "2024-10-19", HomeTeam: "Everton", AwayTeam: "Chelsea", HomeGoals: 0, AwayGoals: 0, HomePossession: 40, AwayPossession: 60, Season: "2425"},
		{Date: "2024-11-02", HomeTeam: "Wolves", AwayTeam: "Chelsea", HomeGoals: 1, AwayGoals: 1, HomePossession: 42, AwayPossession: 58, Season: "2425"},
	}
}

func TestGetH2HRecord_WithSufficientData(t *testing.T) {
	builder := NewMatchContextBuilder(makeH2HFixtures())
	h2h := builder.getH2HRecord("Arsenal", "Chelsea", 2, 10)

	if h2h == nil {
		t.Fatal("expected H2H record, got nil")
	}
	if h2h.TotalMatches() == 0 {
		t.Error("expected non-zero total matches")
	}
	if h2h.HomeTeam != "Arsenal" {
		t.Errorf("expected HomeTeam=Arsenal, got %s", h2h.HomeTeam)
	}
}

func TestGetH2HRecord_InsufficientData(t *testing.T) {
	// Only 2 H2H matches — below the minimum of 3
	fixtures := []HistoricalMatch{
		{Date: "2024-01-01", HomeTeam: "Arsenal", AwayTeam: "Chelsea", HomeGoals: 1, AwayGoals: 0, HomePossession: 55, AwayPossession: 45},
		{Date: "2024-02-01", HomeTeam: "Chelsea", AwayTeam: "Arsenal", HomeGoals: 0, AwayGoals: 1, HomePossession: 50, AwayPossession: 50},
	}
	builder := NewMatchContextBuilder(fixtures)
	h2h := builder.getH2HRecord("Arsenal", "Chelsea", 2, 10)

	if h2h != nil {
		t.Errorf("expected nil for insufficient data, got %+v", h2h)
	}
}

func TestGetH2HRecord_EmptyData(t *testing.T) {
	builder := NewMatchContextBuilder(nil)
	h2h := builder.getH2HRecord("Arsenal", "Chelsea", 2, 10)
	if h2h != nil {
		t.Errorf("expected nil with no historical data, got %+v", h2h)
	}
}

func TestGetH2HRecord_AnomalyTrigger(t *testing.T) {
	// Arsenal=pos 2 (stronger), Chelsea=pos 10 (weaker)
	// Last 3 H2H results: Chelsea unbeaten (D, D, W from Chelsea's perspective)
	fixtures := []HistoricalMatch{
		{Date: "2023-01-01", HomeTeam: "Arsenal", AwayTeam: "Chelsea", HomeGoals: 3, AwayGoals: 0, HomePossession: 55, AwayPossession: 45},
		// Last 3: Chelsea unbeaten
		{Date: "2024-01-01", HomeTeam: "Arsenal", AwayTeam: "Chelsea", HomeGoals: 1, AwayGoals: 1, HomePossession: 55, AwayPossession: 45},
		{Date: "2024-05-01", HomeTeam: "Arsenal", AwayTeam: "Chelsea", HomeGoals: 0, AwayGoals: 2, HomePossession: 57, AwayPossession: 43},
		{Date: "2024-09-01", HomeTeam: "Arsenal", AwayTeam: "Chelsea", HomeGoals: 2, AwayGoals: 2, HomePossession: 56, AwayPossession: 44},
	}
	builder := NewMatchContextBuilder(fixtures)
	h2h := builder.getH2HRecord("Arsenal", "Chelsea", 2, 10)

	if h2h == nil {
		t.Fatal("expected H2H record, got nil")
	}
	if !h2h.AnomalyTriggered {
		t.Errorf("expected AnomalyTriggered=true, streak=%d", h2h.WeakerTeamUnbeatenStreak)
	}
	if h2h.WeakerTeamUnbeatenStreak < 3 {
		t.Errorf("expected streak >= 3, got %d", h2h.WeakerTeamUnbeatenStreak)
	}
}

func TestGetH2HRecord_CachesResult(t *testing.T) {
	builder := NewMatchContextBuilder(makeH2HFixtures())

	h2h1 := builder.getH2HRecord("Arsenal", "Chelsea", 2, 10)
	h2h2 := builder.getH2HRecord("Arsenal", "Chelsea", 2, 10)

	if h2h1 != h2h2 {
		t.Error("expected same pointer on second call (cached)")
	}
}

func TestCalculateSeasonStats_WithData(t *testing.T) {
	builder := NewMatchContextBuilder(makeSeasonFixtures())
	stats := builder.calculateSeasonStats("Chelsea", "away")

	if stats == nil {
		t.Fatal("expected season stats, got nil")
	}
	awayDrawRate, ok := stats["awayDrawRate"].(float64)
	if !ok {
		t.Fatal("awayDrawRate missing or wrong type")
	}
	// 3 draws out of 5 away games = 0.6
	if awayDrawRate < 0.5 {
		t.Errorf("expected awayDrawRate >= 0.5, got %.2f", awayDrawRate)
	}
}

func TestCalculateSeasonStats_EmptyData(t *testing.T) {
	builder := NewMatchContextBuilder(nil)
	stats := builder.calculateSeasonStats("Chelsea", "away")
	if stats != nil {
		t.Error("expected nil stats with no historical data")
	}
}

func TestSetHistoricalData_InvalidatesCaches(t *testing.T) {
	builder := NewMatchContextBuilder(makeH2HFixtures())

	// Prime the cache
	builder.getH2HRecord("Arsenal", "Chelsea", 2, 10)
	builder.calculateSeasonStats("Chelsea", "away")

	if len(builder.h2hCache) == 0 && len(builder.seasonStatsCache) == 0 {
		t.Skip("nothing cached yet, skipping invalidation test")
	}

	// Update with empty data — caches should be cleared
	builder.SetHistoricalData(nil)

	if len(builder.h2hCache) != 0 {
		t.Errorf("expected empty h2hCache after SetHistoricalData, got %d entries", len(builder.h2hCache))
	}
	if len(builder.seasonStatsCache) != 0 {
		t.Errorf("expected empty seasonStatsCache after SetHistoricalData, got %d entries", len(builder.seasonStatsCache))
	}
}

func TestBuildContext_PopulatesH2HAndSeasonStats(t *testing.T) {
	all := append(makeH2HFixtures(), makeSeasonFixtures()...)
	builder := NewMatchContextBuilder(all)

	ctx := builder.BuildContext(
		"Arsenal", "Chelsea",
		55.0, 45.0, // possession
		2, 10, // positions
		"WWDLW", "DWWLD", // form
	)

	if ctx == nil {
		t.Fatal("expected non-nil context")
	}
	if ctx.H2HRecord == nil {
		t.Error("expected H2HRecord to be populated")
	}
	if ctx.AwaySeasonStats == nil {
		t.Error("expected AwaySeasonStats to be populated")
	}
}
