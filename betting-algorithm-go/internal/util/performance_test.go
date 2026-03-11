package util

import (
	"testing"
)

func TestPerformanceTrackerAddBet(t *testing.T) {
	pt := NewPerformanceTracker(1000)

	// Win: stake 50 at odds 2.0
	pt.AddBet(50, 2.0, true, nil, nil)
	if pt.Bankroll != 1050 {
		t.Errorf("expected bankroll 1050 after win, got %f", pt.Bankroll)
	}
	if pt.Wins != 1 || pt.Losses != 0 {
		t.Errorf("expected 1 win 0 losses, got %d/%d", pt.Wins, pt.Losses)
	}
	if pt.CurrentStreak != 1 {
		t.Errorf("expected streak 1, got %d", pt.CurrentStreak)
	}

	// Loss: stake 30 at odds 3.0
	pt.AddBet(30, 3.0, false, nil, nil)
	if pt.Bankroll != 1020 {
		t.Errorf("expected bankroll 1020 after loss, got %f", pt.Bankroll)
	}
	if pt.Wins != 1 || pt.Losses != 1 {
		t.Errorf("expected 1/1, got %d/%d", pt.Wins, pt.Losses)
	}
	if pt.CurrentStreak != -1 {
		t.Errorf("expected streak -1 after loss, got %d", pt.CurrentStreak)
	}
}

func TestPerformanceTrackerStreaks(t *testing.T) {
	pt := NewPerformanceTracker(1000)

	// 3 wins in a row
	pt.AddBet(10, 2.0, true, nil, nil)
	pt.AddBet(10, 2.0, true, nil, nil)
	pt.AddBet(10, 2.0, true, nil, nil)

	if pt.LongestWinStreak != 3 {
		t.Errorf("expected longest win streak 3, got %d", pt.LongestWinStreak)
	}
	if pt.CurrentStreak != 3 {
		t.Errorf("expected current streak 3, got %d", pt.CurrentStreak)
	}

	// 2 losses
	pt.AddBet(10, 2.0, false, nil, nil)
	pt.AddBet(10, 2.0, false, nil, nil)

	if pt.LongestLossStreak != 2 {
		t.Errorf("expected longest loss streak 2, got %d", pt.LongestLossStreak)
	}
	if pt.CurrentStreak != -2 {
		t.Errorf("expected current streak -2, got %d", pt.CurrentStreak)
	}

	// Win streak should still be 3
	if pt.LongestWinStreak != 3 {
		t.Errorf("longest win streak should still be 3, got %d", pt.LongestWinStreak)
	}
}

func TestPerformanceTrackerSummary(t *testing.T) {
	pt := NewPerformanceTracker(1000)

	// Empty summary
	s := pt.GetSummary()
	if s.TotalBets != 0 {
		t.Error("empty tracker should have 0 bets")
	}

	// Add some bets
	pt.AddBet(50, 2.0, true, nil, nil)  // win 50
	pt.AddBet(50, 2.0, false, nil, nil) // lose 50
	pt.AddBet(50, 3.0, true, nil, nil)  // win 100

	s = pt.GetSummary()
	if s.TotalBets != 3 {
		t.Errorf("expected 3 bets, got %d", s.TotalBets)
	}
	if s.Wins != 2 || s.Losses != 1 {
		t.Errorf("expected 2/1, got %d/%d", s.Wins, s.Losses)
	}
	// Win rate should be ~66.67%
	if s.WinRate < 66 || s.WinRate > 67 {
		t.Errorf("expected win rate ~66.67, got %f", s.WinRate)
	}
	// Bankroll should be 1000 + 50 - 50 + 100 = 1100
	if s.CurrentBankroll != 1100 {
		t.Errorf("expected bankroll 1100, got %f", s.CurrentBankroll)
	}
	// ROI should be 10%
	if s.ROI != 10.0 {
		t.Errorf("expected ROI 10.0, got %f", s.ROI)
	}
}

func TestPerformanceTrackerMaxDrawdown(t *testing.T) {
	pt := NewPerformanceTracker(1000)

	pt.AddBet(50, 2.0, true, nil, nil)  // bankroll: 1050
	pt.AddBet(100, 2.0, false, nil, nil) // bankroll: 950
	pt.AddBet(50, 2.0, false, nil, nil)  // bankroll: 900

	s := pt.GetSummary()
	// Peak was 1050, trough is 900 => drawdown = (1050-900)/1050*100 = 14.29%
	if s.MaxDrawdown < 14 || s.MaxDrawdown > 15 {
		t.Errorf("expected max drawdown ~14.29%%, got %f", s.MaxDrawdown)
	}
}

func TestPerformanceTrackerReset(t *testing.T) {
	pt := NewPerformanceTracker(1000)
	pt.AddBet(50, 2.0, true, nil, nil)
	pt.Reset()

	if pt.Bankroll != 1000 {
		t.Errorf("expected bankroll 1000 after reset, got %f", pt.Bankroll)
	}
	if len(pt.Bets) != 0 {
		t.Error("expected 0 bets after reset")
	}
	if pt.Wins != 0 || pt.Losses != 0 {
		t.Error("expected 0 wins/losses after reset")
	}
}

func TestPerformanceTrackerCustomPnL(t *testing.T) {
	pt := NewPerformanceTracker(1000)
	pnl := 75.0
	pt.AddBet(50, 2.0, true, &pnl, nil)

	if pt.Bankroll != 1075 {
		t.Errorf("expected bankroll 1075 with custom PnL, got %f", pt.Bankroll)
	}
}
