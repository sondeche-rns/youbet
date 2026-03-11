package domain

import "fmt"

// DefensiveStyle classifies a team's defensive approach based on possession.
type DefensiveStyle string

const (
	DefensiveStyleHighPress     DefensiveStyle = "high_press"      // > 55% avg possession
	DefensiveStyleBalanced      DefensiveStyle = "balanced"         // 45-55% possession
	DefensiveStyleLowBlock      DefensiveStyle = "low_block"        // < 45% possession
	DefensiveStyleCounterAttack DefensiveStyle = "counter_attack"   // Low possession + high efficiency
)

// ValidDefensiveStyles contains all valid DefensiveStyle values.
var ValidDefensiveStyles = map[DefensiveStyle]bool{
	DefensiveStyleHighPress:     true,
	DefensiveStyleBalanced:      true,
	DefensiveStyleLowBlock:      true,
	DefensiveStyleCounterAttack: true,
}

// Validate checks if the defensive style is valid.
func (d DefensiveStyle) Validate() error {
	if !ValidDefensiveStyles[d] {
		return fmt.Errorf("invalid defensive style: %q", d)
	}
	return nil
}

// Outcome represents a match result.
type Outcome string

const (
	OutcomeWin  Outcome = "W"
	OutcomeDraw Outcome = "D"
	OutcomeLoss Outcome = "L"
)

// ValidOutcomes contains all valid Outcome values.
var ValidOutcomes = map[Outcome]bool{
	OutcomeWin:  true,
	OutcomeDraw: true,
	OutcomeLoss: true,
}

// Validate checks if the outcome is valid.
func (o Outcome) Validate() error {
	if !ValidOutcomes[o] {
		return fmt.Errorf("invalid outcome: %q", o)
	}
	return nil
}

// Recommendation represents the algorithm's betting recommendation.
type Recommendation string

const (
	RecommendHome Recommendation = "HOME"
	RecommendDraw Recommendation = "DRAW"
	RecommendAway Recommendation = "AWAY"
	RecommendSkip Recommendation = "SKIP"
)

// PlayStyle classifies a team's overall playing style.
type PlayStyle string

const (
	StyleAttacking PlayStyle = "attacking"
	StyleBalanced  PlayStyle = "balanced"
	StyleDefensive PlayStyle = "defensive"
)
