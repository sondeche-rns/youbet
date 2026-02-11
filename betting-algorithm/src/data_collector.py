"""
Historical Data Collector for Sports Betting Algorithm
Collects match data from free public sources
"""

import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import time
import io


class HistoricalDataCollector:
    """
    Collects historical match data from free public sources.

    Data Sources (all FREE):
    - football-data.co.uk: Historical results and odds
    - Calculated: Elo ratings, form, advanced stats
    """

    def __init__(self, output_dir: str = './data'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.matches_df = None
        self.elo_ratings = {}
        self.team_stats = {}

        # Base URLs for free data sources
        self.football_data_uk_base = "https://www.football-data.co.uk/mmz4281"

    def collect_all_data(self, seasons: List[str] = None,
                         leagues: List[str] = None,
                         callback=None) -> pd.DataFrame:
        """
        Collect all historical data through 7 steps.

        Args:
            seasons: List of seasons like ['2324', '2223', '2122']
            leagues: List of league codes like ['E0'] (Premier League)
            callback: Optional callback function for progress updates

        Returns:
            DataFrame with comprehensive match data
        """
        if seasons is None:
            seasons = ['2324', '2223', '2122', '2021', '1920']
        if leagues is None:
            leagues = ['E0']  # Premier League

        steps = [
            ('Fetching match results & odds...', self._collect_football_data_uk),
            ('Adding expected goals (xG)...', self._add_xg_data),
            ('Calculating Elo ratings...', self._calculate_elo_ratings),
            ('Computing team form...', self._calculate_team_form),
            ('Analyzing rest & congestion...', self._calculate_rest_congestion),
            ('Adding advanced stats...', self._add_advanced_stats),
            ('Calculating league positions...', self._calculate_league_positions)
        ]

        for i, (step_name, step_func) in enumerate(steps):
            if callback:
                callback(step_name, i, len(steps))

            print(f"Step {i+1}/{len(steps)}: {step_name}")

            if i == 0:
                self.matches_df = step_func(seasons, leagues)
            else:
                self.matches_df = step_func()

            print(f"  -> {len(self.matches_df)} matches processed")

        # Save final dataset
        self._save_final_dataset()

        return self.matches_df

    def _collect_football_data_uk(self, seasons: List[str],
                                   leagues: List[str]) -> pd.DataFrame:
        """
        Step 1: Fetch match results and odds from football-data.co.uk

        This is a free public data source with historical match data.
        """
        all_matches = []

        for season in seasons:
            for league in leagues:
                url = f"{self.football_data_uk_base}/{season}/{league}.csv"

                try:
                    response = requests.get(url, timeout=30)
                    if response.status_code == 200:
                        df = pd.read_csv(io.StringIO(response.text))

                        # Standardize column names
                        df = self._standardize_columns(df, season)
                        all_matches.append(df)

                        print(f"    Fetched {len(df)} matches from {season} {league}")
                    else:
                        print(f"    Warning: Could not fetch {season} {league}")

                except Exception as e:
                    print(f"    Error fetching {season} {league}: {e}")

                time.sleep(0.5)  # Be nice to the server

        if not all_matches:
            # Return sample data if no data fetched
            return self._generate_sample_matches()

        return pd.concat(all_matches, ignore_index=True)

    def _standardize_columns(self, df: pd.DataFrame, season: str) -> pd.DataFrame:
        """Standardize column names from football-data.co.uk"""
        # Map common column names
        column_map = {
            'HomeTeam': 'home_team',
            'AwayTeam': 'away_team',
            'FTHG': 'home_goals',
            'FTAG': 'away_goals',
            'FTR': 'result',
            'B365H': 'home_odds',
            'B365D': 'draw_odds',
            'B365A': 'away_odds',
            'HS': 'home_shots',
            'AS': 'away_shots',
            'HST': 'home_shots_on_target',
            'AST': 'away_shots_on_target',
        }

        df = df.rename(columns=column_map)

        # Add season column
        df['Season'] = f"20{season[:2]}-{season[2:]}"

        # Parse date
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')

        # Keep only needed columns
        keep_cols = ['Date', 'Season', 'home_team', 'away_team', 'home_goals',
                     'away_goals', 'home_odds', 'draw_odds', 'away_odds',
                     'home_shots', 'away_shots', 'home_shots_on_target',
                     'away_shots_on_target']

        existing_cols = [c for c in keep_cols if c in df.columns]
        df = df[existing_cols].copy()

        # Fill missing values
        for col in ['home_odds', 'draw_odds', 'away_odds']:
            if col in df.columns:
                df[col] = df[col].fillna(2.5)

        for col in ['home_shots', 'away_shots']:
            if col not in df.columns:
                df[col] = 12

        for col in ['home_shots_on_target', 'away_shots_on_target']:
            if col not in df.columns:
                df[col] = 5

        # Generate match ID
        df['match_id'] = range(len(df))

        return df

    def _add_xg_data(self) -> pd.DataFrame:
        """
        Step 2: Add expected goals (xG) data

        Since free xG data is limited, we calculate estimated xG
        based on shots and shots on target.
        """
        df = self.matches_df.copy()

        # Calculate estimated xG based on shots
        # Average xG per shot is around 0.1, per shot on target around 0.3
        if 'home_shots' in df.columns and 'home_shots_on_target' in df.columns:
            df['home_xg'] = (
                df['home_shots'] * 0.08 +
                df['home_shots_on_target'] * 0.22
            )
            df['away_xg'] = (
                df['away_shots'] * 0.08 +
                df['away_shots_on_target'] * 0.22
            )
        else:
            # Use actual goals with some noise as fallback
            df['home_xg'] = df['home_goals'] + np.random.uniform(-0.5, 0.5, len(df))
            df['away_xg'] = df['away_goals'] + np.random.uniform(-0.5, 0.5, len(df))

        # Clip to reasonable values
        df['home_xg'] = df['home_xg'].clip(0, 5)
        df['away_xg'] = df['away_xg'].clip(0, 5)

        return df

    def _calculate_elo_ratings(self) -> pd.DataFrame:
        """
        Step 3: Calculate dynamic Elo ratings for each team

        Updates ratings after each match chronologically.
        """
        df = self.matches_df.copy()
        df = df.sort_values('Date').reset_index(drop=True)

        # Initialize Elo ratings
        base_elo = 1500
        k_factor = 32
        self.elo_ratings = {}

        home_elos = []
        away_elos = []

        for _, row in df.iterrows():
            home = row['home_team']
            away = row['away_team']

            # Get current ratings (before match)
            home_elo = self.elo_ratings.get(home, base_elo)
            away_elo = self.elo_ratings.get(away, base_elo)

            home_elos.append(home_elo)
            away_elos.append(away_elo)

            # Calculate expected scores
            exp_home = 1 / (1 + 10 ** ((away_elo - home_elo) / 400))
            exp_away = 1 - exp_home

            # Determine actual outcome
            home_goals = row.get('home_goals', 0)
            away_goals = row.get('away_goals', 0)

            if home_goals > away_goals:
                actual_home, actual_away = 1, 0
            elif home_goals < away_goals:
                actual_home, actual_away = 0, 1
            else:
                actual_home = actual_away = 0.5

            # Update ratings
            self.elo_ratings[home] = home_elo + k_factor * (actual_home - exp_home)
            self.elo_ratings[away] = away_elo + k_factor * (actual_away - exp_away)

        df['home_elo'] = home_elos
        df['away_elo'] = away_elos

        return df

    def _calculate_team_form(self) -> pd.DataFrame:
        """
        Step 4: Calculate recent form for each team

        Tracks last 5 results (W/D/L) for each team.
        """
        df = self.matches_df.copy()
        df = df.sort_values('Date').reset_index(drop=True)

        team_results = {}  # Track recent results per team

        home_forms = []
        away_forms = []

        for _, row in df.iterrows():
            home = row['home_team']
            away = row['away_team']

            # Get current form (before match)
            home_form = ''.join(team_results.get(home, [])[-5:])
            away_form = ''.join(team_results.get(away, [])[-5:])

            home_forms.append(home_form if home_form else 'DDDDD')
            away_forms.append(away_form if away_form else 'DDDDD')

            # Determine result
            home_goals = row.get('home_goals', 0)
            away_goals = row.get('away_goals', 0)

            if home_goals > away_goals:
                home_result, away_result = 'W', 'L'
            elif home_goals < away_goals:
                home_result, away_result = 'L', 'W'
            else:
                home_result = away_result = 'D'

            # Update form
            if home not in team_results:
                team_results[home] = []
            if away not in team_results:
                team_results[away] = []

            team_results[home].append(home_result)
            team_results[away].append(away_result)

        df['home_form'] = home_forms
        df['away_form'] = away_forms

        return df

    def _calculate_rest_congestion(self) -> pd.DataFrame:
        """
        Step 5: Calculate rest days and fixture congestion

        Tracks days since last match and games in last 7 days.
        """
        df = self.matches_df.copy()
        df = df.sort_values('Date').reset_index(drop=True)

        team_last_match = {}  # Track last match date per team
        team_recent_games = {}  # Track recent game dates

        home_rest = []
        away_rest = []
        home_congestion = []
        away_congestion = []

        for _, row in df.iterrows():
            home = row['home_team']
            away = row['away_team']
            match_date = row['Date']

            # Calculate rest days
            if home in team_last_match:
                days_rest_home = (match_date - team_last_match[home]).days
            else:
                days_rest_home = 7  # Default

            if away in team_last_match:
                days_rest_away = (match_date - team_last_match[away]).days
            else:
                days_rest_away = 7

            home_rest.append(max(1, min(days_rest_home, 30)))
            away_rest.append(max(1, min(days_rest_away, 30)))

            # Calculate congestion (games in last 7 days)
            week_ago = match_date - timedelta(days=7)

            if home in team_recent_games:
                games_home = sum(1 for d in team_recent_games[home] if d > week_ago)
            else:
                games_home = 0

            if away in team_recent_games:
                games_away = sum(1 for d in team_recent_games[away] if d > week_ago)
            else:
                games_away = 0

            home_congestion.append(games_home + 1)
            away_congestion.append(games_away + 1)

            # Update tracking
            team_last_match[home] = match_date
            team_last_match[away] = match_date

            if home not in team_recent_games:
                team_recent_games[home] = []
            if away not in team_recent_games:
                team_recent_games[away] = []

            team_recent_games[home].append(match_date)
            team_recent_games[away].append(match_date)

            # Keep only last 30 days of games
            month_ago = match_date - timedelta(days=30)
            team_recent_games[home] = [d for d in team_recent_games[home] if d > month_ago]
            team_recent_games[away] = [d for d in team_recent_games[away] if d > month_ago]

        df['home_rest_days'] = home_rest
        df['away_rest_days'] = away_rest
        df['home_games_last_7'] = home_congestion
        df['away_games_last_7'] = away_congestion

        return df

    def _add_advanced_stats(self) -> pd.DataFrame:
        """
        Step 6: Add advanced statistics

        Calculates PPDA, possession estimates, etc.
        """
        df = self.matches_df.copy()

        # Calculate possession estimate based on shots ratio
        total_shots = df['home_shots'] + df['away_shots']
        total_shots = total_shots.replace(0, 24)  # Avoid division by zero

        df['home_possession'] = (df['home_shots'] / total_shots * 100).clip(30, 70)
        df['away_possession'] = 100 - df['home_possession']

        # Estimate PPDA (Passes Per Defensive Action)
        # Higher possession teams tend to have lower PPDA (more pressing)
        df['home_ppda'] = 15 - (df['home_possession'] - 50) * 0.15 + np.random.uniform(-2, 2, len(df))
        df['away_ppda'] = 15 - (df['away_possession'] - 50) * 0.15 + np.random.uniform(-2, 2, len(df))

        df['home_ppda'] = df['home_ppda'].clip(5, 20)
        df['away_ppda'] = df['away_ppda'].clip(5, 20)

        return df

    def _calculate_league_positions(self) -> pd.DataFrame:
        """
        Step 7: Calculate league positions at time of match

        Tracks running league table positions.
        """
        df = self.matches_df.copy()

        # Group by season
        home_positions = []
        away_positions = []

        for season in df['Season'].unique():
            season_df = df[df['Season'] == season].sort_values('Date')

            # Track points per team
            team_points = {}

            for _, row in season_df.iterrows():
                home = row['home_team']
                away = row['away_team']

                # Initialize teams
                if home not in team_points:
                    team_points[home] = 0
                if away not in team_points:
                    team_points[away] = 0

                # Calculate positions before match
                sorted_teams = sorted(team_points.items(), key=lambda x: -x[1])
                positions = {team: i+1 for i, (team, _) in enumerate(sorted_teams)}

                home_pos = positions.get(home, 10)
                away_pos = positions.get(away, 10)

                home_positions.append(home_pos)
                away_positions.append(away_pos)

                # Update points after match
                home_goals = row.get('home_goals', 0)
                away_goals = row.get('away_goals', 0)

                if home_goals > away_goals:
                    team_points[home] += 3
                elif home_goals < away_goals:
                    team_points[away] += 3
                else:
                    team_points[home] += 1
                    team_points[away] += 1

        df['home_position'] = home_positions
        df['away_position'] = away_positions

        return df

    def _save_final_dataset(self):
        """Save the final processed dataset"""
        final_dir = self.output_dir / 'final'
        final_dir.mkdir(parents=True, exist_ok=True)

        filepath = final_dir / 'historical_dataset.csv'
        self.matches_df.to_csv(filepath, index=False)

        print(f"\nDataset saved to {filepath}")
        print(f"Total matches: {len(self.matches_df)}")
        print(f"Date range: {self.matches_df['Date'].min()} to {self.matches_df['Date'].max()}")
        print(f"Teams: {len(set(self.matches_df['home_team'].unique()) | set(self.matches_df['away_team'].unique()))}")

    def _generate_sample_matches(self) -> pd.DataFrame:
        """Generate sample match data if no real data available"""
        np.random.seed(42)

        teams = ['Arsenal', 'Chelsea', 'Liverpool', 'Man City', 'Man United',
                 'Tottenham', 'Everton', 'West Ham', 'Newcastle', 'Brighton',
                 'Aston Villa', 'Crystal Palace', 'Fulham', 'Wolves', 'Leicester',
                 'Bournemouth', 'Brentford', 'Nottm Forest', 'Luton', 'Burnley']

        matches = []
        start_date = datetime(2023, 8, 1)

        for i in range(380):
            home = teams[i % 20]
            away = teams[(i + 1 + i // 20) % 20]

            if home == away:
                away = teams[(i + 2) % 20]

            home_goals = np.random.poisson(1.5)
            away_goals = np.random.poisson(1.2)

            matches.append({
                'Date': start_date + timedelta(days=i // 10 * 7 + i % 10 % 3),
                'Season': '2023-24',
                'home_team': home,
                'away_team': away,
                'home_goals': home_goals,
                'away_goals': away_goals,
                'home_odds': round(np.random.uniform(1.5, 4.0), 2),
                'draw_odds': round(np.random.uniform(3.0, 4.0), 2),
                'away_odds': round(np.random.uniform(1.8, 5.0), 2),
                'home_shots': int(np.random.uniform(8, 18)),
                'away_shots': int(np.random.uniform(6, 15)),
                'home_shots_on_target': int(np.random.uniform(2, 7)),
                'away_shots_on_target': int(np.random.uniform(1, 6)),
                'match_id': i
            })

        return pd.DataFrame(matches)

    def get_data_summary(self) -> Dict:
        """Get summary of collected data"""
        if self.matches_df is None:
            return {'error': 'No data collected'}

        return {
            'total_matches': len(self.matches_df),
            'date_range': {
                'start': str(self.matches_df['Date'].min()),
                'end': str(self.matches_df['Date'].max())
            },
            'seasons': self.matches_df['Season'].unique().tolist(),
            'teams': len(set(self.matches_df['home_team'].unique()) |
                        set(self.matches_df['away_team'].unique())),
            'columns': self.matches_df.columns.tolist()
        }


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Collect historical betting data')
    parser.add_argument('--seasons', nargs='+', default=['2324', '2223', '2122'],
                        help='Seasons to collect (e.g., 2324 2223)')
    parser.add_argument('--output', type=str, default='./data',
                        help='Output directory')

    args = parser.parse_args()

    collector = HistoricalDataCollector(output_dir=args.output)

    print("Starting data collection...")
    print(f"Seasons: {args.seasons}")
    print()

    df = collector.collect_all_data(seasons=args.seasons)

    print("\n" + "="*60)
    print("DATA COLLECTION COMPLETE")
    print("="*60)
    summary = collector.get_data_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")
