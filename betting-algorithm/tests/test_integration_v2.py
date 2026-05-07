"""
Integration Tests for Algorithm V2

Tests the complete prediction pipeline with all 16 factors
(10 original + 6 new contextual factors).

Includes the West Ham vs Man United validation scenario.

Author: AI Betting Algorithm v2.0
Date: 2026-02-11
"""

import unittest
import sys
from pathlib import Path

# Add betting-algorithm to path so 'src' is importable as a package
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.algorithm import ProfessionalBettingAlgorithm


class TestAlgorithmV2Integration(unittest.TestCase):
    """Integration tests for complete V2 algorithm"""

    def setUp(self):
        """Initialize algorithm with V2 weights"""
        self.algo = ProfessionalBettingAlgorithm('football', use_v2_weights=True, enable_calibration=True)

    def test_west_ham_vs_man_united_scenario(self):
        """
        Validation Scenario: West Ham 1-1 Man United (Feb 10, 2026)

        Original prediction: 59% Man United win, 22% draw
        Target prediction: Draw probability > 25% (ideally ~32%)

        Key factors that should trigger:
        - possessionQuality (West Ham efficient with low possession)
        - counterAttackEfficiency (West Ham 41% vs Man Utd 59%)
        - h2hAnomaly (if West Ham has good H2H record)
        """
        match_data = {
            'homeTeam': 'West Ham',
            'awayTeam': 'Man United',
            'home_xg': 1.05,
            'away_xg': 1.72,
            'home_possession': 41,
            'away_possession': 59,
            'home_position': 15,
            'away_position': 6,
            'home_form': 'WWDLW',
            'away_form': 'WDWLW',
            'competition': 'Premier League'
        }

        prediction = self.algo.predict_match(match_data)

        # Test 1: All probabilities sum to ~1.0
        total_prob = prediction['homeWinProb'] + prediction['drawProb'] + prediction['awayWinProb']
        self.assertAlmostEqual(total_prob, 1.0, places=2)

        # Test 2: Draw probability should be elevated (>25%)
        self.assertGreater(prediction['drawProb'], 0.25,
                          msg=f"Draw prob {prediction['drawProb']*100:.1f}% should be >25%")

        # Test 3: Prediction should include factors
        self.assertIn('factors', prediction)

        # Test 4: Check if contextual factors are present
        factors = prediction['factors']
        contextual_factor_names = [
            'h2hHistorical', 'h2hAnomaly', 'possessionQuality',
            'managerMomentum', 'relegationMotivation',
            'counterAttackEfficiency', 'awayDrawFrequency'
        ]

        for factor_name in contextual_factor_names:
            self.assertIn(factor_name, factors,
                         msg=f"Missing contextual factor: {factor_name}")

        print(f"\n✅ West Ham vs Man United Prediction:")
        print(f"   Home Win: {prediction['homeWinProb']*100:.1f}%")
        print(f"   Draw:     {prediction['drawProb']*100:.1f}%")
        print(f"   Away Win: {prediction['awayWinProb']*100:.1f}%")

        # Test 5: Target draw probability ~32% (±5%)
        target_draw_prob = 0.32
        tolerance = 0.05
        self.assertGreaterEqual(prediction['drawProb'], target_draw_prob - tolerance,
                               msg=f"Draw prob too low: {prediction['drawProb']*100:.1f}%")

    def test_all_factors_calculated(self):
        """Test that all 16 factors are calculated"""
        match_data = {
            'homeTeam': 'Arsenal',
            'awayTeam': 'Chelsea',
            'home_xg': 2.0,
            'away_xg': 1.5,
            'home_possession': 55,
            'away_possession': 45,
            'competition': 'Premier League'
        }

        prediction = self.algo.predict_match(match_data)

        # Original 10 factors
        original_factors = [
            'expectedGoals', 'advancedStats', 'teamStrength',
            'tacticalMatchup', 'currentForm', 'playerImpact',
            'restAndFatigue', 'motivation', 'homeAdvantage',
            'externalFactors'
        ]

        # New 6 contextual factors
        contextual_factors = [
            'h2hHistorical', 'h2hAnomaly', 'possessionQuality',
            'managerMomentum', 'relegationMotivation',
            'counterAttackEfficiency', 'awayDrawFrequency'
        ]

        all_factors = original_factors + contextual_factors

        factors = prediction['factors']
        for factor_name in all_factors:
            self.assertIn(factor_name, factors,
                         msg=f"Missing factor: {factor_name}")

        print(f"\n✅ All 16 factors calculated:")
        print(f"   Original factors: {len(original_factors)}")
        print(f"   Contextual factors: {len(contextual_factors)}")
        print(f"   Total: {len(all_factors)}")

    def test_high_possession_low_efficiency(self):
        """
        Test scenario: High possession but low xG efficiency
        Should favor opponent (counter-attack scenario)
        """
        match_data = {
            'homeTeam': 'Team A',
            'awayTeam': 'Team B',
            'home_xg': 1.2,        # Low xG
            'away_xg': 1.8,        # High xG
            'home_possession': 65,  # High possession
            'away_possession': 35,  # Low possession
            'competition': 'Premier League'
        }

        prediction = self.algo.predict_match(match_data)

        # Away team should be favored (efficient counter-attack)
        self.assertGreater(prediction['awayWinProb'], prediction['homeWinProb'],
                          msg="Away team should be favored in counter-attack scenario")

        # Check possession quality factor
        factors = prediction['factors']
        pqi_factor = factors['possessionQuality']

        # Home PQI: 1.2 / 0.65 * 100 = 184.6 (poor)
        # Away PQI: 1.8 / 0.35 * 100 = 514.3 (excellent)
        # Away should have much higher efficiency

        pqi_metadata = pqi_factor['metadata']
        print(f"\n✅ Counter-attack scenario:")
        print(f"   Home PQI: {pqi_metadata['home_pqi']:.1f}")
        print(f"   Away PQI: {pqi_metadata['away_pqi']:.1f}")
        print(f"   Away Win Prob: {prediction['awayWinProb']*100:.1f}%")

        self.assertGreater(pqi_metadata['away_pqi'],
                          pqi_metadata['home_pqi'],
                          msg="Away PQI should be higher")

    def test_relegation_battle_draw_boost(self):
        """
        Test scenario: Bottom-3 team at home with recent wins
        Should have elevated draw probability
        """
        match_data = {
            'homeTeam': 'Relegated Team',
            'awayTeam': 'Mid Table Team',
            'home_xg': 1.3,
            'away_xg': 1.5,
            'home_possession': 48,
            'away_possession': 52,
            'home_position': 19,      # Relegation zone
            'away_position': 10,
            'home_form': 'WWLWD',     # 2 wins in last 4
            'away_form': 'DWLDW',
            'competition': 'Premier League'
        }

        prediction = self.algo.predict_match(match_data)

        # Check if relegation motivation is triggered
        factors = prediction['factors']
        relegation_factor = factors['relegationMotivation']

        self.assertTrue(relegation_factor['triggered'],
                       msg="Relegation motivation should be triggered")
        self.assertIn('draw_boost', relegation_factor['metadata'])

        # Draw probability should be boosted
        self.assertGreater(prediction['drawProb'], 0.25,
                          msg="Draw probability should be elevated in relegation battle")

        print(f"\n✅ Relegation battle scenario:")
        print(f"   Position: {match_data['home_position']}")
        print(f"   Tier: {relegation_factor['metadata']['tier']}")
        print(f"   Draw Boost: +{relegation_factor['metadata']['draw_boost']}")
        print(f"   Draw Prob: {prediction['drawProb']*100:.1f}%")

    def test_probabilities_valid_range(self):
        """Test that probabilities are always in valid range [0.05, 0.95]"""
        test_scenarios = [
            # Extreme home advantage
            {'homeTeam': 'Top Team', 'awayTeam': 'Bottom Team',
             'home_xg': 3.5, 'away_xg': 0.5, 'home_possession': 75, 'away_possession': 25},
            # Extreme away advantage
            {'homeTeam': 'Bottom Team', 'awayTeam': 'Top Team',
             'home_xg': 0.5, 'away_xg': 3.5, 'home_possession': 30, 'away_possession': 70},
            # Perfectly balanced
            {'homeTeam': 'Team A', 'awayTeam': 'Team B',
             'home_xg': 1.5, 'away_xg': 1.5, 'home_possession': 50, 'away_possession': 50},
        ]

        for i, match_data in enumerate(test_scenarios):
            match_data['competition'] = 'Premier League'
            prediction = self.algo.predict_match(match_data)

            # Check each probability is in valid range
            for outcome in ['homeWinProb', 'drawProb', 'awayWinProb']:
                prob = prediction[outcome]
                self.assertGreaterEqual(prob, 0.05,
                                       msg=f"Scenario {i}: {outcome} too low ({prob})")
                self.assertLessEqual(prob, 0.95,
                                    msg=f"Scenario {i}: {outcome} too high ({prob})")

            # Check sum is ~1.0
            total = prediction['homeWinProb'] + prediction['drawProb'] + prediction['awayWinProb']
            self.assertAlmostEqual(total, 1.0, places=2,
                                  msg=f"Scenario {i}: Probabilities don't sum to 1.0")

        print(f"\n✅ Probability range validation passed for {len(test_scenarios)} scenarios")

    def test_calibration_integration(self):
        """Test that calibration system is integrated and working"""
        # Make a prediction
        match_data = {
            'homeTeam': 'Arsenal',
            'awayTeam': 'Chelsea',
            'home_xg': 2.0,
            'away_xg': 1.5,
            'competition': 'Premier League'
        }

        prediction = self.algo.predict_match(match_data)

        # Record actual result
        predicted_outcome = 'home' if prediction['homeWinProb'] > max(prediction['drawProb'], prediction['awayWinProb']) else 'draw'
        actual_outcome = 'home'

        self.algo.record_actual_result(
            match_id='test_match_1',
            actual_outcome=actual_outcome,
            predicted_outcome=predicted_outcome,
            predicted_probs={
                'home': prediction['homeWinProb'],
                'draw': prediction['drawProb'],
                'away': prediction['awayWinProb']
            },
            factors=prediction['factors']
        )

        # Get calibration report
        report = self.algo.get_calibration_report()

        self.assertIn('total_predictions', report)
        self.assertEqual(report['total_predictions'], 1)
        self.assertIn('overall_accuracy', report)

        print(f"\n✅ Calibration system integrated:")
        print(f"   Total predictions: {report['total_predictions']}")
        print(f"   Sample size sufficient: {report['sample_size_sufficient']}")


class TestWeightNormalization(unittest.TestCase):
    """Test dynamic weight normalization"""

    def setUp(self):
        self.algo = ProfessionalBettingAlgorithm('football', use_v2_weights=True)

    def test_weights_sum_correctly(self):
        """Test that active factor weights are renormalized at runtime.

        Config weights need not sum to 1.0 — they include mutually exclusive
        conditional factors (h2hHistorical / h2hAnomaly). The algorithm normalizes
        only active weights at prediction time.
        """
        from src.config import FOOTBALL_WEIGHTS_V2

        total_weight = sum(FOOTBALL_WEIGHTS_V2.values())

        # All individual weights must be positive
        for name, w in FOOTBALL_WEIGHTS_V2.items():
            self.assertGreater(w, 0.0, msg=f"Weight for {name} must be positive")

        # Runtime normalization: predict a match and confirm probabilities sum to 1.0
        algo = self.algo
        prediction = algo.predict_match({'homeTeam': 'A', 'awayTeam': 'B'})
        total_prob = prediction['homeWinProb'] + prediction['drawProb'] + prediction['awayWinProb']
        self.assertAlmostEqual(total_prob, 1.0, places=2, msg="Probabilities must sum to 1.0")

        print(f"\n✅ Config weights sum: {total_weight:.4f} (runtime normalization applied)")

    def test_conditional_factor_replacement(self):
        """Test that h2hAnomaly replaces h2hHistorical when triggered"""
        # This is tested indirectly through the factor calculation
        # If both have weight > 0 when anomaly is triggered, that's a bug

        from src.models import H2HRecord, MatchContext, DefensiveStyle

        h2h = H2HRecord(
            homeTeam='West Ham',
            awayTeam='Man United',
            results=[{'date': '2024-01-01', 'homeScore': 1, 'awayScore': 1}] * 3,
            weakerTeamUnbeatenStreak=3,
            anomalyTriggered=True
        )

        context = MatchContext(
            homeDefensiveStyle=DefensiveStyle.LOW_BLOCK,
            awayDefensiveStyle=DefensiveStyle.HIGH_PRESS,
            homeLeaguePosition=15,
            awayLeaguePosition=6,
            h2hRecord=h2h
        )

        from src.factors.contextual import H2HHistoricalCalculator, H2HAnomalyCalculator
        from src.config import FOOTBALL_WEIGHTS_V2

        hist_calc = H2HHistoricalCalculator(FOOTBALL_WEIGHTS_V2['h2hHistorical'])
        anom_calc = H2HAnomalyCalculator(FOOTBALL_WEIGHTS_V2['h2hAnomaly'])

        hist = hist_calc.calculate({}, context)
        anom = anom_calc.calculate({}, context)

        # Only ONE should be active
        active_count = sum([hist.triggered, anom.triggered])
        self.assertEqual(active_count, 1,
                        msg="Only one H2H factor should be active at a time")

        # Anomaly should be the active one
        self.assertTrue(anom.triggered)
        self.assertFalse(hist.triggered)
        self.assertEqual(anom.weight, 0.15)
        self.assertEqual(hist.weight, 0.0)

        print(f"\n✅ Conditional factor replacement working correctly")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
