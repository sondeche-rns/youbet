package algorithm

import (
	"math"

	"bet4me/internal/domain"
)

// calculateWeightedProbabilities calculates probabilities from weighted factors with dynamic weight normalization.
func (e *PredictionEngine) calculateWeightedProbabilities(factors map[string]interface{}) Probabilities {
	// Separate FactorResult objects from legacy dict factors
	activeFactors := make(map[string]factorData)
	drawBoostTotal := 0.0
	homeBoostTotal := 0.0
	awayBoostTotal := 0.0

	for factorName, factorDataRaw := range factors {
		// Handle FactorResult objects (new contextual factors)
		if fr, ok := factorDataRaw.(domain.FactorResult); ok {
			if fr.Triggered && fr.Weight > 0 {
				activeFactors[factorName] = factorData{
					score:    fr.Value,
					weight:   fr.Weight,
					metadata: fr.Metadata,
				}

				// Extract draw/home/away boosts from metadata
				if val, ok := fr.Metadata["draw_boost"].(float64); ok {
					drawBoostTotal += val
				}
				if val, ok := fr.Metadata["home_win_boost"].(float64); ok {
					homeBoostTotal += val
				}
			}
		} else if dictData, ok := factorDataRaw.(map[string]interface{}); ok {
			// Handle legacy dict factors (original 10 factors)
			if score, ok := dictData["score"].(float64); ok {
				configWeight := e.config.Weights[factorName]
				if configWeight > 0 {
					activeFactors[factorName] = factorData{
						score:    score,
						weight:   configWeight,
						metadata: make(map[string]any),
					}
				}
			}
		}
	}

	// Calculate dynamic normalized weights
	totalWeight := 0.0
	for _, fd := range activeFactors {
		totalWeight += fd.weight
	}

	if totalWeight == 0 {
		// Fallback to neutral probabilities
		return Probabilities{Home: 0.33, Draw: 0.34, Away: 0.33}
	}

	// Calculate weighted score with normalized weights
	weightedScore := 0.0
	for _, fd := range activeFactors {
		normalizedWeight := fd.weight / totalWeight
		weightedScore += fd.score * normalizedWeight
	}

	// Convert to base probabilities using enhanced draw model
	drawProb := calculateDrawProbability(weightedScore, factors, drawBoostTotal)
	homeProb := weightedScore*(1-drawProb) + homeBoostTotal
	awayProb := (1-weightedScore)*(1-drawProb) - homeBoostTotal

	// Ensure probabilities stay within valid range
	homeProb = math.Max(0.05, math.Min(0.90, homeProb))
	drawProb = math.Max(0.05, math.Min(0.90, drawProb))
	awayProb = math.Max(0.05, math.Min(0.90, awayProb))

	// Final normalization to sum = 1.0
	total := homeProb + drawProb + awayProb

	return Probabilities{
		Home: homeProb / total,
		Draw: drawProb / total,
		Away: awayProb / total,
	}
}

// factorData holds normalized factor data for probability calculation.
type factorData struct {
	score    float64
	weight   float64
	metadata map[string]any
}

// assessDataQuality assesses how much real data we have vs defaults.
//
// Returns 0.0 (no real data, only defaults) to 1.0 (rich data available).
func (e *PredictionEngine) assessDataQuality(data *MatchData) float64 {
	fieldsPresent := 0
	totalFields := 10

	// Check key data fields
	if data.HomeXg != 1.3 {
		fieldsPresent++
	}
	if data.HomeElo != nil || data.AwayElo != nil {
		fieldsPresent++
	}
	if data.HomePosition != 10 {
		fieldsPresent++
	}
	if data.HomeForm != "WDWLD" {
		fieldsPresent++
	}
	if data.HomePossession != 50 {
		fieldsPresent++
	}
	if data.HomeStarRating != 3 {
		fieldsPresent++
	}
	if data.HomeStyle != "balanced" {
		fieldsPresent++
	}
	if data.HomeRestDays != 7 {
		fieldsPresent++
	}
	if data.AwayTravelDistance > 0 {
		fieldsPresent++
	}
	if data.Weather != "clear" {
		fieldsPresent++
	}

	return math.Min(1.0, float64(fieldsPresent)/float64(totalFields))
}

// calibrateProbabilities applies Platt scaling calibration.
func (e *PredictionEngine) calibrateProbabilities(probs Probabilities) Probabilities {
	a := e.calibrationParams.A
	b := e.calibrationParams.B

	calibrate := func(p float64) float64 {
		// Simple linear calibration
		val := p*a + b*(p-0.5)
		return math.Max(0.01, math.Min(0.99, val))
	}

	calibrated := Probabilities{
		Home: calibrate(probs.Home),
		Draw: calibrate(probs.Draw),
		Away: calibrate(probs.Away),
	}

	// Renormalize
	total := calibrated.Home + calibrated.Draw + calibrated.Away
	return Probabilities{
		Home: calibrated.Home / total,
		Draw: calibrated.Draw / total,
		Away: calibrated.Away / total,
	}
}

// calculateConfidence calculates prediction confidence.
func (e *PredictionEngine) calculateConfidence(factors map[string]interface{}, probs Probabilities) float64 {
	// Base confidence from probability spread
	maxProb := math.Max(probs.Home, math.Max(probs.Draw, probs.Away))
	minProb := math.Min(probs.Home, math.Min(probs.Draw, probs.Away))
	spreadConfidence := (maxProb - minProb) * 0.5

	// Factor consistency (how aligned are the factors)
	factorScores := []float64{}
	for _, factorData := range factors {
		if dictData, ok := factorData.(map[string]interface{}); ok {
			if score, ok := dictData["score"].(float64); ok {
				factorScores = append(factorScores, score)
			}
		}
	}

	consistencyBonus := 0.0
	if len(factorScores) > 0 {
		factorStd := stdDev(factorScores)
		consistencyBonus = math.Max(0, 0.2-factorStd)
	}

	// Data quality
	dataQuality := 0.8 // Assume decent data

	confidence := (spreadConfidence + consistencyBonus) * dataQuality
	return math.Min(0.95, math.Max(0.40, 0.5+confidence))
}

// stdDev calculates standard deviation of a slice of float64.
func stdDev(values []float64) float64 {
	if len(values) == 0 {
		return 0
	}

	// Calculate mean
	sum := 0.0
	for _, v := range values {
		sum += v
	}
	mean := sum / float64(len(values))

	// Calculate variance
	variance := 0.0
	for _, v := range values {
		diff := v - mean
		variance += diff * diff
	}
	variance /= float64(len(values))

	return math.Sqrt(variance)
}

// generateRecommendation generates betting recommendation.
func (e *PredictionEngine) generateRecommendation(
	probs Probabilities,
	confidence float64,
	homeOdds, drawOdds, awayOdds *float64,
) *Recommendation {
	// Determine predicted outcome
	predictedOutcome := "Home Win"
	predictedProb := probs.Home

	if probs.Draw > predictedProb {
		predictedOutcome = "Draw"
		predictedProb = probs.Draw
	}
	if probs.Away > predictedProb {
		predictedOutcome = "Away Win"
		predictedProb = probs.Away
	}

	// Calculate expected values if odds available
	evByOutcome := make(map[string]float64)
	var bestEV float64
	var bestBet *struct {
		outcome string
		prob    float64
		odds    float64
	}

	if homeOdds != nil {
		ev := (probs.Home * *homeOdds) - 1
		evByOutcome["home"] = round(ev*100, 2)
		if ev > bestEV {
			bestEV = ev
			bestBet = &struct {
				outcome string
				prob    float64
				odds    float64
			}{"Home Win", probs.Home, *homeOdds}
		}
	}

	if drawOdds != nil {
		ev := (probs.Draw * *drawOdds) - 1
		evByOutcome["draw"] = round(ev*100, 2)
		if ev > bestEV {
			bestEV = ev
			bestBet = &struct {
				outcome string
				prob    float64
				odds    float64
			}{"Draw", probs.Draw, *drawOdds}
		}
	}

	if awayOdds != nil {
		ev := (probs.Away * *awayOdds) - 1
		evByOutcome["away"] = round(ev*100, 2)
		if ev > bestEV {
			bestEV = ev
			bestBet = &struct {
				outcome string
				prob    float64
				odds    float64
			}{"Away Win", probs.Away, *awayOdds}
		}
	}

	// Calculate stake using Kelly Criterion
	stakePct := 0.0
	recommendationType := "No Bet"

	// Default values from config (will be overridden if available)
	kellyFraction := 0.25
	maxBetPct := 0.05

	if bestBet != nil && bestEV > 0 {
		// Kelly: f = (bp - q) / b where b = odds - 1, p = probability, q = 1 - p
		b := bestBet.odds - 1
		kelly := (b*bestBet.prob - (1 - bestBet.prob)) / b

		// Apply fractional Kelly and cap
		stakePct = math.Min(maxBetPct, math.Max(0, kelly*kellyFraction))

		if bestEV > 0.10 && confidence > 0.70 {
			recommendationType = "Strong Bet"
		} else if bestEV > 0.05 && confidence > 0.60 {
			recommendationType = "Value Bet"
		} else if bestEV > 0 {
			recommendationType = "Small Edge"
		}
	} else if predictedProb > 0.60 && confidence > 0.65 {
		recommendationType = "Lean"
	}

	return &Recommendation{
		Outcome:         predictedOutcome,
		Probability:     round(predictedProb*100, 1),
		Recommendation:  recommendationType,
		StakePercentage: round(stakePct*100, 2),
		ExpectedValue:   round(bestEV*100, 2),
		KellyStake:      round(stakePct, 4),
		Confidence:      round(confidence*100, 1),
		EVByOutcome:     evByOutcome,
	}
}

// UpdateElo updates Elo ratings after a match.
func (e *PredictionEngine) UpdateElo(homeTeam, awayTeam string, homeGoals, awayGoals int) {
	homeElo := e.eloRatings[homeTeam]
	if homeElo == 0 {
		homeElo = e.config.BaseElo
	}

	awayElo := e.eloRatings[awayTeam]
	if awayElo == 0 {
		awayElo = e.config.BaseElo
	}

	// Expected scores
	expectedHome := 1 / (1 + math.Pow(10, (awayElo-homeElo)/400))
	expectedAway := 1 - expectedHome

	// Actual scores
	var actualHome, actualAway float64
	if homeGoals > awayGoals {
		actualHome, actualAway = 1, 0
	} else if homeGoals < awayGoals {
		actualHome, actualAway = 0, 1
	} else {
		actualHome, actualAway = 0.5, 0.5
	}

	// Update ratings
	k := e.config.KFactor
	e.eloRatings[homeTeam] = homeElo + k*(actualHome-expectedHome)
	e.eloRatings[awayTeam] = awayElo + k*(actualAway-expectedAway)
}

// SetCalibration sets Platt scaling calibration parameters.
func (e *PredictionEngine) SetCalibration(a, b float64) {
	e.calibrationParams = CalibrationParams{A: a, B: b}
}

// GetConfig returns current algorithm configuration.
func (e *PredictionEngine) GetConfig() *SportConfig {
	return e.config
}
