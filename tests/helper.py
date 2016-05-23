# juju deployment helper functions
#
# we should really use amulet instead, but i was running into heaps of trouble
# with the way it handles series, and our weird requirements around that.

import os
import subprocess
import json
import time

def _sh(cmd):
    return subprocess.check_output(cmd, shell=True)

def deploy(service, series="trusty"):
    local_path = "%s/%s/%s" % (
        os.environ["JUJU_REPOSITORY"],
        series,
        service
    )
    if os.path.exists(local_path):
        service = local_path
    _sh("juju deploy %s --series %s" % (service, series))

def relate(a, b):
    _sh("juju add-relation %s %s" % (a, b))

def get_status():
    return json.loads(_sh("juju status --format json").decode("utf-8"))

def wait_for_status(service, status, timeout=600):
    deadline = time.time() + timeout
    while time.time() < deadline:
        service_status = get_status()["services"][service]["service-status"]["current"]
        if service_status == status:
            break
        time.sleep(1)
    else:
        raise WaitTimedOut()

class WaitTimedOut(Exception):
    pass
