#!/bin/bash
#Example For Bash_lock.inc.sh
#hewei.chn#gmail.com

source ./bash_lock.inc.sh

GetLock

Ret=$?
if [ $Ret -ne 0 ];then
	echo GetLockRet:$Ret
	exit 1
fi

sleep 10

ReleaseLock

echo ReleaseLockRet:$?

