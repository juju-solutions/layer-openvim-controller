import json
import subprocess

from charms.reactive import when, when_not, set_state
from charmhelpers.core.templating import render
from charmhelpers.core.hookenv import status_set
from charmhelpers.core.unitdata import kv
from charmhelpers.contrib.unison import create_private_key, create_public_key

def sh(cmd):
    return subprocess.check_output(cmd, shell=True)

def sh_as_ubuntu(cmd):
    return sh("sudo -iu ubuntu " + cmd)

def initialize_openvim_database(db):
    status_set("maintenance", "initializing openvim database")
    sh_as_ubuntu("./openmano/openvim/database_utils/init_vim_db.sh -u %s -p %s -d %s -h %s" % (
        db.user(),
        db.password(),
        db.database(),
        db.host()
    ))

def generate_ssh_key():
    status_set("maintenance", "generating ssh key")
    user = "ubuntu"
    folder = "/home/ubuntu/.ssh"
    private_path = "%s/id_rsa" % folder
    public_path = "%s.pub" % private_path
    create_private_key(user, private_path)
    create_public_key(user, private_path, public_path)

def add_openvim_to_path():
    status_set("maintenance", "adding openvim to path")
    sh("ln -s /home/ubuntu/openmano/scripts/service-openmano.sh /usr/bin/service-openmano")
    sh("ln -s /home/ubuntu/openmano/openvim/openvim /usr/bin/openvim")

def download_openvim():
    status_set("maintenance", "downloading openvim")
    sh_as_ubuntu("rm -rf openmano")
    sh_as_ubuntu("git clone https://github.com/wwwtyro/openmano.git openmano")

def configure_openvim(db):
    status_set("maintenance", "configuring openvim")
    render(
        source="openvimd.cfg",
        target="/home/ubuntu/openmano/openvim/openvimd.cfg",
        owner="ubuntu",
        perms=0o664,
        context={"db": db}
    )

def start_openvim():
    status_set("maintenance", "starting openvim")
    sh_as_ubuntu("service-openmano openvim start")

# TODO: possibly combine all of these create functions?
def create_tenant():
    status_set("maintenance", "creating tenant")
    render(source="tenant.yaml", target="/tmp/tenant.yaml", owner="ubuntu", perms=0o664, context={})
    cmd = 'openvim tenant-create /tmp/tenant.yaml'
    tenant_uuid = sh_as_ubuntu(cmd).split()[0]
    tenant_uuid = str(tenant_uuid, 'utf-8')
    return tenant_uuid

def create_image(tenant_uuid):
    status_set("maintenance", "creating image")
    render(source="image.yaml", target="/tmp/image.yaml", owner="ubuntu", perms=0o664, context={})
    cmd = 'OPENVIM_TENANT=%s openvim image-create /tmp/image.yaml' % tenant_uuid
    image_uuid = sh_as_ubuntu(cmd).split()[0]
    image_uuid = str(image_uuid, 'utf-8')
    return image_uuid

def create_flavor(tenant_uuid):
    status_set("maintenance", "creating flavor")
    render(source="flavor.yaml", target="/tmp/flavor.yaml", owner="ubuntu", perms=0o664, context={})
    cmd = 'OPENVIM_TENANT=%s openvim flavor-create /tmp/flavor.yaml' % tenant_uuid
    flavor_uuid = sh_as_ubuntu(cmd).split()[0]
    flavor_uuid = str(flavor_uuid, 'utf-8')
    return flavor_uuid

# TODO: especially combine these stupid network functions
def create_default_network(tenant_uuid):
    status_set("maintenance", "creating default network")
    render(source="net-default.yaml", target="/tmp/net-default.yaml", owner="ubuntu", perms=0o664, context={})
    cmd = 'OPENVIM_TENANT=%s openvim net-create /tmp/net-default.yaml' % tenant_uuid
    net_default_uuid = sh_as_ubuntu(cmd).split()[0]
    net_default_uuid = str(net_default_uuid, 'utf-8')
    return net_default_uuid

def create_virbr_network(tenant_uuid):
    status_set("maintenance", "creating virbr0 network")
    render(source="net-virbr0.yaml", target="/tmp/net-virbr0.yaml", owner="ubuntu", perms=0o664, context={})
    cmd = 'OPENVIM_TENANT=%s openvim net-create /tmp/net-virbr0.yaml' % tenant_uuid
    net_virbr0_uuid = sh_as_ubuntu(cmd).split()[0]
    net_virbr0_uuid = str(net_virbr0_uuid, 'utf-8')
    return net_virbr0_uuid

def create_vm_yaml(image_uuid, flavor_uuid, net_default_uuid, net_virbr0_uuid):
    status_set("maintenance", "creating default vm yaml file")
    render(
        source="server.yaml",
        target="/tmp/server.yaml",
        owner="ubuntu",
        perms=0o664,
        context={
            "image_uuid": image_uuid,
            "flavor_uuid": flavor_uuid,
            "net_default_uuid": net_default_uuid,
            "net_virbr0_uuid": net_virbr0_uuid
        }
    )

def create_sane_defaults():
    tenant_uuid = create_tenant()
    image_uuid = create_image(tenant_uuid)
    flavor_uuid = create_flavor(tenant_uuid)
    net_default_uuid = create_default_network(tenant_uuid)
    net_virbr0_uuid = create_virbr_network(tenant_uuid)
    create_vm_yaml(
        image_uuid=image_uuid,
        flavor_uuid=flavor_uuid,
        net_default_uuid=net_default_uuid,
        net_virbr0_uuid=net_virbr0_uuid
    )

@when('db.available')
@when_not('openvim-controller.installed')
def install_openvim_controller(mysql):
    download_openvim()
    add_openvim_to_path()
    configure_openvim(mysql)
    initialize_openvim_database(mysql)
    generate_ssh_key()
    start_openvim()
    create_sane_defaults()
    status_set("active", "openvim controller is running")
    set_state('openvim-controller.installed')

@when('compute.connected', 'openvim-controller.installed')
def send_ssh_key(compute):
    with open('/home/ubuntu/.ssh/id_rsa.pub', 'r') as f:
        key = f.read().strip()
    compute.send_ssh_key(key)

@when('compute.available', 'openvim-controller.installed')
def host_add(compute):
    cache = kv()
    if cache.get("compute:" + compute.address()):
        return
    sh_as_ubuntu("ssh -n -o 'StrictHostKeyChecking no' %s@%s" % (
        compute.user(),
        compute.address())
    )
    data = {
        'host': {
            'name': 'compute-0',
            'user': compute.user(),
            'ip_name': compute.address(),
            'description': 'compute-0'
        }
    }
    with open('/tmp/compute-0.json', 'w') as f:
        json.dump(data, f, indent=4, sort_keys=True)
    # TODO: openvim run function!
    sh_as_ubuntu("openvim host-add /tmp/compute-0.json")
    cache.set("compute:" + compute.address(), True)
