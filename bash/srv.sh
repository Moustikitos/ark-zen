. ~/.local/share/ark-zen/venv/bin/activate
export PYTHONPATH=${PYTHONPATH}:${HOME}/ark-zen
gunicorn --bind=0.0.0.0:5000 --workers=5 zen.app:app --access-logfile -
deactivate
