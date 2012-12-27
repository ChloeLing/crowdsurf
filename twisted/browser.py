from StringIO import StringIO
import gzip
import os, sys, time
import multiprocessing, subprocess

class Browser(multiprocessing.Process):
  """Run a browser instance in a separate process"""

  def __init__(self, command):
    """command is a dictionary mapping (string->string)
       browser => string description of browser (crowd, crowd-full, condom, etc)
       exec    => the path to the browser executable
       domain  => domain of a website to surf
       rank    => The alexa ranking of the domain
       worknumber => A unique number representing the surfing task
       browsetime => Number of seconds to wait at the homepage of domain
    """
    super(Browser, self).__init__()
    self.command = command

  def run(self):
    from twisted.internet import defer
    self._start_xpra()
    try:
      return defer.succeed(self._surf())
    except Exception as e:
      return defer.fail(e)
    finally:
      self._stop_xpra()

  def _start_xpra(self):
    port = self._xpra_port()
    self._stop_xpra()
    fnull = open(os.devnull, 'w')
    subprocess.call('xpra start %d'%port,
        stdout=fnull, stderr=fnull, shell=True)
    os.environ['DISPLAY'] = ':%d'%port
    time.sleep(.1)

  def _stop_xpra(self):
    port = self._xpra_port()
    fnull = open(os.devnull, 'w')
    subprocess.call('xpra stop %d'%port,
        stdout=fnull, stderr=fnull, shell=True)
    os.environ.pop('DISPLAY', '')

  def _xpra_port(self):
    return int(self.command['worknumber']) + 1000

  def _logNames(self):
    outlog = '/tmp/%(browser)s-%(rank)s-%(domain)s.out.gz'%self.command
    errlog = '/tmp/%(browser)s-%(rank)s-%(domain)s.err.gz'%self.command
    return (outlog, errlog)

  def _surf(self):
    outlog = gzip.open(self._logNames()[0], 'wb')
    errlog = gzip.open(self._logNames()[1], 'wb')
    browser = self.command['exec']
    domain  = self.command['domain']

    bp = subprocess.Popen([browser, domain], stdout=outlog, stderr=errlog)
    time.sleep(float(self.command['browsetime']))
    bp.terminate()
    bp.wait()
    outlog.close()
    errlog.close()

    return (bp.returncode, (outlog.filename, errlog.filename))
