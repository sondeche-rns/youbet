"""
Tests for HistoricalDataStore interface implementations.

Behaviors tested via public interface only — InMemoryHistoricalDataStore
and CsvHistoricalDataStore, then MatchContextBuilder wired to the store.
"""

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.historical_data_store import InMemoryHistoricalDataStore, CsvHistoricalDataStore
from src.context_builder import MatchContextBuilder

MATCH_A = {'home_team': 'Arsenal', 'away_team': 'Chelsea', 'home_goals': 2, 'away_goals': 1, 'Date': '2024-01-01'}
MATCH_B = {'home_team': 'Chelsea', 'away_team': 'Arsenal', 'home_goals': 1, 'away_goals': 0, 'Date': '2024-03-01'}
MATCH_C = {'home_team': 'Arsenal', 'away_team': 'Liverpool', 'home_goals': 1, 'away_goals': 1, 'Date': '2024-02-01'}


class TestInMemoryStoreH2H(unittest.TestCase):

    def test_returns_matches_for_both_venue_permutations(self):
        store = InMemoryHistoricalDataStore([MATCH_A, MATCH_B, MATCH_C])
        result = store.get_h2h_matches('Arsenal', 'Chelsea')
        self.assertEqual(len(result), 2)

    def test_returns_empty_list_for_unknown_teams(self):
        store = InMemoryHistoricalDataStore([MATCH_A, MATCH_B])
        result = store.get_h2h_matches('Burnley', 'Wolves')
        self.assertEqual(result, [])

    def test_caps_at_last_ten_matches(self):
        matches = [
            {'home_team': 'Arsenal', 'away_team': 'Chelsea',
             'home_goals': 1, 'away_goals': 0, 'Date': f'2024-{i:02d}-01'}
            for i in range(1, 13)  # 12 matches
        ]
        store = InMemoryHistoricalDataStore(matches)
        result = store.get_h2h_matches('Arsenal', 'Chelsea')
        self.assertEqual(len(result), 10)

    def test_caps_returns_most_recent(self):
        matches = [
            {'home_team': 'Arsenal', 'away_team': 'Chelsea',
             'home_goals': 1, 'away_goals': 0, 'Date': f'2024-{i:02d}-01'}
            for i in range(1, 13)
        ]
        store = InMemoryHistoricalDataStore(matches)
        result = store.get_h2h_matches('Arsenal', 'Chelsea')
        self.assertEqual(result[0]['Date'], '2024-03-01')
        self.assertEqual(result[-1]['Date'], '2024-12-01')


class TestInMemoryStoreSeasonMatches(unittest.TestCase):

    def test_returns_all_matches_for_team(self):
        store = InMemoryHistoricalDataStore([MATCH_A, MATCH_B, MATCH_C])
        result = store.get_team_season_matches('Arsenal')
        self.assertEqual(len(result), 3)

    def test_excludes_matches_not_involving_team(self):
        OTHER = {'home_team': 'Chelsea', 'away_team': 'Liverpool',
                 'home_goals': 0, 'away_goals': 0, 'Date': '2024-04-01'}
        store = InMemoryHistoricalDataStore([MATCH_A, MATCH_B, OTHER])
        result = store.get_team_season_matches('Arsenal')
        self.assertEqual(len(result), 2)

    def test_returns_empty_list_for_unknown_team(self):
        store = InMemoryHistoricalDataStore([MATCH_A, MATCH_B])
        result = store.get_team_season_matches('Burnley')
        self.assertEqual(result, [])


class TestCsvHistoricalDataStore(unittest.TestCase):

    REQUIRED_COLS = ['home_team', 'away_team', 'home_goals', 'away_goals', 'Date']

    def _valid_df(self):
        return pd.DataFrame([MATCH_A, MATCH_B, MATCH_C])

    def test_raises_on_missing_required_column(self):
        df = self._valid_df().drop(columns=['home_goals'])
        with self.assertRaises(ValueError):
            CsvHistoricalDataStore(df)

    def test_accepts_valid_dataframe(self):
        store = CsvHistoricalDataStore(self._valid_df())
        self.assertIsNotNone(store)

    def test_get_h2h_matches_delegates_correctly(self):
        store = CsvHistoricalDataStore(self._valid_df())
        result = store.get_h2h_matches('Arsenal', 'Chelsea')
        self.assertEqual(len(result), 2)

    def test_get_team_season_matches_delegates_correctly(self):
        store = CsvHistoricalDataStore(self._valid_df())
        result = store.get_team_season_matches('Arsenal')
        self.assertEqual(len(result), 3)


class TestMatchContextBuilderWithStore(unittest.TestCase):

    def _store_with_h2h_streak(self, weaker_wins: int):
        """Return a store where 'Burnley' (weaker, pos 19) is unbeaten in last N games vs Arsenal (pos 1)."""
        matches = []
        for i in range(weaker_wins):
            matches.append({
                'home_team': 'Burnley', 'away_team': 'Arsenal',
                'home_goals': 1, 'away_goals': 0,
                'Date': f'2024-{i+1:02d}-01',
                'home_possession': 40, 'away_possession': 60
            })
        return InMemoryHistoricalDataStore(matches)

    def test_builder_accepts_store_and_builds_h2h_record(self):
        store = self._store_with_h2h_streak(3)
        builder = MatchContextBuilder(store=store)
        ctx = builder.build_context({
            'homeTeam': 'Arsenal', 'awayTeam': 'Burnley',
            'homePosition': 1, 'awayPosition': 19
        })
        self.assertIsNotNone(ctx.h2hRecord)

    def test_anomaly_triggered_when_streak_gte_3(self):
        store = self._store_with_h2h_streak(3)
        builder = MatchContextBuilder(store=store)
        ctx = builder.build_context({
            'homeTeam': 'Arsenal', 'awayTeam': 'Burnley',
            'homePosition': 1, 'awayPosition': 19
        })
        self.assertTrue(ctx.h2hRecord.anomalyTriggered)
        self.assertEqual(ctx.h2hRecord.weakerTeamUnbeatenStreak, 3)

    def test_anomaly_not_triggered_when_streak_lt_3(self):
        store = self._store_with_h2h_streak(2)
        builder = MatchContextBuilder(store=store)
        ctx = builder.build_context({
            'homeTeam': 'Arsenal', 'awayTeam': 'Burnley',
            'homePosition': 1, 'awayPosition': 19
        })
        self.assertIsNone(ctx.h2hRecord)  # < 3 matches → insufficient data

    def test_no_store_returns_none_h2h(self):
        builder = MatchContextBuilder()
        ctx = builder.build_context({'homeTeam': 'Arsenal', 'awayTeam': 'Chelsea'})
        self.assertIsNone(ctx.h2hRecord)


class TestConditionalFactorsRemoved(unittest.TestCase):

    def test_conditional_factors_not_in_config(self):
        import src.config as cfg
        self.assertFalse(hasattr(cfg, 'CONDITIONAL_FACTORS'))


if __name__ == '__main__':
    unittest.main()
