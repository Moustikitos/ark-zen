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
    zen-run configure <username> [-s <share> -f <funds> -t <threshold> -e <excludes> -b <block-delay>]
    zen-run configure [-c <currency>]
    zen-run adjust-forge <username> <value>
    zen-run start-tbw
    zen-run stop-tbw
    zen-run launch-payroll <username>
    zen-run resume-payroll <username>

Options:
-b --block-delay=<block-delay> : block amount to wait between payroll
-c --currency=<currency>       : configure the token display on front-end page
-e --excludes=<excludes>       : coma-separated address list to exclude from payroll
-f --funds=<funds>             : delegate funds address
-s --share=<share>             : delegate share rate (0.0<=share<=1.0) [default: 1.0]
-t --threshold=<threshold>     : minimum amount for a payment [default: 0.2]

Subcommands:
    reset          : initialization starting from ark-core installation
    initialize     : initialization starting from delegates configuration
    configure      : configure options for a given <username>
    start-tbw      : start the true block weight process
    stop-tbw       : stop the true block weight process
    launch-payroll : create a payroll for <username> (true block weight status reset)
    resume-payroll : resume existing <username> payroll (true block weight status unchanged)
```
