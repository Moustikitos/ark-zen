# -*- encoding:utf-8 -*-
from zen import crypto

import io
import os
import sys
import json
import shlex
import getpass
import requests
import datetime
import subprocess

__PY3__ = True if sys.version_info[0] >= 3 else False
ROOT = os.path.abspath(os.path.dirname(__file__))
NAME = os.path.splitext(os.path.basename(__file__))[0]

input = raw_input if not __PY3__ else input


def loadJson(path):
	if os.path.exists(path):
		with io.open(path) as in_:
			data = json.load(in_)
	else:
		data = {}
	return data


def dumpJson(data, path):
	with io.open(path, "w" if __PY3__ else "wb") as out:
		json.dump(data, out, indent=4)


def loadConfig():
	return loadJson(os.path.join(ROOT, NAME+".json"))	


def dumpConfig(data):
	dumpJson(data, os.path.join(ROOT, NAME+".json"))


def findBlockchains():
	try:
		return [os.path.splitext(name)[0] for name in os.listdir(os.path.join(ROOT, "cfg")) if name.endswith(".json")]
	except:
		return []


def chooseItem(msg, *elem):
	n = len(elem)
	if n > 1:
		sys.stdout.write(msg + "\n")
		for i in range(n):
			sys.stdout.write("    %d - %s\n" % (i+1, elem[i]))
		i = 0
		while i < 1 or i > n:
			try:
				i = input("Choose an item: [1-%d]> " % n)
				i = int(i)
			except:
				i = 0
		return elem[i-1]
	elif n == 1:
		return elem[0]
	else:
		sys.stdout.write("Nothing to choose...\n")
		return False


def setup():
	config = loadConfig()

	items = findBlockchains()
	blockchain = chooseItem("%d blockchain found:"%len(items), *items)
	blockchain_json = loadJson(os.path.join(ROOT, "cfg", blockchain+".json"))
	network = chooseItem("%d network found:"%len(items), *blockchain_json["networks"].keys())
	config["cmd"] = {
		"rebuild": blockchain_json.pop("rebuild", []),
		"restart": blockchain_json.pop("restart", []),
		"nodeheight": blockchain_json.pop("nodeheight", [])
	}
	config["network"] = network
	config["blockchain"] = blockchain
	config.update(**blockchain_json.pop("networks")[network])
	config.update(**blockchain_json)

	tbw_config = loadJson(os.path.join(ROOT, "tbw.json"))
	node = os.path.dirname(tbw_config.get("node", os.path.expanduser("~/%s-node"%blockchain)))
	while not os.path.exists(os.path.join(node, "config.%s.json" % network)):
		node = input("> enter node path: ")
	tbw_config["node"] = os.path.join(node, "config.%s.json" % network)
	_cnf = loadJson(tbw_config["node"])
	secret = _cnf["forging"]["secret"][0]
	keys = crypto.getKeys(secret)
	config["publicKey"] = keys["publicKey"]
	# config["network"] = _cnf["network"]
	config["nethash"] = _cnf["nethash"]
	config["version"] = _cnf["version"]
	config["port"] = _cnf["port"]

	seed = getBestSeed(*config["seeds"])
	account = requests.get(seed+"/api/delegates/get?publicKey=%s" % keys["publicKey"], verify=True, timeout=5).json().get("delegate", {})
	tbw_config["username"] = account["username"]
	tbw_config["excludes"] = [account["address"]]
	account = requests.get(seed+"/api/accounts?address=%s" % account["address"], verify=True, timeout=5).json().get("account", {})

	if account.get("secondPublicKey", False):
		seed = tbw_config.get("#2", "00")
		secondPublicKey = crypto.getKeys(seed=seed)["publicKey"]
		while secondPublicKey != account["secondPublicKey"]:
			secret = getpass.getpass("> enter your second secret: ")
			seed = crypto.hashlib.sha256(secret.encode("utf8") if not isinstance(secret, bytes) else secret).digest()
			secondPublicKey = crypto.getKeys(seed=seed)
		tbw_config["#2"] = hexlify(seed)
	else:
		tbw_config["#2"] = None

	dumpJson(tbw_config, os.path.join(ROOT, "tbw.json"))
	config["user"] = os.environ.get("USER", None)
	config["homedir"] = os.environ.get("HOME", None)
	dumpConfig(config)


def configure():
	config = loadConfig()
	tbw_config = loadJson(os.path.join(ROOT, "tbw.json"))
	if OPTIONS.share:
		tbw_config["share"] = min(1.0, max(0.1, OPTIONS.share))
	if OPTIONS.threshold:
		tbw_config["threshold"] = max(0.1, OPTIONS.threshold)
	if OPTIONS.funds:
		if requests.get(config["peer"]+"/api/accounts?address=%s" % OPTIONS.funds, verify=True, timeout=5).json().get("success", False):
			tbw_config["funds"] = OPTIONS.funds
		else:
			sys.stdout.write("> %s seems not to be a valid address" % OPTIONS.funds)
	if OPTIONS.vendorField:
		tbw_config["vendorField"] = OPTIONS.vendorField[0:min(64, len(OPTIONS.vendorField))]
	if OPTIONS.excludes:
		tbw_config["excludes"] = OPTIONS.excludes.split(",")
	if OPTIONS.targeting:
		tbw_config["targeting"] = not tbw_config.pop("targeting", False)

	dumpJson(tbw_config, os.path.join(ROOT, "tbw.json"))


def logMsg(msg):
	sys.stdout.write(">>> [%s] %s\n" % (datetime.datetime.now().strftime("%x %X"), msg))
	sys.stdout.flush()


def getBestSeed(*seeds):
	height, url = 0, None
	for seed in seeds:
		try:
			h = requests.get(seed+"/api/blocks/getHeight", verify=True, timeout=5).json().get("height", 0)
			if h > height:
				height = h
				url = seed
		except Exception as error:
			sys.stdout.write("    Error occured with %s : %s\n" % (seed, error))
	return url


def execute(*lines, **config):
	out, err = "", ""
	for line in [l%config for l in lines]:
		if not config.get("quiet", False):
			sys.stdout.write("... %s\n" % line)
		sys.stdout.flush()
		err += "... %s\n"%line
		answer = subprocess.Popen(shlex.split(line), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		code =  answer.wait()
		if code != 0:
			sys.stdout.write("    [STATUS CODE RETURNED: %r]\n" % code)
		_out, _err = answer.communicate()
		out += _out
		err += _err
	return out, err


def bash(*lines, **config):
	answer = subprocess.Popen("/bin/bash", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	out, err = answer.communicate("\n".join([l%config for l in lines]))
	return out, err
