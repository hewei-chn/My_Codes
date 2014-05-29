#!/bin/bash

if [ "x$1" == "x" ]; then
  echo "Usage: $0 all"
  exit 0
fi

CPUNUM=`cat /proc/cpuinfo | grep processor | wc -l`

NIC=$1

if [ "x$NIC" == "xall" ]; then
  LOCALOFFSET=0
  for nic in `ifconfig | grep "^[a-z]" | grep -v lo | awk {'print $1'} | tr "\n" " "`; do
    if [ `ethtool -i $nic | grep bus | grep "0000" | wc -l` -eq 1 ]; then
      MULTIIRQ=`cat /proc/interrupts | grep $nic | wc -l`
      bash $0 $nic $LOCALOFFSET
      let LOCALOFFSET=($LOCALOFFSET+$MULTIIRQ)%$CPUNUM
    fi
  done
  exit 0
fi



if [ "x$2" == "x" ] || [ $2 -lt 0 ] || [ $2 -gt $CPUNUM ]; then
  OFFSET=0
else
  OFFSET=$2
fi

MULTIIRQ=`cat /proc/interrupts | grep $NIC | wc -l`

if [ $MULTIIRQ -eq 0 ]; then
  echo "NIC $NIC not support MultiIRQ, exit."
  exit 0
fi



NUMANODLIST=(`numactl --hardware | grep cpus | head -n 1 | awk -F: {'print $2'}`)
NUMANODS=${#NUMANODLIST[@]}

if [ $OFFSET -ge $NUMANODS ]; then
  NUMANODLIST=(`numactl --hardware | grep cpus | head -n 2 | tail -n 1 | awk -F: {'print $2'}`)
  OFFSET=$(($OFFSET-$NUMANODS))
  NUMANODS=${#NUMANODLIST[@]}
fi

IRQS=(`cat /proc/interrupts | grep $NIC | awk -F: {'print $1'}`)

for ((i=0;i<${#IRQS[@]};i++)); do
  let CUROFFSET=($OFFSET+$i)%$NUMANODS
  cpu[$i]=${NUMANODLIST[$CUROFFSET]}
done

#echo ${cpu[@]} ${IRQS[@]}

for ((i=0;i<${#IRQS[@]};i++)); do
  echo Setup $NIC irq ${IRQS[$i]} to cpu ${cpu[$i]}
  echo ${cpu[$i]} > /proc/irq/${IRQS[$i]}/smp_affinity_list
done


   




