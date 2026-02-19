package util

import (
	"math"
	"testing"
	"time"
)

func TestPerformanceTracker_Empty(t *testing.T) {
	pt := NewPerformanceTracker(1000)
	s := pt.Summary()
	if s.TotalBets != 0 {
		t.Errorf("TotalBets = %d, want 0", s.TotalBets)
	}
	if s.WinRate != 0 {
		t.Errorf("WinRate = %f, want 0", s.WinRate)
	}
}

func TestPerformanceTracker_WinningBet(t *testing.T) {
	pt := NewPerformanceTracker(1000)
	pt.AddBet(50, 2.0, true, 0, time.Now())

	s := pt.Summary()
	if s.TotalBets != 1 {
		t.Errorf("TotalBets = %d, want 1", s.TotalBets)
	}
	if s.Wins != 1 {
		t.Errorf("Wins = %d, want 1", s.Wins)
	}
	if s.WinRate != 100.0 {
		t.Errorf("WinRate = %f, want 100.0", s.WinRate)
	}
	if !almostEqual(s.CurrentBankroll, 1050, 0.01) {
		t.Errorf("CurrentBankroll = %f, want 1050", s.CurrentBankroll)
	}
	if !almostEqual(s.TotalPnL, 50, 0.01) {
		t.Errorf("TotalPnL = %f, want 50", s.TotalPnL)
	}
}

func TestPerformanceTracker_LosingBet(t *testing.T) {
	pt := NewPerformanceTracker(1000)
	pt.AddBet(50, 2.0, false, 0, time.Now())

	s := pt.Summary()
	if s.Losses != 1 {
		t.Errorf("Losses = %d, want 1", s.Losses)
	}
	if !almostEqual(s.CurrentBankroll, 950, 0.01) {
		t.Errorf("CurrentBankroll = %f, want 950", s.CurrentBankroll)
	}
}

func TestPerformanceTracker_MultipleBets(t *testing.T) {
	pt := NewPerformanceTracker(1000)
	now := time.Now()

	pt.AddBet(50, 2.0, true, 0, now)  // +50
	pt.AddBet(50, 2.0, true, 0, now)  // +50
	pt.AddBet(50, 2.0, false, 0, now) // -50
	pt.AddBet(50, 3.0, true, 0, now)  // +100

	s := pt.Summary()
	if s.TotalBets != 4 {
		t.Errorf("TotalBets = %d, want 4", s.TotalBets)
	}
	if s.Wins != 3 {
		t.Errorf("Wins = %d, want 3", s.Wins)
	}
	if s.Losses != 1 {
		t.Errorf("Losses = %d, want 1", s.Losses)
	}
	if !almostEqual(s.WinRate, 75.0, 0.01) {
		t.Errorf("WinRate = %f, want 75.0", s.WinRate)
	}
	// Total PnL = 50 + 50 - 50 + 100 = 150
	if !almostEqual(s.TotalPnL, 150, 0.01) {
		t.Errorf("TotalPnL = %f, want 150", s.TotalPnL)
	}
	if !almostEqual(s.CurrentBankroll, 1150, 0.01) {
		t.Errorf("CurrentBankroll = %f, want 1150", s.CurrentBankroll)
	}
}

func TestPerformanceTracker_StreakTracking(t *testing.T) {
	pt := NewPerformanceTracker(1000)
	now := time.Now()

	// Win streak of 3
	pt.AddBet(10, 2.0, true, 0, now)
	pt.AddBet(10, 2.0, true, 0, now)
	pt.AddBet(10, 2.0, true, 0, now)
	// Loss streak of 2
	pt.AddBet(10, 2.0, false, 0, now)
	pt.AddBet(10, 2.0, false, 0, now)
	// Another win
	pt.AddBet(10, 2.0, true, 0, now)

	s := pt.Summary()
	if s.LongestWinStreak != 3 {
		t.Errorf("LongestWinStreak = %d, want 3", s.LongestWinStreak)
	}
	if s.LongestLossStreak != 2 {
		t.Errorf("LongestLossStreak = %d, want 2", s.LongestLossStreak)
	}
	if s.CurrentStreak != 1 {
		t.Errorf("CurrentStreak = %d, want 1", s.CurrentStreak)
	}
}

func TestPerformanceTracker_MaxDrawdown(t *testing.T) {
	pt := NewPerformanceTracker(1000)
	now := time.Now()

	// Win to 1100
	pt.AddBet(100, 2.0, true, 0, now)
	// Lose back to 1000
	pt.AddBet(100, 2.0, false, 0, now)

	s := pt.Summary()
	// Peak = 1100, trough = 1000, drawdown = 100/1100 * 100 ≈ 9.09%
	expected := 100.0 / 1100.0 * 100
	if !almostEqual(s.MaxDrawdown, expected, 0.1) {
		t.Errorf("MaxDrawdown = %f, want ~%f", s.MaxDrawdown, expected)
	}
}

func TestPerformanceTracker_ROI(t *testing.T) {
	pt := NewPerformanceTracker(1000)
	pt.AddBet(100, 2.0, true, 0, time.Now()) // +100

	s := pt.Summary()
	// ROI = (1100 - 1000) / 1000 * 100 = 10%
	if !almostEqual(s.ROI, 10.0, 0.01) {
		t.Errorf("ROI = %f, want 10.0", s.ROI)
	}
}

func TestPerformanceTracker_ProfitFactor(t *testing.T) {
	pt := NewPerformanceTracker(1000)
	now := time.Now()

	pt.AddBet(50, 3.0, true, 0, now)  // +100
	pt.AddBet(50, 2.0, false, 0, now) // -50

	s := pt.Summary()
	// Profit factor = total_won / total_lost = 100 / 50 = 2.0
	if !almostEqual(s.ProfitFactor, 2.0, 0.01) {
		t.Errorf("ProfitFactor = %f, want 2.0", s.ProfitFactor)
	}
}

func TestPerformanceTracker_Reset(t *testing.T) {
	pt := NewPerformanceTracker(1000)
	pt.AddBet(50, 2.0, true, 0, time.Now())
	pt.Reset()

	s := pt.Summary()
	if s.TotalBets != 0 {
		t.Errorf("after reset, TotalBets = %d, want 0", s.TotalBets)
	}

	_, curve := pt.EquityCurve()
	if len(curve) != 1 || !almostEqual(curve[0], 1000, 0.01) {
		t.Errorf("after reset, equity curve should be [1000], got %v", curve)
	}
}

func TestPerformanceTracker_CustomPnL(t *testing.T) {
	pt := NewPerformanceTracker(1000)
	// Supply custom PnL instead of auto-calculating
	pt.AddBet(50, 2.0, true, 75, time.Now())

	s := pt.Summary()
	if !almostEqual(s.TotalPnL, 75, 0.01) {
		t.Errorf("TotalPnL = %f, want 75", s.TotalPnL)
	}

	// Verify ProfitFactor uses totalWon
	if s.ProfitFactor <= 0 {
		t.Error("ProfitFactor should be positive for winning bet")
	}
}

func TestPerformanceTracker_AvgStake(t *testing.T) {
	pt := NewPerformanceTracker(1000)
	now := time.Now()
	pt.AddBet(30, 2.0, true, 0, now)
	pt.AddBet(50, 2.0, true, 0, now)
	pt.AddBet(40, 2.0, true, 0, now)

	s := pt.Summary()
	expected := (30.0 + 50.0 + 40.0) / 3.0
	if !almostEqual(s.AvgStake, math.Round(expected*100)/100, 0.01) {
		t.Errorf("AvgStake = %f, want %f", s.AvgStake, expected)
	}
}
