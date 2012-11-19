#!/usr/bin/env python

import os
import re
import sys

try:
  import psyco
  psyco.full()
except ImportError:
  print>>sys.stderr, 'Psyco not installed, the program will just run slower'


if len(sys.argv) < 3:
	print 'use '+sys.argv[0]+' inputdumpfile outputfile'
	sys.exit(2)

if not os.path.isfile(sys.argv[1]):
	print "Wrong Input File"+sys.argv[1]
	sys.exit(1)
if os.path.isfile(sys.argv[2]):
	print "File Exist! if you want overwrite it , delete "+sys.argv[2]+" first"
	sys.exit(1)

inputfile=open(sys.argv[1],'r')
outputfile=open(sys.argv[2],'w')

PlenthStr='Prop-content-length:'
PendStr='PROPS-END\n'
ClenthStr='Content-length:'

#svn_key=re.compile(r"^K (\d+)$")
#svn_value=re.compile(r"^V (\d+)$")
#svn_key_ignore='svn:ignore'
#svn_key_log='svn:log'


#Stat List
#0		Start
#1		After \n and stat 0,Maybe Start of New Section.Also Check list for write files.
#10		Revision Section
#11		Revision Have Prop Length
#12		Revision Have Content Length
#13		The "\n" of The end of HEAD.
#14		Revision Have 'K 7\n' Prop
#15		The 'svn:log\n'
#16		The Log Content.
#17


num = 0
stat = 0
len_diff = 0
linelist = [ ]
for eachLine in inputfile:
	if num == 0 and eachLine != 'SVN-fs-dump-format-version: 2\n':
		print 'unsupported svn dump version.'
		sys.exit(2)
	num = num + 1
#	if num > 100:
#		sys.exit(2)
#	print eachLine,stat,
	if stat == 0:
		if eachLine == '\n':
			stat = 1
	elif stat == 1:
		if (eachLine[0] == 'N' or eachLine[0] == 'R'):
			if eachLine[0:16] == 'Revision-number:':
				stat = 10
				linelist.append(eachLine)
				continue
			elif eachLine[0:10] == 'Node-path:':
				stat = 20
				linelist.append(eachLine)
				continue
		elif (eachLine == "\n"):
			stat = 1
		else:
			stat = 0
		while len(linelist):
			if len_diff > 0:
				print linelist[0],
			print >>outputfile, linelist.pop(0),
		if len_diff > 0:
			print "Changed before Line ", num, "\n"
		len_diff = 0
	elif stat == 10 or stat == 20:
		if eachLine[0] == 'P' and eachLine[0:len(PlenthStr)] == PlenthStr:
			plen = int(eachLine[len(PlenthStr):])
			plen_total = 0
			pindex=len(linelist)
			stat = stat + 1
		#Don't Have Prop Section. pop on next loop.
		elif eachLine[0] == '\n':
			stat = 1
		linelist.append(eachLine)
		continue;
	elif stat == 11 or stat == 21:
		if eachLine[0] == 'C' and eachLine[0:len(ClenthStr)] == ClenthStr:
			clen = int(eachLine[len(ClenthStr):])
			clen_total = 0
			cindex = len(linelist)
			stat = stat + 1 
		linelist.append(eachLine)
		continue
	elif stat == 12 or stat == 22:
		if eachLine == "\n":
			stat = stat + 1
		linelist.append(eachLine)
		continue
	elif stat == 13 or stat == 23:
		plen_total = plen_total + len(eachLine)
		clen_total = clen_total + len(eachLine)
		if (eachLine == "K 7\n"):
			stat = 14
		elif (eachLine == "K 10\n"):
			stat = 24
		elif eachLine == PendStr:
			if (plen != plen_total):
				print "plen = %d, plen_total = %d, but len(PendStr) is %d"%(plen, plen_total, len(PendStr))
				print "Warning , LINE CONTENT Error NEAR LINE ", num, "!"
			stat = 1
			if len_diff > 0:
				print "OLD:",linelist[pindex].replace('\n',''),linelist[cindex],
				linelist[cindex] = linelist[cindex].replace("%s"%(clen), "%s"%(clen - len_diff))
				linelist[pindex] = linelist[pindex].replace("%s"%(plen), "%s"%(plen - len_diff))
		linelist.append(eachLine)
		continue
	elif stat == 14 or stat == 24:
		plen_total = plen_total + len(eachLine)
		clen_total = clen_total + len(eachLine)
		if (eachLine == "svn:log\n" and stat == 14) or (eachLine == "svn:ignore\n" and stat == 24):
			stat = stat + 1
		else:
			stat = stat - 1
		linelist.append(eachLine)
		continue
	elif stat == 15 or stat == 25:
		plen_total = plen_total + len(eachLine)
		clen_total = clen_total + len(eachLine)
		if eachLine[0:2] == "V ":
			stat = stat + 1
			vlen = int(eachLine[2:])
			vindex = len(linelist)
			vlen_total=0
		else:
			print "FORMART ERROR NEAR LINE ",num, " !"
		linelist.append(eachLine)
		continue
	elif stat == 16 or stat == 26:
		plen_total = plen_total + len(eachLine)
		clen_total = clen_total + len(eachLine)
		vlen_total = vlen_total + len(eachLine)
		if eachLine.rfind('\r'):
			neweachLine = eachLine.replace('\r','')
			len_diff = len_diff + len(eachLine) - len(neweachLine)
			linelist.append(neweachLine)
		else:
			linelist.append(eachLine)
		if (vlen_total == vlen):
			if len_diff > 0:
				print "OLD:",linelist[vindex],
				linelist[vindex] = linelist[vindex].replace("%s"%(vlen), "%s"%(vlen - len_diff))
			stat = stat - 3
		continue
	print >>outputfile, eachLine,

inputfile.close()
outputfile.close()


		


