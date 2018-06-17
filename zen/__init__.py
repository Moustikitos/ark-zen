# -*- coding:utf-8 -*-

import os
import io
import sys
import json
import time
import datetime

# register python familly
PY3 = True if sys.version_info[0] >= 3 else False
input = raw_input if not PY3 else input

import requests


# configure pathes
ROOT = os.path.abspath(os.path.dirname(__file__))
DATA = os.path.abspath(os.path.join(ROOT, "data"))
JSON = os.path.abspath(os.path.join(ROOT, "json"))
CFG = os.path.abspath(os.path.join(ROOT, "cfg"))
LOG = os.path.abspath(os.path.join(ROOT, "log"))


class Cache(dict):
	"A cache object to store temporally values"

	def __init__(self, delay=60):
		object.__setattr__(self, "delay", delay)
		object.__setattr__(self, "expires", {})

	def __setattr__(self, attr, value):
		object.__getattribute__(self, "expires")[attr] = time.time() + object.__getattribute__(self, "delay")
		self[attr] = value

	def __getattr__(self, attr):
		if time.time() < object.__getattribute__(self, "expires").get(attr, 0):
			return self[attr]
		else:
			object.__getattribute__(self, "expires").pop(attr, None)
			self.pop(attr, None)
			raise AttributeError("%s value expired" % attr)

CACHE = Cache()


class JsonDict(dict):

	def __init__(self, name, folder=None):
		self.__name = name
		self.__folder = folder
		dict.__init__(self, loadJson(self.__name, self.__folder))

	def __setitem__(self, *args, **kwargs):
		dict.__setitem__(self, *args, **kwargs)
		self.flush()
		
	def __delitem__(self, *args, **kwargs):
		dict.__delitem__(self, *args, **kwargs)
		self.flush()

	def pop(self, *args, **kwargs):
		return dict.pop(self,  *args, **kwargs)
		self.flush()

	def flush(self):
		dumpJson(self, self.__name, self.__folder)


def getPeer():
	"""
	Try to get a valid peer from cache. If no peer found, compute one and from
	the highest height and store it.
	"""

	try:
		# try to get a peer from cache
		return CACHE.peer
	except AttributeError:
		# load the root config file
		root = loadJson("root.json")
		# exit if no root config file
		if root == {}:
			logMsg("zen package is not configured")
			raise Exception("zen package is not configured")
		# load peers from env folder
		peers = loadJson("peers.json", root["env"])
		height, peer = 0, None
		# get the best peer available
		for elem in peers["list"]:
			tmp = "http://%(ip)s:%(port)d" % elem
			try:
				h = requests.get("/".join([tmp,"api","blocks","getHeight"]), verify=True, timeout=5).json().get("height", 0)
				if h > height:
					height = h
					peer = tmp
			except requests.exceptions.ConnectionError:
				pass
		CACHE.peer = peer if peer else "http://localhost:%(port)d" % elem
		return CACHE.peer


def restGet(*args, **kwargs):
	path = "/".join([getPeer()]+list(args))
	return requests.get(path, params=kwargs, verify=True).json()


def restPost(*args, **kwargs):
	pass
	# path = "/".join([getPeer()]+list(args))
	# return requests.post(path, params=kwargs, verify=True).json()


def loadJson(name, folder=None):
	filename = os.path.join(JSON, name if not folder else os.path.join(folder, name))
	if os.path.exists(filename):
		with io.open(filename) as in_:
			return json.load(in_)
	else:
		return {}


def dumpJson(data, name, folder=None):
	filename = os.path.join(JSON, name if not folder else os.path.join(folder, name))
	try: os.makedirs(os.path.dirname(filename))
	except OSError: pass
	with io.open(filename, "w" if PY3 else "wb") as out:
		json.dump(data, out, indent=4)


def logMsg(msg, logname=None):
	if logname:
		logfile = os.path.join(LOG, logname)
		try:
			os.makedirs(os.path.dirname(logfile))
		except OSError:
			pass
		stdout = io.open(logfile, "a")
	else:
		stdout = sys.stdout
	stdout.write(">>> [%s] %s\n" % (datetime.datetime.now().strftime("%x %X"), msg))
	stdout.flush()
	return stdout.close() if logname else None


def chooseItem(msg, *elem):
	n = len(elem)
	if n > 1:
		sys.stdout.write(msg + "\n")
		for i in range(n):
			sys.stdout.write("    %d - %s\n" % (i + 1, elem[i]))
		sys.stdout.write("    0 - quit\n")
		i = -1
		while i < 0 or i > n:
			try:
				i = input("Choose an item: [1-%d]> " % n)
				i = int(i)
			except ValueError:
				i = -1
			except KeyboardInterrupt:
				return False
		if i == 0:
			return False
		return elem[i - 1]
	elif n == 1:
		return elem[0]
	else:
		sys.stdout.write("Nothing to choose...\n")
		return False


def init():
	root = loadJson("root.json")

	# first ask network folder
	node_folder = ""
	while not os.path.exists(node_folder):
		try: node_folder = os.path.abspath(input("> enter node folder: "))
		except KeyboardInterrupt: return
	blockchain_folder = os.path.join(node_folder, "packages", "crypto", "lib", "networks")
	blockchain = chooseItem("select blockchain:", *list(os.walk(blockchain_folder))[0][1])

	if not blockchain:
		logMsg("node configuration skipped")
		return
	
	networks_folder = os.path.join(blockchain_folder, blockchain)
	network = chooseItem("select network:", *[os.path.splitext(f)[0] for f in list(os.walk(networks_folder))[0][-1] if f.endswith(".json")])
	
	if not network:
		logMsg("node configuration skipped")
		return

	root["env"] = os.path.expanduser(os.path.join("~", ".%s"%blockchain, "config"))
	root["config"] = os.path.join(networks_folder, "%s.json"%network)
	logMsg("node configuration saved in %s" % os.path.join(JSON, "root.json"))

	dumpJson(root, "root.json")

