#!/usr/bin/env python

import boto
import boto.ec2
import os, time
import paramiko
import commands

os.environ['AWS_SECRET_ACCESS_KEY']='ZvYlHK57Sa78wGBjlGqTuVcVtPQ0Y2IRePaAcUlO'
os.environ['AWS_ACCESS_KEY_ID']='AKIAI4AP5WMTAVRE2ELQ'

def wait_for_status(desired_status, instances):
  for instance in instances:
    status = instance.update()
    while status != desired_status:
      time.sleep(5)
      status = instance.update()

def get_all_slaves(connection):
  slaves = []
  for res in connection.get_all_instances():
    for inst in res.instances:
      if 'slave' not in inst.tags.get('Name', ''):
        continue
      if inst.update() not in ['running', 'stopped']:
        continue
      slaves.append(inst)
  return slaves

def get_all_masters(connection):
  masters = []
  for res in connection.get_all_instances():
    for inst in res.instances:
      if 'master' not in inst.tags.get('Name', ''):
        continue
      masters.append(inst)
  return masters

def runcommand(instance, command):
  print 'runcommand ', instance.private_ip_address, command
  ssh = paramiko.SSHClient()
  ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
  instance.update()
  ssh.connect(instance.private_ip_address, username='ubuntu', key_filename='/home/ubuntu/.ec2/crowdflow.pem')
  return ssh.exec_command(command)

def my_ip_address():
  return commands.getoutput('/sbin/ifconfig').split('\n')[1].split()[1][5:]

def rsync(instance, path):
  ssh_options = " ".join(["ssh",
                "-i", "/home/ubuntu/.ec2/crowdflow.pem",
                "-o", "UserKnownHostsFile=/dev/null",
                "-o", "StrictHostKeyChecking=no"])
  command = 'rsync '
  command += '-az '
  command += '-e "%s" '%ssh_options
  command += path + ' '
  command += instance.private_ip_address + ":" + path + ' '
  os.system(command)

def start_client(instance, num):
  command = 'daemon '
  command += '--name=crowdflow-client%d '%num
  command += '--chdir=/home/ubuntu/jsflow-tcp '
  command += '--command=/home/ubuntu/jsflow-tcp/client.py '
  command += '--stdout=/tmp/jsflow-client%d.py.stdout '%num
  command += '--stderr=/tmp/jsflow-client%d.py.stderr '%num
  command += '-- '
  command += '--server=%s '%my_ip_address()
  runcommand(instance, command)

def start_server(instance):
  command = 'daemon '
  command += '--name=crowdflow-server '
  command += '--chdir=/home/ubuntu/jsflow-tcp '
  command += '--command=/home/ubuntu/jsflow-tcp/server.py '
  command += '--stdout=/tmp/jsflow-server.py.stdout '
  command += '--stderr=/tmp/jsflow-server.py.stderr '
  runcommand(instance, command)

def create_slaves(ec2_conn, num):
  img = ec2_conn.get_image('ami-ac2504e9')
  res = img.run(num,num, key_name='crowdflow', security_groups=['crowdflow'], instance_type='t1.micro')
  i = 0
  for instance in res.instances:
    instance.add_tag('Name', 'slave%03d'%i)
    i += 1
  return res.instances

if __name__ == '__main__':
  ec2_conn = boto.ec2.connect_to_region('us-west-1')

  for master in get_all_masters(ec2_conn):
    start_server(master)

  # ensure that we have some fresh slaves
  slaves = get_all_slaves(ec2_conn)
  if not len(slaves):
    slaves = create_slaves(ec2_conn, 19)
  else:
    [s.reboot() for s in slaves]
    wait_for_status('running', slaves)

  for slave in slaves:
    rsync(slave, '/home/ubuntu/jsflow-tcp/')
    start_client(slave, 1)

  #TODO: detect when done, and terminate all the slaves

