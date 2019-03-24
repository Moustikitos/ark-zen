# `zen`

`zen` package, entirely writen in python, provides `True Block Weight` utilities
for DPOS pool.

## Support this project

  * [X] Send &#1126; to `AUahWfkfr5J4tYakugRbfow7RWVTK35GPW`
  * [X] Vote `arky` on [Ark blockchain](https://explorer.ark.io) and [earn &#1126; weekly](http://arky-delegate.info/arky)

## Supported blockchain

 * [X] Ark-core v2

## Install

### last release

```bash
bash <(curl -s https://raw.githubusercontent.com/Moustikitos/ark-zen/1.7.1/bash/zen-install.sh)
```

### developpement version

```bash
bash <(curl -s https://raw.githubusercontent.com/Moustikitos/ark-zen/master/bash/zen-install-dev.sh)
```

## `zen` command

```bash
cd ~
./activate
./zen --help
```
```
Usage:
    zen (reset | initialize | snap-blockchain | rebuild | remove-custom-peer)
    zen (start-srv | stop-srv | start-chk | stop-chk )
    zen configure <username> [-s <share> -w <wallet> -t <threshold> -e <excludes> -b <block-delay> -f <fee-level>]
    zen add-delegate <username> -h <webhook-peer>
    zen configure [ --fee-coverage --target-delegate --chunk-size <chubk-size> -c <currency>]
    zen adjust-forge <username> <value>
    zen launch-payroll <username>
    zen retry-payroll <username> -n <name-list>
    zen resume-payroll <username>
    zen remove-delegate [<username>]
    zen append-custom-peer <peer-list>

Options:
    -b --block-delay=<block-delay>   : block amount to wait beetween payroll
    -c --currency=<currency>         : configure token display on front-end pages
    -e --excludes=<excludes>         : coma-separated or file address list to exclude from payroll
    -w --wallet=<wallet>             : delegate funds wallet
    -f --fee-level=<fee-level>       : set the fee level for the delegate
    -h --webhook-peer=<webhook-peer> : define the webhook peer to use
    -s --share=<share>               : delegate share rate (0.0<=share<=1.0)
    -t --threshold=<threshold>       : minimum amount for a payment
    -n --name-list=<name-list>       : *.tbw coma-separated name list
    --chunk-size=<chunk-size>        : max transaction per request [default:15]
    --target-delegate                : send transactions to delegate when forging (flag)
    --fee-coverage                   : delegate covers transaction fees (flag)

Subcommands:
    reset              : initialization starting from ark-core config folder
    initialize         : initialization starting from delegates configuration
    rebuild            : rebuild database from snapshots
    configure          : configure options for a given <username>
    start-srv/chk      : start the true block weight server/node checker
    stop-srv/chk       : stop the true block weight server/node checker
    launch-payroll     : create a payroll for <username> (true block weight status reseted)
    retry-payroll      : retry a specified payroll for <username> (true block weight status unchanged)
    resume-payroll     : resume existing <username> payroll (true block weight status unchanged)
    add-delegate       : add remote <username> (ie ark-forger running on remote node)
    remove-delegate    : remove delegate from list or specified by <username>
    snap-blockchain    : update snapshot or create it if no snapshot initialized yet
    append-custom-peer : append custom peer from coma-separated-peer or newline-separated-peer file
    remove-custom-peer : remove one or more custom peer from a selection list
```

## Notification system

4 notification types are available. Notification service is activated if a json configuration file is present in `.json` folder.

**freemobile (french only)**
Notification option must be enabled in your Free mobile account. Then, copy your parameters in `freemobile.json` file&nbsp;:
```json
{
    "user": "12345678", 
    "pass": "..."
}
```

**twilio**
Copy your parameters in `twilio.json` file&nbsp;:
```json
{
    "sid": "...",
    "auth": "...", 
    "receiver": "+1234567890", 
    "sender": "+0987654321"
}
```

**Pushover**
Copy your parameters in `pushover.json` file&nbsp;:
```json
{
    "user": "...",
    "token": "..."
}
```

**Pushbullet**
Copy your API token in `pushbullet.json` file&nbsp;:
```json
{
    "token": "..."
}
```

## `crontab` use case

Edit the crontab file
```shell
crontab -e
```

This crontab create a snapshot every 4 hours and automatically starts relay,
forger, zen server and zen checker.

```shell
PATH=/usr/bin:/bin:/usr/bin/env

0 */4  *   *   *     $HOME/ark-zen/bash/snp
@reboot sleep 10 && yarn exec ark relay:start
@reboot sleep 30 && yarn exec ark forger:start
@reboot cd $HOME/ark-zen && /usr/bin/pm2 start srv.json && /usr/bin/pm2 start chk.json
```

## `zen` front-end

![zen front-end](https://raw.githubusercontent.com/Moustikitos/zen/master/app.png)

## Releases

### Andromeda (v1.2.0)

 - [x] true block weight
 - [x] secured payrolls
 - [x] command line interface
 - [x] light weight HTML front-end
 - [x] multiple pool management

### Boötis (v1.3.0)
 - [x] enable remote delegate management
 - [x] blockchain database rebuild
 - [x] snapshot management
 - [x] custom peer management

### Boötis - minor tweaks (v1.3.1)
 - [x] reward distribution improvement

### Cassiopeia (v1.4.0)
 - [x] automatic fee coverage
 - [x] transaction history rebuild
 - [x] delegate targetting

### Cassiopeia - minor tweaks (v1.4.1)
 - [x] fee coverage is now optional
 - [x] delegate targetting is now optional

### Cassiopeia - minor tweaks (v1.4.2)
 - [x] ark-zen runs with both ark-core mainnet and devnet

### Delphinus (v1.5.0)
 - [x] ark-zen runs with ark-core 2.1.x
 - [x] html front-end improvement

### Eridanus (v1.6.0)
 - [x] notification system added (SMS or push)
 - [x] ark-zen runs with ark-core 2.2.x
 - [x] added node checker

### Fornax (v1.7.0)
 - [x] ark-zen now runs in virtualenv
 - [x] server auto-configuration using gunicorn and nginx 
 - [x] minor bugfixes and improvements

### Fornax - zen script improvement (v1.7.1)
 - [x] setup script improvement
 - [x] initialization improvement
 - [x] added relay checker

### TODO (dev version)
 - [ ] auto-rollback
