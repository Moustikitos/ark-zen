# -*- coding:utf-8 -*-
import zen
import pytz
import json
import flask
import dposlib
import datetime
import psycopg2
import psycopg2.extras

from zen.api import data


def connect():
	if not hasattr(flask.g, database):
		setattr(flask.g, database, psycopg2.connect(
			dbname=zen.ENV["CORE_DB_DATABASE"],
			host=zen.ENV["CORE_DB_HOST"],
			port=zen.ENV["CORE_DB_PORT"],
			user=zen.ENV["CORE_DB_USER"],
			password=zen.ENV["CORE_DB_PASSWORD"]
		))
	return getattr(flask.g, database).cursor(cursor_factory=psycopg2.extras.DictCursor)


@app.route("/report")
def report():
	# compute default time data
	currency = flask.request.args.get('currency', default="USD", type="str")

	timezone = flask.request.args.get('timezone', default="UTC", type="str")
	timezone = pytz.timezone(timezone)

	year = flask.request.args.get('year', default=datetime.datetime.now(timezone).year, type=int)

	from_ = flask.request.args.get('from', default=datetime.datetime(year,1,1,tzinfo=timezone).timestamp(), type=int)
	from_ = datetime.datetime.fromtimestamp(from_)
	pytz.utc.localize(from_)
	from_ = dposlib.blockchain.slots.getTime(from_)

	to = flask.request.args.get('to', default=datetime.datetime(year,12,31,23,59,tzinfo=timezone).timestamp(), type=int)
	to = datetime.datetime.fromtimestamp(to)
	pytz.utc.localize(to)
	to = dposlib.blockchain.slots.getTime(to)

	delegate = flask.request.args.get('username', default="", type=str)
	address = flask.request.args.get('address', default="", type=str)
	publicKey = flask.request.args.get('publicKey', default="", type=str)

	if delegate == address == publicKey == "":
		return json.dumps({"success":False,"message":"provide at least delegate or address or publicKey"})
	else:
		cur = connetc()
		if delegate != "":
			publicKey = zen.rest.GET.api.v2.delegates(delegate)["data"]["publicKey"]
		elif address != "":
			publicKey = zen.rest.GET.api.v2.wallet(address)["data"]["publicKey"]
		parameters = {"publicKey":publicKey, "from":from_, "to":to}
		cur.execute(
			"""SELECT * FROM transactions WHERE
			     type=0 AND 
				 (recipient_id=%(publicKey)s OR sender_public_key=%(publicKey)s) AND
				 (timestamp >= %(from)s AND timestamp <= %(to)s""",
			parameters
		)
		transactions = cur.fetchall()
		cur.execute(
			"""SELECT * FROM blocks WHERE
			     generator_public_key=%(publicKey)s AND
				 (timestamp >= %(from)s AND timestamp <= %(to)s""",
			parameters
		)
		blocks = cur.fetchall()
		
		ARK2BTC = data.loadCryptoCompareYearData(year, "ARK", "BTC")
		BTC2CUR = data.loadCryptoCompareYearData(year, "BTC", currency)
		input_tx = {}
		output_tx = {}
		forgery = {}
