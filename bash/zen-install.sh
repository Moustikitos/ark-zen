#!/bin/bash

VENVDIR="$HOME/.local/share/ark-zen/venv"
GITREPO="https://github.com/Moustikitos/ark-zen.git"

clear

if [ $# = 0 ]; then
    B="master"
else
    B=$1
fi
echo "github branch to use : $B"

echo
echo installing system dependencies
echo ==============================
sudo apt-get -qq install libudev-dev libusb-1.0.0-dev
sudo apt-get -qq install python python-dev python-setuptools python-pip
sudo apt-get -qq install python3 python3-dev python3-setuptools python3-pip
sudo apt-get -qq install pypy
sudo apt-get -qq install virtualenv
sudo apt-get -qq install nginx
echo "done"

echo
echo downloading ark-zen package
echo ===========================

cd ~
if (git clone --branch $B $GITREPO) then
    echo "package cloned !"
else
    echo "package already cloned !"
fi

cd ~/ark-zev
git reset --hard
git fetch --all
if [ "$B" == "master" ]; then
    git checkout $B -f
else
    git checkout tags/$B -f
fi
git pull

echo "done"

echo
echo creating virtual environment
echo =============================

if [ -d $VENVDIR ]; then
    read -p "remove previous virtual environement ? [y/N]> " r
    case $r in
    y) rm -rf $VENVDIR;;
    Y) rm -rf $VENVDIR;;
    *) echo -e "previous virtual environement keeped";;
    esac
fi

if [ ! -d $VENVDIR ]; then
    echo -e "select environment:\n  1) python3\n  2) pypy"
    read -p "[default:python]> " n
    case $n in
    1) TARGET="$(which python3)";;
    2) TARGET="$(which pypy)";;
    *) TARGET="$(which python)";;
    esac
    mkdir $VENVDIR -p
    virtualenv -p $TARGET $VENVDIR -q
fi

. $VENVDIR/bin/activate
export PYTHONPATH=${HOME}/ark-zen
echo "done"

echo
echo installing python dependencies
echo ==============================
cd ~/ark-zen
pip install -r requirements.txt -q
echo "done"

echo
echo installing zen command
echo ======================

chmod +x bash/snp
chmod +x bash/activate

cp bash/zen ~
cd ~
chmod +x zen

echo "done"
