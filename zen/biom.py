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
import hashlib
import subprocess

import dposlib
import dposlib.rest
import dposlib.net


###################
# OS INTERACTIONS #
###################

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


def identify_app():
    appnames = {}
    for name in subprocess.check_output(
        "pm2 ls -m|grep +---|grep -oE '[^ ]+$'", shell=True
    ).decode("utf-8").split():
        if "core" in name:
            appnames["relay"] = appnames["forger"] = name
        else:
            if "relay" in name:
                appnames["relay"] = name
            if "forger" in name:
                appnames["forger"] = name
    return appnames


def start_pm2_app(appname):
    return os.system(f'''
if ! echo "$(pm2 id {appname} | tail -n 1)" | grep -qE "\\[\\]"; then
    echo "restarting {appname}..."
    pm2 restart {appname} -s
fi''')


def stop_pm2_app(appname):
    return os.system(f'''
if ! echo "$(pm2 id {appname} | tail -n 1)" | grep -qE "\\[\\]"; then
    echo stoping {appname}...
    pm2 stop {appname} -s
fi''')


def send_signal(signal, pid):
    return os.system(r'sudo kill -s%s %s' % (signal, pid))


def send_signal_grep(signal, grep_arg):
    return os.system(r'''
sudo kill -s%s $(
    pgrep -a -u $USER,daemon|grep '%s'|sed 's/\ / /'|awk 'NR==1{print $1}'
)
''' % (signal, grep_arg.replace(r"'", r"\'")))


def archive_data(folder=None, extension=".tar.bz2"):
    return os.system(r'''
cd %(path)s
/bin/tar -caf data-bkp.%(timestamp)d%(ext)s *.db app/.tbw app/.data
''' % {
        "path": os.path.abspath(zen.__path__[0]) if folder is None else folder,
        "ext": extension,
        "timestamp": time.time()
    })


def printNewLine():
    sys.stdout.write("\n")
    sys.stdout.flush()


#######################
# SYSTEM INTERACTIONS #
#######################

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


def setup(clear=False, extern=False):
    # load root.json file. If not exists, root is empty dict
    root = zen.loadJson("root.json")
    if "appnames" not in root:
        root["appnames"] = identify_app()
    # delete all keys from root dict if asked
    if clear:
        root.clear()
        root["config-folder"] = None if extern else ""
    # first configuration if no config-folder, it is set to "" because None is
    # used when zen is not running on a blockchain node
    if root.get("config-folder", "") == "":
        # if ark config directory found
        if os.path.isdir(os.path.expanduser("~/.config/ark-core")):
            root["config-folder"] = os.path.abspath(
                os.path.expanduser("~/.config/ark-core")
            )
        else:
            ans = "None"
            try:
                while ans not in "nNyY":
                    ans = input("Is zen installed on a running node ?[Y/n] ")
            except KeyboardInterrupt:
                zen.logMsg("\nconfiguration aborted...")
                return

            if ans in "yY":
                while not os.path.exists(root.get("config-folder", "")):
                    try:
                        root["config-folder"] = os.path.abspath(
                            input("Enter config folder: ")
                        )
                    except KeyboardInterrupt:
                        zen.logMsg("\nconfiguration aborted...")
                        return
            else:
                root["config-folder"] = None
    # if zen is running on a blockchain node
    if root["config-folder"] is not None:
        # get folder containing node configuration
        network = zen.chooseItem(
            "select network:", *list(os.walk(root["config-folder"]))[0][1]
        )
        if not network:
            zen.logMsg("configuration aborted...")
            return
        root["name"] = network
        root["env"] = os.path.join(root["config-folder"], network, ".env")
        root["blockchain"] = zen.loadJson(
            "config.json", folder=os.path.join(root["config-folder"], network)
        ).get("token", None)
        # load .env file and enable webhooks if disabled
        if not os.path.exists(root["env"]):
            zen.logMsg("no env file available...")
            return
        zen.ENV = loadEnv(root["env"])
        if not zen.ENV.get("CORE_WEBHOOKS_ENABLED", "") == "true":
            zen.ENV["CORE_WEBHOOKS_ENABLED"] = "true"
            zen.ENV["CORE_WEBHOOKS_HOST"] = "0.0.0.0"
            zen.ENV["CORE_WEBHOOKS_PORT"] = "4004"
            dumpEnv(zen.ENV, root["env"])
            if input(
                "webhooks are now enabled, restart relay ?[Y/n] "
            ) in "yY":
                start_pm2_app(identify_app().get("relay"))
    # if zen is not running on a blockchain node
    else:
        # get webhook subscription peer address
        try:
            root["webhook"] = input("Peer address for webhook submition: ")
            while dposlib.rest.GET.api.webhooks(
                peer=root.get("webhook", "http://127.0.0.1:4004"), timeout=2
            ).get("status", False) != 200:
                root["webhook"] = input("Peer address for webhook submition: ")
        except KeyboardInterrupt:
            zen.logMsg("\nconfiguration aborted...")
            return
        root["webhook"] = root["webhook"]
        # get monitored node api address
        try:
            root["api"] = input("Peer address for API requests: ")
            while "data" not in dposlib.rest.GET.api.blockchain(
                peer=root.get("api", "http://127.0.0.1:4003"), timeout=2
            ):
                root["api"] = input("Peer address for API requests: ")
        except KeyboardInterrupt:
            zen.logMsg("\nconfiguration aborted...")
            return
        root["api"] = root["api"]

    # final check
    if root.get("blockchain", "") not in dir(dposlib.net):
        root["blockchain"] = zen.chooseItem(
            "Select blockchain running on node:",
            *[
                name for name in dir(dposlib.net)
                if not name.startswith("_") and
                getattr(dposlib.net, name, {}).get("familly", None) == "ark"
            ]
        )

    if not root["blockchain"]:
        zen.logMsg("blockchain can not be determined...")
        return
    else:
        zen.logMsg("configuration done")
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
        zen.WEBHOOK_PEER = "http://127.0.0.1:%s" % zen.ENV.get(
            "CORE_WEBHOOKS_PORT", "4004"
        )
        zen.API_PEER = "http://127.0.0.1:%s" % zen.ENV.get(
            "CORE_API_PORT", "4003"
        )
    else:
        zen.WEBHOOK_PEER = root.get("webhook", False)
        zen.API_PEER = root.get("api", False)

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

    dposlib.rest.use(root.get("blockchain", "dark"))
    custom_peers = root.get("custom_peers", [])
    if len(custom_peers) > 0:
        zen.biom.dposlib.core.stop()
        zen.biom.dposlib.rest.cfg.peers = custom_peers


def configure(**kwargs):
    if "username" in kwargs:
        username = kwargs.pop("username")
        if getPublicKeyFromUsername(username):
            if not os.path.exists(
                os.path.join(zen.JSON, "%s-webhook.json" % username)
            ):
                if not setDelegate(
                    username, peer=kwargs.get("webhook_peer", None)
                ):
                    return
                zen.logMsg("%s delegate webhook set" % username)
            else:
                # load update and save in a row
                zen.dumpJson(
                    dict(zen.loadJson("%s.json" % username), **kwargs),
                    "%s.json" % username
                )
                zen.logMsg("%s delegate set" % username)
        else:
            zen.logMsg("can not find delegate %s" % username)

    elif not len(kwargs):
        root = zen.loadJson("root.json")
        if "env" in root:
            delegates = zen.loadJson(
                "delegates.json", os.path.dirname(root["env"])
            )
            for secret in delegates["secrets"]:
                setDelegate(dposlib.core.crypto.getKeys(secret)["publicKey"])


def removeDelegate(username):
    webhook = zen.loadJson("%s-webhook.json" % username)
    if len(webhook):
        resp = deleteWebhook(webhook["id"], peer=webhook["peer"])
        if resp.get("status", 500) < 300:
            zen.logMsg("webhook subscription removed")
        if input("Remove %s data ?[Y/n] " % username) in "yY":
            zen.dropJson("%s.json" % username)
            zen.dropJson("%s-webhook.json" % username)
            shutil.rmtree(
                os.path.join(zen.DATA, username), ignore_errors=True
            )
            shutil.rmtree(
                os.path.join(zen.TBW, username), ignore_errors=True
            )
            try:
                os.remove(os.path.join(zen.ROOT, "%s.db" % username))
            except Exception:
                pass
            zen.logMsg("%s data removed" % username)
    else:
        zen.logMsg("%s not found" % username)


def waitForPeer(peer):
    try:
        while dposlib.rest.GET(
            peer=peer, timeout=2
        ).get("status", False) != 200:
            time.sleep(2)
            zen.logMsg("wating for peer %s..." % peer)
        return True
    except KeyboardInterrupt:
        return False


def pullKeys():
    module = sys.modules[__name__]
    for username in [
        n.replace("-webhook.json", "") for n in next(os.walk(zen.JSON))[-1]
        if n.endswith("-webhook.json")
    ]:
        config = zen.loadJson("%s.json" % username)
        hide = False
        if "#1" in config:
            setattr(module, "_%s_#1" % username, config.pop("#1"))
            hide = True
        if "#2" in config:
            setattr(module, "_%s_#2" % username, config.pop("#2"))
            hide = True
        if hide:
            zen.logMsg("%s secrets pulled" % username)
            zen.dumpJson(config, "%s.json" % username)


def pushBackKeys():
    module = sys.modules[__name__]
    delegates = []
    for key, value in [
        (k, v) for k, v in module.__dict__.items() if k[-2:] in "#1#2"
    ]:
        username, num = key.replace("_", "").split("#")
        num = "#" + num
        config = zen.loadJson("%s.json" % username)
        config[num] = value
        zen.dumpJson(config, "%s.json" % username)
        delegates.append(username)

    for username in set(delegates):
        zen.logMsg("%s secrets pushed back" % username)


def getUsernameKeys(username):
    module = sys.modules[__name__]
    H1 = module.__dict__.get("_%s_#1" % username, None)
    H2 = module.__dict__.get("_%s_#2" % username, None)
    return (
        H1 if H1 is None else dposlib.core.crypto.getKeys(H1),
        H2 if H2 is None else dposlib.core.crypto.getKeys(H2)
    )


###########################
# BLOCKCHAIN INTERACTIONS #
###########################

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


def transactionApplied(id):
    data = dposlib.rest.GET.api.transactions(id).get("data", {})
    if isinstance(data, dict):
        return data.get("confirmations", 0) >= 10
    else:
        return False


def delegateIsForging(username):
    dlgt = dposlib.rest.GET.api.delegates(username).get("data", {})
    rank = dlgt.get("rank", dposlib.rest.cfg.activeDelegates + 1)
    return rank <= dposlib.rest.cfg.activeDelegates


def setDelegate(uname_or_puk, peer=None):
    peer = zen.WEBHOOK_PEER if peer is None else peer
    account = dposlib.rest.GET.api.wallets(uname_or_puk).get("data", {})
    attributes = account.get("attributes", {})

    if attributes.get("delegate", False):
        username = attributes["delegate"]["username"]
        config = zen.loadJson("%s.json" % username)
        config["publicKey"] = account["publicKey"]
        zen.logMsg("%s configuration:" % username)

        if "#1" not in config:
            config["#1"] = askPrivateKey(
                "enter first secret: ", config["publicKey"]
            )
            if not config.get("#1", False):
                zen.logMsg("\ndelegate identification failed")
                return False

        if "secondPublicKey" in attributes:
            config["#2"] = askPrivateKey(
                "enter second secret: ", attributes["secondPublicKey"]
            )
            if not config.get("#2", False):
                zen.logMsg("\ndelegate identification failed")
                return False

        overwrite = input("Overwrite previous webhoook?[Y/n] ") \
            if os.path.exists(
                os.path.join(zen.JSON, "%s-webhook.json" % username)
            ) else "y"

        if overwrite in "yY":
            if not waitForPeer(peer):
                zen.logMsg("%s peer unreachable" % peer)
                return False
            webhook = setWebhook(config["publicKey"])
            if "token" in webhook:
                webhook["peer"] = peer
                zen.logMsg("webhook subscription succeded")
                zen.dumpJson(webhook, "%s-webhook.json" % username)
            else:
                zen.logMsg(
                    "an error occured with webhook subscription:\n%s" %
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
    data = data.get("data", {})
    if data != {}:
        data["hash"] = hashlib.sha256(
            data.get("token", "").encode("utf-8")
        ).hexdigest()
        data["token"] = data["token"][32:]
    return data


def deleteWebhook(id, peer):
    data = dposlib.rest.DELETE.api.webhooks(id, peer=peer)
    return data.get("data", data)


# https://github.com/ArkEcosystem/core/blob/master/packages/core-state/src/round-state.ts#L230-L249
# https://github.com/ArkEcosystem/explorer/blob/develop/app/Services/Monitor/DelegateTracker.php
# # TOFIX: delegate order is not right
def getRoundOrder(height=None):
    _get = dposlib.rest.GET
    if height is None:
        last_block = _get.api.blockchain(returnKey="data").get("block", {})
        height = last_block.get("height", 0)

    activeDelegates = dposlib.rest.cfg.activeDelegates
    rnd = (height-1) // activeDelegates  # ok to be changed with milestones

    puks = [
        dlgt["publicKey"] for dlgt in
        _get.api.rounds("%s" % rnd, "delegates").get("data", [])
    ]

    # print(
    #     "height:", height,
    #     "- round:", rnd,
    #     "- remaining block:", activeDelegates - height % activeDelegates
    # )

    seed = b"%d" % rnd
    i = 0
    while i < activeDelegates:
        seed = hashlib.sha256(seed).digest()
        for x in seed[:4]:
            if i < activeDelegates:
                new_i = x % activeDelegates
                puk = puks[new_i]
                puks[new_i] = puks[i]
                puks[i] = puk
                i += 1
        # i += 1

    return puks


def _testOrderDelegate():
    _get = dposlib.rest.GET
    dlgt = dict(
        [d["publicKey"], d["username"]]
        for d in _get.api.delegates(returnKey="data")
    )
    last_block = _get.api.blockchain(returnKey="data").get("block", {})
    height = last_block.get("height", 0)
    activeDelegates = dposlib.rest.cfg.activeDelegates

    rnd = (height - 1) // activeDelegates
    prev_rnf = rnd - 1

    first_height = rnd * activeDelegates + 1
    prev_first_height = prev_rnf * activeDelegates + 1

    data = {}
    for height in [prev_first_height, first_height]:
        order = getRoundOrder(height)
        data[height] = [dlgt[puk] for puk in order]

    print(str(prev_first_height).ljust(20, " "), first_height)
    for i in range(activeDelegates):
        print(
            data[prev_first_height][i].ljust(20, " "),
            data[first_height][i],
        )
