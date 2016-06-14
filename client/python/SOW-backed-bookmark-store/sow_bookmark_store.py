#
# sow_bookmark_store.py
#
# A very simple bookmark store that uses an AMPS State of the World (SOW) topic
# for persistence.  See the inline documentation for details.
#
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

"""
This bookmark store uses AMPS to persist progress through a bookmark
subscription. The store publishes an update to AMPS as each message is
discarded.

This bookmark store is designed to support a specific application
scenario. There are important limitations with this store (described following)
and there are prerequisites required to use this bookmark store. The
implementation assumes that these prerequisites are met and that the store
is used within the limitations described. If this bookmark store is used
in another environment, it may throw exceptions or skip messages on recovery.


Usage:
    -To use this bookmark store ensure that the config has the properly defined topic, then call:
     "haclient.set_bookmark_store(sow_bookmark_store.sow_bookmark_store(bkmrkclient, "/amps/bookmarkStore", "haclient"))"
     In this example:
         bkmrkclient: the client that will become our internal bookmark client
         "bookmarkStore": the SOW topic defined in the config that will be used for the bookmark store.
         "haclient": the name of the client whos bookmarks we will be storing
    -Calling haclient.discard(message) will update the bookmark store.
        -On recovery, this message is considered the last message processed by the subscriber.


Using this store has the following prerequisites:
    - This store requires access to an AMPS instance that contains a SOW
      topic defined as follows: 
        example:
            <TopicDefinition>
                <Topic>/amps/bookmarkStore</Topic>
                <FileName>./data/sow/bookmark.sow</FileName>
                <MessageType>json</MessageType>
                <Key>/clientName</Key>
                <Key>/subId</Key>
            </TopicDefinition>
    - There is NO requirement that the instance that contains the store
      must be the same instance where the subscription is placed.
    - As with any bookmark store, the topic for the subscription must be
      recorded in the transaction log.
    - When constructing the bookmark store, you must provide a client that
      is connected and logged on to the instance that contains the
      `/amps/bookmarkStore` topic.
      THIS MUST NOT BE THE CLIENT THAT WILL PLACE THE SUBSCRIPTION


Usage:
    - Create a client for the bookmark store to use. This client must be
      connected and logged on to the instance that contains the topic described
      above.
    - Construct an HAClient for your application to use.
    - Construct and set the bookmark store for the HA client as follows:
      "haclient.set_bookmark_store(sow_bookmark_store.sow_bookmark_store(bkmrkclient, "/amps/bookmarkStore", "haclient"))"
      In this example:
          bkmrkclient: the client that will become our internal bookmark client
         "bookmarkStore": the SOW topic defined in the config that will be used for the bookmark store.
         "haclient": the name of the client whos bookmarks we will be storing
    - Call haclient.discard(message) for each message from a bookmark
      subscription when the client is done with it. Each call to discard
      will update the bookmark store.
        -On recovery, this message is considered the last message processed by the subscriber.

Restrictions:
    - This implementation does not support Bookmark Live subscriptions: do
      not use the "live" option on subscriptions that use this store.
    - This implementation requires that messages are discarded precisely
      in the order in which they are received.
    - This implementation should not be used for replicated topics.
    - You must use this bookmark store with an HAClient.
    - The client provided to the bookmark store MUST NOT be the client
      that places the subscription. 

Important Notes:
    -discard(message) will throw an exception if client is not connected.
        -This exception should be handled by the caller.
        -Exceptions are not thrown if the client is connected, but
         fails to write (for example, due to lack of entitlements).

"""
import json
import AMPS


class sow_bookmark_store:
    def __init__(self, bookmark_client, topic, tracked_client_name):
        """ Class for creating and managing a SOW bookmark store

        :param bookmark_client: The client that will become the bookmark store internal client
        :type bookmark_client: AMPS.HAClient

        :param topic: The SOW topic defined in the config that will be used for the bookmark store.
        :type topic: string

        :param tracked_client_name: The name of the client whos bookmarks we will be storing.
        :type tracked_client_name: string

        :raises AMPS.AMPSException: if the internal client fails to query the SOW.

        """
        self._internalClient = bookmark_client
        self._trackedName = tracked_client_name
        self._topic = topic
        self._mostRecentBookmark = {}

        try:
            for message in self._internalClient.sow(self._topic, "/clientName = '%s'" % self._trackedName):
                if message.get_command() != 'sow':
                    continue

                data = message.get_data()
                bookmark_data = json.loads(data)

                if 'bookmark' in bookmark_data and 'subId' in bookmark_data:
                    self._mostRecentBookmark[bookmark_data['subId']] = bookmark_data['bookmark']
        except AMPS.AMPSException as aex:
            raise AMPS.AMPSException("Error reading bookmark store", aex)

    def set_server_version(self, version):
        """ Internally used to set the server version so the store knows how to deal
            with persisted acks and calls to get_most_recent().

        :param version: The version of the server being used.
        :type version: int

        """
        pass

    def get_most_recent(self, subid):
        """ Returns the most recent bookmark from the store that ought to be used for (re-)subscriptions.

        :param subid: The id of the subscription to check.
        :type subid: string

        :returns: mostRecentBookmark[subid] or '0'

        """
        # if we have a most recent value for that subId, then we'll return it
        # if not, we return EPOCH
        if subid in self._mostRecentBookmark:
            return self._mostRecentBookmark[subid]
        else:
            return '0'

    def is_discarded(self, message):
        """ Called for each arriving message to determine if the application has already seen this bookmark and
        should not be reprocessed. Returns 'true' if the bookmark should not be re-processed, false otherwise.

        :param message: The message to check
        :type message: AMPS.Message

        :returns: True or False

        """
        # since messages are being processed in order, we never see a discarded message.
        return False

    def log(self, message):
        """ Log a bookmark to the store.

        :param message: The message to log in the store
        :type message: AMPS.Message

        :returns: The corresponding bookmark sequence number for this bookmark.

        """
        # since we only ever have one SOW record per _trackedName and subId pair, this can
        # always return '1'
        return '1'

    def persisted(self, subid, bookmark):
        """ Mark all bookmarks up to the provided one as replicated to all replication destinations
        for the given subscription.

        :param subid: The subscription Id to which to bookmark applies
        :type subid: string

        :param bookmark: The most recent bookmark replicated everywhere.
        :type bookmark: string

        """
        # Bookmark Live and Replication are not supported, so this does nothing.
        pass

    def discard_message(self, message):
        """ Mark a message as seen by the application.

        :param message: The message to mark as seen.
        :type message: AMPS.Message

        :raises AMPS.AMPSException: if the internal client cannot publish to the server.
        """
        subid = message.get_sub_id()
        bookmark = message.get_bookmark()
        if bookmark is None or subid is None:
            return
        msg = '{"clientName": "%s", "subId": "%s", "bookmark": "%s"}' % (self._trackedName, subid, bookmark)
        try:
            self._internalClient.publish(self._topic, msg)
            self._mostRecentBookmark[subid] = bookmark
        except AMPS.AMPSException as aex:
            raise AMPS.AMPSException("Error updating bookmark store", aex)

    def discard(self, subid, seqnumber):
        """ Deprecated, Use discard(message) instead.

        :param subid: The id of the subscription to which the bookmark applies
        :type subid: string

        :param seqnumber: The bookmark sequence number to discard.
        :type seqnumber: string

        """
        # deprecated, use discard(message)
        pass
