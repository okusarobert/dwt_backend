FROM python:3.12-slim-bullseye

WORKDIR /app

# Copy application files
COPY ./websocket/ /app/
COPY ./db /app/db
COPY ./scripts /app
COPY requirements.txt alembic.ini /app/

# Install dependencies
RUN pip install -r /app/requirements.txt
RUN apt-get update && apt-get install -y netcat-traditional && rm -rf /var/lib/apt/lists/*

# Make scripts executable
RUN chmod +x /app/entrypoint.sh
RUN chmod +x /app/wait-for-it.sh

# Expose port
EXPOSE 5000

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "app.py"]
