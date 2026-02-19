#!/usr/bin/env python3
"""
Quick test script to check SportPesa jackpot fetching

Usage: python3 test_jackpot_fetch.py [--headless]
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

print("="*70)
print("SPORTPESA JACKPOT FETCH TEST")
print("="*70)

# Test 1: Check if enhanced fetcher is available
print("\n1️⃣ Checking Enhanced Fetcher availability...")
try:
    from src.jackpot_fetcher_enhanced import EnhancedJackpotFetcher
    print("✅ Enhanced fetcher is available")
    enhanced_available = True
except ImportError as e:
    print(f"❌ Enhanced fetcher not available: {e}")
    enhanced_available = False

# Test 2: Check Selenium
print("\n2️⃣ Checking Selenium...")
try:
    from selenium import webdriver
    print("✅ Selenium is installed")
    selenium_available = True
except ImportError:
    print("❌ Selenium not installed")
    print("   Run: pip install selenium webdriver-manager")
    selenium_available = False

if not enhanced_available or not selenium_available:
    print("\n❌ Cannot proceed - missing dependencies")
    sys.exit(1)

# Test 3: Run the enhanced fetcher
print("\n3️⃣ Testing Enhanced Fetcher...")
print("   This will take 20-30 seconds...\n")

# Check for --headless flag
headless = '--headless' in sys.argv or '-h' in sys.argv

try:
    fetcher = EnhancedJackpotFetcher(use_selenium=True, headless=headless)
    print(f"   Mode: {'Headless' if headless else 'Visible Browser'}")

    jackpots = fetcher.fetch_all_sportpesa_jackpots()

    print(f"\n✅ Fetched {len(jackpots)} jackpot(s)")

    # Display results
    for i, jp in enumerate(jackpots, 1):
        print(f"\n{'='*60}")
        print(f"Jackpot {i}: {jp['provider']} - {jp['type']}")
        print(f"{'='*60}")
        print(f"Prize Amount: {jp.get('prize_amount', 'Unknown')}")
        print(f"Match Count: {jp.get('matches_count', 'Unknown')}")
        print(f"Actual Matches: {len(jp.get('matches', []))}")
        print(f"Data Source: {jp.get('data_source', 'unknown')}")
        print(f"Is Sample Data: {jp.get('is_sample_data', jp.get('data_source') == 'sample')}")
        print(f"URL: {jp.get('url', 'N/A')}")

        # Show first 3 matches
        matches = jp.get('matches', [])
        if matches:
            print(f"\nFirst 3 matches:")
            for match in matches[:3]:
                home = match.get('home_team', 'Unknown')
                away = match.get('away_team', 'Unknown')
                comp = match.get('competition', 'Unknown')
                print(f"  {match.get('match_number', '?')}. {home} vs {away} ({comp})")
        else:
            print("\n⚠️  No matches found!")

    # Save results for inspection
    output_dir = Path('./debug')
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / 'test_jackpot_results.json'

    with open(output_file, 'w') as f:
        json.dump(jackpots, f, indent=2)

    print(f"\n💾 Results saved to: {output_file}")

    # Analysis
    print("\n" + "="*70)
    print("ANALYSIS")
    print("="*70)

    live_data_count = sum(1 for jp in jackpots if jp.get('data_source') == 'selenium')
    sample_data_count = sum(1 for jp in jackpots if jp.get('data_source') in ['sample', 'sample_fallback'])

    print(f"\n📊 Summary:")
    print(f"   Total Jackpots: {len(jackpots)}")
    print(f"   Live Data: {live_data_count}")
    print(f"   Sample Data: {sample_data_count}")

    if sample_data_count == len(jackpots):
        print("\n⚠️  WARNING: All jackpots are using sample data!")
        print("   This means Selenium couldn't scrape the actual website.")
        print("\n🔧 Troubleshooting:")
        print("   1. Run: ./fix_selenium.sh")
        print("   2. Check if Chromium is installed: chromium-browser --version")
        print("   3. Run diagnostic: python3 diagnose_sportpesa.py")
        print("   4. Try non-headless mode: python3 test_jackpot_fetch.py (without --headless)")

    elif live_data_count > 0:
        print("\n✅ SUCCESS: Getting live data from SportPesa!")

        # Check if matches are populated
        empty_matches = [jp for jp in jackpots if not jp.get('matches')]
        if empty_matches:
            print(f"\n⚠️  WARNING: {len(empty_matches)} jackpot(s) have no matches")
            print("   The page structure may have changed.")
            print("   Run: python3 diagnose_sportpesa.py")

    else:
        print("\n⚠️  MIXED: Some live, some sample data")
        print("   Check the results above to see which failed")

except Exception as e:
    print(f"\n❌ Error during fetch: {e}")
    import traceback
    traceback.print_exc()
    print("\n🔧 Try running: python3 diagnose_sportpesa.py")

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
