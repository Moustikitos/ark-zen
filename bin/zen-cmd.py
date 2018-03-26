# -*- encoding:utf-8 -*-
import os
import sys
import optparse
import zen.chk

from zen.cmn import setup, configure
from zen.chk import check, rebuild, restart
from zen.tbw import spread, extract, forgery
from zen.pay import build, pay


def launch():
	print(os.path.join(os.path.join(zen.__path__[0], "app")))
	os.environ["FLASK_APP"] = os.path.join(zen.__path__[0], "app", "app.py")
	os.system('daemon --name=tbw --output=%s --command="python -m flask run --host=0.0.0.0" --chdir=%s' % (
		os.path.expanduser("~/flask.log"),
		os.path.join(os.path.join(zen.__path__[0], "app")),
	))


def stop():
	os.system('daemon --name=tbw --stop')


def relaunch():
	stop()
	launch()


if __name__ == "__main__":

	# catch command line
	parser = optparse.OptionParser()
	parser.add_option("-s", "--share",        dest="share",       type="float",  help="pool sharing",                  metavar="RATE")
	parser.add_option("-t", "--threshold",    dest="threshold",   type="float",  help="threshold to initiate payment", metavar="THRESHOLD")
	parser.add_option("-f", "--fund",         dest="funds",       type="string", help="address where you keep funds",  metavar="ADDRESS")
	parser.add_option("-v", "--vendor-field", dest="vendorField", type="string", help="Message you want to associate", metavar="64-CHAR MESSAGE")
	parser.add_option("-e", "--excludes",     dest="excludes",    type="string", help="Addresses to exclude",          metavar="COMA-SEPARATED-ADDRESS LIST")

	(zen.cmn.OPTIONS, args) = parser.parse_args()

	# set the default command
	if not len(args):
		raise Exception("No command to be performed")
	elif len(args) > 1:
		parser.print_help()
		raise Exception("Only one command can be performed")

	func = getattr(sys.modules[__name__], args[0])
	if callable(func):
		func()
