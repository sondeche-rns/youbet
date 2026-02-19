package domain

import (
	"math"
	"testing"
)

func TestFootballWeightsV1_SumToOne(t *testing.T) {
	var sum float64
	for _, w := range FootballWeightsV1 {
		sum += w
	}
	if math.Abs(sum-1.0) > 0.01 {
		t.Errorf("V1 weights sum = %f, want ~1.0", sum)
	}
}

func TestFootballWeightsV2_SumToOne(t *testing.T) {
	var sum float64
	for _, w := range FootballWeightsV2 {
		sum += w
	}
	// V2 includes conditional h2hAnomaly, total defined weights sum to ~1.0
	if math.Abs(sum-1.0) > 0.02 {
		t.Errorf("V2 weights sum = %f, want ~1.0", sum)
	}
}

func TestFootballWeightsV2_HasAllFactors(t *testing.T) {
	expectedFactors := []string{
		"expectedGoals", "advancedStats", "teamStrength", "tacticalMatchup",
		"currentForm", "playerImpact", "restAndFatigue", "motivation",
		"homeAdvantage", "externalFactors", "teamQualityGap",
		"h2hHistorical", "h2hAnomaly", "possessionQuality",
		"managerMomentum", "relegationMotivation", "counterAttackEfficiency",
		"awayDrawFrequency",
	}

	for _, name := range expectedFactors {
		if _, ok := FootballWeightsV2[name]; !ok {
			t.Errorf("missing factor weight: %s", name)
		}
	}
}

func TestLookupTeam_ByCanonicalName(t *testing.T) {
	data, canonical := LookupTeam("Arsenal")
	if data == nil {
		t.Fatal("LookupTeam(Arsenal) returned nil")
	}
	if canonical != "Arsenal" {
		t.Errorf("canonical = %q, want %q", canonical, "Arsenal")
	}
	if data.Elo != 1800 {
		t.Errorf("Elo = %d, want 1800", data.Elo)
	}
}

func TestLookupTeam_ByAlias(t *testing.T) {
	tests := []struct {
		alias     string
		wantName  string
	}{
		{"Man City", "Manchester City"},
		{"Man United", "Manchester United"},
		{"Spurs", "Tottenham"},
		{"Wolves", "Wolverhampton"},
		{"Brighton & Hove Albion", "Brighton"},
		{"West Ham United", "West Ham"},
		{"Nottingham Forest", "Nottingham"},
	}

	for _, tt := range tests {
		t.Run(tt.alias, func(t *testing.T) {
			data, canonical := LookupTeam(tt.alias)
			if data == nil {
				t.Fatalf("LookupTeam(%q) returned nil", tt.alias)
			}
			if canonical != tt.wantName {
				t.Errorf("canonical = %q, want %q", canonical, tt.wantName)
			}
		})
	}
}

func TestLookupTeam_CaseInsensitive(t *testing.T) {
	data, _ := LookupTeam("arsenal")
	if data == nil {
		t.Fatal("LookupTeam(arsenal) should match case-insensitively")
	}
	data2, _ := LookupTeam("CHELSEA")
	if data2 == nil {
		t.Fatal("LookupTeam(CHELSEA) should match case-insensitively")
	}
}

func TestLookupTeam_NotFound(t *testing.T) {
	data, canonical := LookupTeam("Unknown FC")
	if data != nil {
		t.Error("expected nil for unknown team")
	}
	if canonical != "" {
		t.Errorf("canonical = %q, want empty", canonical)
	}
}

func TestPremierLeagueTeams_HasAllTeams(t *testing.T) {
	if len(PremierLeagueTeams) != 20 {
		t.Errorf("PremierLeagueTeams has %d teams, want 20", len(PremierLeagueTeams))
	}
}

func TestDefaultAppConfig(t *testing.T) {
	cfg := DefaultAppConfig()
	if cfg.InitialBankroll != 1000 {
		t.Errorf("InitialBankroll = %f, want 1000", cfg.InitialBankroll)
	}
	if cfg.KellyFraction != 0.25 {
		t.Errorf("KellyFraction = %f, want 0.25", cfg.KellyFraction)
	}
	if cfg.MaxBetPct != 5 {
		t.Errorf("MaxBetPct = %f, want 5", cfg.MaxBetPct)
	}
}
