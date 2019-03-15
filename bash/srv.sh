. ~/.local/share/ark-zen/venv/bin/activate
gunicorn --bind=0.0.0.0:5000 --workers=5 zen.app:app
deactivate

