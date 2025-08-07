#!/bin/bash

# Create litecoin.conf if it doesn't exist
if [ ! -f /litecoin/.litecoin/litecoin.conf ]; then
    cat > /litecoin/.litecoin/litecoin.conf << EOF
# Litecoin Core configuration file for testnet
testnet=1
server=1
rpcuser=litecoin
rpcpassword=litecoinpassword
rpcallowip=0.0.0.0/0
rpcbind=0.0.0.0:19332
rpcport=19332
txindex=0
prune=556
EOF
fi

# Start litecoind with proper arguments
exec litecoind -conf=/litecoin/.litecoin/litecoin.conf 