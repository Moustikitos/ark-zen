# -*- coding:utf-8 -*-

import os
import io
import sys
import json
import datetime

# register python familly
PY3 = sys.version_info[0] >= 3
if not PY3:
    input = raw_input

# configuration pathes
ROOT = os.path.abspath(os.path.dirname(__file__))
JSON = os.path.abspath(os.path.join(ROOT, ".json"))
DATA = os.path.abspath(os.path.join(ROOT, "app", ".data"))
TBW = os.path.abspath(os.path.join(ROOT, "app", ".tbw"))
LOG = os.path.abspath(os.path.join(ROOT, "app", ".log"))

ENV = None
API_PEER = None
WEBHOOK_PEER = None
PUBLIC_IP = None


def loadJson(name, folder=None):
    filename = os.path.join(JSON if not folder else folder, name)
    if os.path.exists(filename):
        with io.open(filename) as in_:
            data = json.load(in_)
    else:
        data = {}
    # hack to avoid "OSError: [Errno 24] Too many open files"
    # with pypy
    try:
        in_.close()
        del in_
    except Exception:
        pass
    #
    return data


def dumpJson(data, name, folder=None):
    filename = os.path.join(JSON if not folder else folder, name)
    try:
        os.makedirs(os.path.dirname(filename))
    except OSError:
        pass
    with io.open(filename, "w" if PY3 else "wb") as out:
        json.dump(data, out, indent=4)
    # hack to avoid "OSError: [Errno 24] Too many open files"
    # with pypy
    try:
        out.close()
        del out
    except Exception:
        pass
    #


def dropJson(name, folder=None):
    filename = os.path.join(JSON if not folder else folder, name)
    if os.path.exists(filename):
        os.remove(filename)


def logMsg(msg, logname=None, dated=False):
    if logname:
        logfile = os.path.join(LOG, logname)
        try:
            os.makedirs(os.path.dirname(logfile))
        except OSError:
            pass
        stdout = io.open(logfile, "a")
    else:
        stdout = sys.stdout

    stdout.write(
        ">>> " +
        (
            "[%s] " % datetime.datetime.now().strftime("%x %X")
            if dated else ""
        ) +
        "%s\n" % msg
    )
    stdout.flush()

    if logname:
        return stdout.close()


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
                sys.stdout.write("\n")
                sys.stdout.flush()
                return False
        if i == 0:
            return None
        return elem[i - 1]
    elif n == 1:
        return elem[0]
    else:
        sys.stdout.write("Nothing to choose...\n")
        return False


def chooseMultipleItem(msg, *elem):
    """
    Convenience function to allow the user to select multiple items from a
    list.
    """
    n = len(elem)
    if n > 0:
        sys.stdout.write(msg + "\n")
        for i in range(n):
            sys.stdout.write("    %d - %s\n" % (i + 1, elem[i]))
        sys.stdout.write("    0 - quit\n")
        indexes = []
        while len(indexes) == 0:
            try:
                indexes = input("Choose items: [1-%d or all]> " % n)
                if indexes == "all":
                    indexes = [i + 1 for i in range(n)]
                elif indexes == "0":
                    indexes = []
                    break
                else:
                    indexes = [
                        int(s) for s in indexes.strip().replace(
                            " ", ","
                        ).split(",") if s != ""
                    ]
                    indexes = [r for r in indexes if 0 < r <= n]
            except Exception:
                indexes = []
        return [elem[i-1] for i in indexes]

    sys.stdout.write("Nothing to choose...\n")
    return []
