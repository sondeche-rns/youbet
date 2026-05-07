"""JackpotSource interface and concrete adapters — issue #3"""
from abc import ABC, abstractmethod
from typing import Dict
from datetime import datetime


class JackpotSource(ABC):
    @abstractmethod
    def fetch(self) -> Dict:
        """Return a jackpot payload including source_type: 'live' | 'sample'."""


_SPORTPESA_MEGA_MATCHES = [
    {'match_number': 1,  'home_team': 'Arsenal',        'away_team': 'Chelsea',       'competition': 'Premier League',      'kickoff': 'Sat 15:00'},
    {'match_number': 2,  'home_team': 'Man City',        'away_team': 'Liverpool',     'competition': 'Premier League',      'kickoff': 'Sat 17:30'},
    {'match_number': 3,  'home_team': 'Tottenham',       'away_team': 'Man United',    'competition': 'Premier League',      'kickoff': 'Sat 15:00'},
    {'match_number': 4,  'home_team': 'Real Madrid',     'away_team': 'Barcelona',     'competition': 'La Liga',             'kickoff': 'Sat 20:00'},
    {'match_number': 5,  'home_team': 'Bayern Munich',   'away_team': 'Dortmund',      'competition': 'Bundesliga',          'kickoff': 'Sat 17:30'},
    {'match_number': 6,  'home_team': 'Inter Milan',     'away_team': 'AC Milan',      'competition': 'Serie A',             'kickoff': 'Sat 19:45'},
    {'match_number': 7,  'home_team': 'PSG',             'away_team': 'Marseille',     'competition': 'Ligue 1',             'kickoff': 'Sat 20:00'},
    {'match_number': 8,  'home_team': 'Juventus',        'away_team': 'Napoli',        'competition': 'Serie A',             'kickoff': 'Sat 17:00'},
    {'match_number': 9,  'home_team': 'Atletico Madrid', 'away_team': 'Sevilla',       'competition': 'La Liga',             'kickoff': 'Sat 18:30'},
    {'match_number': 10, 'home_team': 'Leicester',       'away_team': 'West Ham',      'competition': 'Premier League',      'kickoff': 'Sat 15:00'},
    {'match_number': 11, 'home_team': 'Newcastle',       'away_team': 'Aston Villa',   'competition': 'Premier League',      'kickoff': 'Sat 15:00'},
    {'match_number': 12, 'home_team': 'Brighton',        'away_team': 'Wolves',        'competition': 'Premier League',      'kickoff': 'Sat 15:00'},
    {'match_number': 13, 'home_team': 'Everton',         'away_team': 'Southampton',   'competition': 'Premier League',      'kickoff': 'Sat 15:00'},
    {'match_number': 14, 'home_team': 'Leeds United',    'away_team': 'Burnley',       'competition': 'Championship',        'kickoff': 'Sat 15:00'},
    {'match_number': 15, 'home_team': 'Sheffield United','away_team': 'Norwich',       'competition': 'Championship',        'kickoff': 'Sat 15:00'},
    {'match_number': 16, 'home_team': 'Brentford',       'away_team': 'Fulham',        'competition': 'Premier League',      'kickoff': 'Sat 15:00'},
    {'match_number': 17, 'home_team': 'Crystal Palace',  'away_team': 'Bournemouth',   'competition': 'Premier League',      'kickoff': 'Sat 15:00'},
]

_SPORTPESA_MIDWEEK_MATCHES = [
    {'match_number': 1,  'home_team': 'Arsenal',        'away_team': 'Chelsea',       'competition': 'Premier League',      'kickoff': 'Wed 19:45'},
    {'match_number': 2,  'home_team': 'Man City',        'away_team': 'Liverpool',     'competition': 'Premier League',      'kickoff': 'Wed 19:45'},
    {'match_number': 3,  'home_team': 'Tottenham',       'away_team': 'Man United',    'competition': 'Premier League',      'kickoff': 'Wed 19:45'},
    {'match_number': 4,  'home_team': 'Real Madrid',     'away_team': 'Barcelona',     'competition': 'La Liga',             'kickoff': 'Wed 21:00'},
    {'match_number': 5,  'home_team': 'Bayern Munich',   'away_team': 'Dortmund',      'competition': 'Bundesliga',          'kickoff': 'Wed 20:30'},
    {'match_number': 6,  'home_team': 'Inter Milan',     'away_team': 'AC Milan',      'competition': 'Serie A',             'kickoff': 'Wed 19:45'},
    {'match_number': 7,  'home_team': 'PSG',             'away_team': 'Marseille',     'competition': 'Ligue 1',             'kickoff': 'Wed 20:00'},
    {'match_number': 8,  'home_team': 'Juventus',        'away_team': 'Napoli',        'competition': 'Serie A',             'kickoff': 'Wed 19:45'},
    {'match_number': 9,  'home_team': 'Atletico Madrid', 'away_team': 'Sevilla',       'competition': 'La Liga',             'kickoff': 'Wed 21:00'},
    {'match_number': 10, 'home_team': 'Newcastle',       'away_team': 'Aston Villa',   'competition': 'Premier League',      'kickoff': 'Wed 19:45'},
    {'match_number': 11, 'home_team': 'Brighton',        'away_team': 'Wolves',        'competition': 'Premier League',      'kickoff': 'Wed 19:45'},
    {'match_number': 12, 'home_team': 'Everton',         'away_team': 'Southampton',   'competition': 'Premier League',      'kickoff': 'Wed 19:45'},
    {'match_number': 13, 'home_team': 'Crystal Palace',  'away_team': 'Bournemouth',   'competition': 'Premier League',      'kickoff': 'Wed 19:45'},
]

_BETIKA_MATCHES = [
    {'match_number': 1,  'home_team': 'Arsenal',        'away_team': 'Liverpool',     'competition': 'Premier League',      'kickoff': 'Sat 15:00'},
    {'match_number': 2,  'home_team': 'Man City',        'away_team': 'Chelsea',       'competition': 'Premier League',      'kickoff': 'Sat 17:30'},
    {'match_number': 3,  'home_team': 'Real Madrid',     'away_team': 'Atletico Madrid','competition': 'La Liga',            'kickoff': 'Sat 20:00'},
    {'match_number': 4,  'home_team': 'Barcelona',       'away_team': 'Sevilla',       'competition': 'La Liga',             'kickoff': 'Sat 18:30'},
    {'match_number': 5,  'home_team': 'Bayern Munich',   'away_team': 'RB Leipzig',    'competition': 'Bundesliga',          'kickoff': 'Sat 17:30'},
    {'match_number': 6,  'home_team': 'Inter Milan',     'away_team': 'Juventus',      'competition': 'Serie A',             'kickoff': 'Sat 19:45'},
    {'match_number': 7,  'home_team': 'PSG',             'away_team': 'Lyon',          'competition': 'Ligue 1',             'kickoff': 'Sat 20:00'},
    {'match_number': 8,  'home_team': 'Tottenham',       'away_team': 'Newcastle',     'competition': 'Premier League',      'kickoff': 'Sat 15:00'},
    {'match_number': 9,  'home_team': 'Man United',      'away_team': 'West Ham',      'competition': 'Premier League',      'kickoff': 'Sat 17:00'},
    {'match_number': 10, 'home_team': 'Napoli',          'away_team': 'Roma',          'competition': 'Serie A',             'kickoff': 'Sat 17:00'},
    {'match_number': 11, 'home_team': 'Dortmund',        'away_team': 'Leverkusen',    'competition': 'Bundesliga',          'kickoff': 'Sat 15:30'},
    {'match_number': 12, 'home_team': 'Ajax',            'away_team': 'PSV',           'competition': 'Eredivisie',          'kickoff': 'Sat 19:45'},
    {'match_number': 13, 'home_team': 'Benfica',         'away_team': 'Porto',         'competition': 'Primeira Liga',       'kickoff': 'Sat 20:30'},
    {'match_number': 14, 'home_team': 'Celtic',          'away_team': 'Rangers',       'competition': 'Scottish Premiership','kickoff': 'Sat 15:00'},
    {'match_number': 15, 'home_team': 'Sporting CP',     'away_team': 'Braga',         'competition': 'Primeira Liga',       'kickoff': 'Sat 18:00'},
]

_SAMPLE_REGISTRY = {
    ("sportpesa", "mega"):    ("SportPesa", "Mega Jackpot",    17, _SPORTPESA_MEGA_MATCHES),
    ("sportpesa", "midweek"): ("SportPesa", "Midweek Jackpot", 13, _SPORTPESA_MIDWEEK_MATCHES),
    ("betika",    "jackpot"): ("Betika",    "Jackpot",         15, _BETIKA_MATCHES),
}


class SampleDataSource(JackpotSource):
    """Returns hardcoded fixture data, explicitly marked as sample."""

    def __init__(self, provider: str, jackpot_type: str):
        key = (provider.lower(), jackpot_type.lower())
        if key not in _SAMPLE_REGISTRY:
            raise ValueError(f"No sample data registered for {provider!r}/{jackpot_type!r}")
        self._provider, self._type, self._matches_count, self._matches = _SAMPLE_REGISTRY[key]

    def fetch(self) -> Dict:
        return {
            "source_type":    "sample",
            "provider":       self._provider,
            "type":           self._type,
            "matches_count":  self._matches_count,
            "fetched_at":     datetime.now().isoformat(),
            "matches":        [m.copy() for m in self._matches],
        }


class LiveScraperSource(JackpotSource):
    """Attempts real web scraping; falls back to SampleDataSource on failure."""

    def __init__(self, url: str, provider: str, jackpot_type: str, headers: dict,
                 scraper_fn, fallback: SampleDataSource):
        self._url = url
        self._provider = provider
        self._jackpot_type = jackpot_type
        self._headers = headers
        self._scraper_fn = scraper_fn
        self._fallback = fallback

    def fetch(self) -> Dict:
        try:
            import requests
            response = requests.get(self._url, headers=self._headers, timeout=15)
            response.raise_for_status()
            matches = self._scraper_fn(response.content)
            if not matches:
                raise ValueError("Scraper returned no matches")
            return {
                "source_type":   "live",
                "provider":      self._provider,
                "type":          self._jackpot_type,
                "matches_count": len(matches),
                "fetched_at":    datetime.now().isoformat(),
                "url":           self._url,
                "matches":       matches,
            }
        except Exception as e:
            import warnings
            warnings.warn(f"Live scrape failed for {self._provider} ({self._url}): {e}; falling back to sample data")
            payload = self._fallback.fetch()
            return payload
