#!/bin/bash

# Created by weihe#corp.netease.com 20130228
# Use This Script to Add Script Type for php Scripts.
# Version v0.1
# Usage: Generate Filelist with find or Something else.
#			then ./php_script_4to5.sh [FileList] [BackPath]

function usage() {
	echo "Create FileList by Find or Other tools."
	echo "Usage: $0 [FileList] [BackPath]"
	echo "File will be Backup into BackPath and Log in BackPath/FileList.done"
	exit -1;
}

if [ $# -ne 2 ] || [ ! -s $1 ] ;then
	usage $0
fi

if [ ! -d $2 ] && ! mkdir -p $2 ;then
	echo "Create Dirctory $2 For Backup Failed!"
	usage $0
fi

BACKUPDIR=$2
LOGS=$2/`basename ${1}`.done

echo $LOGS
exit 1;

cp $1 ${BACKUPDIR}/

for file in `cat $1 | grep php$`; do
	echo "Deal with File ${file}"
	echo -n ${file} >>${LOGS}
	LINENUM=`grep "<?$" ${file} | wc -l`
	if [ ${LINENUM} -gt 0 ];then
		sed -i "s/<?$/<?php/g" $file
		FILEDIR=`dirname ${file}`
		mkdir -p ${BACKUPDIR}/${FILEDIR}
		cp -f ${file} ${BACKUPDIR}/${file}
		echo " Changed ${LINENUM} Lines" >>${LOGS}
	else
		echo " Leave Unchanged">>${LOGS}
	fi
done



