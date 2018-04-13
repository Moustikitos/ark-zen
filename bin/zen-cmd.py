# -*- encoding:utf-8 -*-
import os
import sys
import optparse
import zen.chk

from zen.cmn import setup, configure
from zen.chk import check, rebuild, restart
from zen.tbw import spread, extract, forgery
from zen.pay import build, pay


sys.path.append(os.path.expanduser("~/zen"))


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
	parser.add_option("-s", "--share", dest="share", type="float", metavar="RATE", help="Pool sharing rate. Float number >=0. and <= 1.0")
	parser.add_option("-t", "--threshold", dest="threshold", type="float", metavar="THRESHOLD", help="Threshold to initiate payment, transaction fees included.")
	parser.add_option("-f", "--fund", dest="funds", type="string", metavar="ADDRESS", help="Address where you keep funds, the part not distributed to voters.")
	parser.add_option("-v", "--vendor-field", dest="vendorField", metavar="MESSAGE", type="string", help="Message you want to associate.")
	parser.add_option("-e", "--excludes", dest="excludes", type="string", metavar="ADDRESS001,ADDRESS002,...ADDRESSNNN", help="Coma-separated list of addresses to exclude.")
	parser.add_option("-k", "--keep-fees",    dest="targeting",   action="store_true")

	(zen.cmn.OPTIONS, args) = parser.parse_args()

	# set the default command
	if not len(args):
		args = ["configure"]
		# raise Exception("No command to be performed")
	elif len(args) > 1:
		parser.print_help()
		raise Exception("Only one command can be performed")

	func = getattr(sys.modules[__name__], args[0])
	if callable(func):
		func()
