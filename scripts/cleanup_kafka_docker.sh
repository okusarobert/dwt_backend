#!/bin/bash

# Docker Kafka Cleanup Script
# This script works directly with Kafka without needing kubectl

set -e

# Configuration
KAFKA_HOST=${KAFKA_HOST:-"kafka"}
KAFKA_PORT=${KAFKA_PORT:-"9092"}
CONSUMER_GROUP=${CONSUMER_GROUP:-"wallet-merged-consumer"}
BOOTSTRAP_SERVER="${KAFKA_HOST}:${KAFKA_PORT}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🐳 Docker Kafka Cleanup Script${NC}"
echo "=================================="
echo "Kafka Server: $BOOTSTRAP_SERVER"
echo "Consumer Group: $CONSUMER_GROUP"
echo ""

# Function to check if Kafka tools are available
check_kafka_tools() {
    if ! command -v kafka-consumer-groups &> /dev/null; then
        echo -e "${RED}❌ kafka-consumer-groups not found${NC}"
        echo "You need to install Kafka command-line tools or run this from a Kafka container."
        echo "Try: docker exec -it <kafka-container> bash"
        exit 1
    fi
    
    if ! command -v kafka-topics &> /dev/null; then
        echo -e "${RED}❌ kafka-topics not found${NC}"
        echo "You need to install Kafka command-line tools or run this from a Kafka container."
        exit 1
    fi
}

# Function to check Kafka connection
check_kafka_connection() {
    echo -e "${YELLOW}📡 Checking Kafka connection...${NC}"
    
    if kafka-consumer-groups --bootstrap-server "$BOOTSTRAP_SERVER" --list &>/dev/null; then
        echo -e "${GREEN}✅ Successfully connected to Kafka at $BOOTSTRAP_SERVER${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to connect to Kafka at $BOOTSTRAP_SERVER${NC}"
        echo "Make sure:"
        echo "1. Kafka is running"
        echo "2. You're in the same Docker network"
        echo "3. Kafka hostname is correct"
        return 1
    fi
}

# Function to list topics
list_topics() {
    echo -e "${YELLOW}📋 Listing Kafka topics...${NC}"
    
    kafka-topics --bootstrap-server "$BOOTSTRAP_SERVER" --list
}

# Function to list consumer groups
list_consumer_groups() {
    echo -e "${YELLOW}📋 Listing consumer groups...${NC}"
    
    kafka-consumer-groups --bootstrap-server "$BOOTSTRAP_SERVER" --list
}

# Function to describe consumer group
describe_consumer_group() {
    local group=$1
    
    echo -e "${YELLOW}📋 Describing consumer group: $group${NC}"
    
    kafka-consumer-groups --bootstrap-server "$BOOTSTRAP_SERVER" --describe --group "$group"
}

# Function to reset consumer group offsets
reset_consumer_group() {
    local group=$1
    local offset_type=$2
    
    echo -e "${YELLOW}🔄 Resetting consumer group $group to $offset_type offset...${NC}"
    
    kafka-consumer-groups --bootstrap-server "$BOOTSTRAP_SERVER" \
        --group "$group" \
        --reset-offsets \
        --to-$offset_type \
        --execute
}

# Function to delete consumer group
delete_consumer_group() {
    local group=$1
    
    echo -e "${YELLOW}🗑️  Deleting consumer group: $group${NC}"
    
    kafka-consumer-groups --bootstrap-server "$BOOTSTRAP_SERVER" \
        --delete \
        --group "$group"
}

# Function to show help
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -g, --group GROUP       Consumer group name (default: wallet-merged-consumer)"
    echo "  -s, --strategy STRATEGY Cleanup strategy: earliest, latest, delete (default: earliest)"
    echo "  -H, --host HOST         Kafka host (default: kafka)"
    echo "  -p, --port PORT         Kafka port (default: 9092)"
    echo "  --status                Show status only (no changes)"
    echo ""
    echo "Strategies:"
    echo "  earliest                Reset to earliest offset (reprocess all messages)"
    echo "  latest                  Reset to latest offset (skip all pending messages)"
    echo "  delete                  Delete the consumer group entirely"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Reset to earliest offset"
    echo "  $0 -s latest                          # Reset to latest offset"
    echo "  $0 -s delete                          # Delete consumer group"
    echo "  $0 --status                           # Show status only"
    echo ""
}

# Parse command line arguments
STRATEGY="earliest"
SHOW_STATUS_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -g|--group)
            CONSUMER_GROUP="$2"
            shift 2
            ;;
        -s|--strategy)
            STRATEGY="$2"
            shift 2
            ;;
        -H|--host)
            KAFKA_HOST="$2"
            BOOTSTRAP_SERVER="${KAFKA_HOST}:${KAFKA_PORT}"
            shift 2
            ;;
        -p|--port)
            KAFKA_PORT="$2"
            BOOTSTRAP_SERVER="${KAFKA_HOST}:${KAFKA_PORT}"
            shift 2
            ;;
        --status)
            SHOW_STATUS_ONLY=true
            shift
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Main execution
main() {
    echo -e "${BLUE}🚀 Starting Docker Kafka cleanup...${NC}"
    
    # Check prerequisites
    check_kafka_tools
    check_kafka_connection
    
    if [ "$SHOW_STATUS_ONLY" = true ]; then
        # Show status only
        echo ""
        list_topics
        echo ""
        list_consumer_groups
        echo ""
        describe_consumer_group "$CONSUMER_GROUP"
        exit 0
    fi
    
    # Perform cleanup
    case $STRATEGY in
        "earliest")
            echo -e "${YELLOW}🔄 Strategy: Reset to earliest offset (reprocess all messages)${NC}"
            reset_consumer_group "$CONSUMER_GROUP" "earliest"
            ;;
        "latest")
            echo -e "${YELLOW}🔄 Strategy: Reset to latest offset (skip all pending messages)${NC}"
            reset_consumer_group "$CONSUMER_GROUP" "latest"
            ;;
        "delete")
            echo -e "${YELLOW}⚠️  WARNING: This will delete the consumer group $CONSUMER_GROUP${NC}"
            read -p "Are you sure? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                delete_consumer_group "$CONSUMER_GROUP"
            else
                echo -e "${YELLOW}❌ Operation cancelled${NC}"
                exit 0
            fi
            ;;
        *)
            echo -e "${RED}❌ Unknown strategy: $STRATEGY${NC}"
            echo "Valid strategies: earliest, latest, delete"
            exit 1
            ;;
    esac
    
    echo ""
    echo -e "${GREEN}🎉 Cleanup completed successfully!${NC}"
    echo ""
    
    # Show updated status
    describe_consumer_group "$CONSUMER_GROUP"
}

# Run main function
main "$@"
