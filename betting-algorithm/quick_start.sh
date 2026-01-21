#!/bin/bash

echo "🚀 Quick Start - Betting Algorithm"
echo ""

# Check Python version
python3 --version || { echo "Python 3 not found"; exit 1; }

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Setup environment
if [ ! -f .env ]; then
    cp .env.example .env
    echo "📝 Created .env file - please add your API keys"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Run: python src/data_collector.py"
echo "  3. Run: python src/backtest.py"
