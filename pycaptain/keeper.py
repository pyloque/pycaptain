# -*- coding: utf-8 -*-
# pylint: disable=all
'''
captain client implementation
'''

import logging
import time
import threading
from requests.exceptions import RequestException


class ServiceKeeper(object):
    '''
    service keeper thread
    '''
    def __init__(self, client):
        self.client = client
        self.stop_event = threading.Event()
        self.keepalive = 10
        self.check_interval = 1000
        self.last_keep_ts = 0

    def start(self):
        t = threading.Thread(target=self.loop)
        t.daemon = True
        t.start()

    def loop(self):
        while not self.stop_event.is_set():
            self.client.shuffle_origin()
            flag = True
            try:
                self.watch()
            except RequestException, e:
                logging.error("watch versions failed", exc_info=e)
                flag = False
            try:
                self.keep()
            except RequestException:
                logging.error("keep service failed", exc_info=e)
                flag = False
            if flag:
                self.client.on_origin_success()
            else:
                self.client.on_origin_fail()
            self.stop_event.wait(self.check_interval/1000.0)

    def watch(self):
        flags = self.client.check_dirty()
        if flags[0]:
            dirties = self.client.check_service_versions()
            for name in dirties:
                self.client.reload_service(name)
        if flags[1]:
            dirties = self.client.check_kv_versions()
            for key in dirties:
                self.client.reload_kv(key)

    def keep(self):
        now = int(time.time())
        if now - self.last_keep_ts > self.keepalive:
            self.client.keep_service()
            self.last_keep_ts = now

    def quit(self):
        self.stop_event.set()
