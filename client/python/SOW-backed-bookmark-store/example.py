# example.py
#
# Usage example for the sow_bookmark_store. 
#
# The MIT License (MIT)
#
# Copyright (c) 2016 60East Technologies
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

import sow_bookmark_store
import AMPS
import time

#  Handler
#
#  Simple message handler that prints each message, then
#  discards it.

class Handler:
    def __init__(self, client):
        self._client = client

    def __call__(self, message):
        print message.get_data()
        try:
            self._client.discard(message)
        except:
            self._client.disconnect()

# Main example begins here

# Construct a client for the bookmark store to use.
# For example purposes, this connects to the same instance that the
# main client will use.

bkmrkclient = AMPS.HAClient("bkmrk")
bkmrkchooser = AMPS.DefaultServerChooser()
bkmrkchooser.add("tcp://localhost:9007/amps/json")
bkmrkclient.set_server_chooser(bkmrkchooser)
bkmrkclient.connect_and_logon()



# Construct the client for the application to use.

haclient = AMPS.HAClient("haclient")
chooser = AMPS.DefaultServerChooser()
chooser.add("tcp://localhost:9007/amps/json")
haclient.set_server_chooser(chooser)

# Construct and set the bookmark store. Notice that the bookmark client
# is already constructed and connected.
haclient.set_bookmark_store(sow_bookmark_store.sow_bookmark_store(bkmrkclient, "/amps/bookmarkStore", "haclient"))

haclient.connect_and_logon()

haclient.bookmark_subscribe(Handler(haclient), "orders", "recent")

print "Subscribed, using the most recent bookmark."
print "Publishing some messages."

for i in xrange(10):
    haclient.publish("orders", "{'data':'%d'}" % (i))

time.sleep(2)

haclient.disconnect()

print "Disconnected the subscriber."

publisher = AMPS.HAClient("haclient-pub")
chooser2 = AMPS.DefaultServerChooser()
chooser2.add("tcp://localhost:9007/amps/json")
publisher.set_server_chooser(chooser2)
publisher.connect_and_logon()

print "Publishing messages from a separate publisher."

# publish a few messages while the client is disconnected.
for i in xrange(3):
    publisher.publish("orders", "{'data':'%d', 'publisher':'New publisher'}" % (i + 10))

print "Done publishing."
time.sleep(2)

print "Reconnecting the subscriber -- the subscription will resume and see the new messages."

haclient.connect_and_logon()

# will see the 3 messages that were published while the client is disconnected
time.sleep(2)

haclient.disconnect()
