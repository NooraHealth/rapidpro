#!/bin/bash
# Helper script to export channel logs from DynamoDB
# This wraps the Django management command for easier use

set -e

CONTAINER="rapidpro-rapidpro-1"
OUTPUT_DIR="/tmp/channel_logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print usage
usage() {
    echo "Usage: $0 [SCENARIO] [OPTIONS]"
    echo ""
    echo "Quick Scenarios:"
    echo "  errors           - Export all error logs from today"
    echo "  slow             - Export slow requests (>5s)"
    echo "  recent           - Export last 100 logs"
    echo "  channel <UUID>   - Export logs for a specific channel"
    echo "  custom           - Use custom filters (see options below)"
    echo ""
    echo "Options for 'custom' scenario:"
    echo "  --org-id <ID>              Organization ID"
    echo "  --channel-uuid <UUID>      Channel UUID"
    echo "  --log-type <TYPE>          Log type (msg_send, msg_receive, etc.)"
    echo "  --start-date <DATE>        Start date (YYYY-MM-DD)"
    echo "  --end-date <DATE>          End date (YYYY-MM-DD)"
    echo "  --errors-only              Only error logs"
    echo "  --min-elapsed-ms <MS>      Minimum elapsed time"
    echo "  --max-elapsed-ms <MS>      Maximum elapsed time"
    echo "  --limit <N>                Maximum number of logs"
    echo "  --include-http-logs        Include HTTP details"
    echo "  --format <csv|json>        Output format"
    echo "  --output <PATH>            Output file path"
    echo ""
    echo "Examples:"
    echo "  $0 errors"
    echo "  $0 slow"
    echo "  $0 channel 12345678-1234-1234-1234-123456789abc"
    echo "  $0 custom --log-type msg_send --start-date 2025-10-01 --limit 1000"
    exit 1
}

# Check if Docker container is running
check_container() {
    if ! docker ps | grep -q "$CONTAINER"; then
        echo -e "${RED}Error: Container $CONTAINER is not running${NC}"
        echo "Start it with: docker compose up -d"
        exit 1
    fi
}

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Check for scenario argument
if [ $# -eq 0 ]; then
    usage
fi

SCENARIO=$1
shift

# Build the command based on scenario
case "$SCENARIO" in
    errors)
        echo -e "${GREEN}Exporting error logs from today...${NC}"
        TODAY=$(date +%Y-%m-%d)
        OUTPUT="$OUTPUT_DIR/errors_$(date +%Y%m%d_%H%M%S).csv"
        CMD="poetry run python manage.py export_channel_logs --output $OUTPUT --errors-only --start-date $TODAY --verbose"
        ;;
    
    slow)
        echo -e "${GREEN}Exporting slow requests (>5 seconds)...${NC}"
        OUTPUT="$OUTPUT_DIR/slow_$(date +%Y%m%d_%H%M%S).csv"
        CMD="poetry run python manage.py export_channel_logs --output $OUTPUT --min-elapsed-ms 5000 --verbose"
        ;;
    
    recent)
        echo -e "${GREEN}Exporting last 100 logs...${NC}"
        OUTPUT="$OUTPUT_DIR/recent_$(date +%Y%m%d_%H%M%S).json"
        CMD="poetry run python manage.py export_channel_logs --output $OUTPUT --limit 100 --verbose"
        ;;
    
    channel)
        if [ $# -eq 0 ]; then
            echo -e "${RED}Error: Channel UUID required${NC}"
            echo "Usage: $0 channel <UUID>"
            exit 1
        fi
        CHANNEL_UUID=$1
        shift
        echo -e "${GREEN}Exporting logs for channel $CHANNEL_UUID...${NC}"
        OUTPUT="$OUTPUT_DIR/channel_${CHANNEL_UUID}_$(date +%Y%m%d_%H%M%S).csv"
        CMD="poetry run python manage.py export_channel_logs --output $OUTPUT --channel-uuid $CHANNEL_UUID --verbose"
        ;;
    
    custom)
        echo -e "${GREEN}Exporting with custom filters...${NC}"
        OUTPUT="$OUTPUT_DIR/custom_$(date +%Y%m%d_%H%M%S).csv"
        CMD="poetry run python manage.py export_channel_logs --output $OUTPUT --verbose"
        
        # Add all passed arguments
        while [ $# -gt 0 ]; do
            CMD="$CMD $1"
            shift
        done
        ;;
    
    help|--help|-h)
        usage
        ;;
    
    *)
        echo -e "${RED}Error: Unknown scenario '$SCENARIO'${NC}"
        usage
        ;;
esac

# Run the export
echo -e "${YELLOW}Running export command...${NC}"
check_container

# Execute the command in Docker container
docker compose exec -T $CONTAINER $CMD

# Check if file was created
OUTPUT_LOCAL=$(echo "$OUTPUT" | sed 's/\/tmp\/channel_logs\///')
OUTPUT_FILE="/tmp/$OUTPUT_LOCAL"

echo ""
echo -e "${GREEN}Export complete!${NC}"
echo -e "Output file: ${YELLOW}$OUTPUT${NC}"
echo ""
echo "To copy the file to your local machine, run:"
echo -e "${YELLOW}docker compose cp $CONTAINER:$OUTPUT ./$(basename $OUTPUT)${NC}"
echo ""
echo "To analyze the file, run:"
echo -e "${YELLOW}python scripts/analyze_logs.py ./$(basename $OUTPUT)${NC}"

