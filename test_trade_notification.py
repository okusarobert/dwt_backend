#!/usr/bin/env python3
"""
Test script to manually send a trade notification via Redis pub/sub
to verify the WebSocket notification flow is working end-to-end.
"""

import redis
import json
import datetime
import sys

def send_test_notification(trade_id):
    """Send a test trade completion notification"""
    try:
        # Connect to Redis
        r = redis.Redis(
            host='redis',
            port=6379,
            db=0,
            decode_responses=True
        )
        
        # Test Redis connection
        r.ping()
        print(f"✅ Connected to Redis")
        
        # Create test notification data
        notification_data = {
            'type': 'trade_status_update',
            'trade_id': trade_id,
            'data': {
                'status': 'completed',
                'message': f'TEST: Trade #{trade_id} completed successfully',
                'trade_type': 'buy',
                'crypto_currency': 'BTC',
                'crypto_amount': 0.00000121,
                'fiat_amount': 500.0,
                'completed_at': datetime.datetime.utcnow().isoformat()
            },
            'timestamp': datetime.datetime.utcnow().isoformat()
        }
        
        # Publish to Redis
        subscribers = r.publish('trade_updates', json.dumps(notification_data))
        print(f"🔔 PUBLISHED test notification for trade {trade_id} to {subscribers} subscribers")
        print(f"📄 Notification data: {json.dumps(notification_data, indent=2)}")
        
        return True
        
    except redis.ConnectionError as e:
        print(f"❌ Redis connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error sending notification: {e}")
        return False

if __name__ == "__main__":
    trade_id = sys.argv[1] if len(sys.argv) > 1 else "105"
    print(f"🧪 Testing trade notification for trade ID: {trade_id}")
    
    success = send_test_notification(trade_id)
    if success:
        print(f"✅ Test notification sent successfully!")
        print(f"👀 Check the frontend for trade {trade_id} to see if it receives the update")
    else:
        print(f"❌ Failed to send test notification")
