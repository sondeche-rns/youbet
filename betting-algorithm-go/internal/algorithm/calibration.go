package algorithm

import (
	"sync"

	"bet4me/betting-algorithm-go/internal/domain"
)

// PredictionRecord represents a single prediction with its outcome.
type PredictionRecord struct {
	MatchID          string
	PredictedOutcome string
	ActualOutcome    string
	PredictedProbs   map[string]float64
	Factors          map[string]interface{}
	Correct          bool
	Timestamp        string
}

// CalibrationEngine is a self-improving calibration system for the betting algorithm.
//
// Tracks prediction accuracy per factor and adjusts weights to maximize overall accuracy.
//
// Features:
// - Per-factor performance tracking
// - Gradual weight adjustment with learning rate
// - Protection against overfitting (max ±10% adjustment)
// - Minimum sample size requirement (20 predictions)
// - Thread-safe with RWMutex for concurrent access
type CalibrationEngine struct {
	mu                 sync.RWMutex
	learningRate       float64
	maxHistory         int
	predictionHistory  []PredictionRecord
	factorPerformance  map[string]*FactorStats
}

// FactorStats tracks performance statistics for a single factor.
type FactorStats struct {
	Correct      int
	Total        int
	Accuracy     float64
	Contribution float64
}

// NewCalibrationEngine creates a new calibration engine.
func NewCalibrationEngine(learningRate float64, maxHistory int) *CalibrationEngine {
	return &CalibrationEngine{
		learningRate:      learningRate,
		maxHistory:        maxHistory,
		predictionHistory: make([]PredictionRecord, 0, maxHistory),
		factorPerformance: make(map[string]*FactorStats),
	}
}

// RecordPrediction records a prediction and its actual outcome.
//
// This method is thread-safe.
func (ce *CalibrationEngine) RecordPrediction(
	matchID string,
	factors map[string]interface{},
	predictedProbs map[string]float64,
	predictedOutcome string,
	actualOutcome string,
	timestamp string,
) {
	ce.mu.Lock()
	defer ce.mu.Unlock()

	// Create prediction record
	record := PredictionRecord{
		MatchID:          matchID,
		PredictedOutcome: predictedOutcome,
		ActualOutcome:    actualOutcome,
		PredictedProbs:   copyProbs(predictedProbs),
		Factors:          factors,
		Correct:          predictedOutcome == actualOutcome,
		Timestamp:        timestamp,
	}

	// Add to history (maintain max size)
	ce.predictionHistory = append(ce.predictionHistory, record)
	if len(ce.predictionHistory) > ce.maxHistory {
		ce.predictionHistory = ce.predictionHistory[1:]
	}

	// Update factor performance tracking
	for factorName, factorData := range factors {
		// Get or create stats
		if _, exists := ce.factorPerformance[factorName]; !exists {
			ce.factorPerformance[factorName] = &FactorStats{}
		}
		stats := ce.factorPerformance[factorName]

		// Handle FactorResult objects
		if fr, ok := factorData.(domain.FactorResult); ok {
			if fr.Triggered {
				stats.Total++
				if record.Correct {
					stats.Correct++
				}
				stats.Contribution = fr.Weight
			}
		} else if _, ok := factorData.(map[string]interface{}); ok {
			// Handle legacy dict factors
			stats.Total++
			if record.Correct {
				stats.Correct++
			}
		}
	}

	// Recalculate accuracy for all factors
	for _, stats := range ce.factorPerformance {
		if stats.Total > 0 {
			stats.Accuracy = float64(stats.Correct) / float64(stats.Total)
		}
	}
}

// CalibrateWeights adjusts weights based on factor performance.
//
// Strategy:
// - Factors with above-average accuracy get slight weight increase
// - Factors with below-average accuracy get slight weight decrease
// - Adjustments capped at ±10% to prevent overfitting
// - Requires minimum 20 predictions
//
// Returns adjusted weights (normalized to sum = 1.0).
// This method is thread-safe.
func (ce *CalibrationEngine) CalibrateWeights(currentWeights map[string]float64) map[string]float64 {
	ce.mu.RLock()
	defer ce.mu.RUnlock()

	if len(ce.predictionHistory) < 20 {
		// Not enough data for calibration
		return copyWeights(currentWeights)
	}

	// Calculate overall accuracy
	correct := 0
	for _, record := range ce.predictionHistory {
		if record.Correct {
			correct++
		}
	}
	overallAccuracy := float64(correct) / float64(len(ce.predictionHistory))

	if overallAccuracy == 0 {
		// All predictions wrong, no calibration possible
		return copyWeights(currentWeights)
	}

	// Calculate adjustment for each factor
	adjustedWeights := copyWeights(currentWeights)

	for factorName, weight := range currentWeights {
		stats, exists := ce.factorPerformance[factorName]
		if !exists || stats.Total < 5 {
			// Not enough data for this factor
			continue
		}

		factorAccuracy := stats.Accuracy

		// Calculate relative performance
		performanceRatio := factorAccuracy / overallAccuracy

		// Calculate adjustment (positive if factor outperforms, negative if underperforms)
		adjustment := ce.learningRate * (performanceRatio - 1.0)

		// Cap adjustment at ±10%
		if adjustment > 0.10 {
			adjustment = 0.10
		} else if adjustment < -0.10 {
			adjustment = -0.10
		}

		// Apply adjustment
		newWeight := weight * (1 + adjustment)

		// Ensure weight stays positive
		if newWeight < 0.01 {
			newWeight = 0.01
		}

		adjustedWeights[factorName] = newWeight
	}

	// Normalize weights to sum = 1.0
	total := 0.0
	for _, w := range adjustedWeights {
		total += w
	}

	if total > 0 {
		for k := range adjustedWeights {
			adjustedWeights[k] /= total
		}
	}

	return adjustedWeights
}

// GetPerformanceReport generates comprehensive performance report.
//
// This method is thread-safe.
func (ce *CalibrationEngine) GetPerformanceReport() map[string]interface{} {
	ce.mu.RLock()
	defer ce.mu.RUnlock()

	if len(ce.predictionHistory) == 0 {
		return map[string]interface{}{
			"overall_accuracy":        0.0,
			"total_predictions":       0,
			"factor_stats":            map[string]interface{}{},
			"recent_trend":            "N/A",
			"sample_size_sufficient":  false,
		}
	}

	// Overall stats
	totalPredictions := len(ce.predictionHistory)
	correctPredictions := 0
	for _, record := range ce.predictionHistory {
		if record.Correct {
			correctPredictions++
		}
	}
	overallAccuracy := float64(correctPredictions) / float64(totalPredictions)

	// Recent trend (last 20 predictions vs overall)
	recentPredictions := ce.predictionHistory
	if len(recentPredictions) > 20 {
		recentPredictions = recentPredictions[len(recentPredictions)-20:]
	}

	recentCorrect := 0
	for _, record := range recentPredictions {
		if record.Correct {
			recentCorrect++
		}
	}
	recentAccuracy := float64(recentCorrect) / float64(len(recentPredictions))

	trend := "stable"
	if recentAccuracy > overallAccuracy {
		trend = "improving"
	} else if recentAccuracy < overallAccuracy {
		trend = "declining"
	}

	// Factor stats
	factorStats := make(map[string]interface{})
	for factorName, stats := range ce.factorPerformance {
		if stats.Total > 0 {
			relativePerformance := 1.0
			if overallAccuracy > 0 {
				relativePerformance = stats.Accuracy / overallAccuracy
			}

			factorStats[factorName] = map[string]interface{}{
				"accuracy":             stats.Accuracy,
				"total_samples":        stats.Total,
				"contribution":         stats.Contribution,
				"relative_performance": relativePerformance,
			}
		}
	}

	// Outcome distribution
	outcomeDistribution := make(map[string]int)
	for _, record := range ce.predictionHistory {
		outcomeDistribution[record.ActualOutcome]++
	}

	return map[string]interface{}{
		"overall_accuracy":        overallAccuracy,
		"total_predictions":       totalPredictions,
		"correct_predictions":     correctPredictions,
		"recent_accuracy":         recentAccuracy,
		"recent_trend":            trend,
		"factor_stats":            factorStats,
		"outcome_distribution":    outcomeDistribution,
		"sample_size_sufficient":  totalPredictions >= 20,
	}
}

// GetUnderperformingFactors identifies factors performing below threshold.
//
// Returns list of factor names performing below the threshold.
// This method is thread-safe.
func (ce *CalibrationEngine) GetUnderperformingFactors(threshold float64) []string {
	ce.mu.RLock()
	defer ce.mu.RUnlock()

	if len(ce.predictionHistory) < 20 {
		return []string{}
	}

	correct := 0
	for _, record := range ce.predictionHistory {
		if record.Correct {
			correct++
		}
	}
	overallAccuracy := float64(correct) / float64(len(ce.predictionHistory))

	if overallAccuracy == 0 {
		return []string{}
	}

	underperforming := []string{}
	for factorName, stats := range ce.factorPerformance {
		if stats.Total >= 5 { // Minimum sample size
			relativePerformance := stats.Accuracy / overallAccuracy
			if relativePerformance < threshold {
				underperforming = append(underperforming, factorName)
			}
		}
	}

	return underperforming
}

// Reset clears all calibration data.
//
// This method is thread-safe.
func (ce *CalibrationEngine) Reset() {
	ce.mu.Lock()
	defer ce.mu.Unlock()

	ce.predictionHistory = make([]PredictionRecord, 0, ce.maxHistory)
	ce.factorPerformance = make(map[string]*FactorStats)
}

// ExportHistory exports prediction history as a list of simplified records.
//
// This method is thread-safe.
func (ce *CalibrationEngine) ExportHistory() []map[string]interface{} {
	ce.mu.RLock()
	defer ce.mu.RUnlock()

	result := make([]map[string]interface{}, len(ce.predictionHistory))
	for i, record := range ce.predictionHistory {
		result[i] = map[string]interface{}{
			"match_id":          record.MatchID,
			"predicted_outcome": record.PredictedOutcome,
			"actual_outcome":    record.ActualOutcome,
			"correct":           record.Correct,
			"predicted_probs":   copyProbs(record.PredictedProbs),
			"timestamp":         record.Timestamp,
		}
	}

	return result
}

// Helper functions

func copyWeights(weights map[string]float64) map[string]float64 {
	result := make(map[string]float64, len(weights))
	for k, v := range weights {
		result[k] = v
	}
	return result
}

func copyProbs(probs map[string]float64) map[string]float64 {
	result := make(map[string]float64, len(probs))
	for k, v := range probs {
		result[k] = v
	}
	return result
}
