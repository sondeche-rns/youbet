package domain

// DefensiveStyle classifies a team's defensive approach based on possession.
type DefensiveStyle string

const (
	DefensiveStyleHighPress    DefensiveStyle = "high_press"     // > 55% avg possession
	DefensiveStyleBalanced     DefensiveStyle = "balanced"       // 45-55% possession
	DefensiveStyleLowBlock     DefensiveStyle = "low_block"      // < 45% possession
	DefensiveStyleCounterAttack DefensiveStyle = "counter_attack" // Low possession + high efficiency
)

// Outcome represents a match result.
type Outcome string

const (
	OutcomeHome Outcome = "Home"
	OutcomeDraw Outcome = "Draw"
	OutcomeAway Outcome = "Away"
)

// Recommendation represents the betting recommendation strength.
type Recommendation string

const (
	RecommendationStrongBet Recommendation = "Strong Bet"
	RecommendationValueBet  Recommendation = "Value Bet"
	RecommendationSmallEdge Recommendation = "Small Edge"
	RecommendationLean      Recommendation = "Lean"
	RecommendationNoBet     Recommendation = "No Bet"
)

// PlayStyle represents a team's general playing style.
type PlayStyle string

const (
	PlayStyleAttacking  PlayStyle = "attacking"
	PlayStyleBalanced   PlayStyle = "balanced"
	PlayStyleDefensive  PlayStyle = "defensive"
)

// WeightNormalizationMode controls how factor weights are normalized.
type WeightNormalizationMode string

const (
	WeightNormDynamic WeightNormalizationMode = "dynamic"
	WeightNormStatic  WeightNormalizationMode = "static"
)
