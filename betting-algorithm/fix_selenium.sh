#!/bin/bash
#
# Selenium Dependency Fix Script
# Fixes ChromeDriver "Status code 127" error by installing missing dependencies
# Updated for Ubuntu 24.04+ compatibility
#

echo "🔧 Fixing Selenium Dependencies..."
echo "=================================="
echo ""

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "⚠️  This script is for Linux/WSL systems"
    echo "For other platforms, see SELENIUM_TROUBLESHOOTING.md"
    exit 1
fi

# Detect Ubuntu version
if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo "📋 Detected: $NAME $VERSION"
fi

# Update package list
echo ""
echo "📦 Updating package list..."
sudo apt update

# Install Chrome/Chromium and required dependencies
# Updated package names for Ubuntu 22.04+ and 24.04+
echo ""
echo "📦 Installing Chromium and dependencies..."

# Core packages that work across versions
# These are the MINIMAL required packages for ChromeDriver to work
CORE_PACKAGES="
    chromium-browser
    libnss3
    libglib2.0-0
    libfontconfig1
    libgbm1
"

# Optional but recommended packages for better compatibility
OPTIONAL_PACKAGES="
    fonts-liberation
    xdg-utils
    libxss1
"

# Try to install core packages (REQUIRED)
sudo apt install -y $CORE_PACKAGES

if [ $? -ne 0 ]; then
    echo "❌ Failed to install core packages"
    exit 1
fi

# Try optional packages (RECOMMENDED but not required)
echo ""
echo "📦 Installing optional packages for better compatibility..."
sudo apt install -y $OPTIONAL_PACKAGES 2>/dev/null || echo "⚠️  Some optional packages not available (OK)"

echo ""
echo "✅ Available dependencies installed successfully"

# Verify Chrome installation
echo ""
echo "🔍 Verifying Chrome installation..."
if command -v chromium-browser &> /dev/null; then
    CHROME_VERSION=$(chromium-browser --version 2>/dev/null || echo "unknown")
    echo "✅ Chrome installed: $CHROME_VERSION"
elif command -v chromium &> /dev/null; then
    CHROME_VERSION=$(chromium --version 2>/dev/null || echo "unknown")
    echo "✅ Chrome installed: $CHROME_VERSION"
else
    echo "⚠️  Chrome not found in PATH, trying alternative installation..."
    # Try installing chromium as alternative
    sudo apt install -y chromium 2>/dev/null || echo "❌ Could not install Chrome"
fi

# Clear webdriver-manager cache to force fresh download
echo ""
echo "🧹 Clearing ChromeDriver cache..."
rm -rf ~/.wdm/drivers/chromedriver
echo "✅ Cache cleared"

# Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    if [ $? -eq 0 ]; then
        echo "✅ Python packages installed"
    else
        echo "❌ Error installing Python packages"
        exit 1
    fi
else
    echo "⚠️  requirements.txt not found, skipping Python packages"
fi

# Test Selenium
echo ""
echo "🧪 Testing Selenium..."
python3 << 'PYTHON_TEST'
import sys
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    print("   Setting up Chrome options...")
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')

    print("   Installing ChromeDriver...")
    service = Service(ChromeDriverManager().install())

    print("   Starting Chrome...")
    driver = webdriver.Chrome(service=service, options=options)

    print("   Loading test page...")
    driver.get('https://www.google.com')

    if driver.title:
        print(f"✅ Selenium is working correctly!")
        print(f"   Test page title: {driver.title}")

    driver.quit()
    sys.exit(0)
except Exception as e:
    print(f"❌ Selenium test failed: {e}")
    print("\nTroubleshooting:")
    print("  1. Check that Chrome/Chromium is installed: chromium-browser --version")
    print("  2. See SELENIUM_TROUBLESHOOTING.md for more help")
    print("  3. Try manual setup with different Chrome binary")
    sys.exit(1)
PYTHON_TEST

TEST_RESULT=$?

echo ""
if [ $TEST_RESULT -eq 0 ]; then
    echo "🎉 Success! Selenium is working correctly."
    echo ""
    echo "Next steps:"
    echo "  1. Test jackpot fetcher: python3 src/jackpot_fetcher.py"
    echo "  2. Run tests: pytest tests/test_jackpot_fetcher.py -v"
    echo ""
    echo "Your system is ready to fetch live jackpot data!"
else
    echo "❌ Selenium is still not working correctly"
    echo ""
    echo "Alternative options:"
    echo "  1. Use sample data mode: JackpotFetcher(use_selenium=False)"
    echo "  2. See SELENIUM_TROUBLESHOOTING.md for manual setup"
    echo "  3. Check if your system has special requirements"
    exit 1
fi
