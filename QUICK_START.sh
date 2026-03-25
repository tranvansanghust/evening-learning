#!/bin/bash

# Quick Start Script for Evening Learning Backend
# This script automates initial setup steps

set -e

echo "🚀 Evening Learning - Quick Start Setup"
echo "======================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Check Python
echo -e "\n${YELLOW}Step 1: Checking Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 not found. Please install Python 3.9+${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo -e "${GREEN}✅ Python ${PYTHON_VERSION} found${NC}"

# Step 2: Check MySQL
echo -e "\n${YELLOW}Step 2: Checking MySQL...${NC}"
if ! command -v mysql &> /dev/null; then
    echo -e "${RED}❌ MySQL not found. Please install MySQL 8.0+${NC}"
    echo "    Mac: brew install mysql"
    echo "    Linux: sudo apt install mysql-server"
    exit 1
fi
echo -e "${GREEN}✅ MySQL found${NC}"

# Step 3: Create virtual environment
echo -e "\n${YELLOW}Step 3: Creating virtual environment...${NC}"
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
else
    echo -e "${GREEN}✅ Virtual environment already exists${NC}"
fi

# Step 4: Activate venv and install dependencies
echo -e "\n${YELLOW}Step 4: Installing dependencies...${NC}"
source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
echo -e "${GREEN}✅ Dependencies installed${NC}"

# Step 5: Check .env
echo -e "\n${YELLOW}Step 5: Checking .env file...${NC}"
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}⚠️  .env created from template - UPDATE WITH YOUR VALUES!${NC}"
        echo -e "${YELLOW}   Edit backend/.env with your database and Telegram credentials${NC}"
    else
        echo -e "${RED}❌ No .env file found${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ .env file exists${NC}"
fi

# Step 6: Verify .env has values
echo -e "\n${YELLOW}Step 6: Checking .env configuration...${NC}"
if grep -q "your_password_here\|your_bot_token_here\|your_anthropic_api_key" .env; then
    echo -e "${RED}⚠️  WARNING: .env has placeholder values${NC}"
    echo -e "${YELLOW}   Please update the following in backend/.env:${NC}"
    echo "   - DB_PASSWORD (from MySQL setup)"
    echo "   - TELEGRAM_BOT_TOKEN (from @BotFather)"
    echo "   - ANTHROPIC_API_KEY (from console.anthropic.com)"
else
    echo -e "${GREEN}✅ .env appears to be configured${NC}"
fi

# Step 7: Test imports
echo -e "\n${YELLOW}Step 7: Testing imports...${NC}"
python -c "from app.database import Base; from app.models import *; print('✅ Imports successful')" 2>/dev/null || {
    echo -e "${RED}❌ Import failed - check your setup${NC}"
    exit 1
}

echo -e "\n${GREEN}=======================================${NC}"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo -e "${GREEN}=======================================${NC}"

echo -e "\n${YELLOW}Next steps:${NC}"
echo ""
echo "1️⃣  UPDATE .env file with your credentials:"
echo "   nano backend/.env"
echo ""
echo "2️⃣  CREATE MySQL database:"
echo "   mysql -u root -p < docs/setup.sql"
echo ""
echo "3️⃣  START FastAPI server (Terminal 1):"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   uvicorn app.main:app --reload"
echo ""
echo "4️⃣  START Telegram bot (Terminal 2):"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   python app/bot_polling.py"
echo ""
echo "5️⃣  TEST in Telegram:"
echo "   Find your bot and send: /start"
echo ""
echo "📖 Full guide: See TESTING_GUIDE.md"
echo ""
