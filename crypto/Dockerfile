FROM python:3.12-slim-bullseye

WORKDIR /app

COPY crypto /app/
COPY scripts /app
COPY ./shared /app/shared
COPY requirements.txt alembic.ini /app/

RUN pip install  -r /app/requirements.txt
RUN pip install pytest pytest-flask gunicorn flasgger

RUN apt-get update && apt-get install -y netcat-traditional && rm -rf /var/lib/apt/lists/*

RUN chmod +x /app/entrypoint.sh
RUN chmod +x /app/wait-for-it.sh


ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "main.py"]