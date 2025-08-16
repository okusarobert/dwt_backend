#!/usr/bin/env python3
"""
Kafka Job Cleanup Script (Python Version)
This script provides programmatic control over Kafka consumer group cleanup operations.
"""

import os
import sys
import argparse
import json
import logging
from typing import List, Dict, Optional
import subprocess
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class KafkaCleanupManager:
    """Manages Kafka cleanup operations for consumer groups and topics."""
    
    def __init__(self, namespace: str = "tondeka-app"):
        self.namespace = namespace
        self.kafka_pod = None
        self.consumer_groups = []
        self.topics = [
            "wallet-credit-requests",
            "user.registered", 
            "wallet-deposit-requests",
            "wallet-withdraw-requests"
        ]
    
    def check_prerequisites(self) -> bool:
        """Check if kubectl and Kafka are available."""
        try:
            # Check kubectl
            result = subprocess.run(['kubectl', 'version', '--client'], 
                                 capture_output=True, text=True, check=True)
            logger.info("✅ kubectl is available")
            
            # Check namespace
            result = subprocess.run(['kubectl', 'get', 'namespace', self.namespace], 
                                 capture_output=True, text=True, check=True)
            logger.info(f"✅ Namespace {self.namespace} exists")
            
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Prerequisite check failed: {e}")
            return False
        except FileNotFoundError:
            logger.error("❌ kubectl not found in PATH")
            return False
    
    def get_kafka_pod(self) -> Optional[str]:
        """Get the first running Kafka pod name."""
        try:
            result = subprocess.run([
                'kubectl', 'get', 'pods', '-n', self.namespace, 
                '-l', 'app=kafka', '-o', 'jsonpath={.items[0].metadata.name}'
            ], capture_output=True, text=True, check=True)
            
            pod_name = result.stdout.strip()
            if pod_name:
                self.kafka_pod = pod_name
                logger.info(f"✅ Found Kafka pod: {pod_name}")
                return pod_name
            else:
                logger.error("❌ No Kafka pods found")
                return None
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to get Kafka pod: {e}")
            return None
    
    def check_kafka_pod_status(self) -> bool:
        """Check if Kafka pod is running."""
        if not self.kafka_pod:
            return False
            
        try:
            result = subprocess.run([
                'kubectl', 'get', 'pod', self.kafka_pod, '-n', self.namespace,
                '-o', 'jsonpath={.status.phase}'
            ], capture_output=True, text=True, check=True)
            
            status = result.stdout.strip()
            if status == 'Running':
                logger.info(f"✅ Kafka pod {self.kafka_pod} is running")
                return True
            else:
                logger.error(f"❌ Kafka pod {self.kafka_pod} is not running (status: {status})")
                return False
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to check pod status: {e}")
            return False
    
    def list_topics(self) -> List[str]:
        """List all Kafka topics."""
        try:
            result = subprocess.run([
                'kubectl', 'exec', '-n', self.namespace, self.kafka_pod, '--',
                'kafka-topics.sh', '--bootstrap-server', 'localhost:9092', '--list'
            ], capture_output=True, text=True, check=True)
            
            topics = [topic.strip() for topic in result.stdout.strip().split('\n') if topic.strip()]
            logger.info(f"📋 Found {len(topics)} topics: {topics}")
            return topics
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to list topics: {e}")
            return []
    
    def list_consumer_groups(self) -> List[str]:
        """List all consumer groups."""
        try:
            result = subprocess.run([
                'kubectl', 'exec', '-n', self.namespace, self.kafka_pod, '--',
                'kafka-consumer-groups.sh', '--bootstrap-server', 'localhost:9092', '--list'
            ], capture_output=True, text=True, check=True)
            
            groups = [group.strip() for group in result.stdout.strip().split('\n') if group.strip()]
            self.consumer_groups = groups
            logger.info(f"📋 Found {len(groups)} consumer groups: {groups}")
            return groups
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to list consumer groups: {e}")
            return []
    
    def describe_consumer_group(self, group_name: str) -> Dict:
        """Get detailed information about a consumer group."""
        try:
            result = subprocess.run([
                'kubectl', 'exec', '-n', self.namespace, self.kafka_pod, '--',
                'kafka-consumer-groups.sh', '--bootstrap-server', 'localhost:9092',
                '--describe', '--group', group_name
            ], capture_output=True, text=True, check=True)
            
            # Parse the output to extract useful information
            lines = result.stdout.strip().split('\n')
            group_info = {
                'group': group_name,
                'topics': [],
                'total_lag': 0,
                'members': 0
            }
            
            for line in lines:
                if 'TOPIC' in line and 'PARTITION' in line:
                    # Skip header
                    continue
                elif line.strip() and not line.startswith('GROUP'):
                    parts = line.split()
                    if len(parts) >= 6:
                        topic_info = {
                            'topic': parts[0],
                            'partition': parts[1],
                            'current_offset': parts[2],
                            'log_end_offset': parts[3],
                            'lag': parts[4]
                        }
                        group_info['topics'].append(topic_info)
                        try:
                            group_info['total_lag'] += int(parts[4])
                        except ValueError:
                            pass
            
            group_info['members'] = len([line for line in lines if line.startswith('GROUP')])
            
            logger.info(f"📊 Consumer group {group_name}: {group_info['total_lag']} total lag, {len(group_info['topics'])} topic-partitions")
            return group_info
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to describe consumer group {group_name}: {e}")
            return {}
    
    def reset_consumer_group_offsets(self, group_name: str, topic: Optional[str] = None, 
                                    offset_type: str = "earliest") -> bool:
        """Reset consumer group offsets."""
        try:
            cmd = [
                'kubectl', 'exec', '-n', self.namespace, self.kafka_pod, '--',
                'kafka-consumer-groups.sh', '--bootstrap-server', 'localhost:9092',
                '--group', group_name, '--reset-offsets', f'--to-{offset_type}', '--execute'
            ]
            
            if topic:
                cmd.extend(['--topic', topic])
                logger.info(f"🔄 Resetting consumer group {group_name} for topic {topic} to {offset_type}")
            else:
                logger.info(f"🔄 Resetting consumer group {group_name} for all topics to {offset_type}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"✅ Successfully reset offsets for {group_name}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to reset offsets for {group_name}: {e}")
            return False
    
    def delete_consumer_group(self, group_name: str) -> bool:
        """Delete a consumer group."""
        try:
            result = subprocess.run([
                'kubectl', 'exec', '-n', self.namespace, self.kafka_pod, '--',
                'kafka-consumer-groups.sh', '--bootstrap-server', 'localhost:9092',
                '--delete', '--group', group_name
            ], capture_output=True, text=True, check=True)
            
            logger.info(f"✅ Successfully deleted consumer group {group_name}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to delete consumer group {group_name}: {e}")
            return False
    
    def cleanup_unfinished_jobs(self, group_name: str, strategy: str = "reset_earliest") -> bool:
        """Main cleanup function for unfinished jobs."""
        logger.info(f"🧹 Starting cleanup for consumer group: {group_name}")
        
        # Get current status
        group_info = self.describe_consumer_group(group_name)
        if not group_info:
            logger.error(f"❌ Could not get information for consumer group {group_name}")
            return False
        
        total_lag = group_info.get('total_lag', 0)
        if total_lag == 0:
            logger.info(f"✅ Consumer group {group_name} has no lag - no cleanup needed")
            return True
        
        logger.info(f"📊 Found {total_lag} unfinished messages in {group_name}")
        
        if strategy == "reset_earliest":
            logger.info("🔄 Strategy: Reset to earliest offset (reprocess all messages)")
            return self.reset_consumer_group_offsets(group_name, offset_type="earliest")
        
        elif strategy == "reset_latest":
            logger.info("🔄 Strategy: Reset to latest offset (skip all pending messages)")
            return self.reset_consumer_group_offsets(group_name, offset_type="latest")
        
        elif strategy == "delete_group":
            logger.info("🗑️  Strategy: Delete consumer group (will be recreated on next restart)")
            return self.delete_consumer_group(group_name)
        
        else:
            logger.error(f"❌ Unknown strategy: {strategy}")
            return False
    
    def show_status_report(self, group_name: Optional[str] = None):
        """Show comprehensive status report."""
        logger.info("📋 Generating Kafka status report...")
        
        # List topics
        topics = self.list_topics()
        print(f"\n📋 Topics ({len(topics)}):")
        for topic in topics:
            print(f"  - {topic}")
        
        # List consumer groups
        groups = self.list_consumer_groups()
        print(f"\n📋 Consumer Groups ({len(groups)}):")
        for group in groups:
            print(f"  - {group}")
        
        # Detailed info for specific group or all groups
        if group_name:
            if group_name in groups:
                group_info = self.describe_consumer_group(group_name)
                self._print_group_details(group_info)
            else:
                logger.error(f"❌ Consumer group {group_name} not found")
        else:
            # Show details for all groups
            for group in groups:
                group_info = self.describe_consumer_group(group)
                self._print_group_details(group_info)
    
    def _print_group_details(self, group_info: Dict):
        """Print formatted group details."""
        if not group_info:
            return
            
        print(f"\n📊 Consumer Group: {group_info.get('group', 'Unknown')}")
        print(f"  Members: {group_info.get('members', 0)}")
        print(f"  Total Lag: {group_info.get('total_lag', 0)}")
        
        if group_info.get('topics'):
            print("  Topic Details:")
            for topic_info in group_info['topics']:
                print(f"    {topic_info['topic']}:{topic_info['partition']} - "
                      f"Current: {topic_info['current_offset']}, "
                      f"End: {topic_info['log_end_offset']}, "
                      f"Lag: {topic_info['lag']}")

def main():
    parser = argparse.ArgumentParser(description='Kafka Job Cleanup Manager')
    parser.add_argument('-n', '--namespace', default='tondeka-app', 
                       help='Kubernetes namespace (default: tondeka-app)')
    parser.add_argument('-g', '--group', required=True,
                       help='Consumer group name to clean up')
    parser.add_argument('-s', '--strategy', default='reset_earliest',
                       choices=['reset_earliest', 'reset_latest', 'delete_group'],
                       help='Cleanup strategy (default: reset_earliest)')
    parser.add_argument('--status-only', action='store_true',
                       help='Show status only, no cleanup')
    parser.add_argument('--topic', 
                       help='Specific topic to reset (default: all topics)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize cleanup manager
    manager = KafkaCleanupManager(namespace=args.namespace)
    
    # Check prerequisites
    if not manager.check_prerequisites():
        logger.error("❌ Prerequisites not met")
        sys.exit(1)
    
    # Get Kafka pod
    if not manager.get_kafka_pod():
        logger.error("❌ Could not find Kafka pod")
        sys.exit(1)
    
    # Check pod status
    if not manager.check_kafka_pod_status():
        logger.error("❌ Kafka pod is not running")
        sys.exit(1)
    
    if args.status_only:
        # Show status only
        manager.show_status_report(args.group)
    else:
        # Perform cleanup
        if args.topic:
            # Reset specific topic
            success = manager.reset_consumer_group_offsets(
                args.group, topic=args.topic, offset_type=args.strategy.replace('reset_', '')
            )
        else:
            # Cleanup entire group
            success = manager.cleanup_unfinished_jobs(args.group, args.strategy)
        
        if success:
            logger.info("🎉 Cleanup completed successfully!")
            # Show updated status
            manager.show_status_report(args.group)
        else:
            logger.error("❌ Cleanup failed")
            sys.exit(1)

if __name__ == "__main__":
    main()
