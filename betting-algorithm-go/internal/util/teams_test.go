package util

import "testing"

func TestNormalizeTeamName(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"Man United", "Manchester United"},
		{"Man City", "Manchester City"},
		{"Spurs", "Tottenham"},
		{"Tottenham Hotspur", "Tottenham"},
		{"Wolves", "Wolverhampton"},
		{"Wolverhampton Wanderers", "Wolverhampton"},
		{"Brighton & Hove Albion", "Brighton"},
		{"West Ham United", "West Ham"},
		{"Newcastle United", "Newcastle"},
		{"Nottingham Forest", "Nottm Forest"},
		{"Inter Milan", "Inter"},
		{"AC Milan", "Milan"},
		{"Bayern Munich", "Bayern"},
		{"Borussia Dortmund", "Dortmund"},
		// Name not in map - should pass through
		{"Arsenal", "Arsenal"},
		{"Liverpool", "Liverpool"},
		{"Unknown FC", "Unknown FC"},
	}

	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			got := NormalizeTeamName(tt.input)
			if got != tt.expected {
				t.Errorf("NormalizeTeamName(%q) = %q, want %q", tt.input, got, tt.expected)
			}
		})
	}
}
