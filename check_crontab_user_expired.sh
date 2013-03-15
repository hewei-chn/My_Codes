#!/bin/bash

# Created by weihe#corp.netease.com 20130315
# Use This Script to Make Sure that Users who have crontab to run will not expired.
# Version v0.1
# You should Run This Script once if you not sure about the user expired info with root permisson.

#if [ -z $1 ] ; then
	echo "We will Set the Users' Account & Password Nerver Expired."
#fi

if [ `whoami` != "root" ]; then
	echo "You must run with root privilege, Try run with sudo ?"
	exit 1
fi

if [ ! -d "/var/spool/cron/" ]; then
	echo "No User have use crontab. Nothing to do, Bye."
	exit 0;
fi

for file in `ls /var/spool/cron/`; do
	echo -ne "checking $file ...\t\t"
	COMMANDS=`cat /var/spool/cron/$file | grep -v ^$ | grep -v ^MAILTO | grep -v ^# | wc -l`
	if [ $COMMANDS -eq 0 ];then
		echo " No Commands in crontab, Skip it."
		continue;
	fi
	chage -l $file >/dev/null 2>&1
	if [ $? != 0 ];then
		echo "Failed to Check account info with RetCode $?, Skip it."
		continue;
	fi
	EXPINFO=`chage -l $file | grep -E ^"(Password|Account) expires" | grep -v never$`
	if [ ${#EXPINFO} -eq 0 ]; then
		echo "User Will Nerver Expired. Go to Next.."
		continue;
	else
		echo -n "Set Password And Account Expired to -1(never expired)..."
		chage -M -1 -E -1 $file
		echo "Done"
	fi
done

