#!/usr/bin/env bash
echo "Creating isolated virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

echo "Installing requirements..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Build successfully completed!"
