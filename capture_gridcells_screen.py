#!/usr/bin/python

import sys
import bbbot as config

def main():
	if len(sys.argv) != 4:
		print 'Usage: capture_gridcells.py <game screenshot file> <outputfile dir> <outputfile prefix>'
		sys.exit(1)

	n=0
	for y in range(8):
		for x in range(8):
			config.grabScreenShotGridCellBMP(sys.argv[1], sys.argv[2] + '/' + sys.argv[3] + '_' + str(n) + '.png', x, y)
			n += 1

if __name__ == '__main__':
  main()  
