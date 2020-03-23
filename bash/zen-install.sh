#!/bin/bash
# install system dependencies
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
sudo apt-get -qq install curl
sudo apt-get -qq install python python-dev
sudo apt-get -qq install python-setuptools
sudo apt-get -qq install python-pip
sudo apt-get -qq install python3 python3-dev
sudo apt-get -qq install python3-setuptools
sudo apt-get -qq install python3-pip
sudo apt-get -qq install pypy
sudo apt-get -qq install virtualenv
sudo apt-get -qq install nginx
sudo apt-get -qq install libudev-dev libusb-1.0.0-dev

echo "done"

# download zen package
echo
echo downloading zen package
echo =======================
cd ~
if (git clone -q --branch $B https://github.com/Moustikitos/ark-zen.git) then
    echo "cloning ark-zen..."
else
    echo "ark-zen already cloned !"
fi
cd ~/ark-zen
git reset --hard
git fetch --all
if [ "$B" == "master" ]; then
    git checkout $B -fq
else
    git checkout tags/$B -fq
fi
git pull -q
echo "done"

echo
echo creating virtual environement
echo =============================

echo -e "Select the environment:\n  1) python3\n  2) pypy"
read -p "(default:python)> " n
case $n in
1) TARGET="$(which python3)";;
2) TARGET="$(which pypy)";;
*) TARGET="$(which python)";;
esac

if [ ! -d "$HOME/.local/share/ark-zen/venv" ]; then
    mkdir ~/.local/share/ark-zen/venv -p
    virtualenv -p ${TARGET} ~/.local/share/ark-zen/venv -q
else
    echo "virtual environement already there !"
fi

. ~/.local/share/ark-zen/venv/bin/activate
export PYTHONPATH=${HOME}/ark-zen
cd ~/ark-zen
echo "done"

# install python dependencies
echo
echo installing python dependencies
echo ==============================
pip install -r requirements.txt -q
echo "done"

# installing zen command
echo
echo installing zen command
echo ======================

chmod +x bash/snp
chmod +x bash/activate
cp bash/zen ~

cd ~
chmod +x zen
chmod +x activate
echo "done"
