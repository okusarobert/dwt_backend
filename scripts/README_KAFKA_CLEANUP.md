# 🧹 Kafka Job Cleanup Guide

This guide provides comprehensive instructions for cleaning up unfinished Kafka jobs in the DWT Backend system.

## 📋 **Overview**

The DWT Backend system uses Kafka for asynchronous job processing across several services:

- **`wallet-credit-requests`** - Credit requests for wallet operations
- **`user.registered`** - User registration notifications  
- **`wallet-deposit-requests`** - Wallet deposit requests
- **`wallet-withdraw-requests`** - Wallet withdrawal requests

## 🚀 **Quick Start**

### **1. Check Current Status**

```bash
# Show status only (no changes)
./scripts/cleanup_kafka_jobs.py -g wallet-consumer-group --status-only

# Or use the shell script
./scripts/cleanup_kafka_jobs.sh -s
```

### **2. Clean Up All Unfinished Jobs**

```bash
# Reset to earliest offset (reprocess all messages)
./scripts/cleanup_kafka_jobs.py -g wallet-consumer-group -s reset_earliest

# Or use the shell script
./scripts/cleanup_kafka_jobs.sh
```

### **3. Skip All Pending Messages**

```bash
# Reset to latest offset (skip all pending messages)
./scripts/cleanup_kafka_jobs.py -g wallet-consumer-group -s reset_latest

# Or use the shell script
./scripts/cleanup_kafka_jobs.sh -o latest
```

## 🛠️ **Available Scripts**

### **Python Script (`cleanup_kafka_jobs.py`)**

More feature-rich with programmatic control:

```bash
# Basic usage
./scripts/cleanup_kafka_jobs.py -g <consumer-group> -s <strategy>

# Options
-g, --group GROUP          Consumer group name (required)
-s, --strategy STRATEGY    Cleanup strategy (default: reset_earliest)
-n, --namespace NS         Kubernetes namespace (default: tondeka-app)
--status-only              Show status only, no cleanup
--topic TOPIC              Specific topic to reset
--verbose, -v              Verbose logging

# Strategies
reset_earliest             Reset to earliest offset (reprocess all)
reset_latest               Reset to latest offset (skip all pending)
delete_group               Delete the consumer group entirely
```

### **Shell Script (`cleanup_kafka_jobs.sh`)**

Simpler, more traditional approach:

```bash
# Basic usage
./scripts/cleanup_kafka_jobs.sh [OPTIONS]

# Options
-h, --help                 Show help message
-g, --group GROUP          Consumer group name
-n, --namespace NS         Kubernetes namespace
-o, --offset OFFSET        Offset type: earliest, latest
-t, --topic TOPIC          Specific topic to reset
-d, --delete               Delete consumer group
-s, --status               Show status only
```

## 🎯 **Cleanup Strategies**

### **1. Reset to Earliest (`reset_earliest`)**

- **What it does**: Moves consumer group to the beginning of all topics
- **Effect**: All messages will be reprocessed from the start
- **Use case**: When you want to reprocess all messages (e.g., after fixing a bug)
- **Risk**: May cause duplicate processing

```bash
./scripts/cleanup_kafka_jobs.py -g wallet-consumer-group -s reset_earliest
```

### **2. Reset to Latest (`reset_latest`)**

- **What it does**: Moves consumer group to the end of all topics
- **Effect**: All pending messages are skipped
- **Use case**: When you want to skip old messages and start fresh
- **Risk**: Messages may be lost permanently

```bash
./scripts/cleanup_kafka_jobs.py -g wallet-consumer-group -s reset_latest
```

### **3. Delete Consumer Group (`delete_group`)**

- **What it does**: Completely removes the consumer group
- **Effect**: Group will be recreated on next service restart
- **Use case**: When you want a completely fresh start
- **Risk**: All offset information is lost

```bash
./scripts/cleanup_kafka_jobs.py -g wallet-consumer-group -s delete_group
```

## 📊 **Monitoring and Status**

### **Check Consumer Group Status**

```bash
# Show detailed status for a specific group
./scripts/cleanup_kafka_jobs.py -g wallet-consumer-group --status-only

# Show status for all groups
./scripts/cleanup_kafka_jobs.py -g wallet-consumer-group --status-only
```

### **Key Metrics to Monitor**

- **Current Offset**: Where the consumer is currently reading
- **Log End Offset**: Latest message available in the topic
- **Lag**: Number of unprocessed messages
- **Members**: Number of active consumers in the group

### **Example Output**

```
📊 Consumer Group: wallet-consumer-group
  Members: 1
  Total Lag: 150
  Topic Details:
    wallet-credit-requests:0 - Current: 1000, End: 1150, Lag: 150
    user.registered:0 - Current: 500, End: 500, Lag: 0
    wallet-deposit-requests:0 - Current: 750, End: 800, Lag: 50
```

## 🔧 **Troubleshooting**

### **Common Issues**

#### **1. "kubectl not found"**
```bash
# Install kubectl or ensure it's in PATH
# For macOS:
brew install kubectl

# For Linux:
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
```

#### **2. "No Kafka pods found"**
```bash
# Check if Kafka is running
kubectl get pods -n tondeka-app -l app=kafka

# Check namespace
kubectl get namespaces | grep tondeka-app
```

#### **3. "Consumer group not found"**
```bash
# List all consumer groups
kubectl exec -n tondeka-app <kafka-pod> -- kafka-consumer-groups.sh --bootstrap-server localhost:9092 --list

# Check if your service is actually consuming
kubectl logs -n tondeka-app <wallet-pod> | grep "Started merged Kafka consumer"
```

#### **4. "Permission denied"**
```bash
# Ensure you have access to the namespace
kubectl auth can-i get pods -n tondeka-app

# Check your kubeconfig
kubectl config current-context
```

### **Manual Kafka Commands**

If the scripts fail, you can run Kafka commands manually:

```bash
# Get Kafka pod name
KAFKA_POD=$(kubectl get pods -n tondeka-app -l app=kafka -o jsonpath='{.items[0].metadata.name}')

# List topics
kubectl exec -n tondeka-app $KAFKA_POD -- kafka-topics.sh --bootstrap-server localhost:9092 --list

# List consumer groups
kubectl exec -n tondeka-app $KAFKA_POD -- kafka-consumer-groups.sh --bootstrap-server localhost:9092 --list

# Describe consumer group
kubectl exec -n tondeka-app $KAFKA_POD -- kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group wallet-consumer-group

# Reset offsets
kubectl exec -n tondeka-app $KAFKA_POD -- kafka-consumer-groups.sh --bootstrap-server localhost:9092 --group wallet-consumer-group --reset-offsets --to-earliest --execute
```

## 🚨 **Safety Considerations**

### **Before Running Cleanup**

1. **Backup**: Ensure you have backups of critical data
2. **Service Status**: Check if services are running and healthy
3. **Impact Assessment**: Understand what messages will be affected
4. **Monitoring**: Have monitoring in place to detect issues

### **After Running Cleanup**

1. **Verify**: Check that consumer groups are in expected state
2. **Monitor**: Watch for any errors or unexpected behavior
3. **Test**: Verify that new messages are being processed correctly
4. **Document**: Record what cleanup was performed and when

## 📝 **Best Practices**

### **1. Regular Monitoring**

```bash
# Set up a cron job to check status daily
0 9 * * * /path/to/dwt_backend/scripts/cleanup_kafka_jobs.py -g wallet-consumer-group --status-only >> /var/log/kafka-status.log
```

### **2. Gradual Cleanup**

```bash
# Clean up one topic at a time to minimize impact
./scripts/cleanup_kafka_jobs.py -g wallet-consumer-group --topic wallet-credit-requests -s reset_earliest
```

### **3. Document Cleanup Operations**

Keep a log of all cleanup operations:
- Date and time
- Consumer group affected
- Strategy used
- Reason for cleanup
- Results and any issues

### **4. Test in Development First**

Always test cleanup operations in a development environment before running in production.

## 🔄 **Automated Cleanup**

### **Scheduled Cleanup Script**

Create a cron job for automatic cleanup:

```bash
# Clean up lagging consumer groups daily at 2 AM
0 2 * * * /path/to/dwt_backend/scripts/cleanup_kafka_jobs.py -g wallet-consumer-group -s reset_latest --verbose >> /var/log/kafka-cleanup.log 2>&1
```

### **Conditional Cleanup**

Only clean up when lag exceeds a threshold:

```bash
#!/bin/bash
LAG_THRESHOLD=1000

# Check lag and clean up if necessary
LAG=$(./scripts/cleanup_kafka_jobs.py -g wallet-consumer-group --status-only | grep "Total Lag" | awk '{print $3}')

if [ "$LAG" -gt "$LAG_THRESHOLD" ]; then
    echo "High lag detected ($LAG), cleaning up..."
    ./scripts/cleanup_kafka_jobs.py -g wallet-consumer-group -s reset_latest
fi
```

## 📚 **Additional Resources**

- [Kafka Consumer Group Management](https://kafka.apache.org/documentation/#consumerconfigs)
- [Kafka Offset Management](https://kafka.apache.org/documentation/#consumerconfigs)
- [Bitnami Kafka Helm Chart](https://github.com/bitnami/charts/tree/main/bitnami/kafka)

## 🆘 **Getting Help**

If you encounter issues:

1. Check the troubleshooting section above
2. Review the script logs and error messages
3. Verify your Kubernetes and Kafka setup
4. Check the DWT Backend service logs for related errors

---

**⚠️  Warning**: Always test cleanup operations in a development environment first. Cleanup operations can result in data loss or duplicate processing.
