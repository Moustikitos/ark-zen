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
sudo apt-get -qq install python
sudo apt-get -qq install python-setuptools
sudo apt-get -qq install python-pip
sudo apt-get -qq install virtualenv
sudo apt-get -qq install nginx
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
git reset -q --hard
git fetch -q --all
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
if [ ! -d "$HOME/.local/share/ark-zen/venv" ]; then
    mkdir ~/.local/share/ark-zen/venv -p
    virtualenv ~/.local/share/ark-zen/venv -q
    echo "done"
else
    echo "virtual environement already there !"
fi
. ~/.local/share/ark-zen/venv/bin/activate
export PYTHONPATH=${PYTHONPATH}:${HOME}/ark-zen
export PATH=$(yarn global bin):$PATH
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
sudo rm /etc/nginx/sites-enabled/*
sudo cp nginx-zen /etc/nginx/sites-available
sudo ln -sf /etc/nginx/sites-available/nginx-zen /etc/nginx/sites-enabled
sudo service nginx restart

chmod +x bash/snp
cp bash/activate ~
cp bash/zen ~

cd ~
chmod +x zen
chmod +x activate
echo "done"
