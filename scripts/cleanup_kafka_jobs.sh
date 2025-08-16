#!/bin/bash

# Kafka Job Cleanup Script
# This script helps clean up unfinished Kafka jobs by resetting consumer group offsets

set -e

# Configuration
KAFKA_BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS:-"localhost:9092"}
CONSUMER_GROUP=${CONSUMER_GROUP:-"wallet-consumer-group"}
NAMESPACE=${NAMESPACE:-"tondeka-app"}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 Kafka Job Cleanup Script${NC}"
echo "=================================="
echo "Bootstrap Servers: $KAFKA_BOOTSTRAP_SERVERS"
echo "Consumer Group: $CONSUMER_GROUP"
echo "Namespace: $NAMESPACE"
echo ""

# Function to check if kubectl is available
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        echo -e "${RED}❌ kubectl is not installed or not in PATH${NC}"
        exit 1
    fi
}

# Function to check if Kafka pod is running
check_kafka_pod() {
    echo -e "${YELLOW}📋 Checking Kafka pod status...${NC}"
    
    if kubectl get pods -n $NAMESPACE -l app=kafka | grep -q Running; then
        echo -e "${GREEN}✅ Kafka pod is running${NC}"
    else
        echo -e "${RED}❌ Kafka pod is not running in namespace $NAMESPACE${NC}"
        echo "Available pods:"
        kubectl get pods -n $NAMESPACE
        exit 1
    fi
}

# Function to get Kafka pod name
get_kafka_pod() {
    kubectl get pods -n $NAMESPACE -l app=kafka -o jsonpath='{.items[0].metadata.name}'
}

# Function to list topics
list_topics() {
    local pod_name=$1
    echo -e "${YELLOW}📋 Listing Kafka topics...${NC}"
    
    kubectl exec -n $NAMESPACE $pod_name -- kafka-topics.sh \
        --bootstrap-server localhost:9092 \
        --list
}

# Function to describe topics
describe_topics() {
    local pod_name=$1
    local topics=("wallet-credit-requests" "user.registered" "wallet-deposit-requests" "wallet-withdraw-requests")
    
    echo -e "${YELLOW}📋 Describing topics...${NC}"
    
    for topic in "${topics[@]}"; do
        echo -e "${BLUE}Topic: $topic${NC}"
        kubectl exec -n $NAMESPACE $pod_name -- kafka-topics.sh \
            --bootstrap-server localhost:9092 \
            --describe \
            --topic "$topic" || echo "Topic $topic not found"
        echo ""
    done
}

# Function to list consumer groups
list_consumer_groups() {
    local pod_name=$1
    echo -e "${YELLOW}📋 Listing consumer groups...${NC}"
    
    kubectl exec -n $NAMESPACE $pod_name -- kafka-consumer-groups.sh \
        --bootstrap-server localhost:9092 \
        --list
}

# Function to describe consumer group
describe_consumer_group() {
    local pod_name=$1
    local group=$2
    
    echo -e "${YELLOW}📋 Describing consumer group: $group${NC}"
    
    kubectl exec -n $NAMESPACE $pod_name -- kafka-consumer-groups.sh \
        --bootstrap-server localhost:9092 \
        --describe \
        --group "$group" || echo "Consumer group $group not found"
}

# Function to reset consumer group offsets
reset_consumer_group() {
    local pod_name=$1
    local group=$2
    local topic=$3
    local offset_type=${4:-"earliest"}
    
    echo -e "${YELLOW}🔄 Resetting consumer group $group for topic $topic to $offset_type...${NC}"
    
    kubectl exec -n $NAMESPACE $pod_name -- kafka-consumer-groups.sh \
        --bootstrap-server localhost:9092 \
        --group "$group" \
        --topic "$topic" \
        --reset-offsets \
        --to-$offset_type \
        --execute
}

# Function to reset all topics for consumer group
reset_all_topics() {
    local pod_name=$1
    local group=$2
    local offset_type=${3:-"earliest"}
    
    local topics=("wallet-credit-requests" "user.registered" "wallet-deposit-requests" "wallet-withdraw-requests")
    
    echo -e "${YELLOW}🔄 Resetting all topics for consumer group $group to $offset_type...${NC}"
    
    for topic in "${topics[@]}"; do
        echo -e "${BLUE}Resetting topic: $topic${NC}"
        reset_consumer_group "$pod_name" "$group" "$topic" "$offset_type"
        echo ""
    done
}

# Function to show current offsets
show_current_offsets() {
    local pod_name=$1
    local group=$2
    
    echo -e "${YELLOW}📊 Current offsets for consumer group: $group${NC}"
    
    kubectl exec -n $NAMESPACE $pod_name -- kafka-consumer-groups.sh \
        --bootstrap-server localhost:9092 \
        --describe \
        --group "$group" | grep -E "(TOPIC|PARTITION|CURRENT-OFFSET|LOG-END-OFFSET|LAG)"
}

# Function to delete consumer group
delete_consumer_group() {
    local pod_name=$1
    local group=$2
    
    echo -e "${YELLOW}🗑️  Deleting consumer group: $group${NC}"
    
    kubectl exec -n $NAMESPACE $pod_name -- kafka-consumer-groups.sh \
        --bootstrap-server localhost:9092 \
        --delete \
        --group "$group"
}

# Function to show help
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -g, --group GROUP       Consumer group name (default: wallet-consumer-group)"
    echo "  -n, --namespace NS      Kubernetes namespace (default: tondeka-app)"
    echo "  -o, --offset OFFSET     Offset type: earliest, latest, or specific (default: earliest)"
    echo "  -t, --topic TOPIC       Specific topic to reset (default: all topics)"
    echo "  -d, --delete            Delete the consumer group instead of resetting"
    echo "  -s, --status            Show current status only (no changes)"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Reset all topics to earliest offset"
    echo "  $0 -o latest                          # Reset all topics to latest offset"
    echo "  $0 -t wallet-credit-requests          # Reset only credit requests topic"
    echo "  $0 -d                                 # Delete the consumer group"
    echo "  $0 -s                                 # Show status only"
    echo ""
}

# Parse command line arguments
TOPIC=""
OFFSET_TYPE="earliest"
DELETE_GROUP=false
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
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -o|--offset)
            OFFSET_TYPE="$2"
            shift 2
            ;;
        -t|--topic)
            TOPIC="$2"
            shift 2
            ;;
        -d|--delete)
            DELETE_GROUP=true
            shift
            ;;
        -s|--status)
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
    echo -e "${BLUE}🚀 Starting Kafka cleanup process...${NC}"
    
    # Check prerequisites
    check_kubectl
    check_kafka_pod
    
    # Get Kafka pod name
    local pod_name=$(get_kafka_pod)
    echo -e "${GREEN}✅ Using Kafka pod: $pod_name${NC}"
    echo ""
    
    if [ "$SHOW_STATUS_ONLY" = true ]; then
        # Show status only
        list_topics "$pod_name"
        echo ""
        list_consumer_groups "$pod_name"
        echo ""
        describe_consumer_group "$pod_name" "$CONSUMER_GROUP"
        echo ""
        show_current_offsets "$pod_name" "$CONSUMER_GROUP"
        exit 0
    fi
    
    if [ "$DELETE_GROUP" = true ]; then
        # Delete consumer group
        echo -e "${YELLOW}⚠️  WARNING: This will delete the consumer group $CONSUMER_GROUP${NC}"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            delete_consumer_group "$pod_name" "$CONSUMER_GROUP"
            echo -e "${GREEN}✅ Consumer group $CONSUMER_GROUP deleted${NC}"
        else
            echo -e "${YELLOW}❌ Operation cancelled${NC}"
            exit 0
        fi
    else
        # Reset consumer group
        if [ -n "$TOPIC" ]; then
            # Reset specific topic
            echo -e "${YELLOW}🔄 Resetting specific topic: $TOPIC${NC}"
            reset_consumer_group "$pod_name" "$CONSUMER_GROUP" "$TOPIC" "$OFFSET_TYPE"
        else
            # Reset all topics
            echo -e "${YELLOW}🔄 Resetting all topics${NC}"
            reset_all_topics "$pod_name" "$CONSUMER_GROUP" "$OFFSET_TYPE"
        fi
        
        echo -e "${GREEN}✅ Consumer group reset completed${NC}"
        echo ""
        
        # Show new offsets
        show_current_offsets "$pod_name" "$CONSUMER_GROUP"
    fi
    
    echo ""
    echo -e "${GREEN}🎉 Kafka cleanup completed successfully!${NC}"
}

# Run main function
main "$@"
