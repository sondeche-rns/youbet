"""
Utility Functions for Betting Algorithm
Helper functions for calculations, tracking, and analysis
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json
from pathlib import Path
from typing import List, Dict, Optional


# ============================================================================
# BETTING CALCULATIONS
# ============================================================================

def calculate_kelly_stake(probability: float, odds: float, fraction: float = 0.25) -> float:
    """
    Calculate Kelly Criterion stake size
    
    Args:
        probability: Your estimated probability of winning (0-1)
        odds: Decimal odds offered by bookmaker
        fraction: Fraction of Kelly to use (0.25 = quarter Kelly for safety)
    
    Returns:
        Stake size as decimal (0.02 = 2% of bankroll)
    
    Example:
        >>> calculate_kelly_stake(0.60, 2.50, 0.25)
        0.0333  # 3.33% of bankroll
    """
    b = odds - 1  # Net odds
    p = probability
    q = 1 - p
    
    # Kelly formula: (bp - q) / b
    kelly = (b * p - q) / b
    
    # Apply fractional Kelly for safety
    stake = max(0, kelly * fraction)
    
    # Cap at reasonable maximum (5% of bankroll)
    return min(stake, 0.05)


def calculate_implied_probability(decimal_odds: float) -> float:
    """
    Convert decimal odds to implied probability
    
    Args:
        decimal_odds: Bookmaker's decimal odds
    
    Returns:
        Implied probability (0-1)
    
    Example:
        >>> calculate_implied_probability(2.00)
        0.50  # 50% probability
    """
    return 1 / decimal_odds


def calculate_expected_value(probability: float, odds: float) -> float:
    """
    Calculate expected value of a bet
    
    Args:
        probability: Your estimated probability of winning
        odds: Decimal odds
    
    Returns:
        Expected value as percentage
    
    Example:
        >>> calculate_expected_value(0.60, 2.50)
        0.10  # 10% EV - good bet!
    """
    return (probability * (odds - 1)) - (1 - probability)


def calculate_roi(initial_bankroll: float, final_bankroll: float) -> float:
    """
    Calculate return on investment
    
    Args:
        initial_bankroll: Starting bankroll
        final_bankroll: Ending bankroll
    
    Returns:
        ROI as percentage
    """
    return ((final_bankroll - initial_bankroll) / initial_bankroll) * 100


def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
    """
    Calculate Sharpe ratio for bet returns
    
    Args:
        returns: List of return percentages
        risk_free_rate: Annual risk-free rate (default 2%)
    
    Returns:
        Sharpe ratio (higher is better)
    """
    if not returns or len(returns) < 2:
        return 0.0
    
    returns_array = np.array(returns)
    excess_returns = returns_array - risk_free_rate
    
    if np.std(excess_returns) == 0:
        return 0.0
    
    return np.mean(excess_returns) / np.std(excess_returns)


# ============================================================================
# DATA NORMALIZATION
# ============================================================================

def normalize_team_name(name: str) -> str:
    """
    Normalize team names across different data sources
    
    Args:
        name: Team name from any source
    
    Returns:
        Standardized team name
    """
    name_map = {
        'Man United': 'Manchester United',
        'Man City': 'Manchester City',
        'Spurs': 'Tottenham',
        'Tottenham Hotspur': 'Tottenham',
        'Wolves': 'Wolverhampton',
        'Brighton & Hove Albion': 'Brighton',
        'Newcastle United': 'Newcastle',
        'Nottingham Forest FC': 'Nottingham Forest',
        'West Ham United': 'West Ham',
        'Leicester City': 'Leicester'
    }
    
    return name_map.get(name, name)


def normalize_odds_format(odds: str, format_type: str = 'decimal') -> float:
    """
    Convert odds between different formats
    
    Args:
        odds: Odds in any format (string or float)
        format_type: Target format ('decimal', 'fractional', 'american')
    
    Returns:
        Converted odds
    """
    try:
        # If already decimal
        decimal_odds = float(odds)
        
        if format_type == 'decimal':
            return decimal_odds
        elif format_type == 'fractional':
            return decimal_odds - 1
        elif format_type == 'american':
            if decimal_odds >= 2.0:
                return (decimal_odds - 1) * 100
            else:
                return -100 / (decimal_odds - 1)
    except:
        return 0.0


# ============================================================================
# FORMATTING
# ============================================================================

def format_currency(amount: float, currency: str = '£') -> str:
    """
    Format amount as currency
    
    Example:
        >>> format_currency(1234.56)
        '£1,234.56'
    """
    return f"{currency}{amount:,.2f}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Format value as percentage
    
    Example:
        >>> format_percentage(0.6543, 1)
        '65.4%'
    """
    return f"{value * 100:.{decimals}f}%"


def format_odds(odds: float, decimals: int = 2) -> str:
    """
    Format odds for display
    
    Example:
        >>> format_odds(2.50)
        '2.50'
    """
    return f"{odds:.{decimals}f}"


# ============================================================================
# FILE I/O
# ============================================================================

def save_predictions(predictions: List[Dict], filepath: str):
    """
    Save predictions to JSON file
    
    Args:
        predictions: List of prediction dictionaries
        filepath: Path to save file
    """
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w') as f:
        json.dump(predictions, f, indent=2, default=str)


def load_predictions(filepath: str) -> List[Dict]:
    """
    Load predictions from JSON file
    
    Args:
        filepath: Path to JSON file
    
    Returns:
        List of prediction dictionaries
    """
    with open(filepath, 'r') as f:
        return json.load(f)


def save_dataframe(df: pd.DataFrame, filepath: str, format_type: str = 'csv'):
    """
    Save DataFrame to file
    
    Args:
        df: Pandas DataFrame
        filepath: Output path
        format_type: 'csv', 'excel', or 'json'
    """
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    if format_type == 'csv':
        df.to_csv(filepath, index=False)
    elif format_type == 'excel':
        df.to_excel(filepath, index=False)
    elif format_type == 'json':
        df.to_json(filepath, orient='records', indent=2)


# ============================================================================
# PERFORMANCE TRACKING
# ============================================================================

class PerformanceTracker:
    """
    Track betting performance metrics over time
    """
    
    def __init__(self, initial_bankroll: float = 1000):
        """
        Initialize performance tracker
        
        Args:
            initial_bankroll: Starting bankroll amount
        """
        self.initial_bankroll = initial_bankroll
        self.bankroll = initial_bankroll
        self.bets = []
        
    def add_bet(self, prediction: str, outcome: str, stake: float, 
                odds: float, won: bool):
        """
        Add a bet to the tracker
        
        Args:
            prediction: What was predicted
            outcome: What actually happened
            stake: Amount bet
            odds: Decimal odds
            won: Whether bet won
        """
        pnl = stake * (odds - 1) if won else -stake
        self.bankroll += pnl
        
        self.bets.append({
            'timestamp': datetime.now(),
            'prediction': prediction,
            'outcome': outcome,
            'stake': stake,
            'odds': odds,
            'won': won,
            'pnl': pnl,
            'bankroll': self.bankroll
        })
    
    def get_statistics(self) -> Dict:
        """
        Get comprehensive performance statistics
        
        Returns:
            Dictionary with performance metrics
        """
        if not self.bets:
            return {
                'total_bets': 0,
                'bankroll': self.initial_bankroll
            }
        
        df = pd.DataFrame(self.bets)
        
        wins = df['won'].sum()
        losses = (~df['won']).sum()
        
        winning_bets = df[df['won']]
        losing_bets = df[~df['won']]
        
        return {
            'total_bets': len(self.bets),
            'wins': int(wins),
            'losses': int(losses),
            'win_rate': round(df['won'].mean() * 100, 2),
            'total_staked': round(df['stake'].sum(), 2),
            'total_pnl': round(df['pnl'].sum(), 2),
            'roi': round(calculate_roi(self.initial_bankroll, self.bankroll), 2),
            'average_odds': round(df['odds'].mean(), 2),
            'current_bankroll': round(self.bankroll, 2),
            'profit_factor': round(
                winning_bets['pnl'].sum() / abs(losing_bets['pnl'].sum())
                if len(losing_bets) > 0 and losing_bets['pnl'].sum() != 0
                else 0, 2
            ),
            'average_win': round(winning_bets['pnl'].mean(), 2) if len(winning_bets) > 0 else 0,
            'average_loss': round(losing_bets['pnl'].mean(), 2) if len(losing_bets) > 0 else 0,
            'max_win': round(df['pnl'].max(), 2),
            'max_loss': round(df['pnl'].min(), 2),
            'longest_win_streak': self._calculate_longest_streak(df, True),
            'longest_lose_streak': self._calculate_longest_streak(df, False)
        }
    
    def _calculate_longest_streak(self, df: pd.DataFrame, win: bool) -> int:
        """Calculate longest winning or losing streak"""
        if len(df) == 0:
            return 0
        
        max_streak = 0
        current_streak = 0
        
        for won in df['won']:
            if won == win:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        
        return max_streak
    
    def export_to_csv(self, filepath: str):
        """
        Export betting history to CSV
        
        Args:
            filepath: Output CSV path
        """
        if not self.bets:
            print("No bets to export")
            return
        
        df = pd.DataFrame(self.bets)
        df.to_csv(filepath, index=False)
        print(f"Exported {len(self.bets)} bets to {filepath}")
    
    def get_monthly_performance(self) -> pd.DataFrame:
        """
        Get performance grouped by month
        
        Returns:
            DataFrame with monthly statistics
        """
        if not self.bets:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.bets)
        df['month'] = pd.to_datetime(df['timestamp']).dt.to_period('M')
        
        monthly = df.groupby('month').agg({
            'won': ['sum', 'count'],
            'pnl': 'sum',
            'stake': 'sum'
        }).reset_index()
        
        monthly.columns = ['month', 'wins', 'total_bets', 'pnl', 'total_staked']
        monthly['win_rate'] = (monthly['wins'] / monthly['total_bets'] * 100).round(2)
        monthly['roi'] = (monthly['pnl'] / monthly['total_staked'] * 100).round(2)
        
        return monthly
    
    def reset(self):
        """Reset tracker to initial state"""
        self.bankroll = self.initial_bankroll
        self.bets = []


# ============================================================================
# CONSOLE OUTPUT
# ============================================================================

def print_section_header(title: str):
    """Print a formatted section header"""
    print("\n" + "="*70)
    print(f" {title}")
    print("="*70 + "\n")


def print_subsection(title: str):
    """Print a formatted subsection header"""
    print(f"\n{title}")
    print("-"*70)


def print_table(headers: List[str], rows: List[List], col_widths: Optional[List[int]] = None):
    """
    Print formatted table
    
    Args:
        headers: List of column headers
        rows: List of row data
        col_widths: Optional list of column widths
    """
    if col_widths is None:
        col_widths = [15] * len(headers)
    
    # Print header
    header_row = " | ".join(h.ljust(w) for h, w in zip(headers, col_widths))
    print(header_row)
    print("-" * len(header_row))
    
    # Print rows
    for row in rows:
        row_str = " | ".join(str(cell).ljust(w) for cell, w in zip(row, col_widths))
        print(row_str)


# ============================================================================
# STATISTICAL HELPERS
# ============================================================================

def calculate_confidence_interval(data: List[float], confidence: float = 0.95) -> tuple:
    """
    Calculate confidence interval for data
    
    Args:
        data: List of numerical values
        confidence: Confidence level (default 95%)
    
    Returns:
        Tuple of (lower_bound, upper_bound)
    """
    import scipy.stats as stats
    
    n = len(data)
    mean = np.mean(data)
    std_err = stats.sem(data)
    interval = std_err * stats.t.ppf((1 + confidence) / 2, n - 1)
    
    return (mean - interval, mean + interval)


def calculate_variance(data: List[float]) -> float:
    """Calculate variance of data"""
    return np.var(data)


def calculate_standard_deviation(data: List[float]) -> float:
    """Calculate standard deviation of data"""
    return np.std(data)


# ============================================================================
# VALIDATION
# ============================================================================

def validate_probability(prob: float) -> bool:
    """Check if value is valid probability (0-1)"""
    return 0 <= prob <= 1


def validate_odds(odds: float) -> bool:
    """Check if odds are valid (>= 1.01)"""
    return odds >= 1.01


def validate_bankroll(bankroll: float) -> bool:
    """Check if bankroll is positive"""
    return bankroll > 0


# Example usage
if __name__ == "__main__":
    # Test Kelly calculation
    kelly = calculate_kelly_stake(0.60, 2.50, 0.25)
    print(f"Kelly stake: {kelly*100:.2f}% of bankroll")
    
    # Test performance tracker
    tracker = PerformanceTracker(1000)
    tracker.add_bet('Home Win', 'Home Win', 25, 2.10, True)
    tracker.add_bet('Away Win', 'Draw', 30, 3.50, False)
    
    stats = tracker.get_statistics()
    print(f"\nPerformance: {stats}")