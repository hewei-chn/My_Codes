#!/usr/bin/python
# -*- coding: utf-8 -*-
# weihe#corp.netease.com
# A scribe client to update logs.

import os
import datetime
import time
import pyinotify
import logging
import ConfigParser
import re
import socket
import signal
import sys

import cPickle

from scribe import scribe
from thrift.transport import TTransport, TSocket
from thrift.protocol import TBinaryProtocol

ROTATE_MAX=2
BUF_MAX=1024*100
NEEDEXIT=False

def SignalHandler(sig, id):
	global NEEDEXIT
	global DATAFILE
	if sig == signal.SIGUSR1:
		print 'received signal USR1'
	elif sig == signal.SIGHUP:
		print 'received signal HUP'
	elif sig == signal.SIGTERM:
		print 'received SIGTERM, shutting down'
		savefileinfo(DATAFILE)
		exit()
	elif sig == signal.SIGINT:
		print 'received SIGINT, shutting down'
		savefileinfo(DATAFILE)
		exit()

def savefileinfo(datafile):
	global file_info
	for k,v in file_info.items():
		print k,
		v.dump()
	f = open(datafile, "w")
	cPickle.dump(file_info,f)
	f.close()

def loadfileinfo(datafile):
	global file_info
	f = open(datafile, "r")
	file_info = cPickle.load(f)
	f.close()
	for k,v in file_info.items():
		print k,
		v.dump()

def parse_args():
	"""Parse Args Functions"""
	global options
	from optparse import OptionParser
	usage = "usage: %prog [options] [logname1] [logname2]"

	parser = OptionParser(usage=usage, version='%prog v0.2', description="A Simple tool to monitor somefile.")
	parser.add_option("-v", "--verbose", action="count",default=0,
					dest="verbose", help="Verbose mode")
	parser.add_option("-H", "--host", metavar="a.b.c.d", type='string',default="127.0.0.1",
					dest="server_host", help="Server's IP addr")
	parser.add_option("-p", "--port", metavar="1463", type='int',default=1463,
					dest="server_port", help="Server's Listen Port.")
	parser.add_option("-n", "--number", metavar="100", type='int',default=100,
					dest="log_count", help="send logs to server if new log number is more then this.")
	parser.add_option("-t", "--type", metavar="systemname", type='string',default="test",
					dest="type", help="Log's System name")
	parser.add_option("-s", "--subtype", metavar="subsystemname", type='string',
					dest="type", help="Log's Subsystem name")
	parser.add_option("-f", "--file", metavar="monitored_log_files", type='string',
					dest="file", help="Log's Subsystem name")
	parser.add_option("-r", "--rotate", metavar="rotatemode", type='int',
					dest="rotate", help="RotateMode 1 for move old file to file with data end\n\t 2 for Create New File for new Day.")
	parser.add_option("-c", "--continue", action = "store_true", default=True,
					dest="continue_flag", help="send log after we started")
	parser.add_option("-F", "--full", action = "store_false", 
					dest="continue_flag", help="send the full log ")
	
	(options, args) = parser.parse_args()
	if options.verbose:
		print options
		print "=============="
		print args
	
	global file_info

	if options.server_host:
		if options.verbose: print("Server_host:%s" % (options.server_host))
		if (options.server_host.find(':') > 0):
			options.server_port = options.server_host.split(":")[1]
	if options.server_port:
		if options.verbose: print("Server_port:%d" % (options.server_port))
	if not options.file or not os.path.isfile(options.file):
		print("You must specific an regular input file")
		parser.print_help()
		exit(3)

	options.file = os.path.realpath(options.file)
	fname = options.file

	if not options.rotate:
		rotate = filename_detech_rotate(fname)
		if rotate == 0:
			print "Detect Rotate Mode Failed, You Must Spec it with -r "
			exit(4)
		else:
			options.rotate = rotate

	if options.rotate > ROTATE_MAX:
		print "Rotate Mode Can't be Great then %d"%ROTATE_MAX
		exit(4) 
	elif options.rotate < 0:
		print "Rotate Mode Can't be Less then 1"
		exit(4) 

def filename_detech_rotate(fname):
	expname=fname.split('.')[-1]
	if re.match(r"20[0-9]{6}", expname):
		return 2
	return 1

class SendLog():
	def __init__(self):
		pass

	def file_send_log(self, fname):
		global file_info
		fsize = os.path.getsize(fname)
		fullfname=fname
		fname=os.path.basename(fullfname)
		if not file_info.has_key(fname):
			print("File %s add to monitor logs.", fname)
			file_info[fname] = FileInfo()
			return;
		if fsize < file_info[fname]:
			print("File %s is been tracated?", fname)
			file_info[fname] = FileInfo()
			return;
		fobj = open(fname)
		fobj.seek(file_info[fname].getOffset())
		line = fobj.readline()
		while line:
			print line
			line = fobj.readline()
		file_info[fname].setOffset(fobj.tell())
		fobj.close()

def gen_new_fname(fname, rotate, rotate_days = 1):
	if rotate == 1:
		return fname
	if rotate == 2:
		expname=fname.split('.')[-1]
		nextday=time.strftime('%Y%m%d',time.localtime(time.time()+3600*24*rotate_days))
		fname = fname.replace(expname, nextday)
		return fname
	return

class FileInfo:
	global options
	def __init__(self, offset = 0, log_count = 0):
		self.offset = offset
		self.log_count = log_count
		self.time = time.time()
	def isTimeout(self):
		#print "time=%0.2f self.time=%02.f"%(time.time(), self.time)
		return (time.time() - self.time) > 5
	def isNeedLog(self):
		self.log_count += 1
		return self.log_count > options.log_count;
	def setOffset(self, offset, log_count = 0):
		self.offset = offset;
		self.time = time.time();
		self.log_count = log_count;
		return
	def getOffset(self):
		return self.offset
	def getLogcount(self):
		return self.log_count
	def dump(self):
		print "offset = %u, log_count = %d, time = %d"%(self.offset, self.log_count, self.time)


class MyEventHandler(pyinotify.ProcessEvent):
	global file_info
	global options
	def __init__(self, fname, rotate, log_class):
		pyinotify.ProcessEvent.__init__(self)
		self.rotate = rotate
		self.fname = os.path.basename(fname)
		self.path = os.path.dirname(os.path.realpath(fname))
		self.newfname = []
		self.log_class = log_class
		self.init_new_file()
	def init_new_file(self):
		if not self.rotate or self.rotate == 0:
			for i in range(1,ROTATE_MAX):
				newname=gen_new_fname(self.fname,i)
				if not newname in self.newfname:
					self.newfname.append(newname)
		else:
			newname=gen_new_fname(self.fname,self.rotate)
			if not newname in self.newfname:
				self.newfname.append(newname)
		return
	def check_file_timout(self):
		for fname,node in file_info.items():
			#print fname,node
			if file_info[fname].isTimeout():
				print ("%s/%s is TimeOut"%(self.path,fname))
				self.log_class.file_send_log(os.path.join(self.path, fname))
	def process_IN_MODIFY(self, event):
		self.check_file_timout()
		if (options.verbose):
			print event
		if event.dir:
			return
		fname = os.path.basename(event.pathname)
		fullfname=event.pathname
		if file_info.has_key(fname):
			#print self.log_class
			if not file_info[fname].isNeedLog():
				return
			else:
				self.log_class.file_send_log(fullfname)
		else:
			print "Ignore File Change of %s"%fname
	def process_IN_MOVED_TO(self, event):
		self.check_file_timout()
		if (options.verbose):
			print event
		if not event.src_pathname:
			return
		if event.dir:
			return
		if os.path.dirname(event.pathname) != os.path.dirname(event.src_pathname):
			return
		orig_fname = os.path.basename(event.src_pathname)
		fname = os.path.basename(event.pathname)
		fullfname = event.pathname
		if file_info.has_key(orig_fname):
			file_info[fname] = file_info[orig_fname]
			del file_info[orig_fname]
			self.log_class.file_send_log(fullfname)
			del file_info[fname]
			if (options.verbose):
				print "Move File %s to %s"%(orig_fname, fname)
	def process_IN_CREATE(self, event):
		self.check_file_timout()
		if (options.verbose):
			print event
		if event.dir:
			return
		fullfname=event.pathname
		fname=os.path.basename(event.pathname)
		if fname in self.newfname:
			print("Get the New File %s", event.pathname)
			self.newfname.remove(fname)
			self.init_new_file()
			file_info['fname'] = FileInfo()
			self.log_class.file_send_log(fullfname)
	def process_default(self, event):
		self.check_file_timout()
		if (options.verbose):
			print event
		 
		
	

class ScribeClient(SendLog):
	"""Python Client For Scribe_Client."""
	global options
	global file_info
	def __init__(self):
		print "init"
		self.transport = None
		self.client = None
		self.connected = 0
	def connect(self, host, port):
		socket = TSocket.TSocket(host=host, port=port)
		self.transport = TTransport.TFramedTransport(socket)
		protocol = TBinaryProtocol.TBinaryProtocol(trans=self.transport, strictRead=False, strictWrite=False)
		self.client = scribe.Client(iprot=protocol, oprot=protocol)
		self.connected = 1
		self.thriftEx = TTransport.TTransportException();
	def disconnect(self):
		if (self.transport.isOpen()):
			self.transport.close()
		self.client.shutdown()
		self.connected = 0
	def isConnected(self):
		return self.connected
	def file_send_log(self, fname):
		fullfname = fname;
		fname=os.path.basename(fullfname)
		fsize = os.path.getsize(fullfname)
		if not file_info.has_key(fname):
			print("File %s add to monitor logs."%fname)
			file_info[fname] = FileInfo()
			return;
		if fsize < file_info[fname]:
			print("File %s is been tracated?"%fname)
			file_info[fname] = FileInfo()
			return;
		fobj = open(fullfname)
		fobj.seek(file_info[fname].getOffset())
		if (not self.transport.isOpen()):
			try:
				self.transport.open()
			except TTransport.TTransportException, self.thriftEx:
				print self.thriftEx
				file_info[fname].setOffset(fobj.tell())
				fobj.close()
				return -1
		buf = fobj.read(BUF_MAX)
		while buf and len(buf) > 0:
			log_entry = scribe.LogEntry(category=options.type, message=buf)
			try:
				self.client.Log(messages=[log_entry])
			except TTransport.TTransportException, self.thriftEx:
				print self.thriftEx
				fobj.seek(-len(buf),1)
				self.transport.close()
				break
			except socket.error, socketex:
				print socketex
				fobj.seek(-len(buf),1)
				self.transport.close()
				break
			else:
				buf = fobj.read(BUF_MAX)
		file_info[fname].setOffset(fobj.tell())
		fobj.close()

	def monitorfile(self, file, rotate):
		wm = pyinotify.WatchManager()
		wm.add_watch(os.path.dirname(file), pyinotify.ALL_EVENTS, rec=True)
		eh = MyEventHandler( fname = file, rotate = rotate, log_class = self)
		notifier = pyinotify.Notifier(wm, eh)
		notifier.loop()
		
	def run(self):
		self.connect(options.server_host, options.server_port)
		self.monitorfile(file = options.file, rotate = options.rotate)
		

if __name__ == '__main__':
	global file_info
	global options
	global DATAFILE
	signal.signal(signal.SIGUSR1, SignalHandler)
	signal.signal(signal.SIGHUP, SignalHandler)
	signal.signal(signal.SIGTERM, SignalHandler)
	signal.signal(signal.SIGINT, SignalHandler)
	file_info = {}
	parse_args()
	fname = options.file

	datapath=os.path.dirname(os.path.realpath(sys.argv[0]))
	if (options.rotate == 2):
		datafilename=os.path.basename(fname)[0:os.path.basename(fname).rindex('.')]+".data"
	else:
		datafilename=os.path.basename(fname)+".data"
	DATAFILE=os.path.join(datapath, "..", "data", datafilename)

	if (options.continue_flag):
		if (os.path.exists(DATAFILE) and os.path.getsize(DATAFILE) > 0):
			print "Load FileInfo from fileinfo.data..."
			loadfileinfo(DATAFILE)
		if not file_info.has_key(os.path.basename(fname)):
			print "File Name not in stored Data, Init with current state"
			file_info[os.path.basename(fname)] = FileInfo(offset=os.path.getsize(fname))
	else:
		print "All the Log of %s will be Send."
		file_info[os.path.basename(fname)] = FileInfo()

	sc = ScribeClient()
	sc.run()

