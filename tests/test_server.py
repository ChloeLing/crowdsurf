from twisted.internet.defer import Deferred
from twisted.trial.unittest import TestCase
from twisted.internet.protocol import Protocol, ClientFactory
import client, server
import sys
sys.path.append('tests')
from test_MockBrowser import MockBrowser

"""
  General architecture:
  1. A master server that hands out work
     - A work unit is finished when it has received when either
          a) A stderr & stdout report
       or b) An exception report
     - double-check that all units come back
       retry a work-unit after a 1.5 min timeout
  2. A set of slaves that request work
     - Each slave has a watchdog, to ensure 3 per computer
"""

class CrowdClientTest(TestCase):

  def setUp(self):
    factory = server.CrowdFactory(MockBrowser())
    from twisted.internet import reactor
    self.port = reactor.listenTCP(0, factory, interface="127.0.0.1")
    self.portnum = self.port.getHost().port

  def tearDown(self):
    port, self.port = self.port, None
    del self.portnum
    return port.stopListening()

  def browse(self, command):
    from twisted.internet import reactor
    factory = client.CrowdFactory(command)
    reactor.connectTCP('127.0.0.1', self.portnum, factory)
    return factory.deferred

  def test_browser_results(self):
    """The browser returns results successfully"""
    print 'testing'
    command = {
        'exec': '../tests/testBrowser',
        'domain':'-a 1000',
        'browsetime': '.1'}
    d = self.browse(command)
    print 'browsing'
    def got_result(r):
      print 'got_result', r
      self.assertEqual(r[0], 0)                    # check return code
      self.assertEqual(r[1], ('0'*1000, '1'*1000)) # check return value
    d.addCallback(got_result)
    return d

  # create a mock client, and send commands

