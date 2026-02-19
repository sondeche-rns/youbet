package util

import "math"

// KellyStake calculates the Kelly Criterion stake size.
//
// Parameters:
//   - probability: estimated win probability (0-1)
//   - odds: decimal odds
//   - fraction: Kelly fraction (0.25 = quarter Kelly)
//   - maxStake: maximum stake as fraction of bankroll
//
// Returns recommended stake as fraction of bankroll.
func KellyStake(probability, odds, fraction, maxStake float64) float64 {
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

// ImpliedProbability converts decimal odds to implied probability.
func ImpliedProbability(decimalOdds float64) float64 {
	if decimalOdds <= 0 {
		return 0.0
	}
	return 1 / decimalOdds
}

// ExpectedValue calculates the expected value of a bet.
// Returns EV as a decimal (0.05 = 5% edge).
func ExpectedValue(probability, odds float64) float64 {
	return (probability * odds) - 1
}

// ROI calculates return on investment as a percentage.
func ROI(initial, final float64) float64 {
	if initial <= 0 {
		return 0.0
	}
	return ((final - initial) / initial) * 100
}

// SharpeRatio calculates the annualized Sharpe ratio from a slice of returns.
func SharpeRatio(returns []float64, riskFreeRate float64) float64 {
	if len(returns) < 2 {
		return 0.0
	}

	// Calculate excess returns
	n := float64(len(returns))
	var sum float64
	for _, r := range returns {
		sum += r - riskFreeRate
	}
	meanExcess := sum / n

	// Standard deviation of excess returns
	var sumSq float64
	for _, r := range returns {
		diff := (r - riskFreeRate) - meanExcess
		sumSq += diff * diff
	}
	stdDev := math.Sqrt(sumSq / n)

	if stdDev == 0 {
		return 0.0
	}

	// Annualize (assuming daily returns, 252 trading days)
	return (meanExcess / stdDev) * math.Sqrt(252)
}

// ValidateOdds checks if odds are within a valid range.
func ValidateOdds(odds float64) bool {
	return odds >= 1.01 && odds <= 1000
}

// ValidateProbability checks if a probability value is valid.
func ValidateProbability(prob float64) bool {
	return prob > 0.0 && prob < 1.0
}

// ValidateStake checks if a stake is within bankroll limits.
func ValidateStake(stake, bankroll, maxPct float64) bool {
	return stake > 0 && stake <= bankroll*maxPct
}

// DecimalToAmerican converts decimal odds to American odds.
func DecimalToAmerican(decimalOdds float64) int {
	if decimalOdds >= 2.0 {
		return int((decimalOdds - 1) * 100)
	}
	return int(-100 / (decimalOdds - 1))
}

// AmericanToDecimal converts American odds to decimal odds.
func AmericanToDecimal(americanOdds int) float64 {
	if americanOdds > 0 {
		return (float64(americanOdds) / 100) + 1
	}
	return (100 / math.Abs(float64(americanOdds))) + 1
}

// NormalizeOddsFormat converts odds from the specified format to decimal.
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
