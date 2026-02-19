package domain

// TeamData holds the static reference data for a known team.
type TeamData struct {
	Elo        int       `json:"elo"`
	Position   int       `json:"position"`
	Form       string    `json:"form"`
	Stars      int       `json:"stars"`
	HomeXGAvg  float64   `json:"home_xg_avg"`
	AwayXGAvg  float64   `json:"away_xg_avg"`
	Style      PlayStyle `json:"style"`
	Aliases    []string  `json:"aliases"`
}

// ConditionalFactorRule defines the activation rules for conditional factors.
type ConditionalFactorRule struct {
	Replaces         string  `json:"replaces,omitempty"`
	WeightMultiplier float64 `json:"weight_multiplier,omitempty"`
	TriggerCondition string  `json:"trigger_condition,omitempty"`
	DecayFormula     string  `json:"decay_formula,omitempty"`
	BaseBoost        float64 `json:"base_boost,omitempty"`
	InterimMultiplier float64 `json:"interim_multiplier,omitempty"`
	MinThreshold     float64 `json:"min_threshold,omitempty"`
}

// AppConfig holds the algorithm-level configuration loaded from environment.
type AppConfig struct {
	OddsAPIKey      string  `json:"odds_api_key"`
	APIFootballKey  string  `json:"api_football_key"`
	DefaultSport    string  `json:"default_sport"`
	InitialBankroll float64 `json:"initial_bankroll"`
	MaxBetPct       float64 `json:"max_bet_percentage"`
	KellyFraction   float64 `json:"kelly_fraction"`
}

// DefaultAppConfig returns the default application configuration.
func DefaultAppConfig() AppConfig {
	return AppConfig{
		DefaultSport:    "football",
		InitialBankroll: 1000,
		MaxBetPct:       5,
		KellyFraction:   0.25,
	}
}

// FootballWeightsV1 returns the original 10-factor weight map.
var FootballWeightsV1 = map[string]float64{
	"expectedGoals":   0.20,
	"advancedStats":   0.15,
	"teamStrength":    0.12,
	"tacticalMatchup": 0.12,
	"currentForm":     0.10,
	"playerImpact":    0.10,
	"restAndFatigue":  0.08,
	"motivation":      0.06,
	"homeAdvantage":   0.05,
	"externalFactors": 0.02,
}

// FootballWeightsV2 returns the enhanced 17-factor weight map (V3 update).
// NOTE: All defined weights (including conditional h2hAnomaly) sum to ~1.0.
// At runtime, only active factors are used and renormalized dynamically.
var FootballWeightsV2 = map[string]float64{
	// Original factors (rebalanced)
	"expectedGoals":   0.12,
	"advancedStats":   0.07,
	"teamStrength":    0.07,
	"tacticalMatchup": 0.06,
	"currentForm":     0.05,
	"playerImpact":    0.05,
	"restAndFatigue":  0.04,
	"motivation":      0.03,
	"homeAdvantage":   0.02,
	"externalFactors": 0.01,

	// Team Quality Gap
	"teamQualityGap": 0.10,

	// Contextual factors
	"h2hHistorical":          0.04,
	"h2hAnomaly":             0.12,
	"possessionQuality":      0.07,
	"managerMomentum":        0.04,
	"relegationMotivation":   0.04,
	"counterAttackEfficiency": 0.04,
	"awayDrawFrequency":      0.03,
}

// ConditionalFactors defines the activation rules for conditional factors.
var ConditionalFactors = map[string]ConditionalFactorRule{
	"h2hAnomaly": {
		Replaces:         "h2hHistorical",
		WeightMultiplier: 3.0,
		TriggerCondition: "weaker_team_unbeaten_streak >= 3",
	},
	"managerMomentum": {
		DecayFormula:     "baseBoost * (0.85 ^ gamesManaged)",
		BaseBoost:        0.08,
		InterimMultiplier: 0.7,
		MinThreshold:     0.01,
	},
}

// PremierLeagueTeams is the EPL team database (Updated: Feb 2026, GW25).
var PremierLeagueTeams = map[string]TeamData{
	"Arsenal": {
		Elo: 1800, Position: 1, Form: "WWDWW", Stars: 5,
		HomeXGAvg: 2.2, AwayXGAvg: 1.8, Style: PlayStyleAttacking,
		Aliases: []string{"Arsenal FC"},
	},
	"Manchester City": {
		Elo: 1760, Position: 2, Form: "WLWWW", Stars: 5,
		HomeXGAvg: 2.3, AwayXGAvg: 1.9, Style: PlayStyleAttacking,
		Aliases: []string{"Man City", "Man. City"},
	},
	"Aston Villa": {
		Elo: 1720, Position: 3, Form: "WWDWL", Stars: 4,
		HomeXGAvg: 1.8, AwayXGAvg: 1.4, Style: PlayStyleBalanced,
		Aliases: []string{"Villa", "Aston Villa FC"},
	},
	"Manchester United": {
		Elo: 1700, Position: 4, Form: "WDWWD", Stars: 4,
		HomeXGAvg: 1.7, AwayXGAvg: 1.3, Style: PlayStyleBalanced,
		Aliases: []string{"Man United", "Man Utd", "Man. United"},
	},
	"Chelsea": {
		Elo: 1690, Position: 5, Form: "WWDLW", Stars: 4,
		HomeXGAvg: 1.9, AwayXGAvg: 1.5, Style: PlayStyleAttacking,
		Aliases: []string{"Chelsea FC"},
	},
	"Liverpool": {
		Elo: 1680, Position: 6, Form: "WDLWW", Stars: 5,
		HomeXGAvg: 1.8, AwayXGAvg: 1.5, Style: PlayStyleAttacking,
		Aliases: []string{"Liverpool FC"},
	},
	"Brentford": {
		Elo: 1640, Position: 7, Form: "WLLWW", Stars: 3,
		HomeXGAvg: 1.6, AwayXGAvg: 1.2, Style: PlayStyleAttacking,
		Aliases: []string{"Brentford FC"},
	},
	"Everton": {
		Elo: 1610, Position: 8, Form: "DWDWL", Stars: 3,
		HomeXGAvg: 1.4, AwayXGAvg: 1.0, Style: PlayStyleDefensive,
		Aliases: []string{"Everton FC"},
	},
	"Bournemouth": {
		Elo: 1610, Position: 9, Form: "DDDWW", Stars: 3,
		HomeXGAvg: 1.5, AwayXGAvg: 1.1, Style: PlayStyleBalanced,
		Aliases: []string{"AFC Bournemouth", "Bournemouth FC"},
	},
	"Newcastle": {
		Elo: 1610, Position: 10, Form: "WLWDW", Stars: 4,
		HomeXGAvg: 1.6, AwayXGAvg: 1.2, Style: PlayStyleBalanced,
		Aliases: []string{"Newcastle United", "Newcastle Utd"},
	},
	"Sunderland": {
		Elo: 1590, Position: 11, Form: "DWDWL", Stars: 3,
		HomeXGAvg: 1.3, AwayXGAvg: 1.0, Style: PlayStyleDefensive,
		Aliases: []string{"Sunderland AFC"},
	},
	"Fulham": {
		Elo: 1570, Position: 12, Form: "WLWLD", Stars: 3,
		HomeXGAvg: 1.4, AwayXGAvg: 1.1, Style: PlayStyleBalanced,
		Aliases: []string{"Fulham FC"},
	},
	"Crystal Palace": {
		Elo: 1550, Position: 13, Form: "DWDLW", Stars: 3,
		HomeXGAvg: 1.3, AwayXGAvg: 1.0, Style: PlayStyleBalanced,
		Aliases: []string{"C. Palace", "Palace"},
	},
	"Brighton": {
		Elo: 1540, Position: 14, Form: "DLDWD", Stars: 3,
		HomeXGAvg: 1.5, AwayXGAvg: 1.2, Style: PlayStyleAttacking,
		Aliases: []string{"Brighton & Hove Albion", "Brighton and Hove Albion", "Brighton FC"},
	},
	"Leeds United": {
		Elo: 1520, Position: 15, Form: "DLLWD", Stars: 3,
		HomeXGAvg: 1.3, AwayXGAvg: 0.9, Style: PlayStyleBalanced,
		Aliases: []string{"Leeds", "Leeds Utd"},
	},
	"Tottenham": {
		Elo: 1510, Position: 16, Form: "LLDLW", Stars: 4,
		HomeXGAvg: 1.4, AwayXGAvg: 1.1, Style: PlayStyleBalanced,
		Aliases: []string{"Tottenham Hotspur", "Spurs", "Tottenham FC"},
	},
	"Nottingham": {
		Elo: 1470, Position: 17, Form: "DLLDW", Stars: 3,
		HomeXGAvg: 1.2, AwayXGAvg: 0.8, Style: PlayStyleDefensive,
		Aliases: []string{"Nottingham Forest", "Nott'm Forest", "Nottm Forest"},
	},
	"West Ham": {
		Elo: 1440, Position: 18, Form: "WDLLL", Stars: 3,
		HomeXGAvg: 1.1, AwayXGAvg: 0.9, Style: PlayStyleDefensive,
		Aliases: []string{"West Ham United", "West Ham Utd"},
	},
	"Burnley": {
		Elo: 1380, Position: 19, Form: "LLLLD", Stars: 2,
		HomeXGAvg: 1.0, AwayXGAvg: 0.8, Style: PlayStyleDefensive,
		Aliases: []string{"Burnley FC"},
	},
	"Wolverhampton": {
		Elo: 1320, Position: 20, Form: "LLDLL", Stars: 2,
		HomeXGAvg: 0.9, AwayXGAvg: 0.7, Style: PlayStyleDefensive,
		Aliases: []string{"Wolverhampton Wanderers", "Wolves", "Wolverhampton W."},
	},
}

// LookupTeam looks up team data by name or alias. Returns nil if not found.
func LookupTeam(teamName string) (*TeamData, string) {
	normalized := normalizeForLookup(teamName)
	for canonical, data := range PremierLeagueTeams {
		if normalizeForLookup(canonical) == normalized {
			d := data // copy
			return &d, canonical
		}
		for _, alias := range data.Aliases {
			if normalizeForLookup(alias) == normalized {
				d := data // copy
				return &d, canonical
			}
		}
	}
	return nil, ""
}

func normalizeForLookup(s string) string {
	// Simple case-insensitive comparison by lowering and trimming
	result := make([]byte, 0, len(s))
	for i := 0; i < len(s); i++ {
		c := s[i]
		if c >= 'A' && c <= 'Z' {
			c += 'a' - 'A'
		}
		if c == ' ' && (len(result) == 0 || result[len(result)-1] == ' ') {
			continue
		}
		result = append(result, c)
	}
	// Trim trailing spaces
	for len(result) > 0 && result[len(result)-1] == ' ' {
		result = result[:len(result)-1]
	}
	return string(result)
}
