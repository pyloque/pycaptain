# -*- coding: utf-8 -*-

from pycaptain import CaptainClient, ServiceItem, IServiceObserver


class ServiceCallback(IServiceObserver):

    def online(self, client, name):
        print name, "is ready"

    def all_online(self, client):
        print "service4 is all ready"

    def offline(self, client, name):
        print name, "is offline"


client = CaptainClient.origin("localhost", 6789)
(client.watch("service1", "service2", "service3")
    .provide("service4", ServiceItem("localhost", 6400))
    .observe(ServiceCallback())
    .stop_on_exit()
    .wait_until_all_online()
    .start())
client.hang()
