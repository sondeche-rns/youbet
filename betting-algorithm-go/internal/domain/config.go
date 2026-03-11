package domain

import (
	"os"
	"strconv"
	"strings"
)

// AppConfig holds application-level configuration loaded from environment.
type AppConfig struct {
	OddsAPIKey       string  `json:"odds_api_key"`
	APIFootballKey   string  `json:"api_football_key"`
	DefaultSport     string  `json:"default_sport"`
	InitialBankroll  float64 `json:"initial_bankroll"`
	MaxBetPercentage float64 `json:"max_bet_percentage"`
	KellyFraction    float64 `json:"kelly_fraction"`
	Port             string  `json:"port"`
}

// LoadAppConfig reads configuration from environment variables with defaults.
func LoadAppConfig() AppConfig {
	return AppConfig{
		OddsAPIKey:       getEnv("ODDS_API_KEY", ""),
		APIFootballKey:   getEnv("API_FOOTBALL_KEY", ""),
		DefaultSport:     getEnv("DEFAULT_SPORT", "football"),
		InitialBankroll:  getEnvFloat("INITIAL_BANKROLL", 1000),
		MaxBetPercentage: getEnvFloat("MAX_BET_PERCENTAGE", 5),
		KellyFraction:    getEnvFloat("KELLY_FRACTION", 0.25),
		Port:             getEnv("PORT", "5000"),
	}
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func getEnvFloat(key string, fallback float64) float64 {
	if v := os.Getenv(key); v != "" {
		f, err := strconv.ParseFloat(v, 64)
		if err == nil {
			return f
		}
	}
	return fallback
}

// FootballWeights are the original V1 factor weights.
var FootballWeights = map[string]float64{
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

// FootballWeightsV2 are the enhanced V2/V3 factor weights with contextual factors.
// All defined weights (including conditional h2hAnomaly) sum to ~1.0.
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
	"h2hHistorical":           0.04,
	"h2hAnomaly":              0.12,
	"possessionQuality":       0.07,
	"managerMomentum":         0.04,
	"relegationMotivation":    0.04,
	"counterAttackEfficiency": 0.04,
	"awayDrawFrequency":       0.03,
}

// ConditionalFactorRule defines rules for conditional factor activation.
type ConditionalFactorRule struct {
	Replaces         string  `json:"replaces"`
	WeightMultiplier float64 `json:"weight_multiplier"`
	TriggerCondition string  `json:"trigger_condition"`
}

// ManagerMomentumRule defines the decay formula for manager momentum.
type ManagerMomentumRule struct {
	DecayFormula      string  `json:"decay_formula"`
	BaseBoost         float64 `json:"base_boost"`
	InterimMultiplier float64 `json:"interim_multiplier"`
	MinThreshold      float64 `json:"min_threshold"`
}

// ConditionalFactors defines the conditional factor rules.
var ConditionalFactors = struct {
	H2HAnomaly      ConditionalFactorRule
	ManagerMomentum ManagerMomentumRule
}{
	H2HAnomaly: ConditionalFactorRule{
		Replaces:         "h2hHistorical",
		WeightMultiplier: 3.0,
		TriggerCondition: "weaker_team_unbeaten_streak >= 3",
	},
	ManagerMomentum: ManagerMomentumRule{
		DecayFormula:      "baseBoost * (0.85 ^ gamesManaged)",
		BaseBoost:         0.08,
		InterimMultiplier: 0.7,
		MinThreshold:      0.01,
	},
}

// WeightNormalizationMode controls how weights are normalized at runtime.
const WeightNormalizationMode = "dynamic"

// TeamData holds static data for a Premier League team.
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

// PremierLeagueTeams is the EPL team database.
var PremierLeagueTeams = map[string]TeamData{
	"Arsenal": {
		Elo: 1800, Position: 1, Form: "WWDWW", Stars: 5,
		HomeXGAvg: 2.2, AwayXGAvg: 1.8, Style: StyleAttacking,
		Aliases: []string{"Arsenal FC"},
	},
	"Manchester City": {
		Elo: 1760, Position: 2, Form: "WLWWW", Stars: 5,
		HomeXGAvg: 2.3, AwayXGAvg: 1.9, Style: StyleAttacking,
		Aliases: []string{"Man City", "Man. City"},
	},
	"Aston Villa": {
		Elo: 1720, Position: 3, Form: "WWDWL", Stars: 4,
		HomeXGAvg: 1.8, AwayXGAvg: 1.4, Style: StyleBalanced,
		Aliases: []string{"Villa", "Aston Villa FC"},
	},
	"Manchester United": {
		Elo: 1700, Position: 4, Form: "WDWWD", Stars: 4,
		HomeXGAvg: 1.7, AwayXGAvg: 1.3, Style: StyleBalanced,
		Aliases: []string{"Man United", "Man Utd", "Man. United"},
	},
	"Chelsea": {
		Elo: 1690, Position: 5, Form: "WWDLW", Stars: 4,
		HomeXGAvg: 1.9, AwayXGAvg: 1.5, Style: StyleAttacking,
		Aliases: []string{"Chelsea FC"},
	},
	"Liverpool": {
		Elo: 1680, Position: 6, Form: "WDLWW", Stars: 5,
		HomeXGAvg: 1.8, AwayXGAvg: 1.5, Style: StyleAttacking,
		Aliases: []string{"Liverpool FC"},
	},
	"Brentford": {
		Elo: 1640, Position: 7, Form: "WLLWW", Stars: 3,
		HomeXGAvg: 1.6, AwayXGAvg: 1.2, Style: StyleAttacking,
		Aliases: []string{"Brentford FC"},
	},
	"Everton": {
		Elo: 1610, Position: 8, Form: "DWDWL", Stars: 3,
		HomeXGAvg: 1.4, AwayXGAvg: 1.0, Style: StyleDefensive,
		Aliases: []string{"Everton FC"},
	},
	"Bournemouth": {
		Elo: 1610, Position: 9, Form: "DDDWW", Stars: 3,
		HomeXGAvg: 1.5, AwayXGAvg: 1.1, Style: StyleBalanced,
		Aliases: []string{"AFC Bournemouth", "Bournemouth FC"},
	},
	"Newcastle": {
		Elo: 1610, Position: 10, Form: "WLWDW", Stars: 4,
		HomeXGAvg: 1.6, AwayXGAvg: 1.2, Style: StyleBalanced,
		Aliases: []string{"Newcastle United", "Newcastle Utd"},
	},
	"Sunderland": {
		Elo: 1590, Position: 11, Form: "DWDWL", Stars: 3,
		HomeXGAvg: 1.3, AwayXGAvg: 1.0, Style: StyleDefensive,
		Aliases: []string{"Sunderland AFC"},
	},
	"Fulham": {
		Elo: 1570, Position: 12, Form: "WLWLD", Stars: 3,
		HomeXGAvg: 1.4, AwayXGAvg: 1.1, Style: StyleBalanced,
		Aliases: []string{"Fulham FC"},
	},
	"Crystal Palace": {
		Elo: 1550, Position: 13, Form: "DWDLW", Stars: 3,
		HomeXGAvg: 1.3, AwayXGAvg: 1.0, Style: StyleBalanced,
		Aliases: []string{"C. Palace", "Palace"},
	},
	"Brighton": {
		Elo: 1540, Position: 14, Form: "DLDWD", Stars: 3,
		HomeXGAvg: 1.5, AwayXGAvg: 1.2, Style: StyleAttacking,
		Aliases: []string{"Brighton & Hove Albion", "Brighton and Hove Albion", "Brighton FC"},
	},
	"Leeds United": {
		Elo: 1520, Position: 15, Form: "DLLWD", Stars: 3,
		HomeXGAvg: 1.3, AwayXGAvg: 0.9, Style: StyleBalanced,
		Aliases: []string{"Leeds", "Leeds Utd"},
	},
	"Tottenham": {
		Elo: 1510, Position: 16, Form: "LLDLW", Stars: 4,
		HomeXGAvg: 1.4, AwayXGAvg: 1.1, Style: StyleBalanced,
		Aliases: []string{"Tottenham Hotspur", "Spurs", "Tottenham FC"},
	},
	"Nottingham": {
		Elo: 1470, Position: 17, Form: "DLLDW", Stars: 3,
		HomeXGAvg: 1.2, AwayXGAvg: 0.8, Style: StyleDefensive,
		Aliases: []string{"Nottingham Forest", "Nott'm Forest", "Nottm Forest"},
	},
	"West Ham": {
		Elo: 1440, Position: 18, Form: "WDLLL", Stars: 3,
		HomeXGAvg: 1.1, AwayXGAvg: 0.9, Style: StyleDefensive,
		Aliases: []string{"West Ham United", "West Ham Utd"},
	},
	"Burnley": {
		Elo: 1380, Position: 19, Form: "LLLLD", Stars: 2,
		HomeXGAvg: 1.0, AwayXGAvg: 0.8, Style: StyleDefensive,
		Aliases: []string{"Burnley FC"},
	},
	"Wolverhampton": {
		Elo: 1320, Position: 20, Form: "LLDLL", Stars: 2,
		HomeXGAvg: 0.9, AwayXGAvg: 0.7, Style: StyleDefensive,
		Aliases: []string{"Wolverhampton Wanderers", "Wolves", "Wolverhampton W."},
	},
}

// LookupTeam finds team data by name or alias. Returns nil if not found.
func LookupTeam(teamName string) (*TeamData, string) {
	name := strings.TrimSpace(strings.ToLower(teamName))
	for canonical, data := range PremierLeagueTeams {
		if strings.ToLower(canonical) == name {
			d := data
			return &d, canonical
		}
		for _, alias := range data.Aliases {
			if strings.ToLower(alias) == name {
				d := data
				return &d, canonical
			}
		}
	}
	return nil, ""
}
