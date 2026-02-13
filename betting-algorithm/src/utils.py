"""
Utility Functions and Classes for Sports Betting Algorithm
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime


def calculate_kelly_stake(probability: float, odds: float,
                          fraction: float = 0.25, max_stake: float = 0.05) -> float:
    """
    Calculate Kelly Criterion stake size.

    Args:
        probability: Estimated probability of winning (0-1)
        odds: Decimal odds
        fraction: Kelly fraction to use (0.25 = quarter Kelly)
        max_stake: Maximum stake as fraction of bankroll

    Returns:
        Recommended stake as fraction of bankroll
    """
    if probability <= 0 or probability >= 1 or odds <= 1:
        return 0.0

    b = odds - 1  # Net odds (profit per unit stake)
    p = probability
    q = 1 - p

    # Kelly formula: f = (bp - q) / b
    kelly = (b * p - q) / b

    # Apply fractional Kelly and cap
    stake = max(0, kelly * fraction)
    return min(stake, max_stake)


def calculate_implied_probability(decimal_odds: float) -> float:
    """Convert decimal odds to implied probability"""
    if decimal_odds <= 0:
        return 0.0
    return 1 / decimal_odds


def calculate_expected_value(probability: float, odds: float) -> float:
    """
    Calculate expected value of a bet.

    Returns:
        EV as a decimal (0.05 = 5% edge)
    """
    return (probability * odds) - 1


def calculate_roi(initial: float, final: float) -> float:
    """Calculate ROI percentage"""
    if initial <= 0:
        return 0.0
    return ((final - initial) / initial) * 100


def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
    """
    Calculate Sharpe ratio from returns.

    Args:
        returns: List of periodic returns
        risk_free_rate: Risk-free rate for the period

    Returns:
        Annualized Sharpe ratio
    """
    if not returns or len(returns) < 2:
        return 0.0

    returns = np.array(returns)
    excess_returns = returns - risk_free_rate

    mean_return = np.mean(excess_returns)
    std_return = np.std(excess_returns)

    if std_return == 0:
        return 0.0

    # Annualize (assuming daily returns, 252 trading days)
    return (mean_return / std_return) * np.sqrt(252)


def normalize_team_name(name: str) -> str:
    """
    Normalize team names across different data sources.

    Args:
        name: Raw team name

    Returns:
        Normalized team name
    """
    name_map = {
        # Premier League
        'Man United': 'Manchester United',
        'Man City': 'Manchester City',
        'Spurs': 'Tottenham',
        'Tottenham Hotspur': 'Tottenham',
        'Wolves': 'Wolverhampton',
        'Wolverhampton Wanderers': 'Wolverhampton',
        'Brighton & Hove Albion': 'Brighton',
        'West Ham United': 'West Ham',
        'Newcastle United': 'Newcastle',
        'Leicester City': 'Leicester',
        'Leeds United': 'Leeds',
        'Nottingham Forest': 'Nottm Forest',
        'Luton Town': 'Luton',
        'Sheffield United': 'Sheffield Utd',
        # La Liga
        'Atletico Madrid': 'Atl Madrid',
        'Athletic Bilbao': 'Ath Bilbao',
        # Serie A
        'Inter Milan': 'Inter',
        'AC Milan': 'Milan',
        # Bundesliga
        'Bayern Munich': 'Bayern',
        'Borussia Dortmund': 'Dortmund',
        'RB Leipzig': 'Leipzig',
    }

    return name_map.get(name, name)


def normalize_odds_format(odds: float, format_type: str = 'decimal') -> float:
    """
    Convert odds between formats.

    Args:
        odds: Odds value
        format_type: 'decimal', 'fractional', or 'american'

    Returns:
        Decimal odds
    """
    if format_type == 'decimal':
        return odds
    elif format_type == 'american':
        if odds > 0:
            return (odds / 100) + 1
        else:
            return (100 / abs(odds)) + 1
    elif format_type == 'fractional':
        # Assume odds is numerator/denominator as tuple or string
        if isinstance(odds, str):
            parts = odds.split('/')
            return (float(parts[0]) / float(parts[1])) + 1
        return odds + 1

    return odds


class PerformanceTracker:
    """
    Track betting performance over time.

    Features:
    - Win/loss tracking
    - Bankroll monitoring
    - ROI calculation
    - Streak tracking
    - Profit factor calculation
    """

    def __init__(self, initial_bankroll: float = 1000.0):
        self.initial_bankroll = initial_bankroll
        self.bankroll = initial_bankroll

        self.bets = []
        self.wins = 0
        self.losses = 0
        self.total_staked = 0.0
        self.total_won = 0.0
        self.total_lost = 0.0

        # Streak tracking
        self.current_streak = 0
        self.longest_win_streak = 0
        self.longest_loss_streak = 0

        # Time tracking
        self.equity_curve = [initial_bankroll]
        self.timestamps = [datetime.now()]

    def add_bet(self, stake: float, odds: float, won: bool,
                pnl: float = None, timestamp: datetime = None):
        """
        Record a bet result.

        Args:
            stake: Amount staked
            odds: Decimal odds
            won: Whether the bet won
            pnl: Profit/loss (calculated if not provided)
            timestamp: When the bet was placed
        """
        if pnl is None:
            pnl = stake * (odds - 1) if won else -stake

        self.bets.append({
            'stake': stake,
            'odds': odds,
            'won': won,
            'pnl': pnl,
            'timestamp': timestamp or datetime.now(),
            'bankroll_after': self.bankroll + pnl
        })

        self.bankroll += pnl
        self.total_staked += stake

        if won:
            self.wins += 1
            self.total_won += pnl
            self._update_streak(True)
        else:
            self.losses += 1
            self.total_lost += abs(pnl)
            self._update_streak(False)

        self.equity_curve.append(self.bankroll)
        self.timestamps.append(timestamp or datetime.now())

    def _update_streak(self, won: bool):
        """Update streak tracking"""
        if won:
            if self.current_streak >= 0:
                self.current_streak += 1
            else:
                self.current_streak = 1
            self.longest_win_streak = max(self.longest_win_streak, self.current_streak)
        else:
            if self.current_streak <= 0:
                self.current_streak -= 1
            else:
                self.current_streak = -1
            self.longest_loss_streak = max(self.longest_loss_streak, abs(self.current_streak))

    def get_summary(self) -> Dict:
        """Get comprehensive performance summary"""
        total_bets = self.wins + self.losses

        if total_bets == 0:
            return {
                'total_bets': 0,
                'win_rate': 0,
                'roi': 0,
                'profit_factor': 0
            }

        win_rate = self.wins / total_bets * 100
        roi = calculate_roi(self.initial_bankroll, self.bankroll)
        profit_factor = self.total_won / max(self.total_lost, 0.01)

        # Calculate returns for Sharpe
        if len(self.equity_curve) > 1:
            returns = np.diff(self.equity_curve) / self.equity_curve[:-1]
            sharpe = calculate_sharpe_ratio(returns.tolist())
        else:
            sharpe = 0

        # Calculate max drawdown
        max_drawdown = self._calculate_max_drawdown()

        return {
            'total_bets': total_bets,
            'wins': self.wins,
            'losses': self.losses,
            'win_rate': round(win_rate, 2),
            'total_staked': round(self.total_staked, 2),
            'total_pnl': round(self.bankroll - self.initial_bankroll, 2),
            'roi': round(roi, 2),
            'profit_factor': round(profit_factor, 2),
            'sharpe_ratio': round(sharpe, 2),
            'max_drawdown': round(max_drawdown, 2),
            'current_bankroll': round(self.bankroll, 2),
            'longest_win_streak': self.longest_win_streak,
            'longest_loss_streak': self.longest_loss_streak,
            'current_streak': self.current_streak,
            'avg_stake': round(self.total_staked / max(total_bets, 1), 2),
            'avg_odds': round(
                sum(b['odds'] for b in self.bets) / max(len(self.bets), 1), 2
            )
        }

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

    def get_equity_curve(self) -> Tuple[List[datetime], List[float]]:
        """Get equity curve with timestamps"""
        return self.timestamps, self.equity_curve

    def get_monthly_breakdown(self) -> Dict:
        """Get performance breakdown by month"""
        if not self.bets:
            return {}

        df = pd.DataFrame(self.bets)
        df['month'] = pd.to_datetime(df['timestamp']).dt.to_period('M')

        monthly = df.groupby('month').agg({
            'pnl': 'sum',
            'stake': 'sum',
            'won': ['sum', 'count']
        }).reset_index()

        monthly.columns = ['month', 'pnl', 'staked', 'wins', 'bets']
        monthly['roi'] = (monthly['pnl'] / monthly['staked'] * 100).round(2)
        monthly['win_rate'] = (monthly['wins'] / monthly['bets'] * 100).round(2)

        return monthly.to_dict('records')

    def reset(self):
        """Reset tracker to initial state"""
        self.__init__(self.initial_bankroll)


class BettingValidator:
    """Validate betting data and predictions"""

    @staticmethod
    def validate_odds(odds: float) -> bool:
        """Check if odds are valid"""
        return 1.01 <= odds <= 1000

    @staticmethod
    def validate_probability(prob: float) -> bool:
        """Check if probability is valid"""
        return 0.0 < prob < 1.0

    @staticmethod
    def validate_stake(stake: float, bankroll: float, max_pct: float = 0.05) -> bool:
        """Check if stake is within limits"""
        return 0 < stake <= bankroll * max_pct

    @staticmethod
    def validate_match_data(data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate match data for prediction.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        required_fields = ['homeTeam', 'awayTeam']
        for field in required_fields:
            if field not in data and field.lower().replace('team', '_team') not in data:
                errors.append(f"Missing required field: {field}")

        # Validate odds if present
        for odds_field in ['homeOdds', 'drawOdds', 'awayOdds']:
            if odds_field in data:
                if not BettingValidator.validate_odds(data[odds_field]):
                    errors.append(f"Invalid odds value for {odds_field}: {data[odds_field]}")

        return len(errors) == 0, errors


class OddsConverter:
    """Convert between different odds formats"""

    @staticmethod
    def decimal_to_american(decimal_odds: float) -> int:
        """Convert decimal odds to American"""
        if decimal_odds >= 2.0:
            return int((decimal_odds - 1) * 100)
        else:
            return int(-100 / (decimal_odds - 1))

    @staticmethod
    def american_to_decimal(american_odds: int) -> float:
        """Convert American odds to decimal"""
        if american_odds > 0:
            return (american_odds / 100) + 1
        else:
            return (100 / abs(american_odds)) + 1

    @staticmethod
    def decimal_to_fractional(decimal_odds: float) -> str:
        """Convert decimal odds to fractional string"""
        from fractions import Fraction
        frac = Fraction(decimal_odds - 1).limit_denominator(100)
        return f"{frac.numerator}/{frac.denominator}"

    @staticmethod
    def implied_probability(decimal_odds: float) -> float:
        """Get implied probability from decimal odds"""
        return 1 / decimal_odds if decimal_odds > 0 else 0


# Convenience exports
__all__ = [
    'calculate_kelly_stake',
    'calculate_implied_probability',
    'calculate_expected_value',
    'calculate_roi',
    'calculate_sharpe_ratio',
    'normalize_team_name',
    'normalize_odds_format',
    'PerformanceTracker',
    'BettingValidator',
    'OddsConverter'
]
