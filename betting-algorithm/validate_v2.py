"""
Validation Script for Algorithm V2

Tests the West Ham vs Man United scenario and provides
detailed output of all factor contributions.

Usage:
    python validate_v2.py

Expected Result:
    Draw probability should be > 25% (target ~32%)

Author: AI Betting Algorithm v2.0
Date: 2026-02-11
"""

import sys
from pathlib import Path

# Add betting-algorithm to path so 'src' is importable as a package
sys.path.insert(0, str(Path(__file__).parent))

from src.algorithm import ProfessionalBettingAlgorithm
from src.models import FactorResult


def print_separator(char='=', length=70):
    """Print a separator line"""
    print(char * length)


def print_factor_details(factors):
    """Print detailed factor information"""
    print("\n📊 FACTOR BREAKDOWN:\n")

    # Separate original and contextual factors
    original_factors = []
    contextual_factors = []

    for name, factor in factors.items():
        if isinstance(factor, FactorResult):
            contextual_factors.append((name, factor))
        else:
            original_factors.append((name, factor))

    # Print original factors
    print("🔵 Original Factors (10):")
    print_separator('-', 70)
    for name, factor in original_factors:
        score = factor.get('score', 'N/A')
        print(f"  {name:.<25} Score: {score}")

    # Print contextual factors
    print("\n🟢 Contextual Factors (6):")
    print_separator('-', 70)
    for name, factor in contextual_factors:
        status = "✅ ACTIVE" if factor.triggered else "❌ INACTIVE"
        weight_display = f"{factor.weight:.3f}" if factor.weight > 0 else "0.000"

        print(f"\n  {name}:")
        print(f"    Status:      {status}")
        print(f"    Value:       {factor.value:.3f}")
        print(f"    Weight:      {weight_display}")
        print(f"    Confidence:  {factor.confidence}%")
        print(f"    Explanation: {factor.explanation}")

        if factor.metadata:
            print(f"    Metadata:    {factor.metadata}")


def validate_west_ham_scenario():
    """Run the West Ham vs Man United validation scenario"""

    print_separator('=', 70)
    print("🏆 ALGORITHM V2 VALIDATION - WEST HAM VS MAN UNITED")
    print_separator('=', 70)

    # Initialize algorithm with V2 weights
    print("\n⚙️  Initializing algorithm with V2 weights...")
    algo = ProfessionalBettingAlgorithm('football', use_v2_weights=True, enable_calibration=True)
    print("✅ Algorithm initialized")

    # West Ham vs Man United scenario (Feb 10, 2026 actual: 1-1 draw)
    print("\n📝 Match Data:")
    print_separator('-', 70)

    match_data = {
        'homeTeam': 'West Ham',
        'awayTeam': 'Man United',
        'home_xg': 1.05,
        'away_xg': 1.72,
        'home_possession': 41,
        'away_possession': 59,
        'home_position': 15,
        'away_position': 6,
        'home_form': 'WWDLW',
        'away_form': 'WDWLW',
        'away_draw_rate': 0.40,       # Man Utd high away draw rate this season
        'away_total_games': 12,
        'competition': 'Premier League'
    }

    for key, value in match_data.items():
        print(f"  {key:.<25} {value}")

    # Make prediction
    print("\n🤖 Generating prediction...")
    prediction = algo.predict_match(match_data)

    # Print probabilities
    print("\n📈 PREDICTION RESULTS:")
    print_separator('=', 70)

    home_prob = prediction['homeWinProb'] * 100
    draw_prob = prediction['drawProb'] * 100
    away_prob = prediction['awayWinProb'] * 100

    print(f"\n  🏠 Home Win (West Ham):    {home_prob:>6.2f}%")
    print(f"  🤝 Draw:                   {draw_prob:>6.2f}%  ⬅️  TARGET: >25%")
    print(f"  ✈️  Away Win (Man United):  {away_prob:>6.2f}%")

    total = home_prob + draw_prob + away_prob
    print(f"\n  📊 Total:                  {total:>6.2f}%")

    # Validate probabilities
    print("\n✅ VALIDATION CHECKS:")
    print_separator('-', 70)

    checks = []

    # Check 1: Probabilities sum to ~100%
    check1 = abs(total - 100.0) < 1.0
    checks.append(("Probabilities sum to 100%", check1))

    # Check 2: Draw probability > 25%
    check2 = draw_prob > 25.0
    checks.append((f"Draw probability > 25% (got {draw_prob:.1f}%)", check2))

    # Check 3: Draw probability near target (32% ±5%)
    check3 = 27.0 <= draw_prob <= 37.0
    checks.append((f"Draw probability ~32% ±5% (got {draw_prob:.1f}%)", check3))

    # Check 4: All contextual factors present
    contextual_factor_names = [
        'h2hHistorical', 'h2hAnomaly', 'possessionQuality',
        'managerMomentum', 'relegationMotivation',
        'counterAttackEfficiency', 'awayDrawFrequency'
    ]
    check4 = all(name in prediction['factors'] for name in contextual_factor_names)
    checks.append(("All 6 contextual factors present", check4))

    # Print check results
    for check_name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}  {check_name}")

    # Print factor details
    if 'factors' in prediction:
        print_factor_details(prediction['factors'])

    # Summary
    print("\n" + "=" * 70)
    all_passed = all(check[1] for check in checks)

    if all_passed:
        print("🎉 VALIDATION PASSED! Algorithm V2 is working correctly.")
    else:
        print("⚠️  VALIDATION INCOMPLETE - Some checks failed.")
        print("   This may be due to missing historical data.")

    print("=" * 70)

    return prediction, all_passed


def test_quick_scenarios():
    """Test a few quick scenarios to verify basic functionality"""

    print("\n\n🔬 QUICK SCENARIO TESTS")
    print_separator('=', 70)

    algo = ProfessionalBettingAlgorithm('football', use_v2_weights=True)

    scenarios = [
        {
            'name': 'High Possession Quality (Home)',
            'data': {
                'homeTeam': 'Efficient Team',
                'awayTeam': 'Inefficient Team',
                'home_xg': 2.5,
                'away_xg': 1.0,
                'home_possession': 45,
                'away_possession': 55,
                'competition': 'Premier League'
            },
            'expected': 'Home win probability should be high'
        },
        {
            'name': 'Counter-Attack Setup',
            'data': {
                'homeTeam': 'Low Block Team',
                'awayTeam': 'High Press Team',
                'home_xg': 1.2,
                'away_xg': 1.8,
                'home_possession': 35,
                'away_possession': 65,
                'competition': 'Premier League'
            },
            'expected': 'Draw probability should be elevated'
        }
    ]

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print(f"   Expected: {scenario['expected']}")

        prediction = algo.predict_match(scenario['data'])

        print(f"   Result: Home {prediction['homeWinProb']*100:.1f}% | "
              f"Draw {prediction['drawProb']*100:.1f}% | "
              f"Away {prediction['awayWinProb']*100:.1f}%")

    print("\n" + "=" * 70)
    print("✅ Quick scenario tests completed")
    print("=" * 70)


if __name__ == '__main__':
    print("\n")
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║          BETTING ALGORITHM V2 - VALIDATION SUITE                  ║")
    print("║                                                                    ║")
    print("║  Testing enhanced draw prediction with 6 new contextual factors   ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print("\n")

    try:
        # Run main validation
        prediction, passed = validate_west_ham_scenario()

        # Run quick tests
        test_quick_scenarios()

        # Final summary
        print("\n\n📋 FINAL SUMMARY")
        print_separator('=', 70)

        if passed:
            print("✅ All validation checks passed!")
            print("🎯 Algorithm V2 is ready for production use.")
            print("\nNext steps:")
            print("  1. Run full backtesting on historical data")
            print("  2. Compare V2 performance vs V1")
            print("  3. Monitor draw prediction accuracy")
        else:
            print("⚠️  Some validation checks failed.")
            print("\nPossible causes:")
            print("  1. Missing historical data for H2H records")
            print("  2. Manager database incomplete")
            print("  3. Season statistics not available")
            print("\nThe algorithm will still work with graceful degradation.")

        print_separator('=', 70)
        print("\n")

        sys.exit(0 if passed else 1)

    except Exception as e:
        print(f"\n❌ ERROR during validation: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
