#!/usr/bin/env python3
"""
Diagnostic script to debug SportPesa jackpot fetching issues

This script will:
1. Test Selenium availability
2. Load SportPesa page in non-headless mode
3. Save page HTML for inspection
4. Test all CSS selectors
5. Provide detailed output of what's found

Usage: python3 diagnose_sportpesa.py
"""

import sys
import time
from pathlib import Path

# Check Selenium availability
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from webdriver_manager.chrome import ChromeDriverManager
    from bs4 import BeautifulSoup
    SELENIUM_AVAILABLE = True
except ImportError as e:
    print(f"❌ Selenium not available: {e}")
    print("Run: pip install selenium webdriver-manager beautifulsoup4")
    sys.exit(1)

print("="*70)
print("SPORTPESA JACKPOT DIAGNOSTIC TOOL")
print("="*70)

# Create driver
print("\n1️⃣ Creating Chrome WebDriver...")
try:
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')  # Change to False to see browser
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_page_load_timeout(30)

    print("✅ WebDriver created successfully")
except Exception as e:
    print(f"❌ Failed to create WebDriver: {e}")
    sys.exit(1)

# Load SportPesa page
url = "https://www.ke.sportpesa.com/en/mega-jackpot-pro"
print(f"\n2️⃣ Loading SportPesa page: {url}")

try:
    driver.get(url)
    print(f"✅ Page loaded (status: {driver.execute_script('return document.readyState')})")

    # Wait for JavaScript to render
    print("⏳ Waiting 5 seconds for JavaScript to render...")
    time.sleep(5)

except Exception as e:
    print(f"❌ Failed to load page: {e}")
    driver.quit()
    sys.exit(1)

# Get page source
print("\n3️⃣ Analyzing page structure...")
html = driver.page_source
soup = BeautifulSoup(html, 'html.parser')

# Save HTML for manual inspection
debug_dir = Path('./debug')
debug_dir.mkdir(exist_ok=True)
html_file = debug_dir / 'sportpesa_page.html'

with open(html_file, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"💾 Saved page HTML to: {html_file}")
print(f"📊 Page size: {len(html):,} bytes")

# Test carousel indicators
print("\n4️⃣ Testing Carousel Indicators...")
indicator_selectors = [
    'div.carousel-indicators button',
    'div.carousel-indicators li',
    'div[class*="indicator"] button',
    'div[class*="dot"]',
    'button[data-slide-to]',
    '.slick-dots li',
    'ol.carousel-indicators li',
    'div[role="tablist"] button',
    'button[role="tab"]'
]

found_indicators = False
for selector in indicator_selectors:
    try:
        indicators = driver.find_elements(By.CSS_SELECTOR, selector)
        if indicators:
            print(f"✅ Found {len(indicators)} indicators: {selector}")
            found_indicators = True

            # Print indicator details
            for i, ind in enumerate(indicators[:5]):
                try:
                    classes = ind.get_attribute('class')
                    aria_label = ind.get_attribute('aria-label')
                    print(f"   [{i+1}] class='{classes}' aria-label='{aria_label}'")
                except:
                    pass
            break
    except Exception as e:
        continue

if not found_indicators:
    print("⚠️  No carousel indicators found with standard selectors")

# Test next button
print("\n5️⃣ Testing Next Button...")
next_selectors = [
    'button.carousel-control-next',
    'button[data-slide="next"]',
    'div.slick-next',
    'button[class*="next"]',
    'a[class*="next"]',
    'button[aria-label*="next" i]',
    'div[class*="arrow"][class*="right"]',
    'button[class*="arrow"][class*="right"]'
]

found_next = False
for selector in next_selectors:
    try:
        next_btns = driver.find_elements(By.CSS_SELECTOR, selector)
        if next_btns:
            print(f"✅ Found {len(next_btns)} next button(s): {selector}")
            found_next = True

            for i, btn in enumerate(next_btns[:3]):
                try:
                    visible = btn.is_displayed()
                    classes = btn.get_attribute('class')
                    print(f"   [{i+1}] visible={visible} class='{classes}'")
                except:
                    pass
            break
    except:
        continue

if not found_next:
    print("⚠️  No next button found with standard selectors")

# Test jackpot title
print("\n6️⃣ Testing Jackpot Title...")
title_selectors = [
    'h1',
    'h2',
    'h1[class*="title"]',
    'h2[class*="title"]',
    'div[class*="title"]',
    'div[class*="jackpot"][class*="name"]',
    'span[class*="title"]',
    'div[class*="jackpot-title"]',
    'div[class*="heading"]'
]

found_title = False
for selector in title_selectors:
    try:
        titles = soup.select(selector)
        for title in titles:
            text = title.get_text(strip=True)
            if text and 'jackpot' in text.lower():
                print(f"✅ Found title: '{text}'")
                print(f"   Selector: {selector}")
                found_title = True
                break
        if found_title:
            break
    except:
        continue

if not found_title:
    print("⚠️  No jackpot title found")
    # Try regex search
    import re
    text = soup.get_text()
    jackpot_match = re.search(r'([\w\s]+ JACKPOT [\w\s]+\d+)', text, re.I)
    if jackpot_match:
        print(f"✅ Found title via regex: '{jackpot_match.group(1).strip()}'")

# Test prize amount
print("\n7️⃣ Testing Prize Amount...")
prize_patterns = [
    r'KSH\s*([\d,]+)',
    r'Ksh\s*([\d,]+)',
    r'KES\s*([\d,]+)',
    r'([\d,]+)\s*Million',
    r'Prize:?\s*([\d,]+)'
]

found_prize = False
text = soup.get_text()
for pattern in prize_patterns:
    import re
    matches = re.findall(pattern, text, re.I)
    if matches:
        print(f"✅ Found prize amounts: {matches[:3]}")
        print(f"   Pattern: {pattern}")
        found_prize = True
        break

if not found_prize:
    print("⚠️  No prize amount found")

# Test match elements
print("\n8️⃣ Testing Match Elements...")
match_selectors = [
    'div.jackpot-match',
    'div.match-row',
    'div[class*="match"]',
    'tr[class*="match"]',
    'li[class*="match"]',
    'div[class*="game"]',
    'div[class*="fixture"]',
    'article[class*="match"]'
]

found_matches = False
for selector in match_selectors:
    try:
        matches = soup.select(selector)
        if matches and len(matches) > 5:  # Should have multiple matches
            print(f"✅ Found {len(matches)} match elements: {selector}")
            found_matches = True

            # Inspect first match
            first_match = matches[0]
            print(f"\n   First match HTML sample:")
            print(f"   {str(first_match)[:200]}...")

            # Try to extract teams
            team_elems = first_match.find_all(class_=re.compile(r'team|opponent', re.I))
            if team_elems:
                print(f"   Found {len(team_elems)} team elements")
                for i, team in enumerate(team_elems[:2]):
                    print(f"      Team {i+1}: {team.get_text(strip=True)}")

            break
    except Exception as e:
        continue

if not found_matches:
    print("⚠️  No match elements found with standard selectors")

    # Try to find ANY elements that might be matches
    print("\n   Searching for common patterns...")
    all_divs = soup.find_all('div', limit=50)
    for div in all_divs:
        text = div.get_text(strip=True)
        if 'vs' in text.lower() or ' v ' in text.lower():
            classes = div.get('class', [])
            print(f"   Found potential match: class={classes} text='{text[:60]}'")

# Check for common anti-scraping measures
print("\n9️⃣ Checking for Anti-Scraping Measures...")

# Check for Cloudflare
if 'cloudflare' in html.lower() or 'cf-browser-verification' in html.lower():
    print("⚠️  Cloudflare protection detected")

# Check for bot detection
if 'robot' in html.lower() or 'captcha' in html.lower():
    print("⚠️  Bot detection/CAPTCHA detected")

# Check for JavaScript requirements
if 'javascript' in html.lower() and 'enable' in html.lower():
    print("⚠️  JavaScript requirement notice found")

# Print all class names used on page (helps find correct selectors)
print("\n🔍 Top 20 Most Common CSS Classes on Page:")
from collections import Counter
all_classes = []
for elem in soup.find_all(class_=True):
    all_classes.extend(elem.get('class', []))

class_counts = Counter(all_classes)
for cls, count in class_counts.most_common(20):
    print(f"   .{cls} ({count} occurrences)")

# Screenshot (if not headless)
print("\n📸 Taking screenshot...")
screenshot_file = debug_dir / 'sportpesa_screenshot.png'
try:
    driver.save_screenshot(str(screenshot_file))
    print(f"✅ Screenshot saved to: {screenshot_file}")
except Exception as e:
    print(f"⚠️  Could not save screenshot: {e}")

# Cleanup
driver.quit()

print("\n" + "="*70)
print("DIAGNOSTIC COMPLETE")
print("="*70)
print(f"\n📁 Debug files saved to: {debug_dir.absolute()}")
print(f"   - {html_file.name} - Full page HTML")
print(f"   - {screenshot_file.name} - Page screenshot")
print("\n💡 Next Steps:")
print("   1. Review the HTML file to understand page structure")
print("   2. Look at the screenshot to see what's actually displayed")
print("   3. Update CSS selectors in jackpot_fetcher_enhanced.py based on findings")
print("   4. If Cloudflare/bot detection is active, may need to add delays or headers")
