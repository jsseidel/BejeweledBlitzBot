#!/usr/bin/python

import sys
import bbbot as config

def main():
	if len(sys.argv) != 3:
		print 'Usage: capture_gridcells_gameboard.py <gameboard file> <outputdir>'
		sys.exit(1)

	n=0
	for y in range(8):
		for x in range(8):
			config.grabGridCellBMP(sys.argv[1], sys.argv[2] + '/' + str(x) + '_' + str(y) + '.png', x, y)
			n += 1

if __name__ == '__main__':
  main()  
