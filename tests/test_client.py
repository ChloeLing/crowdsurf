from twisted.trial.unittest import TestCase

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

class CrowdSurfClientTestCase(TestCase):

  def setUp(self):
    factory = CrowdSurfServerFactory()
    from twisted.internet import reactor
    self.port = reactor.listenTCP(0, factory, interface="127.0.0.1")
    self.portnum = self.port.getHost().port

  def tearDown(self):
    port, self.port = self.port, None
    return port.stopListening()

  def test_browser_segfault(self):
    """The browser has a segfault."""
    d = browse_results('127.0.0.1', self.portnum)

    def got_results(res):
      self.assertEquals(res, RESULTS)

    return d.addCallback(got_results)

  def test_absent_server(self):
    """Client returns a ConnectError when work server is absent"""
    d = browse_results('127.0.0.1', 0)
    return self.assertFailure(d, ConnectError)

