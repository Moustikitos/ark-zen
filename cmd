#! /usr/bin/env python
# -*- encoding:utf-8 -*-

import os
import sys
import optparse

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

import zen
import zen.tbw


def start_tbw():
	os.system("""
if [ "$(pm2 id zen-tbw) " = "[]" ]; then
	cd %(abspath)s
    pm2 start app.json
else
    pm2 restart zen-tbw
fi
""" % {"abspath": os.path.abspath(os.path.dirname(__file__))}
)


def stop_tbw():
	os.chdir(os.path.abspath(os.path.dirname(__file__)))
	os.system("""
if [ "$(pm2 id zen-tbw) " != "[]" ]; then
	cd %(abspath)s
    pm2 stop zen-tbw
fi
""" % {"abspath": os.path.abspath(os.path.dirname(__file__))}
)


def initialize():
	zen.init()
	zen.tbw.init()


def launch_payroll(username):
	zen.tbw.extract(username)
	zen.tbw.dumpRegistry(username)
	zen.tbw.broadcast(username)


def configure(username=None, **options):
	if username:
		zen.tbw.init(username=username, **options)
	else:
		zen.tbw.init(**options)
	

if __name__ == "__main__":
	tbw = zen.loadJson("tbw.json")

	# catch command line
	parser = optparse.OptionParser()
	# -f --funds
	# -s --symbol
	# -d --delay
	# -e --excludes
	# -u --username
	(options, args) = parser.parse_args()

	if len(args):
		func = getattr(sys.modules[__name__], args[0].replace("-", "_"))
		if callable(func):
			func()
