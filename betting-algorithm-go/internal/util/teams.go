package util

// teamNameMap maps common alternative names to their canonical form.
var teamNameMap = map[string]string{
	// Premier League
	"Man United":                "Manchester United",
	"Man City":                  "Manchester City",
	"Spurs":                     "Tottenham",
	"Tottenham Hotspur":         "Tottenham",
	"Wolves":                    "Wolverhampton",
	"Wolverhampton Wanderers":   "Wolverhampton",
	"Brighton & Hove Albion":    "Brighton",
	"Brighton and Hove Albion":  "Brighton",
	"West Ham United":           "West Ham",
	"Newcastle United":          "Newcastle",
	"Leicester City":            "Leicester",
	"Leeds United":              "Leeds",
	"Nottingham Forest":         "Nottm Forest",
	"Luton Town":                "Luton",
	"Sheffield United":          "Sheffield Utd",
	// La Liga
	"Atletico Madrid":  "Atl Madrid",
	"Athletic Bilbao":  "Ath Bilbao",
	// Serie A
	"Inter Milan": "Inter",
	"AC Milan":    "Milan",
	// Bundesliga
	"Bayern Munich":      "Bayern",
	"Borussia Dortmund":  "Dortmund",
	"RB Leipzig":         "Leipzig",
}

// NormalizeTeamName normalizes a team name using the standard mapping.
// Returns the canonical name if a mapping exists, otherwise returns the original.
func NormalizeTeamName(name string) string {
	if canonical, ok := teamNameMap[name]; ok {
		return canonical
	}
	return name
}
