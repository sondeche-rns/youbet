"""
Match Context Builder

Builds MatchContext from various data sources with caching and graceful fallbacks.

Responsibilities:
- Extract defensive styles from possession data
- Load manager information from database
- Query H2H records from historical data
- Calculate season statistics (possession, away draws, etc.)
- Handle missing data gracefully with defaults

Author: AI Betting Algorithm v2.0
Date: 2026-02-11
"""

from typing import Dict, Optional, List
from pathlib import Path
import pandas as pd
import json
from datetime import datetime, timedelta

from .models import (
    MatchContext, DefensiveStyle, ManagerInfo, H2HRecord,
    create_neutral_context
)


class MatchContextBuilder:
    """
    Builds MatchContext from various data sources.

    Handles missing data gracefully with defaults and caching for performance.
    """

    def __init__(self, historical_data: Optional[pd.DataFrame] = None):
        """
        Initialize context builder.

        Args:
            historical_data: DataFrame with historical matches for calculating
                           season averages, H2H records, etc. Optional.
        """
        self.historical_data = historical_data
        self.h2h_cache = {}   # Cache for H2H lookups
        self.season_stats_cache = {}  # Cache for season stats
        self.manager_db = {}  # Manager database

        # Load manager database if available
        self._load_manager_database()

    def _load_manager_database(self):
        """Load manager database from JSON file"""
        try:
            manager_file = Path(__file__).parent.parent / 'data' / 'managers.json'
            if manager_file.exists():
                with open(manager_file, 'r') as f:
                    data = json.load(f)
                    # Convert to ManagerInfo objects
                    for team, info in data.items():
                        appointment_date = info['appointmentDate']
                        games_managed = self._calculate_games_managed(appointment_date)

                        self.manager_db[team] = ManagerInfo(
                            name=info['manager'],
                            appointmentDate=appointment_date,
                            gamesManaged=games_managed,
                            results=info.get('results', []),
                            isInterim=info.get('isInterim', False)
                        )
        except Exception as e:
            print(f"[Context Builder] Could not load manager database: {e}")
            self.manager_db = {}

    def _calculate_games_managed(self, appointment_date_str: str) -> int:
        """
        Calculate games managed since appointment.

        Rough estimate: ~1 game per week since appointment.
        """
        try:
            appointment = datetime.fromisoformat(appointment_date_str)
            now = datetime.now()
            weeks_elapsed = (now - appointment).days / 7
            # Estimate: ~38 games per season, ~40 weeks/season = ~1 game/week
            return int(weeks_elapsed)
        except:
            return 50  # Default to established manager (>50 games)

    def build_context(self, match_data: Dict) -> MatchContext:
        """
        Build complete MatchContext from match_data.

        Args:
            match_data: Dict with match information (teams, stats, etc.)

        Returns:
            MatchContext with all available data populated
        """
        # Extract team names (handle different key formats)
        home_team = match_data.get('homeTeam', match_data.get('home_team', ''))
        away_team = match_data.get('awayTeam', match_data.get('away_team', ''))

        if not home_team or not away_team:
            # Missing basic data, return neutral context
            return create_neutral_context()

        # Derive defensive styles from possession
        home_poss = match_data.get('home_possession', match_data.get('homePossession', 50))
        away_poss = match_data.get('away_possession', match_data.get('awayPossession', 50))

        home_style = self._classify_defensive_style(home_poss)
        away_style = self._classify_defensive_style(away_poss)

        # Build manager info (with fallback)
        home_manager = self._get_manager_info(home_team)
        away_manager = self._get_manager_info(away_team)

        # Get league positions
        home_pos = match_data.get('home_position', match_data.get('homePosition', 10))
        away_pos = match_data.get('away_position', match_data.get('awayPosition', 10))

        # Get recent form
        home_form = self._parse_form(match_data.get('home_form', match_data.get('homeForm', 'DDDDD')))
        away_form = self._parse_form(match_data.get('away_form', match_data.get('awayForm', 'DDDDD')))

        # Build H2H record (with fallback)
        h2h = self._get_h2h_record(home_team, away_team, home_pos, away_pos)

        # Calculate season stats (from historical data)
        home_season_stats = self._calculate_season_stats(home_team, 'home')
        away_season_stats = self._calculate_season_stats(away_team, 'away')

        return MatchContext(
            homeDefensiveStyle=home_style,
            awayDefensiveStyle=away_style,
            homeManagerInfo=home_manager,
            awayManagerInfo=away_manager,
            homeLeaguePosition=int(home_pos),
            awayLeaguePosition=int(away_pos),
            homeRecentForm=home_form,
            awayRecentForm=away_form,
            h2hRecord=h2h,
            homeSeasonStats=home_season_stats,
            awaySeasonStats=away_season_stats
        )

    def _classify_defensive_style(self, avg_possession: float) -> DefensiveStyle:
        """
        Classify defensive style from average possession.

        Args:
            avg_possession: Average possession percentage (0-100)

        Returns:
            DefensiveStyle enum
        """
        if avg_possession > 55:
            return DefensiveStyle.HIGH_PRESS
        elif avg_possession >= 45:
            return DefensiveStyle.BALANCED
        else:
            return DefensiveStyle.LOW_BLOCK

    def _parse_form(self, form_str: str) -> List[str]:
        """
        Parse form string into list.

        Args:
            form_str: Form as string like "WWDLW"

        Returns:
            List of results ['W', 'W', 'D', 'L', 'W']
        """
        if not form_str or not isinstance(form_str, str):
            return ['D', 'D', 'D', 'D', 'D']

        # Convert to list, filter to only W/D/L
        results = [c.upper() for c in form_str if c.upper() in ['W', 'D', 'L']]
        return results if results else ['D', 'D', 'D', 'D', 'D']

    def _get_manager_info(self, team: str) -> Optional[ManagerInfo]:
        """
        Get manager info for team.

        Args:
            team: Team name

        Returns:
            ManagerInfo if available, None otherwise
        """
        return self.manager_db.get(team, None)

    def _get_h2h_record(self, home_team: str, away_team: str,
                       home_pos: int, away_pos: int) -> Optional[H2HRecord]:
        """
        Get H2H record from historical data.

        Args:
            home_team: Home team name
            away_team: Away team name
            home_pos: Home team league position
            away_pos: Away team league position

        Returns:
            H2HRecord if sufficient data, None otherwise
        """
        if self.historical_data is None or len(self.historical_data) == 0:
            return None

        cache_key = f"{home_team}_{away_team}"
        if cache_key in self.h2h_cache:
            return self.h2h_cache[cache_key]

        try:
            # Query historical data for H2H matches (any venue)
            h2h_matches = self.historical_data[
                ((self.historical_data['home_team'] == home_team) &
                 (self.historical_data['away_team'] == away_team)) |
                ((self.historical_data['home_team'] == away_team) &
                 (self.historical_data['away_team'] == home_team))
            ].tail(10)  # Last 10 H2H matches

            if len(h2h_matches) < 3:
                return None  # Insufficient data

            # Build results list
            results = []
            for _, match in h2h_matches.iterrows():
                results.append({
                    'date': str(match['Date']) if 'Date' in match else '',
                    'homeScore': int(match['home_goals']) if 'home_goals' in match else 0,
                    'awayScore': int(match['away_goals']) if 'away_goals' in match else 0,
                    'homeTeam': str(match['home_team']),
                    'awayTeam': str(match['away_team'])
                })

            # Calculate anomaly (weaker team unbeaten streak)
            weaker_team_streak = self._calculate_weaker_team_streak(
                results, home_team, away_team, home_pos, away_pos
            )
            anomaly_triggered = weaker_team_streak >= 3

            h2h = H2HRecord(
                homeTeam=home_team,
                awayTeam=away_team,
                results=results,
                weakerTeamUnbeatenStreak=weaker_team_streak,
                anomalyTriggered=anomaly_triggered
            )

            self.h2h_cache[cache_key] = h2h
            return h2h

        except Exception as e:
            print(f"[Context Builder] Error building H2H record: {e}")
            return None

    def _calculate_weaker_team_streak(self, results: List[Dict],
                                     home_team: str, away_team: str,
                                     home_pos: int, away_pos: int) -> int:
        """
        Calculate consecutive unbeaten streak for weaker team in H2H.

        Args:
            results: List of H2H results
            home_team: Current home team
            away_team: Current away team
            home_pos: Home team league position
            away_pos: Away team league position

        Returns:
            Consecutive games without loss for weaker team
        """
        # Determine weaker team (higher position number = weaker)
        weaker_is_home = home_pos > away_pos
        weaker_team = home_team if weaker_is_home else away_team

        # Count consecutive games from most recent where weaker team didn't lose
        streak = 0
        for result in reversed(results):  # Most recent first
            # Determine if weaker team was home or away in this H2H match
            if result['homeTeam'] == weaker_team:
                # Weaker team was home
                if result['homeScore'] >= result['awayScore']:
                    streak += 1  # Win or draw
                else:
                    break  # Loss
            else:
                # Weaker team was away
                if result['awayScore'] >= result['homeScore']:
                    streak += 1  # Win or draw
                else:
                    break  # Loss

        return streak

    def _calculate_season_stats(self, team: str, perspective: str = 'home') -> Optional[Dict]:
        """
        Calculate season-level statistics for team.

        Args:
            team: Team name
            perspective: 'home' or 'away' (for away-specific stats)

        Returns:
            Dict with season stats or None if insufficient data
        """
        if self.historical_data is None or len(self.historical_data) == 0:
            return None

        cache_key = f"{team}_{perspective}"
        if cache_key in self.season_stats_cache:
            return self.season_stats_cache[cache_key]

        try:
            # Get all matches for team this season
            team_matches = self.historical_data[
                (self.historical_data['home_team'] == team) |
                (self.historical_data['away_team'] == team)
            ]

            if len(team_matches) < 5:
                return None  # Need minimum sample size

            # Separate home and away matches
            home_matches = team_matches[team_matches['home_team'] == team]
            away_matches = team_matches[team_matches['away_team'] == team]

            # Calculate possession average
            if 'home_possession' in team_matches.columns:
                home_poss = home_matches['home_possession'].mean() if len(home_matches) > 0 else 50
                away_poss = away_matches['away_possession'].mean() if len(away_matches) > 0 else 50
                avg_possession = (home_poss + away_poss) / 2
            else:
                avg_possession = 50.0

            # Calculate away-specific stats
            away_draws = 0
            total_away_games = len(away_matches)

            if total_away_games > 0:
                for _, match in away_matches.iterrows():
                    if match['home_goals'] == match['away_goals']:
                        away_draws += 1

            away_draw_rate = away_draws / total_away_games if total_away_games > 0 else 0.25

            # Calculate goals per game
            home_goals = home_matches['home_goals'].sum() if len(home_matches) > 0 else 0
            away_goals = away_matches['away_goals'].sum() if len(away_matches) > 0 else 0
            total_games = len(team_matches)
            goals_per_game = (home_goals + away_goals) / total_games if total_games > 0 else 1.2

            stats = {
                'avgPossession': float(avg_possession),
                'awayDraws': int(away_draws),
                'totalAwayGames': int(total_away_games),
                'awayDrawRate': float(away_draw_rate),
                'goalsPerGame': float(goals_per_game),
                'homeGames': len(home_matches),
                'awayGames': len(away_matches),
                'totalGames': total_games
            }

            self.season_stats_cache[cache_key] = stats
            return stats

        except Exception as e:
            print(f"[Context Builder] Error calculating season stats for {team}: {e}")
            return None

    def clear_caches(self):
        """Clear all caches (useful for testing or when data updated)"""
        self.h2h_cache = {}
        self.season_stats_cache = {}

    def update_manager_info(self, team: str, manager_info: ManagerInfo):
        """
        Update manager information for a team.

        Args:
            team: Team name
            manager_info: New ManagerInfo object
        """
        self.manager_db[team] = manager_info
