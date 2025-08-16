#!/bin/bash

# Wait for database to be ready
echo "Waiting for database..."
python -c "
import time
import sys
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

max_attempts = 30
attempt = 0

while attempt < max_attempts:
    try:
        engine = create_engine('postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}')
        engine.connect()
        print('Database is ready!')
        sys.exit(0)
    except OperationalError:
        attempt += 1
        print(f'Database not ready, attempt {attempt}/{max_attempts}')
        time.sleep(2)

print('Database connection failed after maximum attempts')
sys.exit(1)
"

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start the application
echo "Starting Ethereum Monitor Service..."
exec python app.py 