package domain

import (
	"testing"
)

func TestFactorResult_Validate(t *testing.T) {
	tests := []struct {
		name    string
		factor  FactorResult
		wantErr bool
	}{
		{
			name: "valid factor",
			factor: FactorResult{
				Name: "expectedGoals", Value: 0.65, Weight: 0.12,
				Triggered: true, Confidence: 85, Explanation: "test",
				Metadata: map[string]any{},
			},
			wantErr: false,
		},
		{
			name: "neutral factor",
			factor: FactorResult{
				Name: "test", Value: 0.5, Weight: 0.0,
				Triggered: false, Confidence: 0, Explanation: "inactive",
				Metadata: map[string]any{},
			},
			wantErr: false,
		},
		{
			name: "value too high",
			factor: FactorResult{
				Name: "test", Value: 1.5, Weight: 0.1,
				Triggered: true, Confidence: 50, Explanation: "test",
			},
			wantErr: true,
		},
		{
			name: "value too low",
			factor: FactorResult{
				Name: "test", Value: -1.5, Weight: 0.1,
				Triggered: true, Confidence: 50, Explanation: "test",
			},
			wantErr: true,
		},
		{
			name: "confidence too high",
			factor: FactorResult{
				Name: "test", Value: 0.5, Weight: 0.1,
				Triggered: true, Confidence: 150, Explanation: "test",
			},
			wantErr: true,
		},
		{
			name: "negative weight",
			factor: FactorResult{
				Name: "test", Value: 0.5, Weight: -0.1,
				Triggered: true, Confidence: 50, Explanation: "test",
			},
			wantErr: true,
		},
		{
			name: "nil metadata gets initialized",
			factor: FactorResult{
				Name: "test", Value: 0.5, Weight: 0.1,
				Triggered: true, Confidence: 50, Explanation: "test",
				Metadata: nil,
			},
			wantErr: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.factor.Validate()
			if (err != nil) != tt.wantErr {
				t.Errorf("Validate() error = %v, wantErr %v", err, tt.wantErr)
			}
			// Nil metadata should be initialized
			if !tt.wantErr && tt.factor.Metadata == nil {
				t.Error("nil metadata was not initialized")
			}
		})
	}
}

func TestNewInactiveFactorResult(t *testing.T) {
	f := NewInactiveFactorResult("h2hAnomaly", "No H2H data")
	if f.Name != "h2hAnomaly" {
		t.Errorf("Name = %q, want %q", f.Name, "h2hAnomaly")
	}
	if f.Value != 0.5 {
		t.Errorf("Value = %f, want 0.5", f.Value)
	}
	if f.Weight != 0.0 {
		t.Errorf("Weight = %f, want 0.0", f.Weight)
	}
	if f.Triggered {
		t.Error("Triggered should be false")
	}
	if f.Confidence != 0 {
		t.Errorf("Confidence = %d, want 0", f.Confidence)
	}
	if err := f.Validate(); err != nil {
		t.Errorf("Validate() unexpected error: %v", err)
	}
}

func TestManagerInfo_WinRate(t *testing.T) {
	tests := []struct {
		name     string
		results  []string
		expected float64
	}{
		{"empty", nil, 0.0},
		{"all wins", []string{"W", "W", "W"}, 1.0},
		{"mixed", []string{"W", "D", "L", "W", "D"}, 0.4},
		{"all losses", []string{"L", "L"}, 0.0},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			m := ManagerInfo{
				Name: "Test Manager", AppointmentDate: "2025-01-01",
				GamesManaged: len(tt.results), Results: tt.results,
			}
			got := m.WinRate()
			if got != tt.expected {
				t.Errorf("WinRate() = %f, want %f", got, tt.expected)
			}
		})
	}
}

func TestManagerInfo_Validate(t *testing.T) {
	tests := []struct {
		name    string
		info    ManagerInfo
		wantErr bool
	}{
		{
			name: "valid",
			info: ManagerInfo{
				Name: "Arteta", AppointmentDate: "2024-01-01",
				GamesManaged: 10, Results: []string{"W", "D", "L"},
			},
			wantErr: false,
		},
		{
			name: "negative games",
			info: ManagerInfo{
				Name: "Test", AppointmentDate: "2024-01-01",
				GamesManaged: -1,
			},
			wantErr: true,
		},
		{
			name: "invalid result",
			info: ManagerInfo{
				Name: "Test", AppointmentDate: "2024-01-01",
				GamesManaged: 1, Results: []string{"X"},
			},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.info.Validate()
			if (err != nil) != tt.wantErr {
				t.Errorf("Validate() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

func TestH2HRecord_Stats(t *testing.T) {
	h := H2HRecord{
		HomeTeam: "Arsenal", AwayTeam: "Chelsea",
		Results: []H2HResult{
			{Date: "2024-01-01", HomeScore: 2, AwayScore: 1}, // Home win
			{Date: "2024-02-01", HomeScore: 1, AwayScore: 1}, // Draw
			{Date: "2024-03-01", HomeScore: 0, AwayScore: 3}, // Away win
			{Date: "2024-04-01", HomeScore: 1, AwayScore: 0}, // Home win
		},
	}

	if h.TotalMatches() != 4 {
		t.Errorf("TotalMatches() = %d, want 4", h.TotalMatches())
	}
	if h.HomeWins() != 2 {
		t.Errorf("HomeWins() = %d, want 2", h.HomeWins())
	}
	if h.Draws() != 1 {
		t.Errorf("Draws() = %d, want 1", h.Draws())
	}
	if h.AwayWins() != 1 {
		t.Errorf("AwayWins() = %d, want 1", h.AwayWins())
	}
	if h.WinRate("home") != 0.5 {
		t.Errorf("WinRate(home) = %f, want 0.5", h.WinRate("home"))
	}
	if h.WinRate("away") != 0.25 {
		t.Errorf("WinRate(away) = %f, want 0.25", h.WinRate("away"))
	}
}

func TestMatchContext_Validate(t *testing.T) {
	ctx := NewNeutralContext()
	if err := ctx.Validate(); err != nil {
		t.Errorf("NewNeutralContext().Validate() unexpected error: %v", err)
	}

	// Invalid form
	ctx2 := NewNeutralContext()
	ctx2.HomeRecentForm = []string{"W", "X", "L"}
	if err := ctx2.Validate(); err == nil {
		t.Error("expected error for invalid form result")
	}

	// Invalid position
	ctx3 := NewNeutralContext()
	ctx3.HomeLeaguePosition = 0
	if err := ctx3.Validate(); err == nil {
		t.Error("expected error for position < 1")
	}
}

func TestMatchContext_RecentWins(t *testing.T) {
	ctx := &MatchContext{
		HomeDefensiveStyle: DefensiveStyleBalanced,
		AwayDefensiveStyle: DefensiveStyleBalanced,
		HomeLeaguePosition: 1,
		AwayLeaguePosition: 10,
		HomeRecentForm:     []string{"W", "W", "D", "W", "L"},
		AwayRecentForm:     []string{"L", "L", "L", "L", "L"},
	}

	if got := ctx.RecentWins("home", 4); got != 2 {
		t.Errorf("RecentWins(home, 4) = %d, want 2", got)
	}
	if got := ctx.RecentWins("away", 4); got != 0 {
		t.Errorf("RecentWins(away, 4) = %d, want 0", got)
	}
}

func TestMatchContext_IsRelegationThreatened(t *testing.T) {
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
		t.Error("position 5 should NOT be relegation threatened")
	}
}
