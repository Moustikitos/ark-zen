# -*- coding:utf-8 -*-

from zen import tfa
from zen.cmn import loadConfig

import flask
import socket
import threading

config = loadConfig()

# app = flask.Flask(__name__)



# """
# {% block identify %}
# <a href="{{{ g.identify_action }}}">{{{ g.identify_text}}}</a>
# {% endblock %}
# """
