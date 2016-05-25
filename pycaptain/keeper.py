# -*- coding: utf-8 -*-
# pylint: disable=all
'''
captain client implementation
'''

import time
import threading
import traceback
from requests.exceptions import RequestException


class ServiceKeeper(object):
    '''
    service keeper thread
    '''
    def __init__(self, client):
        self.client = client
        self.keepalive = 10
        self.check_interval = 1000
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
            time.sleep(self.check_interval/1000.0)

    def watch(self):
        if not self.client.check_dirty():
            return
        dirties = self.client.check_versions()
        for name in dirties:
            self.client.reload_service(name)

    def keep(self):
        now = int(time.time())
        if now - self.last_keep_ts > self.keepalive:
            self.client.keep_service()
            self.last_keep_ts = now

    def quit(self):
        self.stop = True
