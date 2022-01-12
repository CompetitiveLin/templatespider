#!/bin/bash

read -r -p "Env is conda? [y/N] " response

read -p "Enter spider_name: " spider_name
echo $spider_name
#sudo curl --silent --location https://rpm.nodesource.com/setup_14.x | bash -
#sudo yum -y install nodejs
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]
then
    export PATH="/home/ec2-user/anaconda3/bin:$PATH"
    . /home/ec2-user/anaconda3/etc/profile.d/conda.sh
    conda create -n xufeng python=3.9.5
    conda activate xufeng
    conda install gcc_linux-64
else
    source /home/ec2-user/fashionSpider/.env/bin/activate
fi
pip install -r requirements.txt

nohup python -u deploy.py ${spider_name} > /tmp/logs/${spider_name}.log 2>&1 &
ps -ef | grep py

