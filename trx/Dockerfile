FROM python:3.12-slim-bullseye

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
	gcc netcat-traditional\
	&& rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code

COPY ./trx /app/
COPY db /app/db
COPY shared /app/shared
COPY scripts /app
COPY alembic /app/alembic

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port (if needed for health checks)
EXPOSE 8000

RUN chmod +x /app/entrypoint.sh
RUN chmod +x /app/wait-for-it.sh


ENTRYPOINT ["/app/entrypoint.sh"]

# Run the application
CMD ["python", "app.py"] 