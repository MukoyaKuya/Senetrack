FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Create dummy source map to satisfy WhiteNoise collectstatic check
RUN mkdir -p /app/scorecard/static/scorecard/vendor/ && touch /app/scorecard/static/scorecard/vendor/chart.umd.js.map

# Collect static files during build (speeds up container startup)
# Using a dummy secret key for the build process
RUN DJANGO_SECRET_KEY=build-time-insecure-key python manage.py collectstatic --noinput --clear

# Make the startup script executable
RUN chmod +x /app/scripts/start.sh

# Expose port (Cloud Run sets PORT env var)
EXPOSE 8080

# Command to run on container start
CMD ["/app/scripts/start.sh"]
