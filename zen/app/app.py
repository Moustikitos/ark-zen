# -*- encoding:utf-8 -*-
import os
import flask
import sqlite3
import threading
from flask_bootstrap import Bootstrap

from zen import tfa, crypto
from zen.cmn import loadConfig, loadJson
from zen.chk import getBestSeed, getNextForgeRound
from zen.tbw import loadTBW, spread, loadParam

# create the application instance 
app = flask.Flask(__name__) 
Bootstrap(app)
app.config.update(
	# 300 seconds = 5 minutes lifetime session
	PERMANENT_SESSION_LIFETIME = 300,
	# used to encrypt cookies
	# secret key is generated each time app is restarted
	SECRET_KEY = os.urandom(24),
	# JS can't access cookies
	SESSION_COOKIE_HTTPONLY = True,
	# bi use of https
	SESSION_COOKIE_SECURE = False,
	# update cookies on each request
	# cookie are outdated after PERMANENT_SESSION_LIFETIME seconds of idle
	SESSION_REFRESH_EACH_REQUEST = True
)

CONFIG = loadConfig()
PARAM = loadParam()

# show index
@app.route("/")
def render():
	global CONFIG, PARAM
	spread()

	weight = loadTBW()
	tokens = sum(weight.values())
	c = float(sum(weight.values()))
	items = [[k,v/max(1.0, c)*100] for k,v in weight.items()]

	return flask.render_template(
		"bs-layout.html",
		next_block=getNextForgeRound(CONFIG["peer"], **CONFIG),
		items=sorted(items, key=lambda e:e[-1], reverse=True),
		tokens=tokens,
		username=PARAM.get("username", "_"),
		share=PARAM.get("share", 1.),
		threshold=PARAM.get("threshold", 0.),
		symbol=PARAM.get("symbol", "token"),
		explorer=CONFIG["explorer"]
	)


@app.route("/history/<string:field>/<string:value>/<int:start>/<int:number>")
def render_history(field, value, start, number):
	global CONFIG, PARAM
	if value:
		if getattr(flask.g, "search_field", None) != field:
				flask.g.rows = search(**{field:value, "table":"transactions"})
				flask.g.search_field = field

		return flask.render_template(
			"bs-history.html",
			field=field,
			value=value,
			start=start,
			number=number,
			explorer=CONFIG["explorer"],
			symbol=PARAM.get("symbol", "token"),
		)

@app.route("/stats")
def get_stats():
	return flask.render_template(
		"bs-stats.html",
		username=PARAM.get("username", "_")
	)
	
	
@app.teardown_appcontext
def close(*args, **kw):
	if hasattr(flask.g, "database"):
		flask.g.database.close()


def connect():
	if not hasattr(flask.g, "database"):
		setattr(flask.g, "database", sqlite3.connect(os.path.join(app.root_path, "..", "pay.db")))
		flask.g.database.row_factory = sqlite3.Row
	return flask.g.database.cursor()


def search(table="transaction", **kw):
	cursor = connect()
	cursor.execute(
		"SELECT * FROM %s WHERE %s=? ORDER BY timestamp DESC;"%(table, kw.keys()[0]),
		(kw.values()[0], )
	)
	result = cursor.fetchall()
	return [dict(zip(row.keys(), row)) for row in result]


@app.context_processor
def override_url_for():
	return dict(url_for=dated_url_for)

def dated_url_for(endpoint, **values):
	if endpoint == 'static':
		filename = values.get('filename', None)
		if filename:
			file_path = os.path.join(app.root_path,
									 endpoint, filename)
			values['q'] = int(os.stat(file_path).st_mtime)
	return flask.url_for(endpoint, **values)


## Identification

@app.route("/login", methods=["GET", "POST"])
def login():
	global CONFIG, PARAM
	# enable session lifetime to 10 min
	flask.session["permanent"] = True
	# if POST method send from login page or any POST containing a signature field
	if flask.request.method == "POST":
		flask.session.pop("logged", None)
		# check signature match (signature must be sent as hexadecimal string)
		try: check = tfa.check(CONFIG["publicKey"], crypto.unhexlify(flask.request.form["signature"]))
		except: check = False
		if check:
			# store the logged state
			flask.session["logged"] = True
			# go to manage page
			return flask.redirect(flask.url_for("manage"))
		else:
			# store the logged state
			flask.session["logged"] = False
			# return to index
			return flask.redirect(flask.url_for("render"))
	# if classic access render login page 
	else:
		return flask.render_template("login.html")


@app.route("/logout")
def logout():
	# store the logged state
	flask.session["logged"] = False
	# return to index
	return flask.redirect(flask.url_for("render"))


@app.route("/manage")
def manage():
	# check if logged in from cookies
	if not flask.session.get("logged", False):
		# if not logged in return to login page
		return flask.redirect(flask.url_for("login"))
	else:
		# render manage page
		return flask.render_template_string(
"""{% extends "base.html" %}
{% block content %}
<div class="container"> 
<h1 class="jumbotron">Node management page in construction</h1>
<form>
<dl>
<dd/><input type="submit" value="Restart"/><br/>
<dd/><input type="submit" value="Rebuild"/><br/>
<dd/><input type="submit" value="Update"/><br/>
</dl>
</form>
</div>
{% endblock %}
"""
)
