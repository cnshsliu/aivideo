#!/bin/bash

echo "🚀 HKSS Development Environment Starter"
echo "========================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if a service is running
check_service() {
  if [ "$2" = "Database" ]; then
    if docker ps | grep -q "database-m4"; then
      echo -e "${GREEN}✅ $2 is running${NC}"
      return 0
    else
      echo -e "${RED}❌ $2 is not running${NC}"
      return 1
    fi
  elif pgrep -f "$1" >/dev/null; then
    echo -e "${GREEN}✅ $2 is running${NC}"
    return 0
  else
    echo -e "${RED}❌ $2 is not running${NC}"
    return 1
  fi
}

# Function to start database
start_database() {
  echo -e "${YELLOW}🗄️  Starting PostgreSQL database...${NC}"
  if ! docker ps | grep -q "database-m4"; then
    pnpm db:start >/dev/null 2>&1 &
    echo -e "${YELLOW}⏳ Waiting for database to start...${NC}"
    sleep 10
    if docker ps | grep -q "database-m4"; then
      echo -e "${GREEN}✅ Database started successfully${NC}"
    else
      echo -e "${RED}❌ Failed to start database${NC}"
      return 1
    fi
  else
    echo -e "${GREEN}✅ Database is already running${NC}"
  fi
}

# Function to start Python service
start_python_service() {
  echo -e "${YELLOW}🐍 Starting Python translation service...${NC}"
  if ! pgrep -f "python.*translation_service" >/dev/null; then
    # Check if Python dependencies are installed
    if ! pip list | grep -q "psycopg2"; then
      echo -e "${YELLOW}📦 Installing Python dependencies...${NC}"
      pip install -r requirements.txt >/dev/null 2>&1
    fi

    python start_translation_service.py >python_service.log 2>&1 &
    echo -e "${YELLOW}⏳ Waiting for Python service to start...${NC}"
    sleep 5
    if pgrep -f "python.*translation_service" >/dev/null; then
      echo -e "${GREEN}✅ Python service started successfully${NC}"
    else
      echo -e "${RED}❌ Failed to start Python service${NC}"
      return 1
    fi
  else
    echo -e "${GREEN}✅ Python service is already running${NC}"
  fi
}

# Function to start SvelteKit
start_sveltekit() {
  echo -e "${YELLOW}⚡ Starting SvelteKit development server...${NC}"
  if ! pgrep -f "vite.*dev" >/dev/null; then
    pnpm dev >dev.log 2>&1 &
    echo -e "${YELLOW}⏳ Waiting for SvelteKit to start...${NC}"
    sleep 10
    if pgrep -f "vite.*dev" >/dev/null; then
      echo -e "${GREEN}✅ SvelteKit started successfully${NC}"
    else
      echo -e "${RED}❌ Failed to start SvelteKit${NC}"
      return 1
    fi
  else
    echo -e "${GREEN}✅ SvelteKit is already running${NC}"
  fi
}

# Main startup sequence
echo ""
echo "🔍 Checking current service status..."
echo "=================================="
check_service "postgres" "Database"
check_service "python.*translation_service" "Python Translation Service"
check_service "vite.*dev" "SvelteKit"
echo ""

# Start services if they're not running
if ! check_service "postgres" "Database" >/dev/null 2>&1; then
  start_database
fi

if ! check_service "python.*translation_service" "Python Translation Service" >/dev/null 2>&1; then
  start_python_service
fi

if ! check_service "vite.*dev" "SvelteKit" >/dev/null 2>&1; then
  start_sveltekit
fi

echo ""
echo "🔍 Final status check:"
echo "====================="
check_service "postgres" "Database"
check_service "python.*translation_service" "Python Translation Service"
check_service "vite.*dev" "SvelteKit"

echo ""
echo "📋 Service URLs:"
echo "==============="
if pgrep -f "vite.*dev" >/dev/null; then
  PORT=$(lsof -i -P | grep vite | grep LISTEN | awk '{print $9}' | head -1)
  echo -e "${GREEN}🌐 SvelteKit: http://localhost:${PORT#*:}${NC}"
fi
echo -e "${GREEN}🗄️  Database: postgresql://root:mysecretpassword@localhost:5432/local${NC}"
echo ""
echo "📜 Monitor logs with:"
echo "  - SvelteKit: tail -f dev.log"
echo "  - Python: tail -f python_service.log"
echo "  - All services: ./monitor.sh"
echo ""
echo "🎉 Development environment is ready!"

