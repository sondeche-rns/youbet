package util

import (
	"math"
	"testing"
)

func almostEqual(a, b, tolerance float64) bool {
	return math.Abs(a-b) < tolerance
}

func TestKellyStake(t *testing.T) {
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
			want: 0.05, // kelly = (1*0.6 - 0.4)/1 = 0.2, * 0.25 = 0.05
		},
		{
			name: "small edge",
			prob: 0.55, odds: 2.0, fraction: 0.25, maxStake: 0.05,
			want: 0.025, // kelly = (1*0.55 - 0.45)/1 = 0.1, * 0.25 = 0.025
		},
		{
			name: "no edge",
			prob: 0.5, odds: 2.0, fraction: 0.25, maxStake: 0.05,
			want: 0.0, // kelly = (1*0.5 - 0.5)/1 = 0.0
		},
		{
			name: "negative edge returns zero",
			prob: 0.3, odds: 2.0, fraction: 0.25, maxStake: 0.05,
			want: 0.0,
		},
		{
			name: "probability zero",
			prob: 0.0, odds: 2.0, fraction: 0.25, maxStake: 0.05,
			want: 0.0,
		},
		{
			name: "probability one",
			prob: 1.0, odds: 2.0, fraction: 0.25, maxStake: 0.05,
			want: 0.0,
		},
		{
			name: "odds at one",
			prob: 0.6, odds: 1.0, fraction: 0.25, maxStake: 0.05,
			want: 0.0,
		},
		{
			name: "capped at max stake",
			prob: 0.9, odds: 3.0, fraction: 1.0, maxStake: 0.05,
			// kelly = (2*0.9 - 0.1)/2 = 0.85, * 1.0 = 0.85, capped at 0.05
			want: 0.05,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := KellyStake(tt.prob, tt.odds, tt.fraction, tt.maxStake)
			if !almostEqual(got, tt.want, 0.001) {
				t.Errorf("KellyStake(%f, %f, %f, %f) = %f, want %f",
					tt.prob, tt.odds, tt.fraction, tt.maxStake, got, tt.want)
			}
		})
	}
}

func TestImpliedProbability(t *testing.T) {
	tests := []struct {
		odds float64
		want float64
	}{
		{2.0, 0.5},
		{3.0, 1.0 / 3.0},
		{1.5, 1.0 / 1.5},
		{0.0, 0.0},
		{-1.0, 0.0},
	}

	for _, tt := range tests {
		got := ImpliedProbability(tt.odds)
		if !almostEqual(got, tt.want, 0.0001) {
			t.Errorf("ImpliedProbability(%f) = %f, want %f", tt.odds, got, tt.want)
		}
	}
}

func TestExpectedValue(t *testing.T) {
	// prob=0.5, odds=2.0 → EV = (0.5 * 2.0) - 1 = 0.0 (fair bet)
	if got := ExpectedValue(0.5, 2.0); !almostEqual(got, 0.0, 0.001) {
		t.Errorf("ExpectedValue(0.5, 2.0) = %f, want 0.0", got)
	}
	// prob=0.6, odds=2.0 → EV = 0.2 (20% edge)
	if got := ExpectedValue(0.6, 2.0); !almostEqual(got, 0.2, 0.001) {
		t.Errorf("ExpectedValue(0.6, 2.0) = %f, want 0.2", got)
	}
}

func TestROI(t *testing.T) {
	if got := ROI(1000, 1200); !almostEqual(got, 20.0, 0.01) {
		t.Errorf("ROI(1000, 1200) = %f, want 20.0", got)
	}
	if got := ROI(1000, 800); !almostEqual(got, -20.0, 0.01) {
		t.Errorf("ROI(1000, 800) = %f, want -20.0", got)
	}
	if got := ROI(0, 100); got != 0.0 {
		t.Errorf("ROI(0, 100) = %f, want 0.0", got)
	}
}

func TestSharpeRatio(t *testing.T) {
	// Empty returns
	if got := SharpeRatio(nil, 0); got != 0.0 {
		t.Errorf("SharpeRatio(nil) = %f, want 0.0", got)
	}
	// Single return
	if got := SharpeRatio([]float64{0.05}, 0); got != 0.0 {
		t.Errorf("SharpeRatio([0.05]) = %f, want 0.0", got)
	}
	// All same returns (zero std dev)
	if got := SharpeRatio([]float64{0.01, 0.01, 0.01}, 0); got != 0.0 {
		t.Errorf("SharpeRatio([0.01, 0.01, 0.01]) = %f, want 0.0", got)
	}
	// Positive returns should give positive Sharpe
	returns := []float64{0.02, 0.01, 0.03, 0.02, 0.01}
	sharpe := SharpeRatio(returns, 0)
	if sharpe <= 0 {
		t.Errorf("SharpeRatio(positive returns) = %f, want > 0", sharpe)
	}
}

func TestValidateOdds(t *testing.T) {
	if !ValidateOdds(1.5) {
		t.Error("1.5 should be valid odds")
	}
	if !ValidateOdds(1.01) {
		t.Error("1.01 should be valid odds")
	}
	if ValidateOdds(1.0) {
		t.Error("1.0 should be invalid odds")
	}
	if ValidateOdds(0) {
		t.Error("0 should be invalid odds")
	}
	if ValidateOdds(1001) {
		t.Error("1001 should be invalid odds")
	}
}

func TestDecimalToAmerican(t *testing.T) {
	// 2.5 decimal = +150 american
	if got := DecimalToAmerican(2.5); got != 150 {
		t.Errorf("DecimalToAmerican(2.5) = %d, want 150", got)
	}
	// 1.5 decimal = -200 american
	if got := DecimalToAmerican(1.5); got != -200 {
		t.Errorf("DecimalToAmerican(1.5) = %d, want -200", got)
	}
}

func TestAmericanToDecimal(t *testing.T) {
	if got := AmericanToDecimal(150); !almostEqual(got, 2.5, 0.001) {
		t.Errorf("AmericanToDecimal(150) = %f, want 2.5", got)
	}
	if got := AmericanToDecimal(-200); !almostEqual(got, 1.5, 0.001) {
		t.Errorf("AmericanToDecimal(-200) = %f, want 1.5", got)
	}
}

func TestNormalizeOddsFormat(t *testing.T) {
	if got := NormalizeOddsFormat(2.5, "decimal"); got != 2.5 {
		t.Errorf("decimal: got %f, want 2.5", got)
	}
	if got := NormalizeOddsFormat(150, "american"); !almostEqual(got, 2.5, 0.001) {
		t.Errorf("american +150: got %f, want 2.5", got)
	}
	if got := NormalizeOddsFormat(-200, "american"); !almostEqual(got, 1.5, 0.001) {
		t.Errorf("american -200: got %f, want 1.5", got)
	}
}
