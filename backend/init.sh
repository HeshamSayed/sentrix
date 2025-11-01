#!/bin/bash

echo "Waiting for postgres..."
until pg_isready -h postgres -p 5432 -U sentrix > /dev/null 2>&1; do
  sleep 1
done

echo "PostgreSQL ready"

echo "Running migrations..."
python manage.py migrate --fake-initial || python manage.py migrate

echo "Starting Gunicorn..."
exec gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers 4 --timeout 120

