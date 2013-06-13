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
		savefileinfoall()
		exit()
	elif sig == signal.SIGINT:
		print 'received SIGINT, shutting down'
		savefileinfoall()
		exit()

def savefileinfoall():
	global file_info
	for k,v in file_info.items():
		savefileinfo(k)
	return 0

def savefileinfo(filename):
	global file_info
	#for k,v in file_info.items():
	#	print k,
	#	v.dump()
	print filename,file_info[filename].getFname(),
	file_info[filename].dump()
	datafile = gen_data_fname(filename)
	f = open(datafile, "w")
	cPickle.dump(file_info[filename],f)
	f.close()
	return 0

def loadfileinfo(filename):
	#global file_info
	datafile = gen_data_fname(filename)
	if (os.path.exists(datafile) and os.path.getsize(datafile) > 0):
		f = open(datafile, "r")
		file_info = cPickle.load(f)
		f.close()
	else:
		return None
	print filename,file_info.getFname(),
	file_info.dump()
	return file_info

def parse_args():
	"""Parse Args Functions"""
	global options
	from optparse import OptionParser
	usage = "usage: %prog [options] [logname1] [logname2]"

	parser = OptionParser(usage=usage, version='%prog v0.3', description="A Simple tool to monitor somefile.")
	parser.add_option("-v", "--verbose", action="count",default=0,
					dest="verbose", help="Verbose mode")
	parser.add_option("-H", "--host", metavar="a.b.c.d", type='string',default="127.0.0.1",
					dest="server_host", help="Server's IP addr")
	parser.add_option("-p", "--port", metavar="1463", type='int',default=1463,
					dest="server_port", help="Server's Listen Port.")
	parser.add_option("-n", "--number", metavar="100", type='int',default=100,
					dest="log_count", help="send logs to server if new log number is more then this.")
	parser.add_option("-s", "--sysname", metavar="systemname", type='string',default="test",
					dest="sysname", help="Log's System name")
	parser.add_option("-S", "--subsysname", metavar="subsystemname", type='string',
					dest="subsysname", help="Log's Subsystem name")
	parser.add_option("-f", "--file", metavar="monitored_log_files", type='string',
					dest="file", help="Log's Subsystem name")
	parser.add_option("-r", "--rotate", metavar="rotatemode", type='int',
					dest="rotate", help="RotateMode 1 for move old file to file with data end\n\t 2 for Create New File for new Day.")
	parser.add_option("-c", "--config", metavar="scribe_client.conf", type='string',
					dest="config", help="spec the config file")
	parser.add_option("-F", "--full", action = "store_false", default=True,
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
	return options

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
			print("File %s not in monitor logs. Check you configs.", fname)
			#file_info[fname] = FileInfo(fname)
			return;
		if fsize < file_info[fname]:
			print("File %s is been tracated?", fname)
			file_info[fname].setOffset(0)
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
		expname=os.path.basename(fname).split('.')[-1]
		nextday=time.strftime('%Y%m%d',time.localtime(time.time()+3600*24*rotate_days))
		fname = fname.replace(expname, nextday)
		return fname
	return

def gen_data_fname(fname):
	datafname = ""
	names = fname.split(".")
	for subname in names:
		if (not subname.isdigit()):
			datafname = datafname + subname + "."
		else:
			break
	datafname = datafname.replace('/', '_')[1:] + "data"
	return os.path.join(DATAFILEPATH, datafname)

class FileInfo:
	global g_options
	def __init__(self, fname, sysname = None, offset = 0, log_count = 0, rotate = 0):
		self.__offset = offset
		self.__log_count = log_count
		self.__time = time.time()
		self.__fname = fname
		if rotate == None:
			self.__rotate = g_options.rotate
		else:
			self.__rotate = rotate
		if sysname == None:
			self.__sysname = g_options.sysname
		else:
			self.__sysname = sysname
	def isTimeout(self):
		#print "time=%0.2f self.time=%02.f"%(time.time(), self.time)
		return (time.time() - self.__time) > 5
	def isNeedLog(self):
		self.__log_count += 1
		return self.__log_count > g_options.log_count;
	def setOffset(self, offset, log_count = 0):
		self.__offset = offset;
		self.__time = time.time();
		self.__log_count = log_count;
		return
	def getOffset(self):
		return self.__offset
	def getLogcount(self):
		return self.__log_count
	def getRotate(self):
		return self.__rotate
	def getFname(self):
		return self.__fname
	def getCategory(self):
		return self.__sysname
	def newFile(self, rotate = -1):
		if (rotate != -1):
			if (self.__rotate != 0 and self.__rotate != rotate):
				print "Error Rotate %d, wanted is %d"%(rotate, self.__rotate)
				return None
		else:
			ratote = self.__rotate
		return FileInfo(fname = gen_new_fname(self.__fname, self.__rotate), rotate = rotate)
		
	def dump(self):
		print self.__offset, self.__log_count, self.__time, self.__rotate, self.__fname
		print "offset = %u, log_count = %d, time = %d, rotate = %d, fullname = %s"%(self.__offset, self.__log_count, self.__time, self.__rotate, self.__fname)


class MyEventHandler(pyinotify.ProcessEvent):
	global file_info
	global g_options
	def __init__(self, fname, rotate, log_class):
		pyinotify.ProcessEvent.__init__(self)
		self.rotate = rotate
		self.fname = fname
		#self.path = os.path.dirname(os.path.realpath(fname))
		self.newfname = {}
		self.log_class = log_class
		self.init_new_file()
	def init_new_file(self):
		for fname,v in file_info.items():
			if file_info[fname].getRotate() == 0:
				for i in range(1,ROTATE_MAX):
					newname=gen_new_fname(fname,i)
					if not newname in self.newfname.keys():
						self.newfname[newname] = file_info[fname].newFile(rotate=i)
			else:
				newname=gen_new_fname(fname,file_info[fname].getRotate())
				if not newname in self.newfname:
					self.newfname[newname] = file_info[fname].newFile()
		return
	def check_file_timout(self):
		for fname,node in file_info.items():
			#print fname,node
			if file_info[fname].isTimeout():
				print ("%s is TimeOut"%(fname))
				self.log_class.file_send_log(fname)
	def process_IN_MODIFY(self, event):
		self.check_file_timout()
		if (g_options.verbose):
			print event
		if event.dir:
			return
		fname = event.pathname
		if file_info.has_key(fname):
			#print self.log_class
			if not file_info[fname].isNeedLog():
				return
			else:
				self.log_class.file_send_log(fname)
		else:
			print "Ignore File Change of %s"%fname
	def process_IN_MOVED_TO(self, event):
		self.check_file_timout()
		if (g_options.verbose):
			print event
		if not event.src_pathname:
			return
		if event.dir:
			return
		if os.path.dirname(event.pathname) != os.path.dirname(event.src_pathname):
			return
		orig_fname = event.src_pathname
		fname = event.pathname
		if file_info.has_key(orig_fname):
			file_info[fname] = file_info[orig_fname]
			del file_info[orig_fname]
			self.log_class.file_send_log(fname)
			del file_info[fname]
			if (g_options.verbose):
				print "Move File %s to %s"%(orig_fname, fname)
	def process_IN_CREATE(self, event):
		self.check_file_timout()
		if (g_options.verbose):
			print event
		if event.dir:
			return
		fname=event.pathname
		if fname in self.newfname.keys():
			print("Get the New File %s", event.pathname)
			newfileinfo = self.newfname.pop(fname)
			newname = gen_new_fname(newfileinfo.getFname(), newfileinfo.getRotate())
			self.newfname['newname'] = newfileinfo.newFile();
			#self.init_new_file()
			file_info[fname] = newfileinfo
			self.log_class.file_send_log(fname)
	def process_default(self, event):
		self.check_file_timout()
		if (g_options.verbose):
			print event
		 
		
	

class ScribeClient(SendLog):
	"""Python Client For Scribe_Client."""
	global g_options
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
		fname=fullfname
		fsize = os.path.getsize(fullfname)
		if not file_info.has_key(fname):
			print("File %s didn't in monitor files. Check configs."%fname)
			#file_info[fname] = FileInfo(fname)
			return;
		if fsize < file_info[fname]:
			print("File %s is been tracated?"%fname)
			file_info[fname].setOffset(0)
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
			log_entry = scribe.LogEntry(category=file_info[fname].getCategory(), message=buf)
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

	def __format_param(self, param):
		"""
		@param param: Parameter.
		@type param: string or int
		@return: wrap param.
		@rtype: list of type(param)
		"""
		if isinstance(param, list):
			for p_ in param:
				yield p_
		else:
			yield param

	def monitorfile(self, rotate, file = []):
		wm = pyinotify.WatchManager()
		filelist = self.__format_param(file)
		dir = []
		for file in filelist:
			dir.append(os.path.dirname(file))
		wm.add_watch(dir, pyinotify.ALL_EVENTS, rec=True)
		eh = MyEventHandler( fname = file, rotate = rotate, log_class = self)
		notifier = pyinotify.Notifier(wm, eh)
		notifier.loop()
		
	def run(self):
		self.connect(g_options.server_host, g_options.server_port)
		self.monitorfile(file = g_options.file, rotate = g_options.rotate)

def parse_config(config_file):
	config = ConfigParser.ConfigParser()
	config.read(config_file)
	return config

class Goption():
	def __init__(self):
		self.server_host = None
		self.server_port = None
		self.file = []
		self.rotate = None
		self.verbose = None
		self.log_count = None
		self.sysname = None
		self.continue_flag = None
	def setup(self, options, config = None):
		global file_info

		#Init with the default value.
		self.server_host = options.server_host
		self.server_port = options.server_port
		self.verbose = options.verbose
		self.sysname = options.sysname
		self.continue_flag = options.continue_flag
		self.file.append(options.file)
		self.rotate = options.rotate

		if (options.file and not file_info.has_key(options.file)):
			fname = options.file
			local_file_info = None
			if (self.continue_flag):
				local_file_info = loadfileinfo(fname)
				if not local_file_info:
					print "Load FileInfo For %s Failed, will use current offset"%(fname)
					local_file_info = FileInfo(fname = fname, rotate = self.rotate, offset = os.path.getsize(fname), sysname = self.sysname)
			else:
				print "All the Log of %s will be Send."%(fname)
				local_file_info = FileInfo(fname = fname, rotate = self.rotate)
			file_info[fname] = local_file_info

		if (config == None):
			return

		s = "global"
		for o in config.options(s):
			if o == "host":
				self.server_host = config.get(s, o)
				if (options.server_host != self.server_host and options.server_host != "127.0.0.1"):
					print "[host]Options %s Override Config %s"%(options.server_host, self.server_host)
					self.server_host = options.server_host
			elif o == "port":
				self.server_port = config.getint(s, o)
				if (options.server_port != self.server_port and options.server_port != 1463):
					print "[port]Options %d Override Config %d"%(options.server_port, self.server_port)
					self.server_host = options.server_host
			elif o == "verbose":
				self.verbose = max(config.getint(s, o), options.verbose)
			elif o == "system":
				self.sysname = config.get(s,o)
				if (options.sysname != self.sysname and options.sysname != "test"):
					print "[systemname]Options %s Override Config %s"%(options.sysname , self.sysname)
					self.sysname = options.sysname
			elif o == "continue":
				self.continue_flag = config.getboolean(s, o)
				if (options.continue_flag != self.continue_flag and options.sysname != "test"):
					print "[systemname]Options %s Override Config %s"%(options.sysname , self.sysname)
					self.sysname = options.sysname
		
		for s in config.sections():
			if s != "global":
				fname = s
				if fname == options.file:
					print "[File] Options Override Config with file %s"%fname
					continue
				self.file.append(fname)
				rotate = 0
				continue_flag = True
				local_file_info = None
				sysname = self.sysname
				for o in config.options(s):
					if o == "rotate":
						rotate = config.getint(s,o)
					elif o == "sysname":
						sysname = config.get(s,o)
					elif o == "continue":
						continue_flag = config.getboolean(s, o)
				if (continue_flag == True or (continue_flag == None and self.continue_flag == True)):
					local_file_info = loadfileinfo(fname)
					if not local_file_info:
						print "Load FileInfo For %s Failed, will use current offset"%(fname)
						local_file_info = FileInfo(fname = fname, rotate = rotate, offset = os.path.getsize(fname), sysname = sysname)
				else:
					print "All the Log of %s will be Send."%(fname)
					local_file_info = FileInfo(fname = fname, rotate = rotate, sysname = sysname)
				file_info[fname] = local_file_info



if __name__ == '__main__':
	global file_info
	global g_options
	global DATAFILEPATH
	# DATAFILEPATH Must Define Before Parse Options And Config ,Cause some func may use it.
	datapath=os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), "..", "data")
	if (not os.path.isdir(datapath)):
		os.mkdir(datapath)
	DATAFILEPATH=datapath

	g_options = Goption()
	signal.signal(signal.SIGUSR1, SignalHandler)
	signal.signal(signal.SIGHUP, SignalHandler)
	signal.signal(signal.SIGTERM, SignalHandler)
	signal.signal(signal.SIGINT, SignalHandler)
	file_info = {}
	options = parse_args()
	config = None

	if (options.config):
		config = parse_config(options.config)

	g_options.setup(options, config)



	sc = ScribeClient()
	sc.run()

