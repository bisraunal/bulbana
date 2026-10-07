#!/usr/bin/env bash
echo "Installing dependencies with --break-system-packages..."
python3 -m pip install --break-system-packages -r requirements.txt

echo "Collecting static files..."
python3 manage.py collectstatic --noinput --clear

echo "Running migrations..."
python3 manage.py migrate --noinput
