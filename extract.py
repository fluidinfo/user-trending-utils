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
from operator import attrgetter
import sys
from fom.session import Fluid
from fom.errors import Fluid404Error

fdb = Fluid()
users = {}


class User(object):
    def __init__(self, name):
        self.name = name
        self.followers = set()

    def addFollower(self, user):
        self.followers.add(user)

    def printAll(self):
        print 'USER %s:' % self.name
        self._printFollowers()

    def _printFollowers(self):
        print '  Followed by %d: %s' % (
            len(self.followers),
            ', '.join(list(user.name for user in self.followers)))

    @property
    def followersCount(self):
        return len(self.followers)


class VirtualUser(User):
    def __init__(self, name):
        User.__init__(self, name)
        self.real = False


class RealUser(User):
    def __init__(self, name):
        User.__init__(self, name)
        self.real = True

    def printAll(self):
        User.printAll(self)
        self._printFollowing()
        self._printTrending()

    def analyzeTrending(self):
        TAG = 'fluidinfo.com/social-trending'
        try:
            self.trending = loads(fdb.about[u'@' + self.name][TAG].get().value)
        except Fluid404Error:
            self.trending = None

    def _printTrending(self):
        if self.trending:
            if self.followsData:
                followsSummary = 'follows %d real users' % (
                    self.atnameCount - self.fakeAtnameCount)
            else:
                followsSummary = 'has no follows tag'
            print '  Trending summary for %s: hashtags=%d urls=%d (%s)' % (
                self.name, len(self.trending['hashtags']),
                len(self.trending['urls']), followsSummary)
            for hashtag in self.trending['hashtags']:
                print '    %s (%d)' % (
                    hashtag['value'].encode('utf-8'), hashtag['count'])
            for url in self.trending['urls']:
                print '    %s (%d)' % (
                    url['value'].encode('utf-8'), url['count'])
        else:
            print '  No trending tag instance.'

    def analyzeFollowing(self):
        try:
            self.followsData = fdb.values.get(u'has %s/follows' % self.name,
                                              [u'fluiddb/about']).value
        except Fluid404Error:
            self.followsData = None
        else:
            self.followingCount = len(self.followsData['results']['id'])
            self.follows = set()
            self.atnameCount = 0
            self.fakeAtnameCount = 0
            self.hashtagCount = 0
            self.urlCount = 0
            self.otherCount = 0
            for result in self.followsData['results']['id'].values():
                about = result['fluiddb/about']['value']
                if about.startswith('@'):
                    self.atnameCount += 1
                    followeeName = about[1:]
                    if followeeName not in users:
                        users[followeeName] = VirtualUser(followeeName)
                    followee = users[followeeName]
                    if not followee.real:
                        self.fakeAtnameCount += 1
                    followee.addFollower(self)
                    self.follows.add(followee)
                elif about.startswith('#'):
                    self.hashtagCount += 1
                elif about.startswith('http'):
                    self.urlCount += 1
                else:
                    self.otherCount += 1

    def _printFollowing(self):
        if self.followsData:
            print ('  Follows %d: %d atnames (%d fake), %d hashtags, '
                   '%d urls, %d other' % (
                       self.followingCount,
                       self.atnameCount,
                       self.fakeAtnameCount,
                       self.hashtagCount,
                       self.urlCount,
                       self.otherCount))
            followsReal = sorted([user.name for user in self.follows
                                  if user.real])
            if followsReal:
                print '    Follows %d real users: %s' % (
                    len(followsReal), ', '.join(followsReal))
        else:
            print '  Has no follows tag!'


def main():
    for line in sys.stdin:
        name = loads(line[:-1])['fluidinfoUsername']
        users[name] = RealUser(name)

    realUsers = sorted([user for user in users.values()],
                       key=attrgetter('name'))

    # The number of real users to analyze. Set to zero to do everyone.
    numberToAnalyze = 0

    for count, user in enumerate(realUsers):
        print >>sys.stderr, user.name
        user.analyzeTrending();
        user.analyzeFollowing();
        if numberToAnalyze and count == numberToAnalyze - 1:
            break

    print 'Found %d real users.' % len(realUsers)
    for count, user in enumerate(realUsers):
        user.printAll()
        if numberToAnalyze and count == numberToAnalyze - 1:
            break
        print

    fakeUsers = sorted([user for user in users.values() if not user.real],
                       key=attrgetter('followersCount'), reverse=True)
    print
    print 'Found %d fake users.' % len(fakeUsers)
    for user in fakeUsers:
        user.printAll()


if __name__ == '__main__':
    main()
