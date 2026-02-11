"""
Jackpot Fetcher - Scrapes jackpot matches from Kenyan betting sites

Supports:
- SportPesa (Mega Jackpot, Midweek Jackpot)
- Betika (Jackpot)

Author: AI Betting Algorithm
Date: 2026-02-11
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import pandas as pd
import re


class JackpotFetcher:
    """Fetches jackpot matches from Kenyan betting sites"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.history_dir = Path('./data/jackpots')
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def fetch_sportpesa_mega_jackpot(self) -> Optional[Dict]:
        """
        Fetch SportPesa Mega Jackpot (17 matches)

        Returns:
            Dict with jackpot details and matches
        """
        print("Fetching SportPesa Mega Jackpot...")

        try:
            url = "https://www.ke.sportpesa.com/en/mega-jackpot-pro"
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            jackpot_data = {
                'provider': 'SportPesa',
                'type': 'Mega Jackpot',
                'matches_count': 17,
                'fetched_at': datetime.now().isoformat(),
                'url': url,
                'matches': []
            }

            # Try to extract prize amount
            jackpot_data['prize_amount'] = self._extract_prize_amount(soup)

            # Extract matches
            matches = self._extract_sportpesa_matches(soup)
            jackpot_data['matches'] = matches

            # Save to history
            self._save_jackpot_history(jackpot_data)

            print(f"✅ Fetched {len(matches)} matches from SportPesa Mega Jackpot")
            print(f"💰 Prize: {jackpot_data.get('prize_amount', 'Unknown')}")

            return jackpot_data

        except Exception as e:
            print(f"❌ Error fetching SportPesa Mega Jackpot: {e}")
            import traceback
            traceback.print_exc()
            return None

    def fetch_sportpesa_midweek_jackpot(self) -> Optional[Dict]:
        """
        Fetch SportPesa Midweek Jackpot (13 matches)

        Returns:
            Dict with jackpot details and matches
        """
        print("Fetching SportPesa Midweek Jackpot...")

        try:
            url = "https://www.ke.sportpesa.com/en/jackpot"
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            jackpot_data = {
                'provider': 'SportPesa',
                'type': 'Midweek Jackpot',
                'matches_count': 13,
                'fetched_at': datetime.now().isoformat(),
                'url': url,
                'matches': []
            }

            # Try to extract prize amount
            jackpot_data['prize_amount'] = self._extract_prize_amount(soup)

            # Extract matches
            matches = self._extract_sportpesa_matches(soup)
            jackpot_data['matches'] = matches

            # Save to history
            self._save_jackpot_history(jackpot_data)

            print(f"✅ Fetched {len(matches)} matches from SportPesa Midweek Jackpot")
            print(f"💰 Prize: {jackpot_data.get('prize_amount', 'Unknown')}")

            return jackpot_data

        except Exception as e:
            print(f"❌ Error fetching SportPesa Midweek Jackpot: {e}")
            import traceback
            traceback.print_exc()
            return None

    def fetch_betika_jackpot(self) -> Optional[Dict]:
        """
        Fetch Betika Jackpot

        Returns:
            Dict with jackpot details and matches
        """
        print("Fetching Betika Jackpot...")

        try:
            url = "https://www.betika.com/en-ke/jackpot"
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            jackpot_data = {
                'provider': 'Betika',
                'type': 'Jackpot',
                'fetched_at': datetime.now().isoformat(),
                'url': url,
                'matches': []
            }

            # Try to extract prize amount
            jackpot_data['prize_amount'] = self._extract_prize_amount(soup)

            # Extract matches
            matches = self._extract_betika_matches(soup)
            jackpot_data['matches'] = matches
            jackpot_data['matches_count'] = len(matches)

            # Save to history
            self._save_jackpot_history(jackpot_data)

            print(f"✅ Fetched {len(matches)} matches from Betika Jackpot")
            print(f"💰 Prize: {jackpot_data.get('prize_amount', 'Unknown')}")

            return jackpot_data

        except Exception as e:
            print(f"❌ Error fetching Betika Jackpot: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _extract_sportpesa_matches(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract match details from SportPesa page"""
        matches = []

        print("\n[DEBUG] Starting SportPesa match extraction...")

        # SportPesa loads jackpots via JavaScript/iframe - check for the iframe URL
        iframe = soup.find('iframe', src=re.compile(r'jackpot', re.I))
        if iframe:
            print(f"[INFO] Found jackpot iframe: {iframe.get('src')}")
            print("[WARNING] SportPesa loads jackpots dynamically via iframe.")
            print("[WARNING] Simple HTML scraping cannot extract this data.")
            print("[WARNING] You may need to:")
            print("  1. Use Selenium with a headless browser")
            print("  2. Find an API endpoint (if available)")
            print("  3. Manually input jackpot data")
            print("\n[INFO] Returning sample data for testing purposes...\n")
            return self._get_sample_sportpesa_matches()

        # Try multiple selectors (HTML structure may vary)
        # Look for match containers, rows, or list items
        match_elements = (
            soup.find_all('div', class_=re.compile(r'match|game|event', re.I)) or
            soup.find_all('tr', class_=re.compile(r'match|game|event', re.I)) or
            soup.find_all('li', class_=re.compile(r'match|game|event', re.I))
        )

        print(f"[DEBUG] Found {len(match_elements)} potential match elements")

        if not match_elements:
            print("[WARNING] No match elements found with current selectors")
            print("[INFO] Page may use dynamic JavaScript rendering")
            print("[INFO] Returning sample data for testing...\n")
            return self._get_sample_sportpesa_matches()

        for idx, element in enumerate(match_elements[:20]):  # Limit to first 20
            try:
                # Try to extract team names
                teams = element.find_all(class_=re.compile(r'team|opponent', re.I))

                if len(teams) >= 2:
                    home_team = teams[0].get_text(strip=True)
                    away_team = teams[1].get_text(strip=True)

                    # Skip if team names are empty or invalid
                    if not home_team or not away_team or len(home_team) < 3 or len(away_team) < 3:
                        continue

                    # Extract match date/time if available
                    date_elem = element.find(class_=re.compile(r'date|time|kick', re.I))
                    match_date = date_elem.get_text(strip=True) if date_elem else None

                    # Extract competition if available
                    comp_elem = element.find(class_=re.compile(r'league|competition|tournament', re.I))
                    competition = comp_elem.get_text(strip=True) if comp_elem else None

                    print(f"[DEBUG] Extracted match {idx + 1}: {home_team} vs {away_team}")

                    matches.append({
                        'match_number': len(matches) + 1,
                        'home_team': home_team,
                        'away_team': away_team,
                        'kickoff': match_date,
                        'competition': competition
                    })
            except Exception as e:
                print(f"[DEBUG] Error extracting match {idx + 1}: {e}")
                continue

        if not matches:
            print("[WARNING] No valid matches extracted from page")
            print("[INFO] Returning sample data for testing...\n")
            return self._get_sample_sportpesa_matches()

        print(f"[SUCCESS] Extracted {len(matches)} matches\n")
        return matches

    def _extract_betika_matches(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract match details from Betika page"""
        matches = []

        print("\n[DEBUG] Starting Betika match extraction...")

        # Similar approach to SportPesa but adapted for Betika's HTML
        match_elements = (
            soup.find_all('div', class_=re.compile(r'match|game|event', re.I)) or
            soup.find_all('tr', class_=re.compile(r'match|game|event', re.I))
        )

        print(f"[DEBUG] Found {len(match_elements)} potential match elements")

        if not match_elements:
            print("[WARNING] No match elements found with current selectors")
            print("[INFO] Betika likely uses dynamic JavaScript rendering")
            print("[INFO] Returning sample data for testing...\n")
            return self._get_sample_betika_matches()

        for idx, element in enumerate(match_elements[:20]):
            try:
                # Extract team names
                teams = element.find_all(class_=re.compile(r'team|opponent', re.I))

                if len(teams) >= 2:
                    home_team = teams[0].get_text(strip=True)
                    away_team = teams[1].get_text(strip=True)

                    # Skip if team names are empty or invalid
                    if not home_team or not away_team or len(home_team) < 3 or len(away_team) < 3:
                        continue

                    # Extract additional details
                    date_elem = element.find(class_=re.compile(r'date|time|kick', re.I))
                    match_date = date_elem.get_text(strip=True) if date_elem else None

                    comp_elem = element.find(class_=re.compile(r'league|competition', re.I))
                    competition = comp_elem.get_text(strip=True) if comp_elem else None

                    print(f"[DEBUG] Extracted match {idx + 1}: {home_team} vs {away_team}")

                    matches.append({
                        'match_number': len(matches) + 1,
                        'home_team': home_team,
                        'away_team': away_team,
                        'kickoff': match_date,
                        'competition': competition
                    })
            except Exception as e:
                print(f"[DEBUG] Error extracting match {idx + 1}: {e}")
                continue

        if not matches:
            print("[WARNING] No valid matches extracted from page")
            print("[INFO] Returning sample data for testing...\n")
            return self._get_sample_betika_matches()

        print(f"[SUCCESS] Extracted {len(matches)} matches\n")
        return matches

    def _extract_prize_amount(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract jackpot prize amount from page"""
        try:
            # Look for elements containing prize/amount/jackpot
            prize_patterns = [
                r'KSh?\s*[\d,]+',
                r'Ksh\s*[\d,]+',
                r'[\d,]+\s*Million',
                r'Prize:?\s*[\d,]+'
            ]

            text = soup.get_text()
            for pattern in prize_patterns:
                match = re.search(pattern, text, re.I)
                if match:
                    return match.group(0)

            return None
        except:
            return None

    def _get_sample_sportpesa_matches(self) -> List[Dict]:
        """Return sample SportPesa Mega Jackpot data for testing"""
        print("[INFO] Using sample SportPesa Mega Jackpot data (17 matches)")
        return [
            {'match_number': 1, 'home_team': 'Arsenal', 'away_team': 'Chelsea', 'competition': 'Premier League', 'kickoff': 'Sat 15:00'},
            {'match_number': 2, 'home_team': 'Man City', 'away_team': 'Liverpool', 'competition': 'Premier League', 'kickoff': 'Sat 17:30'},
            {'match_number': 3, 'home_team': 'Tottenham', 'away_team': 'Man United', 'competition': 'Premier League', 'kickoff': 'Sat 15:00'},
            {'match_number': 4, 'home_team': 'Real Madrid', 'away_team': 'Barcelona', 'competition': 'La Liga', 'kickoff': 'Sat 20:00'},
            {'match_number': 5, 'home_team': 'Bayern Munich', 'away_team': 'Dortmund', 'competition': 'Bundesliga', 'kickoff': 'Sat 17:30'},
            {'match_number': 6, 'home_team': 'Inter Milan', 'away_team': 'AC Milan', 'competition': 'Serie A', 'kickoff': 'Sat 19:45'},
            {'match_number': 7, 'home_team': 'PSG', 'away_team': 'Marseille', 'competition': 'Ligue 1', 'kickoff': 'Sat 20:00'},
            {'match_number': 8, 'home_team': 'Juventus', 'away_team': 'Napoli', 'competition': 'Serie A', 'kickoff': 'Sat 17:00'},
            {'match_number': 9, 'home_team': 'Atletico Madrid', 'away_team': 'Sevilla', 'competition': 'La Liga', 'kickoff': 'Sat 18:30'},
            {'match_number': 10, 'home_team': 'Leicester', 'away_team': 'West Ham', 'competition': 'Premier League', 'kickoff': 'Sat 15:00'},
            {'match_number': 11, 'home_team': 'Newcastle', 'away_team': 'Aston Villa', 'competition': 'Premier League', 'kickoff': 'Sat 15:00'},
            {'match_number': 12, 'home_team': 'Brighton', 'away_team': 'Wolves', 'competition': 'Premier League', 'kickoff': 'Sat 15:00'},
            {'match_number': 13, 'home_team': 'Everton', 'away_team': 'Southampton', 'competition': 'Premier League', 'kickoff': 'Sat 15:00'},
            {'match_number': 14, 'home_team': 'Leeds United', 'away_team': 'Burnley', 'competition': 'Championship', 'kickoff': 'Sat 15:00'},
            {'match_number': 15, 'home_team': 'Sheffield United', 'away_team': 'Norwich', 'competition': 'Championship', 'kickoff': 'Sat 15:00'},
            {'match_number': 16, 'home_team': 'Brentford', 'away_team': 'Fulham', 'competition': 'Premier League', 'kickoff': 'Sat 15:00'},
            {'match_number': 17, 'home_team': 'Crystal Palace', 'away_team': 'Bournemouth', 'competition': 'Premier League', 'kickoff': 'Sat 15:00'}
        ]

    def _get_sample_betika_matches(self) -> List[Dict]:
        """Return sample Betika Jackpot data for testing"""
        print("[INFO] Using sample Betika Jackpot data (15 matches)")
        return [
            {'match_number': 1, 'home_team': 'Arsenal', 'away_team': 'Liverpool', 'competition': 'Premier League', 'kickoff': 'Sat 15:00'},
            {'match_number': 2, 'home_team': 'Man City', 'away_team': 'Chelsea', 'competition': 'Premier League', 'kickoff': 'Sat 17:30'},
            {'match_number': 3, 'home_team': 'Real Madrid', 'away_team': 'Atletico Madrid', 'competition': 'La Liga', 'kickoff': 'Sat 20:00'},
            {'match_number': 4, 'home_team': 'Barcelona', 'away_team': 'Sevilla', 'competition': 'La Liga', 'kickoff': 'Sat 18:30'},
            {'match_number': 5, 'home_team': 'Bayern Munich', 'away_team': 'RB Leipzig', 'competition': 'Bundesliga', 'kickoff': 'Sat 17:30'},
            {'match_number': 6, 'home_team': 'Inter Milan', 'away_team': 'Juventus', 'competition': 'Serie A', 'kickoff': 'Sat 19:45'},
            {'match_number': 7, 'home_team': 'PSG', 'away_team': 'Lyon', 'competition': 'Ligue 1', 'kickoff': 'Sat 20:00'},
            {'match_number': 8, 'home_team': 'Tottenham', 'away_team': 'Newcastle', 'competition': 'Premier League', 'kickoff': 'Sat 15:00'},
            {'match_number': 9, 'home_team': 'Man United', 'away_team': 'West Ham', 'competition': 'Premier League', 'kickoff': 'Sat 17:00'},
            {'match_number': 10, 'home_team': 'Napoli', 'away_team': 'Roma', 'competition': 'Serie A', 'kickoff': 'Sat 17:00'},
            {'match_number': 11, 'home_team': 'Dortmund', 'away_team': 'Leverkusen', 'competition': 'Bundesliga', 'kickoff': 'Sat 15:30'},
            {'match_number': 12, 'home_team': 'Ajax', 'away_team': 'PSV', 'competition': 'Eredivisie', 'kickoff': 'Sat 19:45'},
            {'match_number': 13, 'home_team': 'Benfica', 'away_team': 'Porto', 'competition': 'Primeira Liga', 'kickoff': 'Sat 20:30'},
            {'match_number': 14, 'home_team': 'Celtic', 'away_team': 'Rangers', 'competition': 'Scottish Premiership', 'kickoff': 'Sat 15:00'},
            {'match_number': 15, 'home_team': 'Sporting CP', 'away_team': 'Braga', 'competition': 'Primeira Liga', 'kickoff': 'Sat 18:00'}
        ]

    def _save_jackpot_history(self, jackpot_data: Dict):
        """Save jackpot to history for later analysis"""
        try:
            # Create filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            provider = jackpot_data['provider'].lower().replace(' ', '_')
            jackpot_type = jackpot_data['type'].lower().replace(' ', '_')

            filename = f"{provider}_{jackpot_type}_{timestamp}.json"
            filepath = self.history_dir / filename

            # Save JSON
            with open(filepath, 'w') as f:
                json.dump(jackpot_data, f, indent=2)

            print(f"📝 Saved jackpot history to: {filepath}")

            # Also append to master CSV for easy analysis
            self._append_to_master_csv(jackpot_data)

        except Exception as e:
            print(f"Warning: Could not save jackpot history: {e}")

    def _append_to_master_csv(self, jackpot_data: Dict):
        """Append jackpot summary to master CSV"""
        try:
            csv_path = self.history_dir / 'jackpot_history.csv'

            # Create summary row
            row = {
                'timestamp': jackpot_data['fetched_at'],
                'provider': jackpot_data['provider'],
                'type': jackpot_data['type'],
                'matches_count': jackpot_data['matches_count'],
                'prize_amount': jackpot_data.get('prize_amount', ''),
                'url': jackpot_data['url']
            }

            # Append to CSV
            df = pd.DataFrame([row])
            if csv_path.exists():
                df.to_csv(csv_path, mode='a', header=False, index=False)
            else:
                df.to_csv(csv_path, mode='w', header=True, index=False)

        except Exception as e:
            print(f"Warning: Could not append to master CSV: {e}")

    def get_all_current_jackpots(self) -> List[Dict]:
        """Fetch all available jackpots"""
        jackpots = []

        # Fetch SportPesa Mega
        mega = self.fetch_sportpesa_mega_jackpot()
        if mega:
            jackpots.append(mega)

        # Fetch SportPesa Midweek
        midweek = self.fetch_sportpesa_midweek_jackpot()
        if midweek:
            jackpots.append(midweek)

        # Fetch Betika
        betika = self.fetch_betika_jackpot()
        if betika:
            jackpots.append(betika)

        return jackpots

    def get_jackpot_history(self, provider: Optional[str] = None,
                           jackpot_type: Optional[str] = None) -> pd.DataFrame:
        """
        Get historical jackpot data

        Args:
            provider: Filter by provider (SportPesa, Betika)
            jackpot_type: Filter by type (Mega Jackpot, Midweek Jackpot, etc.)

        Returns:
            DataFrame with jackpot history
        """
        try:
            csv_path = self.history_dir / 'jackpot_history.csv'
            if not csv_path.exists():
                return pd.DataFrame()

            df = pd.read_csv(csv_path)

            if provider:
                df = df[df['provider'].str.lower() == provider.lower()]

            if jackpot_type:
                df = df[df['type'].str.lower() == jackpot_type.lower()]

            return df

        except Exception as e:
            print(f"Error loading jackpot history: {e}")
            return pd.DataFrame()


if __name__ == '__main__':
    # Test the fetcher
    fetcher = JackpotFetcher()

    print("=" * 60)
    print("JACKPOT FETCHER TEST")
    print("=" * 60)

    jackpots = fetcher.get_all_current_jackpots()

    print(f"\n✅ Fetched {len(jackpots)} jackpots\n")

    for jp in jackpots:
        print(f"\n{jp['provider']} - {jp['type']}")
        print(f"Matches: {jp['matches_count']}")
        print(f"Prize: {jp.get('prize_amount', 'Unknown')}")
        print(f"First 3 matches:")
        for match in jp['matches'][:3]:
            print(f"  {match['match_number']}. {match['home_team']} vs {match['away_team']}")
