# -*- encoding:utf-8 -*-
import os
import sys
import optparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import zen
import zen.tbw


def initialize():
	zen.init()
	zen.tbw.init()


def configure(username, **parameters):
	zen.tbw.init(**parameters)


def launch():
	app = os.path.abspath(os.path.join(zen.__path__[0], "app", "app.py"))
	print(os.path.dirname(app))
	os.environ["FLASK_APP"] = os.path.join(zen.__path__[0], "app", "app.py")
	os.system('daemon --name=tbw --output=%s --command="python -m flask run --host=0.0.0.0" --chdir=%s' % (
		os.path.expanduser("~/flask.log"),
		os.path.dirname(app)
	))


def stop():
	os.system('daemon --name=tbw --stop')


def relaunch():
	stop()
	launch()


if __name__ == "__main__":

	tbw = zen.loadJson("tbw.json")

	# catch command line
	parser = optparse.OptionParser()
	(zen.OPTIONS, args) = parser.parse_args()

	# set the default command
	if not len(args):
		args = ["configure"]
	elif len(args) > 1:
		parser.print_help()
		raise Exception("Only one command can be performed")

	func = getattr(sys.modules[__name__], args[0])
	if callable(func):
		func()
