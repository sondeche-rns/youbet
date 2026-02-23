package util

import (
	"math"
	"testing"
)

const epsilon = 1e-6

func almostEqual(a, b float64) bool {
	return math.Abs(a-b) < epsilon
}

func TestCalculateKellyStake(t *testing.T) {
	tests := []struct {
		name     string
		prob     float64
		odds     float64
		fraction float64
		maxStake float64
		want     float64
	}{
		{
			name: "positive edge",
			prob: 0.6, odds: 2.0, fraction: 0.25, maxStake: 0.05,
			want: 0.05, // kelly = (1*0.6 - 0.4)/1 = 0.2, fractional = 0.05, capped at 0.05
		},
		{
			name: "no edge",
			prob: 0.5, odds: 2.0, fraction: 0.25, maxStake: 0.05,
			want: 0.0, // kelly = 0, so 0
		},
		{
			name: "negative edge",
			prob: 0.3, odds: 2.0, fraction: 0.25, maxStake: 0.05,
			want: 0.0,
		},
		{
			name: "zero probability",
			prob: 0, odds: 2.0, fraction: 0.25, maxStake: 0.05,
			want: 0.0,
		},
		{
			name: "odds equal 1",
			prob: 0.6, odds: 1.0, fraction: 0.25, maxStake: 0.05,
			want: 0.0,
		},
		{
			name: "small positive edge uncapped",
			prob: 0.55, odds: 2.0, fraction: 0.25, maxStake: 0.10,
			want: 0.025, // kelly = 0.1, fractional = 0.025
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := CalculateKellyStake(tt.prob, tt.odds, tt.fraction, tt.maxStake)
			if !almostEqual(got, tt.want) {
				t.Errorf("CalculateKellyStake(%f, %f, %f, %f) = %f, want %f",
					tt.prob, tt.odds, tt.fraction, tt.maxStake, got, tt.want)
			}
		})
	}
}

func TestCalculateImpliedProbability(t *testing.T) {
	if !almostEqual(CalculateImpliedProbability(2.0), 0.5) {
		t.Error("2.0 odds should give 0.5 implied prob")
	}
	if !almostEqual(CalculateImpliedProbability(4.0), 0.25) {
		t.Error("4.0 odds should give 0.25 implied prob")
	}
	if CalculateImpliedProbability(0) != 0.0 {
		t.Error("0 odds should give 0.0")
	}
	if CalculateImpliedProbability(-1) != 0.0 {
		t.Error("negative odds should give 0.0")
	}
}

func TestCalculateExpectedValue(t *testing.T) {
	// 60% chance at 2.0 odds: EV = 0.6 * 2.0 - 1 = 0.2
	ev := CalculateExpectedValue(0.6, 2.0)
	if !almostEqual(ev, 0.2) {
		t.Errorf("expected EV 0.2, got %f", ev)
	}

	// Fair odds: EV = 0
	ev = CalculateExpectedValue(0.5, 2.0)
	if !almostEqual(ev, 0.0) {
		t.Errorf("expected EV 0.0, got %f", ev)
	}
}

func TestCalculateROI(t *testing.T) {
	if !almostEqual(CalculateROI(1000, 1100), 10.0) {
		t.Error("1000 -> 1100 should be 10% ROI")
	}
	if !almostEqual(CalculateROI(1000, 900), -10.0) {
		t.Error("1000 -> 900 should be -10% ROI")
	}
	if CalculateROI(0, 100) != 0.0 {
		t.Error("zero initial should give 0.0 ROI")
	}
}

func TestCalculateSharpeRatio(t *testing.T) {
	// Sharpe of empty/single returns should be 0
	if CalculateSharpeRatio(nil, 0) != 0.0 {
		t.Error("nil returns should give 0.0 Sharpe")
	}
	if CalculateSharpeRatio([]float64{0.05}, 0) != 0.0 {
		t.Error("single return should give 0.0 Sharpe")
	}

	// Constant returns => std=0 => Sharpe=0
	if CalculateSharpeRatio([]float64{0.01, 0.01, 0.01}, 0) != 0.0 {
		t.Error("constant returns should give 0.0 Sharpe")
	}

	// Positive varying returns should give positive Sharpe
	sharpe := CalculateSharpeRatio([]float64{0.01, 0.02, 0.03, 0.01, 0.02}, 0)
	if sharpe <= 0 {
		t.Errorf("expected positive Sharpe for positive returns, got %f", sharpe)
	}
}

func TestNormalizeOddsFormat(t *testing.T) {
	if !almostEqual(NormalizeOddsFormat(2.5, "decimal"), 2.5) {
		t.Error("decimal should pass through")
	}
	if !almostEqual(NormalizeOddsFormat(150, "american"), 2.5) {
		t.Error("+150 American should be 2.5 decimal")
	}
	if !almostEqual(NormalizeOddsFormat(-200, "american"), 1.5) {
		t.Error("-200 American should be 1.5 decimal")
	}
}

func TestDecimalToAmerican(t *testing.T) {
	if DecimalToAmerican(2.5) != 150 {
		t.Errorf("2.5 decimal should be +150, got %d", DecimalToAmerican(2.5))
	}
	if DecimalToAmerican(1.5) != -200 {
		t.Errorf("1.5 decimal should be -200, got %d", DecimalToAmerican(1.5))
	}
}

func TestValidateOdds(t *testing.T) {
	if !ValidateOdds(2.0) {
		t.Error("2.0 should be valid odds")
	}
	if ValidateOdds(1.0) {
		t.Error("1.0 should be invalid odds")
	}
	if ValidateOdds(1001) {
		t.Error("1001 should be invalid odds")
	}
}
