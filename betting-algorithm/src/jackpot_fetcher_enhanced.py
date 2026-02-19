"""
Enhanced Jackpot Fetcher - Handles SportPesa carousel/slideshow interface

This version can navigate through carousel slides to fetch all available jackpots
from a single page, extracting unique matches for each jackpot type.

Author: AI Betting Algorithm
Date: 2026-02-16
"""

import time
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import json
import pandas as pd
import re

from bs4 import BeautifulSoup

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
    from selenium.webdriver.common.action_chains import ActionChains
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedJackpotFetcher:
    """Enhanced fetcher that can handle carousel/slideshow interfaces"""

    def __init__(self, use_selenium: bool = True, headless: bool = True, timeout: int = 30):
        """
        Initialize the Enhanced JackpotFetcher

        Args:
            use_selenium: Whether to use Selenium
            headless: Whether to run Chrome in headless mode
            timeout: Timeout in seconds for page loads
        """
        self.use_selenium = use_selenium and SELENIUM_AVAILABLE
        self.headless = headless
        self.timeout = timeout

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.history_dir = Path('./data/jackpots')
        self.history_dir.mkdir(parents=True, exist_ok=True)

        if not SELENIUM_AVAILABLE and use_selenium:
            logger.warning("Selenium not available. Falling back to sample data mode.")
            self.use_selenium = False

    def _create_driver(self) -> webdriver.Chrome:
        """Create and configure a Chrome WebDriver instance"""
        try:
            chrome_options = Options()

            if self.headless:
                chrome_options.add_argument('--headless=new')

            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument(f'user-agent={self.headers["User-Agent"]}')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(self.timeout)

            logger.info("✅ Chrome WebDriver initialized successfully")
            return driver

        except Exception as e:
            logger.error(f"❌ Failed to create Chrome driver: {e}")
            raise

    def fetch_all_sportpesa_jackpots(self) -> List[Dict]:
        """
        Fetch ALL SportPesa jackpots by navigating through the carousel

        Returns:
            List of jackpot dictionaries, one for each jackpot in the carousel
        """
        if not self.use_selenium:
            logger.info("Selenium disabled, using sample data")
            return self._get_sample_all_jackpots()

        driver = None
        jackpots = []

        try:
            driver = self._create_driver()
            url = "https://www.ke.sportpesa.com/en/mega-jackpot-pro"

            logger.info(f"🌐 Fetching SportPesa jackpots from: {url}")
            driver.get(url)

            # Wait for page to load
            time.sleep(5)

            # Try to find carousel indicators (dots) to see how many jackpots there are
            carousel_indicators = self._find_carousel_indicators(driver)
            num_jackpots = len(carousel_indicators) if carousel_indicators else 1

            logger.info(f"📊 Found {num_jackpots} jackpot(s) in carousel")

            # Navigate through each carousel slide
            for slide_index in range(num_jackpots):
                logger.info(f"\n🎰 Processing jackpot {slide_index + 1}/{num_jackpots}")

                # Wait for content to load
                time.sleep(2)

                # Extract current jackpot data
                jackpot_data = self._extract_current_slide_data(driver)

                if jackpot_data and jackpot_data.get('matches'):
                    jackpots.append(jackpot_data)
                    logger.info(f"✅ Extracted: {jackpot_data['type']} with {len(jackpot_data['matches'])} matches")
                else:
                    logger.warning(f"⚠️ No data found for slide {slide_index + 1}")

                # Click next arrow if not on last slide
                if slide_index < num_jackpots - 1:
                    self._click_next_slide(driver)
                    time.sleep(2)  # Wait for transition

            logger.info(f"\n✅ Successfully extracted {len(jackpots)} jackpot(s)")

        except Exception as e:
            logger.error(f"❌ Error fetching SportPesa jackpots: {e}")
            import traceback
            traceback.print_exc()

            # Return sample data as fallback
            return self._get_sample_all_jackpots()

        finally:
            if driver:
                driver.quit()

        # Save all jackpots to history
        for jackpot in jackpots:
            self._save_jackpot_history(jackpot)

        return jackpots if jackpots else self._get_sample_all_jackpots()

    def _find_carousel_indicators(self, driver) -> List:
        """Find carousel indicator dots to determine number of slides"""
        try:
            # Common carousel indicator selectors
            selectors = [
                'div.carousel-indicators button',
                'div.carousel-indicators li',
                'div[class*="indicator"] button',
                'div[class*="dot"]',
                'button[data-slide-to]',
                '.slick-dots li',
                'ol.carousel-indicators li'
            ]

            for selector in selectors:
                try:
                    indicators = driver.find_elements(By.CSS_SELECTOR, selector)
                    if indicators:
                        logger.info(f"[DEBUG] Found {len(indicators)} indicators with selector: {selector}")
                        return indicators
                except:
                    continue

            logger.warning("[WARNING] No carousel indicators found")
            return []

        except Exception as e:
            logger.debug(f"[DEBUG] Error finding carousel indicators: {e}")
            return []

    def _click_next_slide(self, driver):
        """Click the next arrow/button in the carousel"""
        try:
            # Common next button selectors
            next_selectors = [
                'button.carousel-control-next',
                'button[data-slide="next"]',
                'div.slick-next',
                'button[class*="next"]',
                'a[class*="next"]',
                'button[aria-label*="next" i]',
                'div[class*="arrow"][class*="right"]'
            ]

            for selector in next_selectors:
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, selector)
                    if next_button and next_button.is_displayed():
                        logger.info(f"[DEBUG] Clicking next button: {selector}")
                        next_button.click()
                        return True
                except NoSuchElementException:
                    continue

            logger.warning("[WARNING] Could not find next button")
            return False

        except Exception as e:
            logger.error(f"[ERROR] Failed to click next: {e}")
            return False

    def _extract_current_slide_data(self, driver) -> Optional[Dict]:
        """Extract jackpot data from the current carousel slide"""
        try:
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')

            # Extract jackpot title/type
            jackpot_title = self._extract_jackpot_title(soup)

            # Extract prize amount
            prize_amount = self._extract_prize_amount(soup)

            # Extract number of matches (e.g., "17" from "MEGA JACKPOT PRO 17")
            match_count = self._extract_match_count(jackpot_title)

            # Extract matches
            matches = self._extract_matches(soup)

            jackpot_data = {
                'provider': 'SportPesa',
                'type': jackpot_title or 'Unknown Jackpot',
                'matches_count': match_count or len(matches),
                'prize_amount': prize_amount,
                'fetched_at': datetime.now().isoformat(),
                'url': driver.current_url,
                'data_source': 'selenium',
                'matches': matches
            }

            return jackpot_data

        except Exception as e:
            logger.error(f"[ERROR] Failed to extract slide data: {e}")
            return None

    def _extract_jackpot_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract jackpot title from page"""
        try:
            # Common title selectors
            title_selectors = [
                'h1',
                'h2',
                'div[class*="title"]',
                'div[class*="jackpot"][class*="name"]',
                'span[class*="title"]'
            ]

            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if 'jackpot' in title.lower():
                        logger.info(f"[DEBUG] Found title: {title}")
                        return title

            # Fallback: search for text containing "JACKPOT"
            text = soup.get_text()
            jackpot_match = re.search(r'([\w\s]+ JACKPOT [\w\s]+)', text, re.I)
            if jackpot_match:
                return jackpot_match.group(1).strip()

            return None

        except Exception as e:
            logger.debug(f"[DEBUG] Error extracting title: {e}")
            return None

    def _extract_match_count(self, title: str) -> Optional[int]:
        """Extract number of matches from title (e.g., '17' from 'MEGA JACKPOT PRO 17')"""
        try:
            if not title:
                return None

            # Look for numbers in the title
            numbers = re.findall(r'\d+', title)
            if numbers:
                return int(numbers[-1])  # Usually the last number is the match count

            return None

        except Exception as e:
            logger.debug(f"[DEBUG] Error extracting match count: {e}")
            return None

    def _extract_prize_amount(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract prize amount from page"""
        try:
            # Look for prize patterns
            prize_patterns = [
                r'KSH\s*([\d,]+)',
                r'Ksh\s*([\d,]+)',
                r'([\d,]+)\s*Million',
                r'Prize:?\s*([\d,]+)'
            ]

            text = soup.get_text()
            for pattern in prize_patterns:
                match = re.search(pattern, text, re.I)
                if match:
                    logger.info(f"[DEBUG] Found prize: {match.group(0)}")
                    return match.group(0)

            return None

        except Exception as e:
            logger.debug(f"[DEBUG] Error extracting prize: {e}")
            return None

    def _extract_matches(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract match details from current page"""
        matches = []

        try:
            # Try multiple selectors
            selectors = [
                'div.jackpot-match',
                'div.match-row',
                'div[class*="match"]',
                'tr[class*="match"]',
                'li[class*="match"]'
            ]

            match_elements = []
            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    logger.info(f"[DEBUG] Found {len(elements)} elements with: {selector}")
                    match_elements = elements
                    break

            if not match_elements:
                logger.warning("[WARNING] No match elements found")
                return []

            for idx, element in enumerate(match_elements[:20]):
                try:
                    # Extract teams
                    teams = []

                    # Strategy 1: team classes
                    team_elements = element.find_all(class_=re.compile(r'team|opponent', re.I))
                    if team_elements and len(team_elements) >= 2:
                        teams = [t.get_text(strip=True) for t in team_elements[:2]]

                    # Strategy 2: home/away containers
                    if not teams:
                        home = element.find(class_=re.compile(r'home', re.I))
                        away = element.find(class_=re.compile(r'away', re.I))
                        if home and away:
                            teams = [home.get_text(strip=True), away.get_text(strip=True)]

                    if len(teams) >= 2 and all(len(t) > 2 for t in teams):
                        home_team = teams[0]
                        away_team = teams[1]

                        # Extract additional info
                        date_elem = element.find(class_=re.compile(r'date|time|kick', re.I))
                        match_date = date_elem.get_text(strip=True) if date_elem else None

                        comp_elem = element.find(class_=re.compile(r'league|competition', re.I))
                        competition = comp_elem.get_text(strip=True) if comp_elem else None

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

            logger.info(f"[SUCCESS] Extracted {len(matches)} matches")
            return matches

        except Exception as e:
            logger.error(f"[ERROR] Failed to extract matches: {e}")
            return []

    def _save_jackpot_history(self, jackpot_data: Dict):
        """Save jackpot to history"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            provider = jackpot_data['provider'].lower().replace(' ', '_')
            jackpot_type = jackpot_data['type'].lower().replace(' ', '_')

            filename = f"{provider}_{jackpot_type}_{timestamp}.json"
            filepath = self.history_dir / filename

            with open(filepath, 'w') as f:
                json.dump(jackpot_data, f, indent=2)

            logger.info(f"📝 Saved: {filepath}")

            # Append to CSV
            self._append_to_csv(jackpot_data)

        except Exception as e:
            logger.warning(f"Warning: Could not save history: {e}")

    def _append_to_csv(self, jackpot_data: Dict):
        """Append to master CSV"""
        try:
            csv_path = self.history_dir / 'jackpot_history.csv'

            row = {
                'timestamp': jackpot_data['fetched_at'],
                'provider': jackpot_data['provider'],
                'type': jackpot_data['type'],
                'matches_count': jackpot_data.get('matches_count', len(jackpot_data['matches'])),
                'prize_amount': jackpot_data.get('prize_amount', ''),
                'url': jackpot_data['url'],
                'data_source': jackpot_data.get('data_source', 'unknown')
            }

            df = pd.DataFrame([row])
            if csv_path.exists():
                df.to_csv(csv_path, mode='a', header=False, index=False)
            else:
                df.to_csv(csv_path, mode='w', header=True, index=False)

        except Exception as e:
            logger.warning(f"Warning: Could not append to CSV: {e}")

    def _get_sample_all_jackpots(self) -> List[Dict]:
        """Return sample data for all jackpots"""
        logger.info("[INFO] Using sample data for all jackpots")

        return [
            {
                'provider': 'SportPesa',
                'type': 'Mega Jackpot Pro 17',
                'matches_count': 17,
                'prize_amount': 'KSH 116,478,633',
                'fetched_at': datetime.now().isoformat(),
                'url': 'https://www.ke.sportpesa.com/en/mega-jackpot-pro',
                'data_source': 'sample',
                'matches': self._get_sample_matches(17)
            },
            {
                'provider': 'SportPesa',
                'type': 'Midweek Jackpot 13',
                'matches_count': 13,
                'prize_amount': 'KSH 25,000,000',
                'fetched_at': datetime.now().isoformat(),
                'url': 'https://www.ke.sportpesa.com/en/jackpot',
                'data_source': 'sample',
                'matches': self._get_sample_matches(13)
            }
        ]

    def _get_sample_matches(self, count: int) -> List[Dict]:
        """Generate sample matches"""
        sample_teams = [
            ('Arsenal', 'Chelsea'),
            ('Man City', 'Liverpool'),
            ('Tottenham', 'Man United'),
            ('Real Madrid', 'Barcelona'),
            ('Bayern Munich', 'Dortmund'),
            ('Inter Milan', 'AC Milan'),
            ('PSG', 'Marseille'),
            ('Juventus', 'Napoli'),
            ('Atletico Madrid', 'Sevilla'),
            ('Leicester', 'West Ham'),
            ('Newcastle', 'Aston Villa'),
            ('Brighton', 'Wolves'),
            ('Everton', 'Southampton'),
            ('Leeds United', 'Burnley'),
            ('Sheffield United', 'Norwich'),
            ('Brentford', 'Fulham'),
            ('Crystal Palace', 'Bournemouth')
        ]

        return [
            {
                'match_number': i + 1,
                'home_team': sample_teams[i % len(sample_teams)][0],
                'away_team': sample_teams[i % len(sample_teams)][1],
                'competition': 'Premier League',
                'kickoff': 'Sat 15:00'
            }
            for i in range(count)
        ]


if __name__ == '__main__':
    # Test the enhanced fetcher
    fetcher = EnhancedJackpotFetcher(use_selenium=True, headless=True)

    print("=" * 70)
    print("ENHANCED JACKPOT FETCHER TEST - CAROUSEL NAVIGATION")
    print("=" * 70)

    jackpots = fetcher.fetch_all_sportpesa_jackpots()

    print(f"\n✅ Fetched {len(jackpots)} jackpot(s)\n")

    for jp in jackpots:
        print(f"\n{'='*60}")
        print(f"{jp['provider']} - {jp['type']}")
        print(f"{'='*60}")
        print(f"Prize: {jp.get('prize_amount', 'Unknown')}")
        print(f"Matches: {jp.get('matches_count', len(jp['matches']))}")
        print(f"Data Source: {jp.get('data_source', 'unknown')}")
        print(f"\nFirst 5 matches:")
        for match in jp['matches'][:5]:
            print(f"  {match['match_number']}. {match['home_team']} vs {match['away_team']}")
