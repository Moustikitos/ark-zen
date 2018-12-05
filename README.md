# `zen`

`zen` package, entirely writen in python, provides `True Block Weight` utilities
for DPOS pool.

## Supported blockchain

 * [X] Ark-v2

## Install v1.2.0

```bash
wget https://raw.githubusercontent.com/Moustikitos/ark-zen/1.3.0/bash/zen-install.sh
bash zen-install.sh
```

## `zen` command

```bash
cd ~
./zen --help
```
```
Usage:
    zen (reset | initialize)
    zen (configure | add-delegate) <username> [-s <share> -w <wallet> -t <threshold> -e <excludes> -b <block-delay> -f <fee-level> -h <webhook-peer>]
    zen remove-delegate [<username>]
    zen configure [-c <currency>]
    zen adjust-forge <username> <value>
    zen (start-tbw | stop-tbw)
    zen (launch-payroll | resume-payroll) <username>
    zen retry-payroll <username> -n <name-list>

Options:
-b --block-delay=<block-delay>   : block amount to wait between payroll
-c --currency=<currency>         : configure the token display on front-end page
-e --excludes=<excludes>         : coma-separated or file address list to exclude from payroll
-w --wallet=<wallet>             : delegate funds wallet
-f --fee-level=<fee-level>       : set the fee level for the delegate
-h --webhook-peer=<webhook-peer> : define the webhook peer to use
-s --share=<share>               : delegate share rate (0.0<=share<=1.0)
-t --threshold=<threshold>       : minimum amount for a payment
-n --name-list=<name-list>       : *.tbw name list

Subcommands:
    reset           : initialization starting from ark-core installation
    initialize      : initialization starting from delegates configuration
    configure       : configure options for a given <username>
    start-tbw       : start the true block weight process
    stop-tbw        : stop the true block weight process
    launch-payroll  : create a payroll for <username> (true block weight status reseted)
    retry-payroll   : retry a specified payroll for <username> (true block weight status unchanged)
    resume-payroll  : resume existing <username> payroll (true block weight status unchanged)
    add-delegate    : add <username> delegate not registered on ark-core-forger
    remove-delegate : remove delegate from list or specified by <username>
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

### TODO (dev version)

 - [ ] fork sensor
 - [ ] auto-rollback
