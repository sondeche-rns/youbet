package util

import (
	"math"
	"sync"
	"time"
)

// BetRecord represents a single recorded bet.
type BetRecord struct {
	Stake         float64   `json:"stake"`
	Odds          float64   `json:"odds"`
	Won           bool      `json:"won"`
	PnL           float64   `json:"pnl"`
	Timestamp     time.Time `json:"timestamp"`
	BankrollAfter float64   `json:"bankroll_after"`
}

// PerformanceSummary holds computed performance metrics.
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

// PerformanceTracker tracks betting performance over time.
type PerformanceTracker struct {
	mu sync.RWMutex

	initialBankroll float64
	bankroll        float64

	bets       []BetRecord
	wins       int
	losses     int
	totalStaked float64
	totalWon    float64
	totalLost   float64

	currentStreak     int
	longestWinStreak  int
	longestLossStreak int

	equityCurve []float64
	timestamps  []time.Time
}

// NewPerformanceTracker creates a new tracker with the given initial bankroll.
func NewPerformanceTracker(initialBankroll float64) *PerformanceTracker {
	return &PerformanceTracker{
		initialBankroll: initialBankroll,
		bankroll:        initialBankroll,
		bets:            make([]BetRecord, 0),
		equityCurve:     []float64{initialBankroll},
		timestamps:      []time.Time{time.Now()},
	}
}

// AddBet records a bet result.
func (pt *PerformanceTracker) AddBet(stake, odds float64, won bool, pnl float64, ts time.Time) {
	pt.mu.Lock()
	defer pt.mu.Unlock()

	if pnl == 0 {
		if won {
			pnl = stake * (odds - 1)
		} else {
			pnl = -stake
		}
	}

	if ts.IsZero() {
		ts = time.Now()
	}

	pt.bankroll += pnl
	pt.totalStaked += stake

	record := BetRecord{
		Stake:         stake,
		Odds:          odds,
		Won:           won,
		PnL:           pnl,
		Timestamp:     ts,
		BankrollAfter: pt.bankroll,
	}
	pt.bets = append(pt.bets, record)

	if won {
		pt.wins++
		pt.totalWon += pnl
		pt.updateStreak(true)
	} else {
		pt.losses++
		pt.totalLost += math.Abs(pnl)
		pt.updateStreak(false)
	}

	pt.equityCurve = append(pt.equityCurve, pt.bankroll)
	pt.timestamps = append(pt.timestamps, ts)
}

func (pt *PerformanceTracker) updateStreak(won bool) {
	if won {
		if pt.currentStreak >= 0 {
			pt.currentStreak++
		} else {
			pt.currentStreak = 1
		}
		if pt.currentStreak > pt.longestWinStreak {
			pt.longestWinStreak = pt.currentStreak
		}
	} else {
		if pt.currentStreak <= 0 {
			pt.currentStreak--
		} else {
			pt.currentStreak = -1
		}
		absStreak := -pt.currentStreak
		if absStreak > pt.longestLossStreak {
			pt.longestLossStreak = absStreak
		}
	}
}

// Summary returns a comprehensive performance summary.
func (pt *PerformanceTracker) Summary() PerformanceSummary {
	pt.mu.RLock()
	defer pt.mu.RUnlock()

	totalBets := pt.wins + pt.losses
	if totalBets == 0 {
		return PerformanceSummary{}
	}

	winRate := float64(pt.wins) / float64(totalBets) * 100
	roi := ROI(pt.initialBankroll, pt.bankroll)
	profitFactor := pt.totalWon / math.Max(pt.totalLost, 0.01)

	// Calculate returns for Sharpe
	var sharpe float64
	if len(pt.equityCurve) > 1 {
		returns := make([]float64, len(pt.equityCurve)-1)
		for i := 1; i < len(pt.equityCurve); i++ {
			if pt.equityCurve[i-1] != 0 {
				returns[i-1] = (pt.equityCurve[i] - pt.equityCurve[i-1]) / pt.equityCurve[i-1]
			}
		}
		sharpe = SharpeRatio(returns, 0)
	}

	maxDD := pt.maxDrawdown()

	var totalOdds float64
	for _, b := range pt.bets {
		totalOdds += b.Odds
	}

	return PerformanceSummary{
		TotalBets:         totalBets,
		Wins:              pt.wins,
		Losses:            pt.losses,
		WinRate:           math.Round(winRate*100) / 100,
		TotalStaked:       math.Round(pt.totalStaked*100) / 100,
		TotalPnL:          math.Round((pt.bankroll-pt.initialBankroll)*100) / 100,
		ROI:               math.Round(roi*100) / 100,
		ProfitFactor:      math.Round(profitFactor*100) / 100,
		SharpeRatio:       math.Round(sharpe*100) / 100,
		MaxDrawdown:       math.Round(maxDD*100) / 100,
		CurrentBankroll:   math.Round(pt.bankroll*100) / 100,
		LongestWinStreak:  pt.longestWinStreak,
		LongestLossStreak: pt.longestLossStreak,
		CurrentStreak:     pt.currentStreak,
		AvgStake:          math.Round(pt.totalStaked/float64(max(totalBets, 1))*100) / 100,
		AvgOdds:           math.Round(totalOdds/float64(max(len(pt.bets), 1))*100) / 100,
	}
}

// maxDrawdown calculates the maximum drawdown percentage.
func (pt *PerformanceTracker) maxDrawdown() float64 {
	if len(pt.equityCurve) < 2 {
		return 0.0
	}

	peak := pt.equityCurve[0]
	maxDD := 0.0

	for _, value := range pt.equityCurve {
		if value > peak {
			peak = value
		}
		if peak > 0 {
			dd := (peak - value) / peak * 100
			if dd > maxDD {
				maxDD = dd
			}
		}
	}
	return maxDD
}

// EquityCurve returns the equity curve data.
func (pt *PerformanceTracker) EquityCurve() ([]time.Time, []float64) {
	pt.mu.RLock()
	defer pt.mu.RUnlock()
	return pt.timestamps, pt.equityCurve
}

// Reset resets the tracker to its initial state.
func (pt *PerformanceTracker) Reset() {
	pt.mu.Lock()
	defer pt.mu.Unlock()

	pt.bankroll = pt.initialBankroll
	pt.bets = make([]BetRecord, 0)
	pt.wins = 0
	pt.losses = 0
	pt.totalStaked = 0
	pt.totalWon = 0
	pt.totalLost = 0
	pt.currentStreak = 0
	pt.longestWinStreak = 0
	pt.longestLossStreak = 0
	pt.equityCurve = []float64{pt.initialBankroll}
	pt.timestamps = []time.Time{time.Now()}
}
