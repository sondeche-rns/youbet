"""
Backtesting Engine for Betting Algorithm
Tests algorithm performance on historical data

Usage: python backtest.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, List
import sys

from algorithm import ProfessionalBettingAlgorithm
from utils import calculate_kelly_stake, calculate_roi, PerformanceTracker


class BacktestEngine:
    """
    Comprehensive backtesting engine
    Tests algorithm on historical matches and calculates performance metrics
    """
    
    def __init__(self, algorithm, initial_bankroll=1000):
        """
        Initialize backtest engine
        
        Args:
            algorithm: ProfessionalBettingAlgorithm instance
            initial_bankroll: Starting bankroll amount
        """
        self.algorithm = algorithm
        self.initial_bankroll = initial_bankroll
        self.bankroll = initial_bankroll
        self.results = []
        self.tracker = PerformanceTracker(initial_bankroll)
        
    def load_historical_data(self, filepath='./data/final/historical_dataset.csv'):
        """Load historical dataset"""
        print(f"📂 Loading data from: {filepath}")
        
        try:
            df = pd.read_csv(filepath)
            df['Date'] = pd.to_datetime(df['Date'])
            print(f"✅ Loaded {len(df)} matches")
            return df
        except FileNotFoundError:
            print(f"❌ File not found: {filepath}")
            print("Run data_collector.py first to collect historical data")
            sys.exit(1)
    
    def run_backtest(self, data=None, max_matches=None):
        """
        Run backtest on historical data
        
        Args:
            data: DataFrame with historical matches (if None, loads from file)
            max_matches: Maximum number of matches to test (None = all)
        
        Returns:
            Dictionary with backtest results
        """
        print("="*70)
        print(" BACKTESTING BETTING ALGORITHM")
        print("="*70)
        
        # Load data if not provided
        if data is None:
            data = self.load_historical_data()
        
        # Limit matches if specified
        if max_matches:
            data = data.head(max_matches)
            print(f"Testing on first {max_matches} matches")
        
        print(f"\n🧪 Testing on {len(data)} matches")
        print(f"💰 Initial bankroll: £{self.initial_bankroll:,.2f}")
        print(f"📅 Date range: {data['Date'].min().date()} to {data['Date'].max().date()}\n")
        
        # Process each match
        for idx, row in data.iterrows():
            if idx % 100 == 0 and idx > 0:
                print(f"  Processed {idx}/{len(data)} matches...")
            
            result = self._process_match(row)
            self.results.append(result)
        
        # Generate comprehensive report
        report = self._generate_report()
        
        # Save results
        self._save_results(report)
        
        # Display summary
        self._display_summary(report)
        
        return report
    
    def _process_match(self, match_row):
        """Process a single match"""
        # Prepare match data for algorithm
        match_data = {
            'homeTeam': match_row['home_team'],
            'awayTeam': match_row['away_team'],
            'date': match_row['Date'].strftime('%Y-%m-%d'),
            'venue': 'Home Stadium',
            'competition': 'Premier League'
        }
        
        # Get prediction
        prediction = self.algorithm.predict_match(match_data)
        
        # Determine actual outcome
        if match_row['home_goals'] > match_row['away_goals']:
            actual_outcome = 'Home Win'
        elif match_row['away_goals'] > match_row['home_goals']:
            actual_outcome = 'Away Win'
        else:
            actual_outcome = 'Draw'
        
        # Check if prediction was correct
        predicted_outcome = prediction['recommendation']['outcome']
        is_correct = predicted_outcome == actual_outcome
        
        # Simulate betting
        recommendation = prediction['recommendation']['recommendation']
        stake_pct = prediction['recommendation']['stakePercentage']
        
        pnl = 0
        bet_placed = False
        
        if recommendation in ['Strong Bet', 'Value Bet'] and stake_pct > 0:
            bet_placed = True
            stake = self.bankroll * stake_pct
            
            # Get odds for predicted outcome
            if predicted_outcome == 'Home Win':
                odds = match_row['home_odds']
            elif predicted_outcome == 'Away Win':
                odds = match_row['away_odds']
            else:
                odds = match_row['draw_odds']
            
            # Calculate P&L
            if is_correct:
                pnl = stake * (odds - 1)
                self.bankroll += pnl
            else:
                pnl = -stake
                self.bankroll += pnl
            
            # Track bet
            self.tracker.add_bet(
                prediction=predicted_outcome,
                outcome=actual_outcome,
                stake=stake,
                odds=odds,
                won=is_correct
            )
        
        return {
            'date': match_row['Date'],
            'match': f"{match_row['home_team']} vs {match_row['away_team']}",
            'score': f"{match_row['home_goals']}-{match_row['away_goals']}",
            'predicted': predicted_outcome,
            'actual': actual_outcome,
            'correct': is_correct,
            'confidence': prediction['confidence'],
            'bet_placed': bet_placed,
            'stake_pct': stake_pct,
            'pnl': pnl,
            'bankroll': self.bankroll,
            'home_prob': prediction['homeWinProb'],
            'draw_prob': prediction['drawProb'],
            'away_prob': prediction['awayWinProb']
        }
    
    def _generate_report(self):
        """Generate comprehensive backtest report"""
        df = pd.DataFrame(self.results)
        
        # Overall statistics
        total_matches = len(df)
        correct_predictions = df['correct'].sum()
        overall_accuracy = (correct_predictions / total_matches * 100) if total_matches > 0 else 0
        
        # Betting statistics
        bets_placed = df['bet_placed'].sum()
        bets_won = df[df['bet_placed']]['correct'].sum()
        bet_win_rate = (bets_won / bets_placed * 100) if bets_placed > 0 else 0
        
        total_pnl = df['pnl'].sum()
        roi = calculate_roi(self.initial_bankroll, self.bankroll)
        
        # Accuracy by confidence level
        high_conf = df[df['confidence'] >= 0.80]
        med_conf = df[(df['confidence'] >= 0.65) & (df['confidence'] < 0.80)]
        low_conf = df[df['confidence'] < 0.65]
        
        # Accuracy by prediction type
        home_predictions = df[df['predicted'] == 'Home Win']
        draw_predictions = df[df['predicted'] == 'Draw']
        away_predictions = df[df['predicted'] == 'Away Win']
        
        # Calibration analysis
        calibration = self._analyze_calibration(df)
        
        # Monthly performance
        df['month'] = pd.to_datetime(df['date']).dt.to_period('M')
        monthly_stats = df.groupby('month').agg({
            'correct': ['sum', 'count'],
            'pnl': 'sum'
        }).reset_index()
        
        return {
            'overall': {
                'total_matches': total_matches,
                'correct_predictions': int(correct_predictions),
                'overall_accuracy': round(overall_accuracy, 2),
                'bets_placed': int(bets_placed),
                'bets_won': int(bets_won),
                'bet_win_rate': round(bet_win_rate, 2),
                'total_pnl': round(total_pnl, 2),
                'roi': round(roi, 2),
                'final_bankroll': round(self.bankroll, 2),
                'initial_bankroll': self.initial_bankroll
            },
            'by_confidence': {
                'high': {
                    'count': len(high_conf),
                    'accuracy': round((high_conf['correct'].sum() / len(high_conf) * 100) if len(high_conf) > 0 else 0, 2)
                },
                'medium': {
                    'count': len(med_conf),
                    'accuracy': round((med_conf['correct'].sum() / len(med_conf) * 100) if len(med_conf) > 0 else 0, 2)
                },
                'low': {
                    'count': len(low_conf),
                    'accuracy': round((low_conf['correct'].sum() / len(low_conf) * 100) if len(low_conf) > 0 else 0, 2)
                }
            },
            'by_prediction_type': {
                'home_wins': {
                    'count': len(home_predictions),
                    'accuracy': round((home_predictions['correct'].sum() / len(home_predictions) * 100) if len(home_predictions) > 0 else 0, 2)
                },
                'draws': {
                    'count': len(draw_predictions),
                    'accuracy': round((draw_predictions['correct'].sum() / len(draw_predictions) * 100) if len(draw_predictions) > 0 else 0, 2)
                },
                'away_wins': {
                    'count': len(away_predictions),
                    'accuracy': round((away_predictions['correct'].sum() / len(away_predictions) * 100) if len(away_predictions) > 0 else 0, 2)
                }
            },
            'calibration': calibration,
            'detailed_results': self.results[:10],  # First 10 matches
            'tracker_stats': self.tracker.get_statistics()
        }
    
    def _analyze_calibration(self, df):
        """Analyze prediction calibration"""
        # Group by predicted probability bins
        bins = [0, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0]
        labels = ['<40%', '40-50%', '50-60%', '60-70%', '70-80%', '80%+']
        
        calibration_data = []
        
        for outcome_type in ['home_prob', 'draw_prob', 'away_prob']:
            df['prob_bin'] = pd.cut(df[outcome_type], bins=bins, labels=labels)
            
            for bin_label in labels:
                bin_data = df[df['prob_bin'] == bin_label]
                if len(bin_data) > 0:
                    # Determine if outcome matched
                    if outcome_type == 'home_prob':
                        actual_rate = (bin_data['actual'] == 'Home Win').sum() / len(bin_data)
                    elif outcome_type == 'draw_prob':
                        actual_rate = (bin_data['actual'] == 'Draw').sum() / len(bin_data)
                    else:
                        actual_rate = (bin_data['actual'] == 'Away Win').sum() / len(bin_data)
                    
                    calibration_data.append({
                        'outcome_type': outcome_type.replace('_prob', ''),
                        'predicted_range': bin_label,
                        'count': len(bin_data),
                        'actual_rate': round(actual_rate * 100, 2)
                    })
        
        return calibration_data
    
    def _save_results(self, report):
        """Save backtest results to file"""
        results_dir = Path('./results/backtests')
        results_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = results_dir / f'backtest_{timestamp}.json'
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: {filepath}")
        
        # Also save detailed CSV
        df = pd.DataFrame(self.results)
        csv_path = results_dir / f'backtest_{timestamp}.csv'
        df.to_csv(csv_path, index=False)
        print(f"💾 Detailed results saved to: {csv_path}")
    
    def _display_summary(self, report):
        """Display backtest summary"""
        print("\n" + "="*70)
        print(" BACKTEST RESULTS")
        print("="*70)
        
        overall = report['overall']
        
        print(f"\n📊 OVERALL PERFORMANCE")
        print("-"*70)
        print(f"Total Matches Analyzed: {overall['total_matches']}")
        print(f"Prediction Accuracy: {overall['overall_accuracy']:.2f}%")
        print(f"Correct Predictions: {overall['correct_predictions']}/{overall['total_matches']}")
        
        print(f"\n💰 BETTING PERFORMANCE")
        print("-"*70)
        print(f"Bets Placed: {overall['bets_placed']}")
        print(f"Bets Won: {overall['bets_won']}")
        print(f"Bet Win Rate: {overall['bet_win_rate']:.2f}%")
        print(f"Initial Bankroll: £{overall['initial_bankroll']:,.2f}")
        print(f"Final Bankroll: £{overall['final_bankroll']:,.2f}")
        print(f"Total P&L: £{overall['total_pnl']:,.2f}")
        print(f"ROI: {overall['roi']:.2f}%")
        
        print(f"\n🎯 ACCURACY BY CONFIDENCE")
        print("-"*70)
        by_conf = report['by_confidence']
        print(f"High Confidence (80%+): {by_conf['high']['accuracy']:.2f}% ({by_conf['high']['count']} matches)")
        print(f"Medium Confidence (65-80%): {by_conf['medium']['accuracy']:.2f}% ({by_conf['medium']['count']} matches)")
        print(f"Low Confidence (<65%): {by_conf['low']['accuracy']:.2f}% ({by_conf['low']['count']} matches)")
        
        print(f"\n📈 ACCURACY BY PREDICTION TYPE")
        print("-"*70)
        by_type = report['by_prediction_type']
        print(f"Home Wins: {by_type['home_wins']['accuracy']:.2f}% ({by_type['home_wins']['count']} predictions)")
        print(f"Draws: {by_type['draws']['accuracy']:.2f}% ({by_type['draws']['count']} predictions)")
        print(f"Away Wins: {by_type['away_wins']['accuracy']:.2f}% ({by_type['away_wins']['count']} predictions)")
        
        # Performance verdict
        print(f"\n✅ VERDICT")
        print("-"*70)
        if overall['roi'] > 15:
            print("🎉 EXCELLENT! ROI > 15% - Algorithm performing very well")
        elif overall['roi'] > 8:
            print("✅ GOOD! ROI > 8% - Algorithm shows profit potential")
        elif overall['roi'] > 0:
            print("👍 POSITIVE! ROI > 0% - Algorithm is profitable")
        else:
            print("⚠️ NEEDS IMPROVEMENT - Algorithm needs calibration")
        
        print("\n" + "="*70)


def main():
    """Main execution"""
    print("Initializing backtest...\n")
    
    # Create algorithm
    algo = ProfessionalBettingAlgorithm('football')
    
    # Create backtest engine
    engine = BacktestEngine(algo, initial_bankroll=1000)
    
    # Run backtest
    report = engine.run_backtest()
    
    print("\n✅ Backtest complete!")
    print("\nTo test on more matches, edit max_matches parameter")
    print("Example: engine.run_backtest(max_matches=500)")
    
    return report


if __name__ == "__main__":
    main()