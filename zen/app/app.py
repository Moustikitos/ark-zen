# -*- encoding:utf-8 -*-
import os
import flask
import sqlite3

# from flask import Flask, flask.render_template, flash, url_for
from zen.cmn import loadConfig, loadJson
from zen.chk import getBestSeed, getNextForgeRound
from zen.tbw import loadTBW, spread, loadParam


# create the application instance 
app = flask.Flask(__name__) 
CONFIG = loadConfig()


# show index
@app.route("/")
def render():
	param = loadParam()
	spread()

	weight = loadTBW()
	tokens = sum(weight.values())
	c = float(sum(weight.values()))
	items = [[k,v/max(1.0, c)*100] for k,v in weight.items()]

	return flask.render_template(
		"layout.html",
		next_block=getNextForgeRound(CONFIG["peer"], **CONFIG),
		items=sorted(items, key=lambda e:e[-1], reverse=True),
		tokens=tokens,
		username=param.get("username", "_"),
		share=param.get("share", 1.),
		threshold=param.get("threshold", 0.),
		symbol="\u466",
		explorer=CONFIG["explorer"]
	)


@app.route("/history/<string:field>/<string:value>/<int:start>/<int:number>")
def render_history(field, value, start, number):
	if value:
		if getattr(flask.g, "search_field", None) != field:
				flask.g.rows = search(**{field:value, "table":"transactions"})
				flask.g.search_field = field

		return flask.render_template(
			"history.html",
			field=field,
			value=value,
			start=start,
			number=number,
			explorer=CONFIG["explorer"]
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


_url_for = flask.url_for
@app.context_processor
def url_for():
	return dict(url_for=dated_url_for)
def dated_url_for(endpoint, **values):
	if endpoint == 'static':
		filename = values.get('filename', None)
		if filename:
			file_path = os.path.join(app.root_path,
									 endpoint, filename)
			values['q'] = int(os.stat(file_path).st_mtime)
	return _url_for(endpoint, **values)
flask.url_for = url_for
