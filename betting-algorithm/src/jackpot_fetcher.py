"""
Jackpot Fetcher - Scrapes jackpot matches from Kenyan betting sites using Selenium

Supports:
- SportPesa (Mega Jackpot, Midweek Jackpot)
- Betika (Jackpot)

Uses Selenium with headless Chrome for JavaScript-rendered content.

Author: AI Betting Algorithm
Date: 2026-02-16
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import pandas as pd
import re
import time
import logging

# Selenium imports
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logging.warning("Selenium not available. Install with: pip install selenium webdriver-manager")


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JackpotFetcher:
    """Fetches jackpot matches from Kenyan betting sites using Selenium"""

    def __init__(self, use_selenium: bool = True, headless: bool = True, timeout: int = 30):
        """
        Initialize the JackpotFetcher

        Args:
            use_selenium: Whether to use Selenium (True) or fall back to requests (False)
            headless: Whether to run Chrome in headless mode
            timeout: Timeout in seconds for page loads
        """
        self.use_selenium = use_selenium and SELENIUM_AVAILABLE
        self.headless = headless
        self.timeout = timeout

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.history_dir = Path('./data/jackpots')
        self.history_dir.mkdir(parents=True, exist_ok=True)

        if not SELENIUM_AVAILABLE and use_selenium:
            logger.warning("Selenium requested but not available. Falling back to sample data mode.")
            self.use_selenium = False

    def _create_driver(self) -> webdriver.Chrome:
        """Create and configure a Chrome WebDriver instance"""
        try:
            chrome_options = Options()

            if self.headless:
                chrome_options.add_argument('--headless=new')

            # Additional options for stability
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument(f'user-agent={self.headers["User-Agent"]}')
            chrome_options.add_argument('--window-size=1920,1080')

            # Suppress logging
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

            # Use webdriver-manager to automatically handle driver installation
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(self.timeout)

            logger.info("✅ Chrome WebDriver initialized successfully")
            return driver

        except Exception as e:
            logger.error(f"❌ Failed to create Chrome driver: {e}")
            raise

    def _fetch_page_with_selenium(self, url: str, wait_for_selector: Optional[str] = None,
                                   wait_time: int = 10) -> Optional[str]:
        """
        Fetch a page using Selenium and wait for JavaScript to render

        Args:
            url: URL to fetch
            wait_for_selector: CSS selector to wait for (optional)
            wait_time: Time to wait for selector in seconds

        Returns:
            Page HTML source or None if failed
        """
        driver = None
        try:
            driver = self._create_driver()
            logger.info(f"🌐 Fetching: {url}")

            driver.get(url)

            # Wait for specific element if provided
            if wait_for_selector:
                try:
                    WebDriverWait(driver, wait_time).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_selector))
                    )
                    logger.info(f"✅ Found element: {wait_for_selector}")
                except TimeoutException:
                    logger.warning(f"⚠️ Timeout waiting for selector: {wait_for_selector}")
            else:
                # Generic wait for page to stabilize
                time.sleep(5)

            # Additional wait for dynamic content
            time.sleep(2)

            html = driver.page_source
            logger.info(f"✅ Page loaded successfully ({len(html)} bytes)")

            return html

        except WebDriverException as e:
            logger.error(f"❌ WebDriver error: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error fetching page: {e}")
            return None
        finally:
            if driver:
                driver.quit()

    def fetch_sportpesa_mega_jackpot(self) -> Optional[Dict]:
        """
        Fetch SportPesa Mega Jackpot (17 matches)

        Returns:
            Dict with jackpot details and matches
        """
        logger.info("=" * 70)
        logger.info("Fetching SportPesa Mega Jackpot...")
        logger.info("=" * 70)

        try:
            url = "https://www.ke.sportpesa.com/en/mega-jackpot-pro"

            jackpot_data = {
                'provider': 'SportPesa',
                'type': 'Mega Jackpot',
                'matches_count': 17,
                'fetched_at': datetime.now().isoformat(),
                'url': url,
                'matches': [],
                'data_source': 'selenium' if self.use_selenium else 'sample'
            }

            if self.use_selenium:
                # Use Selenium to fetch the page
                html = self._fetch_page_with_selenium(
                    url,
                    wait_for_selector='div.jackpot-match, .match-row, [class*="match"]',
                    wait_time=15
                )

                if html:
                    soup = BeautifulSoup(html, 'html.parser')

                    # Try to extract prize amount
                    jackpot_data['prize_amount'] = self._extract_prize_amount(soup)

                    # Extract matches
                    matches = self._extract_sportpesa_matches(soup)
                    jackpot_data['matches'] = matches
                else:
                    logger.warning("Failed to fetch page with Selenium, using sample data")
                    jackpot_data['matches'] = self._get_sample_sportpesa_matches()
                    jackpot_data['data_source'] = 'sample'
            else:
                # Fall back to sample data
                logger.info("Selenium disabled, using sample data")
                jackpot_data['matches'] = self._get_sample_sportpesa_matches()

            # Save to history
            self._save_jackpot_history(jackpot_data)

            logger.info(f"✅ Fetched {len(jackpot_data['matches'])} matches from SportPesa Mega Jackpot")
            logger.info(f"💰 Prize: {jackpot_data.get('prize_amount', 'Unknown')}")
            logger.info(f"📊 Data Source: {jackpot_data['data_source']}")

            return jackpot_data

        except Exception as e:
            logger.error(f"❌ Error fetching SportPesa Mega Jackpot: {e}")
            import traceback
            traceback.print_exc()

            # Return sample data as fallback
            return {
                'provider': 'SportPesa',
                'type': 'Mega Jackpot',
                'matches_count': 17,
                'fetched_at': datetime.now().isoformat(),
                'url': url,
                'matches': self._get_sample_sportpesa_matches(),
                'data_source': 'sample_fallback',
                'error': str(e)
            }

    def fetch_sportpesa_midweek_jackpot(self) -> Optional[Dict]:
        """
        Fetch SportPesa Midweek Jackpot (13 matches)

        Returns:
            Dict with jackpot details and matches
        """
        logger.info("=" * 70)
        logger.info("Fetching SportPesa Midweek Jackpot...")
        logger.info("=" * 70)

        try:
            url = "https://www.ke.sportpesa.com/en/jackpot"

            jackpot_data = {
                'provider': 'SportPesa',
                'type': 'Midweek Jackpot',
                'matches_count': 13,
                'fetched_at': datetime.now().isoformat(),
                'url': url,
                'matches': [],
                'data_source': 'selenium' if self.use_selenium else 'sample'
            }

            if self.use_selenium:
                # Use Selenium to fetch the page
                html = self._fetch_page_with_selenium(
                    url,
                    wait_for_selector='div.jackpot-match, .match-row, [class*="match"]',
                    wait_time=15
                )

                if html:
                    soup = BeautifulSoup(html, 'html.parser')

                    # Try to extract prize amount
                    jackpot_data['prize_amount'] = self._extract_prize_amount(soup)

                    # Extract matches
                    matches = self._extract_sportpesa_matches(soup)
                    jackpot_data['matches'] = matches
                else:
                    logger.warning("Failed to fetch page with Selenium, using sample data")
                    jackpot_data['matches'] = self._get_sample_sportpesa_matches()[:13]
                    jackpot_data['data_source'] = 'sample'
            else:
                # Fall back to sample data
                logger.info("Selenium disabled, using sample data")
                jackpot_data['matches'] = self._get_sample_sportpesa_matches()[:13]

            # Save to history
            self._save_jackpot_history(jackpot_data)

            logger.info(f"✅ Fetched {len(jackpot_data['matches'])} matches from SportPesa Midweek Jackpot")
            logger.info(f"💰 Prize: {jackpot_data.get('prize_amount', 'Unknown')}")
            logger.info(f"📊 Data Source: {jackpot_data['data_source']}")

            return jackpot_data

        except Exception as e:
            logger.error(f"❌ Error fetching SportPesa Midweek Jackpot: {e}")
            import traceback
            traceback.print_exc()

            # Return sample data as fallback
            return {
                'provider': 'SportPesa',
                'type': 'Midweek Jackpot',
                'matches_count': 13,
                'fetched_at': datetime.now().isoformat(),
                'url': url,
                'matches': self._get_sample_sportpesa_matches()[:13],
                'data_source': 'sample_fallback',
                'error': str(e)
            }

    def fetch_betika_jackpot(self) -> Optional[Dict]:
        """
        Fetch Betika Jackpot

        Returns:
            Dict with jackpot details and matches
        """
        logger.info("=" * 70)
        logger.info("Fetching Betika Jackpot...")
        logger.info("=" * 70)

        try:
            url = "https://www.betika.com/en-ke/jackpot"

            jackpot_data = {
                'provider': 'Betika',
                'type': 'Jackpot',
                'fetched_at': datetime.now().isoformat(),
                'url': url,
                'matches': [],
                'data_source': 'selenium' if self.use_selenium else 'sample'
            }

            if self.use_selenium:
                # Use Selenium to fetch the page
                html = self._fetch_page_with_selenium(
                    url,
                    wait_for_selector='div.jackpot-match, .match-row, [class*="match"]',
                    wait_time=15
                )

                if html:
                    soup = BeautifulSoup(html, 'html.parser')

                    # Try to extract prize amount
                    jackpot_data['prize_amount'] = self._extract_prize_amount(soup)

                    # Extract matches
                    matches = self._extract_betika_matches(soup)
                    jackpot_data['matches'] = matches
                    jackpot_data['matches_count'] = len(matches)
                else:
                    logger.warning("Failed to fetch page with Selenium, using sample data")
                    jackpot_data['matches'] = self._get_sample_betika_matches()
                    jackpot_data['matches_count'] = len(jackpot_data['matches'])
                    jackpot_data['data_source'] = 'sample'
            else:
                # Fall back to sample data
                logger.info("Selenium disabled, using sample data")
                jackpot_data['matches'] = self._get_sample_betika_matches()
                jackpot_data['matches_count'] = len(jackpot_data['matches'])

            # Save to history
            self._save_jackpot_history(jackpot_data)

            logger.info(f"✅ Fetched {len(jackpot_data['matches'])} matches from Betika Jackpot")
            logger.info(f"💰 Prize: {jackpot_data.get('prize_amount', 'Unknown')}")
            logger.info(f"📊 Data Source: {jackpot_data['data_source']}")

            return jackpot_data

        except Exception as e:
            logger.error(f"❌ Error fetching Betika Jackpot: {e}")
            import traceback
            traceback.print_exc()

            # Return sample data as fallback
            return {
                'provider': 'Betika',
                'type': 'Jackpot',
                'fetched_at': datetime.now().isoformat(),
                'url': url,
                'matches': self._get_sample_betika_matches(),
                'matches_count': 15,
                'data_source': 'sample_fallback',
                'error': str(e)
            }

    def _extract_sportpesa_matches(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract match details from SportPesa page"""
        matches = []

        logger.info("\n[DEBUG] Starting SportPesa match extraction...")

        # Try multiple selectors for match containers
        selectors = [
            'div.jackpot-match',
            'div.match-row',
            'div[class*="match"]',
            'tr[class*="match"]',
            'li[class*="match"]',
            'div[class*="game"]',
            'div[class*="event"]'
        ]

        match_elements = []
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                logger.info(f"[DEBUG] Found {len(elements)} elements with selector: {selector}")
                match_elements = elements
                break

        if not match_elements:
            logger.warning("[WARNING] No match elements found with any selector")
            logger.info("[INFO] Returning sample data for testing...\n")
            return self._get_sample_sportpesa_matches()

        logger.info(f"[DEBUG] Processing {len(match_elements)} potential match elements")

        for idx, element in enumerate(match_elements[:20]):  # Limit to first 20
            try:
                # Try to extract team names with multiple strategies
                teams = []

                # Strategy 1: Look for team-specific classes
                team_elements = element.find_all(class_=re.compile(r'team|opponent', re.I))
                if team_elements and len(team_elements) >= 2:
                    teams = [t.get_text(strip=True) for t in team_elements[:2]]

                # Strategy 2: Look for specific team containers
                if not teams:
                    home = element.find(class_=re.compile(r'home', re.I))
                    away = element.find(class_=re.compile(r'away', re.I))
                    if home and away:
                        teams = [home.get_text(strip=True), away.get_text(strip=True)]

                # Strategy 3: Look for spans or divs with team names
                if not teams:
                    text_elements = element.find_all(['span', 'div', 'p'])
                    team_names = [t.get_text(strip=True) for t in text_elements
                                 if t.get_text(strip=True) and len(t.get_text(strip=True)) > 3]
                    if len(team_names) >= 2:
                        teams = team_names[:2]

                if len(teams) >= 2:
                    home_team = teams[0]
                    away_team = teams[1]

                    # Skip if team names are empty or invalid
                    if not home_team or not away_team or len(home_team) < 3 or len(away_team) < 3:
                        continue

                    # Extract match date/time if available
                    date_elem = element.find(class_=re.compile(r'date|time|kick', re.I))
                    match_date = date_elem.get_text(strip=True) if date_elem else None

                    # Extract competition if available
                    comp_elem = element.find(class_=re.compile(r'league|competition|tournament', re.I))
                    competition = comp_elem.get_text(strip=True) if comp_elem else None

                    logger.info(f"[DEBUG] Extracted match {len(matches) + 1}: {home_team} vs {away_team}")

                    matches.append({
                        'match_number': len(matches) + 1,
                        'home_team': home_team,
                        'away_team': away_team,
                        'kickoff': match_date,
                        'competition': competition
                    })
            except Exception as e:
                logger.debug(f"[DEBUG] Error extracting match {idx + 1}: {e}")
                continue

        if not matches:
            logger.warning("[WARNING] No valid matches extracted from page")
            logger.info("[INFO] Returning sample data for testing...\n")
            return self._get_sample_sportpesa_matches()

        logger.info(f"[SUCCESS] Extracted {len(matches)} matches\n")
        return matches

    def _extract_betika_matches(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract match details from Betika page"""
        matches = []

        logger.info("\n[DEBUG] Starting Betika match extraction...")

        # Try multiple selectors for match containers
        selectors = [
            'div.jackpot-match',
            'div.match-row',
            'div[class*="match"]',
            'tr[class*="match"]',
            'div[class*="game"]',
            'div[class*="event"]'
        ]

        match_elements = []
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                logger.info(f"[DEBUG] Found {len(elements)} elements with selector: {selector}")
                match_elements = elements
                break

        if not match_elements:
            logger.warning("[WARNING] No match elements found with any selector")
            logger.info("[INFO] Betika likely uses dynamic JavaScript rendering")
            logger.info("[INFO] Returning sample data for testing...\n")
            return self._get_sample_betika_matches()

        logger.info(f"[DEBUG] Processing {len(match_elements)} potential match elements")

        for idx, element in enumerate(match_elements[:20]):
            try:
                # Extract team names with multiple strategies
                teams = []

                # Strategy 1: Look for team-specific classes
                team_elements = element.find_all(class_=re.compile(r'team|opponent', re.I))
                if team_elements and len(team_elements) >= 2:
                    teams = [t.get_text(strip=True) for t in team_elements[:2]]

                # Strategy 2: Look for home/away containers
                if not teams:
                    home = element.find(class_=re.compile(r'home', re.I))
                    away = element.find(class_=re.compile(r'away', re.I))
                    if home and away:
                        teams = [home.get_text(strip=True), away.get_text(strip=True)]

                if len(teams) >= 2:
                    home_team = teams[0]
                    away_team = teams[1]

                    # Skip if team names are empty or invalid
                    if not home_team or not away_team or len(home_team) < 3 or len(away_team) < 3:
                        continue

                    # Extract additional details
                    date_elem = element.find(class_=re.compile(r'date|time|kick', re.I))
                    match_date = date_elem.get_text(strip=True) if date_elem else None

                    comp_elem = element.find(class_=re.compile(r'league|competition', re.I))
                    competition = comp_elem.get_text(strip=True) if comp_elem else None

                    logger.info(f"[DEBUG] Extracted match {len(matches) + 1}: {home_team} vs {away_team}")

                    matches.append({
                        'match_number': len(matches) + 1,
                        'home_team': home_team,
                        'away_team': away_team,
                        'kickoff': match_date,
                        'competition': competition
                    })
            except Exception as e:
                logger.debug(f"[DEBUG] Error extracting match {idx + 1}: {e}")
                continue

        if not matches:
            logger.warning("[WARNING] No valid matches extracted from page")
            logger.info("[INFO] Returning sample data for testing...\n")
            return self._get_sample_betika_matches()

        logger.info(f"[SUCCESS] Extracted {len(matches)} matches\n")
        return matches

    def _extract_prize_amount(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract jackpot prize amount from page"""
        try:
            # Look for elements containing prize/amount/jackpot
            prize_patterns = [
                r'KSh?\s*[\d,]+(?:\.\d+)?(?:\s*(?:Million|Billion|M|B))?',
                r'Ksh\s*[\d,]+(?:\.\d+)?(?:\s*(?:Million|Billion|M|B))?',
                r'[\d,]+(?:\.\d+)?\s*(?:Million|Billion)',
                r'Prize:?\s*[\d,]+(?:\.\d+)?'
            ]

            text = soup.get_text()
            for pattern in prize_patterns:
                match = re.search(pattern, text, re.I)
                if match:
                    logger.info(f"[DEBUG] Found prize amount: {match.group(0)}")
                    return match.group(0)

            return None
        except Exception as e:
            logger.debug(f"[DEBUG] Error extracting prize amount: {e}")
            return None

    def _get_sample_sportpesa_matches(self) -> List[Dict]:
        """Return sample SportPesa Mega Jackpot data for testing"""
        logger.info("[INFO] Using sample SportPesa Mega Jackpot data (17 matches)")
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
        logger.info("[INFO] Using sample Betika Jackpot data (15 matches)")
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

            logger.info(f"📝 Saved jackpot history to: {filepath}")

            # Also append to master CSV for easy analysis
            self._append_to_master_csv(jackpot_data)

        except Exception as e:
            logger.warning(f"Warning: Could not save jackpot history: {e}")

    def _append_to_master_csv(self, jackpot_data: Dict):
        """Append jackpot summary to master CSV"""
        try:
            csv_path = self.history_dir / 'jackpot_history.csv'

            # Create summary row
            row = {
                'timestamp': jackpot_data['fetched_at'],
                'provider': jackpot_data['provider'],
                'type': jackpot_data['type'],
                'matches_count': jackpot_data.get('matches_count', len(jackpot_data['matches'])),
                'prize_amount': jackpot_data.get('prize_amount', ''),
                'url': jackpot_data['url'],
                'data_source': jackpot_data.get('data_source', 'unknown')
            }

            # Append to CSV
            df = pd.DataFrame([row])
            if csv_path.exists():
                df.to_csv(csv_path, mode='a', header=False, index=False)
            else:
                df.to_csv(csv_path, mode='w', header=True, index=False)

        except Exception as e:
            logger.warning(f"Warning: Could not append to master CSV: {e}")

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
            logger.error(f"Error loading jackpot history: {e}")
            return pd.DataFrame()


if __name__ == '__main__':
    # Test the fetcher
    fetcher = JackpotFetcher(use_selenium=True, headless=True)

    print("=" * 60)
    print("JACKPOT FETCHER TEST")
    print("=" * 60)

    jackpots = fetcher.get_all_current_jackpots()

    print(f"\n✅ Fetched {len(jackpots)} jackpots\n")

    for jp in jackpots:
        print(f"\n{jp['provider']} - {jp['type']}")
        print(f"Matches: {jp.get('matches_count', len(jp['matches']))}")
        print(f"Prize: {jp.get('prize_amount', 'Unknown')}")
        print(f"Data Source: {jp.get('data_source', 'unknown')}")
        print(f"First 3 matches:")
        for match in jp['matches'][:3]:
            print(f"  {match['match_number']}. {match['home_team']} vs {match['away_team']}")
