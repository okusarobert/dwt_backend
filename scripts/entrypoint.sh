#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Wait for the database to be ready
/app/wait-for-it.sh "${DB_HOST}:${DB_PORT}" -t 60

# Wait for Kafka to be ready
/app/wait-for-it.sh kafka:9092 -t 120

echo "Waiting for postgres..."

while ! nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 0.1
done

echo "PostgreSQL started"

# Start the application
exec "$@"
