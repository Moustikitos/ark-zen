# -*- coding: utf-8 -*-
# BASIC INOUT/OUTPUT MODULE

import io
import os
import sys
import zen
import time
import socket
import shutil
import getpass

import dposlib
import dposlib.rest
import dposlib.net

if not zen.PY3:
    input = raw_input


# OS INTERACTION

def deploy(host="0.0.0.0", port=5000):
    normpath = os.path.normpath
    executable = normpath(sys.executable)
    gunicorn_conf = os.path.normpath(
        os.path.abspath(
            os.path.expanduser("~/ark-zen/gunicorn.conf.py")
        )
    )

    with io.open("./zen.service", "w") as unit:
        unit.write(u"""[Unit]
Description=Zen TBW server
After=network.target

[Service]
User=%(usr)s
WorkingDirectory=%(wkd)s
Environment=PYTHONPATH=%(path)s:${HOME}/dpos
ExecStart=%(bin)s/gunicorn zen.app:app \
--bind=%(host)s:%(port)d --workers=5 --timeout 10 --access-logfile -
Restart=always

[Install]
WantedBy=multi-user.target
""" % {
            "host": host,
            "port": port,
            "usr": os.environ.get("USER", "unknown"),
            "wkd": normpath(sys.prefix),
            "path": normpath(os.path.dirname(zen.__path__[0])),
            "bin": os.path.dirname(executable),
        })

    if os.system("%s -m pip show gunicorn" % executable) != "0":
        os.system("%s -m pip install gunicorn" % executable)
    os.system("chmod +x ./zen.service")
    os.system("sudo cp %s %s" % (gunicorn_conf, normpath(sys.prefix)))
    os.system("sudo mv --force ./zen.service /etc/systemd/system")
    os.system("sudo systemctl daemon-reload")
    if not os.system("sudo systemctl restart zen"):
        os.system("sudo systemctl start zen")


def start_pm2_app(appname):
    os.system(r'''
if echo "$(pm2 id %(appname)s | tail -n 1)" | grep -qE "\[\]"; then
    yarn exec ark %(appname)s:start
else
    echo "(re)starting %(appname)s..."
    pm2 restart %(appname)s -s
fi
''' % {"appname": appname}
    )


def stop_pm2_app(appname):
    os.system(r'''
if ! echo "$(pm2 id %(appname)s | tail -n 1)" | grep -qE "\[\]"; then
    echo stoping %(appname)s...
    pm2 stop %(appname)s -s
fi
''' % {"appname": appname}
    )


def printNewLine():
    sys.stdout.write("\n")
    sys.stdout.flush()


# SYSTEM INTERACTIONS

def loadEnv(pathname):
    with io.open(pathname, "r") as environ:
        lines = [li.strip() for li in environ.read().split("\n")]
    result = {}
    for line in [li for li in lines if li != ""]:
        key, value = [li.strip() for li in line.split("=")]
        try:
            result[key] = int(value)
        except Exception:
            result[key] = value
    return result


def dumpEnv(env, pathname):
    shutil.copy(pathname, pathname+".bak")
    with io.open(pathname, "wb") as environ:
        for key, value in sorted(
            [(k, v) for k, v in env.items()], key=lambda e: e[0]
        ):
            line = "%s=%s\n" % (key, value)
            environ.write(line.encode("utf-8"))


def setup(clear=False):
    # load root.json file. If not exists, root is empty dict
    root = zen.loadJson("root.json")
    if clear:
        root.clear()
        root["config_folder"] = ""
    # first configuration
    if root.get("config_folder", "") == "":
        if os.path.isdir(os.path.expanduser("~/.config/ark-core")):
            root["config_folder"] = os.path.abspath(
                os.path.expanduser("~/.config/ark-core")
            )
        else:
            ans = "None"
            try:
                while ans not in "nNyY":
                    ans = input(
                        "Is zen installed on a running node ?[Y/n] "
                    )
            except KeyboardInterrupt:
                zen.logMsg("\nConfiguration aborted...")
                return

            if ans in "yY":
                while not os.path.exists(root["config_folder"]):
                    try:
                        root["config_folder"] = os.path.abspath(
                            input("Enter config folder: ")
                        )
                    except KeyboardInterrupt:
                        zen.logMsg("\nConfiguration aborted...")
                        return
            else:
                root["config_folder"] = None

    if root["config_folder"] is not None:
        network = zen.chooseItem(
            "select network:", *list(os.walk(root["config_folder"]))[0][1]
        )
        if not network:
            zen.logMsg("Configuration aborted...")
            return
        root["name"] = network
        root["env"] = os.path.join(root["config_folder"], network, ".env")

        blockchain = zen.chooseItem(
            "Select blockchain running on node:",
            *[name for name in dir(dposlib.net) if not name.startswith("_")]
        )
        if not blockchain:
            zen.logMsg("Configuration aborted...")
            return
        root["blockchain"] = blockchain

        zen.ENV = loadEnv(root["env"])
        if not zen.ENV.get("CORE_WEBHOOKS_ENABLED", "") == "true":
            zen.ENV["CORE_WEBHOOKS_ENABLED"] = "true"
            zen.ENV["CORE_WEBHOOKS_HOST"] = "0.0.0.0"
            zen.ENV["CORE_WEBHOOKS_PORT"] = "4004"
            dumpEnv(zen.ENV, root["env"])
            if input("Relay have to be restarted. "
                     "Restart now ?[Y:n] ") in "yY":
                start_pm2_app("relay")

        root["webhook"] = "http://127.0.0.1:%s" % zen.ENV.get(
            "CORE_WEBHOOKS_PORT", "4004"
        )
        root["api"] = "http://127.0.0.1:%s" % zen.ENV.get(
            "CORE_API_PORT", "4003"
        )
    else:
        root["webhook"] = "127.0.0.1:4004"
        try:
            while dposlib.rest.GET.api.webhooks(
                peer="http://"+root["webhook"], timeout=2
            ).get("status", False) != 200:
                root["webhook"] = input("Peer address for webhook submition: ")
        except KeyboardInterrupt:
            zen.logMsg("\nConfiguration aborted...")
            return
        root["webhook"] = "http://" + root["webhook"]

        root["api"] = "127.0.0.1:4003"
        try:
            while "data" not in dposlib.rest.GET.api.blockchain(
                peer="http://"+root["api"], timeout=2
            ):
                root["api"] = input("Peer address for API requests: ")
        except KeyboardInterrupt:
            zen.logMsg("\nConfiguration aborted...")
            return
        root["api"] = "http://" + root["api"]

        blockchain = zen.chooseItem(
            "Select blockchain running on peer:",
            *[name for name in dir(dposlib.net) if not name.startswith("_")]
        )
        if not blockchain:
            zen.logMsg("Configuration aborted...")
            return
        root["blockchain"] = blockchain

    zen.logMsg("Configuration done.")
    zen.dumpJson(root, "root.json")


def load():
    zen.ENV = None
    zen.PUBLIC_IP = None
    zen.WEBHOOK_PEER = None
    zen.API_PEER = None

    root = zen.loadJson("root.json")
    if "env" in root:
        zen.ENV = loadEnv(root["env"])
        zen.PUBLIC_IP = '127.0.0.1'
    if "webhook" in root:
        zen.WEBHOOK_PEER = root["webhook"]
    if "api" in root:
        zen.API_PEER = root["api"]

    dposlib.rest.use(root.get("blockchain", "dark"))

    if zen.PUBLIC_IP != '127.0.0.1':
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            zen.PUBLIC_IP = s.getsockname()[0]
        except Exception:
            zen.PUBLIC_IP = '127.0.0.1'
        finally:
            s.close()


def configure(**kwargs):
    if not len(kwargs):
        root = zen.loadJson("root.json")
        if "env" in root:
            delegates = zen.loadJson(
                "delegates.json", os.path.dirname(root["env"])
            )
            for secret in delegates["secrets"]:
                setDelegate(dposlib.core.crypto.getKeys(secret)["publicKey"])

    elif "username" in kwargs:
        username = kwargs.pop("username")
        if getPublicKeyFromUsername(username):
            config = zen.loadJson("%s.json" % username)
            if not len(config):
                if not setDelegate(
                    username, peer=kwargs.get("webhook_peer", None)
                ):
                    return
            # reload JSON config file
            # config = zen.loadJson("%s.json" % username)
            config.update(zen.loadJson("%s.json" % username), **kwargs)
            zen.dumpJson(config, "%s.json" % username)
            zen.logMsg("%s delegate set" % username)
        else:
            zen.logMsg("can not find delegate %s" % username)


def removeDelegate(username):
    webhook = zen.loadJson("%s-webhook.json" % username)
    if len(webhook):
        resp = deleteWebhook(webhook["id"], peer=webhook["peer"])
        if resp.get("status", 500) < 300:
            zen.dropJson("%s-webhook.json" % username)
            zen.dropJson("%s.json" % username)
            if input("Remove %s data ?[Y/n] " % username) in "yY":
                shutil.rmtree(os.path.join(zen.ROOT, "app", ".data", username))
                shutil.rmtree(os.path.join(zen.ROOT, "app", ".tbw", username))
    else:
        zen.logMsg("%s not found" % username)


def waitForPeer(peer):
    try:
        while dposlib.rest.GET(
            peer=peer, timeout=2
        ).get("status", False) != 200:
            time.sleep(2)
            zen.logMsg("Wating for peer %s..." % peer)
        return True
    except KeyboardInterrupt:
        return False


# BLOCKCHAIN INTERACTIONS

def askPrivateKey(msg, puk):
    keys = dposlib.core.crypto.getKeys("01")
    while keys["publicKey"] != puk:
        try:
            keys = dposlib.core.crypto.getKeys(getpass.getpass(msg))
        except KeyboardInterrupt:
            return False
    return keys["privateKey"]


def getPublicKeyFromUsername(username):
    req = dposlib.rest.GET.api.delegates(username)
    return req.get("data", {}).get("publicKey", False)


def getUsernameFromPublicKey(publicKey):
    req = dposlib.rest.GET.api.delegates(publicKey)
    return req.get("data", {}).get("username", False)


def getUsernameKeys(username):
    module = sys.modules[__name__]

    config = zen.loadJson("%s.json" % username)
    hide = False
    if "#1" in config:
        setattr(module, "_%s_#1" % username, config.pop("#1"))
        hide = True
    if "#2" in config:
        setattr(module, "_%s_#2" % username, config.pop("#2"))
        hide = True
    if hide:
        zen.dumpJson(config, "%s.json" % username)

    H1 = module.__dict__.get("_%s_#1" % username, None)
    H2 = module.__dict__.get("_%s_#2" % username, None)

    return (
        H1 if H1 is None else dposlib.core.crypto.getKeys(H1),
        H2 if H2 is None else dposlib.core.crypto.getKeys(H2)
    )


def pushBackKeys():
    module = sys.modules[__name__]
    for key, value in [
        (k, v) for k, v in module.__dict__.items() if k[-2:] in "#1#2"
    ]:
        username, num = key.replace("_", "").split("#")
        num = "#" + num
        config = zen.loadJson("%s.json" % username)
        config[num] = value
        zen.dumpJson(config, "%s.json" % username)


def transactionApplied(id):
    data = dposlib.rest.GET.api.transactions(id).get("data", {})
    if isinstance(data, dict):
        return data.get("confirmations", 0) >= 10
    else:
        return False


def delegateIsForging(username):
    dlgt = dposlib.rest.GET.api.delegates(username).get("data", {})
    rank = dlgt.get("rank", dlgt.get("attributes", {}).get("rank", -1))
    return rank != -1 and rank <= zen.rest.cfg.activeDelegates


def setWebhook(publicKey):
    data = dposlib.rest.POST.api.webhooks(
        peer=zen.WEBHOOK_PEER,
        event="block.forged" if zen.PUBLIC_IP == "127.0.0.1" else
              "block.applied",
        target="http://%s:5000/block/forged" % zen.PUBLIC_IP,
        conditions=[{
            "key": "generatorPublicKey",
            "condition": "eq",
            "value": publicKey
        }]
    )
    return data.get("data", data)


def deleteWebhook(id, peer):
    data = dposlib.rest.DELETE.api.webhooks(id, peer=peer)
    return data.get("data", data)


def setDelegate(uname_or_puk, peer=None):
    peer = zen.WEBHOOK_PEER if peer is None else peer
    account = dposlib.rest.GET.api.wallets(uname_or_puk).get("data", {})
    attributes = account.get("attributes", {})

    if attributes.get("delegate", False):
        username = attributes["delegate"]["username"]
        config = zen.loadJson("%s.json" % username)
        config["publicKey"] = account["publicKey"]

        if "#1" not in config:
            config["#1"] = askPrivateKey(
                "Enter first secret: ", config["publicKey"]
            )
        if "secondPublicKey" in attributes:
            config["#2"] = askPrivateKey(
                "Enter second secret: ", attributes["secondPublicKey"]
            )

        overwrite = input("Overwrite previous webhoook?[Y/n] ") \
            if os.path.exists(
                os.path.join(zen.JSON, "%s-webhook.json" % username)
            ) else "y"

        if overwrite in "yY":
            if not waitForPeer(peer):
                zen.logMsg("%s peer unreachable" % peer)
                return False
            webhook = setWebhook(config["publicKey"])
            webhook["peer"] = peer
            if "token" in webhook:
                zen.dumpJson(webhook, "%s-webhook.json" % username)
            else:
                zen.logMsg(
                    "An error occured with webhook subscription:\n%s" %
                    webhook
                )

        zen.dumpJson(config, "%s.json" % username)

    else:
        zen.logMsg(
            "%s seems not to be a valid delegate username or public key" %
            uname_or_puk
        )
        return False

    return True
