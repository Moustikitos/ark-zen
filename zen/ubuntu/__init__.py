# -*- coding: utf-8 -*-
# OS INTERACTIONS

import io
import os
import sys
import zen
import time
import subprocess


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
    try:
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
    except Exception:
        pass
    return appnames


def start_pm2_app(appname):
    return os.system(f'''
if ! echo "$(pm2 id {appname} | tail -n 1)" | grep -qE "\\[\\]"; then
    echo "starting {appname}..."
    pm2 start {appname} -s
fi''')


def restart_pm2_app(appname):
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
