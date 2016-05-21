import subprocess


class OpenVIM(object):
    @classmethod
    def create_tenant(cls, name, description):
        pass

    def __init__(self, host='localhost', port=9080, admin_port=9085, tennant=None):
        pass

    def create_flavor(self, name, description, ram, vcpus):
        pass

    def create_image(self, name, description, source, dest):
        pass

    def create_network(self, name, type, provider, shared):
        pass

    def list_hosts(self):
        pass
