#!/bin/bash

SSDIR=~/Desktop/SS
DDIR=~/Desktop/d

n=0

ls $SSDIR | while read f ; do
	echo "in file = '$SSDIR/$f'"
	capture_gridcells_screen.py "$SSDIR/$f" $DDIR $n
	((n = n+1))
done

echo done
