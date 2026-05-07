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
import logging

from .jackpot_source import SampleDataSource

logger = logging.getLogger(__name__)


class JackpotFetcher:
    """Fetches jackpot matches from Kenyan betting sites"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.history_dir = Path('./data/jackpots')
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def fetch_sportpesa_mega_jackpot(self) -> Optional[Dict]:
        """Fetch SportPesa Mega Jackpot (17 matches)"""
        print("Fetching SportPesa Mega Jackpot...")
        url = "https://www.ke.sportpesa.com/en/mega-jackpot-pro"
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            prize_amount = self._extract_prize_amount(soup)
            matches = self._scrape_sportpesa_matches(soup)
            if matches:
                payload = {
                    'source_type': 'live',
                    'provider': 'SportPesa',
                    'type': 'Mega Jackpot',
                    'matches_count': len(matches),
                    'fetched_at': datetime.now().isoformat(),
                    'url': url,
                    'prize_amount': prize_amount,
                    'matches': matches,
                }
            else:
                logger.warning("SportPesa Mega Jackpot uses JavaScript rendering; falling back to sample data")
                payload = SampleDataSource("sportpesa", "mega").fetch()
                payload['prize_amount'] = prize_amount
            self._save_jackpot_history(payload)
            print(f"✅ Fetched {len(payload['matches'])} matches (source: {payload['source_type']})")
            print(f"💰 Prize: {payload.get('prize_amount', 'Unknown')}")
            return payload
        except Exception as e:
            print(f"❌ Error fetching SportPesa Mega Jackpot: {e}")
            import traceback
            traceback.print_exc()
            return None

    def fetch_sportpesa_midweek_jackpot(self) -> Optional[Dict]:
        """Fetch SportPesa Midweek Jackpot (13 matches)"""
        print("Fetching SportPesa Midweek Jackpot...")
        url = "https://www.ke.sportpesa.com/en/jackpot"
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            prize_amount = self._extract_prize_amount(soup)
            matches = self._scrape_sportpesa_matches(soup)
            if matches:
                payload = {
                    'source_type': 'live',
                    'provider': 'SportPesa',
                    'type': 'Midweek Jackpot',
                    'matches_count': len(matches),
                    'fetched_at': datetime.now().isoformat(),
                    'url': url,
                    'prize_amount': prize_amount,
                    'matches': matches,
                }
            else:
                logger.warning("SportPesa Midweek Jackpot uses JavaScript rendering; falling back to sample data")
                payload = SampleDataSource("sportpesa", "midweek").fetch()
                payload['prize_amount'] = prize_amount
            self._save_jackpot_history(payload)
            print(f"✅ Fetched {len(payload['matches'])} matches (source: {payload['source_type']})")
            print(f"💰 Prize: {payload.get('prize_amount', 'Unknown')}")
            return payload
        except Exception as e:
            print(f"❌ Error fetching SportPesa Midweek Jackpot: {e}")
            import traceback
            traceback.print_exc()
            return None

    def fetch_betika_jackpot(self) -> Optional[Dict]:
        """Fetch Betika Jackpot"""
        print("Fetching Betika Jackpot...")
        url = "https://www.betika.com/en-ke/jackpot"
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            prize_amount = self._extract_prize_amount(soup)
            matches = self._scrape_betika_matches(soup)
            if matches:
                payload = {
                    'source_type': 'live',
                    'provider': 'Betika',
                    'type': 'Jackpot',
                    'matches_count': len(matches),
                    'fetched_at': datetime.now().isoformat(),
                    'url': url,
                    'prize_amount': prize_amount,
                    'matches': matches,
                }
            else:
                logger.warning("Betika Jackpot uses JavaScript rendering; falling back to sample data")
                payload = SampleDataSource("betika", "jackpot").fetch()
                payload['prize_amount'] = prize_amount
            self._save_jackpot_history(payload)
            print(f"✅ Fetched {len(payload['matches'])} matches (source: {payload['source_type']})")
            print(f"💰 Prize: {payload.get('prize_amount', 'Unknown')}")
            return payload
        except Exception as e:
            print(f"❌ Error fetching Betika Jackpot: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _scrape_sportpesa_matches(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract match details from SportPesa page. Returns [] when JS-rendered."""
        matches = []
        print("\n[DEBUG] Starting SportPesa match extraction...")

        iframe = soup.find('iframe', src=re.compile(r'jackpot', re.I))
        if iframe:
            print(f"[INFO] Found jackpot iframe — JavaScript rendering detected; cannot scrape statically")
            return []

        match_elements = (
            soup.find_all('div', class_=re.compile(r'match|game|event', re.I)) or
            soup.find_all('tr', class_=re.compile(r'match|game|event', re.I)) or
            soup.find_all('li', class_=re.compile(r'match|game|event', re.I))
        )

        print(f"[DEBUG] Found {len(match_elements)} potential match elements")
        if not match_elements:
            print("[DEBUG] No match elements found; JavaScript rendering likely")
            return []

        for idx, element in enumerate(match_elements[:20]):
            try:
                teams = element.find_all(class_=re.compile(r'team|opponent', re.I))
                if len(teams) >= 2:
                    home_team = teams[0].get_text(strip=True)
                    away_team = teams[1].get_text(strip=True)
                    if not home_team or not away_team or len(home_team) < 3 or len(away_team) < 3:
                        continue
                    date_elem = element.find(class_=re.compile(r'date|time|kick', re.I))
                    comp_elem = element.find(class_=re.compile(r'league|competition|tournament', re.I))
                    print(f"[DEBUG] Extracted match {idx + 1}: {home_team} vs {away_team}")
                    matches.append({
                        'match_number': len(matches) + 1,
                        'home_team': home_team,
                        'away_team': away_team,
                        'kickoff': date_elem.get_text(strip=True) if date_elem else None,
                        'competition': comp_elem.get_text(strip=True) if comp_elem else None,
                    })
            except Exception as e:
                print(f"[DEBUG] Error extracting match {idx + 1}: {e}")

        print(f"[DEBUG] Extracted {len(matches)} matches")
        return matches

    def _scrape_betika_matches(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract match details from Betika page. Returns [] when JS-rendered."""
        matches = []
        print("\n[DEBUG] Starting Betika match extraction...")

        match_elements = (
            soup.find_all('div', class_=re.compile(r'match|game|event', re.I)) or
            soup.find_all('tr', class_=re.compile(r'match|game|event', re.I))
        )

        print(f"[DEBUG] Found {len(match_elements)} potential match elements")
        if not match_elements:
            print("[DEBUG] No match elements found; JavaScript rendering likely")
            return []

        for idx, element in enumerate(match_elements[:20]):
            try:
                teams = element.find_all(class_=re.compile(r'team|opponent', re.I))
                if len(teams) >= 2:
                    home_team = teams[0].get_text(strip=True)
                    away_team = teams[1].get_text(strip=True)
                    if not home_team or not away_team or len(home_team) < 3 or len(away_team) < 3:
                        continue
                    date_elem = element.find(class_=re.compile(r'date|time|kick', re.I))
                    comp_elem = element.find(class_=re.compile(r'league|competition', re.I))
                    print(f"[DEBUG] Extracted match {idx + 1}: {home_team} vs {away_team}")
                    matches.append({
                        'match_number': len(matches) + 1,
                        'home_team': home_team,
                        'away_team': away_team,
                        'kickoff': date_elem.get_text(strip=True) if date_elem else None,
                        'competition': comp_elem.get_text(strip=True) if comp_elem else None,
                    })
            except Exception as e:
                print(f"[DEBUG] Error extracting match {idx + 1}: {e}")

        print(f"[DEBUG] Extracted {len(matches)} matches")
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
                'source_type': jackpot_data.get('source_type', 'unknown'),
                'matches_count': jackpot_data['matches_count'],
                'prize_amount': jackpot_data.get('prize_amount', ''),
                'url': jackpot_data.get('url', ''),
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
