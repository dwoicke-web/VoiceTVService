#!/bin/bash

echo "🚀 Starting VoiceTV Service..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${BLUE}▶ Starting Flask backend on port 5001...${NC}"
cd "$DIR/backend"
source "../venv/bin/activate"
python app.py &
FLASK_PID=$!
sleep 2

echo -e "${GREEN}✓ Flask backend started (PID: $FLASK_PID)${NC}"
echo ""

echo -e "${BLUE}▶ Starting React frontend on port 3000...${NC}"
cd "$DIR/frontend"
npm start &
REACT_PID=$!

echo -e "${GREEN}✓ React frontend started (PID: $REACT_PID)${NC}"
echo ""

echo -e "${GREEN}================================================================${NC}"
echo -e "${GREEN}🎬 VoiceTV Service is running!${NC}"
echo -e "${GREEN}================================================================${NC}"
echo ""
echo "📱 Frontend:  http://localhost:3000"
echo "🔌 Backend:   http://localhost:5001"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for all background jobs
wait
