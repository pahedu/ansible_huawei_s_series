#!/bin/bash
if [ -z `which pip` ]  ; then
   echo "Error: python-pip not install."
   exit 1 
fi

pip install --upgrade pip
if [ `ansible --version | head -1 | cut -f2 -d' '|cut -c1-3` != "2.9" ]; then
   echo "Error: The script only supports ansible 2.9."
   exit 1
fi

ANSIBLE_LOCATION=`pip show ansible | grep Location | cut -f2 -d':'`
ANSIBLE_PATH="$ANSIBLE_LOCATION/ansible"

if [ -z "$ANSIBLE_LOCATION" ] ; then
    echo "Error: Can not get Ansible dist-packages location."
    exit 1
else
    echo "Ansible dist-packages path:$ANSIBLE_PATH"
fi

echo "Huawei S Series modules path:$ANSIBLE_PATH/modules/network/huawei_s_series"
mkdir -p $ANSIBLE_PATH/modules/network/huawei_s_series
mkdir -p $ANSIBLE_PATH/module_utils/network/huawei_s_series

echo "Copying files ..."
if [ -d "./modules" ]; then
    cp -rf ./modules/huawei_s_series/* $ANSIBLE_PATH/modules/network/huawei_s_series
fi

if [ -d "./plugins" ]; then
    cp -rf ./plugins/* $ANSIBLE_PATH/plugins
fi

if [ -d "./module_utils" ]; then
    cp -rf ./module_utils/huawei_s_series/* $ANSIBLE_PATH/module_utils/network/huawei_s_series
fi

echo "Huawei S series Ansible 2.9 library installed."
