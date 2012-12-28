from twisted.python import failure
from twisted.internet import defer
from twisted.protocols.basic import NetstringReceiver
from twisted.internet.protocol import Protocol, ServerFactory
from browser import Browser
import optparse
import pickle
import os
import zlib

def parse_args():
  usage = """usage %prog [options]

  This is the CrowdSurfer Server. It waits for a client to request a page be
  surfed, and then responds with the surf results.
  """

  parser = optparse.OptionParser(usage)

  help = "The port to listen on. Default to a random available port."
  parser.add_option('--port', type='int', help=help, default=0)

  help = "The interface to listen on. Default is localhost."
  parser.add_option('--iface', help=help, default='localhost')

  options, args = parser.parse_args()

  if len(args) != 0:
    parser.error("Specify port or host using options flags.")

  return options, args

class CrowdProtocol(NetstringReceiver):

  def stringReceived(self, command):
    self.command = pickle.loads(command)
    d = self.factory.service.surf(self.command)
    d.addBoth(self.respond)
    return d

  def respond(self, result):
    print 'server.respond', type(result), result

    if isinstance(result, failure.Failure):
      print 'server.respond to failure', result
      self.command['results'] = result.getTraceback()
      self.sendString('log.' + pickle.dumps(self.command))

    elif isinstance(result, tuple):
      print 'server.browseResults are tuple'
      self.command['results'] = result[0]
      outfileName, errfileName = result[1]

      self.command['results'] = zlib.compress(open(outfileName, 'rb').read())
      self.sendString('out.' + pickle.dumps(self.command))
      os.remove(outfileName)

      self.command['results'] = zlib.compress(open(errfileName, 'rb').read())
      self.sendString('err.' + pickle.dumps(self.command))
      os.remove(errfileName)

    else:
      print 'server.Unknown Response', result
      self.command['results'] = result
      self.sendString('log.' + pickle.dumps(self.command))

    self.transport.loseConnection()

class CrowdFactory(ServerFactory):
  protocol = CrowdProtocol

  def __init__(self, service):
    self.service = service

class BrowseService(object):

  def surf(self, command):
    def results():
      bs = Browser(command)
      bs.start()
      bs.join()
      return bs.results

    return defer.maybeDeferred(results)

################################################################################

def main(options, args):
  factory = CrowdFactory(BrowseService())

  from twisted.internet import reactor
  port = reactor.listenTCP(options.port, factory, interface=options.iface)
  print 'CrowdServer %s on %s.'%(options.iface, port.getHost())
  reactor.run()

if __name__ == '__main__':
  main(*parse_args())
