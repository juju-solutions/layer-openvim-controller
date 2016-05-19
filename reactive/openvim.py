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
    render(
        source="openvimd.cfg",
        target="/home/ubuntu/openmano/openvim/openvimd.cfg",
        owner="ubuntu",
        perms=0o664,
        context={"db": mysql}
    )
    status_set("maintenance", "starting openvim")
    subprocess.check_call("sudo -u ubuntu /home/ubuntu/bin/service-openmano openvim start", shell=True)
    set_state("openvim-controller.installed")
    status_set("active", "openvim controller is running")

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
    