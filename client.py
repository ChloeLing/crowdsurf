import optparse
from twisted.internet import defer
from twisted.protocols.basic import NetstringReceiver
from twisted.internet.protocol import Protocol, ClientFactory
import os, pickle, zlib

def parse_args():
  usage = """usage %prog [options] {host:port}

  This is the CrowdSurf Client. It sends out a queue of browsing requests to
  a list of servers, and records the results.
  """

  parser = optparse.OptionParser(usage)

  options, args = parser.parse_args()

  if len(args) < 1:
    parser.error("Specify the list of servers.")

  def parse_address(addr):
    if ':' not in addr:
      host, port = '127.0.0.1', addr
    else:
      host, port = addr.split(':', 1)

    if not port.isdigit():
      parser.error('Ports must be integers.')

    return host, int(port)

  return options, map(parse_address, args)


class CrowdProtocol(NetstringReceiver):

  def connectionMade(self):
    print 'protocol.connectionMade'
    self.sendString(pickle.dumps(self.factory.command))

  def stringReceived(self, result):
    print 'protocol.stringReceived'
    act, data = result.split('.', 1)
    return self.factory.doAction(act, data)

  def connectionLost(self, reason):
    print 'protocol.connectionLost'

class CrowdFactory(ClientFactory):
  protocol = CrowdProtocol

  def __init__(self, command):
    self.deferred = defer.Deferred()
    self.command = command
    self.state = {'out': False, 'err': False, 'log': False}

  def doAction(self, action, data):
    print 'factory.doAction', action
    thunk = getattr(self, 'act_%s'%action, None)
    return thunk(data)

  def _fnames(self, command):
    errName = 'results/%(worknumber)s-%(browser)s-%(rank)s-%(domain)s.err'%command
    outName = 'results/%(worknumber)s-%(browser)s-%(rank)s-%(domain)s.out'%command
    logName = 'results/%(worknumber)s-%(browser)s-%(rank)s-%(domain)s.log'%command
    return {'out': outName, 'err': errName, 'log': logName}

  def act_log(self, data):
    data = pickle.loads(data)
    fname = self._fnames(data)['log']
    print 'factory.act_log', fname
    f = open(fname, 'w')
    f.write(data['results'])
    f.close()
    self.state['log'] = True

  def act_out(self, data):
    data = pickle.loads(data)
    fname = self._fnames(data)['out']
    print 'factory.act_out', fname 
    f = open(fname, 'wb')
    f.write(zlib.decompress(data['results']))
    f.close()
    self.state['out'] = True

  def act_err(self, data):
    data = pickle.loads(data)
    fname = self._fnames(data)['err']
    print 'factory.act_err', fname
    f = open(fname, 'wb')
    f.write(zlib.decompress(data['results']))
    f.close()
    self.state['err'] = True

  def clientConnectionFailed(self, connector, reason):
    if self.deferred is not None:
      d, self.deferred = self.deferred, None
      d.errback(reason)

  def clientConnectionLost(self, connector, reason):
    if self.deferred is not None:
      d, self.deferred = self.deferred, None

    if self.check_done():
      #TODO: re-add this command to worklist
      d.callback(None)
    else:
      d.errback(reason)

  def check_done(self):
    if self.state['out'] and self.state['err']:
      return True
    elif self.state['log']:
      return True
    else:
      return False

class BrowseService(object):
  count = 0

  def __init__(self, work, host, port):
    self.work = work
    self.host = host
    self.port = port

  def browse(self, _):
    try:
      command = self.work.next()
    except StopIteration:
      print 'browseService.stopiteration'
      self.finish()
      return None

    def check_done(failure):
      from twisted.internet.error import ConnectionDone
      e = failure.trap(ConnectionDone)
      factory.check_done(e)
      self.browse(None)

    from twisted.internet import reactor
    factory = CrowdFactory(command)
    connector = reactor.connectTCP(self.host, self.port, factory)
    factory.deferred.addCallback(self.browse)
    factory.deferred.addErrback(self.err)
    return factory.deferred

  def finish(self):
    print 'service.finish?', self.count
    BrowseService.count -= 1
    if BrowseService.count == 0:
      from twisted.internet import reactor
      reactor.stop()

  def err(self, arg):
    print 'service.I had an error:', arg
    arg.printBriefTraceback()
    return self.browse(None)

################################################################################

def genCommand():
  num = 0
  for i in range(1,60):
    for line in open('top-500.csv', 'r'):
      rank, domain = line.strip().split(',')
      for browser in os.listdir('browsers'):
        d = {'exec': 'browsers/' + browser + '/bin/QtTestBrowser',
             'browsetime': '10',
             'iter': str(i),
             'rank': rank,
             'domain': domain,
             'browser': browser,
             'worknumber': str(num) }
        num += 1
        yield d

class LockedIterator(object):
  def __init__(self, it):
    self._lock = threading.Lock()
    self._it = it.__iter__()

  def __iter__(self):
    return self

  def next(self):
    self._lock.acquire()
    try:
      return self._it.next()
    finally:
      self._lock.release()

################################################################################

def main(options, addrs):
  from twisted.internet import reactor

  BrowseService.count = len(addrs)
  gen = genCommand()
  for addr in addrs:
    host, port = addr
    BrowseService(gen, host, port).browse(None)

  reactor.run()

if __name__ == "__main__":
  main(*parse_args())
