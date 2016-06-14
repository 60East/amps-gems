SOW-backed Bookmark Store
=========================

(c) 2016 60East Technologies, Inc.

Covered by the AMPS Gems license, available at
https://github.com/60East/amps-gems/blob/master/LICENSE


This gem is a very simple bookmark store that stores the current position of a
subscription to a SOW topic in AMPS. Should the application restart, this
bookmark store uses that SOW topic to recover the current position of the
subscription.

To keep the bookmark store simple, there are important limitations on how the
store can be used. See the inline documentation for details.

