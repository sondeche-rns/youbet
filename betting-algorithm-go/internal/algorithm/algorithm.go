package algorithm

import (
	"math"
	"time"

	"bet4me/betting-algorithm-go/internal/context"
	"bet4me/betting-algorithm-go/internal/domain"
)

// PredictionEngine is the core betting algorithm using a multi-factor weighted prediction model.
//
// Features:
// - Poisson distribution for goal scoring
// - Probability calibration
// - Kelly Criterion bankroll management
// - Multi-sport support (football, basketball, tennis)
type PredictionEngine struct {
	sport             string
	config            *SportConfig
	weights           map[string]float64
	eloRatings        map[string]float64
	teamForm          map[string]string
	calibrationParams CalibrationParams
	calibrationEngine *CalibrationEngine
	historicalData    []context.HistoricalMatch // Set via SetHistoricalData for context building
}

// SportConfig holds sport-specific configuration parameters.
type SportConfig struct {
	Weights        map[string]float64
	HomeAdvantage  float64
	BaseElo        float64
	KFactor        float64
	DrawThreshold  float64
	MinConfidence  float64
	MaxGoalsLambda float64
}

// CalibrationParams holds Platt scaling parameters.
type CalibrationParams struct {
	A float64 // Platt scaling parameter a
	B float64 // Platt scaling parameter b
}

// PredictionResult is the output of a match prediction.
type PredictionResult struct {
	HomeTeam      string                 `json:"homeTeam"`
	AwayTeam      string                 `json:"awayTeam"`
	HomeWinProb   float64                `json:"homeWinProb"`
	DrawProb      float64                `json:"drawProb"`
	AwayWinProb   float64                `json:"awayWinProb"`
	Confidence    float64                `json:"confidence"`
	Recommendation *Recommendation       `json:"recommendation"`
	Factors       map[string]interface{} `json:"factors"`
	ExpectedGoals struct {
		Home float64 `json:"home"`
		Away float64 `json:"away"`
	} `json:"expectedGoals"`
	Timestamp string `json:"timestamp"`
}

// Recommendation provides betting guidance.
type Recommendation struct {
	Outcome          string             `json:"outcome"`
	Probability      float64            `json:"probability"`
	Recommendation   string             `json:"recommendation"`
	StakePercentage  float64            `json:"stakePercentage"`
	ExpectedValue    float64            `json:"expectedValue"`
	KellyStake       float64            `json:"kellyStake"`
	Confidence       float64            `json:"confidence"`
	EVByOutcome      map[string]float64 `json:"evByOutcome"`
}

// MatchData contains all input data for a match prediction.
type MatchData struct {
	HomeTeam     string  `json:"homeTeam"`
	AwayTeam     string  `json:"awayTeam"`
	Date         string  `json:"date"`
	Venue        string  `json:"venue"`
	Competition  string  `json:"competition"`

	// Odds (optional)
	HomeOdds     *float64 `json:"homeOdds"`
	DrawOdds     *float64 `json:"drawOdds"`
	AwayOdds     *float64 `json:"awayOdds"`

	// Expected Goals
	HomeXg       float64 `json:"homeXg"`
	AwayXg       float64 `json:"awayXg"`

	// Elo Ratings
	HomeElo      *float64 `json:"homeElo"`
	AwayElo      *float64 `json:"awayElo"`

	// Advanced Stats
	HomePPDA          float64 `json:"homePPDA"`
	AwayPPDA          float64 `json:"awayPPDA"`
	HomePossession    float64 `json:"homePossession"`
	AwayPossession    float64 `json:"awayPossession"`
	HomeShots         int     `json:"homeShots"`
	HomeShotsOnTarget int     `json:"homeShotsOnTarget"`
	AwayShots         int     `json:"awayShots"`
	AwayShotsOnTarget int     `json:"awayShotsOnTarget"`

	// Team Strength & Form
	HomePosition int    `json:"homePosition"`
	AwayPosition int    `json:"awayPosition"`
	HomeForm     string `json:"homeForm"`
	AwayForm     string `json:"awayForm"`

	// Tactical
	HomeFormation string `json:"homeFormation"`
	AwayFormation string `json:"awayFormation"`
	HomeStyle     string `json:"homeStyle"`
	AwayStyle     string `json:"awayStyle"`

	// Player Impact
	HomeKeyPlayersAvailable float64 `json:"homeKeyPlayersAvailable"`
	AwayKeyPlayersAvailable float64 `json:"awayKeyPlayersAvailable"`
	HomeStarRating          int     `json:"homeStarRating"`
	AwayStarRating          int     `json:"awayStarRating"`

	// Rest & Fatigue
	HomeRestDays    int `json:"homeRestDays"`
	AwayRestDays    int `json:"awayRestDays"`
	HomeGamesLast7  int `json:"homeGamesLast7"`
	AwayGamesLast7  int `json:"awayGamesLast7"`

	// Motivation & Context
	IsDerby             bool   `json:"isDerby"`
	IsNeutralVenue      bool   `json:"isNeutralVenue"`
	Weather             string `json:"weather"`
	AwayTravelDistance  float64 `json:"awayTravelDistance"`
	ExpectedAttendancePct float64 `json:"expectedAttendancePct"`
}

// NewPredictionEngine creates a new prediction engine for the specified sport.
func NewPredictionEngine(sport string, useV2Weights bool, enableCalibration bool) *PredictionEngine {
	engine := &PredictionEngine{
		sport:             sport,
		eloRatings:        make(map[string]float64),
		teamForm:          make(map[string]string),
		calibrationParams: CalibrationParams{A: 1.0, B: 0.0},
	}

	// Load sport configuration
	engine.config = loadSportConfig(sport)

	// Override with V2 weights if specified
	if useV2Weights {
		engine.weights = make(map[string]float64)
		for k, v := range domain.FootballWeightsV2 {
			engine.weights[k] = v
		}
		engine.config.Weights = engine.weights
	} else {
		engine.weights = make(map[string]float64)
		for k, v := range engine.config.Weights {
			engine.weights[k] = v
		}
	}

	// Initialize calibration engine if enabled
	if enableCalibration {
		engine.calibrationEngine = NewCalibrationEngine(0.01, 1000)
	}

	return engine
}

// loadSportConfig loads sport-specific configuration.
func loadSportConfig(sport string) *SportConfig {
	switch sport {
	case "football":
		return &SportConfig{
			Weights:        domain.FootballWeights,
			HomeAdvantage:  0.10,
			BaseElo:        1500,
			KFactor:        32,
			DrawThreshold:  0.25,
			MinConfidence:  0.55,
			MaxGoalsLambda: 4.0,
		}
	case "basketball":
		return &SportConfig{
			Weights: map[string]float64{
				"offensiveRating": 0.20,
				"defensiveRating": 0.18,
				"pace":            0.12,
				"teamStrength":    0.15,
				"currentForm":     0.12,
				"playerImpact":    0.10,
				"restAndFatigue":  0.08,
				"homeAdvantage":   0.05,
			},
			HomeAdvantage: 0.06,
			BaseElo:       1500,
			KFactor:       20,
			MinConfidence: 0.55,
		}
	case "tennis":
		return &SportConfig{
			Weights: map[string]float64{
				"surfacePerformance": 0.25,
				"headToHead":         0.15,
				"currentForm":        0.20,
				"ranking":            0.15,
				"physicalCondition":  0.10,
				"serveStats":         0.15,
			},
			MinConfidence: 0.60,
		}
	default:
		// Default to football
		return loadSportConfig("football")
	}
}

// SetHistoricalData sets historical data for context building (H2H, season stats).
func (e *PredictionEngine) SetHistoricalData(data []context.HistoricalMatch) {
	e.historicalData = data
}

// RecordActualResult records actual match result for calibration.
func (e *PredictionEngine) RecordActualResult(
	matchID string,
	actualOutcome string,
	predictedOutcome string,
	predictedProbs map[string]float64,
	factors map[string]interface{},
) {
	if e.calibrationEngine != nil {
		e.calibrationEngine.RecordPrediction(
			matchID,
			factors,
			predictedProbs,
			predictedOutcome,
			actualOutcome,
			time.Now().Format(time.RFC3339),
		)
	}
}

// ApplyCalibration applies calibration adjustments to weights based on performance.
func (e *PredictionEngine) ApplyCalibration() map[string]float64 {
	if e.calibrationEngine != nil {
		adjustedWeights := e.calibrationEngine.CalibrateWeights(e.weights)
		e.weights = adjustedWeights
		e.config.Weights = adjustedWeights
		return adjustedWeights
	}
	return e.weights
}

// GetCalibrationReport returns performance report from calibration engine.
func (e *PredictionEngine) GetCalibrationReport() map[string]interface{} {
	if e.calibrationEngine != nil {
		return e.calibrationEngine.GetPerformanceReport()
	}
	return map[string]interface{}{
		"error": "Calibration not enabled",
	}
}

// Predict generates a complete match prediction.
func (e *PredictionEngine) Predict(data *MatchData) (*PredictionResult, error) {
	// Set defaults for optional fields
	e.setDefaults(data)

	// Calculate all factors
	factors := e.calculateAllFactors(data)

	// Calculate raw probabilities using weighted factors
	rawProbs := e.calculateWeightedProbabilities(factors)

	// If we have market odds, incorporate them (weight depends on data quality)
	if data.HomeOdds != nil && data.DrawOdds != nil && data.AwayOdds != nil {
		marketProbs := oddsToProbs(*data.HomeOdds, *data.DrawOdds, *data.AwayOdds)

		// Determine data quality: how much real data do we have vs defaults?
		dataQuality := e.assessDataQuality(data)

		// Low data quality → trust market more (up to 60% market weight)
		// High data quality → trust model more (30% market weight)
		modelWeight := 0.40 + dataQuality*0.30 // range: 0.40 (poor data) to 0.70 (rich data)
		rawProbs = blendProbabilities(rawProbs, marketProbs, modelWeight)
	}

	// Apply Poisson model for football
	var blendedProbs Probabilities
	if e.sport == "football" {
		poissonProbs := e.calculatePoissonProbabilities(data, factors)
		// Blend weighted model with Poisson (60% Poisson, 40% weighted)
		blendedProbs = blendProbabilities(rawProbs, poissonProbs, 0.6)
	} else {
		blendedProbs = rawProbs
	}

	// Calibrate probabilities
	calibratedProbs := e.calibrateProbabilities(blendedProbs)

	// Calculate confidence
	confidence := e.calculateConfidence(factors, calibratedProbs)

	// Generate betting recommendation
	recommendation := e.generateRecommendation(
		calibratedProbs,
		confidence,
		data.HomeOdds,
		data.DrawOdds,
		data.AwayOdds,
	)

	// Build result
	result := &PredictionResult{
		HomeTeam:       data.HomeTeam,
		AwayTeam:       data.AwayTeam,
		HomeWinProb:    round(calibratedProbs.Home, 4),
		DrawProb:       round(calibratedProbs.Draw, 4),
		AwayWinProb:    round(calibratedProbs.Away, 4),
		Confidence:     round(confidence, 4),
		Recommendation: recommendation,
		Factors:        factors,
		Timestamp:      time.Now().Format(time.RFC3339),
	}

	// Set expected goals
	if xgData, ok := factors["expectedGoals"].(map[string]interface{}); ok {
		if homeXg, ok := xgData["homeXg"].(float64); ok {
			result.ExpectedGoals.Home = round(homeXg, 2)
		}
		if awayXg, ok := xgData["awayXg"].(float64); ok {
			result.ExpectedGoals.Away = round(awayXg, 2)
		}
	}

	return result, nil
}

// setDefaults sets default values for optional fields in MatchData.
func (e *PredictionEngine) setDefaults(data *MatchData) {
	if data.HomeXg == 0 {
		data.HomeXg = 1.3
	}
	if data.AwayXg == 0 {
		data.AwayXg = 1.3
	}
	if data.HomePossession == 0 {
		data.HomePossession = 50
	}
	if data.AwayPossession == 0 {
		data.AwayPossession = 50
	}
	if data.HomePPDA == 0 {
		data.HomePPDA = 10.0
	}
	if data.AwayPPDA == 0 {
		data.AwayPPDA = 10.0
	}
	if data.HomeShots == 0 {
		data.HomeShots = 11
	}
	if data.HomeShotsOnTarget == 0 {
		data.HomeShotsOnTarget = 4
	}
	if data.AwayShots == 0 {
		data.AwayShots = 11
	}
	if data.AwayShotsOnTarget == 0 {
		data.AwayShotsOnTarget = 4
	}
	if data.HomePosition == 0 {
		data.HomePosition = 10
	}
	if data.AwayPosition == 0 {
		data.AwayPosition = 10
	}
	if data.HomeForm == "" {
		data.HomeForm = "WDWLD"
	}
	if data.AwayForm == "" {
		data.AwayForm = "WDWLD"
	}
	if data.HomeFormation == "" {
		data.HomeFormation = "4-3-3"
	}
	if data.AwayFormation == "" {
		data.AwayFormation = "4-4-2"
	}
	if data.HomeStyle == "" {
		data.HomeStyle = "balanced"
	}
	if data.AwayStyle == "" {
		data.AwayStyle = "balanced"
	}
	if data.HomeKeyPlayersAvailable == 0 {
		data.HomeKeyPlayersAvailable = 1.0
	}
	if data.AwayKeyPlayersAvailable == 0 {
		data.AwayKeyPlayersAvailable = 1.0
	}
	if data.HomeStarRating == 0 {
		data.HomeStarRating = 3
	}
	if data.AwayStarRating == 0 {
		data.AwayStarRating = 3
	}
	if data.HomeRestDays == 0 {
		data.HomeRestDays = 7
	}
	if data.AwayRestDays == 0 {
		data.AwayRestDays = 7
	}
	if data.HomeGamesLast7 == 0 {
		data.HomeGamesLast7 = 1
	}
	if data.AwayGamesLast7 == 0 {
		data.AwayGamesLast7 = 1
	}
	if data.Weather == "" {
		data.Weather = "clear"
	}
	if data.ExpectedAttendancePct == 0 {
		data.ExpectedAttendancePct = 85
	}
}

// Probabilities holds the three-way probabilities for home/draw/away.
type Probabilities struct {
	Home float64
	Draw float64
	Away float64
}

// GetWeights returns a copy of the current factor weights.
func (e *PredictionEngine) GetWeights() map[string]float64 {
	out := make(map[string]float64, len(e.weights))
	for k, v := range e.weights {
		out[k] = v
	}
	return out
}

// SetWeights replaces the current factor weights and updates the sport config.
func (e *PredictionEngine) SetWeights(weights map[string]float64) {
	e.weights = make(map[string]float64, len(weights))
	for k, v := range weights {
		e.weights[k] = v
	}
	e.config.Weights = e.weights
}

// round rounds a float64 to the specified number of decimal places.
func round(val float64, decimals int) float64 {
	multiplier := math.Pow(10, float64(decimals))
	return math.Round(val*multiplier) / multiplier
}
