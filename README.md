# `zen`

`zen` package, entirely writen in python, provides failover routines for DPOS
nodes and `True Block Weight` utilities for pool management.

## Supported blockchain

 * [X] Ark
 * [X] Kapu

## Install

### Dependencies

  - OS related
    * [X] `daemon` : `sudo apt-get install daemon`
    * [X] `python` : `sudo apt-get install python`
    * [X] `pip` : `sudo apt-get install python-pip`
    * [X] `setuptools` : `sudo pip install setuptools`

  - Python related (automatically managed by `pip`)
    * [X] `pytz`
    * [X] `Flask`
    * [X] `ecdsa`
    * [X] `base58`

`sudo pip install https://github.com/Moustikitos/zen/archive/master.zip`

or

Download and extract https://github.com/Moustikitos/zen/archive/master.zip into
your home directory.

## Use

`python /usr/local/bin/zen-cmd.py [command] [options]`

or

`python /full/path/to/zen-cmd.py [command] [options]`

### Options

  `-h --help`

### Configuration commands

  - `setup`
  Initialize `config.json` and `tbw.json` according to node installed on
  server. Note that if sedond passphrase is asked, it is not stored "as is" in
  the configuration files. Second passphrase is needed for the true block weight
  payroll command `pay`.

  - `build`
  Initialize database used within the web user interface importing from
  blockchain all transactions related to delegate address running the node.

### Failover commands

  - `check`
  Check the behaviour of the node (block speed, height difference...) in order
  to restart or rebuild if needed. This check have to be performed every
  minute to be efficient. Data are stored in `chk.status` file.

  - `restart`
  Restart node. This command is launched by `check` if necessary.

  - `rebuild`
  Download the last snapshot available and rebuild. This command is launched by
  `check` if necessary.

### True Block Weight command

  - `launch`
  Start the web user interface on port 5000.

  - `relaunch`
  Restart the web user interface on port 5000.

  - `stop`
  Stop the web user interface.

  - `spread`
  Spread the weight of voters according to their wallet balance. This command
  have to be performed every 5 minutes to be efficient. Data are stored in
  `tbw.weight` file.

  - `extract`
  Generate `{year-month-day}.tbw` file containing timestamp of the extraction,
  the amount to share, a list of [voter address - weight] pairs and the amount
  keeped for the voters bellow threshold payment. Once extraction is done,
  weight of voters whom reached threshold payment is set to 0.

  - `pay`
  Send transactions from delegate to voters. It generates a registry file
  containing backed transactions and a secured loop removes them once applied
  in blockchain. `{year-month-day}.tbw` is stored in `zen/archive` folder once
  registry file succesfully created.

### Configure `crontab`

`zen` is designed to be run by `crontab`, a resourceless-linux-core service
running tasks in background. First, make sure you're allowed to run tasks using 
`crontab` :

`sudo nano /etc/cron.allow`

Write your username if not present in the file and save (`Ctrl+X`-`Y`-`Enter`)

Then create your tasks (here is just a proposition) :

`crontab -e`

Tell crontab where to find `forever` (type `whitch forever` and copy-paste)

`PATH=PATH:/full/path/to/forever`

Launch `check` every minute and log messages into `/home/username/chk.log`

` */1 * * * * /usr/bin/python /full/path/to/zen-cmd.py check >> /home/username/chk.log &2>1`

Launch `spread` every 5 minutes and log messages into `/home/<username>/tbw.log`

` */5 * * * * /usr/bin/python /full/path/to/zen-cmd.py spread >> /home/username/tbw.log &2>1`

Launch `extract` every sunday 19h00 and log messages into `/home/username/tbw.log`

` 0 19 * * 0 /usr/bin/python /full/path/to/zen-cmd.py extract >> /home/username/tbw.log &2>1`

Launch `pay` every sunday 19h05 and log messages into `/home/username/tbw.log`

` 5 19 * * 0 /usr/bin/python /full/path/to/zen-cmd.py pay >> /home/username/tbw.log &2>1`

Launch every 3 days 19h05 and log messages into `/home/username/tbw.log`

` 5 19 */3 * * /usr/bin/python /full/path/to/zen-cmd.py pay >> /home/username/tbw.log &2>1`

Start web user interface on server boot and log messages into `/home/username/flask.log`

`@reboot /usr/bin/python /full/path/to/zen-cmd.py start >> /home/username/flask.log &2>1`

Close and apply `crontab` tasks (`Ctrl+X`-`Y`-`Enter`)

The magic here is if your server restarts, it will launch `check` every minute
and the node will start automatically when zen identify a to heavy blockchain
height difference.

You can also start your node on server boot adding this line :

`@reboot /usr/bin/python /full/path/to/zen-cmd.py restart >> /home/username/chk.log &2>1`

## Security

The web user interface is contained by `daemon` into the `zen/app` folder so
only files contained in this folder may be exposed. `Flask` framework also
manage security issues a web interface can be subject to.
