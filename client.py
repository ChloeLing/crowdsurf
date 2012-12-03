#!/usr/bin/env python

from socket import *
import subprocess, multiprocessing, thread
import sys, os, time
import pickle, gzip
from optparse import OptionParser
import traceback

parser = OptionParser()
parser.add_option("--server", dest="server", help="server ip address", default='localhost')
parser.add_option("--number", dest="number", help="number of browsers to run", default=3, type="int")

PORT = 10000
BUFSIZE = 4096
BROWSE_TIME = 60 # seconds

class Browser(multiprocessing.Process):

  def __init__(self, server_ip):
    super(Browser, self).__init__()
    self._server_ip = server_ip

  def _connect(self):
    self._sock = socket(AF_INET, SOCK_STREAM)
    self._sock.connect((self._server_ip, PORT))

  def _disconnect(self):
    self._sock.close()
    self._sock = None

  def _send_file(self, local_fname, remote_fname):
    self._connect()
    self._sock.send('file ' + remote_fname + '\n')
    fi = open(local_fname, 'rb')
    print self.name, "sending file local:%s remote:%s of %d bytes"%(local_fname, remote_fname, os.path.getsize(local_fname))
    self._sock.sendall(fi.read())
    fi.close()
    self._disconnect()
    time.sleep(5)

  def _send_exception(self, exc_info, remote_fname):
    self._connect()
    self._sock.send('file ' + remote_fname + '\n')
    sexp = "".join(traceback.format_exception(*exc_info))
    print self.name, "sending exception of length %d"%len(sexp)
    print self.name, sexp
    self._sock.sendall(sexp)
    time.sleep(5)
    self._disconnect()

  def _fetch_command(self):
    self._connect()
    self._sock.sendall('get_command')
    data = self._sock.recv(BUFSIZE)
    self._disconnect()
    return data

  def _start_xpra(self, command):
    xpra = self._xpra_descriptor(command)
    self._stop_xpra(command)
    fnull = open(os.devnull, 'w')
    subprocess.call('xpra start %d'%xpra, stdout=fnull, stderr=fnull, shell=True)
    os.environ['DISPLAY'] = ':%d'%xpra
    time.sleep(1)

  def _stop_xpra(self, command):
    xpra = self._xpra_descriptor(command)
    fnull = open(os.devnull, 'w')
    subprocess.call('xpra stop %d'%xpra, stdout=fnull, stderr=fnull, shell=True)
    time.sleep(1)

  def _xpra_descriptor(self, command):
    return int(command['worknumber'])+100

  def run(self):
    while True:
      command = self._fetch_command()
      if command == "quit":
        self._sock.close()
        return

      command = pickle.loads(command)

      # surf webpage or catch an exception
      try:
        self._start_xpra(command)
        (fout_name, ferr_name) = self._surf(command)
        self._stop_xpra(command)

        self._send_file(fout_name, '%(results)s.out.gz'%command)
        self._send_file(ferr_name, '%(results)s.err.gz'%command)

      except:
        self._send_exception(sys.exc_info(), '%(results)s.exception'%command)

  def _surf(self, work):
    fname = '/tmp/%(browser)s-%(rank)s-%(domain)s.out.gz'%work

    outlog = gzip.open('/tmp/%(browser)s-%(rank)s-%(domain)s.out.gz'%work, 'wb')
    errlog = gzip.open('/tmp/%(browser)s-%(rank)s-%(domain)s.err.gz'%work, 'wb')
    print self.name, work['exec'] + ' browsing ' + work['domain']
    browser = subprocess.Popen([work['exec'], work['domain']], stdout=outlog, stderr=errlog)
    time.sleep(BROWSE_TIME)
    browser.terminate()
    outlog.close()
    errlog.close()

    return (outlog.filename, errlog.filename)

if __name__=='__main__':
  (options, args) = parser.parse_args()

  jobs = []
  for i in range(options.number):
     b = Browser(options.server)
     jobs.append(b)
     b.start()
  for j in jobs:
     j.join()
