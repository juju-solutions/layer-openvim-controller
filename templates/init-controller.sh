#!/bin/sh

set -eu

cd $HOME

# install openvim
rm -rf openmano
git clone https://github.com/wwwtyro/openmano.git openmano
./openmano/openvim/database_utils/init_vim_db.sh -u{{ db.user() }} -p{{ db.password() }} -d{{ db.database() }} -h {{ db.host() }}

# prepare communication with compute nodes
ssh-keygen -f $HOME/.ssh/id_rsa -N ""

# put stuff in path for convenience
mkdir -p $HOME/bin
ln -s $(pwd)/openmano/scripts/service-openmano.sh $HOME/bin/service-openmano
ln -s $(pwd)/openmano/openvim/openvim $HOME/bin/openvim

# TODO: openvim as a systemd service?
