# -*- coding: utf-8 -*-

from pycaptain import CaptainClient, ServiceItem, IServiceObserver


class ServiceCallback(IServiceObserver):

    def online(self, client, name):
        print name, "is ready"

    def all_online(self, client):
        print "service3 is all ready"

    def offline(self, client, name):
        print name, "is offline"


client = CaptainClient.origin("localhost", 6789)
(client.watch("service1", "service2")
    .provide("service3", ServiceItem("localhost", 6301))
    .observe(ServiceCallback())
    .stop_on_exit()
    .start())
client.hang()
