# -*- encoding:utf-8 -*-
import os
import zen
import math
import json
import flask
import datetime

from zen.app.core import app
from zen.tbw import initDb


def connect(username):
	if not hasattr(flask.g, username):
		setattr(flask.g, username, initDb(username))
	return getattr(flask.g, username).cursor()


@app.route("/")
def index():
	return ""


@app.route("/<string:username>")
def zen_index(username):
	return ""


@app.route("/<string:username>/history/<int:page>/<int:n>")
def zen_history(username, page, n):
	cursor = connect(username)

	history_folder = os.path.join(zen.ROOT, "app", ".tbw", username, "history")
	tbw_list = sorted([name for name in os.listdir(history_folder) if name.endswith(".tbw")], reverse=True)
	n_tbw = len(tbw_list)
	n_page = int(math.ceil(float(n_tbw) / n))
	start = page*n

	selection = tbw_list[start:start+n]
	data = dict([name, zen.loadJson(name, folder=history_folder)] for name in selection)
	details = dict(
		[name, cursor.execute("SELECT * FROM transactions WHERE filename = ?", (name.replace(".tbw",""),)).fetchall()] \
		for name in selection 
	)

	return flask.render_template("history.html",
		username=username,
		curent_page=page,
		page_number=n_page,
		entry_number=n,
		selection=selection,
		data=data,
		details=details
	)
