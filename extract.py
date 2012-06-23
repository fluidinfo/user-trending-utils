#!/usr/bin/env python

"""
This script prints a summary of the URLs and hashtags from all user's
fluidinfo.com/social-trending tags.

It reads lines from the social_auth_usersocialauth table in the obrowser
database on fluiddb.fluidinfo.com.  To prepare an input file, run this:

 $ sudo -u postgres psql -A -t -c "SELECT extra_data FROM \
   social_auth_usersocialauth WHERE provider = 'fluidinfo'" obrowser

Note that the input file must not be added to the source code repo for this
script as it contains user OAuth tokens.
"""

from json import loads
import sys
from fom.session import Fluid
from fom.errors import Fluid404Error

TAG = 'fluidinfo.com/social-trending'
fdb = Fluid()
names = []

for line in sys.stdin:
    names.append(loads(line[:-1])['fluidinfoUsername'])

print 'Found %d users.' % len(names)

for name in sorted(names):
    try:
        trending = loads(fdb.about[u'@' + name][TAG].get().value)
    except Fluid404Error:
        print '%20s: no instance.' % name
    else:
        print '%20s: ht=%d urls=%d' % (name,
                                       len(trending['hashtags']),
                                       len(trending['urls']))
        for ht in trending['hashtags']:
            print '%20s  %s (%d)' % (
                '', ht['value'].encode('utf-8'), ht['count'])
        for url in trending['urls']:
            print '%20s  %s (%d)' % (
                '', url['value'].encode('utf-8'), url['count'])
    print >>sys.stderr, name
