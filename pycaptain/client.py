# -*- coding: utf-8 -*-
# pylint: disable=all
'''
captain client implementation
'''

import time
import atexit
import random
import threading
import traceback
import requests
from requests.exceptions import RequestException


class CaptainError(Exception):
    '''
    customize error
    '''
    pass


class ServiceItem(object):
    '''
    service definition
    '''

    def __init__(self, host, port, ttl=30):
        self.host = host
        self.port = port
        self.ttl = ttl

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

    def random_service(self, name):
        '''
        select a service randomly
        '''
        services = self.service_lists[name]
        if not services:
            raise CaptainError("no service provided")
        ind = random.randint(0, len(services) - 1)
        return services[ind]


class IServiceObserver(object):

    def ready(self, name):
        pass

    def all_ready(self):
        pass

    def offline(self, name):
        pass


class ServiceKeeper(object):
    '''
    service keeper thread
    '''
    def __init__(self, client, ttl):
        self.client = client
        self.ttl = ttl
        self.last_keep_ts = 0
        self.stop = False

    def start(self):
        t = threading.Thread(target=self.loop)
        t.daemon = True
        t.start()

    def loop(self):
        while not self.stop:
            self.client.shuffle_url_root()
            try:
                self.watch()
            except RequestException:
                traceback.print_exc()
            try:
                self.keep()
            except RequestException:
                traceback.print_exc()
            time.sleep(1)

    def watch(self):
        if not self.client.check_dirty():
            return
        dirties = self.client.check_versions()
        for name in dirties:
            self.client.reload_service(name)

    def keep(self):
        now = int(time.time())
        if now - self.last_keep_ts > self.ttl:
            self.client.keep_service()
            self.last_keep_ts = now

    def quit(self):
        self.stop = True


class CaptainClient(object):
    '''
    captain client implementation
    '''

    def __init__(self, origins):
        self.origins = []
        for host, port in origins.items():
            self.origins.append(ServiceItem(host, port))
        self.local = LocalService()
        self.keeper = ServiceKeeper(self, 10)  # heartbeat default to 10s
        self.watched = {}
        self.provided = {}
        self.observers = []
        self._url_root = ""

    @classmethod
    def origin(cls, host, port):
        '''
        build from single endpoint
        '''
        return cls({host: port})

    def shuffle_url_root(self):
        '''
        refresh current url root
        '''
        ind = random.randint(0, len(self.origins) - 1)
        self._url_root = self.origins[ind].url_root

    @property
    def url_root(self):
        if not self._url_root:
            self.shuffle_url_root()
        return self._url_root

    def check_dirty(self):
        '''
        check captain global version
        '''
        params = {"version": self.local.global_version}
        url = self.url_root + "/api/service/dirty"
        js = requests.get(url, params=params).json()
        self.local.global_version = js["version"]
        return js["dirty"]

    def check_versions(self):
        '''
        check versions for multiple services
        '''
        dirties = set()
        if not self.watched:
            return dirties
        params = {"name": self.watched.keys()}
        url = self.url_root + "/api/service/version"
        js = requests.get(url, params=params).json()
        for name, version in js["versions"].items():
            if self.local.get_version(name) != version:
                dirties.add(name)
        return dirties

    def reload_service(self, name):
        '''
        reload service information to local
        '''
        params = {"name": name}
        url = self.url_root + "/api/service/set"
        js = requests.get(url, params=params).json()
        services = []
        for item in js["services"]:
            item = ServiceItem(item["host"], item["port"], item["ttl"])
            services.append(item)
        self.local.set_version(name, js["version"])
        self.local.replace_service(name, services)
        if not self.healthy(name) and services:
            self.ready(name)
        if self.healthy(name) and not services:
            self.offline(name)

    def keep_service(self):
        '''
        keep service alive in captain
        '''
        for name, item in self.provided.items():
            params = {
                "name": name,
                "host": item.host,
                "port": item.port,
                "ttl": item.ttl}
            url = self.url_root + "/api/service/keep"
            requests.get(url, params=params)

    def cancel_service(self):
        '''
        cancel service in captain
        '''
        for name, item in self.provided.items():
            params = {
                "name": name,
                "host": item.host,
                "port": item.port}
            url = self.url_root + "/api/service/cancel"
            requests.get(url, params=params)

    def heartbeat(self, ttl):
        '''
        config heartbeat period
        '''
        self.keeper.ttl = ttl
        return self

    def watch(self, *names):
        '''
        watch service
        '''
        for name in names:
            self.watched[name] = False
            self.local.init_service(name)
        return self

    def provide(self, name, service):
        '''
        register service to captain
        '''
        self.provided[name] = service
        return self

    def select(self, name):
        '''
        select a service for name
        '''
        return self.local.random_service(name)

    def observe(self, observer):
        '''
        add observer
        '''
        self.observers.append(observer)
        return self

    def ready(self, name):
        '''
        service is ready, revoke callbacks
        '''
        oldstate = self.all_healthy()
        self.watched[name] = True
        for observer in self.observers:
            observer.ready(name)
        if not oldstate and self.all_healthy():
            observer.all_ready()

    def offline(self, name):
        '''
        service is offline, revoke callbacks
        '''
        self.watched[name] = False
        for observer in self.observers:
            observer.offline(name)

    def healthy(self, name):
        '''
        whether service is healthy
        '''
        return self.watched[name]

    def all_healthy(self):
        '''
        all dependecied services are ready
        '''
        return all(self.watched.values())

    def start(self):
        '''
        start captain client
        '''
        self.keeper.start()
        if not self.watched:
            for observer in self.observers:
                observer.all_ready()

    def stop_on_exit(self):
        '''
        cancel service before stop
        '''
        atexit.register(self.stop)
        return self

    def hang(self):
        '''
        hang forever
        '''
        while True:
            time.sleep(1)

    def stop(self):
        '''
        stop captain client
        '''
        try:
            self.cancel_service()
        except RequestException:
            traceback.print_exc()
        self.keeper.quit()
