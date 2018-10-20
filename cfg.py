# -*- encoding:utf-8 -*-
import os
import sys
import optparse

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

import zen
import zen.tbw


def start():
	os.chdir(os.path.abspath(os.path.dirname(__file__)))
	os.system("""
if [ "$(pm2 id zen-tbw) " = "[]" ]; then
    pm2 start app.json
else
    pm2 restart zen-tbw
fi
""")


def stop():
	os.chdir(os.path.abspath(os.path.dirname(__file__)))
	os.system("""
if [ "$(pm2 id zen-tbw) " = "[]" ]; then
    pm2 stop zen-tbw
fi
""")


def initialize():
	zen.init()
	zen.tbw.init()


if __name__ == "__main__":
	tbw = zen.loadJson("tbw.json")

	# catch command line
	parser = optparse.OptionParser()
	# -f --funds
	# -s --symbol
	# -d --delay
	# -e --excludes
	(options, args) = parser.parse_args()

	if len(args):
		func = getattr(sys.modules[__name__], args[0])
		if callable(func):
			func()
