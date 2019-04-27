# -*- encoding:utf-8 -*-
import os
import time
import threading

import zen
import zen.tbw
import zen.misc
import zen.app

DAEMON = False


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
	global DAEMON
	data = zen.loadJson("svg-maker.json")
	data["stop"] = False
	zen.dumpJson(data, "svg-maker.json")
	DAEMON = loop()
	zen.misc.notify("SVG maker started !")
	try:
		while not DAEMON.is_set():
			delegates = dict(
				[username, dict(zen.loadJson(username+".json", zen.JSON), **zen.dposlib.rest.GET.api.delegates(username, returnKey="data"))] for \
				username in [name.split("-")[0] for name in os.listdir(zen.JSON) if name.endswith("-webhook.json")]
			)
			[zen.misc.chartAir(delegates[username]["share"], 50, username, zen.dposlib.util.misc.deltas()["real blocktime"]) for username in delegates]
			[zen.misc.generateChart(username) for username in delegates]
			time.sleep(zen.rest.cfg.blocktime * zen.rest.cfg.delegate)
	except KeyboardInterrupt:
		zen.misc.notify("SVG maker stoped !")


def stop():
	data = zen.loadJson("svg-maker.json")
	data["stop"] = True
	zen.dumpJson(data, "svg-maker.json")


@setInterval(60)
def loop():
	global DAEMON
	data = zen.loadJson("svg-maker.json")
	if data["stop"] and isinstance(DAEMON, threading._Event):
		DAEMON.set()
		zen.misc.notify("SVG maker stoped !")


if __name__ == "__main__":
	start()
