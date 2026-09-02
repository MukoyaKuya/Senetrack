#!/bin/bash
set -e

echo "Running migrations..."
python manage.py migrate --noinput

if [ "${SKIP_SYNC_PERFORMANCE:-false}" != "true" ]; then
  echo "Syncing performance data from JSON..."
  python manage.py sync_performance --apply
else
  echo "Skipping sync_performance (SKIP_SYNC_PERFORMANCE=true)"
fi

export GUNICORN_BIND="${GUNICORN_BIND:-0.0.0.0:${PORT:-8080}}"
export GUNICORN_WORKERS="${GUNICORN_WORKERS:-2}"

echo "Starting Gunicorn on ${GUNICORN_BIND} with ${GUNICORN_WORKERS} worker(s)..."
exec gunicorn root.wsgi:application -c gunicorn.conf.py
