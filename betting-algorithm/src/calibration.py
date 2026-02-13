"""
Calibration Engine for Self-Improving Betting Algorithm

Tracks prediction performance and automatically adjusts factor weights
to improve accuracy over time.

Author: AI Betting Algorithm v2.0
Date: 2026-02-11
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
import numpy as np


@dataclass
class PredictionRecord:
    """Record of a single prediction with outcome"""
    match_id: str
    predicted_outcome: str  # 'home', 'draw', 'away'
    actual_outcome: str
    predicted_probs: Dict[str, float]  # {'home': 0.5, 'draw': 0.3, 'away': 0.2}
    factors: Dict[str, Any]  # Factor contributions
    correct: bool
    timestamp: str

    def __post_init__(self):
        """Calculate if prediction was correct"""
        self.correct = (self.predicted_outcome == self.actual_outcome)


class CalibrationEngine:
    """
    Self-improving calibration system for betting algorithm.

    Tracks prediction accuracy per factor and adjusts weights to
    maximize overall prediction accuracy.

    Features:
    - Per-factor performance tracking
    - Gradual weight adjustment with learning rate
    - Protection against overfitting (max ±10% adjustment)
    - Minimum sample size requirement (20 predictions)
    """

    def __init__(self, learning_rate: float = 0.01, max_history: int = 1000):
        """
        Initialize calibration engine.

        Args:
            learning_rate: Weight adjustment speed (0.01 = 1% per calibration)
            max_history: Maximum predictions to store (older dropped)
        """
        self.learning_rate = learning_rate
        self.max_history = max_history
        self.prediction_history: List[PredictionRecord] = []
        self.factor_performance: Dict[str, Dict[str, float]] = defaultdict(lambda: {
            'correct': 0,
            'total': 0,
            'accuracy': 0.0,
            'contribution': 0.0
        })

    def record_prediction(
        self,
        match_id: str,
        factors: Dict,
        predicted_probs: Dict[str, float],
        predicted_outcome: str,
        actual_outcome: str,
        timestamp: Optional[str] = None
    ):
        """
        Record a prediction and its actual outcome.

        Args:
            match_id: Unique match identifier
            factors: Factor data from prediction (dict or FactorResult objects)
            predicted_probs: Predicted probabilities {'home': 0.5, ...}
            predicted_outcome: Predicted result ('home', 'draw', 'away')
            actual_outcome: Actual result ('home', 'draw', 'away')
            timestamp: ISO timestamp (defaults to current time)
        """
        from datetime import datetime
        from .models import FactorResult

        if timestamp is None:
            timestamp = datetime.now().isoformat()

        # Create prediction record
        record = PredictionRecord(
            match_id=match_id,
            predicted_outcome=predicted_outcome,
            actual_outcome=actual_outcome,
            predicted_probs=predicted_probs,
            factors=factors,
            correct=(predicted_outcome == actual_outcome),
            timestamp=timestamp
        )

        # Add to history (maintain max size)
        self.prediction_history.append(record)
        if len(self.prediction_history) > self.max_history:
            self.prediction_history.pop(0)

        # Update factor performance tracking
        for factor_name, factor_data in factors.items():
            # Handle FactorResult objects
            if isinstance(factor_data, FactorResult):
                if factor_data.triggered:
                    self.factor_performance[factor_name]['total'] += 1
                    if record.correct:
                        self.factor_performance[factor_name]['correct'] += 1
                    self.factor_performance[factor_name]['contribution'] = factor_data.weight
            # Handle legacy dict factors
            elif isinstance(factor_data, dict):
                self.factor_performance[factor_name]['total'] += 1
                if record.correct:
                    self.factor_performance[factor_name]['correct'] += 1

        # Recalculate accuracy for all factors
        for factor_name, stats in self.factor_performance.items():
            if stats['total'] > 0:
                stats['accuracy'] = stats['correct'] / stats['total']

    def calibrate_weights(self, current_weights: Dict[str, float]) -> Dict[str, float]:
        """
        Adjust weights based on factor performance.

        Strategy:
        - Factors with above-average accuracy get slight weight increase
        - Factors with below-average accuracy get slight weight decrease
        - Adjustments capped at ±10% to prevent overfitting
        - Requires minimum 20 predictions

        Args:
            current_weights: Current factor weights

        Returns:
            Adjusted weights (normalized to sum = 1.0)
        """
        if len(self.prediction_history) < 20:
            # Not enough data for calibration
            return current_weights

        # Calculate overall accuracy
        overall_accuracy = sum(1 for r in self.prediction_history if r.correct) / len(self.prediction_history)

        if overall_accuracy == 0:
            # All predictions wrong, no calibration possible
            return current_weights

        # Calculate adjustment for each factor
        adjusted_weights = current_weights.copy()

        for factor_name, weight in current_weights.items():
            if factor_name not in self.factor_performance:
                continue

            stats = self.factor_performance[factor_name]
            if stats['total'] < 5:
                # Not enough data for this factor
                continue

            factor_accuracy = stats['accuracy']

            # Calculate relative performance
            performance_ratio = factor_accuracy / overall_accuracy

            # Calculate adjustment (positive if factor outperforms, negative if underperforms)
            adjustment = self.learning_rate * (performance_ratio - 1.0)

            # Cap adjustment at ±10%
            adjustment = max(-0.10, min(0.10, adjustment))

            # Apply adjustment
            new_weight = weight * (1 + adjustment)

            # Ensure weight stays positive
            adjusted_weights[factor_name] = max(0.01, new_weight)

        # Normalize weights to sum = 1.0
        total_weight = sum(adjusted_weights.values())
        if total_weight > 0:
            adjusted_weights = {k: v / total_weight for k, v in adjusted_weights.items()}

        return adjusted_weights

    def get_performance_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive performance report.

        Returns:
            Dict with overall stats, factor stats, recent trends
        """
        if not self.prediction_history:
            return {
                'overall_accuracy': 0.0,
                'total_predictions': 0,
                'factor_stats': {},
                'recent_trend': 'N/A'
            }

        # Overall stats
        total_predictions = len(self.prediction_history)
        correct_predictions = sum(1 for r in self.prediction_history if r.correct)
        overall_accuracy = correct_predictions / total_predictions

        # Recent trend (last 20 predictions vs overall)
        recent_predictions = self.prediction_history[-20:]
        recent_correct = sum(1 for r in recent_predictions if r.correct)
        recent_accuracy = recent_correct / len(recent_predictions)

        trend = "improving" if recent_accuracy > overall_accuracy else "declining" if recent_accuracy < overall_accuracy else "stable"

        # Factor stats
        factor_stats = {}
        for factor_name, stats in self.factor_performance.items():
            if stats['total'] > 0:
                factor_stats[factor_name] = {
                    'accuracy': stats['accuracy'],
                    'total_samples': stats['total'],
                    'contribution': stats['contribution'],
                    'relative_performance': stats['accuracy'] / overall_accuracy if overall_accuracy > 0 else 1.0
                }

        # Outcome distribution
        outcome_counts = defaultdict(int)
        for record in self.prediction_history:
            outcome_counts[record.actual_outcome] += 1

        return {
            'overall_accuracy': overall_accuracy,
            'total_predictions': total_predictions,
            'correct_predictions': correct_predictions,
            'recent_accuracy': recent_accuracy,
            'recent_trend': trend,
            'factor_stats': factor_stats,
            'outcome_distribution': dict(outcome_counts),
            'sample_size_sufficient': total_predictions >= 20
        }

    def get_underperforming_factors(self, threshold: float = 0.9) -> List[str]:
        """
        Identify factors performing below threshold.

        Args:
            threshold: Performance ratio threshold (0.9 = 90% of overall accuracy)

        Returns:
            List of factor names performing below threshold
        """
        if len(self.prediction_history) < 20:
            return []

        overall_accuracy = sum(1 for r in self.prediction_history if r.correct) / len(self.prediction_history)

        if overall_accuracy == 0:
            return []

        underperforming = []
        for factor_name, stats in self.factor_performance.items():
            if stats['total'] >= 5:  # Minimum sample size
                relative_performance = stats['accuracy'] / overall_accuracy
                if relative_performance < threshold:
                    underperforming.append(factor_name)

        return underperforming

    def reset(self):
        """Clear all calibration data"""
        self.prediction_history.clear()
        self.factor_performance.clear()

    def export_history(self) -> List[Dict]:
        """
        Export prediction history as list of dicts.

        Returns:
            List of prediction records as dictionaries
        """
        return [
            {
                'match_id': r.match_id,
                'predicted_outcome': r.predicted_outcome,
                'actual_outcome': r.actual_outcome,
                'correct': r.correct,
                'predicted_probs': r.predicted_probs,
                'timestamp': r.timestamp
            }
            for r in self.prediction_history
        ]

    def import_history(self, records: List[Dict]):
        """
        Import prediction history from list of dicts.

        Args:
            records: List of prediction record dictionaries
        """
        for record in records:
            self.record_prediction(
                match_id=record['match_id'],
                factors={},  # Factors not stored in export
                predicted_probs=record['predicted_probs'],
                predicted_outcome=record['predicted_outcome'],
                actual_outcome=record['actual_outcome'],
                timestamp=record['timestamp']
            )
