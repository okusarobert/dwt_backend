FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV LITECOIN_VERSION=0.21.4
ENV LITECOIN_DATA=/home/litecoin/.litecoin

# Install dependencies
RUN apt-get update && apt-get install -y \
	wget \
	ca-certificates \
	&& rm -rf /var/lib/apt/lists/*

# Create litecoin user
RUN useradd -r -m -U -d /home/litecoin -s /bin/bash litecoin

# Download and install Litecoin Core
RUN wget https://download.litecoin.org/litecoin-${LITECOIN_VERSION}/linux/litecoin-${LITECOIN_VERSION}-x86_64-linux-gnu.tar.gz \
	&& tar -xzf litecoin-${LITECOIN_VERSION}-x86_64-linux-gnu.tar.gz \
	&& install -m 0755 -o root -g root -t /usr/local/bin litecoin-${LITECOIN_VERSION}/bin/* \
	&& rm -rf litecoin-${LITECOIN_VERSION}*

# Create data directory
RUN mkdir -p ${LITECOIN_DATA} && chown litecoin:litecoin ${LITECOIN_DATA}

# Copy configuration
COPY litecoin.conf ${LITECOIN_DATA}/
RUN chown litecoin:litecoin ${LITECOIN_DATA}/litecoin.conf

# Expose ports
EXPOSE 9332 9333

# Switch to litecoin user
USER litecoin

# Set working directory
WORKDIR /home/litecoin

# Default command
CMD ["litecoind", "-conf=/home/litecoin/.litecoin/litecoin.conf"] 