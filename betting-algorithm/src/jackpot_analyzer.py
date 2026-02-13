"""
Jackpot Analyzer - Generates predictions for jackpot matches and tracks performance

Integrates with the main betting algorithm to:
1. Generate predictions for all jackpot matches
2. Calculate optimal combinations
3. Track historical performance
4. Refine algorithm based on jackpot results

Author: AI Betting Algorithm
Date: 2026-02-11
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import pandas as pd
import itertools
from .algorithm import ProfessionalBettingAlgorithm


class JackpotAnalyzer:
    """Analyzes jackpots and generates predictions"""

    def __init__(self):
        self.algorithm = ProfessionalBettingAlgorithm('football')
        self.predictions_dir = Path('./data/jackpot_predictions')
        self.predictions_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir = Path('./data/jackpot_results')
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def _enrich_match_data(self, match: Dict) -> Dict:
        """
        Enrich raw jackpot match data with team stats from database.

        Looks up Elo ratings, league positions, form, xG averages, and style
        for both teams. Falls back to neutral defaults when team not found.
        """
        from .config import lookup_team

        home_name = match.get('home_team', '')
        away_name = match.get('away_team', '')

        home_data = lookup_team(home_name)
        away_data = lookup_team(away_name)

        match_data = {
            'homeTeam': home_name,
            'awayTeam': away_name,
            'competition': match.get('competition', 'Unknown'),
            'date': match.get('kickoff'),
        }

        # Enrich home team data
        if home_data:
            match_data.update({
                'home_elo': home_data['elo'],
                'home_position': home_data['position'],
                'homePosition': home_data['position'],
                'home_form': home_data['form'],
                'homeStarRating': home_data['stars'],
                'home_xg': home_data['home_xg_avg'],
                'homeStyle': home_data['style'],
            })

        # Enrich away team data
        if away_data:
            match_data.update({
                'away_elo': away_data['elo'],
                'away_position': away_data['position'],
                'awayPosition': away_data['position'],
                'away_form': away_data['form'],
                'awayStarRating': away_data['stars'],
                'away_xg': away_data['away_xg_avg'],
                'awayStyle': away_data['style'],
            })

        # Pass through odds if available from jackpot source
        if 'home_odds' in match:
            match_data['homeOdds'] = match['home_odds']
        if 'draw_odds' in match:
            match_data['drawOdds'] = match['draw_odds']
        if 'away_odds' in match:
            match_data['awayOdds'] = match['away_odds']

        return match_data

    def analyze_jackpot(self, jackpot_data: Dict) -> Dict:
        """
        Analyze a jackpot and generate predictions for all matches

        Args:
            jackpot_data: Jackpot data from JackpotFetcher

        Returns:
            Dict with predictions and analysis
        """
        print(f"\n{'=' * 70}")
        print(f"ANALYZING: {jackpot_data['provider']} - {jackpot_data['type']}")
        print(f"{'=' * 70}\n")

        predictions = []
        high_confidence_picks = []
        low_confidence_picks = []

        for match in jackpot_data['matches']:
            # Enrich match data with team stats from database
            match_data = self._enrich_match_data(match)

            # Generate prediction
            try:
                prediction = self.algorithm.predict_match(match_data)

                # Determine most likely outcome
                probs = {
                    'Home': prediction['homeWinProb'],
                    'Draw': prediction['drawProb'],
                    'Away': prediction['awayWinProb']
                }
                most_likely = max(probs.items(), key=lambda x: x[1])

                match_prediction = {
                    'match_number': match['match_number'],
                    'home_team': match['home_team'],
                    'away_team': match['away_team'],
                    'prediction': most_likely[0],
                    'confidence': prediction['confidence'],
                    'home_prob': prediction['homeWinProb'],
                    'draw_prob': prediction['drawProb'],
                    'away_prob': prediction['awayWinProb'],
                    'recommendation': prediction['recommendation']['recommendation']
                }

                predictions.append(match_prediction)

                # Categorize by confidence
                if prediction['confidence'] > 0.75:
                    high_confidence_picks.append(match_prediction)
                elif prediction['confidence'] < 0.55:
                    low_confidence_picks.append(match_prediction)

                # Print prediction
                self._print_match_prediction(match_prediction)

            except Exception as e:
                print(f"❌ Error predicting match {match['match_number']}: {e}")
                predictions.append({
                    'match_number': match['match_number'],
                    'home_team': match['home_team'],
                    'away_team': match['away_team'],
                    'prediction': 'Error',
                    'confidence': 0,
                    'error': str(e)
                })

        # Generate analysis
        analysis = {
            'jackpot_id': f"{jackpot_data['provider']}_{jackpot_data['type']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'provider': jackpot_data['provider'],
            'type': jackpot_data['type'],
            'prize_amount': jackpot_data.get('prize_amount'),
            'total_matches': len(predictions),
            'analyzed_at': datetime.now().isoformat(),
            'predictions': predictions,
            'high_confidence_count': len(high_confidence_picks),
            'low_confidence_count': len(low_confidence_picks),
            'high_confidence_picks': high_confidence_picks,
            'low_confidence_picks': low_confidence_picks,
            'average_confidence': sum(p['confidence'] for p in predictions) / len(predictions) if predictions else 0
        }

        # Generate combinations for multi-bet strategies
        analysis['recommended_combinations'] = self._generate_combinations(predictions)

        # Save predictions
        self._save_predictions(analysis)

        # Print summary
        self._print_analysis_summary(analysis)

        return analysis

    def _print_match_prediction(self, prediction: Dict):
        """Print formatted match prediction"""
        confidence_emoji = "🟢" if prediction['confidence'] > 0.75 else "🟡" if prediction['confidence'] > 0.6 else "🔴"

        print(f"{prediction['match_number']:2d}. {prediction['home_team']:20s} vs {prediction['away_team']:20s}")
        print(f"    {confidence_emoji} Prediction: {prediction['prediction']:4s} | "
              f"Confidence: {prediction['confidence']*100:5.1f}% | "
              f"H:{prediction['home_prob']*100:4.1f}% D:{prediction['draw_prob']*100:4.1f}% A:{prediction['away_prob']*100:4.1f}%")
        print()

    def _print_analysis_summary(self, analysis: Dict):
        """Print analysis summary"""
        print(f"\n{'=' * 70}")
        print(f"ANALYSIS SUMMARY")
        print(f"{'=' * 70}\n")
        print(f"Total Matches: {analysis['total_matches']}")
        print(f"Average Confidence: {analysis['average_confidence']*100:.1f}%")
        print(f"High Confidence Picks (>75%): {analysis['high_confidence_count']}")
        print(f"Low Confidence Picks (<55%): {analysis['low_confidence_count']}")
        print(f"\n💡 Recommended Combinations:")
        for i, combo in enumerate(analysis['recommended_combinations'][:3], 1):
            if 'predicted_accuracy' in combo:
                print(f"  {i}. {combo['description']}: {combo['predicted_accuracy']*100:.1f}% accuracy")
            else:
                print(f"  {i}. {combo['description']}")
        print()

    def _generate_combinations(self, predictions: List[Dict]) -> List[Dict]:
        """
        Generate recommended betting combinations

        Strategies:
        1. Single bet (all predictions as-is)
        2. High confidence only bet
        3. Banker bet (keep high confidence, double low confidence)
        4. Multi-bet (3-5 variations)
        """
        combinations = []

        # Strategy 1: Main prediction (single bet)
        main_bet = {
            'strategy': 'Main Prediction',
            'description': 'All matches with highest probability outcome',
            'picks': [f"{p['match_number']}: {p['prediction']}" for p in predictions],
            'predicted_accuracy': sum(
                max(p['home_prob'], p['draw_prob'], p['away_prob']) for p in predictions
            ) / len(predictions) if predictions else 0
        }
        combinations.append(main_bet)

        # Strategy 2: Conservative (only high confidence)
        high_conf = [p for p in predictions if p['confidence'] > 0.7]
        if high_conf:
            conservative_bet = {
                'strategy': 'Conservative',
                'description': f'{len(high_conf)} high confidence picks, others doubled',
                'high_confidence_picks': [f"{p['match_number']}: {p['prediction']}" for p in high_conf],
                'predicted_accuracy': sum(
                    max(p['home_prob'], p['draw_prob'], p['away_prob']) for p in high_conf
                ) / len(high_conf)
            }
            combinations.append(conservative_bet)

        # Strategy 3: Value bet (focus on draws with >30% probability)
        draw_opportunities = [p for p in predictions if p['draw_prob'] > 0.3]
        if draw_opportunities:
            value_bet = {
                'strategy': 'Draw Value',
                'description': f'{len(draw_opportunities)} matches with draw probability >30%',
                'draw_candidates': [
                    f"{p['match_number']}: {p['home_team']} vs {p['away_team']} ({p['draw_prob']*100:.1f}%)"
                    for p in draw_opportunities
                ]
            }
            combinations.append(value_bet)

        return combinations

    def _save_predictions(self, analysis: Dict):
        """Save predictions to file"""
        try:
            filename = f"{analysis['jackpot_id']}.json"
            filepath = self.predictions_dir / filename

            with open(filepath, 'w') as f:
                json.dump(analysis, f, indent=2)

            print(f"📝 Predictions saved to: {filepath}")

            # Also save to CSV for easy viewing
            self._save_predictions_csv(analysis)

        except Exception as e:
            print(f"Warning: Could not save predictions: {e}")

    def _save_predictions_csv(self, analysis: Dict):
        """Save predictions to CSV"""
        try:
            df = pd.DataFrame(analysis['predictions'])
            csv_path = self.predictions_dir / f"{analysis['jackpot_id']}.csv"
            df.to_csv(csv_path, index=False)
        except Exception as e:
            print(f"Warning: Could not save CSV: {e}")

    def record_jackpot_results(self, jackpot_id: str, results: List[Dict]):
        """
        Record actual results for a jackpot

        Args:
            jackpot_id: ID from analysis
            results: List of dicts with match_number and actual_result (Home/Draw/Away)
        """
        try:
            # Load original predictions
            pred_file = self.predictions_dir / f"{jackpot_id}.json"
            if not pred_file.exists():
                print(f"❌ Predictions file not found: {jackpot_id}")
                return

            with open(pred_file, 'r') as f:
                analysis = json.load(f)

            # Match results with predictions
            correct = 0
            total = len(results)

            for result in results:
                match_num = result['match_number']
                actual = result['actual_result']

                # Find prediction
                pred = next((p for p in analysis['predictions'] if p['match_number'] == match_num), None)

                if pred:
                    pred['actual_result'] = actual
                    pred['correct'] = (pred['prediction'] == actual)

                    if pred['correct']:
                        correct += 1

            # Calculate performance
            accuracy = correct / total if total > 0 else 0

            # Save results
            result_data = {
                'jackpot_id': jackpot_id,
                'provider': analysis['provider'],
                'type': analysis['type'],
                'recorded_at': datetime.now().isoformat(),
                'total_matches': total,
                'correct_predictions': correct,
                'accuracy': accuracy,
                'predictions_with_results': analysis['predictions']
            }

            result_file = self.results_dir / f"{jackpot_id}_results.json"
            with open(result_file, 'w') as f:
                json.dump(result_data, f, indent=2)

            print(f"\n✅ Results recorded: {correct}/{total} correct ({accuracy*100:.1f}%)")
            print(f"📝 Saved to: {result_file}")

            # Append to master results CSV
            self._append_to_results_csv(result_data)

            return result_data

        except Exception as e:
            print(f"❌ Error recording results: {e}")
            import traceback
            traceback.print_exc()

    def _append_to_results_csv(self, result_data: Dict):
        """Append results to master CSV"""
        try:
            csv_path = self.results_dir / 'jackpot_results_summary.csv'

            row = {
                'timestamp': result_data['recorded_at'],
                'jackpot_id': result_data['jackpot_id'],
                'provider': result_data['provider'],
                'type': result_data['type'],
                'total_matches': result_data['total_matches'],
                'correct': result_data['correct_predictions'],
                'accuracy': result_data['accuracy']
            }

            df = pd.DataFrame([row])
            if csv_path.exists():
                df.to_csv(csv_path, mode='a', header=False, index=False)
            else:
                df.to_csv(csv_path, mode='w', header=True, index=False)

        except Exception as e:
            print(f"Warning: Could not append to results CSV: {e}")

    def get_performance_stats(self) -> pd.DataFrame:
        """Get historical performance statistics"""
        try:
            csv_path = self.results_dir / 'jackpot_results_summary.csv'
            if not csv_path.exists():
                print("No results data available yet")
                return pd.DataFrame()

            df = pd.read_csv(csv_path)

            print(f"\n{'=' * 70}")
            print(f"JACKPOT PREDICTION PERFORMANCE")
            print(f"{'=' * 70}\n")
            print(f"Total Jackpots Analyzed: {len(df)}")
            print(f"Average Accuracy: {df['accuracy'].mean()*100:.1f}%")
            print(f"Best Performance: {df['accuracy'].max()*100:.1f}%")
            print(f"Worst Performance: {df['accuracy'].min()*100:.1f}%")
            print()

            # By provider
            print("Performance by Provider:")
            for provider in df['provider'].unique():
                provider_df = df[df['provider'] == provider]
                print(f"  {provider}: {provider_df['accuracy'].mean()*100:.1f}% avg accuracy ({len(provider_df)} jackpots)")

            print()

            return df

        except Exception as e:
            print(f"Error getting performance stats: {e}")
            return pd.DataFrame()


if __name__ == '__main__':
    # Test with sample data
    print("Jackpot Analyzer - Test Mode")
    print("=" * 70)

    analyzer = JackpotAnalyzer()

    # Sample jackpot data (would come from JackpotFetcher)
    sample_jackpot = {
        'provider': 'SportPesa',
        'type': 'Test Jackpot',
        'prize_amount': 'KSh 100,000,000',
        'matches': [
            {'match_number': 1, 'home_team': 'Arsenal', 'away_team': 'Chelsea'},
            {'match_number': 2, 'home_team': 'Man City', 'away_team': 'Liverpool'},
            {'match_number': 3, 'home_team': 'Tottenham', 'away_team': 'Man United'},
        ]
    }

    # Analyze
    analysis = analyzer.analyze_jackpot(sample_jackpot)

    print("\n✅ Test complete!")
