"""
HistoricalDataStore — seam for historical match data access.

Provides a protocol-based interface so MatchContextBuilder can be tested
without touching real CSV files, and schema validation is enforced at the
boundary rather than silently failing at query time.
"""

from typing import Dict, List, Protocol, runtime_checkable

import pandas as pd


REQUIRED_COLUMNS = {'home_team', 'away_team', 'home_goals', 'away_goals', 'Date'}


@runtime_checkable
class HistoricalDataStore(Protocol):
    def get_h2h_matches(self, home: str, away: str) -> List[Dict]: ...
    def get_team_season_matches(self, team: str) -> List[Dict]: ...


class InMemoryHistoricalDataStore:
    """Holds matches as plain dicts — no I/O, ideal for unit tests."""

    def __init__(self, matches: List[Dict]):
        self._matches = matches

    def get_h2h_matches(self, home: str, away: str) -> List[Dict]:
        result = [
            m for m in self._matches
            if (m.get('home_team') == home and m.get('away_team') == away) or
               (m.get('home_team') == away and m.get('away_team') == home)
        ]
        return result[-10:]

    def get_team_season_matches(self, team: str) -> List[Dict]:
        return [
            m for m in self._matches
            if m.get('home_team') == team or m.get('away_team') == team
        ]


class CsvHistoricalDataStore:
    """Wraps a pandas DataFrame loaded from CSV; validates schema at construction."""

    def __init__(self, df: pd.DataFrame):
        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(f"DataFrame missing required columns: {sorted(missing)}")
        self._inner = InMemoryHistoricalDataStore(df.to_dict(orient='records'))

    def get_h2h_matches(self, home: str, away: str) -> List[Dict]:
        return self._inner.get_h2h_matches(home, away)

    def get_team_season_matches(self, team: str) -> List[Dict]:
        return self._inner.get_team_season_matches(team)
