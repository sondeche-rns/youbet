"""
Data Models for Enhanced Betting Algorithm

Contains dataclasses for:
- FactorResult: Standardized factor output with metadata
- MatchContext: Complete match context for advanced factors
- H2HRecord: Head-to-head historical record
- ManagerInfo: Manager information for momentum tracking
- DefensiveStyle: Team defensive style classification

Author: AI Betting Algorithm v2.0
Date: 2026-02-11
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum


class DefensiveStyle(Enum):
    """Team's defensive style classification based on possession"""
    HIGH_PRESS = 'high_press'         # > 55% avg possession
    BALANCED = 'balanced'              # 45-55% possession
    LOW_BLOCK = 'low_block'           # < 45% possession
    COUNTER_ATTACK = 'counter_attack' # Low possession + high efficiency


@dataclass
class FactorResult:
    """
    Standardized output for all prediction factors.

    Provides consistent interface for factor calculations with metadata
    for debugging, calibration, and explanation.

    Attributes:
        name: Factor identifier (e.g., 'h2hAnomaly', 'possessionQuality')
        value: Normalized score from -1.0 to 1.0 (0.5 = neutral, >0.5 favors home)
        weight: The weight to apply (may be dynamic/conditional, 0.0 if inactive)
        triggered: Whether this conditional factor is active for this match
        confidence: 0-100, data quality/completeness score
        explanation: Human-readable explanation for debugging
        metadata: Additional factor-specific data for detailed analysis

    Example:
        FactorResult(
            name='possessionQuality',
            value=0.62,  # Slightly favors home
            weight=0.12,
            triggered=True,
            confidence=85,
            explanation="Home PQI: 2.8 (good), Away PQI: 1.9 (poor)",
            metadata={'home_pqi': 2.8, 'away_pqi': 1.9}
        )
    """
    name: str
    value: float          # -1.0 to 1.0 scale (0.5 = neutral for compatibility)
    weight: float         # actual weight to use (can be 0.0 if not triggered)
    triggered: bool       # was this conditional factor active?
    confidence: int       # 0-100, data completeness/quality
    explanation: str      # human-readable reason
    metadata: Optional[Dict[str, Any]] = None  # extra debugging info

    def __post_init__(self):
        """Validate ranges after initialization"""
        if not (-1.0 <= self.value <= 1.0):
            raise ValueError(f"FactorResult value {self.value} out of range [-1.0, 1.0]")
        if not (0 <= self.confidence <= 100):
            raise ValueError(f"Confidence {self.confidence} out of range [0, 100]")
        if self.weight < 0:
            raise ValueError(f"Weight {self.weight} must be non-negative")
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ManagerInfo:
    """
    Manager information for momentum tracking.

    Tracks manager tenure and results for calculating new manager bounce effect.

    Attributes:
        name: Manager full name
        appointmentDate: Appointment date in ISO format (YYYY-MM-DD)
        gamesManaged: Number of games since appointment
        results: Recent results as list of 'W', 'D', 'L' (most recent last)
        isInterim: True if interim/caretaker manager

    Properties:
        win_rate: Calculate win percentage from results
    """
    name: str
    appointmentDate: str         # ISO format YYYY-MM-DD
    gamesManaged: int           # games since appointment
    results: List[str] = field(default_factory=list)  # ['W', 'D', 'L', ...] recent results
    isInterim: bool = False     # interim manager flag

    @property
    def win_rate(self) -> float:
        """Calculate win rate from results"""
        if not self.results:
            return 0.0
        wins = sum(1 for r in self.results if r == 'W')
        return wins / len(self.results)

    def __post_init__(self):
        """Validate data after initialization"""
        if self.gamesManaged < 0:
            raise ValueError(f"gamesManaged must be non-negative, got {self.gamesManaged}")
        # Validate results are only W/D/L
        for result in self.results:
            if result not in ['W', 'D', 'L']:
                raise ValueError(f"Invalid result '{result}', must be W/D/L")


@dataclass
class H2HRecord:
    """
    Head-to-head record between two teams.

    Tracks historical matchups for H2H analysis and anomaly detection.

    Attributes:
        homeTeam: Home team name
        awayTeam: Away team name
        results: List of historical match results (most recent last)
        weakerTeamUnbeatenStreak: Consecutive H2H without loss for weaker team
        anomalyTriggered: Whether H2H anomaly condition is met

    Properties:
        total_matches: Total H2H matches
        home_wins: Number of home wins
        draws: Number of draws
        away_wins: Number of away wins
    """
    homeTeam: str
    awayTeam: str
    results: List[Dict[str, Any]] = field(default_factory=list)  # [{date, homeScore, awayScore}, ...]
    weakerTeamUnbeatenStreak: int = 0  # consecutive H2H without loss for weaker team
    anomalyTriggered: bool = False      # is anomaly condition met?

    @property
    def total_matches(self) -> int:
        """Total number of H2H matches"""
        return len(self.results)

    @property
    def home_wins(self) -> int:
        """Number of home wins in H2H"""
        return sum(1 for r in self.results if r['homeScore'] > r['awayScore'])

    @property
    def draws(self) -> int:
        """Number of draws in H2H"""
        return sum(1 for r in self.results if r['homeScore'] == r['awayScore'])

    @property
    def away_wins(self) -> int:
        """Number of away wins in H2H"""
        return sum(1 for r in self.results if r['homeScore'] < r['awayScore'])

    def get_win_rate(self, perspective: str = 'home') -> float:
        """
        Get win rate from perspective.

        Args:
            perspective: 'home' or 'away'

        Returns:
            Win rate (0.0-1.0)
        """
        if self.total_matches == 0:
            return 0.0

        if perspective == 'home':
            return self.home_wins / self.total_matches
        else:
            return self.away_wins / self.total_matches


@dataclass
class MatchContext:
    """
    Complete match context for advanced factor calculation.

    Encapsulates all contextual data needed for the 6 new factors:
    - Defensive styles (derived from possession)
    - Manager information (for momentum tracking)
    - League positions (for relegation motivation)
    - Recent form (for motivation and trends)
    - H2H record (for anomaly detection)
    - Season statistics (for possession quality, counter-attack, away draws)

    All optional fields default to None for graceful degradation when data unavailable.
    """
    # Defensive styles (derived from avg possession)
    homeDefensiveStyle: DefensiveStyle
    awayDefensiveStyle: DefensiveStyle

    # Manager info (NEW DATA - may be None if unavailable)
    homeManagerInfo: Optional[ManagerInfo] = None
    awayManagerInfo: Optional[ManagerInfo] = None

    # League standings (EXISTING - from match data)
    homeLeaguePosition: int = 10
    awayLeaguePosition: int = 10

    # Recent form (EXISTING - from match data)
    homeRecentForm: List[str] = field(default_factory=lambda: ['D', 'D', 'D', 'D', 'D'])
    awayRecentForm: List[str] = field(default_factory=lambda: ['D', 'D', 'D', 'D', 'D'])

    # H2H record (NEW DATA - derived from historical data)
    h2hRecord: Optional[H2HRecord] = None

    # Season statistics (DERIVED from historical data)
    # Structure: {'avgPossession': float, 'awayDrawRate': float, 'goalsPerGame': float, ...}
    homeSeasonStats: Optional[Dict[str, Any]] = None
    awaySeasonStats: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate context after initialization"""
        # Ensure form lists contain valid results
        for form in [self.homeRecentForm, self.awayRecentForm]:
            for result in form:
                if result not in ['W', 'D', 'L']:
                    raise ValueError(f"Invalid form result '{result}', must be W/D/L")

        # Ensure positions are valid
        if self.homeLeaguePosition < 1 or self.awayLeaguePosition < 1:
            raise ValueError("League positions must be >= 1")

    def get_recent_wins(self, team: str = 'home', last_n: int = 4) -> int:
        """
        Count recent wins for a team.

        Args:
            team: 'home' or 'away'
            last_n: Number of recent games to consider

        Returns:
            Number of wins in last N games
        """
        form = self.homeRecentForm if team == 'home' else self.awayRecentForm
        recent = form[-last_n:] if len(form) >= last_n else form
        return sum(1 for r in recent if r == 'W')

    def is_relegation_threatened(self, team: str = 'home') -> bool:
        """
        Check if team is in relegation zone (bottom 3).

        Args:
            team: 'home' or 'away'

        Returns:
            True if in bottom 3 positions
        """
        position = self.homeLeaguePosition if team == 'home' else self.awayLeaguePosition
        return position >= 18  # Assuming 20-team league


# Helper functions for creating default contexts
def create_neutral_context() -> MatchContext:
    """
    Create a neutral match context with minimal data.

    Useful as fallback when detailed context cannot be built.
    """
    return MatchContext(
        homeDefensiveStyle=DefensiveStyle.BALANCED,
        awayDefensiveStyle=DefensiveStyle.BALANCED,
        homeManagerInfo=None,
        awayManagerInfo=None,
        homeLeaguePosition=10,
        awayLeaguePosition=10,
        homeRecentForm=['D', 'D', 'D', 'D', 'D'],
        awayRecentForm=['D', 'D', 'D', 'D', 'D'],
        h2hRecord=None,
        homeSeasonStats=None,
        awaySeasonStats=None
    )


def create_minimal_factor_result(name: str, explanation: str = "Factor inactive") -> FactorResult:
    """
    Create an inactive factor result with minimal data.

    Args:
        name: Factor name
        explanation: Explanation for why factor is inactive

    Returns:
        FactorResult with triggered=False and weight=0
    """
    return FactorResult(
        name=name,
        value=0.5,  # Neutral
        weight=0.0,  # Inactive
        triggered=False,
        confidence=0,
        explanation=explanation,
        metadata={}
    )
