#!/bin/bash

echo "🔧 Enabling ZMQ in Bitcoin node..."

# Get current Bitcoin configuration
echo "📋 Current Bitcoin configuration:"
docker exec bitcoin cat /home/bitcoin/.bitcoin/bitcoin.conf

echo ""
echo "🔧 Adding ZMQ configuration..."

# Create a backup of the current config
docker exec bitcoin cp /home/bitcoin/.bitcoin/bitcoin.conf /home/bitcoin/.bitcoin/bitcoin.conf.backup

# Add ZMQ configuration to Bitcoin config
cat << 'EOF' | docker exec -i bitcoin tee -a /home/bitcoin/.bitcoin/bitcoin.conf

# ZMQ Configuration for real-time notifications
zmqpubrawtx=tcp://0.0.0.0:28332
zmqpubrawblock=tcp://0.0.0.0:28333
zmqpubhashblock=tcp://0.0.0.0:28334
zmqpubhashtx=tcp://0.0.0.0:28335
zmqpubsequence=tcp://0.0.0.0:28336
EOF

echo "✅ ZMQ configuration added to Bitcoin config"
echo ""
echo "📋 Updated Bitcoin configuration:"
docker exec bitcoin cat /home/bitcoin/.bitcoin/bitcoin.conf

echo ""
echo "🔄 Restarting Bitcoin node to apply ZMQ configuration..."
docker restart bitcoin

echo "⏳ Waiting for Bitcoin node to restart..."
sleep 10

echo "📊 Checking Bitcoin node status..."
docker exec bitcoin bitcoin-cli -conf=/home/bitcoin/.bitcoin/bitcoin.conf -rpcuser=bitcoin -rpcpassword=bitcoinpassword getblockchaininfo | head -10

echo ""
echo "🔍 Checking if ZMQ is enabled..."
docker exec bitcoin bitcoin-cli -conf=/home/bitcoin/.bitcoin/bitcoin.conf -rpcuser=bitcoin -rpcpassword=bitcoinpassword getnetworkinfo | grep -i zmq || echo "ZMQ not found in network info (this is normal)"

echo ""
echo "✅ ZMQ should now be enabled!"
echo "💡 You can now run: python bitcoin_zmq_monitor.py" 