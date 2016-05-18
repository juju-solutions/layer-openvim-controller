#!/bin/sh

set -eu

cd $HOME

sudo apt update

# install and configure mysql
echo "mysql-server mysql-server/root_password password root" | sudo debconf-set-selections
echo "mysql-server mysql-server/root_password_again password root" | sudo debconf-set-selections
sudo apt install -y mysql-server
mysqladmin -u root -proot create vim_db
mysqladmin -u root -proot create mano_db
cat << EOF | mysql -u root -proot
  CREATE USER 'vim'@'localhost' identified by 'vimpw';
  GRANT ALL PRIVILEGES ON vim_db.* TO 'vim'@'localhost';
  CREATE USER 'mano'@'localhost' identified by 'manopw';
  GRANT ALL PRIVILEGES ON mano_db.* TO 'mano'@'localhost';
EOF

# install and start openvim
#sudo apt install -y git screen wget python-yaml python-libvirt python-bottle \
#  python-mysqldb python-jsonschema python-paramiko python-argcomplete \
#  python-requests python-novaclient python-keystoneclient python-glanceclient \
#  python-neutronclient
git clone https://github.com/wwwtyro/openmano.git openmano
./openmano/openvim/database_utils/init_vim_db.sh -uvim -pvimpw
./openmano/openmano/database_utils/init_mano_db.sh -umano -pmanopw
./openmano/scripts/service-openmano.sh openvim start

# prepare communication with compute nodes
ssh-keygen -f $HOME/.ssh/id_rsa -N ""

# put stuff in path for convenience
mkdir -p $HOME/bin
ln -s $(pwd)/openmano/scripts/service-openmano.sh $HOME/bin/service-openmano
ln -s $(pwd)/openmano/openvim/openvim $HOME/bin/openvim

# TODO: openvim as a systemd service?
