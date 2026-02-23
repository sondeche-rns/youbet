package domain

import (
	"testing"
)

func TestFactorResultValidate(t *testing.T) {
	tests := []struct {
		name    string
		fr      FactorResult
		wantErr bool
	}{
		{
			name: "valid factor result",
			fr: FactorResult{
				Name: "test", Value: 0.5, Weight: 0.1,
				Triggered: true, Confidence: 85, Explanation: "ok",
			},
			wantErr: false,
		},
		{
			name: "value too high",
			fr: FactorResult{
				Name: "test", Value: 1.5, Weight: 0.1,
				Triggered: true, Confidence: 50, Explanation: "bad",
			},
			wantErr: true,
		},
		{
			name: "value too low",
			fr: FactorResult{
				Name: "test", Value: -1.5, Weight: 0.1,
				Triggered: true, Confidence: 50, Explanation: "bad",
			},
			wantErr: true,
		},
		{
			name: "confidence too high",
			fr: FactorResult{
				Name: "test", Value: 0.5, Weight: 0.1,
				Triggered: true, Confidence: 150, Explanation: "bad",
			},
			wantErr: true,
		},
		{
			name: "negative weight",
			fr: FactorResult{
				Name: "test", Value: 0.5, Weight: -0.1,
				Triggered: true, Confidence: 50, Explanation: "bad",
			},
			wantErr: true,
		},
		{
			name: "nil metadata gets initialized",
			fr: FactorResult{
				Name: "test", Value: 0.0, Weight: 0.0,
				Triggered: false, Confidence: 0, Explanation: "ok",
				Metadata: nil,
			},
			wantErr: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.fr.Validate()
			if (err != nil) != tt.wantErr {
				t.Errorf("Validate() error = %v, wantErr %v", err, tt.wantErr)
			}
			if !tt.wantErr && tt.fr.Metadata == nil {
				t.Error("Metadata should be initialized after Validate()")
			}
		})
	}
}

func TestNewInactiveFactorResult(t *testing.T) {
	fr := NewInactiveFactorResult("testFactor", "not enough data")
	if fr.Name != "testFactor" {
		t.Errorf("expected name 'testFactor', got %q", fr.Name)
	}
	if fr.Value != 0.5 {
		t.Errorf("expected value 0.5, got %f", fr.Value)
	}
	if fr.Weight != 0.0 {
		t.Errorf("expected weight 0.0, got %f", fr.Weight)
	}
	if fr.Triggered {
		t.Error("expected triggered=false")
	}
	if fr.Confidence != 0 {
		t.Errorf("expected confidence 0, got %d", fr.Confidence)
	}
}

func TestManagerInfoValidate(t *testing.T) {
	m := &ManagerInfo{
		Name: "Test Manager", AppointmentDate: "2026-01-01",
		GamesManaged: 5, Results: []string{"W", "D", "L", "W", "W"},
	}
	if err := m.Validate(); err != nil {
		t.Errorf("unexpected error: %v", err)
	}

	m.GamesManaged = -1
	if err := m.Validate(); err == nil {
		t.Error("expected error for negative gamesManaged")
	}

	m.GamesManaged = 5
	m.Results = []string{"W", "X"}
	if err := m.Validate(); err == nil {
		t.Error("expected error for invalid result 'X'")
	}
}

func TestManagerInfoWinRate(t *testing.T) {
	m := &ManagerInfo{Results: []string{"W", "D", "L", "W", "W"}}
	rate := m.WinRate()
	expected := 3.0 / 5.0
	if rate != expected {
		t.Errorf("expected win rate %f, got %f", expected, rate)
	}

	m2 := &ManagerInfo{Results: []string{}}
	if m2.WinRate() != 0.0 {
		t.Error("expected 0.0 win rate for empty results")
	}
}

func TestH2HRecord(t *testing.T) {
	h := &H2HRecord{
		HomeTeam: "Arsenal",
		AwayTeam: "Chelsea",
		Results: []H2HResult{
			{Date: "2025-01-01", HomeScore: 2, AwayScore: 1},
			{Date: "2025-03-01", HomeScore: 1, AwayScore: 1},
			{Date: "2025-06-01", HomeScore: 0, AwayScore: 3},
		},
	}

	if h.TotalMatches() != 3 {
		t.Errorf("expected 3 total matches, got %d", h.TotalMatches())
	}
	if h.HomeWins() != 1 {
		t.Errorf("expected 1 home win, got %d", h.HomeWins())
	}
	if h.Draws() != 1 {
		t.Errorf("expected 1 draw, got %d", h.Draws())
	}
	if h.AwayWins() != 1 {
		t.Errorf("expected 1 away win, got %d", h.AwayWins())
	}

	homeRate := h.WinRate("home")
	if homeRate < 0.333 || homeRate > 0.334 {
		t.Errorf("expected home win rate ~0.333, got %f", homeRate)
	}
}

func TestMatchContextValidate(t *testing.T) {
	ctx := NewNeutralContext()
	if err := ctx.Validate(); err != nil {
		t.Errorf("neutral context should be valid: %v", err)
	}

	ctx.HomeRecentForm = []string{"W", "X"}
	if err := ctx.Validate(); err == nil {
		t.Error("expected error for invalid form result")
	}

	ctx2 := NewNeutralContext()
	ctx2.HomeLeaguePosition = 0
	if err := ctx2.Validate(); err == nil {
		t.Error("expected error for position < 1")
	}
}

func TestMatchContextRecentWins(t *testing.T) {
	ctx := &MatchContext{
		HomeDefensiveStyle: DefensiveStyleBalanced,
		AwayDefensiveStyle: DefensiveStyleBalanced,
		HomeLeaguePosition: 1,
		AwayLeaguePosition: 10,
		HomeRecentForm:     []string{"W", "W", "D", "W", "L"},
		AwayRecentForm:     []string{"L", "L", "L", "L", "L"},
	}

	if wins := ctx.RecentWins("home", 4); wins != 2 {
		t.Errorf("expected 2 recent home wins (last 4), got %d", wins)
	}
	if wins := ctx.RecentWins("away", 5); wins != 0 {
		t.Errorf("expected 0 away wins, got %d", wins)
	}
}

func TestMatchContextRelegation(t *testing.T) {
	ctx := &MatchContext{
		HomeDefensiveStyle: DefensiveStyleBalanced,
		AwayDefensiveStyle: DefensiveStyleBalanced,
		HomeLeaguePosition: 18,
		AwayLeaguePosition: 5,
		HomeRecentForm:     []string{"D"},
		AwayRecentForm:     []string{"D"},
	}

	if !ctx.IsRelegationThreatened("home") {
		t.Error("position 18 should be relegation threatened")
	}
	if ctx.IsRelegationThreatened("away") {
		t.Error("position 5 should not be relegation threatened")
	}
}

func TestDefensiveStyleValidate(t *testing.T) {
	if err := DefensiveStyleBalanced.Validate(); err != nil {
		t.Errorf("Balanced should be valid: %v", err)
	}
	if err := DefensiveStyle("invalid").Validate(); err == nil {
		t.Error("'invalid' should not be valid")
	}
}

func TestLookupTeam(t *testing.T) {
	data, canonical := LookupTeam("Arsenal")
	if data == nil || canonical != "Arsenal" {
		t.Error("should find Arsenal by canonical name")
	}

	data, canonical = LookupTeam("Man City")
	if data == nil || canonical != "Manchester City" {
		t.Error("should find Manchester City by alias 'Man City'")
	}

	data, canonical = LookupTeam("Spurs")
	if data == nil || canonical != "Tottenham" {
		t.Errorf("should find Tottenham by alias 'Spurs', got %q", canonical)
	}

	data, _ = LookupTeam("Nonexistent FC")
	if data != nil {
		t.Error("should return nil for unknown team")
	}
}
