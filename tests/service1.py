# -*- coding: utf-8 -*-

from pycaptain import CaptainClient, ServiceItem, IServiceObserver


class ServiceCallback(IServiceObserver):

    def online(self, name):
        print name, "is ready"

    def all_online(self):
        print "service1 is all ready"

    def offline(self, name):
        print name, "is offline"


client = CaptainClient.origin("localhost", 6789)
(client.provide("service1", ServiceItem("localhost", 6100))
    .observe(ServiceCallback())
    .stop_on_exit()
    .start())
client.hang()
