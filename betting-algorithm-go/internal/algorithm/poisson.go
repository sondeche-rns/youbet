package algorithm

import (
	"math"

	"gonum.org/v1/gonum/stat/distuv"
)

// calculatePoissonProbabilities calculates match outcome probabilities using Poisson distribution.
//
// This models goal scoring as independent Poisson processes for home and away teams,
// then aggregates scoreline probabilities to determine win/draw/loss outcomes.
func (e *PredictionEngine) calculatePoissonProbabilities(data *MatchData, factors map[string]interface{}) Probabilities {
	// Get expected goals from factors
	homeXg := 1.3
	awayXg := 1.3

	if xgData, ok := factors["expectedGoals"].(map[string]interface{}); ok {
		if val, ok := xgData["homeXg"].(float64); ok {
			homeXg = val
		}
		if val, ok := xgData["awayXg"].(float64); ok {
			awayXg = val
		}
	}

	// Adjust based on team strength
	strengthFactor := 0.5
	if strengthData, ok := factors["teamStrength"].(map[string]interface{}); ok {
		if val, ok := strengthData["score"].(float64); ok {
			strengthFactor = val
		}
	}

	homeXg *= (0.8 + strengthFactor*0.4)
	awayXg *= (1.2 - strengthFactor*0.4)

	// Cap xG to reasonable values
	maxGoalsLambda := e.config.MaxGoalsLambda
	if maxGoalsLambda == 0 {
		maxGoalsLambda = 4.0
	}
	homeXg = math.Min(homeXg, maxGoalsLambda)
	awayXg = math.Min(awayXg, maxGoalsLambda)

	// Calculate probabilities for each scoreline (0-0 to 5-5)
	homeWinProb := 0.0
	drawProb := 0.0
	awayWinProb := 0.0

	// Create Poisson distributions
	homePoisson := distuv.Poisson{Lambda: homeXg}
	awayPoisson := distuv.Poisson{Lambda: awayXg}

	// Iterate through all possible scorelines up to 5-5
	for homeGoals := 0; homeGoals <= 5; homeGoals++ {
		for awayGoals := 0; awayGoals <= 5; awayGoals++ {
			// Calculate probability of this exact scoreline
			prob := homePoisson.Prob(float64(homeGoals)) * awayPoisson.Prob(float64(awayGoals))

			// Accumulate into outcome categories
			if homeGoals > awayGoals {
				homeWinProb += prob
			} else if homeGoals == awayGoals {
				drawProb += prob
			} else {
				awayWinProb += prob
			}
		}
	}

	// Normalize to ensure probabilities sum to 1.0
	total := homeWinProb + drawProb + awayWinProb

	return Probabilities{
		Home: homeWinProb / total,
		Draw: drawProb / total,
		Away: awayWinProb / total,
	}
}

// calculateDrawProbability calculates draw probability using multi-signal model.
//
// Replaces the old formula: 0.25 * (1 - |ws - 0.5| * 2) which capped at 25%.
// EPL average draw rate is ~26%, and evenly-matched defensive games can reach 35%.
//
// Returns draw probability in range [0.08, 0.40].
func calculateDrawProbability(weightedScore float64, factors map[string]interface{}, drawBoostTotal float64) float64 {
	// Signal 1: Base league draw rate
	baseDraw := 0.26

	// Signal 2: Quality gap (teams close in quality = higher draw probability)
	qualityGap := math.Abs(weightedScore - 0.5) // 0 = perfectly even, 0.5 = total mismatch
	// gap=0 → +0.06, gap=0.15 → +0.01, gap=0.3 → -0.04, gap=0.5 → -0.10
	qualityGapAdjustment := 0.06 - qualityGap*0.32

	// Signal 3: Defensive profile from xG
	hXg := 1.3
	aXg := 1.3

	if homeXgData, ok := factors["expectedGoals"].(map[string]interface{}); ok {
		if val, ok := homeXgData["homeXg"].(float64); ok {
			hXg = val
		}
		if val, ok := homeXgData["awayXg"].(float64); ok {
			aXg = val
		}
	}

	totalXg := hXg + aXg
	var defensiveBoost float64
	if totalXg < 2.0 {
		defensiveBoost = 0.05
	} else if totalXg < 2.5 {
		defensiveBoost = 0.02
	} else {
		defensiveBoost = 0.0
	}

	// Signal 4: xG closeness (similar xG = higher draw chance)
	xgDiff := math.Abs(hXg - aXg)
	xgClosenessAdj := math.Max(-0.04, 0.04-xgDiff*0.04)

	// Signal 5: Contextual factor draw boosts (already accumulated)
	contextualBoost := drawBoostTotal

	// Combine signals
	drawProb := baseDraw + qualityGapAdjustment + defensiveBoost + xgClosenessAdj + contextualBoost

	// Clamp to realistic range
	return math.Max(0.08, math.Min(0.40, drawProb))
}

// blendProbabilities blends two probability distributions.
//
// Args:
//   probs1: First probability distribution
//   probs2: Second probability distribution
//   weight2: Weight for second distribution (0-1)
//
// Returns blended probabilities.
func blendProbabilities(probs1, probs2 Probabilities, weight2 float64) Probabilities {
	weight1 := 1 - weight2
	return Probabilities{
		Home: probs1.Home*weight1 + probs2.Home*weight2,
		Draw: probs1.Draw*weight1 + probs2.Draw*weight2,
		Away: probs1.Away*weight1 + probs2.Away*weight2,
	}
}

// oddsToProbs converts decimal odds to implied probabilities.
//
// Removes bookmaker margin to get fair probabilities.
func oddsToProbs(homeOdds, drawOdds, awayOdds float64) Probabilities {
	// Convert odds to implied probabilities
	homeImplied := 1 / homeOdds
	if homeOdds <= 0 {
		homeImplied = 0.33
	}

	drawImplied := 1 / drawOdds
	if drawOdds <= 0 {
		drawImplied = 0.33
	}

	awayImplied := 1 / awayOdds
	if awayOdds <= 0 {
		awayImplied = 0.33
	}

	// Normalize to remove margin
	total := homeImplied + drawImplied + awayImplied

	return Probabilities{
		Home: homeImplied / total,
		Draw: drawImplied / total,
		Away: awayImplied / total,
	}
}
