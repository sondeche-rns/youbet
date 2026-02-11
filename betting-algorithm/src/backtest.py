"""
Backtesting Engine for Sports Betting Algorithm
Comprehensive testing framework with detailed performance metrics
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json
from pathlib import Path

from .algorithm import ProfessionalBettingAlgorithm
from .utils import calculate_kelly_stake, calculate_roi, PerformanceTracker


class BacktestEngine:
    """
    Comprehensive backtesting engine for evaluating betting algorithms.

    Features:
    - Chronological match processing
    - Kelly Criterion stake sizing
    - Detailed performance tracking
    - Multiple metric calculations
    - Export to JSON/CSV
    """

    def __init__(self, algorithm: ProfessionalBettingAlgorithm = None,
                 initial_bankroll: float = 1000.0,
                 kelly_fraction: float = 0.25,
                 max_stake_pct: float = 5.0):
        """
        Initialize the backtest engine.

        Args:
            algorithm: ProfessionalBettingAlgorithm instance
            initial_bankroll: Starting bankroll amount
            kelly_fraction: Fraction of Kelly stake to use (0.25 = quarter Kelly)
            max_stake_pct: Maximum stake as percentage of bankroll
        """
        self.algorithm = algorithm or ProfessionalBettingAlgorithm('football')
        self.initial_bankroll = initial_bankroll
        self.kelly_fraction = kelly_fraction
        self.max_stake_pct = max_stake_pct

        # State tracking
        self.bankroll = initial_bankroll
        self.results = []
        self.predictions = []
        self.equity_curve = [initial_bankroll]
        self.tracker = PerformanceTracker()

    def load_historical_data(self, filepath: str = None) -> pd.DataFrame:
        """Load historical match data for backtesting"""
        if filepath is None:
            filepath = Path('./data/final/historical_dataset.csv')

        if not Path(filepath).exists():
            # Generate sample data if none exists
            return self._generate_sample_data()

        df = pd.read_csv(filepath)

        # Ensure required columns exist
        required_cols = ['Date', 'home_team', 'away_team', 'home_goals', 'away_goals']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        # Sort by date
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date').reset_index(drop=True)

        return df

    def _generate_sample_data(self) -> pd.DataFrame:
        """Generate sample historical data for testing"""
        np.random.seed(42)

        teams = ['Arsenal', 'Chelsea', 'Liverpool', 'Man City', 'Man United',
                 'Tottenham', 'Everton', 'West Ham', 'Newcastle', 'Brighton',
                 'Aston Villa', 'Crystal Palace', 'Fulham', 'Wolves', 'Leicester',
                 'Bournemouth', 'Brentford', 'Nottm Forest', 'Luton', 'Burnley']

        matches = []
        start_date = datetime(2023, 8, 1)

        for i in range(380):  # Full season
            home = teams[i % 20]
            away = teams[(i + 1 + i // 20) % 20]

            if home == away:
                away = teams[(i + 2) % 20]

            # Generate realistic scores
            home_lambda = 1.5 + np.random.uniform(-0.3, 0.5)
            away_lambda = 1.2 + np.random.uniform(-0.3, 0.3)

            home_goals = np.random.poisson(home_lambda)
            away_goals = np.random.poisson(away_lambda)

            # Generate realistic odds
            if home_goals > away_goals:
                home_odds = np.random.uniform(1.5, 2.5)
                draw_odds = np.random.uniform(3.0, 4.0)
                away_odds = np.random.uniform(3.5, 6.0)
            elif away_goals > home_goals:
                home_odds = np.random.uniform(2.5, 4.5)
                draw_odds = np.random.uniform(3.0, 4.0)
                away_odds = np.random.uniform(1.8, 2.8)
            else:
                home_odds = np.random.uniform(2.2, 3.2)
                draw_odds = np.random.uniform(3.0, 3.5)
                away_odds = np.random.uniform(2.5, 3.5)

            matches.append({
                'Date': (start_date + pd.Timedelta(days=i // 10 * 7 + i % 10 % 3)).strftime('%Y-%m-%d'),
                'Season': '2023-24',
                'home_team': home,
                'away_team': away,
                'home_goals': home_goals,
                'away_goals': away_goals,
                'home_xg': home_lambda,
                'away_xg': away_lambda,
                'home_shots': int(np.random.uniform(8, 18)),
                'away_shots': int(np.random.uniform(6, 15)),
                'home_shots_on_target': int(np.random.uniform(2, 7)),
                'away_shots_on_target': int(np.random.uniform(1, 6)),
                'home_possession': np.random.uniform(40, 65),
                'away_possession': 100 - np.random.uniform(40, 65),
                'home_ppda': np.random.uniform(7, 15),
                'away_ppda': np.random.uniform(7, 15),
                'home_elo': 1500 + np.random.uniform(-200, 300),
                'away_elo': 1500 + np.random.uniform(-200, 300),
                'home_form': ''.join(np.random.choice(['W', 'D', 'L'], 5)),
                'away_form': ''.join(np.random.choice(['W', 'D', 'L'], 5)),
                'home_rest_days': int(np.random.uniform(3, 10)),
                'away_rest_days': int(np.random.uniform(3, 10)),
                'home_games_last_7': int(np.random.uniform(1, 3)),
                'away_games_last_7': int(np.random.uniform(1, 3)),
                'home_position': int(np.random.uniform(1, 20)),
                'away_position': int(np.random.uniform(1, 20)),
                'home_odds': round(home_odds, 2),
                'draw_odds': round(draw_odds, 2),
                'away_odds': round(away_odds, 2)
            })

        return pd.DataFrame(matches)

    def run_backtest(self, data: pd.DataFrame,
                     start_date: str = None,
                     end_date: str = None) -> Dict:
        """
        Run backtest on historical data.

        Args:
            data: DataFrame with historical match data
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)

        Returns:
            Dict with comprehensive backtest results
        """
        # Reset state
        self.bankroll = self.initial_bankroll
        self.results = []
        self.predictions = []
        self.equity_curve = [self.initial_bankroll]
        self.tracker = PerformanceTracker()

        # Filter by date if specified
        if start_date:
            data = data[data['Date'] >= start_date]
        if end_date:
            data = data[data['Date'] <= end_date]

        # Process each match chronologically
        for idx, row in data.iterrows():
            result = self._process_match(row)
            if result:
                self.results.append(result)
                self.equity_curve.append(self.bankroll)

        # Generate summary
        summary = self._generate_summary()

        # Save results
        self._save_results(summary)

        return summary

    def _process_match(self, match: pd.Series) -> Optional[Dict]:
        """Process a single match and return result"""
        # Build match data for prediction
        match_data = {
            'homeTeam': match.get('home_team', 'Home'),
            'awayTeam': match.get('away_team', 'Away'),
            'date': str(match.get('Date', '')),
            'home_xg': match.get('home_xg', 1.5),
            'away_xg': match.get('away_xg', 1.2),
            'home_shots': match.get('home_shots', 12),
            'away_shots': match.get('away_shots', 10),
            'home_shots_on_target': match.get('home_shots_on_target', 5),
            'away_shots_on_target': match.get('away_shots_on_target', 4),
            'home_possession': match.get('home_possession', 50),
            'away_possession': match.get('away_possession', 50),
            'home_ppda': match.get('home_ppda', 10),
            'away_ppda': match.get('away_ppda', 10),
            'home_elo': match.get('home_elo', 1500),
            'away_elo': match.get('away_elo', 1500),
            'home_form': match.get('home_form', 'WWDLW'),
            'away_form': match.get('away_form', 'WDLWD'),
            'home_rest_days': match.get('home_rest_days', 7),
            'away_rest_days': match.get('away_rest_days', 7),
            'home_games_last_7': match.get('home_games_last_7', 1),
            'away_games_last_7': match.get('away_games_last_7', 1),
            'home_position': match.get('home_position', 10),
            'away_position': match.get('away_position', 10),
            'homeOdds': match.get('home_odds', 2.0),
            'drawOdds': match.get('draw_odds', 3.5),
            'awayOdds': match.get('away_odds', 3.5)
        }

        # Get prediction
        prediction = self.algorithm.predict_match(match_data)
        self.predictions.append(prediction)

        # Determine actual result
        home_goals = match.get('home_goals', 0)
        away_goals = match.get('away_goals', 0)

        if home_goals > away_goals:
            actual_result = 'Home Win'
        elif away_goals > home_goals:
            actual_result = 'Away Win'
        else:
            actual_result = 'Draw'

        # Get recommendation
        recommendation = prediction.get('recommendation', {})
        predicted_outcome = recommendation.get('outcome', '')
        stake_pct = recommendation.get('stakePercentage', 0) / 100
        expected_value = recommendation.get('expectedValue', 0)

        # Calculate if we should bet
        should_bet = stake_pct > 0 and expected_value > 0

        # Simulate bet
        pnl = 0.0
        bet_won = False
        stake_amount = 0.0

        if should_bet and self.bankroll > 0:
            stake_amount = min(self.bankroll * stake_pct,
                              self.bankroll * self.max_stake_pct / 100)

            # Get odds for predicted outcome
            if predicted_outcome == 'Home Win':
                odds = match.get('home_odds', 2.0)
            elif predicted_outcome == 'Away Win':
                odds = match.get('away_odds', 3.5)
            else:
                odds = match.get('draw_odds', 3.5)

            if predicted_outcome == actual_result:
                pnl = stake_amount * (odds - 1)
                bet_won = True
            else:
                pnl = -stake_amount

            self.bankroll += pnl

            # Track in performance tracker
            self.tracker.add_bet(
                stake=stake_amount,
                odds=odds,
                won=bet_won,
                pnl=pnl
            )

        # Update algorithm Elo ratings
        self.algorithm.update_elo(
            match_data['homeTeam'],
            match_data['awayTeam'],
            home_goals,
            away_goals
        )

        return {
            'date': str(match.get('Date', '')),
            'home_team': match_data['homeTeam'],
            'away_team': match_data['awayTeam'],
            'actual_result': actual_result,
            'actual_score': f"{home_goals}-{away_goals}",
            'predicted_outcome': predicted_outcome,
            'prediction_correct': predicted_outcome == actual_result,
            'home_prob': prediction.get('homeWinProb', 0),
            'draw_prob': prediction.get('drawProb', 0),
            'away_prob': prediction.get('awayWinProb', 0),
            'confidence': prediction.get('confidence', 0),
            'should_bet': should_bet,
            'stake_amount': stake_amount,
            'odds_played': odds if should_bet else None,
            'bet_won': bet_won if should_bet else None,
            'pnl': pnl,
            'bankroll': self.bankroll,
            'expected_value': expected_value
        }

    def _generate_summary(self) -> Dict:
        """Generate comprehensive backtest summary"""
        if not self.results:
            return {'error': 'No results to summarize'}

        df = pd.DataFrame(self.results)

        # Overall metrics
        total_matches = len(df)
        correct_predictions = df['prediction_correct'].sum()
        overall_accuracy = correct_predictions / total_matches * 100

        # Betting metrics
        bets_placed = df['should_bet'].sum()
        bets_won = df[df['should_bet']]['bet_won'].sum()
        win_rate = bets_won / max(bets_placed, 1) * 100

        total_pnl = df['pnl'].sum()
        final_bankroll = self.bankroll
        roi = calculate_roi(self.initial_bankroll, final_bankroll)

        # Calculate by prediction type
        accuracy_by_type = {}
        for outcome in ['Home Win', 'Away Win', 'Draw']:
            subset = df[df['predicted_outcome'] == outcome]
            if len(subset) > 0:
                accuracy_by_type[outcome] = {
                    'count': len(subset),
                    'correct': subset['prediction_correct'].sum(),
                    'accuracy': subset['prediction_correct'].mean() * 100
                }

        # Calculate by confidence level
        accuracy_by_confidence = {}
        confidence_bins = [(0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0)]
        for low, high in confidence_bins:
            subset = df[(df['confidence'] >= low) & (df['confidence'] < high)]
            if len(subset) > 0:
                accuracy_by_confidence[f'{int(low*100)}-{int(high*100)}%'] = {
                    'count': len(subset),
                    'correct': subset['prediction_correct'].sum(),
                    'accuracy': subset['prediction_correct'].mean() * 100
                }

        # Calibration analysis
        calibration = self._calculate_calibration(df)

        # Tracker statistics
        tracker_stats = self.tracker.get_summary()

        # Maximum drawdown
        max_drawdown = self._calculate_max_drawdown()

        # Sharpe ratio (simplified)
        returns = np.diff(self.equity_curve) / self.equity_curve[:-1] if len(self.equity_curve) > 1 else [0]
        sharpe = np.mean(returns) / max(np.std(returns), 0.0001) * np.sqrt(252) if len(returns) > 0 else 0

        return {
            'overall': {
                'total_matches': total_matches,
                'correct_predictions': int(correct_predictions),
                'overall_accuracy': round(overall_accuracy, 2),
                'initial_bankroll': self.initial_bankroll,
                'final_bankroll': round(final_bankroll, 2),
                'total_pnl': round(total_pnl, 2),
                'roi': round(roi, 2),
                'max_drawdown': round(max_drawdown, 2),
                'sharpe_ratio': round(sharpe, 2)
            },
            'betting': {
                'bets_placed': int(bets_placed),
                'bets_won': int(bets_won),
                'win_rate': round(win_rate, 2),
                'avg_stake': round(df[df['should_bet']]['stake_amount'].mean(), 2) if bets_placed > 0 else 0,
                'avg_odds': round(df[df['should_bet']]['odds_played'].mean(), 2) if bets_placed > 0 else 0
            },
            'accuracy_by_type': accuracy_by_type,
            'accuracy_by_confidence': accuracy_by_confidence,
            'calibration': calibration,
            'tracker_stats': tracker_stats,
            'equity_curve': self.equity_curve[-100:] if len(self.equity_curve) > 100 else self.equity_curve,
            'timestamp': datetime.now().isoformat()
        }

    def _calculate_calibration(self, df: pd.DataFrame) -> Dict:
        """Calculate probability calibration metrics"""
        calibration = {
            'home_win': {},
            'draw': {},
            'away_win': {}
        }

        prob_bins = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)]

        # Home win calibration
        for low, high in prob_bins:
            subset = df[(df['home_prob'] >= low) & (df['home_prob'] < high)]
            if len(subset) > 0:
                actual_rate = (subset['actual_result'] == 'Home Win').mean()
                expected_rate = subset['home_prob'].mean()
                calibration['home_win'][f'{int(low*100)}-{int(high*100)}%'] = {
                    'count': len(subset),
                    'expected': round(expected_rate * 100, 1),
                    'actual': round(actual_rate * 100, 1),
                    'error': round((actual_rate - expected_rate) * 100, 1)
                }

        return calibration

    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown percentage"""
        if len(self.equity_curve) < 2:
            return 0.0

        peak = self.equity_curve[0]
        max_drawdown = 0.0

        for value in self.equity_curve:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak * 100
            max_drawdown = max(max_drawdown, drawdown)

        return max_drawdown

    def _save_results(self, summary: Dict):
        """Save backtest results to files"""
        results_dir = Path('./results/backtests')
        results_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save JSON summary
        json_path = results_dir / f'backtest_{timestamp}.json'
        with open(json_path, 'w') as f:
            json.dump(summary, f, indent=2, default=str)

        # Save detailed CSV
        if self.results:
            csv_path = results_dir / f'backtest_{timestamp}.csv'
            pd.DataFrame(self.results).to_csv(csv_path, index=False)

        print(f"Results saved to {results_dir}")

    def get_detailed_results(self) -> pd.DataFrame:
        """Get detailed results as DataFrame"""
        return pd.DataFrame(self.results)

    def get_equity_curve(self) -> List[float]:
        """Get equity curve"""
        return self.equity_curve


class WalkForwardOptimizer:
    """Walk-forward optimization for algorithm parameters"""

    def __init__(self, algorithm_class, data: pd.DataFrame,
                 train_size: int = 100, test_size: int = 50):
        self.algorithm_class = algorithm_class
        self.data = data
        self.train_size = train_size
        self.test_size = test_size
        self.results = []

    def optimize(self, param_grid: Dict) -> Dict:
        """
        Run walk-forward optimization.

        Args:
            param_grid: Dictionary of parameters to optimize

        Returns:
            Best parameters and results
        """
        n_splits = (len(self.data) - self.train_size) // self.test_size

        all_results = []

        for i in range(n_splits):
            train_start = i * self.test_size
            train_end = train_start + self.train_size
            test_end = train_end + self.test_size

            train_data = self.data.iloc[train_start:train_end]
            test_data = self.data.iloc[train_end:test_end]

            # Test each parameter combination
            for params in self._generate_param_combinations(param_grid):
                algo = self.algorithm_class('football')
                engine = BacktestEngine(algo)

                # Train phase (update Elo ratings)
                for _, row in train_data.iterrows():
                    algo.update_elo(
                        row['home_team'],
                        row['away_team'],
                        row['home_goals'],
                        row['away_goals']
                    )

                # Test phase
                results = engine.run_backtest(test_data)

                all_results.append({
                    'split': i,
                    'params': params,
                    'roi': results['overall']['roi'],
                    'accuracy': results['overall']['overall_accuracy']
                })

        # Find best parameters
        best_result = max(all_results, key=lambda x: x['roi'])

        return {
            'best_params': best_result['params'],
            'best_roi': best_result['roi'],
            'all_results': all_results
        }

    def _generate_param_combinations(self, param_grid: Dict) -> List[Dict]:
        """Generate all parameter combinations"""
        from itertools import product

        keys = list(param_grid.keys())
        values = [param_grid[k] for k in keys]

        combinations = []
        for combo in product(*values):
            combinations.append(dict(zip(keys, combo)))

        return combinations


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Run betting algorithm backtest')
    parser.add_argument('--data', type=str, help='Path to historical data CSV')
    parser.add_argument('--bankroll', type=float, default=1000, help='Initial bankroll')
    parser.add_argument('--kelly', type=float, default=0.25, help='Kelly fraction')
    parser.add_argument('--sport', type=str, default='football', help='Sport type')

    args = parser.parse_args()

    # Initialize
    algo = ProfessionalBettingAlgorithm(args.sport)
    engine = BacktestEngine(algo, initial_bankroll=args.bankroll, kelly_fraction=args.kelly)

    # Load data
    if args.data:
        data = engine.load_historical_data(args.data)
    else:
        data = engine.load_historical_data()

    print(f"Loaded {len(data)} matches")
    print(f"Date range: {data['Date'].min()} to {data['Date'].max()}")
    print()

    # Run backtest
    print("Running backtest...")
    results = engine.run_backtest(data)

    # Print summary
    print("\n" + "="*60)
    print("BACKTEST RESULTS")
    print("="*60)
    print(f"Total Matches: {results['overall']['total_matches']}")
    print(f"Overall Accuracy: {results['overall']['overall_accuracy']}%")
    print(f"Final Bankroll: ${results['overall']['final_bankroll']:.2f}")
    print(f"ROI: {results['overall']['roi']}%")
    print(f"Max Drawdown: {results['overall']['max_drawdown']}%")
    print(f"Sharpe Ratio: {results['overall']['sharpe_ratio']}")
    print()
    print(f"Bets Placed: {results['betting']['bets_placed']}")
    print(f"Win Rate: {results['betting']['win_rate']}%")
    print("="*60)
