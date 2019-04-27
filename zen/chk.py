# -*- encoding:utf-8 -*-
import time
import threading

import zen
import zen.misc

DAEMON = False
STATUS = SEED_STATUS = IS_SYNCING = {}

def setInterval(interval):
	""" threaded decorator
	>>> @setInterval(10)
	... def tick():
	...     print("Tick")
	>>> event = tick() # print 'Tick' every 10 sec
	>>> type(event)
	<class 'threading.Event'>
	>>> event.set() # stop printing 'Tick' every 10 sec
	"""
	def decorator(function):
		"""Main decorator function."""

		def wrapper(*args, **kwargs):
			"""Helper function to create thread."""

			stopped = threading.Event()

			# executed in another thread
			def loop():
				"""Thread entry point."""

				# until stopped
				while not stopped.wait(interval):
					function(*args, **kwargs)

			t = threading.Thread(target=loop)
			# stop if the program exits
			t.daemon = True
			t.start()
			return stopped
		return wrapper
	return decorator


def start():
	global DAEMON, STATUS, IS_SYNCING, SEED_STATUS
	data = zen.loadJson("fork-check.json")
	data["stop"] = False
	zen.dumpJson(data, "fork-check.json")
	DAEMON = loop()
	zen.misc.notify("Node checker started !")
	try:
		while not DAEMON.is_set():
			time.sleep(60)
			if IS_SYNCING == {} or STATUS == {} or SEED_STATUS == {}:
				pass
			else:
				if not STATUS["synced"]:
					data["issue"] = True
					zen.dumpJson(data, "fork-check.json")
					if IS_SYNCING["syncing"]:
						zen.misc.notify("Your node is syncing... %d blocks from network height" % IS_SYNCING["blocks"])
					else:
						zen.misc.notify("Your node is not synced and seems stoped at height %d, network is at height %d" % (
							IS_SYNCING["height"],
							SEED_STATUS["now"]
						))
				elif data.get("issue", False):
					data.pop("issue", False)
					zen.dumpJson(data, "fork-check.json")
					zen.misc.notify("Your node had recovered network height %d" % STATUS["now"])
			zen.logMsg(zen.json.dumps(STATUS))
	except KeyboardInterrupt:
		zen.misc.notify("Node checker stoped !")


def stop():
	data = zen.loadJson("fork-check.json")
	data["stop"] = True
	zen.dumpJson(data, "fork-check.json")


@setInterval(60)
def loop():
	global DAEMON, STATUS, IS_SYNCING, SEED_STATUS
	data = zen.loadJson("fork-check.json")
	if not data["stop"]:
		IS_SYNCING = zen.rest.GET.api.node.syncing(peer="http://127.0.0.1:4003").get("data", {})
		# {u'data': {u'syncing': False, u'blocks': 0, u'id': u'5652062772472552437', u'height': 7453939}}
		STATUS = zen.rest.GET.api.node.status(peer="http://127.0.0.1:4003").get("data", {})
		# {u'data': {u'synced': True, u'now': 7453939, u'blocksCount': 0}}
		SEED_STATUS = zen.rest.GET.api.node.status(peer="https://explorer.ark.io:8443").get("data", {})
		# {u'data': {u'synced': True, u'now': 7453939, u'blocksCount': -1}}
	elif isinstance(DAEMON, threading._Event):
		DAEMON.set()
		zen.misc.notify("Node checker stoped !")


if __name__ == "__main__":
	start()
