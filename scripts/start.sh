#!/bin/bash
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Running migrations..."
python manage.py migrate --noinput

echo "Starting Gunicorn server..."
# Use the PORT environment variable provided by Cloud Run, default to 8080
exec gunicorn root.wsgi:application --bind 0.0.0.0:${PORT:-8080} --workers 2 --threads 4 --timeout 60
