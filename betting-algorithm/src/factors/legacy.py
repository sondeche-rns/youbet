"""
Legacy factor calculators — the original 10 factors plus teamQualityGap.

Each always triggers and uses base_weight directly from config.
Factor-specific data is stored in FactorResult.metadata for downstream use
(Poisson model, draw probability, serialization).
"""

import numpy as np
from typing import Dict, Optional

from ..models import FactorCalculator, FactorResult, MatchContext


class ExpectedGoalsCalculator(FactorCalculator):
    def __init__(self, base_weight: float):
        super().__init__('expectedGoals', base_weight)

    def calculate(self, match_data: Dict, context: MatchContext) -> FactorResult:
        home_xg = float(match_data.get('home_xg', match_data.get('homeXg', 1.3)))
        away_xg = float(match_data.get('away_xg', match_data.get('awayXg', 1.3)))
        xg_diff = home_xg - away_xg
        normalized_diff = float(np.tanh(xg_diff / 2))
        return FactorResult(
            name='expectedGoals',
            value=float(0.5 + normalized_diff * 0.5),
            weight=self.base_weight,
            triggered=True,
            confidence=80,
            explanation=f"xG: Home {home_xg:.2f} vs Away {away_xg:.2f}",
            metadata={
                'homeXg': home_xg,
                'awayXg': away_xg,
                'xgDifferential': float(xg_diff),
                'homeAdvantage': float(0.5 + normalized_diff * 0.3),
            }
        )


class AdvancedStatsCalculator(FactorCalculator):
    def __init__(self, base_weight: float):
        super().__init__('advancedStats', base_weight)

    def calculate(self, match_data: Dict, context: MatchContext) -> FactorResult:
        home_ppda = float(match_data.get('home_ppda', 10.0))
        away_ppda = float(match_data.get('away_ppda', 10.0))
        home_poss = float(match_data.get('home_possession', 50))
        away_poss = float(match_data.get('away_possession', 50))
        home_shots = int(match_data.get('home_shots', 11))
        home_sot = int(match_data.get('home_shots_on_target', 4))
        away_shots = int(match_data.get('away_shots', 11))
        away_sot = int(match_data.get('away_shots_on_target', 4))

        home_accuracy = home_sot / max(home_shots, 1)
        away_accuracy = away_sot / max(away_shots, 1)

        home_score = (
            (1 - min(home_ppda, 20) / 20) * 0.3 +
            (home_poss / 100) * 0.3 +
            home_accuracy * 0.4
        )
        away_score = (
            (1 - min(away_ppda, 20) / 20) * 0.3 +
            (away_poss / 100) * 0.3 +
            away_accuracy * 0.4
        )

        return FactorResult(
            name='advancedStats',
            value=float(0.5 + (home_score - away_score) * 0.5),
            weight=self.base_weight,
            triggered=True,
            confidence=70,
            explanation=f"PPDA H:{home_ppda:.1f}/A:{away_ppda:.1f}  Poss H:{home_poss:.0f}%/A:{away_poss:.0f}%",
            metadata={
                'homePPDA': home_ppda,
                'awayPPDA': away_ppda,
                'homePossession': home_poss,
                'awayPossession': away_poss,
                'homeAccuracy': float(home_accuracy),
                'awayAccuracy': float(away_accuracy),
            }
        )


class TeamStrengthCalculator(FactorCalculator):
    def __init__(self, base_weight: float, base_elo: int = 1500, elo_ratings: Optional[Dict] = None):
        super().__init__('teamStrength', base_weight)
        self.base_elo = base_elo
        self.elo_ratings = elo_ratings if elo_ratings is not None else {}

    def calculate(self, match_data: Dict, context: MatchContext) -> FactorResult:
        home_team = match_data.get('homeTeam', match_data.get('home_team', 'Home'))
        away_team = match_data.get('awayTeam', match_data.get('away_team', 'Away'))
        home_elo = float(match_data.get('home_elo', self.elo_ratings.get(home_team, self.base_elo)))
        away_elo = float(match_data.get('away_elo', self.elo_ratings.get(away_team, self.base_elo)))
        elo_diff = home_elo - away_elo
        expected_home = float(1 / (1 + 10 ** (-elo_diff / 400)))
        return FactorResult(
            name='teamStrength',
            value=expected_home,
            weight=self.base_weight,
            triggered=True,
            confidence=80,
            explanation=f"Elo H:{home_elo:.0f} vs A:{away_elo:.0f} (diff: {elo_diff:+.0f})",
            metadata={
                'homeElo': home_elo,
                'awayElo': away_elo,
                'eloDifferential': float(elo_diff),
                'expectedHome': expected_home,
            }
        )


class TacticalMatchupCalculator(FactorCalculator):
    _STYLE_MATCHUPS = {
        ('attacking', 'defensive'): 0.45,
        ('attacking', 'attacking'): 0.50,
        ('defensive', 'attacking'): 0.55,
        ('defensive', 'defensive'): 0.50,
        ('balanced', 'balanced'): 0.50,
    }

    def __init__(self, base_weight: float):
        super().__init__('tacticalMatchup', base_weight)

    def calculate(self, match_data: Dict, context: MatchContext) -> FactorResult:
        home_formation = match_data.get('homeFormation', '4-3-3')
        away_formation = match_data.get('awayFormation', '4-4-2')
        home_style = match_data.get('homeStyle', 'balanced')
        away_style = match_data.get('awayStyle', 'balanced')
        score = float(self._STYLE_MATCHUPS.get((home_style, away_style), 0.52))
        return FactorResult(
            name='tacticalMatchup',
            value=score,
            weight=self.base_weight,
            triggered=True,
            confidence=60,
            explanation=f"{home_formation} vs {away_formation} ({home_style} vs {away_style})",
            metadata={
                'homeFormation': home_formation,
                'awayFormation': away_formation,
                'homeStyle': home_style,
                'awayStyle': away_style,
            }
        )


class CurrentFormCalculator(FactorCalculator):
    def __init__(self, base_weight: float):
        super().__init__('currentForm', base_weight)

    @staticmethod
    def _form_to_score(form_str: str) -> float:
        if not form_str:
            return 0.5
        points = {'W': 1.0, 'D': 0.5, 'L': 0.0}
        weights = [0.3, 0.25, 0.2, 0.15, 0.1]
        score = 0.0
        for i, result in enumerate(str(form_str)[:5]):
            w = weights[i] if i < len(weights) else 0.1
            score += points.get(result.upper(), 0.5) * w
        return score

    def calculate(self, match_data: Dict, context: MatchContext) -> FactorResult:
        home_form = match_data.get('home_form', 'WDWLD')
        away_form = match_data.get('away_form', 'WDWLD')
        home_score = self._form_to_score(home_form)
        away_score = self._form_to_score(away_form)
        return FactorResult(
            name='currentForm',
            value=float(0.5 + (home_score - away_score) * 0.5),
            weight=self.base_weight,
            triggered=True,
            confidence=75,
            explanation=f"Form H:{str(home_form)[:5]} ({home_score:.2f}) vs A:{str(away_form)[:5]} ({away_score:.2f})",
            metadata={
                'homeForm': str(home_form)[:5],
                'awayForm': str(away_form)[:5],
                'homeFormScore': float(home_score),
                'awayFormScore': float(away_score),
            }
        )


class PlayerImpactCalculator(FactorCalculator):
    def __init__(self, base_weight: float):
        super().__init__('playerImpact', base_weight)

    def calculate(self, match_data: Dict, context: MatchContext) -> FactorResult:
        home_kp = float(match_data.get('homeKeyPlayersAvailable', 1.0))
        away_kp = float(match_data.get('awayKeyPlayersAvailable', 1.0))
        home_stars = int(match_data.get('homeStarRating', 3))
        away_stars = int(match_data.get('awayStarRating', 3))
        home_impact = home_kp * (home_stars / 5)
        away_impact = away_kp * (away_stars / 5)
        return FactorResult(
            name='playerImpact',
            value=float(0.5 + (home_impact - away_impact) * 0.3),
            weight=self.base_weight,
            triggered=True,
            confidence=65,
            explanation=f"Stars H:{home_stars}/5 ({home_kp:.0%}) vs A:{away_stars}/5 ({away_kp:.0%})",
            metadata={
                'homeKeyPlayers': home_kp,
                'awayKeyPlayers': away_kp,
                'homeStars': home_stars,
                'awayStars': away_stars,
            }
        )


class RestFatigueCalculator(FactorCalculator):
    def __init__(self, base_weight: float):
        super().__init__('restAndFatigue', base_weight)

    @staticmethod
    def _rest_score(days: int, games: int) -> float:
        rest_factor = 1.0
        if days < 3:
            rest_factor = 0.85
        elif days < 5:
            rest_factor = 0.95
        elif days > 10:
            rest_factor = 0.97
        congestion_factor = max(0.8, 1 - (games - 1) * 0.1)
        return rest_factor * congestion_factor

    def calculate(self, match_data: Dict, context: MatchContext) -> FactorResult:
        home_rest = int(match_data.get('home_rest_days', match_data.get('homeRestDays', 7)))
        away_rest = int(match_data.get('away_rest_days', match_data.get('awayRestDays', 7)))
        home_cong = int(match_data.get('home_games_last_7', match_data.get('homeGamesLast7', 1)))
        away_cong = int(match_data.get('away_games_last_7', match_data.get('awayGamesLast7', 1)))
        home_score = self._rest_score(home_rest, home_cong)
        away_score = self._rest_score(away_rest, away_cong)
        return FactorResult(
            name='restAndFatigue',
            value=float(0.5 + (home_score - away_score) * 0.5),
            weight=self.base_weight,
            triggered=True,
            confidence=70,
            explanation=f"Rest H:{home_rest}d vs A:{away_rest}d",
            metadata={
                'homeRestDays': home_rest,
                'awayRestDays': away_rest,
                'homeCongestion': home_cong,
                'awayCongestion': away_cong,
            }
        )


class MotivationCalculator(FactorCalculator):
    def __init__(self, base_weight: float):
        super().__init__('motivation', base_weight)

    @staticmethod
    def _motivation_score(position: int) -> float:
        score = 0.5
        if position <= 4:
            score += 0.1
        elif position >= 17:
            score += 0.08
        return min(1.0, score)

    def calculate(self, match_data: Dict, context: MatchContext) -> FactorResult:
        home_pos = int(match_data.get('home_position', match_data.get('homePosition', 10)))
        away_pos = int(match_data.get('away_position', match_data.get('awayPosition', 10)))
        competition = match_data.get('competition', 'League')
        is_derby = bool(match_data.get('isDerby', False))
        is_cup_final = 'final' in competition.lower() if competition else False
        home_m = self._motivation_score(home_pos)
        away_m = self._motivation_score(away_pos)
        if is_derby:
            home_m += 0.05
            away_m += 0.03
        if is_cup_final:
            home_m += 0.05
            away_m += 0.05
        return FactorResult(
            name='motivation',
            value=float(0.5 + (home_m - away_m) * 0.5),
            weight=self.base_weight,
            triggered=True,
            confidence=65,
            explanation=f"Pos H:{home_pos} vs A:{away_pos}" + (" DERBY" if is_derby else ""),
            metadata={
                'homePosition': home_pos,
                'awayPosition': away_pos,
                'isDerby': is_derby,
                'isCupFinal': is_cup_final,
            }
        )


class HomeAdvantageCalculator(FactorCalculator):
    def __init__(self, base_weight: float, home_advantage: float = 0.10):
        super().__init__('homeAdvantage', base_weight)
        self.home_advantage = home_advantage

    def calculate(self, match_data: Dict, context: MatchContext) -> FactorResult:
        venue = match_data.get('venue', 'Home Stadium')
        is_neutral = bool(match_data.get('isNeutralVenue', False))
        home_adv = 0.02 if is_neutral else self.home_advantage
        home_pos = int(match_data.get('home_position', match_data.get('homePosition', 10)))
        away_pos = int(match_data.get('away_position', match_data.get('awayPosition', 10)))
        quality_gap = home_pos - away_pos
        dampen_factor = 1.0
        if quality_gap > 8:
            dampen_factor = max(0.30, 1.0 - (quality_gap - 8) * 0.07)
            home_adv *= dampen_factor
        crowd_factor = 1 + (float(match_data.get('expectedAttendancePct', 85)) - 50) / 500
        final_advantage = home_adv * crowd_factor
        return FactorResult(
            name='homeAdvantage',
            value=float(0.5 + final_advantage),
            weight=self.base_weight,
            triggered=True,
            confidence=75,
            explanation=f"Advantage: {final_advantage:.3f} (dampen: {dampen_factor:.2f})",
            metadata={
                'venue': str(venue),
                'isNeutral': is_neutral,
                'baseAdvantage': self.home_advantage,
                'dampenedAdvantage': float(final_advantage),
                'qualityGapDampening': float(dampen_factor),
                'crowdFactor': float(crowd_factor),
            }
        )


class ExternalFactorsCalculator(FactorCalculator):
    _WEATHER_IMPACTS = {
        'clear': 0.0, 'rain': -0.02, 'snow': -0.05, 'wind': -0.03, 'extreme_heat': -0.04,
    }

    def __init__(self, base_weight: float):
        super().__init__('externalFactors', base_weight)

    def calculate(self, match_data: Dict, context: MatchContext) -> FactorResult:
        weather = match_data.get('weather', 'clear')
        travel_distance = float(match_data.get('awayTravelDistance', 0))
        weather_impact = float(self._WEATHER_IMPACTS.get(weather.lower(), 0.0))
        travel_impact = 0.04 if travel_distance > 1000 else (0.02 if travel_distance > 500 else 0.0)
        return FactorResult(
            name='externalFactors',
            value=float(0.5 + travel_impact + weather_impact),
            weight=self.base_weight,
            triggered=True,
            confidence=50,
            explanation=f"Weather:{weather} ({weather_impact:+.2f}), Travel:{travel_distance:.0f}km",
            metadata={
                'weather': str(weather),
                'travelDistance': travel_distance,
                'weatherImpact': weather_impact,
                'travelImpact': travel_impact,
            }
        )


class TeamQualityGapCalculator(FactorCalculator):
    def __init__(self, base_weight: float, base_elo: int = 1500, elo_ratings: Optional[Dict] = None):
        super().__init__('teamQualityGap', base_weight)
        self.base_elo = base_elo
        self.elo_ratings = elo_ratings if elo_ratings is not None else {}

    def calculate(self, match_data: Dict, context: MatchContext) -> FactorResult:
        home_team = match_data.get('homeTeam', match_data.get('home_team', ''))
        away_team = match_data.get('awayTeam', match_data.get('away_team', ''))
        home_elo = float(match_data.get('home_elo', self.elo_ratings.get(home_team, self.base_elo)))
        away_elo = float(match_data.get('away_elo', self.elo_ratings.get(away_team, self.base_elo)))
        elo_diff = home_elo - away_elo
        elo_signal = 0.5 + float(np.tanh(elo_diff / 300)) * 0.4

        home_pos = int(match_data.get('home_position', match_data.get('homePosition', 10)))
        away_pos = int(match_data.get('away_position', match_data.get('awayPosition', 10)))
        pos_diff = away_pos - home_pos
        position_signal = 0.5 + float(np.tanh(pos_diff / 10)) * 0.35

        home_stars = int(match_data.get('homeStarRating', 3))
        away_stars = int(match_data.get('awayStarRating', 3))
        star_signal = max(0.2, min(0.8, 0.5 + (home_stars - away_stars) * 0.1))

        has_elo = match_data.get('home_elo') is not None or home_team in self.elo_ratings
        if has_elo:
            quality_score = elo_signal * 0.50 + position_signal * 0.35 + star_signal * 0.15
        else:
            quality_score = position_signal * 0.60 + star_signal * 0.40

        gap_magnitude = abs(quality_score - 0.5) * 2
        favorite = 'home' if quality_score > 0.55 else ('away' if quality_score < 0.45 else 'neutral')
        return FactorResult(
            name='teamQualityGap',
            value=float(quality_score),
            weight=self.base_weight,
            triggered=True,
            confidence=85,
            explanation=f"Quality: {favorite} favored (gap: {gap_magnitude:.2f})",
            metadata={
                'homeElo': home_elo,
                'awayElo': away_elo,
                'eloDiff': float(elo_diff),
                'positionDiff': int(pos_diff),
                'gapMagnitude': float(gap_magnitude),
                'qualityFavorite': favorite,
            }
        )
