#!/usr/bin/env bash
# Render build script (runs on Linux during deploy, NOT locally on Windows).
set -o errexit
set -o pipefail

pip install --upgrade pip
pip install -r requirements.txt

python manage.py migrate --noinput
python manage.py createcachetable
python manage.py collectstatic --noinput
