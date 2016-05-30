# -*- coding: utf-8 -*-
# pylint: disable=all
'''
captain client implementation
'''
import random


class CaptainError(Exception):
    '''
    customize error
    '''
    pass


ORIGIN_DEFAULT_PROBE = 1024


class ServiceItem(object):
    '''
    service definition
    '''

    def __init__(self, host, port, ttl=30):
        self.host = host
        self.port = port
        self.ttl = ttl
        self.probe = ORIGIN_DEFAULT_PROBE

    @property
    def url_root(self):
        '''
        http url prefix
        '''
        return "http://%s:%s" % (self.host, self.port)


class LocalService(object):
    '''
    keep service information in memory
    '''

    def __init__(self):
        self.global_version = -1
        self.versions = {}
        self.service_lists = {}
        self.failovers = {}

    def set_failovers(self, name, items):
        '''
        set failover services
        '''
        self.failovers[name] = items

    def get_version(self, name):
        '''
        get local service version
        '''
        return self.versions.get(name, -1)

    def set_version(self, name, v):
        '''
        update local service version
        '''
        self.versions[name] = v

    def replace_service(self, name, services):
        '''
        update local services
        '''
        self.service_lists[name] = services

    def init_service(self, name):
        '''
        initiaze service list
        '''
        self.service_lists[name] = []

    def random_service(self, name, failovers):
        '''
        select a service randomly
        '''
        services = self.service_lists[name]
        failovers = self.failovers.get(name)
        if not services:
            if not failovers:
                raise CaptainError("no service provided for name=" + name)
            services = failovers
        ind = random.randint(0, len(services) - 1)
        return services[ind]
