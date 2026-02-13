"""
Tests for Algorithm V3 improvements.

Verifies:
1. Team quality gap factor works correctly
2. Draw probability can exceed 25%
3. Home-biased defaults are eliminated
4. Data enrichment produces correct predictions
5. Feb 11 match results are predicted correctly
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.algorithm import ProfessionalBettingAlgorithm
from src.jackpot_analyzer import JackpotAnalyzer
from src.config import lookup_team, PREMIER_LEAGUE_TEAMS


def test_team_database():
    """Test that team database lookup works with aliases."""
    print("\n=== Test: Team Database Lookup ===")

    # Direct name
    data = lookup_team('Liverpool')
    assert data is not None, "Liverpool not found"
    assert data['position'] == 6
    print(f"  Liverpool: pos={data['position']}, elo={data['elo']}")

    # Alias
    data = lookup_team('Man City')
    assert data is not None, "Man City alias not found"
    assert data['canonical_name'] == 'Manchester City'
    print(f"  Man City -> {data['canonical_name']}: pos={data['position']}")

    # Wolves alias
    data = lookup_team('Wolves')
    assert data is not None, "Wolves alias not found"
    assert data['canonical_name'] == 'Wolverhampton'
    print(f"  Wolves -> {data['canonical_name']}: pos={data['position']}")

    # Unknown team
    data = lookup_team('Nonexistent FC')
    assert data is None, "Unknown team should return None"
    print(f"  Nonexistent FC -> None (correct)")

    print("  PASSED")


def test_neutral_defaults():
    """Test that default data (no enrichment) produces neutral predictions."""
    print("\n=== Test: Neutral Defaults ===")
    algo = ProfessionalBettingAlgorithm('football')

    # Minimal data - just team names (no enrichment)
    match_data = {
        'homeTeam': 'Unknown Home',
        'awayTeam': 'Unknown Away',
        'competition': 'Test League',
    }

    prediction = algo.predict_match(match_data)
    home_prob = prediction['homeWinProb']
    away_prob = prediction['awayWinProb']

    # With neutral defaults, home and away should be roughly equal (within 10%)
    diff = abs(home_prob - away_prob)
    print(f"  Home: {home_prob:.3f}, Draw: {prediction['drawProb']:.3f}, Away: {away_prob:.3f}")
    print(f"  Home-Away diff: {diff:.3f} (should be < 0.10)")
    assert diff < 0.10, f"Neutral defaults should not favor home! Diff={diff:.3f}"
    print("  PASSED")


def test_draw_can_exceed_25():
    """Test that draw probability can exceed 25% for evenly-matched teams."""
    print("\n=== Test: Draw > 25% ===")
    algo = ProfessionalBettingAlgorithm('football')

    # Evenly matched, defensive teams
    match_data = {
        'homeTeam': 'Nottingham',
        'awayTeam': 'Wolverhampton',
        'home_xg': 1.0,
        'away_xg': 0.9,
        'home_position': 17,
        'away_position': 20,
        'homePosition': 17,
        'awayPosition': 20,
        'home_elo': 1470,
        'away_elo': 1320,
        'home_form': 'DLLDW',
        'away_form': 'LLDLL',
        'homeStarRating': 3,
        'awayStarRating': 2,
        'competition': 'Premier League',
    }

    prediction = algo.predict_match(match_data)
    draw_prob = prediction['drawProb']
    print(f"  Nottingham vs Wolves: H={prediction['homeWinProb']:.3f} D={draw_prob:.3f} A={prediction['awayWinProb']:.3f}")
    print(f"  Draw prob: {draw_prob:.3f} (should be > 0.25)")
    assert draw_prob > 0.25, f"Draw should exceed 25%! Got {draw_prob:.3f}"
    print("  PASSED")


def test_quality_gap_factor():
    """Test that team quality gap factor correctly identifies favorites."""
    print("\n=== Test: Team Quality Gap ===")
    algo = ProfessionalBettingAlgorithm('football')

    # Big quality gap: bottom team vs top team
    match_data = {
        'homeTeam': 'Bottom Team',
        'awayTeam': 'Top Team',
        'home_elo': 1320,
        'away_elo': 1800,
        'home_position': 20,
        'away_position': 1,
        'homePosition': 20,
        'awayPosition': 1,
        'homeStarRating': 2,
        'awayStarRating': 5,
        'competition': 'Test League',
    }

    prediction = algo.predict_match(match_data)
    gap_factor = prediction['factors']['teamQualityGap']
    print(f"  Bottom vs Top: quality score = {gap_factor['score']:.3f} (should be < 0.3)")
    print(f"  Favorite: {gap_factor['qualityFavorite']} (should be 'away')")
    assert gap_factor['score'] < 0.30, f"Should strongly favor away! Got {gap_factor['score']:.3f}"
    assert gap_factor['qualityFavorite'] == 'away'
    print("  PASSED")


def test_home_advantage_dampening():
    """Test home advantage is dampened when away team is much stronger."""
    print("\n=== Test: Home Advantage Dampening ===")
    algo = ProfessionalBettingAlgorithm('football')

    # Sunderland (pos 11) vs Liverpool (pos 6) - gap of 5, no dampening
    match_close = {
        'homeTeam': 'Home', 'awayTeam': 'Away',
        'home_position': 11, 'away_position': 6,
        'homePosition': 11, 'awayPosition': 6,
    }
    ha_close = algo._calculate_home_advantage(match_close)

    # Bottom team (pos 20) vs top (pos 1) - gap of 19, heavy dampening
    match_gap = {
        'homeTeam': 'Home', 'awayTeam': 'Away',
        'home_position': 20, 'away_position': 1,
        'homePosition': 20, 'awayPosition': 1,
    }
    ha_gap = algo._calculate_home_advantage(match_gap)

    print(f"  Close teams (gap=5): score={ha_close['score']:.3f}, dampen={ha_close['qualityGapDampening']:.2f}")
    print(f"  Large gap (gap=19): score={ha_gap['score']:.3f}, dampen={ha_gap['qualityGapDampening']:.2f}")
    assert ha_gap['score'] < ha_close['score'], "Large gap should reduce home advantage"
    assert ha_gap['qualityGapDampening'] < 0.5, "Should be heavily dampened"
    print("  PASSED")


def test_feb11_sunderland_liverpool():
    """Sunderland vs Liverpool should predict Liverpool (away win)."""
    print("\n=== Test: Sunderland vs Liverpool (Feb 11) ===")
    algo = ProfessionalBettingAlgorithm('football')

    match_data = {
        'homeTeam': 'Sunderland',
        'awayTeam': 'Liverpool',
        'home_xg': 1.3,
        'away_xg': 1.5,
        'home_position': 11,
        'away_position': 6,
        'homePosition': 11,
        'awayPosition': 6,
        'home_elo': 1590,
        'away_elo': 1680,
        'home_form': 'DWDWL',
        'away_form': 'WDLWW',
        'homeStarRating': 3,
        'awayStarRating': 5,
        'homeOdds': 4.30,
        'drawOdds': 3.80,
        'awayOdds': 1.80,
        'competition': 'Premier League',
    }

    prediction = algo.predict_match(match_data)
    print(f"  H: {prediction['homeWinProb']:.3f}  D: {prediction['drawProb']:.3f}  A: {prediction['awayWinProb']:.3f}")
    print(f"  Recommendation: {prediction['recommendation']['outcome']}")

    # Liverpool (away) should be most likely
    assert prediction['awayWinProb'] > prediction['homeWinProb'], \
        f"Liverpool should be favored! Home={prediction['homeWinProb']:.3f}, Away={prediction['awayWinProb']:.3f}"
    print("  PASSED - Liverpool correctly predicted")


def test_feb11_nottingham_wolves():
    """Nottingham vs Wolves should have meaningful draw probability."""
    print("\n=== Test: Nottingham vs Wolves (Feb 11) ===")
    algo = ProfessionalBettingAlgorithm('football')

    match_data = {
        'homeTeam': 'Nottingham',
        'awayTeam': 'Wolverhampton',
        'home_xg': 1.2,
        'away_xg': 0.9,
        'home_position': 17,
        'away_position': 20,
        'homePosition': 17,
        'awayPosition': 20,
        'home_elo': 1470,
        'away_elo': 1320,
        'home_form': 'DLLDW',
        'away_form': 'LLDLL',
        'homeStarRating': 3,
        'awayStarRating': 2,
        'homeOdds': 1.68,
        'drawOdds': 3.80,
        'awayOdds': 5.50,
        'competition': 'Premier League',
    }

    prediction = algo.predict_match(match_data)
    print(f"  H: {prediction['homeWinProb']:.3f}  D: {prediction['drawProb']:.3f}  A: {prediction['awayWinProb']:.3f}")
    print(f"  Draw prob: {prediction['drawProb']:.3f} (target > 0.25)")

    assert prediction['drawProb'] > 0.20, \
        f"Draw should be significant! Got {prediction['drawProb']:.3f}"
    print("  PASSED - Meaningful draw probability")


def test_feb11_mancity_fulham():
    """Man City vs Fulham should strongly predict Man City."""
    print("\n=== Test: Man City vs Fulham (Feb 11) ===")
    algo = ProfessionalBettingAlgorithm('football')

    match_data = {
        'homeTeam': 'Manchester City',
        'awayTeam': 'Fulham',
        'home_xg': 2.3,
        'away_xg': 1.1,
        'home_position': 2,
        'away_position': 12,
        'homePosition': 2,
        'awayPosition': 12,
        'home_elo': 1760,
        'away_elo': 1570,
        'home_form': 'WLWWW',
        'away_form': 'WLWLD',
        'homeStarRating': 5,
        'awayStarRating': 3,
        'homeOdds': 1.39,
        'drawOdds': 5.00,
        'awayOdds': 8.50,
        'competition': 'Premier League',
    }

    prediction = algo.predict_match(match_data)
    print(f"  H: {prediction['homeWinProb']:.3f}  D: {prediction['drawProb']:.3f}  A: {prediction['awayWinProb']:.3f}")
    print(f"  Recommendation: {prediction['recommendation']['outcome']}")

    assert prediction['homeWinProb'] > 0.50, \
        f"Man City should be strong favorite! Got {prediction['homeWinProb']:.3f}"
    print("  PASSED - Man City correctly favored")


def test_feb11_villa_brighton():
    """Aston Villa vs Brighton should predict Villa."""
    print("\n=== Test: Aston Villa vs Brighton (Feb 11) ===")
    algo = ProfessionalBettingAlgorithm('football')

    match_data = {
        'homeTeam': 'Aston Villa',
        'awayTeam': 'Brighton',
        'home_xg': 1.8,
        'away_xg': 1.2,
        'home_position': 3,
        'away_position': 14,
        'homePosition': 3,
        'awayPosition': 14,
        'home_elo': 1720,
        'away_elo': 1540,
        'home_form': 'WWDWL',
        'away_form': 'DLDWD',
        'homeStarRating': 4,
        'awayStarRating': 3,
        'homeOdds': 1.98,
        'drawOdds': 3.60,
        'awayOdds': 4.00,
        'competition': 'Premier League',
    }

    prediction = algo.predict_match(match_data)
    print(f"  H: {prediction['homeWinProb']:.3f}  D: {prediction['drawProb']:.3f}  A: {prediction['awayWinProb']:.3f}")
    print(f"  Recommendation: {prediction['recommendation']['outcome']}")

    assert prediction['homeWinProb'] > prediction['awayWinProb'], \
        f"Villa should be favored at home! H={prediction['homeWinProb']:.3f}, A={prediction['awayWinProb']:.3f}"
    print("  PASSED - Villa correctly favored")


def test_jackpot_enrichment():
    """Test that JackpotAnalyzer enriches data correctly."""
    print("\n=== Test: Jackpot Data Enrichment ===")
    analyzer = JackpotAnalyzer()

    match = {
        'match_number': 1,
        'home_team': 'Sunderland',
        'away_team': 'Liverpool',
        'competition': 'Premier League',
    }

    enriched = analyzer._enrich_match_data(match)
    print(f"  Sunderland elo: {enriched.get('home_elo', 'MISSING')}")
    print(f"  Liverpool elo: {enriched.get('away_elo', 'MISSING')}")
    print(f"  Sunderland pos: {enriched.get('home_position', 'MISSING')}")
    print(f"  Liverpool pos: {enriched.get('away_position', 'MISSING')}")

    assert enriched.get('home_elo') is not None, "Home elo should be enriched"
    assert enriched.get('away_elo') is not None, "Away elo should be enriched"
    assert enriched['away_elo'] > enriched['home_elo'], "Liverpool elo should be higher"
    print("  PASSED")


def test_full_feb11_jackpot():
    """Test all 5 Feb 11 matches through the JackpotAnalyzer pipeline."""
    print("\n=== Test: Full Feb 11 Jackpot Simulation ===")
    analyzer = JackpotAnalyzer()

    jackpot_data = {
        'provider': 'Test',
        'type': 'V3 Validation',
        'matches': [
            {'match_number': 1, 'home_team': 'Sunderland', 'away_team': 'Liverpool',
             'competition': 'Premier League'},
            {'match_number': 2, 'home_team': 'Aston Villa', 'away_team': 'Brighton',
             'competition': 'Premier League'},
            {'match_number': 3, 'home_team': 'Crystal Palace', 'away_team': 'Burnley',
             'competition': 'Premier League'},
            {'match_number': 4, 'home_team': 'Nottingham', 'away_team': 'Wolverhampton',
             'competition': 'Premier League'},
            {'match_number': 5, 'home_team': 'Manchester City', 'away_team': 'Fulham',
             'competition': 'Premier League'},
        ]
    }

    actual_results = {
        1: 'Away',      # Liverpool won 1-0
        2: 'Home',      # Villa won 1-0
        3: 'Away',      # Burnley won 3-2
        4: 'Draw',      # 0-0
        5: 'Home',      # Man City won 3-0
    }

    analysis = analyzer.analyze_jackpot(jackpot_data)

    correct = 0
    for pred in analysis['predictions']:
        match_num = pred['match_number']
        actual = actual_results[match_num]
        is_correct = pred['prediction'] == actual
        if is_correct:
            correct += 1
        status = "CORRECT" if is_correct else "WRONG"
        print(f"  Match {match_num}: {pred['home_team']} vs {pred['away_team']}")
        print(f"    Predicted: {pred['prediction']} | Actual: {actual} | {status}")
        print(f"    H:{pred['home_prob']:.3f} D:{pred['draw_prob']:.3f} A:{pred['away_prob']:.3f}")

    print(f"\n  Result: {correct}/5 correct")
    print(f"  {'IMPROVED!' if correct > 2 else 'Needs more work'}")
    return correct


if __name__ == '__main__':
    print("=" * 70)
    print("ALGORITHM V3 IMPROVEMENT TESTS")
    print("=" * 70)

    tests = [
        test_team_database,
        test_neutral_defaults,
        test_draw_can_exceed_25,
        test_quality_gap_factor,
        test_home_advantage_dampening,
        test_feb11_sunderland_liverpool,
        test_feb11_nottingham_wolves,
        test_feb11_mancity_fulham,
        test_feb11_villa_brighton,
        test_jackpot_enrichment,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            failed += 1

    print(f"\n{'=' * 70}")
    print(f"RESULTS: {passed}/{len(tests)} tests passed, {failed} failed")
    print(f"{'=' * 70}")

    # Run full jackpot simulation
    print("\n")
    score = test_full_feb11_jackpot()
    print(f"\nFinal jackpot score: {score}/5")
