"""
Professional Betting Algorithm
Multi-factor prediction model with Poisson distribution and probability calibration
"""

import numpy as np
from scipy.stats import poisson
from datetime import datetime
from typing import Dict, List, Optional
import json
from dataclasses import asdict
from pathlib import Path

from .config import FOOTBALL_WEIGHTS, INITIAL_BANKROLL, KELLY_FRACTION, MAX_BET_PERCENTAGE
from .models import FactorResult, FactorCalculator


class ProfessionalBettingAlgorithm:
    """
    Professional betting algorithm using 18-factor weighted prediction model.

    Factors are registered as FactorCalculator adapters in self.calculators.
    Each calculator receives base_weight from FOOTBALL_WEIGHTS_V2 at construction.
    The compositor (_calculate_all_factors) runs all calculators and aggregates results.
    """

    def __init__(self, sport: str = 'football', use_v2_weights: bool = True, enable_calibration: bool = True):
        self.sport = sport
        self.config = self._load_config(sport)

        if use_v2_weights:
            from .config import FOOTBALL_WEIGHTS_V2
            self.config['weights'] = FOOTBALL_WEIGHTS_V2

        self.elo_ratings = {}
        self.team_form = {}
        self.calibration_params = {'a': 1.0, 'b': 0.0}
        self.historical_data = None
        self._store = None

        self.calibration_engine = None
        if enable_calibration:
            from .calibration import CalibrationEngine
            self.calibration_engine = CalibrationEngine(learning_rate=0.01, max_history=1000)

        self.calculators: List[FactorCalculator] = self._build_calculators(self.config['weights'])

    def _build_calculators(self, weights: Dict) -> List[FactorCalculator]:
        from .factors import (
            ExpectedGoalsCalculator, AdvancedStatsCalculator, TeamStrengthCalculator,
            TacticalMatchupCalculator, CurrentFormCalculator, PlayerImpactCalculator,
            RestFatigueCalculator, MotivationCalculator, HomeAdvantageCalculator,
            ExternalFactorsCalculator, TeamQualityGapCalculator,
            H2HHistoricalCalculator, H2HAnomalyCalculator,
            PossessionQualityCalculator, ManagerMomentumCalculator,
            RelegationMotivationCalculator, CounterAttackCalculator,
            AwayDrawFrequencyCalculator,
        )
        return [
            ExpectedGoalsCalculator(weights.get('expectedGoals', 0.0)),
            AdvancedStatsCalculator(weights.get('advancedStats', 0.0)),
            TeamStrengthCalculator(weights.get('teamStrength', 0.0),
                                   base_elo=self.config.get('base_elo', 1500),
                                   elo_ratings=self.elo_ratings),
            TacticalMatchupCalculator(weights.get('tacticalMatchup', 0.0)),
            CurrentFormCalculator(weights.get('currentForm', 0.0)),
            PlayerImpactCalculator(weights.get('playerImpact', 0.0)),
            RestFatigueCalculator(weights.get('restAndFatigue', 0.0)),
            MotivationCalculator(weights.get('motivation', 0.0)),
            HomeAdvantageCalculator(weights.get('homeAdvantage', 0.0),
                                    home_advantage=self.config.get('home_advantage', 0.10)),
            ExternalFactorsCalculator(weights.get('externalFactors', 0.0)),
            TeamQualityGapCalculator(weights.get('teamQualityGap', 0.0),
                                     base_elo=self.config.get('base_elo', 1500),
                                     elo_ratings=self.elo_ratings),
            H2HHistoricalCalculator(weights.get('h2hHistorical', 0.0)),
            H2HAnomalyCalculator(weights.get('h2hAnomaly', 0.0)),
            PossessionQualityCalculator(weights.get('possessionQuality', 0.0)),
            ManagerMomentumCalculator(weights.get('managerMomentum', 0.0)),
            RelegationMotivationCalculator(weights.get('relegationMotivation', 0.0)),
            CounterAttackCalculator(weights.get('counterAttackEfficiency', 0.0)),
            AwayDrawFrequencyCalculator(weights.get('awayDrawFrequency', 0.0)),
        ]

    def set_historical_data(self, data):
        """Set historical data for context building (H2H, season stats)"""
        self.historical_data = data
        if data is not None:
            from .historical_data_store import CsvHistoricalDataStore
            self._store = CsvHistoricalDataStore(data)
        else:
            self._store = None

    def record_actual_result(self, match_id: str, actual_outcome: str, predicted_outcome: str,
                             predicted_probs: Dict[str, float], factors: Dict):
        """Record actual match result for calibration."""
        if self.calibration_engine:
            self.calibration_engine.record_prediction(
                match_id=match_id,
                factors=factors,
                predicted_probs=predicted_probs,
                predicted_outcome=predicted_outcome,
                actual_outcome=actual_outcome
            )

    def apply_calibration(self):
        """Apply calibration adjustments to weights and rebuild calculator registry."""
        if self.calibration_engine:
            adjusted_weights = self.calibration_engine.calibrate_weights(self.config['weights'])
            self.config['weights'] = adjusted_weights
            self.calculators = self._build_calculators(adjusted_weights)
            return adjusted_weights
        return self.config['weights']

    def get_calibration_report(self) -> Dict:
        """Get performance report from calibration engine"""
        if self.calibration_engine:
            return self.calibration_engine.get_performance_report()
        return {'error': 'Calibration not enabled'}

    def _load_config(self, sport: str) -> Dict:
        """Load sport-specific configuration"""
        configs = {
            'football': {
                'weights': FOOTBALL_WEIGHTS,
                'home_advantage': 0.10,
                'base_elo': 1500,
                'k_factor': 32,
                'draw_threshold': 0.25,
                'min_confidence': 0.55,
                'max_goals_lambda': 4.0
            },
            'basketball': {
                'weights': {
                    'offensiveRating': 0.20,
                    'defensiveRating': 0.18,
                    'pace': 0.12,
                    'teamStrength': 0.15,
                    'currentForm': 0.12,
                    'playerImpact': 0.10,
                    'restAndFatigue': 0.08,
                    'homeAdvantage': 0.05
                },
                'home_advantage': 0.06,
                'base_elo': 1500,
                'k_factor': 20,
                'min_confidence': 0.55
            },
            'tennis': {
                'weights': {
                    'surfacePerformance': 0.25,
                    'headToHead': 0.15,
                    'currentForm': 0.20,
                    'ranking': 0.15,
                    'physicalCondition': 0.10,
                    'serveStats': 0.15
                },
                'min_confidence': 0.60
            }
        }
        return configs.get(sport, configs['football'])

    def predict_match(self, match_data: Dict) -> Dict:
        """
        Main prediction method — generates full match prediction.

        Args:
            match_data: Dict with homeTeam, awayTeam, date, competition, optional stats and odds.

        Returns:
            Dict with probabilities, confidence, recommendation, and serialized factor results.
        """
        home_team = match_data.get('homeTeam', match_data.get('home_team', 'Home'))
        away_team = match_data.get('awayTeam', match_data.get('away_team', 'Away'))

        factors = self._calculate_all_factors(match_data)
        raw_probs = self._calculate_weighted_probabilities(factors)

        if match_data.get('homeOdds') and match_data.get('drawOdds') and match_data.get('awayOdds'):
            market_probs = self._odds_to_probabilities(
                match_data['homeOdds'], match_data['drawOdds'], match_data['awayOdds']
            )
            data_quality = self._assess_data_quality(match_data)
            model_weight = 0.40 + data_quality * 0.30
            raw_probs = self._blend_probabilities(raw_probs, market_probs, model_weight)

        if self.sport == 'football':
            poisson_probs = self._calculate_poisson_probabilities(match_data, factors)
            blended_probs = self._blend_probabilities(raw_probs, poisson_probs, 0.6)
        else:
            blended_probs = raw_probs

        calibrated_probs = self._calibrate_probabilities(blended_probs)
        confidence = self._calculate_confidence(factors, calibrated_probs)
        recommendation = self._generate_recommendation(
            calibrated_probs, confidence,
            match_data.get('homeOdds', match_data.get('home_odds')),
            match_data.get('drawOdds', match_data.get('draw_odds')),
            match_data.get('awayOdds', match_data.get('away_odds'))
        )

        factors_by_name = {f.name: f for f in factors}
        xg = factors_by_name.get('expectedGoals')

        return {
            'homeTeam': home_team,
            'awayTeam': away_team,
            'homeWinProb': round(calibrated_probs['home'], 4),
            'drawProb': round(calibrated_probs['draw'], 4),
            'awayWinProb': round(calibrated_probs['away'], 4),
            'confidence': round(confidence, 4),
            'recommendation': recommendation,
            'factors': {name: asdict(f) for name, f in factors_by_name.items()},
            'expectedGoals': {
                'home': round(xg.metadata.get('homeXg', 1.3) if xg else 1.3, 2),
                'away': round(xg.metadata.get('awayXg', 1.3) if xg else 1.3, 2),
            },
            'timestamp': datetime.now().isoformat()
        }

    def _calculate_all_factors(self, match_data: Dict) -> List[FactorResult]:
        """Run all registered calculators and return their results."""
        from .context_builder import MatchContextBuilder
        context = MatchContextBuilder(store=self._store).build_context(match_data)
        return [calc.calculate(match_data, context) for calc in self.calculators]

    def _calculate_weighted_probabilities(self, factors: List[FactorResult]) -> Dict:
        """Aggregate FactorResults into home/draw/away probabilities."""
        active = [f for f in factors if f.triggered and f.weight > 0]

        total_weight = sum(f.weight for f in active)
        if total_weight == 0:
            return {'home': 0.33, 'draw': 0.34, 'away': 0.33}

        weighted_score = sum(f.value * f.weight for f in active) / total_weight

        draw_boost_total = sum(f.metadata.get('draw_boost', 0.0) for f in active if f.metadata)
        home_boost_total = sum(f.metadata.get('home_win_boost', 0.0) for f in active if f.metadata)

        xg = next((f for f in factors if f.name == 'expectedGoals'), None)
        h_xg = xg.metadata.get('homeXg', 1.3) if xg else 1.3
        a_xg = xg.metadata.get('awayXg', 1.3) if xg else 1.3

        draw_prob = self._calculate_draw_probability(weighted_score, h_xg, a_xg, draw_boost_total)
        home_prob = weighted_score * (1 - draw_prob) + home_boost_total
        away_prob = (1 - weighted_score) * (1 - draw_prob) - home_boost_total

        home_prob = max(0.05, min(0.90, home_prob))
        draw_prob = max(0.05, min(0.90, draw_prob))
        away_prob = max(0.05, min(0.90, away_prob))

        total = home_prob + draw_prob + away_prob
        return {'home': home_prob / total, 'draw': draw_prob / total, 'away': away_prob / total}

    def _calculate_draw_probability(self, weighted_score: float,
                                    h_xg: float = 1.3, a_xg: float = 1.3,
                                    draw_boost_total: float = 0.0) -> float:
        """Calculate draw probability using multi-signal model."""
        base_draw = 0.26
        quality_gap = abs(weighted_score - 0.5)
        quality_gap_adjustment = 0.06 - quality_gap * 0.32

        total_xg = h_xg + a_xg
        if total_xg < 2.0:
            defensive_boost = 0.05
        elif total_xg < 2.5:
            defensive_boost = 0.02
        else:
            defensive_boost = 0.0

        xg_diff = abs(h_xg - a_xg)
        xg_closeness_adj = max(-0.04, 0.04 - xg_diff * 0.04)

        draw_prob = base_draw + quality_gap_adjustment + defensive_boost + xg_closeness_adj + draw_boost_total
        return max(0.08, min(0.40, draw_prob))

    def _assess_data_quality(self, match_data: Dict) -> float:
        """Return 0.0 (defaults only) to 1.0 (rich data) based on fields present."""
        data_fields = [
            ('home_xg', 'homeXg'), ('away_xg', 'awayXg'),
            ('home_elo', 'away_elo'), ('home_position', 'homePosition'),
            ('away_position', 'awayPosition'), ('home_form',), ('away_form',),
            ('home_possession', 'away_possession'), ('homeStarRating', 'awayStarRating'),
            ('homeStyle', 'awayStyle'),
        ]
        fields_present = 0
        for field_group in data_fields:
            for field in field_group:
                if field in match_data:
                    fields_present += 1
                    break
        return min(1.0, fields_present / len(data_fields))

    def _calculate_poisson_probabilities(self, match_data: Dict, factors: List[FactorResult]) -> Dict:
        """Calculate probabilities using Poisson distribution over scorelines."""
        xg_factor = next((f for f in factors if f.name == 'expectedGoals'), None)
        home_xg = xg_factor.metadata.get('homeXg', 1.3) if xg_factor else 1.3
        away_xg = xg_factor.metadata.get('awayXg', 1.3) if xg_factor else 1.3

        strength_factor = next((f for f in factors if f.name == 'teamStrength'), None)
        strength_score = strength_factor.value if strength_factor else 0.5

        home_xg *= (0.8 + strength_score * 0.4)
        away_xg *= (1.2 - strength_score * 0.4)
        home_xg = min(home_xg, self.config.get('max_goals_lambda', 4.0))
        away_xg = min(away_xg, self.config.get('max_goals_lambda', 4.0))

        home_win_prob = draw_prob = away_win_prob = 0.0
        for home_goals in range(6):
            for away_goals in range(6):
                prob = poisson.pmf(home_goals, home_xg) * poisson.pmf(away_goals, away_xg)
                if home_goals > away_goals:
                    home_win_prob += prob
                elif home_goals == away_goals:
                    draw_prob += prob
                else:
                    away_win_prob += prob

        total = home_win_prob + draw_prob + away_win_prob
        return {'home': home_win_prob / total, 'draw': draw_prob / total, 'away': away_win_prob / total}

    def _blend_probabilities(self, probs1: Dict, probs2: Dict, weight2: float) -> Dict:
        """Blend two probability distributions."""
        w1 = 1 - weight2
        return {
            'home': probs1['home'] * w1 + probs2['home'] * weight2,
            'draw': probs1['draw'] * w1 + probs2['draw'] * weight2,
            'away': probs1['away'] * w1 + probs2['away'] * weight2,
        }

    def _odds_to_probabilities(self, home_odds: float, draw_odds: float, away_odds: float) -> Dict:
        """Convert decimal odds to implied probabilities (margin removed)."""
        home_implied = 1 / home_odds if home_odds > 0 else 0.33
        draw_implied = 1 / draw_odds if draw_odds > 0 else 0.33
        away_implied = 1 / away_odds if away_odds > 0 else 0.33
        total = home_implied + draw_implied + away_implied
        return {'home': home_implied / total, 'draw': draw_implied / total, 'away': away_implied / total}

    def _calibrate_probabilities(self, probs: Dict) -> Dict:
        """Apply Platt scaling calibration."""
        a = self.calibration_params['a']
        b = self.calibration_params['b']

        def calibrate(p: float) -> float:
            return max(0.01, min(0.99, p * a + b * (p - 0.5)))

        calibrated = {k: calibrate(v) for k, v in probs.items()}
        total = sum(calibrated.values())
        return {k: v / total for k, v in calibrated.items()}

    def _calculate_confidence(self, factors: List[FactorResult], probs: Dict) -> float:
        """Calculate prediction confidence from probability spread and factor consistency."""
        max_prob = max(probs.values())
        min_prob = min(probs.values())
        spread_confidence = (max_prob - min_prob) * 0.5

        factor_values = [f.value for f in factors if f.triggered]
        if factor_values:
            consistency_bonus = max(0, 0.2 - float(np.std(factor_values)))
        else:
            consistency_bonus = 0

        confidence = (spread_confidence + consistency_bonus) * 0.8
        return min(0.95, max(0.40, 0.5 + confidence))

    def _generate_recommendation(self, probs: Dict, confidence: float,
                                  home_odds: Optional[float] = None,
                                  draw_odds: Optional[float] = None,
                                  away_odds: Optional[float] = None) -> Dict:
        """Generate betting recommendation using Kelly Criterion."""
        outcomes = [('Home Win', probs['home']), ('Draw', probs['draw']), ('Away Win', probs['away'])]
        predicted_outcome, predicted_prob = max(outcomes, key=lambda x: x[1])

        ev_home = ev_draw = ev_away = None
        best_ev = 0
        best_bet = None

        if home_odds:
            ev_home = (probs['home'] * home_odds) - 1
            if ev_home > best_ev:
                best_ev = ev_home
                best_bet = ('Home Win', probs['home'], home_odds)
        if draw_odds:
            ev_draw = (probs['draw'] * draw_odds) - 1
            if ev_draw > best_ev:
                best_ev = ev_draw
                best_bet = ('Draw', probs['draw'], draw_odds)
        if away_odds:
            ev_away = (probs['away'] * away_odds) - 1
            if ev_away > best_ev:
                best_ev = ev_away
                best_bet = ('Away Win', probs['away'], away_odds)

        stake_pct = 0.0
        recommendation_type = 'No Bet'

        if best_bet and best_ev > 0:
            prob, odds = best_bet[1], best_bet[2]
            b = odds - 1
            kelly = (b * prob - (1 - prob)) / b
            stake_pct = min(MAX_BET_PERCENTAGE / 100, max(0, kelly * KELLY_FRACTION))
            if best_ev > 0.10 and confidence > 0.70:
                recommendation_type = 'Strong Bet'
            elif best_ev > 0.05 and confidence > 0.60:
                recommendation_type = 'Value Bet'
            elif best_ev > 0:
                recommendation_type = 'Small Edge'
        elif predicted_prob > 0.60 and confidence > 0.65:
            recommendation_type = 'Lean'

        return {
            'outcome': predicted_outcome,
            'probability': round(predicted_prob * 100, 1),
            'recommendation': recommendation_type,
            'stakePercentage': round(stake_pct * 100, 2),
            'expectedValue': round(best_ev * 100, 2) if best_ev else 0,
            'kellyStake': round(stake_pct, 4),
            'confidence': round(confidence * 100, 1),
            'evByOutcome': {
                'home': round(ev_home * 100, 2) if ev_home else None,
                'draw': round(ev_draw * 100, 2) if ev_draw else None,
                'away': round(ev_away * 100, 2) if ev_away else None,
            }
        }

    def update_elo(self, home_team: str, away_team: str, home_goals: int, away_goals: int):
        """Update Elo ratings after a match."""
        home_elo = self.elo_ratings.get(home_team, self.config.get('base_elo', 1500))
        away_elo = self.elo_ratings.get(away_team, self.config.get('base_elo', 1500))

        expected_home = 1 / (1 + 10 ** ((away_elo - home_elo) / 400))
        expected_away = 1 - expected_home

        if home_goals > away_goals:
            actual_home, actual_away = 1, 0
        elif home_goals < away_goals:
            actual_home, actual_away = 0, 1
        else:
            actual_home = actual_away = 0.5

        k = self.config.get('k_factor', 32)
        self.elo_ratings[home_team] = home_elo + k * (actual_home - expected_home)
        self.elo_ratings[away_team] = away_elo + k * (actual_away - expected_away)

    def set_calibration(self, a: float, b: float):
        """Set Platt scaling calibration parameters."""
        self.calibration_params = {'a': a, 'b': b}

    def get_config(self) -> Dict:
        """Get current algorithm configuration."""
        return self.config

    def save_state(self, filepath: str):
        """Save algorithm state (Elo ratings, calibration)."""
        state = {
            'elo_ratings': self.elo_ratings,
            'calibration_params': self.calibration_params,
            'sport': self.sport
        }
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)

    def load_state(self, filepath: str):
        """Load algorithm state."""
        if Path(filepath).exists():
            with open(filepath, 'r') as f:
                state = json.load(f)
                self.elo_ratings = state.get('elo_ratings', {})
                self.calibration_params = state.get('calibration_params', {'a': 1.0, 'b': 0.0})


def predict_match(home_team: str, away_team: str, **kwargs) -> Dict:
    """Convenience function for quick one-off predictions."""
    algo = ProfessionalBettingAlgorithm('football')
    return algo.predict_match({'homeTeam': home_team, 'awayTeam': away_team, **kwargs})
