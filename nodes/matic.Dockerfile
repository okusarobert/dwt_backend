#
# NOTE: THIS DOCKERFILE IS GENERATED VIA "generate-templates.sh"
#
# PLEASE DO NOT EDIT IT DIRECTLY.
#

FROM python:3.11-alpine AS base
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV ELECTRUM_USER=electrum
ENV ELECTRUM_HOME=/home/$ELECTRUM_USER
ENV ELECTRUM_DIRECTORY=${ELECTRUM_HOME}/.bitcart-matic
ENV IN_DOCKER=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_NO_CACHE=1
ENV UV_NO_SYNC=1
ENV MATIC_HOST=0.0.0.0
LABEL org.bitcart.image=matic-daemon

FROM base AS build-image

RUN adduser -D $ELECTRUM_USER && \
	mkdir -p /data/ && \
	ln -sf /data/ $ELECTRUM_DIRECTORY && \
	chown ${ELECTRUM_USER} $ELECTRUM_DIRECTORY && \
	mkdir -p $ELECTRUM_HOME/site && \
	chown ${ELECTRUM_USER} $ELECTRUM_HOME/site && \
	apk add --no-cache libsecp256k1 libsecp256k1-dev git && \
	apk add --no-cache --repository=https://dl-cdn.alpinelinux.org/alpine/edge/main jemalloc && \
	ln -sf /usr/lib/libsecp256k1.so.2 /usr/lib/libsecp256k1.so.0

COPY bitcart $ELECTRUM_HOME/site

RUN apk add git gcc python3-dev musl-dev automake autoconf libtool file git make libffi-dev && \
	cd $ELECTRUM_HOME/site && \
	pip install --no-cache-dir python-decouple==3.7 && \
	pip install --no-cache-dir aiohttp==3.8.4 && \
	pip install --no-cache-dir mnemonic==0.20 && \
	pip install --no-cache-dir web3>=6.0.0

# No need to copy from compile-image since we're installing directly in build-image

ENV PYTHONUNBUFFERED=1 PYTHONMALLOC=malloc LD_PRELOAD=libjemalloc.so.2 MALLOC_CONF=background_thread:true,max_background_threads:1,metadata_thp:auto,dirty_decay_ms:80000,muzzy_decay_ms:80000
ENV PATH="$ELECTRUM_HOME/.venv/bin:$PATH"
USER $ELECTRUM_USER
WORKDIR $ELECTRUM_HOME/site

CMD ["python","daemons/matic.py"]