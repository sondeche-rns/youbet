"""
Unit Tests for Contextual Factor Calculators (Algorithm V2)

Tests each contextual calculator in isolation through its own interface.
"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import MatchContext, H2HRecord, ManagerInfo, DefensiveStyle
from src.factors.contextual import (
    H2HHistoricalCalculator,
    H2HAnomalyCalculator,
    PossessionQualityCalculator,
    ManagerMomentumCalculator,
    RelegationMotivationCalculator,
    CounterAttackCalculator,
    AwayDrawFrequencyCalculator,
)
from src.config import FOOTBALL_WEIGHTS_V2


class TestH2HFactors(unittest.TestCase):
    """Test H2H historical and anomaly detection"""

    def setUp(self):
        self.hist_calc = H2HHistoricalCalculator(FOOTBALL_WEIGHTS_V2['h2hHistorical'])
        self.anom_calc = H2HAnomalyCalculator(FOOTBALL_WEIGHTS_V2['h2hAnomaly'])

    def test_h2h_no_data(self):
        """Test H2H with no data available"""
        context = MatchContext(
            homeDefensiveStyle=DefensiveStyle.BALANCED,
            awayDefensiveStyle=DefensiveStyle.BALANCED,
            h2hRecord=None
        )
        match_data = {'homeTeam': 'Arsenal', 'awayTeam': 'Chelsea'}

        hist = self.hist_calc.calculate(match_data, context)
        anom = self.anom_calc.calculate(match_data, context)

        self.assertEqual(hist.name, 'h2hHistorical')
        self.assertEqual(hist.weight, 0.0)
        self.assertFalse(hist.triggered)
        self.assertEqual(anom.name, 'h2hAnomaly')
        self.assertEqual(anom.weight, 0.0)
        self.assertFalse(anom.triggered)

    def test_h2h_normal_record(self):
        """Test H2H with normal historical record"""
        h2h = H2HRecord(
            homeTeam='Arsenal',
            awayTeam='Chelsea',
            results=[
                {'date': '2024-01-01', 'homeScore': 2, 'awayScore': 1},
                {'date': '2024-03-01', 'homeScore': 1, 'awayScore': 1},
                {'date': '2024-05-01', 'homeScore': 0, 'awayScore': 2},
            ],
            weakerTeamUnbeatenStreak=1,
            anomalyTriggered=False
        )

        context = MatchContext(
            homeDefensiveStyle=DefensiveStyle.BALANCED,
            awayDefensiveStyle=DefensiveStyle.BALANCED,
            homeLeaguePosition=5,
            awayLeaguePosition=8,
            h2hRecord=h2h
        )

        match_data = {'homeTeam': 'Arsenal', 'awayTeam': 'Chelsea'}
        hist = self.hist_calc.calculate(match_data, context)
        anom = self.anom_calc.calculate(match_data, context)

        self.assertEqual(hist.weight, 0.05)
        self.assertTrue(hist.triggered)
        self.assertGreater(hist.confidence, 0)

        self.assertEqual(anom.weight, 0.0)
        self.assertFalse(anom.triggered)

    def test_h2h_anomaly_detected(self):
        """Test H2H anomaly (weaker team unbeaten in 3+ H2H)"""
        h2h = H2HRecord(
            homeTeam='West Ham',
            awayTeam='Man United',
            results=[
                {'date': '2024-01-01', 'homeScore': 1, 'awayScore': 1},
                {'date': '2024-03-01', 'homeScore': 2, 'awayScore': 0},
                {'date': '2024-05-01', 'homeScore': 1, 'awayScore': 1},
            ],
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

        match_data = {'homeTeam': 'West Ham', 'awayTeam': 'Man United'}
        hist = self.hist_calc.calculate(match_data, context)
        anom = self.anom_calc.calculate(match_data, context)

        self.assertEqual(hist.weight, 0.0)
        self.assertFalse(hist.triggered)

        self.assertEqual(anom.weight, 0.15)
        self.assertTrue(anom.triggered)
        self.assertEqual(anom.confidence, 90)
        self.assertIn('streak', anom.metadata)
        self.assertEqual(anom.metadata['streak'], 3)


class TestPossessionQuality(unittest.TestCase):
    """Test Possession Quality Index (PQI)"""

    def setUp(self):
        self.calc = PossessionQualityCalculator(FOOTBALL_WEIGHTS_V2['possessionQuality'])

    def test_pqi_calculation(self):
        """Test PQI calculation with known values"""
        context = MatchContext(
            homeDefensiveStyle=DefensiveStyle.LOW_BLOCK,
            awayDefensiveStyle=DefensiveStyle.HIGH_PRESS
        )
        match_data = {
            'home_xg': 1.05,
            'away_xg': 1.72,
            'home_possession': 41,
            'away_possession': 59
        }

        result = self.calc.calculate(match_data, context)

        self.assertEqual(result.name, 'possessionQuality')
        self.assertEqual(result.weight, 0.12)
        self.assertTrue(result.triggered)
        self.assertIn('home_pqi', result.metadata)
        self.assertIn('away_pqi', result.metadata)

        home_pqi = result.metadata['home_pqi']
        away_pqi = result.metadata['away_pqi']

        # Home: 1.05 / 0.41 * 100 = 256.1
        # Away: 1.72 / 0.59 * 100 = 291.5
        self.assertAlmostEqual(home_pqi, 256.1, places=1)
        self.assertAlmostEqual(away_pqi, 291.5, places=1)


class TestManagerMomentum(unittest.TestCase):
    """Test Manager Bounce Decay"""

    def setUp(self):
        self.calc = ManagerMomentumCalculator(FOOTBALL_WEIGHTS_V2['managerMomentum'])

    def test_new_manager_bounce(self):
        """Test new manager bounce (first few games)"""
        home_mgr = ManagerInfo(
            name='New Manager',
            appointmentDate='2024-01-01',
            gamesManaged=2,
            results=['W', 'W'],
            isInterim=False
        )
        away_mgr = ManagerInfo(
            name='Established Manager',
            appointmentDate='2020-01-01',
            gamesManaged=150,
            results=['W', 'D', 'L', 'W', 'W'],
            isInterim=False
        )

        context = MatchContext(
            homeDefensiveStyle=DefensiveStyle.BALANCED,
            awayDefensiveStyle=DefensiveStyle.BALANCED,
            homeManagerInfo=home_mgr,
            awayManagerInfo=away_mgr
        )

        result = self.calc.calculate({}, context)

        self.assertTrue(result.triggered)
        self.assertGreater(result.weight, 0)
        self.assertIn('home_bounce', result.metadata)
        self.assertIn('away_bounce', result.metadata)

        home_bounce = result.metadata['home_bounce']
        # base * (0.85 ^ 2) = 0.08 * 0.7225 = 0.0578
        self.assertAlmostEqual(home_bounce, 0.0578, places=3)

        away_bounce = result.metadata['away_bounce']
        self.assertLess(away_bounce, 0.01)

    def test_interim_manager_penalty(self):
        """Test interim manager receives lower bounce"""
        interim_mgr = ManagerInfo(
            name='Interim Manager',
            appointmentDate='2024-01-01',
            gamesManaged=1,
            results=['W'],
            isInterim=True
        )
        full_mgr = ManagerInfo(
            name='Full Manager',
            appointmentDate='2024-01-01',
            gamesManaged=1,
            results=['W'],
            isInterim=False
        )

        context = MatchContext(
            homeDefensiveStyle=DefensiveStyle.BALANCED,
            awayDefensiveStyle=DefensiveStyle.BALANCED,
            homeManagerInfo=interim_mgr,
            awayManagerInfo=full_mgr
        )

        result = self.calc.calculate({}, context)

        home_bounce = result.metadata['home_bounce']
        away_bounce = result.metadata['away_bounce']

        # Interim: 0.056 * 0.85 = 0.0476
        # Full: 0.08 * 0.85 = 0.068
        self.assertAlmostEqual(home_bounce, 0.0476, places=3)
        self.assertAlmostEqual(away_bounce, 0.068, places=3)
        self.assertLess(home_bounce, away_bounce)


class TestRelegationMotivation(unittest.TestCase):
    """Test Relegation Motivation Factor"""

    def setUp(self):
        self.calc = RelegationMotivationCalculator(FOOTBALL_WEIGHTS_V2['relegationMotivation'])

    def test_critical_zone_with_fight(self):
        """Test bottom 3 team with recent wins"""
        context = MatchContext(
            homeDefensiveStyle=DefensiveStyle.LOW_BLOCK,
            awayDefensiveStyle=DefensiveStyle.HIGH_PRESS,
            homeLeaguePosition=19,
            homeRecentForm=['L', 'W', 'W', 'D', 'W']
        )

        result = self.calc.calculate({}, context)

        self.assertTrue(result.triggered)
        self.assertEqual(result.weight, 0.08)
        self.assertIn('draw_boost', result.metadata)
        self.assertIn('home_win_boost', result.metadata)
        self.assertEqual(result.metadata['draw_boost'], 0.08)
        self.assertEqual(result.metadata['home_win_boost'], 0.03)
        self.assertEqual(result.metadata['tier'], 'critical')

    def test_danger_zone(self):
        """Test position 17-18"""
        context = MatchContext(
            homeDefensiveStyle=DefensiveStyle.BALANCED,
            awayDefensiveStyle=DefensiveStyle.HIGH_PRESS,
            homeLeaguePosition=17,
            homeRecentForm=['L', 'D', 'L', 'D', 'D']
        )

        result = self.calc.calculate({}, context)

        self.assertTrue(result.triggered)
        self.assertEqual(result.weight, 0.08)
        self.assertEqual(result.metadata['draw_boost'], 0.04)
        self.assertEqual(result.metadata['home_win_boost'], 0.02)
        self.assertEqual(result.metadata['tier'], 'danger')

    def test_safe_position(self):
        """Test mid-table team (no relegation factor)"""
        context = MatchContext(
            homeDefensiveStyle=DefensiveStyle.BALANCED,
            awayDefensiveStyle=DefensiveStyle.BALANCED,
            homeLeaguePosition=12,
            homeRecentForm=['W', 'D', 'W', 'L', 'D']
        )

        result = self.calc.calculate({}, context)

        self.assertFalse(result.triggered)
        self.assertEqual(result.weight, 0.0)


class TestCounterAttackEfficiency(unittest.TestCase):
    """Test Counter-Attack Efficiency Factor"""

    def setUp(self):
        self.calc = CounterAttackCalculator(FOOTBALL_WEIGHTS_V2['counterAttackEfficiency'])

    def test_counter_attack_scenario(self):
        """Test low-possession team vs high-possession team"""
        context = MatchContext(
            homeDefensiveStyle=DefensiveStyle.LOW_BLOCK,
            awayDefensiveStyle=DefensiveStyle.HIGH_PRESS,
            homeSeasonStats={'avgPossession': 41, 'goalsPerGame': 1.3},
            awaySeasonStats={'avgPossession': 62, 'goalsPerGame': 1.8}
        )

        result = self.calc.calculate({}, context)

        self.assertTrue(result.triggered)
        self.assertEqual(result.weight, 0.06)
        self.assertIn('underdog_team', result.metadata)
        self.assertEqual(result.metadata['underdog_team'], 'home')
        self.assertEqual(result.metadata['draw_boost'], 0.06)

    def test_no_counter_scenario(self):
        """Test balanced possession (no counter-attack setup)"""
        context = MatchContext(
            homeDefensiveStyle=DefensiveStyle.BALANCED,
            awayDefensiveStyle=DefensiveStyle.BALANCED,
            homeSeasonStats={'avgPossession': 50, 'goalsPerGame': 1.5},
            awaySeasonStats={'avgPossession': 50, 'goalsPerGame': 1.5}
        )

        result = self.calc.calculate({}, context)

        self.assertFalse(result.triggered)
        self.assertEqual(result.weight, 0.0)


class TestAwayDrawFrequency(unittest.TestCase):
    """Test Away Draw Frequency Factor"""

    def setUp(self):
        self.calc = AwayDrawFrequencyCalculator(FOOTBALL_WEIGHTS_V2['awayDrawFrequency'])

    def test_high_away_draw_rate(self):
        """Test team with high away draw frequency"""
        context = MatchContext(
            homeDefensiveStyle=DefensiveStyle.BALANCED,
            awayDefensiveStyle=DefensiveStyle.LOW_BLOCK,
            awaySeasonStats={
                'awayDrawRate': 0.45,
                'totalAwayGames': 15,
                'awayDraws': 7
            }
        )

        result = self.calc.calculate({}, context)

        self.assertTrue(result.triggered)
        self.assertEqual(result.weight, 0.06)
        self.assertIn('draw_boost', result.metadata)
        # Boost = (0.45 - 0.25) * 0.5 = 0.10
        self.assertAlmostEqual(result.metadata['draw_boost'], 0.10, places=2)

    def test_normal_away_draw_rate(self):
        """Test team with normal away draw frequency"""
        context = MatchContext(
            homeDefensiveStyle=DefensiveStyle.BALANCED,
            awayDefensiveStyle=DefensiveStyle.BALANCED,
            awaySeasonStats={
                'awayDrawRate': 0.25,
                'totalAwayGames': 12,
                'awayDraws': 3
            }
        )

        result = self.calc.calculate({}, context)

        self.assertFalse(result.triggered)
        self.assertEqual(result.weight, 0.0)

    def test_insufficient_data(self):
        """Test with insufficient away games"""
        context = MatchContext(
            homeDefensiveStyle=DefensiveStyle.BALANCED,
            awayDefensiveStyle=DefensiveStyle.BALANCED,
            awaySeasonStats={
                'awayDrawRate': 0.50,
                'totalAwayGames': 4,
                'awayDraws': 2
            }
        )

        result = self.calc.calculate({}, context)

        self.assertFalse(result.triggered)
        self.assertEqual(result.weight, 0.0)
        self.assertEqual(result.confidence, 20)


if __name__ == '__main__':
    unittest.main()
