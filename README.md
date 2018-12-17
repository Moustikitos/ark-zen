# `zen`

`zen` package, entirely writen in python, provides `True Block Weight` utilities
for DPOS pool.

## Supported blockchain

 * [X] Ark-v2

## Install last release

```bash
wget https://raw.githubusercontent.com/Moustikitos/ark-zen/1.4.1/bash/zen-install.sh
bash zen-install.sh
```

## `zen` command

```bash
cd ~
./zen --help
```
```
Usage:
    zen (reset | initialize | rebuild | start-tbw | stop-tbw | snap-blockchain | remove-custom-peer)
    zen (configure | add-delegate) <username> [-s <share> -w <wallet> -t <threshold> -e <excludes> -b <block-delay> -f <fee-level> -h <webhook-peer>]
    zen configure [-c <currency> --fee-coverage --target-delegate --chunk-size <chubk-size>]
    zen adjust-forge <username> <value>
    zen launch-payroll <username>
    zen retry-payroll <username> -n <name-list>
    zen resume-payroll <username>
    zen remove-delegate [<username>]
    zen append-custom-peer <peer-list>

Options:
-b --block-delay=<block-delay>   : block amount to wait beetween payroll
-c --currency=<currency>         : configure token display on front-end page
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
    reset              : initialization starting from ark-core installation
    initialize         : initialization starting from delegates configuration
    rebuild            : rebuild database from snapshots
    configure          : configure options for a given <username>
    start-tbw          : start the true block weight process
    stop-tbw           : stop the true block weight process
    launch-payroll     : create a payroll for <username> (true block weight status reseted)
    retry-payroll      : retry a specified payroll for <username> (true block weight status unchanged)
    resume-payroll     : resume existing <username> payroll (true block weight status unchanged)
    add-delegate       : add remote <username> (ie ark-core-forger running on remote node)
    remove-delegate    : remove delegate from list or specified by <username>
    snap-blockchain    : update snapshot or create it if no snapshot initialized yet
    append-custom-peer : append custom peer from coma-separated-peer or newline-separated-peer file
    remove-custom-peer : remove one or more custom peer from a selection list
```

## crontab use case

Edit the crontab file
```bash
crontab -e
```
**create a snapshot and update it every 12 hours**
```
0 */12 *   *   *     /home/{username}/zen snap-blockchain
```
**automatic startup on server restart**
```
@reboot /usr/bin/pm2 start /home/{username}/core-commander/ecosystem.config.js --only ark-core-relay >> /home/{username}/core-commander/logs/commander.log 2>&1
@reboot sleep 30 && /usr/bin/pm2 start /home/{username}/core-commander/ecosystem.config.js --only ark-core-forger >> /home/{username}/core-commander/logs/commander.log 2>&1
@reboot cd /home/{username}/ark-zen && /usr/bin/pm2 start app.json
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

### Cassiopeia (v1.3.1)
 - [x] reward distribution bugfix

### Delphinus (v1.4.0)
 - [x] automatic fee coverage
 - [x] transaction history rebuild
 - [x] delegate targetting

### Eridanus (v1.4.1)
 - [x] fee coverage bugfix
 - [x] fee coverage is now optioinal
 - [x] delegate targetting is now optional

### TODO (dev version)
 - [ ] fork sensor
 - [ ] auto-rollback
