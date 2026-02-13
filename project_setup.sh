#!/bin/bash

# ==============================================================================
# Sports Betting Analytics Platform - Automated Setup Script
# ==============================================================================
# This script automatically sets up the complete project:
# - Python Flask Backend
# - Angular Frontend
# - All necessary files and dependencies
#
# Usage: bash setup.sh
# ==============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${PURPLE}╔════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║${NC}  $1${PURPLE}║${NC}"
    echo -e "${PURPLE}╚════════════════════════════════════════════════════════════════════╝${NC}"
}

print_step() {
    echo -e "\n${CYAN}▶${NC} ${BLUE}$1${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

check_command() {
    if command -v $1 &> /dev/null; then
        print_success "$1 is installed"
        return 0
    else
        print_error "$1 is not installed"
        return 1
    fi
}

# Clear screen and show header
clear
print_header "  SPORTS BETTING ANALYTICS PLATFORM - AUTOMATED SETUP  "

echo -e "\n${CYAN}This script will set up the complete project:${NC}"
echo "  • Python Flask Backend"
echo "  • Angular Frontend"
echo "  • All necessary dependencies"
echo "  • Project structure and files"
echo ""
echo -e "${YELLOW}Press Ctrl+C to cancel, or Enter to continue...${NC}"
read

# ==============================================================================
# STEP 1: Check Prerequisites
# ==============================================================================

print_step "Step 1: Checking prerequisites..."

PREREQUISITES_OK=true

# Check Python
if check_command python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python version: $PYTHON_VERSION"
else
    print_error "Python 3.8+ is required"
    PREREQUISITES_OK=false
fi

# Check Node.js
if check_command node; then
    NODE_VERSION=$(node --version)
    print_success "Node.js version: $NODE_VERSION"
else
    print_error "Node.js 18+ is required"
    PREREQUISITES_OK=false
fi

# Check npm
if check_command npm; then
    NPM_VERSION=$(npm --version)
    print_success "npm version: $NPM_VERSION"
else
    print_error "npm is required"
    PREREQUISITES_OK=false
fi

# Check Angular CLI
if check_command ng; then
    NG_VERSION=$(ng version 2>/dev/null | grep "Angular CLI" | cut -d':' -f2 | xargs)
    print_success "Angular CLI version: $NG_VERSION"
else
    print_warning "Angular CLI not found. Will install it..."
    npm install -g @angular/cli
fi

if [ "$PREREQUISITES_OK" = false ]; then
    print_error "\nPrerequisites check failed. Please install missing software and try again."
    exit 1
fi

print_success "\nAll prerequisites met!"

# ==============================================================================
# STEP 2: Create Project Directory
# ==============================================================================

print_step "Step 2: Creating project directory..."

PROJECT_NAME="betting-analytics-platform"

if [ -d "$PROJECT_NAME" ]; then
    print_warning "Directory $PROJECT_NAME already exists."
    echo -e "${YELLOW}Do you want to remove it and start fresh? (y/N):${NC} "
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        rm -rf "$PROJECT_NAME"
        print_success "Removed existing directory"
    else
        print_error "Setup cancelled"
        exit 1
    fi
fi

mkdir -p "$PROJECT_NAME"
cd "$PROJECT_NAME"

print_success "Created project directory: $PROJECT_NAME"

# ==============================================================================
# STEP 3: Setup Python Backend
# ==============================================================================

print_step "Step 3: Setting up Python Flask backend..."

# Create backend directory structure
mkdir -p backend/{src,data/{raw,processed,final},results/{backtests,predictions,performance},models/{calibration,weights},config,templates}

# Create Python virtual environment
print_step "Creating Python virtual environment..."
python3 -m venv backend/venv

# Activate virtual environment
source backend/venv/bin/activate

# Create requirements.txt
cat > backend/requirements.txt << 'EOF'
# Core dependencies
flask==3.0.0
flask-cors==4.0.0
pandas>=1.5.0
numpy>=1.23.0
requests>=2.28.0
beautifulsoup4>=4.11.0
python-dotenv>=0.20.0

# Sports data
soccerdata>=1.3.0

# Optional: Advanced features
scikit-learn>=1.1.0
matplotlib>=3.5.0
seaborn>=0.12.0
EOF

print_step "Installing Python dependencies..."
pip install -r backend/requirements.txt

print_success "Python dependencies installed"

# Create .env file
cat > backend/.env << 'EOF'
# API Keys
ODDS_API_KEY=your_key_here
API_FOOTBALL_KEY=your_key_here

# Configuration
DEFAULT_SPORT=football
INITIAL_BANKROLL=1000
MAX_BET_PERCENTAGE=5
KELLY_FRACTION=0.25

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
EOF

print_success "Created .env file"

# Create .gitignore
cat > backend/.gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
.env

# Data
data/raw/*
data/processed/*
data/final/*
!data/.gitkeep

# Results
results/backtests/*
results/predictions/*
results/performance/*
!results/.gitkeep

# Jupyter
.ipynb_checkpoints/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
EOF

print_success "Backend structure created"

# ==============================================================================
# STEP 4: Setup Angular Frontend
# ==============================================================================

print_step "Step 4: Setting up Angular frontend..."

cd ..

# Create Angular project
print_step "Creating Angular project (this may take a few minutes)..."
ng new frontend --routing --style=scss --skip-git --package-manager=npm << 'ANSWERS'
y
ANSWERS

cd frontend

# Install Angular Material
print_step "Installing Angular Material..."
ng add @angular/material --skip-confirmation << 'MATERIAL_ANSWERS'
custom
y
y
MATERIAL_ANSWERS

# Install additional dependencies
print_step "Installing additional dependencies..."
npm install chart.js ng2-charts --save

print_success "Angular dependencies installed"

# Create directory structure
mkdir -p src/app/{core/{services,models,guards},features/{dashboard,predictions,backtesting,data-collection,performance,configuration},shared/components}

print_success "Angular structure created"

# ==============================================================================
# STEP 5: Create Python Backend Files
# ==============================================================================

print_step "Step 5: Creating Python backend files..."

cd ../backend

# Create app.py
cat > app.py << 'EOF'
"""
Flask Backend Server for Sports Betting Analytics Platform
"""

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return jsonify({
        'message': 'Sports Betting Analytics API',
        'version': '1.0.0',
        'status': 'running'
    })

@app.route('/api/dashboard/stats')
def get_dashboard_stats():
    return jsonify({
        'overall_accuracy': 67.2,
        'roi': 18.4,
        'total_predictions': 1248,
        'win_streak': 7,
        'current_bankroll': 1184,
        'total_pnl': 184
    })

@app.route('/api/dashboard/upcoming')
def get_upcoming():
    return jsonify([
        {
            'id': 'arsenal-chelsea',
            'homeTeam': 'Arsenal',
            'awayTeam': 'Chelsea',
            'competition': 'Premier League',
            'kickoff': '2025-01-21T15:00:00Z',
            'homeOdds': 2.10,
            'drawOdds': 3.40,
            'awayOdds': 3.60,
            'prediction': {
                'outcome': 'Home Win',
                'homeProb': 0.58,
                'drawProb': 0.23,
                'awayProb': 0.19,
                'confidence': 0.82,
                'expectedValue': 12.3,
                'recommendation': 'Strong Bet'
            }
        }
    ])

@app.route('/api/dashboard/recent')
def get_recent():
    return jsonify([])

if __name__ == '__main__':
    print("="*70)
    print(" SPORTS BETTING ANALYTICS PLATFORM - SERVER")
    print("="*70)
    print("\n🚀 Starting Flask server...")
    print("📊 Dashboard: http://localhost:5000")
    print("🔌 API: http://localhost:5000/api")
    print("\nPress CTRL+C to stop\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
EOF

print_success "Created app.py"

# Create src/__init__.py
touch src/__init__.py

print_success "Python backend files created"

# ==============================================================================
# STEP 6: Create Angular Files
# ==============================================================================

print_step "Step 6: Creating Angular files..."

cd ../frontend

# Update environment files
cat > src/environments/environment.ts << 'EOF'
export const environment = {
  production: false,
  apiUrl: 'http://localhost:5000/api',
  wsUrl: 'ws://localhost:5000',
  apiTimeout: 30000
};
EOF

cat > src/environments/environment.prod.ts << 'EOF'
export const environment = {
  production: true,
  apiUrl: 'https://your-production-api.com/api',
  wsUrl: 'wss://your-production-api.com',
  apiTimeout: 30000
};
EOF

# Update angular.json to use environment files
print_success "Environment files created"

# Create app.routes.ts
cat > src/app/app.routes.ts << 'EOF'
import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    redirectTo: '/dashboard',
    pathMatch: 'full'
  },
  {
    path: 'dashboard',
    loadComponent: () => import('./features/dashboard/dashboard.component')
      .then(m => m.DashboardComponent),
    title: 'Dashboard - Betting Analytics'
  },
  {
    path: '**',
    redirectTo: '/dashboard'
  }
];
EOF

print_success "Angular routing configured"

# Update styles.scss
cat > src/styles.scss << 'EOF'
@use '@angular/material' as mat;

@include mat.core();

$my-primary: mat.define-palette(mat.$indigo-palette);
$my-accent: mat.define-palette(mat.$purple-palette);
$my-warn: mat.define-palette(mat.$red-palette);

$my-theme: mat.define-dark-theme((
  color: (
    primary: $my-primary,
    accent: $my-accent,
    warn: $my-warn,
  ),
));

@include mat.all-component-themes($my-theme);

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  height: 100%;
  font-family: 'Inter', 'Roboto', sans-serif;
}

body {
  margin: 0;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  color: #e2e8f0;
}
EOF

print_success "Angular styles configured"

# ==============================================================================
# STEP 7: Create README Files
# ==============================================================================

print_step "Step 7: Creating documentation..."

cd ..

# Main README
cat > README.md << 'EOF'
# 🎯 Sports Betting Analytics Platform

Professional sports betting analytics platform with AI-powered predictions, backtesting, and performance tracking.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 18+
- Angular CLI 17+

### Installation

1. **Clone/Navigate to project**
```bash
cd betting-analytics-platform
```

2. **Start Backend**
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python app.py
```

3. **Start Frontend** (in new terminal)
```bash
cd frontend
ng serve --open
```

4. **Access Application**
- Frontend: http://localhost:4200
- Backend API: http://localhost:5000

## 📁 Project Structure

```
betting-analytics-platform/
├── backend/          # Flask API
│   ├── src/         # Python source code
│   ├── data/        # Data storage
│   ├── results/     # Backtest results
│   └── app.py       # Flask server
└── frontend/        # Angular app
    └── src/         # Angular source code
```

## 🎨 Features

- 📊 Real-time Dashboard
- 🎯 AI-Powered Predictions
- 🧪 Historical Backtesting
- 📥 Automated Data Collection
- 📈 Performance Analytics
- ⚙️ Configurable Algorithm

## 🛠️ Development

See individual README files in `backend/` and `frontend/` folders for detailed development instructions.

## 📄 License

MIT License
EOF

# Backend README
cat > backend/README.md << 'EOF'
# Backend - Flask API

## Setup

```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

API will be available at http://localhost:5000

## API Endpoints

- `GET /api/dashboard/stats` - Dashboard statistics
- `GET /api/dashboard/upcoming` - Upcoming predictions
- `GET /api/dashboard/recent` - Recent results

See app.py for full API documentation.
EOF

# Frontend README
cat > frontend/README.md << 'EOF'
# Frontend - Angular Application

## Setup

```bash
npm install
```

## Development

```bash
ng serve --open
```

Application will be available at http://localhost:4200

## Build

```bash
ng build --configuration production
```

Output will be in `dist/` folder.
EOF

print_success "Documentation created"

# ==============================================================================
# STEP 8: Create Startup Scripts
# ==============================================================================

print_step "Step 8: Creating startup scripts..."

# Start backend script
cat > start-backend.sh << 'EOF'
#!/bin/bash
cd backend
source venv/bin/activate
python app.py
EOF

chmod +x start-backend.sh

# Start frontend script
cat > start-frontend.sh << 'EOF'
#!/bin/bash
cd frontend
ng serve --open
EOF

chmod +x start-frontend.sh

# Start both script
cat > start-all.sh << 'EOF'
#!/bin/bash

echo "🚀 Starting Sports Betting Analytics Platform..."
echo ""

# Start backend in background
echo "📡 Starting Backend API..."
cd backend
source venv/bin/activate
python app.py &
BACKEND_PID=$!
cd ..

# Wait a bit for backend to start
sleep 3

# Start frontend
echo "🎨 Starting Frontend..."
cd frontend
ng serve --open &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Both services started!"
echo ""
echo "  Backend API: http://localhost:5000"
echo "  Frontend:    http://localhost:4200"
echo ""
echo "Press Ctrl+C to stop all services..."

# Wait for Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
EOF

chmod +x start-all.sh

# Windows batch files
cat > start-backend.bat << 'EOF'
@echo off
cd backend
call venv\Scripts\activate.bat
python app.py
EOF

cat > start-frontend.bat << 'EOF'
@echo off
cd frontend
ng serve --open
EOF

print_success "Startup scripts created"

# ==============================================================================
# STEP 9: Final Summary
# ==============================================================================

print_header "  SETUP COMPLETE!  "

echo -e "\n${GREEN}✓ Project successfully created!${NC}\n"

echo -e "${CYAN}Project Location:${NC}"
echo -e "  $(pwd)\n"

echo -e "${CYAN}What was installed:${NC}"
echo -e "  ${GREEN}✓${NC} Python Flask Backend"
echo -e "  ${GREEN}✓${NC} Angular 17 Frontend"
echo -e "  ${GREEN}✓${NC} All dependencies"
echo -e "  ${GREEN}✓${NC} Project structure"
echo -e "  ${GREEN}✓${NC} Startup scripts\n"

echo -e "${CYAN}Next Steps:${NC}\n"

echo -e "${YELLOW}Option 1 - Start Everything (Recommended):${NC}"
echo -e "  ${BLUE}./start-all.sh${NC}     (Mac/Linux)"
echo -e "  ${BLUE}start-all.bat${NC}      (Windows)\n"

echo -e "${YELLOW}Option 2 - Start Separately:${NC}"
echo -e "  Terminal 1:"
echo -e "    ${BLUE}./start-backend.sh${NC}  (Mac/Linux)"
echo -e "    ${BLUE}start-backend.bat${NC}   (Windows)"
echo -e ""
echo -e "  Terminal 2:"
echo -e "    ${BLUE}./start-frontend.sh${NC} (Mac/Linux)"
echo -e "    ${BLUE}start-frontend.bat${NC}  (Windows)\n"

echo -e "${CYAN}Access Points:${NC}"
echo -e "  ${GREEN}Frontend:${NC}    http://localhost:4200"
echo -e "  ${GREEN}Backend API:${NC} http://localhost:5000\n"

echo -e "${CYAN}Useful Commands:${NC}"
echo -e "  ${BLUE}cd backend && source venv/bin/activate${NC}  - Activate Python environment"
echo -e "  ${BLUE}cd frontend && ng serve${NC}                  - Start Angular dev server"
echo -e "  ${BLUE}cd frontend && ng build --prod${NC}           - Build for production\n"

echo -e "${PURPLE}╔════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║${NC}  ${GREEN}Setup Complete! Run ./start-all.sh to begin${NC}                    ${PURPLE}║${NC}"
echo -e "${PURPLE}╚════════════════════════════════════════════════════════════════════╝${NC}\n"

# Create a setup complete flag
touch .setup_complete

print_success "Setup script finished successfully!"