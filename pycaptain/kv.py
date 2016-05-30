# -*- coding: utf-8 -*-
# pylint: disable=all


class KvItem(object):

    def __init__(self, key, value, version):
        self.key = key
        self.value = value
        self.version = version


class LocalKv(object):
    '''
    keep key value in memory
    '''

    def __init__(self):
        self.global_version = -1
        self.versions = {}
        self.kvs = {}

    def get_version(self, key):
        return self.versions.get(key, -1)

    def set_version(self, key, v):
        self.versions[key] = v

    def replace_kv(self, key, value):
        self.kvs[key] = value

    def init_kv(self, key):
        self.kvs[key] = {}

    def get_kv(self, key):
        return self.kvs.get(key, {})
