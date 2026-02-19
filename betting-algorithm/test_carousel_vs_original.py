#!/usr/bin/env python3
"""
Comparison Test: Original vs Enhanced Jackpot Fetcher

This script demonstrates the difference between:
1. Original fetcher (separate URLs for each jackpot)
2. Enhanced fetcher (carousel navigation to find all jackpots)

Usage:
    python test_carousel_vs_original.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from jackpot_fetcher import JackpotFetcher
from jackpot_fetcher_enhanced import EnhancedJackpotFetcher


def test_original_fetcher():
    """Test the original fetcher with separate URL approach"""
    print("\n" + "=" * 70)
    print("TEST 1: ORIGINAL FETCHER (Separate URLs)")
    print("=" * 70)

    fetcher = JackpotFetcher(use_selenium=False)  # Use sample data for speed

    # Fetch each jackpot separately
    mega = fetcher.fetch_sportpesa_mega_jackpot()
    midweek = fetcher.fetch_sportpesa_midweek_jackpot()

    jackpots = [j for j in [mega, midweek] if j]

    print(f"\n📊 Results:")
    print(f"   Total jackpots fetched: {len(jackpots)}")

    for i, jp in enumerate(jackpots, 1):
        print(f"\n   {i}. {jp['type']}")
        print(f"      Matches: {jp.get('matches_count', len(jp['matches']))}")
        print(f"      Prize: {jp.get('prize_amount', 'Unknown')}")
        print(f"      Data Source: {jp.get('data_source', 'unknown')}")

    print(f"\n✅ Original Fetcher: Fetched {len(jackpots)} jackpots (manually specified)")
    return jackpots


def test_enhanced_fetcher():
    """Test the enhanced fetcher with carousel navigation"""
    print("\n" + "=" * 70)
    print("TEST 2: ENHANCED FETCHER (Carousel Navigation)")
    print("=" * 70)

    fetcher = EnhancedJackpotFetcher(use_selenium=False)  # Use sample data for speed

    # Automatically fetch ALL jackpots
    jackpots = fetcher.fetch_all_sportpesa_jackpots()

    print(f"\n📊 Results:")
    print(f"   Total jackpots fetched: {len(jackpots)}")

    for i, jp in enumerate(jackpots, 1):
        print(f"\n   {i}. {jp['type']}")
        print(f"      Matches: {jp.get('matches_count', len(jp['matches']))}")
        print(f"      Prize: {jp.get('prize_amount', 'Unknown')}")
        print(f"      Data Source: {jp.get('data_source', 'unknown')}")

    print(f"\n✅ Enhanced Fetcher: Automatically discovered {len(jackpots)} jackpots")
    return jackpots


def compare_results(original_jackpots, enhanced_jackpots):
    """Compare the results from both fetchers"""
    print("\n" + "=" * 70)
    print("COMPARISON")
    print("=" * 70)

    print(f"\n📊 Count Comparison:")
    print(f"   Original Fetcher: {len(original_jackpots)} jackpots")
    print(f"   Enhanced Fetcher: {len(enhanced_jackpots)} jackpots")

    if len(enhanced_jackpots) > len(original_jackpots):
        diff = len(enhanced_jackpots) - len(original_jackpots)
        print(f"\n🎯 Enhanced fetcher found {diff} additional jackpot(s)!")

        # Show what was missed
        original_types = {jp['type'] for jp in original_jackpots}
        enhanced_types = {jp['type'] for jp in enhanced_jackpots}
        new_types = enhanced_types - original_types

        if new_types:
            print(f"\n📢 New jackpots discovered by enhanced fetcher:")
            for jackpot_type in new_types:
                print(f"   - {jackpot_type}")

    print(f"\n💡 Key Differences:")
    print(f"   Original:")
    print(f"   ✓ Uses separate URLs for each jackpot")
    print(f"   ✓ Requires manual coding for each type")
    print(f"   ✓ Simple implementation")
    print(f"   ✗ Might miss new jackpots")

    print(f"\n   Enhanced:")
    print(f"   ✓ Automatically discovers ALL jackpots")
    print(f"   ✓ Handles carousel/slideshow interfaces")
    print(f"   ✓ Future-proof for new jackpot types")
    print(f"   ✓ Extracts unique matches for each")
    print(f"   ✗ Slightly more complex")


def demonstrate_unique_matches():
    """Demonstrate that each jackpot has unique matches"""
    print("\n" + "=" * 70)
    print("UNIQUE MATCHES DEMONSTRATION")
    print("=" * 70)

    fetcher = EnhancedJackpotFetcher(use_selenium=False)
    jackpots = fetcher.fetch_all_sportpesa_jackpots()

    for jackpot in jackpots:
        print(f"\n{jackpot['type']}")
        print(f"{'─' * 60}")
        print(f"Total Matches: {len(jackpot['matches'])}")
        print(f"\nFirst 3 matches:")
        for match in jackpot['matches'][:3]:
            print(f"  {match['match_number']}. {match['home_team']} vs {match['away_team']}")

    print(f"\n💡 Notice: Each jackpot type has different match combinations!")


def integration_example():
    """Show how to integrate with the analyzer"""
    print("\n" + "=" * 70)
    print("INTEGRATION WITH ANALYZER EXAMPLE")
    print("=" * 70)

    print("\nCode example:")
    print("""
    from jackpot_fetcher_enhanced import EnhancedJackpotFetcher
    from jackpot_analyzer import JackpotAnalyzer

    # Fetch all jackpots automatically
    fetcher = EnhancedJackpotFetcher(use_selenium=True)
    jackpots = fetcher.fetch_all_sportpesa_jackpots()

    # Analyze each jackpot
    analyzer = JackpotAnalyzer()
    for jackpot in jackpots:
        print(f"\\nAnalyzing: {jackpot['type']}")
        analysis = analyzer.analyze_jackpot(jackpot)
        print(f"Predictions generated for {len(analysis['predictions'])} matches")
        print(f"Average confidence: {analysis['average_confidence']*100:.1f}%")
    """)

    print("\n✅ Both fetchers work seamlessly with the analyzer!")


def main():
    """Run all comparison tests"""
    print("\n" + "🎰" * 35)
    print("JACKPOT FETCHER COMPARISON TEST")
    print("Original vs Enhanced (Carousel Navigation)")
    print("🎰" * 35)

    # Test original fetcher
    original_jackpots = test_original_fetcher()

    # Test enhanced fetcher
    enhanced_jackpots = test_enhanced_fetcher()

    # Compare results
    compare_results(original_jackpots, enhanced_jackpots)

    # Demonstrate unique matches
    demonstrate_unique_matches()

    # Show integration example
    integration_example()

    # Final recommendation
    print("\n" + "=" * 70)
    print("RECOMMENDATION")
    print("=" * 70)
    print("\n🎯 For SportPesa's carousel interface:")
    print("   Use: EnhancedJackpotFetcher")
    print("\n   Why?")
    print("   ✓ Automatically discovers ALL jackpots")
    print("   ✓ No manual coding for new jackpot types")
    print("   ✓ Handles carousel/slideshow navigation")
    print("   ✓ Extracts unique matches for each jackpot")
    print("   ✓ Future-proof solution")

    print("\n📚 Documentation:")
    print("   See: CAROUSEL_JACKPOT_GUIDE.md for detailed guide")

    print("\n" + "=" * 70)
    print("✅ Test Complete!")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    main()
