#!/bin/bash

echo "🔍 HKSS Translation Service Monitor"
echo "====================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "📊 Checking Services Status..."
echo ""

# Check SvelteKit
if pgrep -f "vite.*dev" > /dev/null; then
    echo -e "${GREEN}✅ SvelteKit: RUNNING${NC}"
    SK_PORT=$(lsof -i -P | grep vite | grep LISTEN | awk '{print $9}' | head -1)
    echo -e "   Port: ${SK_PORT}"
else
    echo -e "${RED}❌ SvelteKit: NOT RUNNING${NC}"
fi

# Check Python Service
if pgrep -f "python.*translation_service" > /dev/null; then
    echo -e "${GREEN}✅ Python Translation Service: RUNNING${NC}"
else
    echo -e "${RED}❌ Python Translation Service: NOT RUNNING${NC}"
fi

# Check Database
if pgrep -f "postgres.*local" > /dev/null || docker ps | grep -q "hkss-db"; then
    echo -e "${GREEN}✅ Database: RUNNING${NC}"
else
    echo -e "${RED}❌ Database: NOT RUNNING${NC}"
fi

echo ""
echo "📋 Recent Tasks Status:"
echo "======================"

# Check recent tasks
psql "postgresql://root:mysecretpassword@localhost:5432/local" -c "
SELECT
    task_id as id,
    status,
    source_type as type,
    CASE
        WHEN status = 'pending' THEN '⏳ Waiting for processing'
        WHEN status = 'pending_python_processing' THEN '🐍 Python processing...'
        WHEN status = 'processing' THEN '⚙️ Processing...'
        WHEN status = 'completed' THEN '✅ Completed'
        WHEN status = 'failed' THEN '❌ Failed'
        ELSE status
    END as status_text,
    created_at as created
FROM translation_task
ORDER BY created_at DESC
LIMIT 10;" 2>/dev/null | while read line; do
    echo "   $line"
done

echo ""
echo "📁 Recent Files:"
find uploads -name "*.docx" -type f -mtime -1 | head -5 | sed 's/^/   /'

echo ""
echo "📜 Live Logs (Ctrl+C to stop):"
echo "=============================="
echo ""

# Function to show logs
show_logs() {
    echo -e "${BLUE}=== SVELTEKIT LOGS ===${NC}"
    if [ -f dev_new.log ]; then
        tail -10 dev_new.log | sed 's/^/   /'
    fi

    echo ""
    echo -e "${BLUE}=== PYTHON SERVICE LOGS ===${NC}"
    if [ -f python_service.log ]; then
        tail -10 python_service.log | sed 's/^/   /'
    fi
}

# Show initial logs
show_logs

# Monitor for changes
echo ""
echo "🔄 Monitoring for changes... (Press Ctrl+C to exit)"
echo ""

while true; do
    sleep 5
    echo -e "${YELLOW}--- $(date '+%H:%M:%S') ---${NC}"
    show_logs
    echo ""
done