import json
import subprocess

from charms.reactive import when, when_not, set_state
from charmhelpers.core.templating import render
from charmhelpers.core.hookenv import status_set
from charmhelpers.core.unitdata import kv

@when('db.available')
@when_not('openvim-controller.installed')
def install_openvim_controller(mysql):
    status_set("maintenance", "installing openvim controller")
    render(
        source="init-controller.sh",
        target="/tmp/init-controller.sh",
        owner="ubuntu",
        perms=0o775,
        context={"db": mysql}
    )
    subprocess.check_call("sudo -u ubuntu /tmp/init-controller.sh", shell=True)

    status_set("maintenance", "starting openvim")
    render(
        source="openvimd.cfg",
        target="/home/ubuntu/openmano/openvim/openvimd.cfg",
        owner="ubuntu",
        perms=0o664,
        context={"db": mysql}
    )
    subprocess.check_call("sudo -u ubuntu /home/ubuntu/bin/service-openmano openvim start", shell=True)

    status_set("maintenance", "creating tenant")
    render(source="tenant.yaml", target="/tmp/tenant.yaml", owner="ubuntu", perms=0o664, context={})
    cmd = 'sudo -u ubuntu /home/ubuntu/openmano/openvim/openvim tenant-create /tmp/tenant.yaml'
    tenant_uuid = subprocess.check_output(cmd, shell=True).split()[0]
    tenant_uuid = str(tenant_uuid, 'utf-8')

    status_set("maintenance", "creating image")
    render(source="image.yaml", target="/tmp/image.yaml", owner="ubuntu", perms=0o664, context={})
    cmd = 'sudo -u ubuntu OPENVIM_TENANT=%s /home/ubuntu/openmano/openvim/openvim image-create /tmp/image.yaml' % tenant_uuid
    image_uuid = subprocess.check_output(cmd, shell=True).split()[0]
    image_uuid = str(image_uuid, 'utf-8')

    status_set("maintenance", "creating flavor")
    render(source="flavor.yaml", target="/tmp/flavor.yaml", owner="ubuntu", perms=0o664, context={})
    cmd = 'sudo -u ubuntu OPENVIM_TENANT=%s /home/ubuntu/openmano/openvim/openvim flavor-create /tmp/flavor.yaml' % tenant_uuid
    flavor_uuid = subprocess.check_output(cmd, shell=True).split()[0]
    flavor_uuid = str(flavor_uuid, 'utf-8')
    
    status_set("maintenance", "creating default network")
    render(source="net-default.yaml", target="/tmp/net-default.yaml", owner="ubuntu", perms=0o664, context={})
    cmd = 'sudo -u ubuntu OPENVIM_TENANT=%s /home/ubuntu/openmano/openvim/openvim net-create /tmp/net-default.yaml' % tenant_uuid
    net_default_uuid = subprocess.check_output(cmd, shell=True).split()[0]
    net_default_uuid = str(net_default_uuid, 'utf-8')
    
    status_set("maintenance", "creating virbr0 network")
    render(source="net-virbr0.yaml", target="/tmp/net-virbr0.yaml", owner="ubuntu", perms=0o664, context={})
    cmd = 'sudo -u ubuntu OPENVIM_TENANT=%s /home/ubuntu/openmano/openvim/openvim net-create /tmp/net-virbr0.yaml' % tenant_uuid
    net_virbr0_uuid = subprocess.check_output(cmd, shell=True).split()[0]
    net_virbr0_uuid = str(net_virbr0_uuid, 'utf-8')

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
    if cache.get(compute.address()):
        return
    cmd = "sudo -u ubuntu ssh -n -o 'StrictHostKeyChecking no' %s@%s" % (compute.user(), compute.address())
    subprocess.check_call(cmd, shell=True)
    data = json.dumps({
        'host': {
            'name': 'compute-0',
            'user': compute.user(),
            'ip_name': compute.address(),
            'description': 'compute-0'
        }
    }, indent=4, sort_keys=True)
    with open('/tmp/compute-0.json', 'w') as f:
        f.write(data)
    cmd = 'sudo -u ubuntu /home/ubuntu/openmano/openvim/openvim host-add /tmp/compute-0.json'
    subprocess.check_call(cmd, shell=True)
    cache.set(compute.address(), True)




# cmd = 'sudo -u ubuntu OPENVIM_TENANT=%s /home/ubuntu/openmano/openvim/openvim vm-create /tmp/server.yaml' % tenant_uuid
# subprocess.check_call(cmd, shell=True)
