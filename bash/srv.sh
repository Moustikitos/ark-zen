#!/bin/bash
. ~/.local/share/ark-zen/venv/bin/activate
export PYTHONPATH=${PYTHONPATH}:${HOME}/ark-zen
gunicorn zen.app:app --bind=0.0.0.0:5000 --workers=5 --timeout 10 --access-logfile -
