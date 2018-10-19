# -*- encoding:utf-8 -*-
import os
import sys
import optparse

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

import zen
import zen.tbw


def initialize():
	zen.init()
	zen.tbw.init()


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
