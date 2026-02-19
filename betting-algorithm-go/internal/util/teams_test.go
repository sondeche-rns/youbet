package util

import "testing"

func TestNormalizeTeamName(t *testing.T) {
	tests := []struct {
		input string
		want  string
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
		{"Bayern Munich", "Bayern"},
		{"Borussia Dortmund", "Dortmund"},
		{"Inter Milan", "Inter"},
		{"AC Milan", "Milan"},
		// Names not in the map return as-is
		{"Arsenal", "Arsenal"},
		{"Chelsea", "Chelsea"},
		{"Unknown FC", "Unknown FC"},
	}

	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			got := NormalizeTeamName(tt.input)
			if got != tt.want {
				t.Errorf("NormalizeTeamName(%q) = %q, want %q", tt.input, got, tt.want)
			}
		})
	}
}
