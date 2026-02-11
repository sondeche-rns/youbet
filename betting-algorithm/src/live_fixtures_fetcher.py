"""
Live Fixtures Fetcher
Fetches current season matches and live odds from multiple sources
"""

import requests
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class LiveFixturesFetcher:
    """
    Fetches live/upcoming fixtures and odds from various sources.

    Supports:
    - The Odds API (live odds)
    - Football-Data.co.uk (current season results)
    - API-Football (live fixtures)
    """

    def __init__(self):
        self.odds_api_key = os.getenv('ODDS_API_KEY', '')
        self.api_football_key = os.getenv('API_FOOTBALL_KEY', '')

        # Load config
        config_path = Path('./config/data_sources.json')
        if config_path.exists():
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {}

    def get_upcoming_matches(self, sport: str = 'soccer_epl',
                            days_ahead: int = 7) -> List[Dict]:
        """
        Get upcoming matches for the next N days

        Args:
            sport: Sport key (e.g., 'soccer_epl', 'soccer_spain_la_liga')
            days_ahead: Number of days to look ahead

        Returns:
            List of matches with odds
        """
        matches = []

        # Try The Odds API first (if enabled and has key)
        if self.odds_api_key:
            try:
                print(f"Fetching from Odds API for sport: {sport}")
                odds_matches = self._fetch_from_odds_api(sport)
                matches.extend(odds_matches)
                print(f"Fetched {len(odds_matches)} matches from Odds API")
            except Exception as e:
                print(f"Error fetching from Odds API: {e}")
                import traceback
                traceback.print_exc()

        # Fallback to football-data.co.uk current season (only for historical data)
        # Note: This won't have upcoming matches, only completed ones
        if not matches:
            print("No upcoming matches from Odds API, checking football-data.co.uk...")
            try:
                fd_matches = self._fetch_from_football_data_uk()
                # Football-data.co.uk only has historical matches, not upcoming
                print(f"Fetched {len(fd_matches)} historical matches from Football-Data.co.uk")
                # Return empty list since these are historical, not upcoming
                return []
            except Exception as e:
                print(f"Error fetching from Football-Data.co.uk: {e}")
                return []

        # Filter to upcoming only
        from datetime import timezone
        now = datetime.now(timezone.utc)
        upcoming = []
        for match in matches:
            try:
                match_time = self._parse_match_time(match.get('commence_time') or match.get('date'))
                if match_time:
                    # Make sure match_time is timezone-aware
                    if match_time.tzinfo is None:
                        match_time = match_time.replace(tzinfo=timezone.utc)

                    if match_time > now:
                        days_diff = (match_time - now).days
                        if days_diff <= days_ahead:
                            upcoming.append(match)
            except Exception as e:
                print(f"Error parsing match time: {e}")
                continue

        print(f"Returning {len(upcoming)} upcoming matches")
        return upcoming

    def _fetch_from_odds_api(self, sport: str = 'soccer_epl') -> List[Dict]:
        """
        Fetch from The Odds API

        Available sports:
        - soccer_epl (Premier League)
        - soccer_spain_la_liga
        - soccer_germany_bundesliga
        - soccer_italy_serie_a
        - soccer_france_ligue_one
        """
        if not self.odds_api_key:
            print("No Odds API key found")
            return []

        base_url = "https://api.the-odds-api.com/v4"

        # Get odds
        url = f"{base_url}/sports/{sport}/odds"
        params = {
            'apiKey': self.odds_api_key,
            'regions': 'uk,eu',  # UK and European bookmakers
            'markets': 'h2h',     # Head to head (1X2)
            'oddsFormat': 'decimal'
        }

        print(f"Making request to: {url}")
        print(f"API Key (first 10 chars): {self.odds_api_key[:10]}...")

        response = requests.get(url, params=params, timeout=10)

        if response.status_code != 200:
            print(f"API Error: {response.status_code}")
            print(f"Response: {response.text}")
            response.raise_for_status()

        data = response.json()
        print(f"Received {len(data)} events from API")

        # Transform to our format
        matches = []
        for event in data:
            # Extract best odds
            home_odds, draw_odds, away_odds = self._extract_best_odds(event)

            matches.append({
                'id': event['id'],
                'sport': sport,
                'commence_time': event['commence_time'],
                'home_team': event['home_team'],
                'away_team': event['away_team'],
                'home_odds': home_odds,
                'draw_odds': draw_odds,
                'away_odds': away_odds,
                'bookmakers': len(event.get('bookmakers', [])),
                'source': 'the-odds-api'
            })

        return matches

    def _extract_best_odds(self, event: Dict) -> tuple:
        """Extract best available odds from bookmakers"""
        home_odds = []
        draw_odds = []
        away_odds = []

        for bookmaker in event.get('bookmakers', []):
            for market in bookmaker.get('markets', []):
                if market['key'] == 'h2h':
                    outcomes = market['outcomes']
                    for outcome in outcomes:
                        if outcome['name'] == event['home_team']:
                            home_odds.append(outcome['price'])
                        elif outcome['name'] == event['away_team']:
                            away_odds.append(outcome['price'])
                        elif outcome['name'] == 'Draw':
                            draw_odds.append(outcome['price'])

        # Return best (highest) odds
        return (
            max(home_odds) if home_odds else None,
            max(draw_odds) if draw_odds else None,
            max(away_odds) if away_odds else None
        )

    def _fetch_from_football_data_uk(self) -> List[Dict]:
        """
        Fetch current season from football-data.co.uk
        This gives us completed matches, useful for building recent form
        """
        import pandas as pd
        import io

        # Current season code
        current_year = datetime.now().year
        if datetime.now().month >= 8:  # Season starts in August
            season_code = f"{str(current_year)[2:]}{str(current_year + 1)[2:]}"
        else:
            season_code = f"{str(current_year - 1)[2:]}{str(current_year)[2:]}"

        base_url = "https://www.football-data.co.uk/mmz4281"
        leagues = ['E0', 'E1', 'SP1', 'D1', 'I1', 'F1']  # Major leagues

        matches = []
        for league in leagues:
            try:
                url = f"{base_url}/{season_code}/{league}.csv"
                response = requests.get(url, timeout=15)

                if response.status_code == 200:
                    df = pd.read_csv(io.StringIO(response.text))

                    # Convert to our format
                    for _, row in df.iterrows():
                        if pd.notna(row.get('Date')) and pd.notna(row.get('HomeTeam')):
                            matches.append({
                                'date': row['Date'],
                                'home_team': row['HomeTeam'],
                                'away_team': row['AwayTeam'],
                                'home_goals': row.get('FTHG'),
                                'away_goals': row.get('FTAG'),
                                'home_odds': row.get('B365H') or row.get('BWH'),
                                'draw_odds': row.get('B365D') or row.get('BWD'),
                                'away_odds': row.get('B365A') or row.get('BWA'),
                                'league': league,
                                'season': season_code,
                                'source': 'football-data-uk'
                            })
            except Exception as e:
                print(f"Error fetching {league}: {e}")
                continue

        return matches

    def get_available_sports(self) -> List[Dict]:
        """Get available sports from The Odds API"""
        if not self.odds_api_key:
            return []

        try:
            base_url = "https://api.the-odds-api.com/v4"
            url = f"{base_url}/sports"
            params = {'apiKey': self.odds_api_key}

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            return response.json()
        except Exception as e:
            print(f"Error fetching sports: {e}")
            return []

    def get_live_odds_for_match(self, home_team: str, away_team: str,
                                sport: str = 'soccer_epl') -> Optional[Dict]:
        """
        Get live odds for a specific match

        Args:
            home_team: Home team name
            away_team: Away team name
            sport: Sport key

        Returns:
            Match with odds or None
        """
        matches = self.get_upcoming_matches(sport=sport, days_ahead=30)

        # Find matching fixture
        for match in matches:
            if (self._normalize_team_name(match['home_team']) == self._normalize_team_name(home_team) and
                self._normalize_team_name(match['away_team']) == self._normalize_team_name(away_team)):
                return match

        return None

    def _normalize_team_name(self, name: str) -> str:
        """Normalize team name for matching"""
        return name.lower().strip().replace(' ', '')

    def _parse_match_time(self, time_str: str) -> Optional[datetime]:
        """Parse match time from various formats"""
        if not time_str:
            return None

        from datetime import timezone

        try:
            # ISO format from Odds API (e.g., "2024-02-11T15:00:00Z")
            if 'Z' in time_str or '+' in time_str:
                dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                # Ensure it's timezone-aware
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
        except:
            pass

        try:
            # DD/MM/YYYY from football-data.co.uk
            dt = datetime.strptime(time_str, '%d/%m/%Y')
            # Make timezone-aware (assume UTC)
            return dt.replace(tzinfo=timezone.utc)
        except:
            pass

        try:
            # DD/MM/YY
            dt = datetime.strptime(time_str, '%d/%m/%y')
            return dt.replace(tzinfo=timezone.utc)
        except:
            pass

        return None

    def get_quota_usage(self) -> Optional[Dict]:
        """Check API quota usage for The Odds API"""
        if not self.odds_api_key:
            return None

        try:
            # The API returns quota info in response headers
            base_url = "https://api.the-odds-api.com/v4"
            url = f"{base_url}/sports"
            params = {'apiKey': self.odds_api_key}

            response = requests.get(url, params=params, timeout=10)

            return {
                'requests_remaining': response.headers.get('x-requests-remaining'),
                'requests_used': response.headers.get('x-requests-used'),
                'requests_limit': response.headers.get('x-requests-limit')
            }
        except Exception as e:
            print(f"Error checking quota: {e}")
            return None

    def get_current_season_results(self, league: str = 'E0') -> List[Dict]:
        """
        Get all completed matches from current season
        Useful for calculating current form and league positions
        """
        matches = self._fetch_from_football_data_uk()

        # Filter by league
        return [m for m in matches if m.get('league') == league and
                pd.notna(m.get('home_goals'))]


# Convenience functions
def get_premier_league_fixtures(days_ahead: int = 7) -> List[Dict]:
    """Get upcoming Premier League fixtures"""
    fetcher = LiveFixturesFetcher()
    return fetcher.get_upcoming_matches('soccer_epl', days_ahead)


def get_live_odds(home_team: str, away_team: str) -> Optional[Dict]:
    """Get live odds for a specific match"""
    fetcher = LiveFixturesFetcher()
    return fetcher.get_live_odds_for_match(home_team, away_team)
