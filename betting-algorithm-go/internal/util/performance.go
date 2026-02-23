package util

import (
	"math"
	"time"
)

// BetRecord represents a single bet in the performance tracker.
type BetRecord struct {
	Stake         float64   `json:"stake"`
	Odds          float64   `json:"odds"`
	Won           bool      `json:"won"`
	PnL           float64   `json:"pnl"`
	Timestamp     time.Time `json:"timestamp"`
	BankrollAfter float64   `json:"bankroll_after"`
}

// PerformanceTracker tracks betting performance over time.
type PerformanceTracker struct {
	InitialBankroll float64      `json:"initial_bankroll"`
	Bankroll        float64      `json:"bankroll"`
	Bets            []BetRecord  `json:"bets"`
	Wins            int          `json:"wins"`
	Losses          int          `json:"losses"`
	TotalStaked     float64      `json:"total_staked"`
	TotalWon        float64      `json:"total_won"`
	TotalLost       float64      `json:"total_lost"`
	CurrentStreak   int          `json:"current_streak"`
	LongestWinStreak  int        `json:"longest_win_streak"`
	LongestLossStreak int        `json:"longest_loss_streak"`
	EquityCurve     []float64    `json:"equity_curve"`
	Timestamps      []time.Time  `json:"timestamps"`
}

// NewPerformanceTracker creates a new tracker with the given initial bankroll.
func NewPerformanceTracker(initialBankroll float64) *PerformanceTracker {
	now := time.Now()
	return &PerformanceTracker{
		InitialBankroll: initialBankroll,
		Bankroll:        initialBankroll,
		Bets:            make([]BetRecord, 0),
		EquityCurve:     []float64{initialBankroll},
		Timestamps:      []time.Time{now},
	}
}

// AddBet records a bet result. If pnl is nil, it is calculated from stake, odds, and won.
func (pt *PerformanceTracker) AddBet(stake, odds float64, won bool, pnl *float64, timestamp *time.Time) {
	var actualPnL float64
	if pnl != nil {
		actualPnL = *pnl
	} else if won {
		actualPnL = stake * (odds - 1)
	} else {
		actualPnL = -stake
	}

	ts := time.Now()
	if timestamp != nil {
		ts = *timestamp
	}

	record := BetRecord{
		Stake:         stake,
		Odds:          odds,
		Won:           won,
		PnL:           actualPnL,
		Timestamp:     ts,
		BankrollAfter: pt.Bankroll + actualPnL,
	}

	pt.Bets = append(pt.Bets, record)
	pt.Bankroll += actualPnL
	pt.TotalStaked += stake

	if won {
		pt.Wins++
		pt.TotalWon += actualPnL
		pt.updateStreak(true)
	} else {
		pt.Losses++
		pt.TotalLost += math.Abs(actualPnL)
		pt.updateStreak(false)
	}

	pt.EquityCurve = append(pt.EquityCurve, pt.Bankroll)
	pt.Timestamps = append(pt.Timestamps, ts)
}

func (pt *PerformanceTracker) updateStreak(won bool) {
	if won {
		if pt.CurrentStreak >= 0 {
			pt.CurrentStreak++
		} else {
			pt.CurrentStreak = 1
		}
		if pt.CurrentStreak > pt.LongestWinStreak {
			pt.LongestWinStreak = pt.CurrentStreak
		}
	} else {
		if pt.CurrentStreak <= 0 {
			pt.CurrentStreak--
		} else {
			pt.CurrentStreak = -1
		}
		absStreak := -pt.CurrentStreak
		if absStreak > pt.LongestLossStreak {
			pt.LongestLossStreak = absStreak
		}
	}
}

// PerformanceSummary is the output of GetSummary.
type PerformanceSummary struct {
	TotalBets         int     `json:"total_bets"`
	Wins              int     `json:"wins"`
	Losses            int     `json:"losses"`
	WinRate           float64 `json:"win_rate"`
	TotalStaked       float64 `json:"total_staked"`
	TotalPnL          float64 `json:"total_pnl"`
	ROI               float64 `json:"roi"`
	ProfitFactor      float64 `json:"profit_factor"`
	SharpeRatio       float64 `json:"sharpe_ratio"`
	MaxDrawdown       float64 `json:"max_drawdown"`
	CurrentBankroll   float64 `json:"current_bankroll"`
	LongestWinStreak  int     `json:"longest_win_streak"`
	LongestLossStreak int     `json:"longest_loss_streak"`
	CurrentStreak     int     `json:"current_streak"`
	AvgStake          float64 `json:"avg_stake"`
	AvgOdds           float64 `json:"avg_odds"`
}

// GetSummary returns a comprehensive performance summary.
func (pt *PerformanceTracker) GetSummary() PerformanceSummary {
	totalBets := pt.Wins + pt.Losses

	if totalBets == 0 {
		return PerformanceSummary{}
	}

	winRate := float64(pt.Wins) / float64(totalBets) * 100
	roi := CalculateROI(pt.InitialBankroll, pt.Bankroll)
	profitFactor := pt.TotalWon / math.Max(pt.TotalLost, 0.01)

	// Sharpe from equity curve returns
	var sharpe float64
	if len(pt.EquityCurve) > 1 {
		returns := make([]float64, len(pt.EquityCurve)-1)
		for i := 1; i < len(pt.EquityCurve); i++ {
			returns[i-1] = (pt.EquityCurve[i] - pt.EquityCurve[i-1]) / pt.EquityCurve[i-1]
		}
		sharpe = CalculateSharpeRatio(returns, 0.0)
	}

	maxDrawdown := pt.calculateMaxDrawdown()

	// Average odds
	var oddsSum float64
	for _, b := range pt.Bets {
		oddsSum += b.Odds
	}

	return PerformanceSummary{
		TotalBets:         totalBets,
		Wins:              pt.Wins,
		Losses:            pt.Losses,
		WinRate:           math.Round(winRate*100) / 100,
		TotalStaked:       math.Round(pt.TotalStaked*100) / 100,
		TotalPnL:          math.Round((pt.Bankroll-pt.InitialBankroll)*100) / 100,
		ROI:               math.Round(roi*100) / 100,
		ProfitFactor:      math.Round(profitFactor*100) / 100,
		SharpeRatio:       math.Round(sharpe*100) / 100,
		MaxDrawdown:       math.Round(maxDrawdown*100) / 100,
		CurrentBankroll:   math.Round(pt.Bankroll*100) / 100,
		LongestWinStreak:  pt.LongestWinStreak,
		LongestLossStreak: pt.LongestLossStreak,
		CurrentStreak:     pt.CurrentStreak,
		AvgStake:          math.Round(pt.TotalStaked/math.Max(float64(totalBets), 1)*100) / 100,
		AvgOdds:           math.Round(oddsSum/math.Max(float64(len(pt.Bets)), 1)*100) / 100,
	}
}

func (pt *PerformanceTracker) calculateMaxDrawdown() float64 {
	if len(pt.EquityCurve) < 2 {
		return 0.0
	}

	peak := pt.EquityCurve[0]
	maxDrawdown := 0.0

	for _, value := range pt.EquityCurve {
		if value > peak {
			peak = value
		}
		drawdown := (peak - value) / peak * 100
		if drawdown > maxDrawdown {
			maxDrawdown = drawdown
		}
	}

	return maxDrawdown
}

// Reset resets the tracker to its initial state.
func (pt *PerformanceTracker) Reset() {
	now := time.Now()
	pt.Bankroll = pt.InitialBankroll
	pt.Bets = make([]BetRecord, 0)
	pt.Wins = 0
	pt.Losses = 0
	pt.TotalStaked = 0
	pt.TotalWon = 0
	pt.TotalLost = 0
	pt.CurrentStreak = 0
	pt.LongestWinStreak = 0
	pt.LongestLossStreak = 0
	pt.EquityCurve = []float64{pt.InitialBankroll}
	pt.Timestamps = []time.Time{now}
}
