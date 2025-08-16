#!/usr/bin/env python3
"""
Startup script for the WebSocket service
"""

import os
import sys
import logging
from pathlib import Path

# Add the websocket directory to Python path
websocket_dir = Path(__file__).parent
sys.path.insert(0, str(websocket_dir))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('websocket.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main startup function"""
    try:
        logger.info("🚀 Starting DWT Exchange WebSocket Service...")
        
        # Check if required environment variables are set
        required_env_vars = ['APP_SECRET']
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.warning(f"⚠️  Missing environment variables: {missing_vars}")
            logger.info("Using default values for development...")
            os.environ.setdefault('APP_SECRET', 'dev-secret-key-change-in-production')
        
        # Import and start the service
        from app import app, socketio
        
        logger.info("✅ WebSocket service initialized successfully")
        logger.info("🌐 Starting on http://0.0.0.0:5000")
        logger.info("📡 WebSocket endpoint: ws://localhost:5000")
        logger.info("🔌 Crypto price streaming: ENABLED")
        logger.info("💡 Press Ctrl+C to stop the service")
        
        # Start the service
        socketio.run(
            app, 
            host='0.0.0.0', 
            port=5000, 
            debug=False,  # Set to False for production
            use_reloader=False
        )
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("Make sure all dependencies are installed:")
        logger.error("  pip install -r requirements.txt")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"💥 Failed to start WebSocket service: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
