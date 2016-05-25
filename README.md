Use Captain Python Client
---------------------------
```python
from pycaptain import CaptainClient, ServiceItem, IServiceObserver


class ServiceCallback(IServiceObserver):

    def online(self, name):
        print name, "is ready"

    def all_online(self):
        print "service4 is all ready"

    def offline(self, name):
        print name, "is offline"


# connect to multiple captain servers
client = CaptainClient([ServiceItem("localhost", 6789), ServiceItem("localhost", 6790)])
# client = CaptainClient.origin("localhost", 6789) connect to single captain server
(client.watch("service1", "service2", "service3") # define service dependencies
    .provide("service4", ServiceItem("localhost", 6400)) # provide service
    .observe(ServiceCallback()) # add observer for dependent service's event
    .keepalive(10) # set keepalive heartbeat in seconds for provided service
    .check_interval(1000) # set check interval in milliseconds for watched services
    .stop_on_exit() # cancel service before python vm quit
    .start())
client.hang() # hang just for test
```
