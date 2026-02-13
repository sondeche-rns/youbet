"""
Professional Betting Algorithm
Multi-factor prediction model with Poisson distribution and probability calibration
"""

import numpy as np
from scipy.stats import poisson
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
from pathlib import Path

from .config import FOOTBALL_WEIGHTS, INITIAL_BANKROLL, KELLY_FRACTION, MAX_BET_PERCENTAGE


class ProfessionalBettingAlgorithm:
    """
    Professional betting algorithm using 12-factor weighted prediction model.

    Features:
    - Poisson distribution for goal scoring
    - Probability calibration
    - Kelly Criterion bankroll management
    - Multi-sport support (football, basketball, tennis)
    """

    def __init__(self, sport: str = 'football', use_v2_weights: bool = True, enable_calibration: bool = True):
        self.sport = sport
        self.config = self._load_config(sport)

        # NEW: Add V2 weights support
        if use_v2_weights:
            from .config import FOOTBALL_WEIGHTS_V2
            self.config['weights'] = FOOTBALL_WEIGHTS_V2

        self.elo_ratings = {}
        self.team_form = {}
        self.calibration_params = {'a': 1.0, 'b': 0.0}  # Platt scaling params

        # NEW: Add historical data storage for context building
        self.historical_data = None  # Set via set_historical_data()

        # NEW: Add calibration engine for self-improving weights
        self.calibration_engine = None
        if enable_calibration:
            from .calibration import CalibrationEngine
            self.calibration_engine = CalibrationEngine(learning_rate=0.01, max_history=1000)

    def set_historical_data(self, data):
        """Set historical data for context building (H2H, season stats)"""
        self.historical_data = data

    def record_actual_result(self, match_id: str, actual_outcome: str, predicted_outcome: str,
                            predicted_probs: Dict[str, float], factors: Dict):
        """
        Record actual match result for calibration.

        Args:
            match_id: Unique match identifier
            actual_outcome: Actual result ('home', 'draw', 'away')
            predicted_outcome: Predicted result
            predicted_probs: Predicted probabilities
            factors: Factor data from prediction
        """
        if self.calibration_engine:
            self.calibration_engine.record_prediction(
                match_id=match_id,
                factors=factors,
                predicted_probs=predicted_probs,
                predicted_outcome=predicted_outcome,
                actual_outcome=actual_outcome
            )

    def apply_calibration(self):
        """Apply calibration adjustments to weights based on performance"""
        if self.calibration_engine:
            adjusted_weights = self.calibration_engine.calibrate_weights(self.config['weights'])
            self.config['weights'] = adjusted_weights
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
        Main prediction method - generates full match prediction.

        Args:
            match_data: Dict containing:
                - homeTeam: str
                - awayTeam: str
                - date: str (ISO format)
                - venue: str (optional)
                - competition: str
                - homeOdds: float (optional)
                - drawOdds: float (optional)
                - awayOdds: float (optional)
                - Additional stats if available

        Returns:
            Dict with prediction probabilities, confidence, and recommendation
        """
        home_team = match_data.get('homeTeam', match_data.get('home_team', 'Home'))
        away_team = match_data.get('awayTeam', match_data.get('away_team', 'Away'))

        # Calculate all 12 factors
        factors = self._calculate_all_factors(match_data)

        # Calculate raw probabilities using weighted factors
        raw_probs = self._calculate_weighted_probabilities(factors)

        # If we have market odds, incorporate them (weight depends on data quality)
        if match_data.get('homeOdds') and match_data.get('drawOdds') and match_data.get('awayOdds'):
            market_probs = self._odds_to_probabilities(
                match_data['homeOdds'],
                match_data['drawOdds'],
                match_data['awayOdds']
            )
            # Determine data quality: how much real data do we have vs defaults?
            data_quality = self._assess_data_quality(match_data)
            # Low data quality → trust market more (up to 60% market weight)
            # High data quality → trust model more (30% market weight)
            model_weight = 0.40 + data_quality * 0.30  # range: 0.40 (poor data) to 0.70 (rich data)
            raw_probs = self._blend_probabilities(raw_probs, market_probs, model_weight)

        # Apply Poisson model for football
        if self.sport == 'football':
            poisson_probs = self._calculate_poisson_probabilities(match_data, factors)
            # Blend weighted model with Poisson (60% Poisson, 40% weighted)
            blended_probs = self._blend_probabilities(raw_probs, poisson_probs, 0.6)
        else:
            blended_probs = raw_probs

        # Calibrate probabilities
        calibrated_probs = self._calibrate_probabilities(blended_probs)

        # Calculate confidence
        confidence = self._calculate_confidence(factors, calibrated_probs)

        # Generate betting recommendation
        recommendation = self._generate_recommendation(
            calibrated_probs,
            confidence,
            match_data.get('homeOdds', match_data.get('home_odds')),
            match_data.get('drawOdds', match_data.get('draw_odds')),
            match_data.get('awayOdds', match_data.get('away_odds'))
        )

        return {
            'homeTeam': home_team,
            'awayTeam': away_team,
            'homeWinProb': round(calibrated_probs['home'], 4),
            'drawProb': round(calibrated_probs['draw'], 4),
            'awayWinProb': round(calibrated_probs['away'], 4),
            'confidence': round(confidence, 4),
            'recommendation': recommendation,
            'factors': factors,
            'expectedGoals': {
                'home': round(factors.get('expectedGoals', {}).get('homeXg', 1.3), 2),
                'away': round(factors.get('expectedGoals', {}).get('awayXg', 1.3), 2)
            },
            'timestamp': datetime.now().isoformat()
        }

    def _calculate_all_factors(self, match_data: Dict) -> Dict:
        """Calculate all prediction factors (original 10 + new 6 contextual)"""
        from .context_builder import MatchContextBuilder
        from .models import FactorResult

        # Build match context for new factors
        context_builder = MatchContextBuilder(self.historical_data if hasattr(self, 'historical_data') else None)
        context = context_builder.build_context(match_data)

        factors = {}

        # 1. Expected Goals (xG) - 20%
        factors['expectedGoals'] = self._calculate_expected_goals(match_data)

        # 2. Advanced Stats - 15%
        factors['advancedStats'] = self._calculate_advanced_stats(match_data)

        # 3. Team Strength (Elo) - 12%
        factors['teamStrength'] = self._calculate_team_strength(match_data)

        # 4. Tactical Matchup - 12%
        factors['tacticalMatchup'] = self._analyze_tactical_matchup(match_data)

        # 5. Current Form - 10%
        factors['currentForm'] = self._calculate_current_form(match_data)

        # 6. Player Impact - 10%
        factors['playerImpact'] = self._calculate_player_impact(match_data)

        # 7. Rest & Fatigue - 8%
        factors['restAndFatigue'] = self._calculate_rest_fatigue(match_data)

        # 8. Motivation - 6%
        factors['motivation'] = self._calculate_motivation(match_data)

        # 9. Home Advantage - 5%
        factors['homeAdvantage'] = self._calculate_home_advantage(match_data)

        # 10. External Factors - 2%
        factors['externalFactors'] = self._calculate_external_factors(match_data)

        # 11. Team Quality Gap (V3) - anchors prediction to fundamental quality
        factors['teamQualityGap'] = self._calculate_team_quality_gap(match_data)

        # Contextual factors (Version 2.0)
        h2h_hist, h2h_anom = self._calculate_h2h_factors(match_data, context)
        factors['h2hHistorical'] = h2h_hist
        factors['h2hAnomaly'] = h2h_anom
        factors['possessionQuality'] = self._calculate_possession_quality(match_data, context)
        factors['managerMomentum'] = self._calculate_manager_momentum(match_data, context)
        factors['relegationMotivation'] = self._calculate_relegation_motivation(match_data, context)
        factors['counterAttackEfficiency'] = self._calculate_counter_attack_efficiency(match_data, context)
        factors['awayDrawFrequency'] = self._calculate_away_draw_frequency(match_data, context)

        return factors

    def _calculate_expected_goals(self, match_data: Dict) -> Dict:
        """Calculate expected goals factor"""
        home_xg = match_data.get('home_xg', match_data.get('homeXg', 1.3))
        away_xg = match_data.get('away_xg', match_data.get('awayXg', 1.3))

        # Normalize xG difference to -1 to 1 range
        xg_diff = home_xg - away_xg
        normalized_diff = np.tanh(xg_diff / 2)  # Smooth normalization

        return {
            'homeXg': float(home_xg),
            'awayXg': float(away_xg),
            'xgDifferential': float(xg_diff),
            'homeAdvantage': float(0.5 + normalized_diff * 0.3),
            'score': float(0.5 + normalized_diff * 0.5)
        }

    def _calculate_advanced_stats(self, match_data: Dict) -> Dict:
        """Calculate advanced statistics factor"""
        # PPDA (Passes Per Defensive Action) - lower is more aggressive
        home_ppda = match_data.get('home_ppda', 10.0)
        away_ppda = match_data.get('away_ppda', 10.0)

        # Possession
        home_poss = match_data.get('home_possession', 50)
        away_poss = match_data.get('away_possession', 50)

        # Shot accuracy
        home_shots = match_data.get('home_shots', 11)
        home_sot = match_data.get('home_shots_on_target', 4)
        away_shots = match_data.get('away_shots', 11)
        away_sot = match_data.get('away_shots_on_target', 4)

        home_accuracy = home_sot / max(home_shots, 1)
        away_accuracy = away_sot / max(away_shots, 1)

        # Combine metrics
        home_score = (
            (1 - min(home_ppda, 20) / 20) * 0.3 +  # Lower PPDA is better
            (home_poss / 100) * 0.3 +
            home_accuracy * 0.4
        )

        away_score = (
            (1 - min(away_ppda, 20) / 20) * 0.3 +
            (away_poss / 100) * 0.3 +
            away_accuracy * 0.4
        )

        return {
            'homePPDA': float(home_ppda),
            'awayPPDA': float(away_ppda),
            'homePossession': float(home_poss),
            'awayPossession': float(away_poss),
            'homeAccuracy': float(home_accuracy),
            'awayAccuracy': float(away_accuracy),
            'score': float(0.5 + (home_score - away_score) * 0.5)
        }

    def _calculate_team_strength(self, match_data: Dict) -> Dict:
        """Calculate team strength using Elo ratings"""
        home_team = match_data.get('homeTeam', match_data.get('home_team', 'Home'))
        away_team = match_data.get('awayTeam', match_data.get('away_team', 'Away'))

        # Get or initialize Elo ratings
        home_elo = match_data.get('home_elo', self.elo_ratings.get(home_team, self.config['base_elo']))
        away_elo = match_data.get('away_elo', self.elo_ratings.get(away_team, self.config['base_elo']))

        # Calculate expected score using Elo formula
        elo_diff = home_elo - away_elo
        expected_home = 1 / (1 + 10 ** (-elo_diff / 400))

        return {
            'homeElo': float(home_elo),
            'awayElo': float(away_elo),
            'eloDifferential': float(elo_diff),
            'expectedHome': float(expected_home),
            'score': float(expected_home)
        }

    def _analyze_tactical_matchup(self, match_data: Dict) -> Dict:
        """Analyze tactical matchup between teams"""
        # Formation compatibility (simplified)
        home_formation = match_data.get('homeFormation', '4-3-3')
        away_formation = match_data.get('awayFormation', '4-4-2')

        # Playing style
        home_style = match_data.get('homeStyle', 'balanced')
        away_style = match_data.get('awayStyle', 'balanced')

        # Style matchup matrix
        style_matchups = {
            ('attacking', 'defensive'): 0.45,
            ('attacking', 'attacking'): 0.50,
            ('defensive', 'attacking'): 0.55,
            ('defensive', 'defensive'): 0.50,
            ('balanced', 'balanced'): 0.50,
        }

        score = style_matchups.get((home_style, away_style), 0.52)

        return {
            'homeFormation': home_formation,
            'awayFormation': away_formation,
            'homeStyle': home_style,
            'awayStyle': away_style,
            'score': float(score)
        }

    def _calculate_current_form(self, match_data: Dict) -> Dict:
        """Calculate current form based on recent results"""
        home_form = match_data.get('home_form', 'WDWLD')
        away_form = match_data.get('away_form', 'WDWLD')

        def form_to_score(form_str: str) -> float:
            if not form_str:
                return 0.5
            points = {'W': 1.0, 'D': 0.5, 'L': 0.0}
            # Weight recent matches more heavily
            weights = [0.3, 0.25, 0.2, 0.15, 0.1]
            score = 0.0
            for i, result in enumerate(form_str[:5]):
                weight = weights[i] if i < len(weights) else 0.1
                score += points.get(result.upper(), 0.5) * weight
            return score

        home_score = form_to_score(str(home_form))
        away_score = form_to_score(str(away_form))

        return {
            'homeForm': str(home_form)[:5],
            'awayForm': str(away_form)[:5],
            'homeFormScore': float(home_score),
            'awayFormScore': float(away_score),
            'score': float(0.5 + (home_score - away_score) * 0.5)
        }

    def _calculate_player_impact(self, match_data: Dict) -> Dict:
        """Calculate impact of key players"""
        # Key player availability (0-1 scale)
        home_key_players = match_data.get('homeKeyPlayersAvailable', 1.0)
        away_key_players = match_data.get('awayKeyPlayersAvailable', 1.0)

        # Star player factor
        home_stars = match_data.get('homeStarRating', 3)  # 1-5 scale
        away_stars = match_data.get('awayStarRating', 3)

        home_impact = home_key_players * (home_stars / 5)
        away_impact = away_key_players * (away_stars / 5)

        return {
            'homeKeyPlayers': float(home_key_players),
            'awayKeyPlayers': float(away_key_players),
            'homeStars': int(home_stars),
            'awayStars': int(away_stars),
            'score': float(0.5 + (home_impact - away_impact) * 0.3)
        }

    def _calculate_rest_fatigue(self, match_data: Dict) -> Dict:
        """Calculate rest and fatigue impact"""
        home_rest = match_data.get('home_rest_days', match_data.get('homeRestDays', 7))
        away_rest = match_data.get('away_rest_days', match_data.get('awayRestDays', 7))

        # Games in last 7 days (congestion)
        home_congestion = match_data.get('home_games_last_7', match_data.get('homeGamesLast7', 1))
        away_congestion = match_data.get('away_games_last_7', match_data.get('awayGamesLast7', 1))

        def rest_score(days: int, games: int) -> float:
            # Optimal rest is 5-7 days
            rest_factor = 1.0
            if days < 3:
                rest_factor = 0.85
            elif days < 5:
                rest_factor = 0.95
            elif days > 10:
                rest_factor = 0.97  # Slight rust

            # Congestion penalty
            congestion_factor = max(0.8, 1 - (games - 1) * 0.1)

            return rest_factor * congestion_factor

        home_score = rest_score(home_rest, home_congestion)
        away_score = rest_score(away_rest, away_congestion)

        return {
            'homeRestDays': int(home_rest),
            'awayRestDays': int(away_rest),
            'homeCongestion': int(home_congestion),
            'awayCongestion': int(away_congestion),
            'score': float(0.5 + (home_score - away_score) * 0.5)
        }

    def _calculate_motivation(self, match_data: Dict) -> Dict:
        """Calculate motivation factors"""
        home_position = match_data.get('home_position', match_data.get('homePosition', 10))
        away_position = match_data.get('away_position', match_data.get('awayPosition', 10))

        competition = match_data.get('competition', 'League')
        is_derby = match_data.get('isDerby', False)
        is_cup_final = 'final' in competition.lower() if competition else False

        def motivation_score(position: int, is_home: bool) -> float:
            score = 0.5
            # Title race boost
            if position <= 4:
                score += 0.1
            # Relegation fight boost
            elif position >= 17:
                score += 0.08

            return min(1.0, score)

        home_motivation = motivation_score(home_position, True)
        away_motivation = motivation_score(away_position, False)

        # Derby and cup final adjustments
        if is_derby:
            home_motivation += 0.05
            away_motivation += 0.03
        if is_cup_final:
            home_motivation += 0.05
            away_motivation += 0.05

        return {
            'homePosition': int(home_position),
            'awayPosition': int(away_position),
            'isDerby': bool(is_derby),
            'isCupFinal': bool(is_cup_final),
            'score': float(0.5 + (home_motivation - away_motivation) * 0.5)
        }

    def _calculate_home_advantage(self, match_data: Dict) -> Dict:
        """Calculate home advantage, dampened when away team is significantly stronger."""
        venue = match_data.get('venue', 'Home Stadium')
        is_neutral = match_data.get('isNeutralVenue', False)

        # Base home advantage
        home_adv = self.config.get('home_advantage', 0.10)

        if is_neutral:
            home_adv = 0.02  # Slight familiarity advantage

        # Dampen home advantage when away team is much stronger
        home_pos = match_data.get('home_position', match_data.get('homePosition', 10))
        away_pos = match_data.get('away_position', match_data.get('awayPosition', 10))
        quality_gap = home_pos - away_pos  # Positive = away team is better (lower position)
        dampen_factor = 1.0
        if quality_gap > 8:
            # Significant quality gap: reduce home advantage by up to 70%
            dampen_factor = max(0.30, 1.0 - (quality_gap - 8) * 0.07)
            home_adv *= dampen_factor

        # Crowd factor (if available)
        expected_attendance_pct = match_data.get('expectedAttendancePct', 85)
        crowd_factor = 1 + (expected_attendance_pct - 50) / 500  # Small adjustment

        final_advantage = home_adv * crowd_factor

        return {
            'venue': str(venue),
            'isNeutral': bool(is_neutral),
            'baseAdvantage': float(self.config.get('home_advantage', 0.10)),
            'dampenedAdvantage': float(final_advantage),
            'qualityGapDampening': float(dampen_factor),
            'crowdFactor': float(crowd_factor),
            'score': float(0.5 + final_advantage)
        }

    def _calculate_external_factors(self, match_data: Dict) -> Dict:
        """Calculate external factors (weather, travel, etc.)"""
        weather = match_data.get('weather', 'clear')
        travel_distance = match_data.get('awayTravelDistance', 0)  # km

        # Weather impact
        weather_impacts = {
            'clear': 0.0,
            'rain': -0.02,
            'snow': -0.05,
            'wind': -0.03,
            'extreme_heat': -0.04
        }
        weather_impact = weather_impacts.get(weather.lower(), 0.0)

        # Travel fatigue (affects away team)
        travel_impact = 0.0
        if travel_distance > 500:
            travel_impact = 0.02  # Home team benefits
        if travel_distance > 1000:
            travel_impact = 0.04

        return {
            'weather': str(weather),
            'travelDistance': float(travel_distance),
            'weatherImpact': float(weather_impact),
            'travelImpact': float(travel_impact),
            'score': float(0.5 + travel_impact + weather_impact)
        }

    def _calculate_team_quality_gap(self, match_data: Dict) -> Dict:
        """
        Calculate fundamental team quality gap using Elo, position, and star ratings.

        This factor anchors predictions to the actual quality difference between teams,
        preventing the algorithm from picking massive underdogs (e.g. Sunderland over Liverpool).

        Score: >0.5 favors home, <0.5 favors away.
        Range: ~0.15 (massive away advantage) to ~0.85 (massive home advantage).
        """
        # Signal 1: Elo difference
        home_elo = match_data.get('home_elo', self.elo_ratings.get(
            match_data.get('homeTeam', match_data.get('home_team', '')), self.config['base_elo']))
        away_elo = match_data.get('away_elo', self.elo_ratings.get(
            match_data.get('awayTeam', match_data.get('away_team', '')), self.config['base_elo']))
        elo_diff = home_elo - away_elo
        elo_signal = 0.5 + np.tanh(elo_diff / 300) * 0.4

        # Signal 2: League position difference
        home_pos = match_data.get('home_position', match_data.get('homePosition', 10))
        away_pos = match_data.get('away_position', match_data.get('awayPosition', 10))
        pos_diff = away_pos - home_pos  # Positive = home team better positioned
        position_signal = 0.5 + np.tanh(pos_diff / 10) * 0.35

        # Signal 3: Star rating difference (squad quality proxy)
        home_stars = match_data.get('homeStarRating', 3)
        away_stars = match_data.get('awayStarRating', 3)
        star_signal = 0.5 + (home_stars - away_stars) * 0.1
        star_signal = max(0.2, min(0.8, star_signal))

        # Weighted combination (Elo is most reliable if available)
        has_elo = (match_data.get('home_elo') is not None or
                   match_data.get('homeTeam', '') in self.elo_ratings)
        if has_elo:
            quality_score = elo_signal * 0.50 + position_signal * 0.35 + star_signal * 0.15
        else:
            quality_score = position_signal * 0.60 + star_signal * 0.40

        gap_magnitude = abs(quality_score - 0.5) * 2

        return {
            'homeElo': float(home_elo),
            'awayElo': float(away_elo),
            'eloDiff': float(elo_diff),
            'positionDiff': int(pos_diff),
            'gapMagnitude': float(gap_magnitude),
            'qualityFavorite': 'home' if quality_score > 0.55 else ('away' if quality_score < 0.45 else 'neutral'),
            'score': float(quality_score)
        }

    # ========================================================================
    # CONTEXTUAL FACTORS (Version 2.0 - Enhanced Draw Prediction)
    # ========================================================================

    def _calculate_h2h_factors(self, match_data: Dict, context) -> tuple:
        """
        Calculate H2H historical and anomaly factors.

        Returns tuple: (historical_factor, anomaly_factor)
        """
        from .models import FactorResult

        if context.h2hRecord is None:
            return (
                FactorResult(name='h2hHistorical', value=0.5, weight=0.0, triggered=False,
                            confidence=0, explanation="No H2H data available"),
                FactorResult(name='h2hAnomaly', value=0.5, weight=0.0, triggered=False,
                            confidence=0, explanation="No H2H data for anomaly detection")
            )

        h2h = context.h2hRecord

        # Calculate base H2H score
        if h2h.total_matches == 0:
            h2h_score = 0.5
            confidence = 0
        else:
            home_win_rate = h2h.home_wins / h2h.total_matches
            h2h_score = 0.5 + (home_win_rate - 0.33) * 0.5
            confidence = min(h2h.total_matches * 10, 100)

        # Check anomaly
        weaker_team_is_home = context.homeLeaguePosition > context.awayLeaguePosition
        anomaly_detected = h2h.anomalyTriggered and h2h.weakerTeamUnbeatenStreak >= 3

        if anomaly_detected:
            anomaly_boost = 0.2 if weaker_team_is_home else -0.1
            return (
                FactorResult(name='h2hHistorical', value=h2h_score, weight=0.0, triggered=False,
                            confidence=confidence, explanation=f"Replaced by anomaly (streak: {h2h.weakerTeamUnbeatenStreak})"),
                FactorResult(name='h2hAnomaly', value=0.5 + anomaly_boost, weight=0.15, triggered=True,
                            confidence=90, explanation=f"Weaker team unbeaten in {h2h.weakerTeamUnbeatenStreak} H2H",
                            metadata={'streak': h2h.weakerTeamUnbeatenStreak, 'weaker_team_home': weaker_team_is_home})
            )
        else:
            return (
                FactorResult(name='h2hHistorical', value=h2h_score, weight=0.05, triggered=True,
                            confidence=confidence, explanation=f"H2H: {h2h.home_wins}W-{h2h.draws}D-{h2h.away_wins}L"),
                FactorResult(name='h2hAnomaly', value=0.5, weight=0.0, triggered=False,
                            confidence=50, explanation="No anomaly (streak < 3)")
            )

    def _calculate_possession_quality(self, match_data: Dict, context) -> object:
        """Calculate possession quality index (xG efficiency per possession)."""
        from .models import FactorResult
        import numpy as np

        home_xg = match_data.get('home_xg', match_data.get('homeXg', 1.3))
        away_xg = match_data.get('away_xg', match_data.get('awayXg', 1.3))
        home_poss = max(match_data.get('home_possession', 50) / 100, 0.3)
        away_poss = max(match_data.get('away_possession', 50) / 100, 0.3)

        home_pqi = (home_xg / home_poss) * 100
        away_pqi = (away_xg / away_poss) * 100

        pqi_diff = home_pqi - away_pqi
        normalized_score = 0.5 + np.tanh(pqi_diff / 100) * 0.3

        classify = lambda pqi: "excellent" if pqi > 300 else "good" if pqi > 200 else "poor"

        return FactorResult(
            name='possessionQuality', value=float(normalized_score), weight=0.12, triggered=True,
            confidence=80, explanation=f"Home PQI: {home_pqi:.1f} ({classify(home_pqi)}), Away: {away_pqi:.1f} ({classify(away_pqi)})",
            metadata={'home_pqi': float(home_pqi), 'away_pqi': float(away_pqi)}
        )

    def _calculate_manager_momentum(self, match_data: Dict, context) -> object:
        """Calculate manager momentum (new manager bounce with decay)."""
        from .models import FactorResult

        if context.homeManagerInfo is None or context.awayManagerInfo is None:
            return FactorResult(name='managerMomentum', value=0.5, weight=0.0, triggered=False,
                               confidence=0, explanation="No manager data")

        def calc_bounce(mgr):
            base = 0.08 if not mgr.isInterim else 0.056
            bounce = base * (0.85 ** mgr.gamesManaged)
            return bounce if bounce >= 0.01 else 0.0

        home_bounce = calc_bounce(context.homeManagerInfo)
        away_bounce = calc_bounce(context.awayManagerInfo)
        net_bounce = home_bounce - away_bounce

        if abs(net_bounce) < 0.01:
            return FactorResult(name='managerMomentum', value=0.5, weight=0.0, triggered=False,
                               confidence=50, explanation="No active bounce")

        value = 0.5 + net_bounce * 2
        return FactorResult(
            name='managerMomentum', value=float(value), weight=float(max(home_bounce, away_bounce)),
            triggered=True, confidence=80,
            explanation=f"Home: {home_bounce:.3f}, Away: {away_bounce:.3f}",
            metadata={'home_bounce': float(home_bounce), 'away_bounce': float(away_bounce)}
        )

    def _calculate_relegation_motivation(self, match_data: Dict, context) -> object:
        """Calculate relegation motivation factor."""
        from .models import FactorResult

        home_pos = context.homeLeaguePosition
        recent_form = context.homeRecentForm[-4:] if len(context.homeRecentForm) >= 4 else context.homeRecentForm
        recent_wins = sum(1 for r in recent_form if r == 'W')
        showing_fight = recent_wins >= 2

        if home_pos >= 18 and showing_fight:
            draw_boost, home_win_boost, tier = 0.08, 0.03, "critical"
        elif home_pos >= 17:
            draw_boost, home_win_boost, tier = 0.04, 0.02, "danger"
        else:
            return FactorResult(name='relegationMotivation', value=0.5, weight=0.0, triggered=False,
                               confidence=100, explanation=f"Not in relegation zone (pos {home_pos})")

        return FactorResult(
            name='relegationMotivation', value=float(0.5 + draw_boost + home_win_boost),
            weight=0.08, triggered=True, confidence=90,
            explanation=f"{tier} zone (pos {home_pos}), {recent_wins}/4 wins",
            metadata={'draw_boost': float(draw_boost), 'home_win_boost': float(home_win_boost), 'tier': tier}
        )

    def _calculate_counter_attack_efficiency(self, match_data: Dict, context) -> object:
        """Calculate counter-attack efficiency factor."""
        from .models import FactorResult

        # Use season stats if available, fall back to match-level possession
        if context.homeSeasonStats is not None and context.awaySeasonStats is not None:
            home_poss = context.homeSeasonStats.get('avgPossession', 50)
            away_poss = context.awaySeasonStats.get('avgPossession', 50)
            confidence_base = 75
        elif 'home_possession' in match_data or 'away_possession' in match_data:
            home_poss = match_data.get('home_possession', 50)
            away_poss = match_data.get('away_possession', 50)
            confidence_base = 60  # Lower confidence from single-match data
        else:
            return FactorResult(name='counterAttackEfficiency', value=0.5, weight=0.0, triggered=False,
                               confidence=0, explanation="No possession data")

        scenario = (home_poss < 45 and away_poss > 58) or (away_poss < 45 and home_poss > 58)

        if not scenario:
            return FactorResult(name='counterAttackEfficiency', value=0.5, weight=0.0, triggered=False,
                               confidence=confidence_base, explanation=f"No counter setup (H:{home_poss:.1f}% A:{away_poss:.1f}%)")

        if home_poss < 45:
            underdog_team, underdog_poss = "home", home_poss
            value = 0.5 + 0.05  # favor home underdog slightly
        else:
            underdog_team, underdog_poss = "away", away_poss
            value = 0.5 - 0.05  # favor away underdog slightly

        return FactorResult(
            name='counterAttackEfficiency', value=float(value), weight=0.06, triggered=True,
            confidence=confidence_base, explanation=f"{underdog_team} counter threat (poss: {underdog_poss:.1f}%)",
            metadata={'underdog_team': underdog_team, 'draw_boost': 0.06, 'underdog_boost': 0.04}
        )

    def _calculate_away_draw_frequency(self, match_data: Dict, context) -> object:
        """Calculate away draw frequency factor."""
        from .models import FactorResult

        # Use season stats if available, fall back to match-level data
        if context.awaySeasonStats is not None:
            away_draw_rate = context.awaySeasonStats.get('awayDrawRate', 0.25)
            total_away_games = context.awaySeasonStats.get('totalAwayGames', 0)
        elif 'away_draw_rate' in match_data:
            away_draw_rate = match_data['away_draw_rate']
            total_away_games = match_data.get('away_total_games', 10)
        else:
            return FactorResult(name='awayDrawFrequency', value=0.5, weight=0.0, triggered=False,
                               confidence=0, explanation="No away stats")

        if total_away_games < 5 or away_draw_rate <= 0.35:
            return FactorResult(name='awayDrawFrequency', value=0.5, weight=0.0, triggered=False,
                               confidence=20 if total_away_games < 5 else 80,
                               explanation=f"Normal rate: {away_draw_rate*100:.1f}%" if total_away_games >= 5 else "Insufficient games")

        boost = min((away_draw_rate - 0.25) * 0.5, 0.15)

        return FactorResult(
            name='awayDrawFrequency', value=float(0.5 + boost), weight=0.06, triggered=True,
            confidence=min(total_away_games * 5, 100),
            explanation=f"Draw-prone: {away_draw_rate*100:.1f}% (rate over {total_away_games} games)",
            metadata={'draw_boost': float(boost), 'away_draw_rate': float(away_draw_rate)}
        )

    def _calculate_draw_probability(self, weighted_score: float, factors: Dict,
                                      draw_boost_total: float = 0.0) -> float:
        """
        Calculate draw probability using multi-signal model.

        Replaces the old formula: 0.25 * (1 - |ws - 0.5| * 2) which capped at 25%.
        EPL average draw rate is ~26%, and evenly-matched defensive games can reach 35%.

        Returns:
            Draw probability in range [0.08, 0.40]
        """
        # Signal 1: Base league draw rate
        base_draw = 0.26

        # Signal 2: Quality gap (teams close in quality = higher draw probability)
        quality_gap = abs(weighted_score - 0.5)  # 0 = perfectly even, 0.5 = total mismatch
        # gap=0 → +0.06, gap=0.15 → +0.01, gap=0.3 → -0.04, gap=0.5 → -0.10
        quality_gap_adjustment = 0.06 - quality_gap * 0.32

        # Signal 3: Defensive profile from xG
        home_xg = factors.get('expectedGoals', {})
        if isinstance(home_xg, dict):
            h_xg = home_xg.get('homeXg', 1.3)
            a_xg = home_xg.get('awayXg', 1.3)
        else:
            h_xg, a_xg = 1.3, 1.3
        total_xg = h_xg + a_xg
        if total_xg < 2.0:
            defensive_boost = 0.05
        elif total_xg < 2.5:
            defensive_boost = 0.02
        else:
            defensive_boost = 0.0

        # Signal 4: xG closeness (similar xG = higher draw chance)
        xg_diff = abs(h_xg - a_xg)
        xg_closeness_adj = max(-0.04, 0.04 - xg_diff * 0.04)

        # Signal 5: Contextual factor draw boosts (already accumulated)
        contextual_boost = draw_boost_total

        # Combine signals
        draw_prob = (base_draw + quality_gap_adjustment + defensive_boost +
                     xg_closeness_adj + contextual_boost)

        # Clamp to realistic range
        return max(0.08, min(0.40, draw_prob))

    def _calculate_weighted_probabilities(self, factors: Dict) -> Dict:
        """Calculate probabilities from weighted factors with dynamic weight normalization"""
        from .models import FactorResult

        # Separate FactorResult objects from legacy dict factors
        active_factors = {}
        draw_boost_total = 0.0
        home_boost_total = 0.0
        away_boost_total = 0.0

        for factor_name, factor_data in factors.items():
            # Handle FactorResult objects (new contextual factors)
            if isinstance(factor_data, FactorResult):
                if factor_data.triggered and factor_data.weight > 0:
                    active_factors[factor_name] = {
                        'score': factor_data.value,
                        'weight': factor_data.weight,
                        'metadata': factor_data.metadata or {}
                    }
                    # Extract draw/home/away boosts from metadata
                    if 'draw_boost' in factor_data.metadata:
                        draw_boost_total += factor_data.metadata['draw_boost']
                    if 'home_win_boost' in factor_data.metadata:
                        home_boost_total += factor_data.metadata['home_win_boost']
            # Handle legacy dict factors (original 10 factors)
            elif isinstance(factor_data, dict) and 'score' in factor_data:
                config_weight = self.config['weights'].get(factor_name, 0.0)
                if config_weight > 0:
                    active_factors[factor_name] = {
                        'score': factor_data['score'],
                        'weight': config_weight,
                        'metadata': {}
                    }

        # Calculate dynamic normalized weights
        total_weight = sum(f['weight'] for f in active_factors.values())
        if total_weight == 0:
            # Fallback to neutral probabilities
            return {'home': 0.33, 'draw': 0.34, 'away': 0.33}

        # Calculate weighted score with normalized weights
        weighted_score = 0.0
        for factor_name, factor in active_factors.items():
            normalized_weight = factor['weight'] / total_weight
            weighted_score += factor['score'] * normalized_weight

        # Convert to base probabilities using enhanced draw model
        draw_prob = self._calculate_draw_probability(weighted_score, factors, draw_boost_total)
        home_prob = weighted_score * (1 - draw_prob) + home_boost_total
        away_prob = (1 - weighted_score) * (1 - draw_prob) - home_boost_total

        # Ensure probabilities stay within valid range
        home_prob = max(0.05, min(0.90, home_prob))
        draw_prob = max(0.05, min(0.90, draw_prob))
        away_prob = max(0.05, min(0.90, away_prob))

        # Final normalization to sum = 1.0
        total = home_prob + draw_prob + away_prob

        return {
            'home': home_prob / total,
            'draw': draw_prob / total,
            'away': away_prob / total
        }

    def _assess_data_quality(self, match_data: Dict) -> float:
        """
        Assess how much real data we have vs defaults.

        Returns:
            Float 0.0 (no real data, only defaults) to 1.0 (rich data available)
        """
        # Key data fields that indicate real data was provided
        data_fields = [
            ('home_xg', 'homeXg'),
            ('away_xg', 'awayXg'),
            ('home_elo', 'away_elo'),
            ('home_position', 'homePosition'),
            ('away_position', 'awayPosition'),
            ('home_form',),
            ('away_form',),
            ('home_possession', 'away_possession'),
            ('homeStarRating', 'awayStarRating'),
            ('homeStyle', 'awayStyle'),
        ]
        fields_present = 0
        for field_group in data_fields:
            for field in field_group:
                if field in match_data:
                    fields_present += 1
                    break
        return min(1.0, fields_present / len(data_fields))

    def _calculate_poisson_probabilities(self, match_data: Dict, factors: Dict) -> Dict:
        """Calculate probabilities using Poisson distribution"""
        # Get expected goals
        home_xg = factors.get('expectedGoals', {}).get('homeXg', 1.3)
        away_xg = factors.get('expectedGoals', {}).get('awayXg', 1.3)

        # Adjust based on team strength
        strength_factor = factors.get('teamStrength', {}).get('score', 0.5)
        home_xg *= (0.8 + strength_factor * 0.4)
        away_xg *= (1.2 - strength_factor * 0.4)

        # Cap xG to reasonable values
        home_xg = min(home_xg, self.config.get('max_goals_lambda', 4.0))
        away_xg = min(away_xg, self.config.get('max_goals_lambda', 4.0))

        # Calculate probabilities for each scoreline (0-0 to 5-5)
        home_win_prob = 0.0
        draw_prob = 0.0
        away_win_prob = 0.0

        for home_goals in range(6):
            for away_goals in range(6):
                prob = (poisson.pmf(home_goals, home_xg) *
                       poisson.pmf(away_goals, away_xg))

                if home_goals > away_goals:
                    home_win_prob += prob
                elif home_goals == away_goals:
                    draw_prob += prob
                else:
                    away_win_prob += prob

        # Normalize
        total = home_win_prob + draw_prob + away_win_prob

        return {
            'home': home_win_prob / total,
            'draw': draw_prob / total,
            'away': away_win_prob / total
        }

    def _blend_probabilities(self, probs1: Dict, probs2: Dict, weight2: float) -> Dict:
        """Blend two probability distributions"""
        weight1 = 1 - weight2
        return {
            'home': probs1['home'] * weight1 + probs2['home'] * weight2,
            'draw': probs1['draw'] * weight1 + probs2['draw'] * weight2,
            'away': probs1['away'] * weight1 + probs2['away'] * weight2
        }

    def _odds_to_probabilities(self, home_odds: float, draw_odds: float, away_odds: float) -> Dict:
        """
        Convert decimal odds to implied probabilities

        Args:
            home_odds: Decimal odds for home win
            draw_odds: Decimal odds for draw
            away_odds: Decimal odds for away win

        Returns:
            Dict with normalized probabilities
        """
        # Convert odds to implied probabilities
        home_implied = 1 / home_odds if home_odds > 0 else 0.33
        draw_implied = 1 / draw_odds if draw_odds > 0 else 0.33
        away_implied = 1 / away_odds if away_odds > 0 else 0.33

        # Calculate bookmaker margin (overround)
        total_implied = home_implied + draw_implied + away_implied
        margin = total_implied - 1.0

        # Remove margin to get fair probabilities (divide by total)
        fair_total = home_implied + draw_implied + away_implied

        return {
            'home': home_implied / fair_total,
            'draw': draw_implied / fair_total,
            'away': away_implied / fair_total
        }

    def _calibrate_probabilities(self, probs: Dict) -> Dict:
        """Apply Platt scaling calibration"""
        # Platt scaling: P_calibrated = 1 / (1 + exp(a * P + b))
        a = self.calibration_params['a']
        b = self.calibration_params['b']

        def calibrate(p: float) -> float:
            # Simple linear calibration for now
            return max(0.01, min(0.99, p * a + b * (p - 0.5)))

        calibrated = {
            'home': calibrate(probs['home']),
            'draw': calibrate(probs['draw']),
            'away': calibrate(probs['away'])
        }

        # Renormalize
        total = sum(calibrated.values())
        return {k: v / total for k, v in calibrated.items()}

    def _calculate_confidence(self, factors: Dict, probs: Dict) -> float:
        """Calculate prediction confidence"""
        # Base confidence from probability spread
        max_prob = max(probs.values())
        min_prob = min(probs.values())
        spread_confidence = (max_prob - min_prob) * 0.5

        # Factor consistency (how aligned are the factors)
        factor_scores = [f.get('score', 0.5) for f in factors.values() if isinstance(f, dict)]
        if factor_scores:
            factor_std = np.std(factor_scores)
            consistency_bonus = max(0, 0.2 - factor_std)
        else:
            consistency_bonus = 0

        # Data quality (do we have actual data vs defaults)
        data_quality = 0.8  # Assume decent data

        confidence = (spread_confidence + consistency_bonus) * data_quality
        return min(0.95, max(0.40, 0.5 + confidence))

    def _generate_recommendation(self, probs: Dict, confidence: float,
                                  home_odds: Optional[float] = None,
                                  draw_odds: Optional[float] = None,
                                  away_odds: Optional[float] = None) -> Dict:
        """Generate betting recommendation"""
        # Determine predicted outcome
        outcomes = [('Home Win', probs['home']), ('Draw', probs['draw']), ('Away Win', probs['away'])]
        predicted_outcome, predicted_prob = max(outcomes, key=lambda x: x[1])

        # Calculate expected values if odds available
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

        # Calculate stake using Kelly Criterion
        stake_pct = 0.0
        recommendation_type = 'No Bet'

        if best_bet and best_ev > 0:
            prob, odds = best_bet[1], best_bet[2]
            # Kelly: f = (bp - q) / b where b = odds - 1, p = probability, q = 1 - p
            b = odds - 1
            kelly = (b * prob - (1 - prob)) / b
            # Apply fractional Kelly and cap
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
                'away': round(ev_away * 100, 2) if ev_away else None
            }
        }

    def update_elo(self, home_team: str, away_team: str, home_goals: int, away_goals: int):
        """Update Elo ratings after a match"""
        home_elo = self.elo_ratings.get(home_team, self.config['base_elo'])
        away_elo = self.elo_ratings.get(away_team, self.config['base_elo'])

        # Expected scores
        expected_home = 1 / (1 + 10 ** ((away_elo - home_elo) / 400))
        expected_away = 1 - expected_home

        # Actual scores
        if home_goals > away_goals:
            actual_home, actual_away = 1, 0
        elif home_goals < away_goals:
            actual_home, actual_away = 0, 1
        else:
            actual_home = actual_away = 0.5

        # Update ratings
        k = self.config['k_factor']
        self.elo_ratings[home_team] = home_elo + k * (actual_home - expected_home)
        self.elo_ratings[away_team] = away_elo + k * (actual_away - expected_away)

    def set_calibration(self, a: float, b: float):
        """Set Platt scaling calibration parameters"""
        self.calibration_params = {'a': a, 'b': b}

    def get_config(self) -> Dict:
        """Get current algorithm configuration"""
        return self.config

    def save_state(self, filepath: str):
        """Save algorithm state (Elo ratings, calibration)"""
        state = {
            'elo_ratings': self.elo_ratings,
            'calibration_params': self.calibration_params,
            'sport': self.sport
        }
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)

    def load_state(self, filepath: str):
        """Load algorithm state"""
        if Path(filepath).exists():
            with open(filepath, 'r') as f:
                state = json.load(f)
                self.elo_ratings = state.get('elo_ratings', {})
                self.calibration_params = state.get('calibration_params', {'a': 1.0, 'b': 0.0})


# Convenience function for quick predictions
def predict_match(home_team: str, away_team: str, **kwargs) -> Dict:
    """Quick prediction function"""
    algo = ProfessionalBettingAlgorithm('football')
    match_data = {
        'homeTeam': home_team,
        'awayTeam': away_team,
        **kwargs
    }
    return algo.predict_match(match_data)
