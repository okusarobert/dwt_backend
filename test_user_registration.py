#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from shared.kafka_producer import get_kafka_producer

def test_user_registration():
    """Test sending a user registration event to Kafka"""
    producer = get_kafka_producer()
    
    # Create a test user registration event
    test_event = {
        "user_id": 999,  # Test user ID
        "email": "test@example.com",
        "timestamp": "2025-08-04T11:30:00.000000"
    }
    
    try:
        producer.send("user.registered", test_event)
        print("Successfully sent user registration event to Kafka")
        print("Event: " + json.dumps(test_event, indent=2))
    except Exception as e:
        print("Failed to send user registration event: " + str(e))

if __name__ == "__main__":
    test_user_registration() 