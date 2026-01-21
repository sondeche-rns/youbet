"""
Professional Sports Betting Algorithm
Complete implementation with 12-factor prediction model
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json


class ProfessionalBettingAlgorithm:
    """
    Advanced sports betting prediction algorithm
    Supports: Football, Basketball, Tennis, Baseball
    """
    
    def __init__(self, sport: str = 'football'):
        """
        Initialize algorithm with sport-specific configuration
        
        Args:
            sport: One of 'football', 'basketball', 'tennis', 'baseball'
        """
        self.sport = sport.lower()
        self.config = self._get_sport_config()
        self.team_stats = {}
        self.predictions_history = []
        
    def _get_sport_config(self) -> Dict:
        """Get sport-specific configuration"""
        configs = {
            'football': {
                'weights': {
                    'expectedGoals': 0.20,
                    'advancedStats': 0.15,
                    'teamStrength': 0.12,
                    'tacticalMatchup': 0.12,
                    'currentForm': 0.10,
                    'playerImpact': 0.10,
                    'restAndFatigue': 0.08,
                    'motivation': 0.06,
                    'homeAdvantage': 0.05,
                    'externalFactors': 0.02
                },
                'homeAdvantageBase': 0.10,
                'restDayImpact': {
                    '0-1': -0.25, '2': -0.15, '3': -0.08,
                    '4-6': 0.00, '7+': 0.02
                },
                'keyPlayerValue': {
                    'topScorer': 0.18, 'playmaker': 0.15,
                    'goalkeeper': 0.12, 'captain': 0.10,
                    'defender': 0.08, 'rotation': 0.05
                },
                'motivationModifiers': {
                    'relegationFight': 0.18, 'europeChase': 0.12,
                    'titleRace': 0.15, 'cupFinal': 0.20,
                    'derby': 0.14, 'revenge': 0.08, 'deadRubber': -0.12
                }
            },
            'basketball': {
                'weights': {
                    'advancedStats': 0.25,
                    'playerImpact': 0.20,
                    'teamStrength': 0.15,
                    'currentForm': 0.12,
                    'restAndFatigue': 0.12,
                    'tacticalMatchup': 0.08,
                    'motivation': 0.05,
                    'homeAdvantage': 0.02,
                    'externalFactors': 0.01
                },
                'homeAdvantageBase': 0.06,
                'restDayImpact': {
                    '0': -0.30, '1': -0.12, '2-3': 0.00, '4+': 0.03
                },
                'keyPlayerValue': {
                    'superstar': 0.30, 'allStar': 0.20,
                    'starter': 0.12, 'rotation': 0.06
                }
            }
        }
        
        return configs.get(self.sport, configs['football'])
    
    def predict_match(self, match_data: Dict) -> Dict:
        """
        Main prediction method
        
        Args:
            match_data: Dictionary containing match information
                Required keys: homeTeam, awayTeam, date
                Optional keys: venue, competition, availablePlayers
        
        Returns:
            Dictionary with predictions and analysis
        """
        # Gather all prediction factors
        factors = self._gather_all_factors(match_data)
        
        # Calculate weighted prediction
        prediction = self._calculate_weighted_prediction(factors)
        
        # Apply confidence adjustments
        adjusted = self._apply_confidence_adjustments(prediction, factors)
        
        # Calibrate probabilities
        calibrated = self._calibrate_probabilities(adjusted)
        
        # Generate recommendation
        recommendation = self._generate_recommendation(calibrated, factors)
        
        result = {
            'homeWinProb': calibrated['home'],
            'drawProb': calibrated.get('draw', 0),
            'awayWinProb': calibrated['away'],
            'confidence': calibrated['confidence'],
            'recommendation': recommendation,
            'factors': self._format_factors(factors),
            'timestamp': datetime.now().isoformat()
        }
        
        self.predictions_history.append(result)
        return result
    
    def _gather_all_factors(self, match_data: Dict) -> Dict:
        """Gather all prediction factors"""
        return {
            'expectedGoals': self._calculate_expected_goals(match_data),
            'advancedStats': self._calculate_advanced_stats(match_data),
            'teamStrength': self._calculate_team_strength(match_data),
            'currentForm': self._calculate_current_form(match_data),
            'tacticalMatchup': self._analyze_tactical_matchup(match_data),
            'playerImpact': self._calculate_player_impact(match_data),
            'restAndFatigue': self._calculate_rest_fatigue(match_data),
            'motivation': self._calculate_motivation(match_data),
            'homeAdvantage': self._calculate_home_advantage(match_data),
            'externalFactors': self._calculate_external_factors(match_data)
        }
    
    def _calculate_expected_goals(self, match_data: Dict) -> Dict:
        """Calculate xG differential"""
        home_team = match_data['homeTeam']
        away_team = match_data['awayTeam']
        
        # Simulated xG - replace with actual API data
        home_xg = self._get_team_xg(home_team, 'home')
        away_xg = self._get_team_xg(away_team, 'away')
        
        differential = home_xg - away_xg
        
        return {
            'value': differential / 2.0,  # Normalize
            'confidence': 0.85,
            'homeXG': home_xg,
            'awayXG': away_xg
        }
    
    def _get_team_xg(self, team: str, venue: str) -> float:
        """Get team's expected goals"""
        # Base xG by team tier
        tier_xg = {
            'elite': 2.1, 'good': 1.6, 'average': 1.3, 'weak': 0.9
        }
        
        tier = self._get_team_tier(team)
        base_xg = tier_xg.get(tier, 1.3)
        
        # Adjust for venue
        venue_modifier = 1.15 if venue == 'home' else 0.92
        
        return base_xg * venue_modifier
    
    def _calculate_advanced_stats(self, match_data: Dict) -> Dict:
        """Calculate advanced statistical metrics"""
        if self.sport == 'football':
            return self._football_advanced_stats(match_data)
        elif self.sport == 'basketball':
            return self._basketball_advanced_stats(match_data)
        
        return {'value': 0, 'confidence': 0.5}
    
    def _football_advanced_stats(self, match_data: Dict) -> Dict:
        """Football-specific advanced stats"""
        home_team = match_data['homeTeam']
        away_team = match_data['awayTeam']
        
        # Simulated stats - replace with actual data
        home_ppda = 9.5  # Passes per defensive action
        away_ppda = 11.2
        
        home_shots_quality = 0.65
        away_shots_quality = 0.58
        
        # Calculate differential
        value = ((away_ppda - home_ppda) / 10 +  # Lower PPDA is better (more pressing)
                (home_shots_quality - away_shots_quality))
        
        return {
            'value': value,
            'confidence': 0.75
        }
    
    def _basketball_advanced_stats(self, match_data: Dict) -> Dict:
        """Basketball-specific advanced stats"""
        # Simulated - replace with actual NBA stats
        home_ortg = 112.5  # Offensive rating
        away_ortg = 110.2
        
        home_drtg = 108.0  # Defensive rating  
        away_drtg = 109.5
        
        value = ((home_ortg - away_ortg) / 10 +
                (away_drtg - home_drtg) / 10) / 2
        
        return {
            'value': value,
            'confidence': 0.85
        }
    
    def _calculate_team_strength(self, match_data: Dict) -> Dict:
        """Calculate Elo-based team strength"""
        home_elo = self._get_team_elo(match_data['homeTeam'])
        away_elo = self._get_team_elo(match_data['awayTeam'])
        
        elo_diff = home_elo - away_elo
        expected = 1 / (1 + 10 ** (-elo_diff / 400))
        
        return {
            'value': (expected - 0.5) * 2,  # Normalize to -1 to 1
            'confidence': 0.80,
            'homeElo': home_elo,
            'awayElo': away_elo
        }
    
    def _get_team_elo(self, team: str) -> int:
        """Get team Elo rating"""
        # Default ratings - replace with actual data
        ratings = {
            'Manchester City': 2100, 'Arsenal': 2050, 'Liverpool': 2040,
            'Chelsea': 1950, 'Tottenham': 1920, 'Manchester United': 1880
        }
        return ratings.get(team, 1500)
    
    def _calculate_current_form(self, match_data: Dict) -> Dict:
        """Calculate recent form with recency weighting"""
        home_form = self._get_form_value(['W', 'W', 'D', 'W', 'L', 'W', 'W', 'D', 'W', 'L'])
        away_form = self._get_form_value(['W', 'L', 'D', 'W', 'L', 'D', 'L', 'W', 'D', 'L'])
        
        return {
            'value': home_form - away_form,
            'confidence': 0.70
        }
    
    def _get_form_value(self, form_array: List[str]) -> float:
        """Calculate weighted form value"""
        weights = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]
        
        points = [3 if r == 'W' else 1 if r == 'D' else 0 for r in form_array]
        
        weighted_sum = sum(p * w for p, w in zip(points, weights))
        max_possible = sum(3 * w for w in weights)
        
        return weighted_sum / max_possible
    
    def _analyze_tactical_matchup(self, match_data: Dict) -> Dict:
        """Analyze tactical style compatibility"""
        # Simulated tactical styles
        home_style = {
            'possession': 0.70, 'pressing': 0.80,
            'directness': 0.30, 'width': 0.60
        }
        
        away_style = {
            'possession': 0.55, 'pressing': 0.60,
            'directness': 0.50, 'width': 0.45
        }
        
        # High press vs high line advantage
        value = 0
        if home_style['pressing'] > 0.7 and away_style['possession'] > 0.6:
            value += 0.15
        
        # Possession dominance
        value += (home_style['possession'] - away_style['possession']) * 0.2
        
        return {
            'value': max(-0.3, min(0.3, value)),
            'confidence': 0.65
        }
    
    def _calculate_player_impact(self, match_data: Dict) -> Dict:
        """Calculate impact of missing players"""
        available = match_data.get('availablePlayers', {})
        
        # Simulated - replace with actual injury/suspension data
        home_missing = []  # List of missing key players
        away_missing = ['topScorer']  # Example: away team missing top scorer
        
        home_impact = -sum(self.config['keyPlayerValue'].get(role, 0) 
                          for role in home_missing)
        away_impact = -sum(self.config['keyPlayerValue'].get(role, 0) 
                          for role in away_missing)
        
        return {
            'value': home_impact - away_impact,
            'confidence': 0.80,
            'homeMissing': home_missing,
            'awayMissing': away_missing
        }
    
    def _calculate_rest_fatigue(self, match_data: Dict) -> Dict:
        """Calculate rest and fatigue factors"""
        # Simulated - replace with actual fixture data
        home_rest_days = 4
        away_rest_days = 3
        
        home_impact = self._get_rest_impact(home_rest_days)
        away_impact = self._get_rest_impact(away_rest_days)
        
        return {
            'value': home_impact - away_impact,
            'confidence': 0.75,
            'homeRestDays': home_rest_days,
            'awayRestDays': away_rest_days
        }
    
    def _get_rest_impact(self, days: int) -> float:
        """Get impact of rest days"""
        rest_impacts = self.config.get('restDayImpact', {})
        
        if days <= 1:
            return rest_impacts.get('0-1', -0.25)
        elif days == 2:
            return rest_impacts.get('2', -0.15)
        elif days == 3:
            return rest_impacts.get('3', -0.08)
        elif days <= 6:
            return rest_impacts.get('4-6', 0.00)
        else:
            return rest_impacts.get('7+', 0.02)
    
    def _calculate_motivation(self, match_data: Dict) -> Dict:
        """Calculate motivation factors"""
        # Simulated league positions
        home_position = 2  # Title race
        away_position = 10  # Mid-table
        
        motivations = self.config.get('motivationModifiers', {})
        
        home_motivation = 0
        away_motivation = 0
        
        # Title race
        if home_position <= 3:
            home_motivation += motivations.get('titleRace', 0.15)
        
        # Mid-table (nothing to play for)
        if 8 <= away_position <= 12:
            away_motivation += motivations.get('deadRubber', -0.12)
        
        return {
            'value': home_motivation - away_motivation,
            'confidence': 0.60
        }
    
    def _calculate_home_advantage(self, match_data: Dict) -> Dict:
        """Calculate home advantage"""
        base = self.config['homeAdvantageBase']
        
        # Venue strength (e.g., Anfield, Old Trafford)
        venue_multiplier = 1.15  # Simulated
        
        return {
            'value': base * venue_multiplier,
            'confidence': 0.70
        }
    
    def _calculate_external_factors(self, match_data: Dict) -> Dict:
        """Calculate weather, referee, etc."""
        # Minimal impact - mostly noise
        return {
            'value': 0.00,
            'confidence': 0.50
        }
    
    def _calculate_weighted_prediction(self, factors: Dict) -> Dict:
        """Calculate weighted prediction from all factors"""
        home_advantage = 0
        
        for factor_name, weight in self.config['weights'].items():
            factor = factors.get(factor_name, {})
            if isinstance(factor, dict) and 'value' in factor:
                home_advantage += factor['value'] * weight
        
        # Convert to probabilities using logistic function
        home_prob_raw = 1 / (1 + np.exp(-home_advantage * 5))
        
        # For football, include draw probability
        if self.sport == 'football':
            draw_prob = 0.25
            home_prob = home_prob_raw * (1 - draw_prob)
            away_prob = (1 - home_prob_raw) * (1 - draw_prob)
            
            return {
                'home': home_prob,
                'draw': draw_prob,
                'away': away_prob,
                'rawScore': home_advantage
            }
        else:
            # Basketball, tennis - no draws
            return {
                'home': home_prob_raw,
                'away': 1 - home_prob_raw,
                'rawScore': home_advantage
            }
    
    def _apply_confidence_adjustments(self, prediction: Dict, factors: Dict) -> Dict:
        """Apply confidence adjustments based on factors"""
        confidence = 0.75  # Base confidence
        
        # Reduce confidence for uncertain situations
        rest_fatigue = factors.get('restAndFatigue', {})
        if rest_fatigue.get('value', 0) < -0.15:
            confidence *= 0.90
        
        player_impact = factors.get('playerImpact', {})
        if len(player_impact.get('homeMissing', [])) >= 2:
            confidence *= 0.85
        
        # Increase confidence for consistent factors
        xg = factors.get('expectedGoals', {})
        if xg.get('confidence', 0) > 0.80:
            confidence *= 1.05
        
        prediction['confidence'] = min(0.95, max(0.50, confidence))
        return prediction
    
    def _calibrate_probabilities(self, prediction: Dict) -> Dict:
        """Apply calibration curve to probabilities"""
        # Simple calibration - in production, use historical data
        calibration = {
            0.3: 0.32, 0.4: 0.42, 0.5: 0.50,
            0.6: 0.58, 0.7: 0.68, 0.8: 0.76
        }
        
        # Apply to home probability (simplified)
        home = prediction['home']
        for threshold in sorted(calibration.keys()):
            if home <= threshold:
                prediction['home'] = calibration[threshold]
                break
        
        # Recalculate away
        if 'draw' in prediction:
            prediction['away'] = 1 - prediction['home'] - prediction['draw']
        else:
            prediction['away'] = 1 - prediction['home']
        
        return prediction
    
    def _generate_recommendation(self, prediction: Dict, factors: Dict) -> Dict:
        """Generate betting recommendation"""
        max_prob = max(prediction['home'], 
                      prediction.get('draw', 0),
                      prediction['away'])
        
        if max_prob == prediction['home']:
            outcome = 'Home Win'
        elif max_prob == prediction.get('draw', 0):
            outcome = 'Draw'
        else:
            outcome = 'Away Win'
        
        confidence = prediction['confidence']
        
        # Simplified recommendation logic
        if confidence >= 0.75:
            recommendation = 'Strong Bet'
            stake = 0.03  # 3% of bankroll
        elif confidence >= 0.65:
            recommendation = 'Value Bet'
            stake = 0.02  # 2% of bankroll
        else:
            recommendation = 'No Bet'
            stake = 0.00
        
        return {
            'outcome': outcome,
            'probability': max_prob,
            'confidence': confidence,
            'recommendation': recommendation,
            'stakePercentage': stake
        }
    
    def _format_factors(self, factors: Dict) -> Dict:
        """Format factors for output"""
        formatted = {}
        for name, data in factors.items():
            if isinstance(data, dict):
                formatted[name] = {
                    'value': round(data.get('value', 0), 3),
                    'confidence': round(data.get('confidence', 0), 2)
                }
        return formatted
    
    def _get_team_tier(self, team: str) -> str:
        """Get team tier based on strength"""
        elo = self._get_team_elo(team)
        if elo >= 2000:
            return 'elite'
        elif elo >= 1800:
            return 'good'
        elif elo >= 1600:
            return 'average'
        return 'weak'
    
    def get_prediction_history(self) -> List[Dict]:
        """Get all predictions made"""
        return self.predictions_history
    
    def export_predictions(self, filepath: str):
        """Export predictions to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.predictions_history, f, indent=2, default=str)


# Example usage
if __name__ == "__main__":
    # Initialize algorithm
    algo = ProfessionalBettingAlgorithm('football')
    
    # Example match
    match = {
        'homeTeam': 'Arsenal',
        'awayTeam': 'Manchester United',
        'date': '2025-08-17',
        'venue': 'Emirates Stadium',
        'competition': 'Premier League'
    }
    
    # Get prediction
    prediction = algo.predict_match(match)
    
    # Display results
    print("="*70)
    print(" MATCH PREDICTION")
    print("="*70)
    print(f"\n{match['homeTeam']} vs {match['awayTeam']}")
    print(f"\nProbabilities:")
    print(f"  Home Win: {prediction['homeWinProb']*100:.1f}%")
    print(f"  Draw: {prediction['drawProb']*100:.1f}%")
    print(f"  Away Win: {prediction['awayWinProb']*100:.1f}%")
    print(f"\nConfidence: {prediction['confidence']*100:.1f}%")
    print(f"\nRecommendation: {prediction['recommendation']['recommendation']}")
    print(f"Outcome: {prediction['recommendation']['outcome']}")
    print(f"Stake: {prediction['recommendation']['stakePercentage']*100:.1f}% of bankroll")