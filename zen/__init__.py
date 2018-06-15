# -*- encoding:utf-8 -*-

import os
import io
import sys
import json
import datetime

# configure pathes
ROOT = os.path.abspath(os.path.dirname(__file__))
DATA = os.path.abspath(os.path.join(ROOT, "data"))
JSON = os.path.abspath(os.path.join(ROOT, "json"))
CFG = os.path.abspath(os.path.join(ROOT, "cfg"))
LOG = os.path.abspath(os.path.join(ROOT, "log"))

# register python familly
PY3 = True if sys.version_info[0] >= 3 else False

input = raw_input if not PY3 else input


def loadJson(name, folder=None):
	filename = os.path.join(JSON, "%s.json"%name if not folder else os.path.join(folder, "%s.json"%name))
	if os.path.exists(filename):
		with io.open(filename) as in_:
			return json.load(in_)
	else:
		return {}


def dumpJson(data, name, folder=None):
	filename = os.path.join(JSON, "%s.json"%name if not folder else os.path.join(folder, "%s.json"%name))
	try: os.makedirs(os.path.dirname(filename))
	except OSError: pass
	with io.open(filename, "w" if PY3 else "wb") as out:
		json.dump(data, out, indent=4)


def logMsg(msg, logname=None):
	stdout = io.open(os.path.join(LOG, "%s.log"%logname), "w") if logname else sys.stdout
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
	root = loadJson("root")

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

	dumpJson(root, "root")
