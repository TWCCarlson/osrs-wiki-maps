import glob
import os.path
import json
import time
import heapq
from collections import defaultdict
from _collections_abc import MutableMapping
from dataclasses import dataclass, field
from memory_profiler import memory_usage
import pprint
import math
from math import floor
from copy import deepcopy

# Pyvips on windows is finnicky
# Windows binaries are required: https://pypi.org/project/pyvips/, https://www.libvips.org/install.html
LIBVIPS_VERSION = "8.15"
vipsbin = os.path.join(os.getcwd(), f"vipsbin/vips-dev-{LIBVIPS_VERSION}/bin")
os.environ['PATH'] = os.pathsep.join((vipsbin, os.environ['PATH']))
# os.environ['VIPS_PROFILE'] = "1"
import pyvips as pv
# logging.basicConfig(level = logging.DEBUG)


def createIconManager(basePath):
	"""
		Returns an icon manager loaded with a pre-processed list of icons
	"""
	coordFilePath = os.path.join(basePath, "coordinateData.json")
	with open(coordFilePath) as coordDataFile:
		coordData = json.load(coordDataFile)
	with open("./scripts/mapBuilderConfig.json") as configFile:
		configData = json.load(configFile)

	zoomLevelHasIcons = configData["ICON_OPTS"]["zoomLevelHasIcons"]
	baselineZoomLevel = configData["ZOOM_OPTS"]["baselineZoomLevel"]
	defsPath = configData["ICON_OPTS"]["iconDefs"]
	defsPath = os.path.join(basePath, defsPath)

	return processIconlist(defsPath, coordData, zoomLevelHasIcons, baselineZoomLevel)


def processIconlist(iconDefsPath, coordData, zoomLevelHasIcons, baselineZoomLevel):
	with open(iconDefsPath) as iconDefsFile:
		iconDefs = json.load(iconDefsFile)

	# Instantiate the icon manager
	iconManager = IconManager(zoomLevelHasIcons, baselineZoomLevel, coordData)

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
		iconManager.addIconSource(newIcon)
		iconOrderIndex += 1
	return iconManager


@dataclass(order=True)
class mapSquare():
	sort_index: tuple = field(init=False, repr=False)
	displaySquareY: int
	displaySquareX: int
	sourceSquareY: int = field(compare=False)
	sourceSquareX: int = field(compare=False)
	level: int = field(compare=False)
	tilePath: int = field(compare=False)
	coordData: dict = field(compare=False)
	ownedIcons: list = field(init=False, compare=False)

	def __post_init__(self):
		# Sort with descending y
		self.sort_index = (-self.displaySquareY, self.displaySquareX)

	def fetchSquare(self):
		# Fetch the mapSquare image if it exists
		sourcePath = os.path.join(self.tilePath, f"{self.level}_{self.sourceSquareX}_{self.sourceSquareY}.png")
		
		if os.path.exists(sourcePath):
			return pv.Image.new_from_file(sourcePath)
		else:
			# If it doesn't exist, return a blank image
			return pv.Image.black(self.coordData["squarePixelLength"], self.coordData["squarePixelLength"], bands=3).copy(interpretation="srgb")
		
	def findIcons(self, iconStore):	
		# Collect all the icons which are located in this square
		iconList = getFlattenedDict(iconStore.sourceTileOwnsIconList[2][self.level][(self.sourceSquareX, self.sourceSquareY)])
		self.ownedIcons = self.filterIconList(iconList, 2)
		self.loadIconDisplayData(iconStore)
		return iconStore
	
	def loadIconDisplayData(self, iconStore):
		# Tell the icon manager where icons should be displayed
		for icon in self.ownedIcons:
			iconStore.addIconDisplay(icon, self)
		return iconStore

	def filterIconList(self, iconList, zoomLevel):
		def filterFunc(icon: IconDefinition):
			if icon.tilePosition[zoomLevel] == (self.sourceSquareX, self.sourceSquareY):
				return True
			return False
		
		return list(filter(filterFunc, iconList))
	
	def getDisplayData(self):
		return (self.displaySquareX, self.displaySquareY)

	def __eq__(self, other):
		if isinstance(other, mapSquare):
			return (self.displaySquareY, self.displaySquareX) == (other.displaySquareY, self.displaySquareX)
		elif isinstance(other, tuple):
			return (self.displaySquareY, self.displaySquareX) == other
		return False

	def __hash__(self):
		# Only hash with the display squares for `in` checks
		return hash((self.displaySquareY, self.displaySquareX))
	
	def __repr__(self):
		return f"mapSquare:({self.sourceSquareX},{self.sourceSquareY})->({self.displaySquareX},{self.displaySquareY})"

@dataclass(order=True)
class mapZone():
	sort_index: int = field(init=False, repr=False)
	displaySquareY: int
	displaySquareX: int
	displayZoneY: int
	displayZoneX: int
	sourceSquareY: int = field(compare=False)
	sourceSquareX: int = field(compare=False)
	sourceZoneY: int = field(compare=False)
	sourceZoneX: int = field(compare=False)
	level: int = field(compare=False)
	tilePath: int = field(compare=False)
	coordData: dict = field(compare=False)
	ownedIcons: list = field(init=False, compare=False)

	def __post_init__(self):
		# Sort with descending y
		self.sort_index = (-self.displaySquareY, self.displaySquareX, -self.displayZoneY, self.displayZoneX)

	def fetchZone(self):
		# Load the zone image if it exists
		sourcePath = os.path.join(self.tilePath, f"{self.level}_{self.sourceSquareX}_{self.sourceSquareY}.png")
		if os.path.exists(sourcePath):
			sourceSquare = pv.Image.new_from_file(sourcePath)
			# Crop out the zone
			zoneSideLength = self.coordData["zonePixelLength"]
			sourceZoneX_px = self.sourceZoneX * zoneSideLength
			sourceZoneY_px = (self.coordData["squareZoneLength"] - self.sourceZoneY - 1) * zoneSideLength
			return sourceSquare.crop(sourceZoneX_px, sourceZoneY_px, zoneSideLength, zoneSideLength)
		else:
			# Return a blank image
			return pv.Image.black(self.coordData["zonePixelLength"], self.coordData["zonePixelLength"], bands=3).copy(interpretation="srgb")

	def addIcons(self, iconList):
		# Stores a reference to the icon objects belonging to this zone
		self.ownedIcons = iconList

	def getDisplayData(self):
		return (self.displaySquareX, self.displaySquareY, self.displayZoneX, self.displayZoneY)

	def __eq__(self, other):
		if isinstance(other, mapSquare):
			selfData = (self.displaySquareY, self.displaySquareX, self.displayZoneY, self.displayZoneX)
			otherData = (other.displaySquareY, self.displaySquareX, self.displayZoneY, self.displayZoneX)
			return selfData == otherData
		elif isinstance(other, tuple):
			selfData = (self.displaySquareY, self.displaySquareX, self.displayZoneY, self.displayZoneX)
			return selfData == other
		return False

	def __hash__(self):
		# Only hash with the display squares for `in` checks
		return hash((self.displaySquareY, self.displaySquareX, self.displayZoneY, self.displayZoneX))

	def __repr__(self):
		return f"mapZone({self.sourceSquareX},{self.sourceSquareY}):[{self.sourceZoneX},{self.sourceZoneY}] -> ({self.displaySquareX},{self.displaySquareY}):[{self.displayZoneX},{self.displayZoneY}]"

@dataclass(order=True)
class mapSquareOfZones(mapSquare):
	"""
		Subclasses mapSquare
		Extended to contain a set of mapZones which fill in the square
	"""
	# displayZoneY: int
	# displayZoneX: int
	# sourceZoneY: int = field(compare=False)
	# sourceZoneX: int = field(compare=False)
	zoneCount: int = field(init=False, compare=False)
	zoneSidelength: int = field(init=False, compare=False)
	sidelength: int = field(init=False, compare=False)
	zoneList: list = field(init=False, compare=False)
	zoneImages: list = field(init=False, compare=False)

	def __init__(self, displaySquareY, displaySquareX, displayZoneY, displayZoneX,
			  	sourceSquareY, sourceSquareX, sourceZoneY, sourceZoneX,
				level, tilePath, coordData):
		# Split the init args to use base class mapSquare
		super().__init__(displaySquareX, displaySquareY, sourceSquareY, sourceSquareX, 
				   		level, tilePath, coordData)
		# Add the zone fields
		# Zone arguments are discarded for now
		# self.sourceZoneX = sourceZoneX
		# self.sourceZoneY = sourceZoneY
		# self.displayZoneX = displayZoneX
		# self.displayZoneY = displayZoneY

	def __post_init__(self):
		# Initialize like a mapSquare
		super().__post_init__()

		# But also establish the necessary items for storing zones
		self.zoneCount = 0
		self.zoneSidelength = self.coordData["zonePixelLength"]
		self.sideLength = self.coordData["squareZoneLength"]
		mat = list()
		for n in range(self.sideLength):
			row = list()
			for m in range(self.sideLength):
				row.append(None)
			mat.append(row)
		self.zoneList = deepcopy(mat)
		self.zoneImages = deepcopy(mat)

	def addZoneToSquare(self, mapZone: mapZone):
		# Place the mapZone within the square
		displayZoneY = mapZone.displayZoneY
		displayZoneX = mapZone.displayZoneX
		self.zoneList[displayZoneY][displayZoneX] = mapZone
		self.zoneCount += 1

	def fetchSquare(self):
		# Create the stitched image of the square from the array of zones
		for row in range(len(self.zoneList)):
			for col in range(len(self.zoneList[0])):
				# Convert to top left coordinates for rendering
				renderRow = self.sideLength - row - 1
				cell = self.zoneList[row][col]
				if isinstance(cell, mapZone):
					# Replace the cell data with the image
					self.zoneImages[renderRow][col] = self.zoneList[row][col].fetchZone()
				else:
					self.zoneImages[renderRow][col] = pv.Image.black(self.zoneSidelength, self.zoneSidelength, bands=3).copy(interpretation="srgb")
		
		# Flatten the list for joining
		squareList = [cell for row in self.zoneImages for cell in row]
		return pv.Image.arrayjoin(squareList, across=self.sideLength)
	
	def findIcons(self, iconStore):
		# Collect all the icons which are lcoated in this square
		iconList = list()
		# Check each zone definition
		for i in range(len(self.zoneList)):
			for j in range(len(self.zoneList[i])):
				targetZone = self.zoneList[i][j]
				zoneIcons = iconStore.sourceTileOwnsIconList[2][self.level][(self.sourceSquareX, self.sourceSquareY)][(j, i)]
				targetZone.addIcons(zoneIcons)
				iconList.extend(zoneIcons)
		self.ownedIcons = iconList
		self.loadIconDisplayData(iconStore)
		return iconStore

	def loadIconDisplayData(self, iconStore):
		# Iterate over all zones, loading their icons in
		for i in range(len(self.zoneList)):
			for j in range(len(self.zoneList[i])):
				targetZone = self.zoneList[i][j]
				iconList = targetZone.ownedIcons
				for icon in iconList:
					iconStore.addIconDisplay(icon, targetZone)
		return iconStore

	def checkIfZoneEmpty(self, x, y):
		# Checks whether the zone cell is empty (==None)
		targetX = x
		targetY = y
		return bool(not self.zoneList[targetY][targetX])

	def __repr__(self) -> str:
		return f"mapSquareOfZones(len:{self.zoneCount})"
	
	def __reprdebug__(self) -> str:
		return pprint.pprint(self.zoneList)

@dataclass(order=True)
class squareDefinition:
	groupId: int
	sourceSquareX: int = field(compare=False)
	sourceSquareZ: int = field(compare=False)
	displaySquareX: int = field(compare=False)
	displaySquareZ: int = field(compare=False)
	minLevel: int = field(compare=False)
	levels: int = field(compare=False)
	fileId: int = field(compare=False)
	# Post init vals
	sourceSquareY: int = field(init=False, compare=False)
	displaySquareY: int = field(init=False, compare=False)
	lowerPlane: int = field(init=False, compare=False)
	upperPlane: int = field(init=False, compare=False)

	def __post_init__(self):
		# Convert from Z to Y
		self.sourceSquareY = self.sourceSquareZ
		self.displaySquareY = self.displaySquareZ
		# Calculate lower and upper planes for ease of reference
		self.lowerPlane = self.minLevel
		self.upperPlane = self.minLevel+self.levels-1

	def getSquareData(self):
		sourceData = (self.sourceSquareY, self.sourceSquareX)
		displayData = (self.displaySquareY, self.displaySquareX)
		levelData = (self.lowerPlane, self.upperPlane)
		return (sourceData, displayData, levelData)

	def __repr__(self) -> str:
		return f"squareDef({self.sourceSquareX, self.sourceSquareY})->({self.displaySquareX, self.displaySquareY})"

@dataclass(order=True)
class zoneDefinition:
	groupId: int
	sourceSquareX: int = field(compare=False)
	sourceSquareZ: int = field(compare=False)
	sourceZoneX: int = field(compare=False)
	sourceZoneZ: int = field(compare=False)
	displaySquareX: int = field(compare=False)
	displaySquareZ: int = field(compare=False)
	displayZoneX: int = field(compare=False)
	displayZoneZ: int = field(compare=False)
	minLevel: int = field(compare=False)
	levels: int = field(compare=False)
	fileId: int = field(compare=False)
	# Post init vals
	sourceSquareY: int = field(init=False, compare=False)
	sourceZoneY: int = field(init=False, compare=False)
	displaySquareY: int = field(init=False, compare=False)
	displayZoneY: int = field(init=False, compare=False)
	lowerPlane: int = field(init=False, compare=False)
	upperPlane: int = field(init=False, compare=False)

	def __post_init__(self):
		# Convert from Z to Y
		self.sourceSquareY = self.sourceSquareZ
		self.sourceZoneY = self.sourceZoneZ
		self.displaySquareY = self.displaySquareZ
		self.displayZoneY = self.displayZoneZ
		# Calculate lower and upper planes for ease of reference
		self.lowerPlane = self.minLevel
		self.upperPlane = self.minLevel+self.levels-1

	def getZoneData(self):
		sourceData = (self.sourceSquareY, self.sourceSquareX, self.sourceZoneY, self.sourceZoneX)
		displayData = (self.displaySquareY, self.displaySquareX, self.displayZoneY, self.displayZoneX)
		levelData = (self.lowerPlane, self.upperPlane)
		return (sourceData, displayData, levelData)

	def __repr__(self) -> str:
		return f"squareDef({self.sourceSquareX, self.sourceSquareY})[{self.sourceZoneX,self.sourceZoneY}]->({self.displaySquareX, self.displaySquareY})[{self.displayZoneX,self.displayZoneY}]"

class planeContainer:
	def __init__(self) -> None:
		self.planeDefinitions = dict()
		self.planeSquareImages = dict()
		self.planeImages = dict()

	def defineBlankSquare(self, blankSquare):
		self.blankSquare = blankSquare

	def setPlaneDimensions(self, lowerX, upperX, lowerY, upperY):
		self.drawSpaceWidth = upperX - lowerX + 1
		self.drawSpaceHeight = upperY - lowerY + 1
		self.lowerX = lowerX
		self.lowerY = lowerY
		self.upperX = upperX
		self.upperY = upperY
		self.imageWidth = self.upperX - self.lowerX + 1 
		self.imageHeight = self.upperY - self.lowerY + 1

	def addPlane(self):
		nextPlaneID = len(self.planeDefinitions)
		# Preallocate as empty
		mat = list()
		for row in range(self.lowerY, self.upperY+1):
			rowlist = list()
			for cell in range(self.lowerX, self.upperX+1):
				rowlist.append(None)
			mat.append(rowlist)
		self.planeDefinitions[nextPlaneID] = deepcopy(mat)
		self.planeSquareImages[nextPlaneID] = deepcopy(mat)
		self.planeImages[nextPlaneID] = deepcopy(mat)

	def getPlaneCount(self):
		return len(self.planeDefinitions)

	def _setPlaneCell(self, planeID, x, y, obj):
		# Private, expects converted coordinates
		self.planeDefinitions[planeID][y][x] = obj

	def setPlaneCell(self, planeID, x, y, obj):
		# Insert object into plane at y,x cell
		targetX, targetY = self.convertCoordinates(x, y)
		self.planeDefinitions[planeID][targetY][targetX] = obj

	def _checkPlaneCell(self, planeID, x, y):
		# Private, expects converted coordinates
		print(f"{planeID, x, y} occupied: {type(self.planeDefinitions[planeID][y][x])}")
		return type(self.planeDefinitions[planeID][y][x])
	
	def checkPlaneCell(self, planeID, x, y):
		# Check the contents of a cell in a plane
		targetX, targetY = self.convertCoordinates(x, y)
		return type(self.planeDefinitions[planeID][targetY][targetX])
	
	def _getPlaneCell(self, planeID, x, y):
		# Private, expects converted coordinates
		return self.planeDefinitions[planeID][y][x]
	
	def getPlaneCell(self, planeID, x, y):
		# Get the contents of a cell in a plane
		targetX, targetY = self.convertCoordinates(x, y)
		return self.planeDefinitions[planeID][targetY][targetX]

	def convertCoordinates(self, x, y):
		# Converts from bottom left (Jagex) coordinates to top left origin coordinates
		# Accounts for the padding
		targetX = x - self.lowerX
		targetY = self.upperY - y - 1 + 1 # -1 for height conversion, +1 to move away from padding
		# Add one to each to account for padding
		return (targetX, targetY)

	def setPlaneCellWhereAvailable(self, x, y, obj):
		# Convert the coordinates to top left origin
		targetX, targetY = self.convertCoordinates(x, y)
		# Traverse the plane list, seeking the first open cell counting upward
		# Accounts for padding, spins up a new layer if need be
		planeID = self._getCellAvailablePlane(targetX, targetY)
		# If the necessary planeID isn't already in the dict
		for n in range(planeID - (len(self.planeDefinitions)-1)):
			# Spin up a new plane to hold the object
			self.addPlane()
		self._setPlaneCell(planeID, targetX, targetY, obj)

	def _getCellAvailablePlane(self, x, y):
		# Private, expects converted coordinates
		# Iterate upward through existing planes to find an empty cell
		for planeID in range(len(self.planeDefinitions)):
			if self._getPlaneCell(planeID, x, y) is None:
				return planeID
		else:
			# If there were no empty cells, then a new plane is needed
			return planeID+1

	def getCellAvailablePlane(self, x, y):
		# Returns the first plane available for a particular coordinate
		targetX, targetY = self.convertCoordinates(x, y)
		# Traverse the plane list, seeking the first open cell counting upward
		planeID = 0
		while self._getPlaneCell(planeID, targetX, targetY) is not None:
			# Cell is occupied, check the next
			planeID += 1
		return planeID
	
	def renderPlaneSquares(self, planeID):
		# Renders the square images, but not the whole plane image
		# Iterate defs cells, transforming contents to images and storing in images dict
		for y in range(self.imageHeight):
			for x in range(self.imageWidth):
				content = self.planeDefinitions[planeID][y][x]
				if isinstance(content, mapSquare):
					cellImage = content.fetchSquare()
				# elif isinstance(content, mapSquareOfZones):
				# 	cellImage = content.drawSquare()
				elif content is None:
					# Default to empty image
					cellImage = self.blankSquare
				elif isinstance(content, pv.Image):
					# Already rendered
					cellImage = content
				# May want to catch an error here
				self.planeSquareImages[planeID][y][x] = cellImage

	def renderPlane(self, planeID):
		# Renders the whole plane image 
		self.renderPlaneSquares(planeID)
		targetPlane = self.planeSquareImages[planeID]

		# Return a flattened list of the content of the cells
		return [cell for row in targetPlane for cell in row]


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
	displayTilePosition: dict = field(init=False, compare=False)
	positionInTile: dict = field(init=False, compare=False)
	overflowsInto: dict = field(init=False, compare=False)
	zonePosition: tuple = field(init=False, compare=False)
	positionInZone: tuple = field(init=False, compare=False)

	def __post_init__(self):
		# Alter the dict keys to become ints, simplying later referencing
		self.zoomLevelHasIcon = {int(k):v for k,v in self.zoomLevelHasIcon.items() if v}

		# We want to store the icon's owner tile and position in the tile at each zoom level
		self.tilePosition = dict()
		self.positionInTile = dict()
		self.overflowsInto = dict()
		self.displayTilePosition = dict()

		# Calculate the source tile and zone
		squareX = self.tileX // self.coordData["squareTileLength"]
		squareY = self.tileY // self.coordData["squareTileLength"]
		self.tilePosition[self.baselineZoomLevel] = (squareX, squareY)
		zoneX = (self.tileX % self.coordData["squareTileLength"]) // self.coordData["zoneTileLength"]
		zoneY = (self.tileY % self.coordData["squareTileLength"]) // self.coordData["zoneTileLength"]
		self.zonePosition = (zoneX, zoneY)

	def calculateDisplayLocation(self, squareX, squareY):
		# The source square position is provided on init, but other coordinates need calculating
		for zoomLevel in self.zoomLevelHasIcon:
			# Calculate the leaflet tile coordinates using the zoom level to scale the division
			scaleFactor = 2.0**zoomLevel / 2.0**self.baselineZoomLevel
			scaleTileX = int(floor(squareX * scaleFactor))
			scaleTileY = int(floor(squareY * scaleFactor))

			# Save the icon square in a way that is indexable using zoom level
			self.displayTilePosition[zoomLevel] = (scaleTileX, scaleTileY)

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
		return f"Icon '{self.spriteID}'#{self.orderIndex}:[{self.tileX, self.tileY}]"


class IconManager:
	def __init__(self, zoomLevelHasIcons, baselineZoomLevel, coordData) -> None:
		# Initialize information stores
		self.sourceTileOwnsIconList = dict()
		self.displayTileOwnsIconList = dict()
		self.displayTileOverflowIconList = dict()
		self.iconSpriteList = list()
		self.zoomLevelsWithIcons = {int(k):v for k,v in zoomLevelHasIcons.items() if v}
		self.baselineZoomLevel = baselineZoomLevel
		self.coordData = coordData
		for zoomLevel in self.zoomLevelsWithIcons:
			self.sourceTileOwnsIconList[zoomLevel] = dict()
			self.displayTileOwnsIconList[zoomLevel] = dict()
			self.displayTileOverflowIconList[zoomLevel] = dict()
			for planeID in range(0, 3+1):
				# From here we want to nest by square tuple and then by zone tuple into a list of icon objects
				# The source list uses a square and zone spec to save on filtering calculations
				self.sourceTileOwnsIconList[zoomLevel][planeID] = defaultdict(lambda: defaultdict(list))
				self.displayTileOwnsIconList[zoomLevel][planeID] = defaultdict(list)
				self.displayTileOverflowIconList[zoomLevel][planeID] = defaultdict(list)

		# Parse the square definitions to map source->display and display->source lookups
		# self.sourceLookup = dict()
		# self.displayLookup = dict()
		# for squareDef in squareDefs:
		# 	sourceX = squareDef["sourceSquareX"]
		# 	sourceY = squareDef["sourceSquareY"]
		# 	displayX = squareDef["displaySquareX"]
		# 	displayY = squareDef["displaySquareY"]
		# 	self.sourceLookup[(displayX, displayY)] = (sourceX, sourceY)
		# 	self.displayLookup[(sourceX, sourceY)] = (displayX, displayY)

	def addIconSource(self, iconObj: IconDefinition):
		# Ingest the new icon, logging what source square it belongs to at each zoom level
		tilePosX, tilePosY = iconObj.tilePosition[self.baselineZoomLevel] #source square
		zonePosX, zonePosY = iconObj.zonePosition
		plane = iconObj.plane
		self.sourceTileOwnsIconList[self.baselineZoomLevel][plane][(tilePosX, tilePosY)][iconObj.zonePosition].append(iconObj)
		if (tilePosX == 28 or tilePosX == 27) and (tilePosY == 83 or tilePosY == 84):
			print(f"ICON ADDED TO [{tilePosX, tilePosY}][{zonePosX, zonePosY}]:{iconObj}")

	def addIconDisplay(self, iconObj: IconDefinition, iconContainer: mapSquare | mapZone):
		# Using the icon definition and the object it belongs to calculate and store display data
		# print(f"\t{iconObj}")
		# pprint.pprint(self.sourceTileOwnsIconList[self.baselineZoomLevel][1][(27, 83)]) #sources are correct
		for zoomLevel in self.zoomLevelsWithIcons:
			# print(f"\tZoom level: {zoomLevel}")
			# Determine the scale factor for this zoom level
			scaleFactor = 2.0**zoomLevel / 2.0**self.baselineZoomLevel

			# Calculate the in-tile position of the icon
			tilePixelLength = self.coordData["tilePixelLength"]
			squarePixelLength = self.coordData["squarePixelLength"]
			zonePixelLength = self.coordData["zonePixelLength"]
			LEAFLET_TILE_SIZE = 256 #px

			# Start with the icon's prescribed location
			x_px = iconObj.tileX * tilePixelLength 
			y_px = iconObj.tileY * tilePixelLength
			# print(f"\t\t{iconObj.tileX, iconObj.tileY} -> {x_px, y_px}")

			# Determine the relative placement of each icon at a zoom level of 2
			# Use the display data from the definition which owns the icon
			displayData = iconContainer.getDisplayData()
			# print(displayData)
			
			if isinstance(iconContainer, mapZone):
				# For squares compiled from zones
				# Find pixel position of the icon within the zone
				zoneIconRelX_px = x_px % zonePixelLength
				zoneIconRelY_px = y_px % zonePixelLength
				# print(f"\t\tIcon: {zoneIconRelX_px, zoneIconRelY_px} in zone {x_px % squarePixelLength // zonePixelLength, y_px % squarePixelLength // zonePixelLength}")
				# Find pixel position of the displayed zone in the square
				# print(f"\t\t{displayData[2]}, {displayData[3]}")
				squareZoneRelX_px = displayData[2] * zonePixelLength
				squareZoneRelY_px = displayData[3] * zonePixelLength
				# print(f"\t\tZone: {squareZoneRelX_px, squareZoneRelY_px}")
				# Find pixel position of the displayed square in the plane
				originSquareRelX_px = displayData[0] * squarePixelLength
				originSquareRelY_px = displayData[1] * squarePixelLength
				# Sum to get display pixel position, then scale
				relX_px = zoneIconRelX_px + squareZoneRelX_px + originSquareRelX_px
				relY_px = zoneIconRelY_px + squareZoneRelY_px + originSquareRelY_px
			elif isinstance(iconContainer, mapSquare):
				# For regular map squares
				# Find the pixel coordinates of the icon within the square			
				squareIconRelX_px = x_px % squarePixelLength
				squareIconRelY_px = y_px % squarePixelLength
				# Find pixel position of the displayed square in the plane
				originSquareRelX_px = displayData[0] * squarePixelLength
				originSquareRelY_px = displayData[1] * squarePixelLength
				# Sum to get display pixel position, then scale
				relX_px = squareIconRelX_px + originSquareRelX_px
				relY_px = squareIconRelY_px + originSquareRelY_px

			# Scale the relative value
			scaledX_px = relX_px * scaleFactor
			scaledY_px = relY_px * scaleFactor

			# Find the in-tile pixel position of the icon
			inTileX_px = scaledX_px % LEAFLET_TILE_SIZE
			inTileY_px = scaledY_px % LEAFLET_TILE_SIZE
			inTileY_px = LEAFLET_TILE_SIZE - inTileY_px - 1
			iconObj.positionInTile[zoomLevel] = (inTileX_px, inTileY_px)

			# Calculate the leaflet tile coordinates containing the icon
			tileX = scaledX_px // LEAFLET_TILE_SIZE
			tileY = scaledY_px // LEAFLET_TILE_SIZE
			tilePos = (tileX, tileY)
			iconObj.displayTilePosition[zoomLevel] = tilePos

			# Store the icon to be referenced via leaflet coords
			plane = iconObj.plane
			self.displayTileOwnsIconList[zoomLevel][plane][tilePos].append(iconObj)

			# Check for icon overflow into neighbor tiles
			overflowsInto = list()
			leftOverflow = inTileX_px - (15//2) < 0
			topOverflow = inTileY_px - (15//2) < 0
			rightOverflow = inTileX_px + (15//2) > self.coordData["squarePixelLength"]
			bottomOverflow = inTileY_px + (15//2) > self.coordData["squarePixelLength"]
			# recall that the relative y-values are top left origin (-ve means the tile above)
			if leftOverflow: overflowsInto.append((-1, 0))
			if rightOverflow: overflowsInto.append((1, 0))
			if topOverflow: overflowsInto.append((0, 1))
			if bottomOverflow: overflowsInto.append((0, -1)) 
			if leftOverflow and topOverflow: overflowsInto.append((-1, 1))
			if leftOverflow and bottomOverflow: overflowsInto.append((-1, -1))
			if rightOverflow and topOverflow: overflowsInto.append((1, 1))
			if rightOverflow and bottomOverflow: overflowsInto.append((1, -1))
			iconObj.overflowsInto[zoomLevel] = overflowsInto

			# Calculate the overflow targets and store the icon
			for overflowDirection in overflowsInto:
				xShift, yShift = overflowDirection
				overflowX = tileX + xShift
				overflowY = tileY + yShift
				overflowTilePos = (overflowX, overflowY)
				self.displayTileOverflowIconList[zoomLevel][plane][overflowTilePos].append(iconObj)

		# With the proper display position calculated, the iconDef can find the rest
		# iconObj.calculateDisplayLocation(displayX, displayY)
		# # Now map those values
		# for zoomLevel in self.zoomLevelsWithIcons:
		# 	# Fully within the tile
		# 	tilePosX, tilePosY = iconObj.displayTilePosition[zoomLevel]
		# 	zonePosX, zonePosY = iconObj.zonePosition
		# 	plane = iconObj.plane
		# 	self.displayTileOwnsIconList[zoomLevel][plane][(tilePosX, tilePosY)][(zonePosX, zonePosY)].append(iconObj)
			
		# 	# Overflowing into neighbor tiles
		# 	overflowList = iconObj.overflowsInto[zoomLevel]
		# 	for overflowDirection in overflowList:
		# 		xShift, yShift = overflowDirection
		# 		overflowX = tilePosX + xShift
		# 		overflowY = tilePosY + yShift
		# 		overflowZoneX = (zonePosX + xShift) % 8
		# 		overflowZoneY = (zonePosY + yShift) % 8
		# 		self.displayTileOverflowIconList[zoomLevel][plane][(overflowX, overflowY)][(overflowZoneX, overflowZoneY)].append(iconObj)



def buildMapID(mapID, squareDefs, zoneDefs, coordData, tilePath, baseOutPath, configData, basePath):
	# Assemble an image using the square and zone defs
	# First, find the square dimensions of the output
	defUpperSquareX = defUpperSquareY = -999
	defLowerSquareX = defLowerSquareY = 999
	defUpperPlane = -999
	defLowerPlane = 999

	# Parse square definitions
	squareDefs = [squareDefinition(**squareDef) for squareDef in squareDefs]
	heapq.heapify(squareDefs) # ordered by groupID

	# Parse zone definitions
	zoneDefs = [zoneDefinition(**zoneDef) for zoneDef in zoneDefs]
	heapq.heapify(zoneDefs) # ordered by groupID

	# Range the image
	for squareDef in squareDefs:
		defUpperSquareX = max(defUpperSquareX, squareDef.displaySquareX)
		defLowerSquareX = min(defLowerSquareX, squareDef.displaySquareX)
		defUpperSquareY = max(defUpperSquareY, squareDef.displaySquareY)
		defLowerSquareY = min(defLowerSquareY, squareDef.displaySquareY)
		defUpperPlane = max(defUpperPlane, squareDef.upperPlane)
		defLowerPlane = min(defLowerPlane, squareDef.lowerPlane)

	# Range the image
	for zoneDef in zoneDefs:
		defUpperSquareX = max(defUpperSquareX, zoneDef.displaySquareX)
		defLowerSquareX = min(defLowerSquareX, zoneDef.displaySquareX)
		defUpperSquareY = max(defUpperSquareY, zoneDef.displaySquareY)
		defLowerSquareY = min(defLowerSquareY, zoneDef.displaySquareY)
		defUpperPlane = max(defUpperPlane, zoneDef.upperPlane)
		defLowerPlane = min(defLowerPlane, zoneDef.lowerPlane)

	# For now the game only has four planes: 0,1,2,3
	defUpperPlane = min(defUpperPlane, 3)
	defLowerPlane = max(defLowerPlane, 0)

	# Preallocate the data structure containing the squares to be rendered
	# Start with just the base plane, spins up new layers as needed
	planeImages = planeContainer()
	planeImages.setPlaneDimensions(defLowerSquareX, defUpperSquareX, defLowerSquareY, defUpperSquareY)
	planeImages.addPlane()

	# Empty squares will be rendered with a pure black square
	blankSquare = pv.Image.black(coordData["squarePixelLength"], coordData["squarePixelLength"], bands=3).copy(interpretation="srgb")
	planeImages.defineBlankSquare(blankSquare)

	# Iterate over the definitions, replacing cells with mapSquare/mapZone objects
	for squareDef in squareDefs:
		# Get the data from the definition
		sourceData, displayData, levelData = squareDef.getSquareData()

		# Some defs capture and draw on multiple planes
		for level in range(levelData[0], levelData[1]+1):
			# Create the object to go in the cell
			obj = mapSquare(*displayData, *sourceData, level, tilePath, coordData)
			# Place it where possible
			planeImages.setPlaneCellWhereAvailable(squareDef.displaySquareX, squareDef.displaySquareY, obj)

	for zoneDef in zoneDefs:
		# Get the data from the definition
		sourceData, displayData, levelData = zoneDef.getZoneData()
		# print(displayData)
		# Zones in squares belong to a special object which manages the set of zones
		# If this object doesn't already exist it needs to be created
		for level in range(levelData[0], levelData[1]+1):
			# Iterate upward through the planes, checking the content of cells at each height
			for plane in range(planeImages.getPlaneCount()):
				content = planeImages.getPlaneCell(plane, zoneDef.displaySquareX, zoneDef.displaySquareY)
				if content is None:
					# If the cell is empty, claim it
					# msoz = mapSquareOfZones(coordData["squareZoneLength"], coordData["zonePixelLength"], plane)
					msoz = mapSquareOfZones(*displayData, *sourceData, level, tilePath, coordData)
					msoz.addZoneToSquare(mapZone(*displayData, *sourceData, level, tilePath, coordData))
					planeImages.setPlaneCell(plane, zoneDef.displaySquareX, zoneDef.displaySquareY, msoz)
					break
				elif isinstance(content, mapSquareOfZones):
					# If the cell contains the right object, check if its zone is available
					if content.checkIfZoneEmpty(zoneDef.displayZoneX, zoneDef.displayZoneY):
						# If it is empty, claim it
						content.addZoneToSquare(mapZone(*displayData, *sourceData, level, tilePath, coordData))
						break
				else:
					# If the cell contains something else, ignore it
					pass
			else:
				# If the entire list of planes is checked and there are no available spots for the zone
				# Add a plane
				planeImages.addPlane()
				# Create a new map square, add the zone to it, then add the square to the new plane
				planeID = planeImages.getPlaneCount() - 1
				msoz = mapSquareOfZones(coordData["squareZoneLength"], coordData["zonePixelLength"])
				msoz.addZoneToSquare(mapZone(*displayData, *sourceData, level, tilePath, coordData))
				planeImages.setPlaneCell(planeID, zoneDef.displaySquareX, zoneDef.displaySquareY, msoz)
		
	# Once all definitions have been organized, render the results and save
	# outPath = os.path.join(baseOutPath, "base")
	# if not os.path.exists(outPath):
	# 	os.makedirs(outPath)
	# for plane in range(planeImages.getPlaneCount()):
	# 	imageList = planeImages.renderPlane(plane)
	# 	output = pv.Image.arrayjoin(imageList, across=planeImages.imageWidth)
	# 	if output != pv.Image.black(planeImages.imageWidth, planeImages.imageHeight):
	# 		output.write_to_file(os.path.join(outPath, f"{plane}.png"))

	# Once all definitions have been organized, render the results with composites
	# outPath = os.path.join(baseOutPath, "composite")
	# if not os.path.exists(outPath):
	# 	os.makedirs(outPath)
	# Always render and save plane 0
	squareImageList = planeImages.renderPlane(0)
	baseImage = pv.Image.arrayjoin(squareImageList, across=planeImages.imageWidth)
	# Handling of multiband images appears to be bugged, this fixes it
	baseImage = baseImage
	# baseImage.write_to_file(os.path.join(outPath, f"0.png")) # Save immediately
	
	# Load mask thresholding data
	transparencyColor = configData["COMPOSITE_OPTS"]["transparencyColor"]
	transparencyTolerance = configData["COMPOSITE_OPTS"]["transparencyTolerance"]

	print("===========DEFS===========")
	pprint.pprint(planeImages.planeDefinitions)
	print("===========DEFS===========")
	for plane in range(0, planeImages.getPlaneCount()):
		# Render the current plane
		squareImageList = planeImages.renderPlane(plane)
		planeImage = pv.Image.arrayjoin(squareImageList, across=planeImages.imageWidth)

		# If the plane is above 0, it will need to be overlaid atop some composite image
		if plane > 0:
			# Create the new underlay
			mask = (abs(planeImage - transparencyColor) > transparencyTolerance).bandor()
			baseImage = mask.ifthenelse(planeImage, baseImage)

			# Style the underlay
			styledBaseImage = styleLayer(baseImage, configData["COMPOSITE_OPTS"])

			# Composite using mask
			compositeImage = mask.ifthenelse(planeImage, styledBaseImage)
		else:
			compositeImage = planeImage

		# Save the composite
		# outPath = os.path.join(baseOutPath, "composite")
		# if not os.path.exists(outPath):
		# 	os.makedirs(outPath)
		# compositeImage.write_to_file(os.path.join(outPath, f"{plane}.png"))

		# Rescale
		minZoom = configData["ZOOM_OPTS"]["zoomLevels"]["min"]
		maxZoom = configData["ZOOM_OPTS"]["zoomLevels"]["max"]
		baselineZoom = configData["ZOOM_OPTS"]["baselineZoomLevel"]
		kernels = configData["ZOOM_OPTS"]["kernels"] #dict
		squareLength_px = coordData["squarePixelLength"]
		for zoomLevel in range(minZoom, maxZoom+1):
			# Calculate scale factor
			scaleFactor = 2.0**zoomLevel / 2.0**baselineZoom

			# Select the kernel (json keys must be strings)
			kernelStyle = kernels[str(zoomLevel)]

			# Scale and write
			zoomedImage = compositeImage.resize(scaleFactor, kernel=kernelStyle)
			# outPath = os.path.join(baseOutPath, f"scaled/{zoomLevel}")
			# if not os.path.exists(outPath):
			# 	os.makedirs(outPath)
			# zoomedImage.write_to_file(os.path.join(outPath, f"plane_{plane}.png"))

			# At each zoom level lower than baseline we need to pad the image out to align the slicer
			# We need to go to the nearest lower left point, via integer division
			if zoomLevel < baselineZoom:
				# Calculate nearest corner's x position
				zoomCornerX = (planeImages.lowerX // (scaleFactor ** -1)) * (scaleFactor ** -1)
				cornerPadX_squares = 0
				if zoomCornerX != planeImages.lowerX:
					# The missing number of squares can then be calculated
					cornerPadX_squares = planeImages.lowerX - zoomCornerX
					# Convert to pixels
					cornerPadX_px = cornerPadX_squares * squareLength_px * scaleFactor
					# Attach padding to image
					leftPadding = pv.Image.black(cornerPadX_px, zoomedImage.height).copy(interpretation="srgb")
					zoomedImage = leftPadding.join(zoomedImage, "horizontal")
				
				# Calculate nearest corner's y position
				zoomCornerY = (planeImages.lowerY // (scaleFactor ** -1)) * (scaleFactor ** -1)
				cornerPadY_squares = 0
				if zoomCornerY != planeImages.lowerY:
					# The missing number of squares can then be calculated
					cornerPadY_squares = planeImages.lowerY - zoomCornerY
					# Convert to pixels
					cornerPadY_px = cornerPadY_squares * squareLength_px * scaleFactor
					# Attach padding to image
					bottomPadding = pv.Image.black(zoomedImage.width, cornerPadY_px)
					zoomedImage = zoomedImage.join(bottomPadding, "vertical")
				
				# Now the top and right edges need to be aligned to the slicer
				# There may be some number of tiles missing that would complete the zoom box
				# The bit that exists already is "extra" and needs to be rounded out
				extraX_px = (zoomedImage.width % squareLength_px) / squareLength_px
				if extraX_px != 0:
					# Calculate the missing pixels via complement
					missing_px = (1 - extraX_px) * squareLength_px
					rightPadding = pv.Image.black(missing_px, zoomedImage.height)
					zoomedImage = zoomedImage.join(rightPadding, "horizontal")
				
				extraY_px = (zoomedImage.height % squareLength_px) / squareLength_px
				if extraY_px != 0:
					# Calculate the missing pixels via complement
					missing_px = (1 - extraY_px) * squareLength_px
					topPadding = pv.Image.black(zoomedImage.width, missing_px)
					zoomedImage = topPadding.join(zoomedImage, "vertical")

				# Write the output
				# zoomedImage.write_to_file(os.path.join(outPath, f"plane_{plane}_aligned.png"))

			# Now the image is ready for slicing
			dzPath = f"osrs-wiki-maps/out/mapgen/versions/2024-05-29_a/fullplanes/mapID/{mapID}/tiled"
			dzPath = os.path.join("./temp")
			zoomedImage.dzsave(os.path.join(dzPath, f"plane_{plane}/{zoomLevel}"),
								tile_size=squareLength_px,
								suffix='.png[Q=100]',
								depth='one',
								overlap=0,
								layout='google',
								region_shrink='nearest',
								background=0,
								skip_blanks=0)
			
			# The directory needs to be restructured to comport with Jagex/Leaflet coordinates
			# Generate an iterable of all the files in the directory for this pyramid layer
			planeDirectory = os.path.join("./temp", f"plane_{plane}/{zoomLevel}/0")
			pyramidSearchPath = os.path.join(planeDirectory, "**/*.png") 
			pyramidFiles = glob.iglob(pyramidSearchPath, recursive=True)

			# Iterate, using multiple cores if enabled
			for imagePath in pyramidFiles:
				# Google structure inserts images used to compare and eliminate empty tiles
				# Ignore them
				if os.path.split(imagePath)[-1] == "blank.png":
					continue
				imageSquareDimensions = {
					"lowerX": defLowerSquareX, 
					"lowerY": defLowerSquareY, 
					"upperX": defUpperSquareX, 
					"upperY": defUpperSquareY
				}
				renameFile(imagePath, imageSquareDimensions, baselineZoom, coordData, baseOutPath)
			
			# After the files have been moved, the old directory structure can be deleted
			removeSubdirectories("./temp")
			os.rmdir("./temp")

	# Finally, draw the relevant icons
	# First read in the processed list of icons
	iconManager = createIconManager(basePath)

	# Iterating over all map squares to find which icons are drawn where
	for plane in range(0, planeImages.getPlaneCount()):
		for y in range(0, planeImages.imageHeight):
			for x in range(0, planeImages.imageWidth):
				target = planeImages.planeDefinitions[plane][y][x]
				if isinstance(target, mapSquareOfZones):
					# Find the icons that need to be drawn
					target.findIcons(iconManager)
					# print(targetIcons)

					# Now pair those icons with output squares and zones
					pass
				elif isinstance(target, mapSquare):
					# print(target, mapSquare)
					# Filter the list to only owned icons
					target.findIcons(iconManager)
					# print(targetIcons)

					# Now pair these icon lists with the associated output squares
					# target.loadIconDisplayData(iconManager)
					# targetDisplayX = target.displaySquareX
					# targetDisplayY = target.displaySquareY
					# for icon in targetIcons:
					# 	iconManager.addIconDisplay(icon, targetDisplayX, targetDisplayY)
				# elif isinstance(target, mapSquareOfZones):
				# 	# Filter the list to only owned icons
				# 	targetIcons = target.findIcons(iconManager)

	# Load the icon images
	spritesPath = os.path.join(basePath, configData["ICON_OPTS"]["iconPath"])
	iconSprites = loadIcons(spritesPath)

	# With icons found and stored, they can now be written onto the images
	zoomLevelHasIcons = configData["ICON_OPTS"]["zoomLevelHasIcons"]
	for zoomLevel in (int(zl) for zl in zoomLevelHasIcons if zoomLevelHasIcons[zl]):
		# Fetch the files in the directory for post-processing
		zoomDirPath = os.path.join(baseOutPath, str(zoomLevel))
		tileImagePaths = glob.iglob(os.path.join(zoomDirPath, "*.png"))
		for tileImagePath in tileImagePaths:
			plane, squareX, squareY = map(int, os.path.basename(tileImagePath).split(".png")[0].split("_"))

			# Fetch all the icons that need to be drawn
			iconDefs = list()
			if plane == 0:
				for z in range(0, 3+1):
					iconDefs.extend(iconManager.displayTileOwnsIconList[zoomLevel][z][(squareX, squareY)])
					iconDefs.extend(iconManager.displayTileOverflowIconList[zoomLevel][z][(squareX, squareY)])
			else:
				iconDefs.extend(iconManager.displayTileOwnsIconList[zoomLevel][plane][(squareX, squareY)])
				iconDefs.extend(iconManager.displayTileOverflowIconList[zoomLevel][plane][(squareX, squareY)])

			# If there are no icons to draw, skip the tile
			print(f"{plane}, {squareX, squareY} icons: {bool(iconDefs)}")
			if not iconDefs:
				continue

			# If there are icons, create a blank tile to hold them
			iconLayer = pv.Image.black(256, 256, bands=4).copy(interpretation="srgb")

			# Draw every defined icon onto the blank tile
			for iconDef in iconDefs:
				# Load the icon image
				tileX, tileY = iconDef.displayTilePosition[zoomLevel]
				x, y = iconDef.positionInTile[zoomLevel]
				iconImage = pv.Image.new_from_file(iconSprites[iconDef.spriteID])

				# Create a temporary layer for just this icon
				temp = pv.Image.black(256, 256, bands=4).copy(interpretation="srgb")

				# Calculate the icon position
				if tileX==squareX and tileY==squareY:
					# If the icon is drawn in the tile
					iconX = x - math.ceil(iconImage.width/2)
					iconY = y - math.ceil(iconImage.height/2)
					temp = temp.insert(iconImage, iconX, iconY, expand=False)
				else:
					# Icon is overflowing into the tile
					# Calculate current tile's relation to the icon's tile
					offsetX = squareX - tileX
					offsetY = squareY - tileY
					# Use the relation to calculate the icon's position in the current tile
					iconX = x - (offsetX * 256) - math.ceil(iconImage.width/2)
					iconY = y + (offsetY * 256) - math.ceil(iconImage.height/2) # top left coordinates
					temp = temp.insert(iconImage, iconX, iconY, expand=False)

				# Create a mask out of the temp layer and draw onto the iconLayer with it
				mask = (temp[3] == 255) # select pixels with alpha 255
				iconLayer = mask.ifthenelse(temp, iconLayer) # draw them

			# Merge the icon layer onto the tile image
			layerMask = (iconLayer[3] == 255)
			tileImage = pv.Image.new_from_file(tileImagePath)
			outImage = layerMask.ifthenelse(iconLayer[0:3], tileImage)

			# Save the image to temporary file
			# This is necessary because vips reads from the source file while writing the out file
			outPath = os.path.join(os.path.dirname(tileImagePath), f"{plane}_{squareX}_{squareY}-icon.png")
			outImage.write_to_file(outPath)

			# # The original image can now be removed
			# os.remove(tileImagePath)
			# # And the new one renamed
			# os.rename(outPath, tileImagePath)
		# To do this I will need to be able to speedily access the source and display square data from either direction

		# The pre-processing step for icon insertion depends on the defs
		# i.e. the "neighbor" that an icon spills into is determined by the display instead of the source
		# - this is already relative though
		# so its the iconManager that needs to be altered, when adding icons to the scene being rendered

		# Read in the image path
		# Obtain the display plane, x, y
		# From there, look up the corresponding source plane, x, y
		# From there, check the icon manager for icons drawn in those coordinates
		# Then draw those coordinates
		# Now look up 


def getFlattenedDict(dict):
	# Returns a list of all leaves in the dict
	output = list()
	for k, v in dict.items():
		if isinstance(v, MutableMapping):
			output.extend(getFlattenedDict(v))
		else:
			output.extend(v)
	return output


def loadIcons(spritesPath):
	iconPaths = glob.glob(os.path.join(spritesPath, "*.png"))
	iconDict = dict()
	for iconPath in iconPaths:
		iconID = os.path.basename(iconPath).split(".")[0]
		iconDict[int(iconID)] = iconPath
	return iconDict


def removeSubdirectories(topLevelDir):
	# Use DFS to find tree leaves and remove them
	dirsToRemove = [os.path.normpath(path) for path in glob.glob(os.path.join(topLevelDir, "**/"))]
	filesToRemove = [os.path.normpath(path) for path in glob.glob(os.path.join(topLevelDir, "*.*"))]
	# Traverse deeper into the tree
	for dir in dirsToRemove:
		# Empty subdirs and delete
		removeSubdirectories(dir)
		os.rmdir(dir)
	# Remove files
	for file in filesToRemove:
		os.remove(file)


def renameFile(filePath, imageSquareDimensions, baselineZoom, coordData, outPath):
	# Parse the filename to get the tile's location data
	splitPath = os.path.normpath(filePath).split(os.sep)[-5:]
	planeNum = int(splitPath[0].split("_")[-1])
	zoom = int(splitPath[1])
	y = int(splitPath[-2])
	x = int(splitPath[-1].split(".")[0])

	# Scale factor is relevant for all transformations here
	scaleFactor = 2.0**zoom / 2.0**baselineZoom

	# Calculate the height of the slice
	# Need to add one to get the coordinate of the top of the highest square
	# Then use ceiling on the scaling calculation to get the top left corner
	upperY = math.ceil((imageSquareDimensions["upperY"] + 1) / (scaleFactor ** -1))
	lowerY = imageSquareDimensions["lowerY"] // (scaleFactor ** -1)
	height = (upperY - lowerY)

	# Transform the image location within slicer frame to bottom left coordinates
	x_sliceSquare = x
	y_sliceSquare = height - y - 1

	# Calculate the coordinate of the bottom left of the slicer frame
	slicerXBL_square = imageSquareDimensions["lowerX"] // (scaleFactor ** -1)
	slicerYBL_square = lowerY

	# Add the distance from Jagex reference to distance from slicer bottom left
	relX = slicerXBL_square + x_sliceSquare
	relY = slicerYBL_square + y_sliceSquare

	newFileName = f"{planeNum}_{int(relX)}_{int(relY)}.png"
	outPath = os.path.join(outPath, f"{zoom}")
	if not os.path.exists(outPath):
		os.makedirs(outPath)
	
	# If there is an old file in the way it should be replaced
	newPath = os.path.join(outPath, newFileName)
	if os.path.exists(newPath):
		os.remove(newPath)
	os.rename(filePath, newPath)

def styleLayer(image, stylerOpts):
	# Load the style options
	brightnessFrac = stylerOpts["brightnessFraction"]
	contrastFrac = stylerOpts["contrastFraction"]
	grayscaleFrac = stylerOpts["grayscaleFraction"]
	blurRadius = stylerOpts["blurRadius"]
	
	### Brightness and contrast
	# This is done via a linear equation out = contrast * in + brightness
	brightnessValue = ((brightnessFrac * 255) - 255) / 2
	image = contrastFrac * (image - 127) + (127 + brightnessValue)

	### Grayscale
	if 0 < grayscaleFrac <= 1:
		# Convert to .hsv, adjust the saturation band, and convert back to srgb
		image = (image.colourspace("hsv") * [1, (1-grayscaleFrac), 1]).colourspace("srgb")

	### Color Palette
	# Seems unpopular, but would be sepia, etc

	### Dropshadow
	# Seems unpopular, looks nice in some areas of the map

	### Blur
	# Preview the radius of this blur operation using:
	# print(pv.Image.gaussmat(sigma, min_ampl, precision="float", separable=True).rot90().numpy())
	# pyvips implementation skips the first term of the Gaussian: https://www.libvips.org/API/8.9/libvips-create.html#vips-gaussmat
	if blurRadius > 0:
		sigma = 1
		n = blurRadius + 1 
		nthGaussTerm = math.e ** ((-n**2)/(2 * (sigma**2)))
		image = image.gaussblur(sigma, min_ampl=nthGaussTerm, precision="float")

	return image

def loadDefinitions(defsBasePath):
	# Loads the map and square definitions, returning dicts with ID numbers as keys
	# Load mapID square definitions
	squareDefsPath = os.path.join(defsBasePath, "squares")
	squareDefFiles = [os.path.normpath(path) for path in glob.glob(os.path.join(squareDefsPath, "*.json"))]
	squareDefinitions = dict()
	for squareDef in squareDefFiles:
		_, defID = os.path.splitext(os.path.basename(squareDef))[0].split("_") # Expecting 'mapSquareDefinitions_X.json'
		defs = list()
		with open(squareDef) as squareDefFile:
			squareDefs = json.load(squareDefFile)
			for squareDef in squareDefs:
				defs.append(squareDef)
		squareDefinitions[int(defID)] = defs

	# Load mapID zone defintions
	zoneDefsPath = os.path.join(defsBasePath, "zones")
	zoneDefFiles = [os.path.normpath(path) for path in glob.glob(os.path.join(zoneDefsPath, "*.json"))]
	zoneDefinitions = dict()
	for zoneDef in zoneDefFiles:
		_, defID = os.path.splitext(os.path.basename(zoneDef))[0].split("_") # Expecting 'mapZoneDefinitions_X.json'
		defs = list()
		with open(zoneDef) as zoneDefFile:
			zoneDefs = json.load(zoneDefFile)
			for zoneDef in zoneDefs:
				defs.append(zoneDef)
		zoneDefinitions[int(defID)] = defs

	# Package and return
	mapDefinitions = {
		"squares": squareDefinitions,
		"zones": zoneDefinitions
	}
	# Add the number of mapIDs
	mapDefinitions["count"] = max(len(mapDefinitions["squares"]), len(mapDefinitions["zones"]))
	return mapDefinitions

def actionRoutine(basePath):
	"""
		Generates all tiles for mapIDs using the worldMapCompositeDefinitions files from RuneLite
		Uses classes to store the data from the definitions and renders the images tile by tile
		Each generated image is then rescaled, styled, composited, sliced per config file settings
		The resulting image directory is then restructured to match Jagex/Leaflet coordinates
	"""
	coordFilePath = os.path.join(basePath, "coordinateData.json")
	with open(coordFilePath) as coordDataFile:
		coordData = json.load(coordDataFile)
	with open("./scripts/mapBuilderConfig.json") as configFile:
		configData = json.load(configFile)

	# Load the map definitions
	definitionsDirPath = os.path.join(basePath, "worldMapCompositeDefinitions")
	mapDefinitions = loadDefinitions(definitionsDirPath)

	# Find the base tiles to use
	baseTileDir = os.path.join(basePath, configData["MAPID_OPTS"]["baseTilePath"])

	# Build the mapID
	# for mapID in range(0, mapDefinitions["count"]):
	# 	# prevTime = time.time()
	# 	# print(f"MapID: {mapID}")
	# 	squareDefs = mapDefinitions["squares"][mapID]
	# 	zoneDefs = mapDefinitions["zones"][mapID]
	# 	mapIDoutPath = os.path.join(basePath, configData["MAPID_OPTS"]["mapIDoutPath"], str(mapID))
	# 	buildMapID(mapID, squareDefs, zoneDefs, coordData, baseTileDir, mapIDoutPath, configData, basePath)
		# print(f"\tTime: {time.time()-prevTime}")

	mapID = 1
	mapIDoutPath = os.path.join(basePath, configData["MAPID_OPTS"]["mapIDoutPath"], str(mapID))
	buildMapID(mapID, mapDefinitions["squares"][mapID], mapDefinitions["zones"][mapID], coordData, baseTileDir, mapIDoutPath, configData, basePath)

if __name__ == "__main__":
	startTime = time.time()
	actionRoutine("osrs-wiki-maps/out/mapgen/versions/2024-05-29_a")
	print(f"MapID generation took {time.time()-startTime}s")