#!/bin/bash
# install system dependencies
clear
echo installing system dependencies
echo ==============================
sudo apt-get -qq install curl
sudo apt-get -qq install python
sudo apt-get -qq install python-setuptools
sudo apt-get -qq install python-pip
sudo apt-get -qq install virtualenv
sudo apt-get -qq install nginx

# download zen package
echo
echo downloading zen package
echo =======================
cd ~
if ! (git clone --branch master https://github.com/Moustikitos/ark-zen.git) then
    cd ~/ark-zen
else
    cd ~/ark-zen
    git reset --hard
fi
git fetch --all
git checkout master -f
git pull

echo
echo creating virtual environement
echo =============================
mkdir ~/.local/share/ark-zen/venv -p
virtualenv ~/.local/share/ark-zen/venv -q
. ~/.local/share/ark-zen/venv/bin/activate
export PYTHONPATH=${PYTHONPATH}:${HOME}/ark-zen
cd ~/ark-zen

# install python dependencies
echo
echo installing python dependencies
echo ==============================
pip install -r requirements.txt -q

# installing zen command
echo
echo installing zen command
echo ======================
sudo rm /etc/nginx/sites-enabled/*
sudo cp nginx-zen /etc/nginx/sites-available
sudo ln -sf /etc/nginx/sites-available/nginx-zen /etc/nginx/sites-enabled
sudo service nginx restart

cp bash/activate ~
cp bash/zen ~
cd ~
chmod +x zen
chmod +x activate
chmod +x bash/snp

./zen initialize
