#!/usr/bin/env python3
"""
Simple Kafka Cleanup Script for Docker Containers
This script works directly with Kafka without needing kubectl.
"""

import os
import sys
import subprocess
import json
import logging
from typing import List, Dict, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DockerKafkaCleanup:
    """Simple Kafka cleanup for Docker environments."""
    
    def __init__(self, kafka_host: str = "kafka", kafka_port: int = 9092):
        self.kafka_host = kafka_host
        self.kafka_port = kafka_port
        self.bootstrap_server = f"{kafka_host}:{kafka_port}"
        
        # Your Kafka topics
        self.topics = [
            "wallet-credit-requests",
            "user.registered", 
            "wallet-deposit-requests",
            "wallet-withdraw-requests"
        ]
        
        # Your consumer group
        self.consumer_group = "wallet-merged-consumer"
    
    def check_kafka_connection(self) -> bool:
        """Check if Kafka is reachable."""
        try:
            # Try to connect to Kafka
            result = subprocess.run([
                'kafka-consumer-groups', '--bootstrap-server', self.bootstrap_server, '--list'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                logger.info(f"✅ Successfully connected to Kafka at {self.bootstrap_server}")
                return True
            else:
                logger.error(f"❌ Failed to connect to Kafka: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Connection to Kafka timed out")
            return False
        except FileNotFoundError:
            logger.error("❌ kafka-consumer-groups command not found. Make sure Kafka tools are installed.")
            return False
        except Exception as e:
            logger.error(f"❌ Error connecting to Kafka: {e}")
            return False
    
    def list_topics(self) -> List[str]:
        """List all Kafka topics."""
        try:
            result = subprocess.run([
                'kafka-topics', '--bootstrap-server', self.bootstrap_server, '--list'
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
                'kafka-consumer-groups', '--bootstrap-server', self.bootstrap_server, '--list'
            ], capture_output=True, text=True, check=True)
            
            groups = [group.strip() for group in result.stdout.strip().split('\n') if group.strip()]
            logger.info(f"📋 Found {len(groups)} consumer groups: {groups}")
            return groups
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to list consumer groups: {e}")
            return []
    
    def describe_consumer_group(self, group_name: str) -> Dict:
        """Get detailed information about a consumer group."""
        try:
            result = subprocess.run([
                'kafka-consumer-groups', '--bootstrap-server', self.bootstrap_server,
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
    
    def reset_consumer_group_offsets(self, group_name: str, offset_type: str = "earliest") -> bool:
        """Reset consumer group offsets to clear pending jobs."""
        try:
            logger.info(f"🔄 Resetting consumer group {group_name} to {offset_type} offset...")
            
            result = subprocess.run([
                'kafka-consumer-groups', '--bootstrap-server', self.bootstrap_server,
                '--group', group_name, '--reset-offsets', f'--to-{offset_type}', '--execute'
            ], capture_output=True, text=True, check=True)
            
            logger.info(f"✅ Successfully reset offsets for {group_name}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to reset offsets for {group_name}: {e}")
            return False
    
    def delete_consumer_group(self, group_name: str) -> bool:
        """Delete a consumer group entirely."""
        try:
            logger.info(f"🗑️  Deleting consumer group {group_name}...")
            
            result = subprocess.run([
                'kafka-consumer-groups', '--bootstrap-server', self.bootstrap_server,
                '--delete', '--group', group_name
            ], capture_output=True, text=True, check=True)
            
            logger.info(f"✅ Successfully deleted consumer group {group_name}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to delete consumer group {group_name}: {e}")
            return False
    
    def cleanup_pending_jobs(self, strategy: str = "reset_earliest") -> bool:
        """Main function to clean up pending Kafka jobs."""
        logger.info(f"🧹 Starting cleanup for consumer group: {self.consumer_group}")
        
        # Check connection
        if not self.check_kafka_connection():
            return False
        
        # Get current status
        group_info = self.describe_consumer_group(self.consumer_group)
        if not group_info:
            logger.error(f"❌ Could not get information for consumer group {self.consumer_group}")
            return False
        
        total_lag = group_info.get('total_lag', 0)
        if total_lag == 0:
            logger.info(f"✅ Consumer group {self.consumer_group} has no pending jobs - no cleanup needed")
            return True
        
        logger.info(f"📊 Found {total_lag} pending jobs in {self.consumer_group}")
        
        if strategy == "reset_earliest":
            logger.info("🔄 Strategy: Reset to earliest offset (reprocess all messages)")
            return self.reset_consumer_group_offsets(self.consumer_group, "earliest")
        
        elif strategy == "reset_latest":
            logger.info("🔄 Strategy: Reset to latest offset (skip all pending messages)")
            return self.reset_consumer_group_offsets(self.consumer_group, "latest")
        
        elif strategy == "delete_group":
            logger.info("🗑️  Strategy: Delete consumer group (will be recreated on next restart)")
            return self.delete_consumer_group(self.consumer_group)
        
        else:
            logger.error(f"❌ Unknown strategy: {strategy}")
            return False
    
    def show_status(self):
        """Show current Kafka status."""
        logger.info("📋 Checking Kafka status...")
        
        # Check connection
        if not self.check_kafka_connection():
            return
        
        # List topics
        topics = self.list_topics()
        
        # List consumer groups
        groups = self.list_consumer_groups()
        
        # Show detailed info for your consumer group
        if self.consumer_group in groups:
            group_info = self.describe_consumer_group(self.consumer_group)
            self._print_group_details(group_info)
        else:
            logger.warning(f"⚠️  Consumer group {self.consumer_group} not found")
    
    def _print_group_details(self, group_info: Dict):
        """Print formatted group details."""
        if not group_info:
            return
            
        print(f"\n📊 Consumer Group: {group_info.get('group', 'Unknown')}")
        print(f"  Members: {group_info.get('members', 0)}")
        print(f"  Total Pending Jobs: {group_info.get('total_lag', 0)}")
        
        if group_info.get('topics'):
            print("  Topic Details:")
            for topic_info in group_info['topics']:
                print(f"    {topic_info['topic']}:{topic_info['partition']} - "
                      f"Current: {topic_info['current_offset']}, "
                      f"End: {topic_info['log_end_offset']}, "
                      f"Pending: {topic_info['lag']}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Docker Kafka Cleanup Tool')
    parser.add_argument('-s', '--strategy', default='reset_earliest',
                       choices=['reset_earliest', 'reset_latest', 'delete_group'],
                       help='Cleanup strategy (default: reset_earliest)')
    parser.add_argument('--status-only', action='store_true',
                       help='Show status only, no cleanup')
    parser.add_argument('--kafka-host', default='kafka',
                       help='Kafka host (default: kafka)')
    parser.add_argument('--kafka-port', type=int, default=9092,
                       help='Kafka port (default: 9092)')
    parser.add_argument('--consumer-group', default='wallet-merged-consumer',
                       help='Consumer group name (default: wallet-merged-consumer)')
    
    args = parser.parse_args()
    
    # Initialize cleanup tool
    cleanup = DockerKafkaCleanup(
        kafka_host=args.kafka_host,
        kafka_port=args.kafka_port
    )
    cleanup.consumer_group = args.consumer_group
    
    if args.status_only:
        # Show status only
        cleanup.show_status()
    else:
        # Perform cleanup
        success = cleanup.cleanup_pending_jobs(args.strategy)
        
        if success:
            logger.info("🎉 Cleanup completed successfully!")
            # Show updated status
            cleanup.show_status()
        else:
            logger.error("❌ Cleanup failed")
            sys.exit(1)

if __name__ == "__main__":
    main()
