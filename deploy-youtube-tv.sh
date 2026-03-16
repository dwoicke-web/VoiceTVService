#!/bin/bash

###############################################################################
# VoiceTV Service - YouTube TV Integration Deployment Script
#
# This script automates the deployment of YouTube TV integration to production
#
# Usage: ./deploy-youtube-tv.sh [API_KEY]
#        ./deploy-youtube-tv.sh AIzaSyA3tHHwRL3buxDfitygN4yOB7JY8hxcIo4
#
# Or run interactively:
#        ./deploy-youtube-tv.sh
###############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
VENV_PATH="$SCRIPT_DIR/venv"
BACKEND_DIR="$SCRIPT_DIR/backend"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          VoiceTV YouTube TV Integration Deployer               ║${NC}"
echo -e "${BLUE}║                     v1.0.0 Production                          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to print status
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Function to validate API key format
validate_api_key() {
    local key=$1
    if [[ $key =~ ^AIzaSy[A-Za-z0-9_-]{35}$ ]]; then
        return 0
    else
        return 1
    fi
}

# Step 1: Check prerequisites
echo -e "${BLUE}Step 1: Checking Prerequisites${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    print_status "Python 3 found: $PYTHON_VERSION"
else
    print_error "Python 3 not found. Please install Python 3.11+"
    exit 1
fi

# Check virtual environment
if [ -d "$VENV_PATH" ]; then
    print_status "Virtual environment found"
else
    print_error "Virtual environment not found at $VENV_PATH"
    exit 1
fi

# Check Flask
if $VENV_PATH/bin/pip show Flask &> /dev/null; then
    FLASK_VERSION=$($VENV_PATH/bin/pip show Flask | grep Version | awk '{print $2}')
    print_status "Flask found: $FLASK_VERSION"
else
    print_error "Flask not found in virtual environment"
    exit 1
fi

echo ""

# Step 2: Get API Key
echo -e "${BLUE}Step 2: Configure YouTube TV API Key${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

YOUTUBE_TV_API_KEY=""

# Check if API key provided as argument
if [ -n "$1" ]; then
    YOUTUBE_TV_API_KEY="$1"
    print_info "API key provided as argument"
else
    # Prompt for API key
    print_info "Enter your YouTube TV API key (from Google Cloud Console)"
    print_info "Format: AIzaSy... (39 characters)"
    echo ""
    read -sp "YouTube TV API Key: " YOUTUBE_TV_API_KEY
    echo ""
fi

# Validate API key format
if validate_api_key "$YOUTUBE_TV_API_KEY"; then
    print_status "API key format is valid"
else
    print_warning "API key format doesn't match expected pattern"
    print_info "Expected format: AIzaSy... (39 characters)"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_error "Deployment cancelled"
        exit 1
    fi
fi

echo ""

# Step 3: Install Dependencies
echo -e "${BLUE}Step 3: Installing Dependencies${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

print_info "Installing aiohttp..."
if $VENV_PATH/bin/pip install aiohttp -q; then
    print_status "aiohttp installed successfully"
else
    print_error "Failed to install aiohttp"
    exit 1
fi

print_info "Verifying python-dotenv..."
if $VENV_PATH/bin/pip show python-dotenv &> /dev/null; then
    print_status "python-dotenv already installed"
else
    print_info "Installing python-dotenv..."
    if $VENV_PATH/bin/pip install python-dotenv -q; then
        print_status "python-dotenv installed successfully"
    fi
fi

echo ""

# Step 4: Update .env file
echo -e "${BLUE}Step 4: Updating Configuration${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if .env exists
if [ ! -f "$ENV_FILE" ]; then
    print_warning ".env file not found, creating from .env.example"
    if [ -f "$ENV_FILE.example" ]; then
        cp "$ENV_FILE.example" "$ENV_FILE"
        print_status ".env file created from template"
    else
        print_error ".env.example not found"
        exit 1
    fi
fi

# Update or add YOUTUBE_TV_API_KEY
if grep -q "^YOUTUBE_TV_API_KEY=" "$ENV_FILE"; then
    # Key exists, update it
    sed -i "s|^YOUTUBE_TV_API_KEY=.*|YOUTUBE_TV_API_KEY=$YOUTUBE_TV_API_KEY|" "$ENV_FILE"
    print_status "Updated YOUTUBE_TV_API_KEY in .env"
else
    # Key doesn't exist, add it
    echo "" >> "$ENV_FILE"
    echo "# YouTube TV Integration (Added at deployment)" >> "$ENV_FILE"
    echo "YOUTUBE_TV_API_KEY=$YOUTUBE_TV_API_KEY" >> "$ENV_FILE"
    print_status "Added YOUTUBE_TV_API_KEY to .env"
fi

echo ""

# Step 5: Stop existing Flask instance
echo -e "${BLUE}Step 5: Restarting Flask Service${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

print_info "Stopping existing Flask instances..."
pkill -f "python app.py" 2>/dev/null || true
sleep 2
print_status "Flask stopped"

# Step 6: Start Flask
print_info "Starting Flask service..."
cd "$BACKEND_DIR"
nohup $VENV_PATH/bin/python app.py > /tmp/flask.log 2>&1 &
FLASK_PID=$!
sleep 3

# Verify Flask started
if ps -p $FLASK_PID &> /dev/null; then
    print_status "Flask started successfully (PID: $FLASK_PID)"
else
    print_error "Flask failed to start. Check /tmp/flask.log"
    tail -20 /tmp/flask.log
    exit 1
fi

echo ""

# Step 7: Run validation tests
echo -e "${BLUE}Step 6: Validating YouTube TV Integration${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

print_info "Running YouTube TV API validation tests..."
echo ""

cd "$SCRIPT_DIR"
if $VENV_PATH/bin/python test_youtube_api.py; then
    print_status "All validation tests passed!"
else
    print_warning "Some validation tests failed (see above)"
    read -p "Continue deployment anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_error "Deployment cancelled"
        exit 1
    fi
fi

echo ""

# Step 8: Deployment Complete
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ✓ Deployment Completed Successfully               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${GREEN}Summary:${NC}"
echo "  • Python: $PYTHON_VERSION"
echo "  • Flask: $FLASK_VERSION"
echo "  • aiohttp: $(($VENV_PATH/bin/pip show aiohttp 2>/dev/null | grep Version || echo 'installed') | awk '{print $2}')"
echo "  • Configuration: $ENV_FILE"
echo "  • API Key: Set (${YOUTUBE_TV_API_KEY:0:10}...)"
echo ""

echo -e "${GREEN}Next Steps:${NC}"
echo "  1. Open web UI: ${YELLOW}http://localhost:3000${NC}"
echo "  2. Search for content: ${YELLOW}breaking bad${NC}"
echo "  3. Verify YouTube results appear"
echo "  4. Select a TV and click Play"
echo "  5. Watch the TV graphic update"
echo ""

echo -e "${GREEN}Monitoring:${NC}"
echo "  • View logs: ${YELLOW}tail -f /tmp/flask.log${NC}"
echo "  • Filter YouTube: ${YELLOW}tail -f /tmp/flask.log | grep YouTube${NC}"
echo "  • Run tests: ${YELLOW}python test_youtube_api.py${NC}"
echo ""

echo -e "${GREEN}Documentation:${NC}"
echo "  • Setup guide: ${YELLOW}YOUTUBE_TV_INTEGRATION.md${NC}"
echo "  • Release notes: ${YELLOW}RELEASE_NOTES.md${NC}"
echo "  • Troubleshooting: ${YELLOW}See YOUTUBE_TV_INTEGRATION.md${NC}"
echo ""

print_status "YouTube TV Integration is now in production!"
