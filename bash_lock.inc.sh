#!/bin/bash
# weihe#corp.netease.com 2013.04.09
# Single Run Lock Implement.
# Version 0.1


NAME=`basename $0`
FULLNAME=`readlink -f $0`
FULLPATH=`dirname $FULLNAME`
PID_FILE=$FULLPATH/.${NAME}.pid
LOCK_FILE=$FULLPATH/.${NAME}.lock
#WAIT Some Seconds to Get Lock.
WAIT_TIME=1

function GetLock(){
#@Start We Lock Files To  Check & Create Pid Files..
echo PID = $$
(
#Check With No wait. 
flock -xon 200
if [ $? -eq 0 ];then
	echo Lock OK!
	if [ -s ${PID_FILE} ];then
		RUNNINGPID=`head -n 1 ${PID_FILE}`
		if [ `ps ax | grep "^[ ]*$RUNNINGPID" | wc -l` -eq 0 ];then
			echo $$ > ${PID_FILE}
			echo Replace PidFile ${PID_FILE}. File is expired.
		else
			echo Somebody it\'s running This file \(${NAME}\) now..
			exit 1
		fi
	else
		echo $$ >> ${PID_FILE}
	fi
else
	echo Lock Failed
	exit 1
fi
) 200>$LOCK_FILE

RETCODE=$?
if [ $RETCODE -ne 0 ];then
	echo Lock Ret is $RETCODE
	return $RETCODE
fi
}

function ReleaseLock(){
#Done Remove the Pid Files... Wait Some Seconds to Hold the lock...
(
flock -xo -w ${WAIT_TIME} 200
if [ $? -eq 0 ];then
	echo Lock OK!
	if [ -s ${PID_FILE} ];then
		RUNNINGPID=`head -n 1 ${PID_FILE}`
		if [ $RUNNINGPID -eq $$ ];then
			unlink ${PID_FILE}
			echo Replace PidFile ${PID_FILE}. All Work is Done.
		else
			echo Somebody it\'s running This file \(${NAME}\) With Pid ${RUNNINGPID} now..
			exit 1
		fi
	else
		echo Who Delete My Pid ${RUNNINGPID} Files ...
		exit 2
	fi
else
	echo Lock Failed, Check The work..
	exit 3
fi
) 200>$LOCK_FILE

RETCODE=$?
return $RETCODE
}

function example(){

#GetLock First..
GetLock

if [ $? -eq 0 ];then
	echo Get Lock OK!
else
	echo Lock Failed
	exit 1
fi

#Do Something under Pid Files' Protect. Only one instance is running at a time.like Sleep ..

sleep 10


#Try ReleaseLock
ReleaseLock

if [ $? -eq 0 ];then
	echo ReleaseLock OK!
else
	echo ReleaseLock Failed!
fi

}
