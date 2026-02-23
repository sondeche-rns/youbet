package util

import "math"

// CalculateKellyStake computes the Kelly Criterion stake size.
//
// Parameters:
//   - probability: estimated probability of winning (0-1)
//   - odds: decimal odds
//   - fraction: Kelly fraction to use (0.25 = quarter Kelly)
//   - maxStake: maximum stake as fraction of bankroll
//
// Returns recommended stake as fraction of bankroll.
func CalculateKellyStake(probability, odds, fraction, maxStake float64) float64 {
	if probability <= 0 || probability >= 1 || odds <= 1 {
		return 0.0
	}

	b := odds - 1 // net odds (profit per unit stake)
	p := probability
	q := 1 - p

	// Kelly formula: f = (bp - q) / b
	kelly := (b*p - q) / b

	// Apply fractional Kelly and cap
	stake := math.Max(0, kelly*fraction)
	return math.Min(stake, maxStake)
}

// CalculateImpliedProbability converts decimal odds to implied probability.
func CalculateImpliedProbability(decimalOdds float64) float64 {
	if decimalOdds <= 0 {
		return 0.0
	}
	return 1.0 / decimalOdds
}

// CalculateExpectedValue computes the expected value of a bet.
// Returns EV as a decimal (0.05 = 5% edge).
func CalculateExpectedValue(probability, odds float64) float64 {
	return (probability * odds) - 1
}

// CalculateROI computes ROI percentage from initial and final values.
func CalculateROI(initial, final float64) float64 {
	if initial <= 0 {
		return 0.0
	}
	return ((final - initial) / initial) * 100
}

// CalculateSharpeRatio computes the annualized Sharpe ratio from a slice of returns.
// Assumes daily returns with 252 trading days per year.
func CalculateSharpeRatio(returns []float64, riskFreeRate float64) float64 {
	if len(returns) < 2 {
		return 0.0
	}

	// Calculate excess returns
	n := float64(len(returns))
	var sum float64
	for _, r := range returns {
		sum += r - riskFreeRate
	}
	meanReturn := sum / n

	// Standard deviation
	var sumSq float64
	for _, r := range returns {
		diff := (r - riskFreeRate) - meanReturn
		sumSq += diff * diff
	}
	stdReturn := math.Sqrt(sumSq / n)

	if stdReturn == 0 {
		return 0.0
	}

	// Annualize (252 trading days)
	return (meanReturn / stdReturn) * math.Sqrt(252)
}

// NormalizeOddsFormat converts odds from various formats to decimal.
func NormalizeOddsFormat(odds float64, formatType string) float64 {
	switch formatType {
	case "decimal":
		return odds
	case "american":
		if odds > 0 {
			return (odds / 100) + 1
		}
		return (100 / math.Abs(odds)) + 1
	case "fractional":
		return odds + 1
	default:
		return odds
	}
}

// DecimalToAmerican converts decimal odds to American format.
func DecimalToAmerican(decimalOdds float64) int {
	if decimalOdds >= 2.0 {
		return int((decimalOdds - 1) * 100)
	}
	return int(-100 / (decimalOdds - 1))
}

// AmericanToDecimal converts American odds to decimal format.
func AmericanToDecimal(americanOdds int) float64 {
	if americanOdds > 0 {
		return (float64(americanOdds) / 100) + 1
	}
	return (100 / math.Abs(float64(americanOdds))) + 1
}

// ValidateOdds checks if decimal odds are within valid range.
func ValidateOdds(odds float64) bool {
	return odds >= 1.01 && odds <= 1000
}

// ValidateProbability checks if a probability is valid (exclusive of 0 and 1).
func ValidateProbability(prob float64) bool {
	return prob > 0.0 && prob < 1.0
}

// ValidateStake checks if a stake is within limits.
func ValidateStake(stake, bankroll, maxPct float64) bool {
	return stake > 0 && stake <= bankroll*maxPct
}
