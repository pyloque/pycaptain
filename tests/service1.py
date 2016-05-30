# -*- coding: utf-8 -*-

from pycaptain import CaptainClient, ServiceItem, IServiceObserver


class ServiceCallback(IServiceObserver):

    def online(self, client, name):
        print name, "is ready"

    def all_online(self, client):
        print "service1 is all ready"

    def offline(self, client, name):
        print name, "is offline"

    def kv_update(self, client, key):
        print key, client.get_kv(key)


origins = [ServiceItem("localhost", 6789), ServiceItem("localhost", 6790)]
client = CaptainClient(origins)
(client.provide("service1", ServiceItem("localhost", 6101))
    .observe(ServiceCallback())
    .watch_kv("project_settings_service1")
    .stop_on_exit()
    .start())
client.hang()
