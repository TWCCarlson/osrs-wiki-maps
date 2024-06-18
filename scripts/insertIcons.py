import time
import json
import os
from dataclasses import dataclass, field
from collections import defaultdict
from math import floor, ceil
import glob
import pprint
import math
import logging

# Pyvips on windows is finnicky
# Windows binaries are required: https://pypi.org/project/pyvips/, https://www.libvips.org/install.html
LIBVIPS_VERSION = "8.15"
vipsbin = os.path.join(os.getcwd(), f"vipsbin/vips-dev-{LIBVIPS_VERSION}/bin")
os.environ['PATH'] = os.pathsep.join((vipsbin, os.environ['PATH']))
# os.environ['VIPS_CONCURRENCY'] = "2"
import pyvips as pv
# logging.basicConfig(level = logging.DEBUG)

# Pre-process the list
# Bucket icons into categories:
# - Belongs to tile
# - - Drawn no matter what
# - Overflows into tile
# - - Drawn if the owner tile is in the directory
# - - This avoids the case where an overflowing icon is from a tile that isn't in the mapID

# Icons should be drawn into overlays which are then masked overtop the respective tiles
# If the target tile isn't in the directory then the overlay can just be saved



# To draw the tiles we want to traverse the directory with files in it
# This means there may be missing tiles in the mapID directories that need to be created where icons have overflowed

# For each mapID
# Load the mapID definition
# Read in the source tiles from the definition
	# For each zoom
		# For each plane
			# For each source square (mapSquareOfZones should handle this)
				# Access the pre-processed list to find all icons in that source square
				# Collect a list of any that would spill over
				# Access the pre-processed list to find any icons spilling into this square
				# Calculate the output tile file name using the zoomlevel/plane/display square
			





@dataclass(order=True)
class IconDefinition:
	orderIndex: int
	tileX: int = field(compare=False)
	tileY: int = field(compare=False)
	plane: int = field(compare=False)
	spriteID: int = field(compare=False)
	coordData: int = field(compare=False)
	zoomLevelHasIcon: int = field(compare=False)
	baselineZoomLevel: int = field(compare=False)
	tilePosition: dict = field(init=False, compare=False)
	positionInTile: dict = field(init=False, compare=False)
	overflowsInto: dict = field(init=False, compare=False)

	def __post_init__(self):
		# Alter the dict keys to become ints, simplying later referencing
		self.zoomLevelHasIcon = {int(k):v for k,v in self.zoomLevelHasIcon.items() if v}

		# We want to store the icon's owner tile and position in the tile at each zoom level
		self.tilePosition = dict()
		self.positionInTile = dict()
		self.overflowsInto = dict()

		# The game tile position is provided, but other coordinates need calculating
		# The owner square is calculable by integer division of tiles per ssquare
		squareX = self.tileX // self.coordData["squareTileLength"]
		squareY = self.tileY // self.coordData["squareTileLength"]

		for zoomLevel in self.zoomLevelHasIcon:
			# Calculate the leaflet tile coordinates using the zoom level to scale the division
			scaleFactor = 2.0**zoomLevel / 2.0**self.baselineZoomLevel
			scaleTileX = int(floor(squareX * scaleFactor))
			scaleTileY = int(floor(squareY * scaleFactor))

			# Save the icon square in a way that is indexable using zoom level
			self.tilePosition[zoomLevel] = (scaleTileX, scaleTileY)

			# Calculate the relative position, in px, of the icon within the tile
			# Scale the pixel dimensions and find the remainder on a grid of 256x256
			x_px = self.tileX * self.coordData["tilePixelLength"]
			y_px = self.tileY * self.coordData["tilePixelLength"]

			# The relative position within a tile needs to be calculated from the top left
			relX_px = (x_px * scaleFactor) % self.coordData["squarePixelLength"]
			relY_px = (y_px * scaleFactor) % self.coordData["squarePixelLength"]
			relY_px = self.coordData["squarePixelLength"] - relY_px - 1

			# Save the icon in-tile positions in a way that is indexable using zoom level
			self.positionInTile[zoomLevel] = (relX_px, relY_px)

			# Also store any neighbor tiles that this icon spills into
			overflowsInto = list()
			leftOverflow = relX_px - (15//2) < 0
			topOverflow = relY_px - (15//2) < 0
			rightOverflow = relX_px + (15//2) > self.coordData["squarePixelLength"]
			bottomOverflow = relY_px + (15//2) > self.coordData["squarePixelLength"]
			# recall that the relative y-values are top left origin (-ve means the tile above)
			if leftOverflow: overflowsInto.append((-1, 0))
			if rightOverflow: overflowsInto.append((1, 0))
			if topOverflow: overflowsInto.append((0, 1))
			if bottomOverflow: overflowsInto.append((0, -1)) 
			if leftOverflow and topOverflow: overflowsInto.append((-1, 1))
			if leftOverflow and bottomOverflow: overflowsInto.append((-1, -1))
			if rightOverflow and topOverflow: overflowsInto.append((1, 1))
			if rightOverflow and bottomOverflow: overflowsInto.append((1, -1))
			self.overflowsInto[zoomLevel] = overflowsInto

	def __repr__(self):
		return f"Icon '{self.orderIndex}':[{self.tileX, self.tileY}]@zoom2"


class IconManager:
	# Stores an square-coordinate indexable dict with a list of all the icons in the square
	def __init__(self, zoomLevelHasIcons, ) -> None:
		self.tileOwnsIconList = dict()
		self.tileOverflowIconList = dict()
		self.iconSpriteList = list()
		self.zoomLevelsWithIcons = {int(k):v for k,v in zoomLevelHasIcons.items() if v}
		for zoomLevel in self.zoomLevelsWithIcons:
			self.tileOwnsIconList[zoomLevel] = dict()
			self.tileOverflowIconList[zoomLevel] = dict()
			for planeID in range(0, 3+1):
				self.tileOwnsIconList[zoomLevel][planeID] = defaultdict(list)
				self.tileOverflowIconList[zoomLevel][planeID] = defaultdict(list)

	def addIcon(self, iconObj: IconDefinition):
		# Ingest the new icon
		for zoomLevel in self.zoomLevelsWithIcons:
			### Record which tiles the icon should be drawn on

			# Icons are always drawn on the leaflet tile their game tile is in
			tilePosX, tilePosY = iconObj.tilePosition[zoomLevel]
			plane = iconObj.plane
			self.tileOwnsIconList[zoomLevel][plane][(tilePosX, tilePosY)].append(iconObj)

			# Icons also need to be drawn on the tiles they spill into
			overflowList = iconObj.overflowsInto[zoomLevel]
			for overflowDirection in overflowList:
				# Calculate the destination tile
				xShift, yShift = overflowDirection
				overflowX = tilePosX + xShift
				overflowY = tilePosY + yShift
				# Save it
				self.tileOverflowIconList[zoomLevel][plane][(overflowX, overflowY)].append(iconObj)
		
def processIconlist(iconDefsPath, coordData, zoomLevelHasIcons, baselineZoomLevel):
	with open(iconDefsPath) as iconDefsFile:
		iconDefs = json.load(iconDefsFile)

	# Instantiate the icon manager
	iconManager = IconManager(zoomLevelHasIcons)

	# We would like the icons to be sortable, so we supply an index value based on the .json order
	iconOrderIndex = 0
	for iconDef in iconDefs:
		# Create the icon dataclass representing this icon
		tileX = iconDef["position"]["x"]
		tileY = iconDef["position"]["y"]
		plane = iconDef["position"]["z"]
		spriteID = iconDef["spriteId"]
		newIcon = IconDefinition(iconOrderIndex, tileX, tileY, plane, spriteID,
						   		coordData, zoomLevelHasIcons, baselineZoomLevel)

		# Add it to the icon manager
		iconManager.addIcon(newIcon)
		iconOrderIndex += 1
	return iconManager


def loadIcons(spritesPath):
	iconPaths = glob.glob(os.path.join(spritesPath, "*.png"))
	iconDict = dict()
	for iconPath in iconPaths:
		iconID = os.path.basename(iconPath).split(".")[0]
		iconDict[int(iconID)] = iconPath
	return iconDict


def insertIcons(directory, iconManager: IconManager, iconSprites, zoomLevel):
	# Find the images to draw onto
	tileImagePaths = glob.iglob(os.path.join(directory, "*.png"))
	iconCount = 0
	for tileImagePath in tileImagePaths:
		plane, squareX, squareY = map(int, os.path.basename(tileImagePath).split(".png")[0].split("_"))

		# Find all icons to draw on the tile
		iconDefs = list()
		if plane == 0:
			for z in range(0, 3+1):
				# Find icons which are located in the tile
				iconDefs.extend(iconManager.tileOwnsIconList[zoomLevel][z][(squareX, squareY)])
				# Find icons which overflow into the tile
				iconDefs.extend(iconManager.tileOverflowIconList[zoomLevel][z][(squareX, squareY)])
		else:
			iconDefs.extend(iconManager.tileOwnsIconList[zoomLevel][plane][(squareX, squareY)])
			iconDefs.extend(iconManager.tileOverflowIconList[zoomLevel][plane][(squareX, squareY)])

		# If there are no icons, skip the tile
		if not iconDefs:
			continue
		
		# If there are icons, create a blank tile to hold them
		iconLayer = pv.Image.black(256, 256, bands=4).copy(interpretation="srgb")

		# Draw every defined icon onto the new image
		for iconDef in iconDefs:
			# Load the icon image
			tileX, tileY = iconDef.tilePosition[zoomLevel]
			x, y = iconDef.positionInTile[zoomLevel]
			iconImage = pv.Image.new_from_file(iconSprites[iconDef.spriteID])

			# Create a temporary layer for just this icon
			temp = pv.Image.black(256, 256, bands=4).copy(interpretation="srgb")

			# Calculate the icon position
			# If the icon is drawn in the tile
			if tileX==squareX and tileY==squareY:
				iconX = x - math.ceil(iconImage.width/2)
				iconY = y - math.ceil(iconImage.height/2)
				temp = temp.insert(iconImage, iconX, iconY, expand=False)
			else:
				# Otherwise the icon is spilling into this tile
				# Calculate current tile's relation to icon's tile
				offsetX = squareX - tileX
				offsetY = squareY - tileY
				# Use the relation to calculate the icon's position in the current tile
				iconX = x - (offsetX * 256) - math.ceil(iconImage.width/2)
				iconY = y + (offsetY * 256) - math.ceil(iconImage.height/2) # top left vs bottom left origin
				temp = temp.insert(iconImage, iconX, iconY, expand=False)

			iconCount += 1

			# Create a mask and insert to the iconlayer
			mask = (temp[3] == 255)
			iconLayer = mask.ifthenelse(temp, iconLayer)
		# iconLayer.write_to_file(outPath)

		# Merge the layers using a mask
		layerMask = (iconLayer[3] == 255)
		tileImage = pv.Image.new_from_file(tileImagePath)
		outImage = layerMask.ifthenelse(iconLayer[0:3], tileImage)

		# The image needs to be saved to a temporary file, vips reads from the original while writing
		outPath = os.path.join(os.path.dirname(tileImagePath), f"{plane}_{squareX}_{squareY}-icon.png")
		outImage.write_to_file(outPath)
		# The original image can then be removed
		os.remove(tileImagePath)
		# And the new one renamed
		os.rename(outPath, tileImagePath)


def actionRoutine(basePath):
	"""
		Draws icons onto existing tiles
		Checks for icons which escape the bounds of a tile, drawing them elsewhere
	"""
	coordFilePath = os.path.join(basePath, "coordinateData.json")
	with open(coordFilePath) as coordDataFile:
		coordData = json.load(coordDataFile)
	with open("./scripts/mapBuilderConfig.json") as configFile:
		configData = json.load(configFile)

	defsPath = configData["ICON_OPTS"]["iconDefs"]
	spritesPath = configData["ICON_OPTS"]["iconPath"]
	mapIDPath = configData["ICON_OPTS"]["mapIDDirectory"]
	squareDefsPath = configData["MAPID_OPTS"]["squareDefsPath"]
	zoneDefsPath = configData["MAPID_OPTS"]["zoneDefsPath"]
	zoomLevelHasIcons = configData["ICON_OPTS"]["zoomLevelHasIcons"]
	baselineZoomLevel = configData["ZOOM_OPTS"]["baselineZoomLevel"]

	defsPath = os.path.join(basePath, defsPath)
	spritesPath = os.path.join(basePath, spritesPath)
	mapIDPath = os.path.join(basePath, mapIDPath)
	squareDefsPath = os.path.join(basePath, squareDefsPath)
	zoneDefsPath = os.path.join(basePath, zoneDefsPath)
	
	iconManager = processIconlist(defsPath, coordData, zoomLevelHasIcons, baselineZoomLevel)
	iconSprites = loadIcons(spritesPath)

	# MapID directories will need to use their definitions to make sure icons are properly located
	# mapID_dirs = glob.iglob(os.path.join(mapIDPath, "**/"))
	# for mapID in mapID_dirs:
	# 	for zoomLevel in (int(zl) for zl in zoomLevelHasIcons if zoomLevelHasIcons[zl]):
	# 		operationDir = os.path.join(mapID, zoomLevel)
	# 		print(operationDir)
			# Load definitions files
			# Need the source/display squares from zones and squares to 
			# with open(os.path.join(squareDefsPath, f"mapSquareDefinitions_{mapID}")) as squareDefsFile:
			# 	squareDefs = json.load(squareDefsFile)
			# with open(os.path.join(zoneDefsPath, f"zoneDefinitions_{mapID}")) as zoneDefsFile:
			# 	zoneDefs = json.load(zoneDefsFile)
			# insertIcons(operationDir, squareDefs, zoneDefs)
	# 		break
	# 	break

	# For mapID -1 there is no definition to manage
	for zoomLevel in (int(zl) for zl in zoomLevelHasIcons if zoomLevelHasIcons[zl]):
		basePlaneDir = os.path.join(mapIDPath, "-1", f"{zoomLevel}")
		insertIcons(basePlaneDir, iconManager, iconSprites, zoomLevel)
			
	# print(mapID_dirs)

if __name__ == "__main__":
	startTime = time.time()
	actionRoutine("./osrs-wiki-maps/out/mapgen/versions/2024-05-29_a")
	print(f"Took {time.time() - startTime}")