"""
Test script for Jackpot System

Tests the complete workflow:
1. Fetch jackpots from websites
2. Generate AI predictions
3. Save predictions
4. Simulate results recording
5. View performance stats

Run: python test_jackpot_system.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.jackpot_fetcher import JackpotFetcher
from src.jackpot_analyzer import JackpotAnalyzer


def test_jackpot_workflow():
    """Test complete jackpot workflow"""

    print("\n" + "=" * 70)
    print("JACKPOT SYSTEM TEST")
    print("=" * 70 + "\n")

    # Step 1: Fetch jackpots
    print("📡 STEP 1: Fetching jackpots from betting sites...")
    print("-" * 70)

    fetcher = JackpotFetcher()

    # Test SportPesa Mega
    print("\n1️⃣  Fetching SportPesa Mega Jackpot...")
    mega = fetcher.fetch_sportpesa_mega_jackpot()

    if mega and len(mega.get('matches', [])) > 0:
        print(f"   ✅ Success! Found {len(mega['matches'])} matches")
        print(f"   💰 Prize: {mega.get('prize_amount', 'Unknown')}")
    else:
        print("   ⚠️  No matches found (website may have changed or jackpot not available)")
        print("   ℹ️  Creating sample data for testing...")

        # Create sample data for testing
        mega = {
            'provider': 'SportPesa',
            'type': 'Mega Jackpot (Sample)',
            'matches_count': 17,
            'prize_amount': 'KSh 100,000,000',
            'fetched_at': '2026-02-11T10:00:00',
            'url': 'https://www.ke.sportpesa.com/en/mega-jackpot-pro',
            'matches': [
                {'match_number': 1, 'home_team': 'Arsenal', 'away_team': 'Chelsea', 'competition': 'Premier League'},
                {'match_number': 2, 'home_team': 'Man City', 'away_team': 'Liverpool', 'competition': 'Premier League'},
                {'match_number': 3, 'home_team': 'Tottenham', 'away_team': 'Man United', 'competition': 'Premier League'},
                {'match_number': 4, 'home_team': 'Newcastle', 'away_team': 'Aston Villa', 'competition': 'Premier League'},
                {'match_number': 5, 'home_team': 'Brighton', 'away_team': 'Wolves', 'competition': 'Premier League'},
                {'match_number': 6, 'home_team': 'Real Madrid', 'away_team': 'Barcelona', 'competition': 'La Liga'},
                {'match_number': 7, 'home_team': 'Bayern Munich', 'away_team': 'Dortmund', 'competition': 'Bundesliga'},
                {'match_number': 8, 'home_team': 'Inter Milan', 'away_team': 'AC Milan', 'competition': 'Serie A'},
                {'match_number': 9, 'home_team': 'PSG', 'away_team': 'Marseille', 'competition': 'Ligue 1'},
                {'match_number': 10, 'home_team': 'Ajax', 'away_team': 'PSV', 'competition': 'Eredivisie'},
                {'match_number': 11, 'home_team': 'Porto', 'away_team': 'Benfica', 'competition': 'Liga Portugal'},
                {'match_number': 12, 'home_team': 'Celtic', 'away_team': 'Rangers', 'competition': 'Scottish Premiership'},
                {'match_number': 13, 'home_team': 'Galatasaray', 'away_team': 'Fenerbahce', 'competition': 'Super Lig'},
                {'match_number': 14, 'home_team': 'Boca Juniors', 'away_team': 'River Plate', 'competition': 'Argentine Primera'},
                {'match_number': 15, 'home_team': 'Flamengo', 'away_team': 'Palmeiras', 'competition': 'Brasileirao'},
                {'match_number': 16, 'home_team': 'LA Galaxy', 'away_team': 'LAFC', 'competition': 'MLS'},
                {'match_number': 17, 'home_team': 'Al Hilal', 'away_team': 'Al Nassr', 'competition': 'Saudi Pro League'},
            ]
        }

    # Step 2: Analyze jackpot and generate predictions
    print("\n🤖 STEP 2: Generating AI predictions...")
    print("-" * 70)

    analyzer = JackpotAnalyzer()
    analysis = analyzer.analyze_jackpot(mega)

    print(f"\n✅ Analysis complete!")
    print(f"   📊 Jackpot ID: {analysis['jackpot_id']}")
    print(f"   📈 Average Confidence: {analysis['average_confidence']*100:.1f}%")
    print(f"   🎯 High Confidence Picks (>75%): {analysis['high_confidence_count']}")
    print(f"   ⚠️  Low Confidence Picks (<55%): {analysis['low_confidence_count']}")

    # Step 3: Show recommended combinations
    print("\n💡 STEP 3: Recommended betting strategies...")
    print("-" * 70)

    for i, combo in enumerate(analysis['recommended_combinations'][:3], 1):
        print(f"\n   Strategy {i}: {combo['strategy']}")
        print(f"   Description: {combo['description']}")
        if 'predicted_accuracy' in combo:
            print(f"   Expected Accuracy: {combo['predicted_accuracy']*100:.1f}%")

    # Step 4: Simulate recording results
    print("\n📝 STEP 4: Simulating result recording...")
    print("-" * 70)

    # Simulate some results (in real use, this would be actual match results)
    sample_results = []
    for pred in analysis['predictions'][:5]:  # Just first 5 for demo
        # Simulate result based on prediction (80% accurate)
        import random
        if random.random() < 0.8:
            result = pred['prediction']  # Correct prediction
        else:
            # Wrong prediction
            options = ['Home', 'Draw', 'Away']
            options.remove(pred['prediction'])
            result = random.choice(options)

        sample_results.append({
            'match_number': pred['match_number'],
            'actual_result': result
        })

    # Record results
    result_data = analyzer.record_jackpot_results(
        analysis['jackpot_id'],
        sample_results
    )

    # Step 5: View performance stats
    print("\n📊 STEP 5: Performance statistics...")
    print("-" * 70)

    stats_df = analyzer.get_performance_stats()

    # Summary
    print("\n" + "=" * 70)
    print("TEST COMPLETE ✅")
    print("=" * 70)
    print("\nGenerated files:")
    print(f"  📄 Predictions: data/jackpot_predictions/{analysis['jackpot_id']}.json")
    print(f"  📄 CSV: data/jackpot_predictions/{analysis['jackpot_id']}.csv")
    if result_data:
        print(f"  📄 Results: data/jackpot_results/{analysis['jackpot_id']}_results.json")

    print("\n📖 Next steps:")
    print("  1. Check the generated JSON and CSV files")
    print("  2. Review the predictions and strategies")
    print("  3. When actual matches complete, record real results")
    print("  4. Track performance over time")

    print("\n💡 Tips:")
    print("  - Use multiple betting strategies (not just main prediction)")
    print("  - Focus on high-confidence picks for better accuracy")
    print("  - Track all results to improve the algorithm")

    print("\n📚 Read JACKPOT_GUIDE.md for detailed usage instructions")
    print()


if __name__ == '__main__':
    try:
        test_jackpot_workflow()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
