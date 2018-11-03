# -*- encoding:utf-8 -*-
import os
import zen
import math
import json
import flask
import dposlib
import datetime

from zen.app.core import app
from zen.tbw import initDb


def connect(username):
	if not hasattr(flask.g, username):
		setattr(flask.g, username, initDb(username))
	return getattr(flask.g, username).cursor()


@app.route("/")
def index():
	usernames = [name.split("-")[0] for name in os.listdir(os.path.join(zen.JSON)) if name.endswith("-webhook.json")]
	accounts = [dposlib.rest.GET.api.v2.delegates(username, returnKey="data") for username in usernames]
	return flask.render_template("index.html", accounts=[a for a in accounts if not a.get("username", False)])


@app.route("/<string:username>")
def zen_index(username):
	return ""


@app.route("/<string:username>/history/<int:page>/<int:n>")
def zen_history(username, page, n):
	cursor = connect(username)
	history_folder = os.path.join(zen.ROOT, "app", ".tbw", username, "history")

	try:
		tbw_list = sorted([os.path.splitext(name)[0] for name in os.listdir(history_folder) if name.endswith(".tbw")], reverse=True)
	except:
		tbw_list = []

	n_tbw = len(tbw_list)
	n_page = int(math.ceil(float(n_tbw) / n))
	start = page*n

	selection = list(sorted(tbw_list, reverse=True))[start:start+n]
	data = dict([name, zen.loadJson(name+".tbw", folder=history_folder)] for name in selection)

	details = dict(
		[name, cursor.execute("SELECT * FROM transactions WHERE filename = ?", (name,)).fetchall()] \
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
