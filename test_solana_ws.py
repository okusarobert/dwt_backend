#!/usr/bin/env python3
"""
Simple test script to debug Solana WebSocket connection
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
            "method": "logsSubscribe",
            "params": [{"mentions": []}, {"commitment": "confirmed"}],
            "id": 1
        },
        {
            "jsonrpc": "2.0", 
            "method": "slotSubscribe",
            "params": [],
            "id": 2
        }
    ]
    
    for sub in subscriptions:
        print(f"📡 Sending: {json.dumps(sub)}")
        ws.send(json.dumps(sub))
        time.sleep(1)

def main():
    api_key = "EbcNdRQag_4Ep75VtLuPLV3-MMfLKMvH"
    ws_url = f"wss://solana-mainnet.g.alchemy.com/v2/{api_key}"
    
    print(f"🔗 Connecting to: {ws_url}")
    
    ws = websocket.WebSocketApp(
        ws_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    print("⏳ Starting WebSocket connection...")
    ws.run_forever()

if __name__ == "__main__":
    main() 