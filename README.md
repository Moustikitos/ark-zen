# `zen`

`zen` package, entirely writen in python, provides `True Block Weight` utilities
for DPOS pool.

## Supported blockchain

 * [X] Ark-v2

## Install

```bash
wget https://raw.githubusercontent.com/Moustikitos/zen/master/bash/zen-install.sh
bash zen-install.sh
```

## `zen-run` command

```bash
cd ~
./zen-run -h
```
```
Usage:
    zen-run reset
    zen-run initialize
    zen-run configure <username> [-s <share> -w <wallet> -t <threshold> -e <excludes> -b <block-delay> -f <fee-level>]
    zen-run configure [-c <currency>]
    zen-run adjust-forge <username> <value>
    zen-run start-tbw
    zen-run stop-tbw
    zen-run launch-payroll <username>
    zen-run retry-payroll <username> -n <name-list>
    zen-run resume-payroll <username>
    zen-run remove-delegate [<username>]

Options:
-b --block-delay=<block-delay> : block amount to wait between payroll
-c --currency=<currency>       : configure the token display on front-end page
-e --excludes=<excludes>       : coma-separated or file address list to exclude from payroll
-w --wallet=<wallet>           : delegate funds wallet
-f --fee-level=<fee-level>     : set the fee level for the delegate
-s --share=<share>             : delegate share rate (0.0<=share<=1.0)
-t --threshold=<threshold>     : minimum amount for a payment
-n --name-list=<name-list>     : *.tbw name list

Subcommands:
    reset          : initialization starting from ark-core installation
    initialize     : initialization starting from delegates configuration
    configure      : configure options for a given <username>
    start-tbw      : start the true block weight process
    stop-tbw       : stop the true block weight process
    launch-payroll : create a payroll for <username> (true block weight status reseted)
    retry-payroll  : retry a specified payroll for <username> (true block weight status unchanged)
    resume-payroll : resume existing <username> payroll (true block weight status unchanged)
```

## `zen` front-end

https://raw.githubusercontent.com/Moustikitos/zen/master/app.png
