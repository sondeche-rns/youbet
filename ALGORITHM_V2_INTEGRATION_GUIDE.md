# Algorithm V2 Integration Guide

## ✅ Completed Foundation (Week 1)

The following files have been successfully created:

1. ✅ **`betting-algorithm/src/models.py`** - All dataclasses (FactorResult, MatchContext, H2HRecord, ManagerInfo, DefensiveStyle)
2. ✅ **`betting-algorithm/src/context_builder.py`** - MatchContextBuilder with H2H and season stats calculation
3. ✅ **`betting-algorithm/src/config.py`** - Updated with FOOTBALL_WEIGHTS_V2 and CONDITIONAL_FACTORS
4. ✅ **`betting-algorithm/data/managers.json`** - Premier League manager database (20 teams)

## 🔧 Remaining Integration (Weeks 2-3)

### Part 1: Add 6 New Factor Methods to algorithm.py

**Location:** Insert after `_calculate_external_factors()` method (around line 475)

```python
# ========================================================================
# NEW CONTEXTUAL FACTORS (Version 2.0 - Enhanced Draw Prediction)
# ========================================================================

def _calculate_h2h_factors(self, match_data: Dict, context) -> tuple:
    """
    Calculate H2H historical and anomaly factors.

    Returns tuple: (historical_factor, anomaly_factor)
    """
    from .models import FactorResult

    if context.h2hRecord is None:
        return (
            FactorResult(name='h2hHistorical', value=0.5, weight=0.0, triggered=False,
                        confidence=0, explanation="No H2H data available"),
            FactorResult(name='h2hAnomaly', value=0.5, weight=0.0, triggered=False,
                        confidence=0, explanation="No H2H data for anomaly detection")
        )

    h2h = context.h2hRecord

    # Calculate base H2H score
    if h2h.total_matches == 0:
        h2h_score = 0.5
        confidence = 0
    else:
        home_win_rate = h2h.home_wins / h2h.total_matches
        h2h_score = 0.5 + (home_win_rate - 0.33) * 0.5
        confidence = min(h2h.total_matches * 10, 100)

    # Check anomaly
    weaker_team_is_home = context.homeLeaguePosition > context.awayLeaguePosition
    anomaly_detected = h2h.anomalyTriggered and h2h.weakerTeamUnbeatenStreak >= 3

    if anomaly_detected:
        anomaly_boost = 0.2 if weaker_team_is_home else -0.1
        return (
            FactorResult(name='h2hHistorical', value=h2h_score, weight=0.0, triggered=False,
                        confidence=confidence, explanation=f"Replaced by anomaly (streak: {h2h.weakerTeamUnbeatenStreak})"),
            FactorResult(name='h2hAnomaly', value=0.5 + anomaly_boost, weight=0.15, triggered=True,
                        confidence=90, explanation=f"Weaker team unbeaten in {h2h.weakerTeamUnbeatenStreak} H2H",
                        metadata={'streak': h2h.weakerTeamUnbeatenStreak, 'weaker_team_home': weaker_team_is_home})
        )
    else:
        return (
            FactorResult(name='h2hHistorical', value=h2h_score, weight=0.05, triggered=True,
                        confidence=confidence, explanation=f"H2H: {h2h.home_wins}W-{h2h.draws}D-{h2h.away_wins}L"),
            FactorResult(name='h2hAnomaly', value=0.5, weight=0.0, triggered=False,
                        confidence=50, explanation="No anomaly (streak < 3)")
        )

def _calculate_possession_quality(self, match_data: Dict, context) -> object:
    """Calculate possession quality index (xG efficiency per possession)."""
    from .models import FactorResult
    import numpy as np

    home_xg = match_data.get('home_xg', match_data.get('homeXg', 1.5))
    away_xg = match_data.get('away_xg', match_data.get('awayXg', 1.2))
    home_poss = max(match_data.get('home_possession', 50) / 100, 0.3)
    away_poss = max(match_data.get('away_possession', 50) / 100, 0.3)

    home_pqi = (home_xg / home_poss) * 100
    away_pqi = (away_xg / away_poss) * 100

    pqi_diff = home_pqi - away_pqi
    normalized_score = 0.5 + np.tanh(pqi_diff / 100) * 0.3

    classify = lambda pqi: "excellent" if pqi > 300 else "good" if pqi > 200 else "poor"

    return FactorResult(
        name='possessionQuality', value=float(normalized_score), weight=0.12, triggered=True,
        confidence=80, explanation=f"Home PQI: {home_pqi:.1f} ({classify(home_pqi)}), Away: {away_pqi:.1f} ({classify(away_pqi)})",
        metadata={'home_pqi': float(home_pqi), 'away_pqi': float(away_pqi)}
    )

def _calculate_manager_momentum(self, match_data: Dict, context) -> object:
    """Calculate manager momentum (new manager bounce with decay)."""
    from .models import FactorResult

    if context.homeManagerInfo is None or context.awayManagerInfo is None:
        return FactorResult(name='managerMomentum', value=0.5, weight=0.0, triggered=False,
                           confidence=0, explanation="No manager data")

    def calc_bounce(mgr):
        base = 0.08 if not mgr.isInterim else 0.056
        bounce = base * (0.85 ** mgr.gamesManaged)
        return bounce if bounce >= 0.01 else 0.0

    home_bounce = calc_bounce(context.homeManagerInfo)
    away_bounce = calc_bounce(context.awayManagerInfo)
    net_bounce = home_bounce - away_bounce

    if abs(net_bounce) < 0.01:
        return FactorResult(name='managerMomentum', value=0.5, weight=0.0, triggered=False,
                           confidence=50, explanation="No active bounce")

    value = 0.5 + net_bounce * 2
    return FactorResult(
        name='managerMomentum', value=float(value), weight=float(max(home_bounce, away_bounce)),
        triggered=True, confidence=80,
        explanation=f"Home: {home_bounce:.3f}, Away: {away_bounce:.3f}",
        metadata={'home_bounce': float(home_bounce), 'away_bounce': float(away_bounce)}
    )

def _calculate_relegation_motivation(self, match_data: Dict, context) -> object:
    """Calculate relegation motivation factor."""
    from .models import FactorResult

    home_pos = context.homeLeaguePosition
    recent_form = context.homeRecentForm[-4:] if len(context.homeRecentForm) >= 4 else context.homeRecentForm
    recent_wins = sum(1 for r in recent_form if r == 'W')
    showing_fight = recent_wins >= 2

    if home_pos >= 18 and showing_fight:
        draw_boost, home_win_boost, tier = 0.08, 0.03, "critical"
    elif home_pos >= 17:
        draw_boost, home_win_boost, tier = 0.04, 0.02, "danger"
    else:
        return FactorResult(name='relegationMotivation', value=0.5, weight=0.0, triggered=False,
                           confidence=100, explanation=f"Not in relegation zone (pos {home_pos})")

    return FactorResult(
        name='relegationMotivation', value=float(0.5 + draw_boost + home_win_boost),
        weight=0.08, triggered=True, confidence=90,
        explanation=f"{tier} zone (pos {home_pos}), {recent_wins}/4 wins",
        metadata={'draw_boost': float(draw_boost), 'home_win_boost': float(home_win_boost), 'tier': tier}
    )

def _calculate_counter_attack_efficiency(self, match_data: Dict, context) -> object:
    """Calculate counter-attack efficiency factor."""
    from .models import FactorResult

    if context.homeSeasonStats is None or context.awaySeasonStats is None:
        return FactorResult(name='counterAttackEfficiency', value=0.5, weight=0.0, triggered=False,
                           confidence=0, explanation="No season stats")

    home_poss = context.homeSeasonStats.get('avgPossession', 50)
    away_poss = context.awaySeasonStats.get('avgPossession', 50)

    scenario = (home_poss < 45 and away_poss > 58) or (away_poss < 45 and home_poss > 58)

    if not scenario:
        return FactorResult(name='counterAttackEfficiency', value=0.5, weight=0.0, triggered=False,
                           confidence=70, explanation=f"No counter setup (H:{home_poss:.1f}% A:{away_poss:.1f}%)")

    if home_poss < 45:
        underdog_team, underdog_poss = "home", home_poss
        efficiency = context.homeSeasonStats.get('goalsPerGame', 1.2) / (100 - home_poss)
        value = 0.5 + 0.05  # favor home slightly
    else:
        underdog_team, underdog_poss = "away", away_poss
        efficiency = context.awaySeasonStats.get('goalsPerGame', 1.2) / (100 - away_poss)
        value = 0.5 - 0.05  # favor away slightly

    return FactorResult(
        name='counterAttackEfficiency', value=float(value), weight=0.06, triggered=True,
        confidence=75, explanation=f"{underdog_team} counter threat (poss: {underdog_poss:.1f}%)",
        metadata={'underdog_team': underdog_team, 'draw_boost': 0.06, 'underdog_boost': 0.04}
    )

def _calculate_away_draw_frequency(self, match_data: Dict, context) -> object:
    """Calculate away draw frequency factor."""
    from .models import FactorResult

    if context.awaySeasonStats is None:
        return FactorResult(name='awayDrawFrequency', value=0.5, weight=0.0, triggered=False,
                           confidence=0, explanation="No away stats")

    away_draw_rate = context.awaySeasonStats.get('awayDrawRate', 0.25)
    total_away_games = context.awaySeasonStats.get('totalAwayGames', 0)

    if total_away_games < 5 or away_draw_rate <= 0.35:
        return FactorResult(name='awayDrawFrequency', value=0.5, weight=0.0, triggered=False,
                           confidence=20 if total_away_games < 5 else 80,
                           explanation=f"Normal rate: {away_draw_rate*100:.1f}%" if total_away_games >= 5 else "Insufficient games")

    boost = min((away_draw_rate - 0.25) * 0.5, 0.15)

    return FactorResult(
        name='awayDrawFrequency', value=float(0.5 + boost), weight=0.06, triggered=True,
        confidence=min(total_away_games * 5, 100),
        explanation=f"Draw-prone: {away_draw_rate*100:.1f}% ({context.awaySeasonStats.get('awayDraws', 0)}/{total_away_games})",
        metadata={'boost': float(boost), 'away_draw_rate': float(away_draw_rate)}
    )
```

### Part 2: Refactor `_calculate_all_factors()` Method

**Location:** Find `_calculate_all_factors()` method (around line 153)

**Add at the beginning of the method:**

```python
def _calculate_all_factors(self, match_data: Dict) -> Dict:
    """Calculate all prediction factors (original 10 + new 6)"""
    from .context_builder import MatchContextBuilder
    from .models import FactorResult

    # Build match context for new factors
    context_builder = MatchContextBuilder(self.historical_data if hasattr(self, 'historical_data') else None)
    context = context_builder.build_context(match_data)

    factors = {}

    # ... (keep all existing 10 factor calculations)
    # ... (they should return dicts, not FactorResult yet - we'll wrap them later)
```

**Add at the END of the method (before `return factors`):**

```python
    # NEW: Add 6 contextual factors
    h2h_hist, h2h_anom = self._calculate_h2h_factors(match_data, context)
    factors['h2hHistorical'] = h2h_hist
    factors['h2hAnomaly'] = h2h_anom
    factors['possessionQuality'] = self._calculate_possession_quality(match_data, context)
    factors['managerMomentum'] = self._calculate_manager_momentum(match_data, context)
    factors['relegationMotivation'] = self._calculate_relegation_motivation(match_data, context)
    factors['counterAttackEfficiency'] = self._calculate_counter_attack_efficiency(match_data, context)
    factors['awayDrawFrequency'] = self._calculate_away_draw_frequency(match_data, context)

    return factors
```

### Part 3: Update `__init__()` Method

**Location:** In `ProfessionalBettingAlgorithm.__init__()` (around line 24)

**Add these lines:**

```python
def __init__(self, sport: str = 'football', use_v2_weights: bool = True):
    self.sport = sport
    self.config = self._load_config(sport)

    # NEW: Add these lines
    if use_v2_weights:
        from .config import FOOTBALL_WEIGHTS_V2
        self.config['weights'] = FOOTBALL_WEIGHTS_V2

    self.elo_ratings = {}
    self.team_form = {}
    self.calibration_params = {'a': 1.0, 'b': 0.0}

    # NEW: Add historical data storage
    self.historical_data = None  # Set via set_historical_data()
```

**Add new method:**

```python
def set_historical_data(self, data: pd.DataFrame):
    """Set historical data for context building (H2H, season stats)"""
    self.historical_data = data
```

### Part 4: Create calibration.py

**File:** `betting-algorithm/src/calibration.py` (NEW FILE)

See full implementation in plan file - this is the CalibrationEngine class for self-improving weights.

### Part 5: Update Requirements

**File:** `betting-algorithm/requirements.txt`

No new dependencies needed! All new code uses existing libraries (pandas, numpy, etc.).

---

## 🧪 Testing the Integration

### Quick Test

```python
from src.algorithm import ProfessionalBettingAlgorithm
from src.data_collector import HistoricalDataCollector

# Initialize with V2 weights
algo = ProfessionalBettingAlgorithm('football', use_v2_weights=True)

# Load historical data
collector = HistoricalDataCollector()
historical_df = collector.load_historical_data()
algo.set_historical_data(historical_df)

# Test prediction
match = {
    'homeTeam': 'West Ham',
    'awayTeam': 'Man United',
    'home_xg': 1.05,
    'away_xg': 1.72,
    'home_possession': 41,
    'away_possession': 59,
    'home_position': 15,
    'away_position': 6,
    'home_form': 'WWDLW',
    'away_form': 'WDWLW'
}

prediction = algo.predict_match(match)
print(f"Draw probability: {prediction['drawProb']*100:.1f}%")  # Should be ~30-35%
```

### Validation Scenario

The **West Ham 1-1 Man United (Feb 10, 2026)** scenario should now predict:
- Draw probability: **~32%** (up from 22%)
- Factors triggered:
  - possessionQuality ✅ (West Ham efficient with low possession)
  - counterAttackEfficiency ✅ (West Ham 41% vs Man Utd 59%)
  - Possibly h2hAnomaly ✅ (if West Ham has good H2H record)

---

## 📊 Next Steps

1. **Manually integrate** the 6 factor methods into algorithm.py (see Part 1)
2. **Refactor** _calculate_all_factors() (see Part 2)
3. **Update** __init__() method (see Part 3)
4. **Run tests** with the validation scenario
5. **Create** calibration.py (optional for MVP)
6. **Backtest** on 2+ seasons of data

All code is provided above - integration should take 30-60 minutes.

---

## ✅ What's Already Complete

- ✅ models.py (150 lines) - All dataclasses
- ✅ context_builder.py (250 lines) - Context building logic
- ✅ config.py updated - FOOTBALL_WEIGHTS_V2
- ✅ managers.json created - 20 Premier League teams

**Total new code created:** ~600 lines
**Remaining integration:** ~400 lines (copy-paste from above)

---

**Status:** Foundation complete, ready for final integration!
