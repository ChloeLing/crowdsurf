
from twisted.trial.unittest import TestCase
from signal import SIGTERM
import time

"""Run a MockBrowser in a separate process, just to fiddle with the browser-server API"""

class MockBrowser(object):

  def run(self):
    print 'mockbrowser, running'
    from twisted.internet import defer
    try:
      return defer.succeed(self._surf())
    except Exception as e:
      return defer.fail(e)

  def _surf(self):
    from subprocess import Popen, PIPE
    browser = self.command['exec']
    domain = self.command['domain']

    bp = Popen([browser, domain], stdout=PIPE, stderr=PIPE)
    time.sleep(float(self.command['browsetime']))
    bp.terminate()

    bp.wait()
    return (bp.returncode, bp.communicate())

class MockBrowserTest(TestCase):
  
  def setUp(self):
    self.browser = MockBrowser()

  def tearDown(self):
    pass

  def test_browser_results(self):
    """The browser returns results successfully"""
    self.browser.command = {
        'exec': '../tests/testBrowser',
        'domain':'-a1000',
        'browsetime': '.1'}
    r = self.browser.run().result
    self.assertEqual(r[0], 0)                    # check return code
    self.assertEqual(r[1], ('0'*1000, '1'*1000)) # check return value
    return

  def test_browser_not_exist(self):
    self.browser.command = {
        'exec': '/tmp/notexist',
        'domain': '-'}
    r = self.browser.run()
    self.assertFailure(r, OSError)
    return

  def test_browser_terminate(self):
    """The browser has to be terminated, results should be short"""
    self.browser.command = {
        'exec': '../tests/testBrowser',
        'domain':'-a10000',
        'browsetime': '.01'}
    r = self.browser.run().result
    self.assertEqual(r[0], -SIGTERM)     # check return code
    self.assertIsInstance(r[1], tuple)   # check return type
    self.assertLess(len(r[1][0]), 10000) # check return value
    return

  def test_browser_segfault(self):
    """The browser crashed"""
    self.browser.command = {
        'exec': '../tests/testBrowser',
        'domain':'-f',
        'browsetime': '.1'}
    r = self.browser.run().result
    self.assertLess(r[0], 0) # check return code 
    return
