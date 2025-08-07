#!/usr/bin/env python3
"""
Test script to debug World Chain WebSocket connection
"""

import json
import websocket
import time

def on_message(ws, message):
    print(f"📨 Received: {message[:200]}...")
    
def on_error(ws, error):
    print(f"❌ Error: {error}")
    
def on_close(ws, close_status_code, close_msg):
    print(f"🔌 Closed: {close_status_code} - {close_msg}")
    
def on_open(ws):
    print("🔌 Connected!")
    
    # Try different subscription methods
    subscriptions = [
        {
            "jsonrpc": "2.0",
            "method": "eth_subscribe",
            "params": ["newHeads"],
            "id": 1
        },
        {
            "jsonrpc": "2.0",
            "method": "eth_subscribe", 
            "params": ["logs", {"topics": []}],
            "id": 2
        },
        {
            "jsonrpc": "2.0",
            "method": "eth_subscribe",
            "params": ["newPendingTransactions"],
            "id": 3
        }
    ]
    
    for sub in subscriptions:
        ws.send(json.dumps(sub))
        print(f"📡 Sent: {sub['method']}")
        time.sleep(1)

# Connect to World Chain WebSocket
ws_url = "wss://worldchain-mainnet.g.alchemy.com/v2/EbcNdRQag_4Ep75VtLuPLV3-MMfLKMvH"

print("🔧 Testing World Chain WebSocket connection...")
print(f"📡 URL: {ws_url}")

websocket.enableTrace(True)
ws = websocket.WebSocketApp(
    ws_url,
    on_open=on_open,
    on_message=on_message,
    on_error=on_error,
    on_close=on_close
)

print("⏳ Running for 30 seconds...")
ws.run_forever() 