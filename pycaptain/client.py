# -*- coding: utf-8 -*-
# pylint: disable=all
'''
captain client implementation
'''

import json
import time
import atexit
import random
import traceback
import threading
import requests
from requests.exceptions import RequestException

from .service import LocalService, ServiceItem
from .service import ORIGIN_DEFAULT_PROBE
from .kv import LocalKv
from .keeper import ServiceKeeper


class IServiceObserver(object):
    '''
    service state callback
    '''
    def online(self, client, name):
        pass

    def all_online(self, client):
        pass

    def offline(self, client, name):
        pass

    def kv_update(self, client, key):
        pass


class CaptainClient(object):
    '''
    captain client implementation
    '''
    def __init__(self, origins):
        self.origins = origins
        self.services = LocalService()
        self.kvs = LocalKv()
        self.keeper = ServiceKeeper(self)
        self.watched = {}
        self.watched_kvs = set()
        self.provided = {}
        self.observers = []
        self.waiter = None
        self.current_origin = None

    @classmethod
    def origin(cls, host, port):
        '''
        build from single endpoint
        '''
        return cls([ServiceItem(host, port)])

    def shuffle_origin(self):
        '''
        refresh current origin
        '''
        total_probe = 0
        for origin in self.origins:
            total_probe += origin.probe
        rand_probe = random.randint(0, total_probe)
        acc_probe = 0
        for origin in self.origins:
            acc_probe += origin.probe
            if acc_probe > rand_probe:
                self.current_origin = origin
                break

    @property
    def url_root(self):
        if not self.current_origin:
            self.shuffle_origin()
        return self.current_origin.url_root

    def on_origin_success(self):
        '''
        current origin available, recover probe
        '''
        self.current_origin.probe = ORIGIN_DEFAULT_PROBE

    def on_origin_fail(self):
        '''
        current origin unavailable, decrease probe
        '''
        if self.current_origin.probe > 1:
            self.current_origin.probe >>= 1

    def check_dirty(self):
        '''
            check service and kv version
        '''
        url = self.url_root + "/api/version"
        js = requests.get(url).json()
        flags = [False, False]
        if js["service.version"] != self.services.global_version:
            flags[0] = True
        if js["kv.version"] != self.kvs.global_version:
            flags[1] = True
        return flags

    def check_service_versions(self):
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
            if self.services.get_version(name) != version:
                dirties.add(name)
        return dirties

    def check_kv_versions(self):
        '''
        check versions for multiple services
        '''
        dirties = set()
        if not self.watched_kvs:
            return dirties
        params = {"key": self.watched_kvs}
        url = self.url_root + "/api/kv/version"
        js = requests.get(url, params=params).json()
        for key, version in js["versions"].items():
            if self.kvs.get_version(key) != version:
                dirties.add(key)
        return dirties

    def reload_service(self, name):
        '''
        reload service information to services
        '''
        params = {"name": name}
        url = self.url_root + "/api/service/set"
        js = requests.get(url, params=params).json()
        services = []
        for item in js["services"]:
            item = ServiceItem(
                item["host"], item["port"], item["ttl"], item["payload"])
            services.append(item)
        self.services.set_version(name, js["version"])
        self.services.replace_service(name, services)
        if not self.healthy(name) and services:
            self.online(name)
        if self.healthy(name) and not services:
            self.offline(name)

    def reload_kv(self, key):
        '''
        reload key value information
        '''
        params = {"key": key}
        url = self.url_root + "/api/kv/get"
        js = requests.get(url, params=params).json()
        self.kvs.set_version(key, js["kv"]["version"])
        self.kvs.replace_kv(key, js["kv"]["value"])
        self.kv_update(key)

    def update_kv(self, key, value):
        '''
        update key value information
        '''
        url = self.url_root + "/api/kv/set"
        requests.post(
            url, data={"key": key, "value": json.dumps(value)}).json()

    def keep_service(self):
        '''
        keep service alive in captain
        '''
        for name, item in self.provided.items():
            params = {
                "name": name,
                "host": item.host,
                "port": item.port,
                "ttl": item.ttl,
                "payload": item.payload}
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

    def watch(self, *names):
        '''
        watch service
        '''
        for name in names:
            self.watched[name] = False
            self.services.init_service(name)
        return self

    def watch_kv(self, *keys):
        '''
        watch service
        '''
        for key in keys:
            self.watched_kvs.add(key)
            self.kvs.init_kv(key)
        return self

    def failover(self, name, *items):
        '''
        add backup services incase no dependent services provided
        '''
        self.services.failover(name, items)
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
        return self.services.random_service(name, self.failovers.get(name))

    def get_kv(self, key):
        '''
        get key value information from memory
        '''
        return self.kvs.get_kv(key)

    def observe(self, observer):
        '''
        add observer
        '''
        self.observers.append(observer)
        return self

    def online(self, name):
        '''
        service is ready, revoke callbacks
        '''
        oldstate = self.all_healthy()
        self.watched[name] = True
        for observer in self.observers:
            observer.online(self, name)
        if not oldstate and self.all_healthy():
            self.all_online()

    def all_online(self):
        '''
        all dependent services are ready, revoke callbacks
        '''
        for observer in self.observers:
            observer.all_online(self)
        waiter = self.waiter
        if waiter is not None:
            waiter.set()

    def offline(self, name):
        '''
        service is offline, revoke callbacks
        '''
        self.watched[name] = False
        for observer in self.observers:
            observer.offline(self, name)

    def kv_update(self, key):
        '''
        key value is updated, revoke callbacks
        '''
        for observer in self.observers:
            observer.kv_update(self, key)

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

    def keepalive(self, keepalive):
        '''
        set keeplive interval in seconds for provided service
        '''
        self.keeper.keepalive = keepalive

    def check_interval(self, interval):
        '''
        set check interval in milliseconds for watched services
        '''
        self.keeper.check_interval = interval

    def start(self):
        '''
        start captain client
        '''
        for key in self.watched_kvs:
            self.reload_kv(key)
        self.keeper.start()
        if not self.watched:
            self.all_online()
        if self.waiter is not None:
            self.waiter.wait()
            self.waiter = None

    def wait_until_all_online(self):
        '''
        wait until all dependent services are ready
        '''
        self.waiter = threading.Event()
        return self

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
