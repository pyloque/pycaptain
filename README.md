Captain
--------------------------
Captain is yet another service discovery implementation based on redis.
Captain sacrifices a little high availability for simplicity and performance.
In most cases, we dont have so many machines as google/amazon.
The possibility of machine crashing is very low, high Availability is not so abviously important yet.
But the market only provides zookeeper/etcd/consul, they are complex, at least much complexer compared with captain.

Use Captain Python Client
---------------------------
```python
from pycaptain import CaptainClient, ServiceItem, IServiceObserver


class ServiceCallback(IServiceObserver):

    def online(self, name):
        print name, "is ready"

    def all_online(self):
        print "service4 is all ready"
        print client.select("service1").url_root() // client can use the service now
        print client.select("service2").url_root()

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
