#!/usr/bin/python

#################################################
# This is a python script that, when tuned
# properly, can beat the Guinness world record
# for the Facebook version of Bejewled Blitz.
#################################################

import os
import math
import time
import sys
import random
import datetime

from autopy import bitmap
from autopy import color
from autopy import mouse

################################################# Things that change a lot

# When true, dumps the moves the script finds on the
# board and bails
DEBUG=False

# How long the script should run in seconds
GAME_TIME=90

# The x position of the pixel that represents the upper
# left-hand corner of the game grid. Find it by taking
# a screenshot of the game in play.
XOFF = 543

# The y position of the pixel that represents the upper
# left-hand corner of the game grid.
#
# For Macs, this number represents the y-position of the
# pixel that represents the upper left-hand corner of
# the game grid.
YOFFNOSCREEN=396

# The y position of the pixel that represents the upper
# left-hand corner of the game grid.
#
# For Linux/Windows, this is the same as the NOSCREEN
# number above.
#
# For Macs, this number should be set to:
#     SCREEN_HEIGHT - The BOTTOM left-hand corner of the game grid
YOFF=396

# These are (x,y) screen coordinates for the middle of the
# PLAY NOW button during normal play, when playing with a 
# rare gem loaded, and when in challenge mode.

# NORMAL
#PLAYX=633
#PLAYY=704
# WITH RARE GEM
PLAYX=633
PLAYY=720
# CHALLENGE
#PLAYX=513
#PLAYY=800

# These store extra DB prefixes
#   h1 = hypercube = imgdb/h1.png
#   h2 = hypercube = imgdb/h2.png
#   h3 = hypercube = imgdb/h3.png
#   h4 = hypercube = imgdb/h4.png
#   yc = yellow coin = imgdb/yc.png
#   wr2 = white rare 2 = imgdb/wr2.png
# If you use a different rare gem, you'll need to change/add to
# this list to reflect the right image in imgdb.
#
# I don't like to load them all because it isn't efficient to 
# search the image DB for images you know can't happen during
# a given game.

EXTRAIMGDBPREFIXES = ['h1', 'h2', 'h3', 'h4', 'yc', 'or1']

# Uncomment for whichever mode you'd like to play. In challenge
# mode, I've found that better scores can be acheived by waiting
# a bit longer between moves while stuff is exploding onscreen.

## CHALLENGE MODE
CHALLENGEMODE=False

if CHALLENGEMODE:
	TIMEBETWEENMOVES=1.5 # seconds
	TIMEBETWEENMOVESMAX=2.0 # seconds
	TIMEBETWEENMOVESMIN=1.5 # seconds
	SECSTODECREASEMOVETIME=45 # seconds
	NUMMOVESLONGWAIT=3
else:
	TIMEBETWEENMOVES=0.25 # seconds
	TIMEBETWEENMOVESMAX=0.75 # seconds
	TIMEBETWEENMOVESMIN=0.50 # seconds
	SECSTODECREASEMOVETIME=30 # seconds
	NUMMOVESLONGWAIT=5
################################################# END config

IMGDBPATH='./imgdb'
IMGDB=[]
CYCLESBEFOREPANIC=9999
NUMRANDOMSWAPS=20
PANICMOVES=10

W=320
H=320
GRIDW=40
GRIDH=40
GRIDX=20
GRIDY=20
GRIDCELLSAMPLEW=30
GRIDCELLSAMPLEH=30
NUMHISTBUCKETS=3
HISTMATCHTHRESH=300
IMGDB={}
THREEGEMMATCHPRI=0
FOURGEMMATCHPRI=500
FIVEGEMMATCHPRI=1000
HYPERMATCHPRI=2000

def genImgDBPrefixes():
	colors = ['r', 'g', 'b', 'y', 'p', 'w', 'o']
	pfxList = EXTRAIMGDBPREFIXES
	for color in colors:
		pfxList.append(color)	
		pfxList.append(color + 'f')	
		pfxList.append(color + 's')
		for mult in range(2, 9):
			pfxList.append(color + 'm' + str(mult))

	return pfxList

def loadImgDB(path):
	pfxList = genImgDBPrefixes()
	for pfx in pfxList:
		imgFile = path + '/' + pfx + '.png'
		if os.path.isfile(imgFile):
			print 'loading ' + imgFile
			xs = GRIDX - GRIDCELLSAMPLEW/2
			ys = GRIDY - GRIDCELLSAMPLEH/2
			bmp = openBMP(imgFile)	
			IMGDB[pfx] = computeHist(bmp.get_portion((xs, ys), (GRIDCELLSAMPLEW, GRIDCELLSAMPLEH)))

def computeHist(bmp):
	rh = [0 for i in range(NUMHISTBUCKETS)]
	gh = [0 for i in range(NUMHISTBUCKETS)]
	bh = [0 for i in range(NUMHISTBUCKETS)]

	for y in range(GRIDCELLSAMPLEH):
		for x in range(GRIDCELLSAMPLEW):
			(r, g, b) = color.hex_to_rgb(bmp.get_color(x, y))
			rh[r/int(math.ceil(256.0/float(NUMHISTBUCKETS)))] += 1
			gh[g/int(math.ceil(256.0/float(NUMHISTBUCKETS)))] += 1
			bh[b/int(math.ceil(256.0/float(NUMHISTBUCKETS)))] += 1

	return (rh, gh, bh)

def compHist(h1, h2):
	(rh1, gh1, bh1) = h1
	(rh2, gh2, bh2) = h2

	sum = 0
	for i in range(NUMHISTBUCKETS):
		sum += abs(rh1[i] - rh2[i]) + abs(gh1[i] - gh2[i]) + abs(bh1[i] - bh2[i])
	
	return sum

def dumpGridImgDBToFile(grid, f):
	for y in range(8):
		for x in range(8):
			f.write(grid[x][y].ljust(2) + ' ')
		f.write('\n')
	f.write('\n\n')

def	dumpGridHistCompareImgDBToFile(grid, bmp, f):
	for y in range(8):
		for x in range(8):
			xs = x*GRIDW+GRIDX - GRIDCELLSAMPLEW/2
			ys = y*GRIDH+GRIDY - GRIDCELLSAMPLEH/2
			gh = computeHist(bmp.get_portion((xs, ys), (GRIDCELLSAMPLEW, GRIDCELLSAMPLEH)))

			cellType = '~'
			for pfx in IMGDB.keys():
				sum = compHist(gh, IMGDB[pfx])
				f.write('gridPos=' + str(x) + ',' + str(y) + '   prefixCheck=' + pfx + '   sum=' + str(sum) + '\n')

def loadGridImgDB(grid, bmp):
	for y in range(8):
		for x in range(8):
			xs = x*GRIDW+GRIDX - GRIDCELLSAMPLEW/2
			ys = y*GRIDH+GRIDY - GRIDCELLSAMPLEH/2
			gh = computeHist(bmp.get_portion((xs, ys), (GRIDCELLSAMPLEW, GRIDCELLSAMPLEH)))

			cellType = '~'
			for pfx in IMGDB.keys():
				sum = compHist(gh, IMGDB[pfx])
				
				matchThresh = HISTMATCHTHRESH

				#print 'gridPos=' + str(x) + ',' + str(y) + '   prefixCheck=' + pfx + '   sum=' + str(sum)
				if sum <= matchThresh:
					cellType = pfx
					break 
			
			#print cellType.ljust(2),
	
			grid[x][y] = cellType

		#print

def grabGameScreen(useFake, saveGameScreen):
	if useFake == True:
		screen = openBMP('./gamescreen.png')
		bmp = screen.get_portion((XOFF, YOFFNOSCREEN), (W, H))
	else:
		bmp = bitmap.capture_screen(((XOFF, YOFF), (W, H)))

	if saveGameScreen == True:	
		bmp.save(os.getcwd() + '/gameboard.png')

	return bmp

def grabGridCellBMP(ifile, ofile, x, y):
	xstart = x*GRIDW
	ystart = y*GRIDH
	screen = openBMP(ifile)
	bmp = screen.get_portion((xstart, ystart), (GRIDW, GRIDH))
	bmp.save(ofile)

def grabScreenShotGridCellBMP(ssfile, ofile, x, y):
	xstart = XOFF + x*GRIDW
	ystart = YOFFNOSCREEN + y*GRIDH
	screen = openBMP(ssfile)
	bmp = screen.get_portion((xstart, ystart), (GRIDW, GRIDH))
	bmp.save(ofile)

def openBMP(bmpFile):
	return bitmap.Bitmap.open(bmpFile)

def gridToMouseCoord(((x1, y1), (x2, y2))):
    xs1 = XOFF + x1*GRIDW + GRIDX
    ys1 = YOFFNOSCREEN + y1*GRIDH + GRIDY
    xs2 = XOFF + x2*GRIDW + GRIDX
    ys2 = YOFFNOSCREEN + y2*GRIDH + GRIDY
    return ((xs1, ys1), (xs2, ys2))

def loadGrid(grid, bmp):
  loadGridImgDB(grid, bmp)

def inGrid(x, y):
  if x >= 0 and x <= 7 and y >=0 and y <= 7:
    return True
  return False

def compGrid3(grid, x1, y1, x2, y2, x3, y3):
	return compGrid3Pfx(grid, x1, y1, x2, y2, x3, y3)

def compGrid4(grid, x1, y1, x2, y2, x3, y3, x4, y4):
	return compGrid4Pfx(grid, x1, y1, x2, y2, x3, y3, x4, y4)

def compGrid5(grid, x1, y1, x2, y2, x3, y3, x4, y4, x5, y5):
	return compGrid5Pfx(grid, x1, y1, x2, y2, x3, y3, x4, y4, x5, y5)

def getPriority(s):
	priority = 0

	if len(s) > 1:
		if s[1] == 'm':
			priority += 5000
		elif s[1] == 's':
			priority += 50
		elif s[1] == 'f':
			priority += 25
		elif s[1] == 'c':
			priority += 10 
		elif s[1] == 'r':
			priority += 50
	
	return priority

def compGrid3Pfx(grid, x1, y1, x2, y2, x3, y3):
	match = False
	priority = THREEGEMMATCHPRI

	if inGrid(x1, y1) and inGrid(x2, y2) and inGrid(x3, y3):
		pfx1 = grid[x1][y1]
		pfx2 = grid[x2][y2]
		pfx3 = grid[x3][y3]

		if pfx1[0] == '~' or pfx2[0] == '~' or pfx3[0] == '~':
			return (0, False)

		match = pfx1[0] == pfx2[0] == pfx3[0]
		priority += getPriority(pfx1)
		priority += getPriority(pfx2)
		priority += getPriority(pfx3)

	return (priority, match)

def compGrid4Pfx(grid, x1, y1, x2, y2, x3, y3, x4, y4):
	match = False
	priority = FOURGEMMATCHPRI

	if inGrid(x1, y1) and inGrid(x2, y2) and inGrid(x3, y3) and inGrid(x4, y4):
		pfx1 = grid[x1][y1]
		pfx2 = grid[x2][y2]
		pfx3 = grid[x3][y3]
		pfx4 = grid[x4][y4]

		if pfx1[0] == '~' or pfx2[0] == '~' or pfx3[0] == '~' or pfx4[0] == '~':
			return (0, False)

		match = pfx1[0] == pfx2[0] == pfx3[0] == pfx4[0]
		priority += getPriority(pfx1)
		priority += getPriority(pfx2)
		priority += getPriority(pfx3)
		priority += getPriority(pfx4)
	
	return (priority, match)

def compGrid5Pfx(grid, x1, y1, x2, y2, x3, y3, x4, y4, x5, y5):
	match = False
	priority = FIVEGEMMATCHPRI

	if inGrid(x1, y1) and inGrid(x2, y2) and inGrid(x3, y3) and inGrid(x4, y4) and inGrid(x5, y5):
		pfx1 = grid[x1][y1]
		pfx2 = grid[x2][y2]
		pfx3 = grid[x3][y3]
		pfx4 = grid[x4][y4]
		pfx5 = grid[x5][y5]

		if pfx1[0] == '~' or pfx2[0] == '~' or pfx3[0] == '~' or pfx4[0] == '~' or pfx5[0] == '~':
			return (0, False)

		match = pfx1[0] == pfx2[0] == pfx3[0] == pfx4[0] == pfx5[0]
		priority += getPriority(pfx1)
		priority += getPriority(pfx2)
		priority += getPriority(pfx3)
		priority += getPriority(pfx4)
		priority += getPriority(pfx5)
		
	
	return (priority, match)

def compGridHyper(grid, x, y):
	match = False
	priority = 0

	if inGrid(x, y):
		if grid[x][y][0] == 'h':
			match = True
			priority = HYPERMATCHPRI
		
	return (priority, match)

def bestMoveHyper(grid, x, y):
	c1 = 'x'
	c2 = 'x'
	c3 = 'x'
	c4 = 'x'

	if inGrid(x, y-1):
		c1 = grid[x][y-1][0]
		if c1 == 'h':
			return ((x, y-1), (x, y), ((0, 0), (7, 7)))
	
	if inGrid(x+1, y):
		c2 = grid[x+1][y][0]
		if c2 == 'h':
			return ((x+1, y), (x, y), ((0, 0), (7, 7)))
	
	if inGrid(x, y+1):
		c3 = grid[x][y+1][0]
		if c3 == 'h':
			return ((x, y+1), (x, y), ((0, 0), (7, 7)))
	
	if inGrid(x-1, y):
		c4 = grid[x-1][y][0]
		if c4 == 'h':
			return ((x-1, y), (x, y), ((0, 0), (7, 7)))

	colCnt = [0, 0, 0, 0]

	for gy in range(8):		
		for gx in range(8):
			c = grid[gx][gy]
			if c[0] != '~':
				if c[0] == c1:
					colCnt[0] = colCnt[0] + 1
				elif c[0] == c2:
					colCnt[1] = colCnt[1] + 1
				elif c[0] == c3:
					colCnt[2] = colCnt[2] + 1
				elif c[0] == c4:
					colCnt[3] = colCnt[3] + 1

	if colCnt[0] > colCnt[1] and colCnt[0] > colCnt[2] and colCnt[0] > colCnt[3]: 
		return ((x, y-1), (x, y), ((0, 0), (7, 7)))
	
	if colCnt[1] > colCnt[0] and colCnt[1] > colCnt[2] and colCnt[1] > colCnt[3]: 
		return ((x+1, y), (x, y), ((0, 0), (7, 7)))
	
	if colCnt[2] > colCnt[0] and colCnt[2] > colCnt[1] and colCnt[2] > colCnt[3]: 
		return ((x, y+1), (x, y), ((0, 0), (7, 7)))
	
	if colCnt[3] > colCnt[0] and colCnt[3] > colCnt[1] and colCnt[3] > colCnt[2]: 
		return ((x-1, y), (x, y), ((0, 0), (7, 7)))
	
	return ((-1, -1), (-1, -1), ((-1, -1), (-1, -1)))

def findMoves(grid):
	moves = []
	for y in range(7, -1, -1):
		for x in range(0, 8):
			# Hypercube gem move
			(p, m) = compGridHyper(grid, x, y)
			if m:
				((x1, y1), (x2, y2), ((xb1, yb1), (xb2, yb2))) = bestMoveHyper(grid, x, y)
				if x1 != -1:
					moves.append((p, (x1, y1), (x2, y2), ((xb1, yb1), (xb2, yb2))))
			
			# V 5 Gem Left
			(p, m) = compGrid5(grid, x, y, x, y-1, x-1, y-2, x, y-3, x, y-4)
			if m:
				moves.append((p, (x-1, y-2), (x, y-2), ((x-1,y-4), (x, y))))
			
			# V 5 Gem Right
			(p, m) = compGrid5(grid, x, y, x, y-1, x+1, y-2, x, y-3, x, y-4)
			if m:
				moves.append((p, (x+1, y-2), (x, y-2), ((x,y-4), (x+1, y))))
			
			# L Right Top Top
			(p, m) = compGrid5(grid, x, y, x, y-1, x+1, y-2, x+2, y-2, x, y-3)
			if m:
				moves.append((p, (x, y-3), (x, y-2), ((x,y-3), (x+2, y))))
			
			# L Right Bottom Bottom
			(p, m) = compGrid5(grid, x, y, x+1, y-1, x+2, y-1, x, y-2, x, y-3)
			if m:
				moves.append((p, (x, y), (x, y-1), ((x,y-3), (x+2, y))))
			
			# L Right Left Top
			(p, m) = compGrid5(grid, x, y, x, y-1, x-1, y-2, x+1, y-2, x+2, y-2)
			if m:
				moves.append((p, (x-1, y-2), (x, y-2), ((x-1,y-2), (x+2, y))))
			
			# L Right Left Bottom
			(p, m) = compGrid5(grid, x, y, x+1, y-1, x+1, y-2, x+2, y, x+3, y)
			if m:
				moves.append((p, (x, y), (x+1, y), ((x,y-2), (x+3, y))))

			# L Left Top Top
			(p, m) = compGrid5(grid, x, y, x, y-1, x-1, y-2, x-2, y-2, x, y-3)
			if m:
				moves.append((p, (x, y-3), (x, y-2), ((x-2,y-3), (x, y))))
			
			# L Left Top Right
			(p, m) = compGrid5(grid, x, y, x+1, y, x+2, y+1, x+2, y+2, x+3, y)
			if m:
				moves.append((p, (x+3, y), (x+2, y), ((x,y), (x+3, y+2))))
			
			# L Left Bottom Bottom
			(p, m) = compGrid5(grid, x, y, x-1, y-1, x-2, y-1, x, y-2, x, y-3)
			if m:
				moves.append((p, (x, y), (x, y-1), ((x-2,y-3), (x, y))))
			
			# L Left Bottom Right
			(p, m) = compGrid5(grid, x, y, x+1, y, x+2, y-1, x+2, y-2, x+3, y)
			if m:
				moves.append((p, (x+3, y), (x+2, y), ((x,y-2), (x+3, y))))

			# V T Up
			(p, m) = compGrid5(grid, x, y, x-1, y-1, x+1, y-1, x, y-2, x, y-3)
			if m:
				moves.append((p, (x, y), (x, y-1), ((x-1,y-3), (x+1, y))))
			
			# V T Down
			(p, m) = compGrid5(grid, x, y, x, y-1, x-1, y-2, x+1, y-2, x, y-3)
			if m:
				moves.append((p, (x, y-1), (x, y-2), ((x-1,y-3), (x+1, y))))

			# V 4 Left Bottom
			(p, m) = compGrid4(grid, x, y, x-1, y-1, x, y-2, x, y-3)
			if m:
				moves.append((p, (x-1, y-1), (x, y-1), ((x-1,y-3), (x, y))))
			
			# V 4 Right Bottom
			(p, m) = compGrid4(grid, x, y, x+1, y-1, x, y-2, x, y-3)
			if m:
				moves.append((p, (x+1, y-1), (x, y-1), ((x,y-3), (x+1, y))))
			
			# V 4 Left Top
			(p, m) = compGrid4(grid, x, y, x, y-1, x-1, y-2, x, y-3)
			if m:
				moves.append((p, (x-1, y-2), (x, y-2), ((x-1,y-3), (x, y))))
			
			# V 4 Right Top
			(p, m) = compGrid4(grid, x, y, x, y-1, x+1, y-2, x, y-3)
			if m:
				moves.append((p, (x+1, y-2), (x, y-2), ((x,y-3), (x+1, y))))

			# V TopRight	
			(p, m) = compGrid3(grid, x, y, x, y-1, x+1, y-2)
			if m:
				moves.append((p, (x+1, y-2), (x, y-2), ((x,y-2), (x+1, y))))
			
			# V TopLeft
			(p, m) = compGrid3(grid, x, y, x, y-1, x-1, y-2)
			if m:
				moves.append((p, (x-1, y-2), (x, y-2), ((x-1, y-2), (x, y))))
		
			# V BottomRight	
			(p, m) = compGrid3(grid, x, y, x, y+1, x+1, y+2)
			if m:
				moves.append((p, (x+1, y+2), (x, y+2), ((x, y), (x+1, y+2))))
		
			# V BottomLeft	
			(p, m) = compGrid3(grid, x, y, x, y+1, x-1, y+2)
			if m:
				moves.append((p, (x-1, y+2), (x, y+2), ((x-1, y), (x, y+2))))
		
			# V TopSame	
			(p, m) = compGrid3(grid, x, y, x, y-1, x, y-3)
			if m:
				moves.append((p, (x, y-3), (x, y-2), ((x, y-3), (x, y))))
			
			# V BottomSame
			(p, m) = compGrid3(grid, x, y, x, y+1, x, y+3)
			if m:
				moves.append((p, (x, y+3), (x, y+2), ((x, y), (x, y+3))))
		
			# V MiddleRight	
			(p, m) = compGrid3(grid, x, y, x, y-2, x+1, y-1)
			if m:
				moves.append((p, (x+1, y-1), (x, y-1), ((x, y-2), (x+1, y))))
		
			# V MiddleLeft	
			(p, m) = compGrid3(grid, x, y, x, y-2, x-1, y-1)
			if m:
				moves.append((p, (x-1, y-1), (x, y-1), ((x-1, y-2), (x, y))))
			
			# H 5 Gem Left
			(p, m) = compGrid5(grid, x, y, x+1, y, x+2, y-1, x+3, y, x+4, y)
			if m:
				moves.append((p, (x+2, y-1), (x+2, y), ((x,y-1), (x+4, y))))
			
			# H 5 Gem Right
			(p, m) = compGrid5(grid, x, y, x+1, y, x+2, y+1, x+3, y, x+4, y)
			if m:
				moves.append((p, (x+2, y+1), (x+2, y), ((x,y), (x+4, y+1))))
			
			
			# H T Up
			(p, m) = compGrid5(grid, x, y, x+1, y-1, x+1, y+1, x+2, y, x+3, y)
			if m:
				moves.append((p, (x, y), (x+1, y), ((x,y-1), (x+3, y+1))))
			
			# H T Down
			(p, m) = compGrid5(grid, x, y, x+1, y, x+2, y-1, x+2, y+1, x+3, y)
			if m:
				moves.append((p, (x+3, y), (x+2, y), ((x,y-1), (x+3, y+1))))
			
			# H 4 Left Bottom
			(p, m) = compGrid4(grid, x, y, x+1, y-1, x+2, y, x+3, y)
			if m:
				moves.append((p, (x+1, y-1), (x+1, y), ((x,y-1), (x+3, y))))
			
			# H 4 Right Bottom
			(p, m) = compGrid4(grid, x, y, x+1, y+1, x+2, y, x+3, y)
			if m:
				moves.append((p, (x+1, y+1), (x+1, y), ((x,y), (x+3, y+1))))
			
			# H 4 Left Top
			(p, m) = compGrid4(grid, x, y, x+1, y, x+2, y-1, x+3, y)
			if m:
				moves.append((p, (x+2, y-1), (x+2, y), ((x,y-1), (x+3, y))))
			
			# H 4 Right Top
			(p, m) = compGrid4(grid, x, y, x+1, y, x+2, y+1, x+3, y)
			if m:
				moves.append((p, (x+2, y+1), (x+2, y), ((x,y), (x+3, y+1))))
			
			# H TopRight
			(p, m) = compGrid3(grid, x, y, x+1, y, x+2, y+1)
			if m:
				moves.append((p, (x+2, y+1),(x+2, y), ((x, y), (x+2, y+1))))
		
			# H TopLeft	
			(p, m) = compGrid3(grid, x, y, x+1, y, x+2, y-1)
			if m:
				moves.append((p, (x+2, y-1),(x+2, y), ((x, y-1), (x+2, y))))
		
			# H BottomRight	
			(p, m) = compGrid3(grid, x+1, y, x+2, y, x, y+1)
			if m:
				moves.append((p, (x, y+1),(x, y), ((x, y), (x+2, y+1))))
		
			# H BottomLeft	
			(p, m) = compGrid3(grid, x+1, y, x+2, y, x, y-1)
			if m:
				moves.append((p, (x, y-1),(x, y), ((x, y-1), (x+2, y))))
			
			# H TopSame	
			(p, m) = compGrid3(grid, x, y, x+1, y, x+3, y)
			if m:
				moves.append((p, (x+3, y),(x+2, y), ((x, y), (x+3, y))))
		
			# H BottomSame	
			(p, m) = compGrid3(grid, x-1, y, x+1, y, x+2, y)
			if m:
				moves.append((p, (x-1, y),(x, y), ((x-1, y), (x+2, y))))
		
			# H MiddleRight	
			(p, m) = compGrid3(grid, x, y, x+1, y+1, x+2, y)
			if m:
				moves.append((p, (x+1, y+1),(x+1, y), ((x,  y), (x+2, y+1))))
		
			# H MiddleLeft	
			(p, m) = compGrid3(grid, x, y, x+1, y-1, x+2, y)
			if m:
				moves.append((p, (x+1, y-1),(x+1, y), ((x, y-1), (x+2, y))))
	
	return moves

def randomizeMoves(moves):
	mlen = len(moves)
	for i in range(0, NUMRANDOMSWAPS):
		ridx1 = random.randint(0, mlen-1)
		ridx2 = random.randint(0, mlen-1)
		m = moves[ridx1]
		moves[ridx1] = moves[ridx2]
		moves[ridx2] = m

	return moves

def randomMove():
	basex = random.randint(1, 6)
	basey = random.randint(1, 6)

	swapDir = 1
	if random.randint(0, 100) > 50:
		swapDir = -1

	dx = 0
	dy = 0

	if random.randint(0, 100) > 50:
		dx += swapDir
	else:
		dy += swapDir
   
	return ((basex, basey), (basex+dx, basey+dy))

def sortPriority(mvs):
	n = len(mvs)
	swapped = True
	while swapped:
		swapped = False
		for i in range(1, len(mvs)):
			(p1, (x1, y1), (dx1, dy1), rect1) = mvs[i-1]
			(p2, (x2, y2), (dx2, dy2), rect2) = mvs[i]
			if (p2 > p1):
				tmp = mvs[i-1]
				mvs[i-1] = mvs[i]
				mvs[i] = tmp
				swapped = True

	return mvs


def pickMoves(panicMode, moves):
	rmoves = []
	
	if panicMode:
		for i in range(PANICMOVES):
			rmoves.append(randomMove())
		return rmoves

	return pickMovesBoundingRects(sortPriority(moves))

def pickMovesFirst(moves):
	rmoves = []	
	if len(moves) > 0:
		(p, (x1, y1), (x2, y2), rect) = moves[0]
		rmoves.append(((x1, y1), (x2, y2)))

	return rmoves

def pickMovesHalves(moves):
	rmoves = []

	# Note that even though this checks a move against
  # itself, it doesn't matter because a move checked
	# against itself can never satisfy the criteria and
	# the checks are not expensive	
	for (p, (ox1, oy1), (ox2, oy2), rect) in moves:
		for (p, (dx1, dy1), (dx2, dy2), rect) in moves:
			if ox1 > 3 and ox2 > 3 and dx1 < 4 and dx1 < 4:
				rmoves.append(((ox1, oy1), (ox2, oy2)))	
				rmoves.append(((dx1, dy1), (dx2, dy2)))
				return rmoves
			
			if ox1 < 4 and ox2 < 4 and dx1 > 3 and dx1 > 3:
				rmoves.append(((ox1, oy1), (ox2, oy2)))	
				rmoves.append(((dx1, dy1), (dx2, dy2)))
				return rmoves
			
			if oy1 > 3 and oy2 > 3 and dy1 < 4 and dy1 < 4:
				rmoves.append(((dx1, dy1), (dx2, dy2)))
				rmoves.append(((ox1, oy1), (ox2, oy2)))	
				return rmoves
			
			if oy1 < 4 and oy2 < 4 and dy1 > 3 and dy1 > 3:
				rmoves.append(((ox1, oy1), (ox2, oy2)))	
				rmoves.append(((dx1, dy1), (dx2, dy2)))
				return rmoves
			
	if len(moves) > 0:
		(p, (x1, y1), (x2, y2), rect) = moves[0]
		rmoves.append(((x1, y1), (x2, y2)))
	
	return rmoves

def ptInRect(r, p):
	((x, y), (dx, dy)) = r
	(px, py) = p
	return px >= x and px <= dx and py >= y and py <= dy

def rectInRect(r1, r2):
	((x, y), (dx, dy)) = r2
	return ptInRect(r1, (x, y)) or ptInRect(r1, (dx, y)) or ptInRect(r1, (dx, dy)) or ptInRect(r1, (x, dy))

def sorty(mvs):
	n = len(mvs)
	swapped = True
	while swapped:
		swapped = False
		for i in range(1, len(mvs)):
			((x1, y1), (dx1, dy1)) = mvs[i-1]
			((x2, y2), (dx2, dy2)) = mvs[i]
			if (y2 < y1):
				tmp = mvs[i-1]
				mvs[i-1] = mvs[i]
				mvs[i] = tmp
				swapped = True

	return mvs

def pickMovesBoundingRects(moves):
	llen = len(moves)

	if llen == 0:
		return moves 

	endLoop = False
	currList = moves
	keepList = [] 
	while not endLoop:
		(dum, (x1, y1), (dx1, dy1), r1) = currList[0]	
		keepList.append((dum, (x1, y1), (dx1, dy1), r1))
		newList = []	
		llen = len(currList)
		for i in range(1, llen):
			(dum, (x2, y2), (dx2, dy2), r2) = currList[i]	
			if not rectInRect(r1, r2):
				newList.append((dum, (x2, y2), (dx2, dy2), r2))
	
		if len(newList) == 0:
			endLoop = True
		else:		
			currList = newList
			
	moveList = []
	for (priority, (x1, y1), (x2, y2), rect) in keepList:
		moveList.append(((x1, y1), (x2, y2)))	
	
	return sorty(moveList)

def panicBail(grid, bmp):
	print "PANICKED!"
	f = open('./panic.log', 'w')
	f.write('In panic mode. Here\'s the grid:\n')
	dumpGridImgDBToFile(grid, f)
	dumpGridHistCompareImgDBToFile(grid, bmp, f)
	f.close()	
	bmp.save("./panicboard.png")
	screen = bitmap.capture_screen()
	screen.save("./panicscreen.png")
	sys.exit(0)

def main():
	# Seed the random number generator
	random.seed()

	# Build our image database
	loadImgDB(IMGDBPATH)

	# This guarantees a timely first move	
	loopStart = datetime.datetime.now()
	
  # Click in the middle of the "Play" button on the game
	mouse.smooth_move(PLAYX, PLAYY)
	mouse.click()
	time.sleep(1)	

	startTime = time.time();
	endLoop = False
	grid = [['~' for x in range(8)] for x in range(8)] 
	loopElapsed = datetime.datetime.now() - loopStart
	timeBetweenMoves = TIMEBETWEENMOVES
	noMovesCnt = 0	
	panicMode = False

	while endLoop == False:
		# Only make a move if enough time has elapsed	
		if loopElapsed.total_seconds() >= timeBetweenMoves:
			bmp = grabGameScreen(False, False);
	
			loadGrid(grid, bmp)
		
			pickedMoves = pickMoves(panicMode, findMoves(grid))

			if DEBUG:
				print str(pickedMoves)
				panicBail(grid, bmp)

			numMovesAttempted = len(pickedMoves)

			for move in pickedMoves:
				((x1, y1),(x2, y2)) = gridToMouseCoord(move)
					
				mouse.move(x1, y1)
				time.sleep(0.05)
				mouse.click()
				
				mouse.move(x2, y2)
				time.sleep(0.05)
				mouse.click()
				
			mouse.move(210, 500)

			if numMovesAttempted > NUMMOVESLONGWAIT and not panicMode:
				timeBetweenMoves = TIMEBETWEENMOVESMAX
				if time.time() - startTime > SECSTODECREASEMOVETIME:
					timeBetweenMoves = TIMEBETWEENMOVESMIN
			else:
				timeBetweenMoves = TIMEBETWEENMOVES

			if numMovesAttempted == 0:
				noMovesCnt += 1

			if noMovesCnt > CYCLESBEFOREPANIC:
				panicMode = True
				noMovesCnt = 0
				panicBail(grid, bmp)
			else:
				panicMode = False

			loopStart = datetime.datetime.now()

		if time.time() - startTime > GAME_TIME:
			endLoop = True

		loopElapsed = datetime.datetime.now() - loopStart
	
if __name__ == '__main__':
  main()  

