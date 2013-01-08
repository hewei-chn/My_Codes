#!/bin/bash

# Created by weihe#corp.netease.com 20130108
# Use This Script to Archive logs monthly in gzip mode and back the orig log files in lastmonth dir.
# Version v0.1
# You should Add this script in your crontab or run it every month.


if [ -z $1 ] || [ ! -d $1 ];then
	echo "use $0 /path/have/logs/ to archive logs in the directory."
	echo "In Default we move file into archive dir with gzip compressed, and orig logs into lastmonth."
	echo "We also filtered the nagios check access log :)"
	exit -1;
fi

MONTH=`date +"%Y%m" -d "1 month ago"`
WORKDIR=$1
ARCHIVEDIR=archive
BACKUPDIR=lastmonth

cd $WORKDIR

for dir in log logs;do
	if [ -d $dir ];then
		cd $WORKDIR/$dir
		if [ ! -d ${ARCHIVEDIR} ];then
			mkdir ${ARCHIVEDIR};
		fi
		if [ ! -d ${BACKUPDIR} ];then
			mkdir ${BACKUPDIR};
		else
			rm -f ${BACKUPDIR}/*
		fi
		for logfile in `ls *${MONTH}* | awk -F. {'print $1'} | sort | uniq`;do
			echo Process ${logfile}
			for file in `ls ${logfile}.log.${MONTH}*`;do
				cat $file | grep -v " (nagios-plugins" | gzip >>${ARCHIVEDIR}/${logfile}.log.${MONTH}.gz
				mv $file ${BACKUPDIR}/
			done
		done
	fi
	cd $WORKDIR
done
