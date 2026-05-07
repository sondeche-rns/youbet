"""
Contextual factor calculators (Algorithm v2.0).

These factors are conditional: they return weight=0.0 when not triggered.
H2HHistorical and H2HAnomaly are mutually exclusive — they coordinate
through context.h2hRecord.anomalyTriggered.

Note: ManagerMomentumCalculator computes its effective weight dynamically
from the bounce magnitude rather than using base_weight directly.
"""

import numpy as np
from typing import Dict

from ..models import FactorCalculator, FactorResult, MatchContext


class H2HHistoricalCalculator(FactorCalculator):
    def __init__(self, base_weight: float):
        super().__init__('h2hHistorical', base_weight)

    def calculate(self, match_data: Dict, context: MatchContext) -> FactorResult:
        if context.h2hRecord is None:
            return FactorResult(name='h2hHistorical', value=0.5, weight=0.0, triggered=False,
                                confidence=0, explanation="No H2H data available")

        h2h = context.h2hRecord

        if h2h.total_matches == 0:
            h2h_score, confidence = 0.5, 0
        else:
            home_win_rate = h2h.home_wins / h2h.total_matches
            h2h_score = 0.5 + (home_win_rate - 0.33) * 0.5
            confidence = min(h2h.total_matches * 10, 100)

        if h2h.anomalyTriggered and h2h.weakerTeamUnbeatenStreak >= 3:
            return FactorResult(
                name='h2hHistorical', value=float(h2h_score), weight=0.0, triggered=False,
                confidence=confidence,
                explanation=f"Replaced by anomaly (streak: {h2h.weakerTeamUnbeatenStreak})"
            )

        return FactorResult(
            name='h2hHistorical', value=float(h2h_score), weight=self.base_weight, triggered=True,
            confidence=confidence,
            explanation=f"H2H: {h2h.home_wins}W-{h2h.draws}D-{h2h.away_wins}L"
        )


class H2HAnomalyCalculator(FactorCalculator):
    def __init__(self, base_weight: float):
        super().__init__('h2hAnomaly', base_weight)

    def calculate(self, match_data: Dict, context: MatchContext) -> FactorResult:
        if context.h2hRecord is None:
            return FactorResult(name='h2hAnomaly', value=0.5, weight=0.0, triggered=False,
                                confidence=0, explanation="No H2H data for anomaly detection")

        h2h = context.h2hRecord
        anomaly_detected = h2h.anomalyTriggered and h2h.weakerTeamUnbeatenStreak >= 3

        if not anomaly_detected:
            return FactorResult(name='h2hAnomaly', value=0.5, weight=0.0, triggered=False,
                                confidence=50, explanation="No anomaly (streak < 3)")

        weaker_team_is_home = context.homeLeaguePosition > context.awayLeaguePosition
        anomaly_boost = 0.2 if weaker_team_is_home else -0.1
        return FactorResult(
            name='h2hAnomaly', value=float(0.5 + anomaly_boost), weight=self.base_weight,
            triggered=True, confidence=90,
            explanation=f"Weaker team unbeaten in {h2h.weakerTeamUnbeatenStreak} H2H",
            metadata={'streak': h2h.weakerTeamUnbeatenStreak, 'weaker_team_home': weaker_team_is_home}
        )


class PossessionQualityCalculator(FactorCalculator):
    def __init__(self, base_weight: float):
        super().__init__('possessionQuality', base_weight)

    def calculate(self, match_data: Dict, context: MatchContext) -> FactorResult:
        home_xg = float(match_data.get('home_xg', match_data.get('homeXg', 1.3)))
        away_xg = float(match_data.get('away_xg', match_data.get('awayXg', 1.3)))
        home_poss = max(float(match_data.get('home_possession', 50)) / 100, 0.3)
        away_poss = max(float(match_data.get('away_possession', 50)) / 100, 0.3)

        home_pqi = (home_xg / home_poss) * 100
        away_pqi = (away_xg / away_poss) * 100
        pqi_diff = home_pqi - away_pqi
        normalized_score = 0.5 + float(np.tanh(pqi_diff / 100)) * 0.3

        classify = lambda pqi: "excellent" if pqi > 300 else "good" if pqi > 200 else "poor"
        return FactorResult(
            name='possessionQuality', value=float(normalized_score), weight=self.base_weight,
            triggered=True, confidence=80,
            explanation=f"PQI H:{home_pqi:.1f} ({classify(home_pqi)}) vs A:{away_pqi:.1f} ({classify(away_pqi)})",
            metadata={'home_pqi': float(home_pqi), 'away_pqi': float(away_pqi)}
        )


class ManagerMomentumCalculator(FactorCalculator):
    """
    Weight is computed dynamically from bounce magnitude rather than using base_weight.
    base_weight from config acts as a reference for calibration purposes only.
    """

    def __init__(self, base_weight: float):
        super().__init__('managerMomentum', base_weight)

    def calculate(self, match_data: Dict, context: MatchContext) -> FactorResult:
        if context.homeManagerInfo is None or context.awayManagerInfo is None:
            return FactorResult(name='managerMomentum', value=0.5, weight=0.0, triggered=False,
                                confidence=0, explanation="No manager data")

        def calc_bounce(mgr) -> float:
            base = 0.08 if not mgr.isInterim else 0.056
            bounce = base * (0.85 ** mgr.gamesManaged)
            return bounce if bounce >= 0.01 else 0.0

        home_bounce = calc_bounce(context.homeManagerInfo)
        away_bounce = calc_bounce(context.awayManagerInfo)
        net_bounce = home_bounce - away_bounce

        if abs(net_bounce) < 0.01:
            return FactorResult(name='managerMomentum', value=0.5, weight=0.0, triggered=False,
                                confidence=50, explanation="No active bounce")

        value = float(0.5 + net_bounce * 2)
        effective_weight = float(max(home_bounce, away_bounce))
        return FactorResult(
            name='managerMomentum', value=value, weight=effective_weight,
            triggered=True, confidence=80,
            explanation=f"Bounce H:{home_bounce:.3f} vs A:{away_bounce:.3f}",
            metadata={'home_bounce': float(home_bounce), 'away_bounce': float(away_bounce)}
        )


class RelegationMotivationCalculator(FactorCalculator):
    def __init__(self, base_weight: float):
        super().__init__('relegationMotivation', base_weight)

    def calculate(self, match_data: Dict, context: MatchContext) -> FactorResult:
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
            weight=self.base_weight, triggered=True, confidence=90,
            explanation=f"{tier} zone (pos {home_pos}), {recent_wins}/4 wins",
            metadata={'draw_boost': float(draw_boost), 'home_win_boost': float(home_win_boost), 'tier': tier}
        )


class CounterAttackCalculator(FactorCalculator):
    def __init__(self, base_weight: float):
        super().__init__('counterAttackEfficiency', base_weight)

    def calculate(self, match_data: Dict, context: MatchContext) -> FactorResult:
        if context.homeSeasonStats is not None and context.awaySeasonStats is not None:
            home_poss = context.homeSeasonStats.get('avgPossession', 50)
            away_poss = context.awaySeasonStats.get('avgPossession', 50)
            confidence_base = 75
        elif 'home_possession' in match_data or 'away_possession' in match_data:
            home_poss = match_data.get('home_possession', 50)
            away_poss = match_data.get('away_possession', 50)
            confidence_base = 60
        else:
            return FactorResult(name='counterAttackEfficiency', value=0.5, weight=0.0, triggered=False,
                                confidence=0, explanation="No possession data")

        scenario = (home_poss < 45 and away_poss > 58) or (away_poss < 45 and home_poss > 58)
        if not scenario:
            return FactorResult(
                name='counterAttackEfficiency', value=0.5, weight=0.0, triggered=False,
                confidence=confidence_base,
                explanation=f"No counter setup (H:{home_poss:.1f}% A:{away_poss:.1f}%)"
            )

        if home_poss < 45:
            underdog_team, underdog_poss, value = "home", home_poss, 0.5 + 0.05
        else:
            underdog_team, underdog_poss, value = "away", away_poss, 0.5 - 0.05

        return FactorResult(
            name='counterAttackEfficiency', value=float(value), weight=self.base_weight,
            triggered=True, confidence=confidence_base,
            explanation=f"{underdog_team} counter threat (poss: {underdog_poss:.1f}%)",
            metadata={'underdog_team': underdog_team, 'draw_boost': 0.06, 'underdog_boost': 0.04}
        )


class AwayDrawFrequencyCalculator(FactorCalculator):
    def __init__(self, base_weight: float):
        super().__init__('awayDrawFrequency', base_weight)

    def calculate(self, match_data: Dict, context: MatchContext) -> FactorResult:
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
            return FactorResult(
                name='awayDrawFrequency', value=0.5, weight=0.0, triggered=False,
                confidence=20 if total_away_games < 5 else 80,
                explanation=f"Normal rate: {away_draw_rate*100:.1f}%" if total_away_games >= 5 else "Insufficient games"
            )

        boost = min((away_draw_rate - 0.25) * 0.5, 0.15)
        return FactorResult(
            name='awayDrawFrequency', value=float(0.5 + boost), weight=self.base_weight,
            triggered=True, confidence=min(total_away_games * 5, 100),
            explanation=f"Draw-prone: {away_draw_rate*100:.1f}% ({total_away_games} games)",
            metadata={'draw_boost': float(boost), 'away_draw_rate': float(away_draw_rate)}
        )
