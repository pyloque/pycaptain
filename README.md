Use Captain Python Client
---------------------------
```
git clone github.com/pyloque/pycaptain.git

from pycaptain import CaptainClient, ServiceItem, IServiceObserver


class ServiceCallback(IServiceObserver):

    def ready(self, name):
        print name, "is ready"

    def all_ready(self):
        print "service4 is all ready"

    def offline(self, name):
        print name, "is offline"


client = CaptainClient.origin("localhost", 6789)
(client.watch("service1", "service2", "service3")
    .provide("service4", ServiceItem("localhost", 6400))
    .observe(ServiceCallback())
    .stop_on_exit()
    .start())
client.hang() # hang just for test

```
