package algorithm

import (
	"fmt"
	"math"

	"bet4me/internal/context"
	"bet4me/internal/domain"
)

// calculateAllFactors calculates all prediction factors (original 10 + new 6 contextual).
func (e *PredictionEngine) calculateAllFactors(data *MatchData) map[string]interface{} {
	factors := make(map[string]interface{})

	// Build match context for new factors
	contextBuilder := context.NewMatchContextBuilder(e.historicalData)
	matchContext := contextBuilder.BuildContext(data)

	// Original 10 factors
	factors["expectedGoals"] = e.calculateExpectedGoals(data)
	factors["advancedStats"] = e.calculateAdvancedStats(data)
	factors["teamStrength"] = e.calculateTeamStrength(data)
	factors["tacticalMatchup"] = e.analyzeTacticalMatchup(data)
	factors["currentForm"] = e.calculateCurrentForm(data)
	factors["playerImpact"] = e.calculatePlayerImpact(data)
	factors["restAndFatigue"] = e.calculateRestFatigue(data)
	factors["motivation"] = e.calculateMotivation(data)
	factors["homeAdvantage"] = e.calculateHomeAdvantage(data)
	factors["externalFactors"] = e.calculateExternalFactors(data)

	// Team Quality Gap (V3)
	factors["teamQualityGap"] = e.calculateTeamQualityGap(data)

	// Contextual factors (Version 2.0)
	h2hHist, h2hAnom := e.calculateH2HFactors(data, matchContext)
	factors["h2hHistorical"] = h2hHist
	factors["h2hAnomaly"] = h2hAnom
	factors["possessionQuality"] = e.calculatePossessionQuality(data, matchContext)
	factors["managerMomentum"] = e.calculateManagerMomentum(data, matchContext)
	factors["relegationMotivation"] = e.calculateRelegationMotivation(data, matchContext)
	factors["counterAttackEfficiency"] = e.calculateCounterAttackEfficiency(data, matchContext)
	factors["awayDrawFrequency"] = e.calculateAwayDrawFrequency(data, matchContext)

	return factors
}

// calculateExpectedGoals calculates the expected goals factor.
func (e *PredictionEngine) calculateExpectedGoals(data *MatchData) map[string]interface{} {
	homeXg := data.HomeXg
	awayXg := data.AwayXg

	// Normalize xG difference to -1 to 1 range
	xgDiff := homeXg - awayXg
	normalizedDiff := math.Tanh(xgDiff / 2) // Smooth normalization

	return map[string]interface{}{
		"homeXg":        homeXg,
		"awayXg":        awayXg,
		"xgDifferential": xgDiff,
		"homeAdvantage":  0.5 + normalizedDiff*0.3,
		"score":          0.5 + normalizedDiff*0.5,
	}
}

// calculateAdvancedStats calculates advanced statistics factor.
func (e *PredictionEngine) calculateAdvancedStats(data *MatchData) map[string]interface{} {
	// PPDA (Passes Per Defensive Action) - lower is more aggressive
	homePPDA := data.HomePPDA
	awayPPDA := data.AwayPPDA

	// Possession
	homePoss := data.HomePossession
	awayPoss := data.AwayPossession

	// Shot accuracy
	homeAccuracy := float64(data.HomeShotsOnTarget) / math.Max(float64(data.HomeShots), 1)
	awayAccuracy := float64(data.AwayShotsOnTarget) / math.Max(float64(data.AwayShots), 1)

	// Combine metrics
	homeScore := (1-math.Min(homePPDA, 20)/20)*0.3 + (homePoss/100)*0.3 + homeAccuracy*0.4
	awayScore := (1-math.Min(awayPPDA, 20)/20)*0.3 + (awayPoss/100)*0.3 + awayAccuracy*0.4

	return map[string]interface{}{
		"homePPDA":       homePPDA,
		"awayPPDA":       awayPPDA,
		"homePossession": homePoss,
		"awayPossession": awayPoss,
		"homeAccuracy":   homeAccuracy,
		"awayAccuracy":   awayAccuracy,
		"score":          0.5 + (homeScore-awayScore)*0.5,
	}
}

// calculateTeamStrength calculates team strength using Elo ratings.
func (e *PredictionEngine) calculateTeamStrength(data *MatchData) map[string]interface{} {
	// Get or initialize Elo ratings
	homeElo := e.config.BaseElo
	if data.HomeElo != nil {
		homeElo = *data.HomeElo
	} else if rating, ok := e.eloRatings[data.HomeTeam]; ok {
		homeElo = rating
	}

	awayElo := e.config.BaseElo
	if data.AwayElo != nil {
		awayElo = *data.AwayElo
	} else if rating, ok := e.eloRatings[data.AwayTeam]; ok {
		awayElo = rating
	}

	// Calculate expected score using Elo formula
	eloDiff := homeElo - awayElo
	expectedHome := 1 / (1 + math.Pow(10, -eloDiff/400))

	return map[string]interface{}{
		"homeElo":         homeElo,
		"awayElo":         awayElo,
		"eloDifferential": eloDiff,
		"expectedHome":    expectedHome,
		"score":           expectedHome,
	}
}

// analyzeTacticalMatchup analyzes tactical matchup between teams.
func (e *PredictionEngine) analyzeTacticalMatchup(data *MatchData) map[string]interface{} {
	// Style matchup matrix
	styleMatchups := map[string]map[string]float64{
		"attacking": {
			"defensive": 0.45,
			"attacking": 0.50,
			"balanced":  0.52,
		},
		"defensive": {
			"attacking": 0.55,
			"defensive": 0.50,
			"balanced":  0.50,
		},
		"balanced": {
			"attacking": 0.48,
			"defensive": 0.50,
			"balanced":  0.50,
		},
	}

	score := 0.52 // Default
	if homeStyleMap, ok := styleMatchups[data.HomeStyle]; ok {
		if matchupScore, ok := homeStyleMap[data.AwayStyle]; ok {
			score = matchupScore
		}
	}

	return map[string]interface{}{
		"homeFormation": data.HomeFormation,
		"awayFormation": data.AwayFormation,
		"homeStyle":     data.HomeStyle,
		"awayStyle":     data.AwayStyle,
		"score":         score,
	}
}

// calculateCurrentForm calculates current form based on recent results.
func (e *PredictionEngine) calculateCurrentForm(data *MatchData) map[string]interface{} {
	homeFormScore := formToScore(data.HomeForm)
	awayFormScore := formToScore(data.AwayForm)

	return map[string]interface{}{
		"homeForm":      data.HomeForm[:min(len(data.HomeForm), 5)],
		"awayForm":      data.AwayForm[:min(len(data.AwayForm), 5)],
		"homeFormScore": homeFormScore,
		"awayFormScore": awayFormScore,
		"score":         0.5 + (homeFormScore-awayFormScore)*0.5,
	}
}

// formToScore converts a form string to a score.
func formToScore(form string) float64 {
	if form == "" {
		return 0.5
	}

	points := map[rune]float64{'W': 1.0, 'D': 0.5, 'L': 0.0}
	weights := []float64{0.3, 0.25, 0.2, 0.15, 0.1}
	score := 0.0

	formRunes := []rune(form)
	for i, result := range formRunes {
		if i >= 5 {
			break
		}
		weight := 0.1
		if i < len(weights) {
			weight = weights[i]
		}
		if val, ok := points[result]; ok {
			score += val * weight
		} else {
			score += 0.5 * weight
		}
	}

	return score
}

// calculatePlayerImpact calculates impact of key players.
func (e *PredictionEngine) calculatePlayerImpact(data *MatchData) map[string]interface{} {
	homeImpact := data.HomeKeyPlayersAvailable * (float64(data.HomeStarRating) / 5)
	awayImpact := data.AwayKeyPlayersAvailable * (float64(data.AwayStarRating) / 5)

	return map[string]interface{}{
		"homeKeyPlayers": data.HomeKeyPlayersAvailable,
		"awayKeyPlayers": data.AwayKeyPlayersAvailable,
		"homeStars":      data.HomeStarRating,
		"awayStars":      data.AwayStarRating,
		"score":          0.5 + (homeImpact-awayImpact)*0.3,
	}
}

// calculateRestFatigue calculates rest and fatigue impact.
func (e *PredictionEngine) calculateRestFatigue(data *MatchData) map[string]interface{} {
	homeScore := restScore(data.HomeRestDays, data.HomeGamesLast7)
	awayScore := restScore(data.AwayRestDays, data.AwayGamesLast7)

	return map[string]interface{}{
		"homeRestDays":    data.HomeRestDays,
		"awayRestDays":    data.AwayRestDays,
		"homeCongestion":  data.HomeGamesLast7,
		"awayCongestion":  data.AwayGamesLast7,
		"score":           0.5 + (homeScore-awayScore)*0.5,
	}
}

// restScore calculates rest score based on rest days and games in last 7 days.
func restScore(days int, games int) float64 {
	// Optimal rest is 5-7 days
	restFactor := 1.0
	if days < 3 {
		restFactor = 0.85
	} else if days < 5 {
		restFactor = 0.95
	} else if days > 10 {
		restFactor = 0.97 // Slight rust
	}

	// Congestion penalty
	congestionFactor := math.Max(0.8, 1-float64(games-1)*0.1)

	return restFactor * congestionFactor
}

// calculateMotivation calculates motivation factors.
func (e *PredictionEngine) calculateMotivation(data *MatchData) map[string]interface{} {
	homeMot := motivationScore(data.HomePosition, true, data.IsDerby, data.Competition)
	awayMot := motivationScore(data.AwayPosition, false, data.IsDerby, data.Competition)

	return map[string]interface{}{
		"homePosition": data.HomePosition,
		"awayPosition": data.AwayPosition,
		"isDerby":      data.IsDerby,
		"isCupFinal":   isCupFinal(data.Competition),
		"score":        0.5 + (homeMot-awayMot)*0.5,
	}
}

// motivationScore calculates motivation score based on league position and context.
func motivationScore(position int, isHome bool, isDerby bool, competition string) float64 {
	score := 0.5

	// Title race boost
	if position <= 4 {
		score += 0.1
	}
	// Relegation fight boost
	if position >= 17 {
		score += 0.08
	}

	// Derby boost
	if isDerby {
		if isHome {
			score += 0.05
		} else {
			score += 0.03
		}
	}

	// Cup final boost
	if isCupFinal(competition) {
		score += 0.05
	}

	return math.Min(1.0, score)
}

// isCupFinal checks if the competition is a cup final.
func isCupFinal(competition string) bool {
	if competition == "" {
		return false
	}
	comp := toLower(competition)
	return contains(comp, "final")
}

// calculateHomeAdvantage calculates home advantage, dampened when away team is significantly stronger.
func (e *PredictionEngine) calculateHomeAdvantage(data *MatchData) map[string]interface{} {
	// Base home advantage
	homeAdv := e.config.HomeAdvantage

	if data.IsNeutralVenue {
		homeAdv = 0.02 // Slight familiarity advantage
	}

	// Dampen home advantage when away team is much stronger
	homePos := data.HomePosition
	awayPos := data.AwayPosition
	qualityGap := homePos - awayPos // Positive = away team is better (lower position)
	dampenFactor := 1.0

	if qualityGap > 8 {
		// Significant quality gap: reduce home advantage by up to 70%
		dampenFactor = math.Max(0.30, 1.0-float64(qualityGap-8)*0.07)
		homeAdv *= dampenFactor
	}

	// Crowd factor
	crowdFactor := 1 + (data.ExpectedAttendancePct-50)/500 // Small adjustment

	finalAdvantage := homeAdv * crowdFactor

	return map[string]interface{}{
		"venue":                  data.Venue,
		"isNeutral":              data.IsNeutralVenue,
		"baseAdvantage":          e.config.HomeAdvantage,
		"dampenedAdvantage":      finalAdvantage,
		"qualityGapDampening":    dampenFactor,
		"crowdFactor":            crowdFactor,
		"score":                  0.5 + finalAdvantage,
	}
}

// calculateExternalFactors calculates external factors (weather, travel, etc.).
func (e *PredictionEngine) calculateExternalFactors(data *MatchData) map[string]interface{} {
	weather := toLower(data.Weather)

	// Weather impact
	weatherImpacts := map[string]float64{
		"clear":        0.0,
		"rain":         -0.02,
		"snow":         -0.05,
		"wind":         -0.03,
		"extreme_heat": -0.04,
	}

	weatherImpact := 0.0
	if impact, ok := weatherImpacts[weather]; ok {
		weatherImpact = impact
	}

	// Travel fatigue (affects away team)
	travelImpact := 0.0
	if data.AwayTravelDistance > 500 {
		travelImpact = 0.02 // Home team benefits
	}
	if data.AwayTravelDistance > 1000 {
		travelImpact = 0.04
	}

	return map[string]interface{}{
		"weather":        data.Weather,
		"travelDistance": data.AwayTravelDistance,
		"weatherImpact":  weatherImpact,
		"travelImpact":   travelImpact,
		"score":          0.5 + travelImpact + weatherImpact,
	}
}

// calculateTeamQualityGap calculates fundamental team quality gap.
func (e *PredictionEngine) calculateTeamQualityGap(data *MatchData) map[string]interface{} {
	// Signal 1: Elo difference
	homeElo := e.config.BaseElo
	if data.HomeElo != nil {
		homeElo = *data.HomeElo
	} else if rating, ok := e.eloRatings[data.HomeTeam]; ok {
		homeElo = rating
	}

	awayElo := e.config.BaseElo
	if data.AwayElo != nil {
		awayElo = *data.AwayElo
	} else if rating, ok := e.eloRatings[data.AwayTeam]; ok {
		awayElo = rating
	}

	eloDiff := homeElo - awayElo
	eloSignal := 0.5 + math.Tanh(eloDiff/300)*0.4

	// Signal 2: League position difference
	homePos := data.HomePosition
	awayPos := data.AwayPosition
	posDiff := awayPos - homePos // Positive = home team better positioned
	positionSignal := 0.5 + math.Tanh(float64(posDiff)/10)*0.35

	// Signal 3: Star rating difference
	homeStars := data.HomeStarRating
	awayStars := data.AwayStarRating
	starSignal := 0.5 + float64(homeStars-awayStars)*0.1
	starSignal = math.Max(0.2, math.Min(0.8, starSignal))

	// Weighted combination
	hasElo := data.HomeElo != nil || (_, ok := e.eloRatings[data.HomeTeam]; ok)
	var qualityScore float64
	if hasElo {
		qualityScore = eloSignal*0.50 + positionSignal*0.35 + starSignal*0.15
	} else {
		qualityScore = positionSignal*0.60 + starSignal*0.40
	}

	gapMagnitude := math.Abs(qualityScore-0.5) * 2

	qualityFavorite := "neutral"
	if qualityScore > 0.55 {
		qualityFavorite = "home"
	} else if qualityScore < 0.45 {
		qualityFavorite = "away"
	}

	return map[string]interface{}{
		"homeElo":          homeElo,
		"awayElo":          awayElo,
		"eloDiff":          eloDiff,
		"positionDiff":     posDiff,
		"gapMagnitude":     gapMagnitude,
		"qualityFavorite":  qualityFavorite,
		"score":            qualityScore,
	}
}

// calculateH2HFactors calculates H2H historical and anomaly factors.
func (e *PredictionEngine) calculateH2HFactors(data *MatchData, ctx *domain.MatchContext) (domain.FactorResult, domain.FactorResult) {
	if ctx.H2HRecord == nil {
		return domain.NewInactiveFactorResult("h2hHistorical", "No H2H data available"),
			domain.NewInactiveFactorResult("h2hAnomaly", "No H2H data for anomaly detection")
	}

	h2h := ctx.H2HRecord

	// Calculate base H2H score
	var h2hScore float64
	var confidence int

	if h2h.TotalMatches() == 0 {
		h2hScore = 0.5
		confidence = 0
	} else {
		homeWinRate := float64(h2h.HomeWins()) / float64(h2h.TotalMatches())
		h2hScore = 0.5 + (homeWinRate-0.33)*0.5
		confidence = min(h2h.TotalMatches()*10, 100)
	}

	// Check anomaly
	weakerTeamIsHome := ctx.HomeLeaguePosition > ctx.AwayLeaguePosition
	anomalyDetected := h2h.AnomalyTriggered && h2h.WeakerTeamUnbeatenStreak >= 3

	if anomalyDetected {
		anomalyBoost := 0.2
		if !weakerTeamIsHome {
			anomalyBoost = -0.1
		}

		return domain.FactorResult{
				Name:        "h2hHistorical",
				Value:       h2hScore,
				Weight:      0.0,
				Triggered:   false,
				Confidence:  confidence,
				Explanation: fmt.Sprintf("Replaced by anomaly (streak: %d)", h2h.WeakerTeamUnbeatenStreak),
				Metadata:    make(map[string]any),
			},
			domain.FactorResult{
				Name:        "h2hAnomaly",
				Value:       0.5 + anomalyBoost,
				Weight:      0.15,
				Triggered:   true,
				Confidence:  90,
				Explanation: fmt.Sprintf("Weaker team unbeaten in %d H2H", h2h.WeakerTeamUnbeatenStreak),
				Metadata: map[string]any{
					"streak":           h2h.WeakerTeamUnbeatenStreak,
					"weaker_team_home": weakerTeamIsHome,
				},
			}
	}

	return domain.FactorResult{
			Name:        "h2hHistorical",
			Value:       h2hScore,
			Weight:      0.05,
			Triggered:   true,
			Confidence:  confidence,
			Explanation: fmt.Sprintf("H2H: %dW-%dD-%dL", h2h.HomeWins(), h2h.Draws(), h2h.AwayWins()),
			Metadata:    make(map[string]any),
		},
		domain.FactorResult{
			Name:        "h2hAnomaly",
			Value:       0.5,
			Weight:      0.0,
			Triggered:   false,
			Confidence:  50,
			Explanation: "No anomaly (streak < 3)",
			Metadata:    make(map[string]any),
		}
}

// calculatePossessionQuality calculates possession quality index.
func (e *PredictionEngine) calculatePossessionQuality(data *MatchData, ctx *domain.MatchContext) domain.FactorResult {
	homeXg := data.HomeXg
	awayXg := data.AwayXg
	homePoss := math.Max(data.HomePossession/100, 0.3)
	awayPoss := math.Max(data.AwayPossession/100, 0.3)

	homePQI := (homeXg / homePoss) * 100
	awayPQI := (awayXg / awayPoss) * 100

	pqiDiff := homePQI - awayPQI
	normalizedScore := 0.5 + math.Tanh(pqiDiff/100)*0.3

	classify := func(pqi float64) string {
		if pqi > 300 {
			return "excellent"
		} else if pqi > 200 {
			return "good"
		}
		return "poor"
	}

	return domain.FactorResult{
		Name:        "possessionQuality",
		Value:       normalizedScore,
		Weight:      0.12,
		Triggered:   true,
		Confidence:  80,
		Explanation: fmt.Sprintf("Home PQI: %.1f (%s), Away: %.1f (%s)", homePQI, classify(homePQI), awayPQI, classify(awayPQI)),
		Metadata: map[string]any{
			"home_pqi": homePQI,
			"away_pqi": awayPQI,
		},
	}
}

// calculateManagerMomentum calculates manager momentum (new manager bounce with decay).
func (e *PredictionEngine) calculateManagerMomentum(data *MatchData, ctx *domain.MatchContext) domain.FactorResult {
	if ctx.HomeManagerInfo == nil || ctx.AwayManagerInfo == nil {
		return domain.NewInactiveFactorResult("managerMomentum", "No manager data")
	}

	calcBounce := func(mgr *domain.ManagerInfo) float64 {
		base := 0.08
		if mgr.IsInterim {
			base = 0.056
		}
		bounce := base * math.Pow(0.85, float64(mgr.GamesManaged))
		if bounce < 0.01 {
			return 0.0
		}
		return bounce
	}

	homeBounce := calcBounce(ctx.HomeManagerInfo)
	awayBounce := calcBounce(ctx.AwayManagerInfo)
	netBounce := homeBounce - awayBounce

	if math.Abs(netBounce) < 0.01 {
		return domain.NewInactiveFactorResult("managerMomentum", "No active bounce")
	}

	value := 0.5 + netBounce*2
	weight := math.Max(homeBounce, awayBounce)

	return domain.FactorResult{
		Name:        "managerMomentum",
		Value:       value,
		Weight:      weight,
		Triggered:   true,
		Confidence:  80,
		Explanation: fmt.Sprintf("Home: %.3f, Away: %.3f", homeBounce, awayBounce),
		Metadata: map[string]any{
			"home_bounce": homeBounce,
			"away_bounce": awayBounce,
		},
	}
}

// calculateRelegationMotivation calculates relegation motivation factor.
func (e *PredictionEngine) calculateRelegationMotivation(data *MatchData, ctx *domain.MatchContext) domain.FactorResult {
	homePos := ctx.HomeLeaguePosition
	recentForm := ctx.HomeRecentForm
	if len(recentForm) > 4 {
		recentForm = recentForm[len(recentForm)-4:]
	}

	recentWins := 0
	for _, r := range recentForm {
		if r == "W" {
			recentWins++
		}
	}
	showingFight := recentWins >= 2

	var drawBoost, homeWinBoost float64
	var tier string

	if homePos >= 18 && showingFight {
		drawBoost = 0.08
		homeWinBoost = 0.03
		tier = "critical"
	} else if homePos >= 17 {
		drawBoost = 0.04
		homeWinBoost = 0.02
		tier = "danger"
	} else {
		return domain.FactorResult{
			Name:        "relegationMotivation",
			Value:       0.5,
			Weight:      0.0,
			Triggered:   false,
			Confidence:  100,
			Explanation: fmt.Sprintf("Not in relegation zone (pos %d)", homePos),
			Metadata:    make(map[string]any),
		}
	}

	return domain.FactorResult{
		Name:        "relegationMotivation",
		Value:       0.5 + drawBoost + homeWinBoost,
		Weight:      0.08,
		Triggered:   true,
		Confidence:  90,
		Explanation: fmt.Sprintf("%s zone (pos %d), %d/4 wins", tier, homePos, recentWins),
		Metadata: map[string]any{
			"draw_boost":     drawBoost,
			"home_win_boost": homeWinBoost,
			"tier":           tier,
		},
	}
}

// calculateCounterAttackEfficiency calculates counter-attack efficiency factor.
func (e *PredictionEngine) calculateCounterAttackEfficiency(data *MatchData, ctx *domain.MatchContext) domain.FactorResult {
	// Use season stats if available, fall back to match-level possession
	var homePoss, awayPoss float64
	confidenceBase := 60

	if ctx.HomeSeasonStats != nil && ctx.AwaySeasonStats != nil {
		homePoss = ctx.HomeSeasonStats["avgPossession"].(float64)
		awayPoss = ctx.AwaySeasonStats["avgPossession"].(float64)
		confidenceBase = 75
	} else {
		homePoss = data.HomePossession
		awayPoss = data.AwayPossession
	}

	scenario := (homePoss < 45 && awayPoss > 58) || (awayPoss < 45 && homePoss > 58)

	if !scenario {
		return domain.FactorResult{
			Name:        "counterAttackEfficiency",
			Value:       0.5,
			Weight:      0.0,
			Triggered:   false,
			Confidence:  confidenceBase,
			Explanation: fmt.Sprintf("No counter setup (H:%.1f%% A:%.1f%%)", homePoss, awayPoss),
			Metadata:    make(map[string]any),
		}
	}

	var value float64
	var underdogTeam string
	var underdogPoss float64

	if homePoss < 45 {
		underdogTeam = "home"
		underdogPoss = homePoss
		value = 0.5 + 0.05
	} else {
		underdogTeam = "away"
		underdogPoss = awayPoss
		value = 0.5 - 0.05
	}

	return domain.FactorResult{
		Name:        "counterAttackEfficiency",
		Value:       value,
		Weight:      0.06,
		Triggered:   true,
		Confidence:  confidenceBase,
		Explanation: fmt.Sprintf("%s counter threat (poss: %.1f%%)", underdogTeam, underdogPoss),
		Metadata: map[string]any{
			"underdog_team":  underdogTeam,
			"draw_boost":     0.06,
			"underdog_boost": 0.04,
		},
	}
}

// calculateAwayDrawFrequency calculates away draw frequency factor.
func (e *PredictionEngine) calculateAwayDrawFrequency(data *MatchData, ctx *domain.MatchContext) domain.FactorResult {
	var awayDrawRate float64
	var totalAwayGames int

	// Use season stats if available
	if ctx.AwaySeasonStats != nil {
		awayDrawRate = ctx.AwaySeasonStats["awayDrawRate"].(float64)
		totalAwayGames = ctx.AwaySeasonStats["totalAwayGames"].(int)
	} else {
		return domain.NewInactiveFactorResult("awayDrawFrequency", "No away stats")
	}

	if totalAwayGames < 5 || awayDrawRate <= 0.35 {
		explanation := "Insufficient games"
		if totalAwayGames >= 5 {
			explanation = fmt.Sprintf("Normal rate: %.1f%%", awayDrawRate*100)
		}

		confidence := 20
		if totalAwayGames >= 5 {
			confidence = 80
		}

		return domain.FactorResult{
			Name:        "awayDrawFrequency",
			Value:       0.5,
			Weight:      0.0,
			Triggered:   false,
			Confidence:  confidence,
			Explanation: explanation,
			Metadata:    make(map[string]any),
		}
	}

	boost := math.Min((awayDrawRate-0.25)*0.5, 0.15)

	return domain.FactorResult{
		Name:        "awayDrawFrequency",
		Value:       0.5 + boost,
		Weight:      0.06,
		Triggered:   true,
		Confidence:  min(totalAwayGames*5, 100),
		Explanation: fmt.Sprintf("Draw-prone: %.1f%% (rate over %d games)", awayDrawRate*100, totalAwayGames),
		Metadata: map[string]any{
			"draw_boost":      boost,
			"away_draw_rate":  awayDrawRate,
		},
	}
}

// Helper functions

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func toLower(s string) string {
	// Simple ASCII lowercase conversion
	result := make([]byte, len(s))
	for i := 0; i < len(s); i++ {
		if s[i] >= 'A' && s[i] <= 'Z' {
			result[i] = s[i] + 32
		} else {
			result[i] = s[i]
		}
	}
	return string(result)
}

func contains(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		match := true
		for j := 0; j < len(substr); j++ {
			if s[i+j] != substr[j] {
				match = false
				break
			}
		}
		if match {
			return true
		}
	}
	return false
}
