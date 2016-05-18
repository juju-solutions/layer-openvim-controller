from charms.reactive import when, when_not, set_state
from charmhelpers.core.templating import render
from charmhelpers.core.hookenv import status_set

import subprocess

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
    set_state("openvim-controller.installed")
    status_set("active", "openvim controller is running")

@when('compute.available')
def stuff(compute):
    kv = KV()
    for node in compute.list_nodes():
        if node.hostname in kv.get('already-set-up'):
            continue
        node.send_ssh_key(<key>)
        node.hostname()
        node.address()
        node.user()
        kv.add('already-set-up', node.hostname())
