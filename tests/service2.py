# -*- coding: utf-8 -*-

from pycaptain import CaptainClient, ServiceItem, IServiceObserver


class ServiceCallback(IServiceObserver):

    def ready(self, name):
        print name, "is ready"

    def all_ready(self):
        print "service2 is all ready"

    def offline(self, name):
        print name, "is offline"


client = CaptainClient.origin("localhost", 6789)
(client.provide("service2", ServiceItem("localhost", 6200))
    .observe(ServiceCallback())
    .stop_on_exit()
    .start())
client.hang()
