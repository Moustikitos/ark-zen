#!/bin/bash
. ~/.local/share/ark-zen/venv/bin/activate
export PYTHONPATH=${PYTHONPATH}:${HOME}/ark-zen
python bg.py
deactivate
exit
