from config import MapBuilderConfig, GlobalCoordinateDefinition
GCS = GlobalCoordinateDefinition.fromJSON("./osrs-wiki-maps/coordinateData.json")
CONFIG = MapBuilderConfig.fromJSON("./scripts/mapBuilderConfig.json")
from definitions import (SquareDefinition, ZoneDefinition, IconDefinition)
from images import PlaneImage, SquareImage, ZoneImage, IconImage
from mapelements import (MapPlane, MapSquare, MapZone, MapIcon, MapMosaic,
						 MapSquareOfZones)

from collections import defaultdict
import math
import pprint
from copy import deepcopy
import os
import time
import json
import glob

### Pyvips import
# Windows binaries are required: 
# https://pypi.org/project/pyvips/
# https://www.libvips.org/install.html
LIBVIPS_VERSION = "8.15"
vipsbin = os.path.join(os.getcwd(), f"vipsbin/vips-dev-{LIBVIPS_VERSION}/bin")
os.environ['PATH'] = os.pathsep.join((vipsbin, os.environ['PATH']))
# os.environ['VIPS_PROFILE'] = "1"
import pyvips as pv


# Generic image processing

def brightnessAndContrast(image):
	brightnessFrac = CONFIG.composite.brightnessFraction
	contrastFrac = CONFIG.composite.contrastFraction
	if 0 <= brightnessFrac <= 1.0 and 0 <= contrastFrac <= 1.0:
		# This is done via a linear equation out = contrast * in + brightness
		brightnessValue = ((brightnessFrac * 255) - 255) / 2
		image = contrastFrac * (image - 127) + (127 + brightnessValue)
		return image
	elif brightnessFrac > 1 or brightnessFrac < 0:
		raise ValueError("Brightness adjustment fraction not between 0 and 1")
	elif contrastFrac > 1 or contrastFrac < 0:
		raise ValueError("Contrast adjustment fraction not between 0 and 1")

def grayscale(image):
	grayscaleFrac = CONFIG.composite.grayscaleFraction
	if 0 <= grayscaleFrac <= 1:
		# Convert to .hsv, adjust the saturation band, and convert back to srgb
		image = image.colourspace("hsv")
		image = image * [1, (1-grayscaleFrac), 1]
		image = image.colourspace("srgb")
		return image
	else:
		raise ValueError("Grayscale adjustment fraction not between 0 and 1")

def blur(image):
	# Preview the radius of this blur operation using:
	# print(pv.Image.gaussmat(sigma, min_ampl, precision="float", separable=True).rot90().numpy())
	# pyvips implementation skips the first term of the Gaussian: https://www.libvips.org/API/8.9/libvips-create.html#vips-gaussmat
	blurRadius = CONFIG.composite.blurRadius
	if blurRadius > 0:
		# This approach calculates the amplitude cutoff for passed radius
		sigma = 1
		n = blurRadius + 1
		nthGaussTerm = math.e ** (-(n**2)/(2 * (sigma**2)))
		return image.gaussblur(sigma, min_ampl=nthGaussTerm, precision="float")


class MapDefsManager():
	"""
	Stores the square and zone definitions
	Also maps source squares and zones to display squares and zones
	"""
	# Holds a map of source->display [plane][square][zone]
	def __init__(self, squareDefs: list[SquareDefinition], 
			  	 zoneDefs: list[SquareDefinition]):
		self.squareDefs = squareDefs
		self.zoneDefs = zoneDefs

		# Default map dimensions
		self.lowerSquareX = math.inf
		self.upperSquareX = -math.inf
		self.lowerSquareZ = math.inf
		self.upperSquareZ = -math.inf
		self.lowerPlane = math.inf
		self.upperPlane = -math.inf

		# Post-init tasks
		self._rangeImage()
		self._sortDefinitions()
		self._buildReferences(self.squareDefs, self.zoneDefs)
	
	def _rangeImage(self) -> None:
		# Calculate the dimensions of the output image in squares
		# Check square definitions
		for sd in self.squareDefs:
			self.lowerSquareX = min(self.lowerSquareX, sd.displaySquareX)
			self.upperSquareX = max(self.upperSquareX, sd.displaySquareX)
			self.lowerSquareZ = min(self.lowerSquareZ, sd.displaySquareZ)
			self.upperSquareZ = max(self.upperSquareZ, sd.displaySquareZ)
			self.lowerPlane = min(self.lowerPlane, sd.lowerPlane)
			self.upperPlane = max(self.upperPlane, sd.upperPlane)
		# Check zone definitions
		for zd in self.zoneDefs:
			self.lowerSquareX = min(self.lowerSquareX, zd.displaySquareX)
			self.upperSquareX = max(self.upperSquareX, zd.displaySquareX)
			self.lowerSquareZ = min(self.lowerSquareZ, zd.displaySquareZ)
			self.upperSquareZ = max(self.upperSquareZ, zd.displaySquareZ)
			self.lowerPlane = min(self.lowerPlane, zd.lowerPlane)
			self.upperPlane = max(self.upperPlane, zd.upperPlane)
	
	def _sortDefinitions(self) -> None:
		self.squareDefs.sort()
		self.zoneDefs.sort()

	def _buildReferences(self, squareDefs: list[SquareDefinition],
						 zoneDefs: list[ZoneDefinition]) -> None:
		# Constructs a dictionary mapping tuple source coords to display coords
		self.sourceToDisplay = dict()
		for plane in range(self.lowerPlane, self.upperPlane+1):
			self.sourceToDisplay[plane] = dict()

		# Square definitions don't change zone locations, preallocate
		unchangedSquare = dict(displaySquare={}, sourceZone={})
		for i in range(0, GCS.squareZoneLength):
			for j in range(0, GCS.squareZoneLength):
				unchangedSquare['sourceZone'][(i, j)] = (i, j)

		# Load square definition mappings
		for sd in squareDefs:
			for plane in range(sd.lowerPlane, sd.upperPlane+1):
				source = sd.getSourceSquare()
				display = sd.getDisplaySquare()
				# Zones are unchanged, but need to be mapped
				self.sourceToDisplay[plane][source] = deepcopy(unchangedSquare)
				parentSquare = self.sourceToDisplay[plane][source]
				parentSquare['displaySquare'] = display

		# Load zone definition mappings
		for zd in zoneDefs:
			for plane in range(zd.lowerPlane, zd.upperPlane+1):
				sourceSquare = zd.getSourceSquare()
				sourceZone = zd.getSourceZone()
				displaySquare = zd.getDisplaySquare()
				displayZone = zd.getDisplayZone()
				planeDict = self.sourceToDisplay[plane]
				if sourceSquare not in self.sourceToDisplay[plane]:
					planeDict[sourceSquare] = dict(displaySquare={}, sourceZone={})
				parentSquare = self.sourceToDisplay[plane][sourceSquare]
				parentSquare['displaySquare'] = displaySquare
				parentSquare['sourceZone'][sourceZone] = displayZone

	def getDefsBBox(self):
		out = {
			"lowerX": self.lowerSquareX,
			"upperX": self.upperSquareX,
			"lowerZ": self.lowerSquareZ,
			"upperZ": self.upperSquareZ,
			"lowerPlane": self.lowerPlane,
			"upperPlane": self.upperPlane
		}
		return out


class MapBuilder():
	def __init__(self, defsStore: MapDefsManager, ID) -> None:
		self.mapID = ID

		# Save a reference to the store
		self.defsStore = defsStore

		# Define plane shape
		bbox = defsStore.getDefsBBox()

		# Clamp plane range to 0 through 3
		# This is necessary because The Abyss (ID 40) has levels:6 (???)
		# Also, some mapIDs only source tiles from planes above 0
		# The current output strategy pushes things down to the bottommost plane
		# Therefore 0 should always be included
		self.lowerPlane = 0
		self.upperPlane = min(3, bbox["upperPlane"])

		# Track the highest display plane needed
		self.upperDisplayPlane = -math.inf
		self.lowerDisplayPlane = math.inf

		# Create the registry of planes
		self.planes = dict()
		for planeNum in range(self.lowerPlane, self.upperPlane+1):
			# Planes are a mosaic of squares
			self.planes[planeNum] = MapPlane(bbox["lowerX"],
											 bbox["upperX"],
											 bbox["lowerZ"],
											 bbox["upperZ"],
											 planeNum)
			
		# Iterate the definitions, loading them into the plane
		self._loadDefinitions(defsStore.squareDefs, defsStore.zoneDefs)


	def _loadDefinitions(self, squareDefs: list[SquareDefinition],
					 	zoneDefs: list[ZoneDefinition]):
		for sd in squareDefs:
			# Squares get defined for each source plane in the level range
			lowerPlane, upperPlane = sd.getPlaneRange()
			for planeNum in range(lowerPlane, upperPlane+1):
				self._loadSquareDefinition(sd, planeNum)

		for zd in zoneDefs:
			# Zones get defined for each source plane in the level range
			lowerPlane, upperPlane = zd.getPlaneRange()
			for planeNum in range(lowerPlane, upperPlane+1):
				self._loadZoneDefinition(zd, planeNum)

	def _loadSquareDefinition(self, sqDef: SquareDefinition, sourcePlane):
		newSquare = MapSquare(sqDef, sourcePlane)
		for planeNum in range(self.lowerPlane, self.upperPlane+1):
			x, y = newSquare.definition.getDisplaySquare()
			targetPlane = self.planes[planeNum] # type: MapPlane
			if targetPlane.checkIfCellEmpty(x, y):
				targetPlane.insertToCell(x, y, newSquare)
				self.updateDisplayPlanes(planeNum)
				break
		else:
			# The next free plane is outside the clamped range
			# This is a fallthrough case requiring code adjustments, probably
			# Currently triggered by MapID 40 (The Abyss) which has 6 levels
			# raise IndexError("Cell is occupied on all allowed planes")
			pass
		
	def _loadZoneDefinition(self, zDef: ZoneDefinition, sourcePlane):
		newZone = MapZone(zDef, sourcePlane)
		newZoneDef = newZone.definition # type: ZoneDefinition
		# Iterate the display planes
		for planeNum in range(self.lowerPlane, self.upperPlane+1):
			x, y = newZoneDef.getDisplaySquare()
			i, j = newZoneDef.getDisplayZone()
			targetPlane = self.planes[planeNum] # type: MapPlane
			# If the cell is empty, a zone container needs to be created
			if targetPlane.checkIfCellEmpty(x, y):
				msoz = MapSquareOfZones(planeNum)
				targetPlane.insertToCell(x, y, msoz)
			# If not, then the contents must be MapSquareOfZones
			target = targetPlane.getCellContents(x, y) # type: MapSquareOfZones
			if target.checkIfCellEmpty(i, j):
				target.insertToCell(i, j, newZone)
				self.updateDisplayPlanes(planeNum)
				break
			# Its possible an error on Jagex's side could cause both zones and
			# squares to appear in the same 'cell'. This would cause a problem
			# that needs to be handled, but hasn't been seen yet.
		else:
			# The next free plane is outside the spec'd or clamped range
			# This is a fallthrough case requiring code adjustments, probably
			# Currently triggered by MapID 40 (The Abyss) which has 6 levels
			# raise IndexError("Cell is occupied on all allowed planes")
			pass

	def updateDisplayPlanes(self, planeNum):
		self.upperDisplayPlane = max(self.upperDisplayPlane, planeNum)
		self.lowerDisplayPlane = min(self.lowerDisplayPlane, planeNum)

	def renderImages(self, basePath):
		# For each plane, render all relevant images
		for planeNum in range(self.lowerDisplayPlane, self.upperDisplayPlane+1):
			targetPlane = self.planes[planeNum] # type: MapMosaic
			targetPlane.render()

			# Style the planes and then stack them for aesthetics
			image = targetPlane.getImage()
			# The lowest plane is the base image for stacking operations
			if planeNum == self.lowerPlane:
				baseImage = image
				compositeImage = image
			# For planes above 0, the finalized plane image will be a composite
			elif planeNum > self.lowerPlane:
				# Create the stacked underlay
				mask = targetPlane.imageContainer.getMask()
				baseImage = mask.ifthenelse(image, baseImage)
				styledPlane = self.stylePlane(baseImage)
				compositeImage = mask.ifthenelse(image, styledPlane)

			# Rescale the plane images and slice into map tiles
			minZoom = CONFIG.zoom.minZoom
			maxZoom = CONFIG.zoom.maxZoom
			baselineZoom = CONFIG.zoom.baselineZoomLevel
			for zoomLevel in range(minZoom, maxZoom+1):
				# Calculate scale factor for this zoom level
				scaleFactor = 2.0 ** zoomLevel / 2.0 ** baselineZoom
				zoomedImage = self.resizeImage(compositeImage, 
								   			   zoomLevel, scaleFactor)

				# At each zoom level lower than baseline, the image need aligning
				# Pad the image to the lower left point via integer division
				if zoomLevel < 2:
					lowerX = targetPlane.bbox["lowerX"]
					zoomedImage = self.padLeft(zoomedImage, lowerX, scaleFactor)
					lowerY = targetPlane.bbox["lowerZ"]
					zoomedImage = self.padDown(zoomedImage, lowerY, scaleFactor)

					# Grow the image up and right until it aligns with grid
					zoomedImage = self.padRight(zoomedImage)
					zoomedImage = self.padUp(zoomedImage)
			
				# The image can now be sliced
				self.tileImage(zoomedImage, planeNum, zoomLevel)
				
				# The output directory of the slicer needs restructuring
				self.restructureDirectory(planeNum, zoomLevel, basePath)

	def resizeImage(self, image, zoomLevel, scaleFactor):
		# Select the kernel for this zoom level (zooming in uses NN)
		kernels = CONFIG.zoom.kernels
		kernelStyle = kernels[zoomLevel]
		
		# Scale
		zoomedImage = image.resize(scaleFactor, kernel=kernelStyle)
		return zoomedImage

	def tileImage(self, image, planeNum, zoomLevel):
		dzPath = "./temp"
		outPath = os.path.join(dzPath, f"plane_{planeNum}/{zoomLevel}")
		backgroundColor = CONFIG.composite.transparencyColor
		backgroundTolerance = CONFIG.composite.transparencyTolerance
		image.dzsave(outPath,
					 tile_size = GCS.squarePixelLength,
					 suffix='.png[Q=100]',
					 depth='one',
					 overlap=0,
					 layout='google',
					 region_shrink='nearest',
					 background=backgroundColor,
					 skip_blanks=backgroundTolerance)
		
	def restructureDirectory(self, planeNum, zoomLevel, basePath):
		# It should match Jagex/Leaflet coordinates
		# Generate an iterable of all the files in the directory
		dirSpec = f"plane_{planeNum}/{zoomLevel}/0"
		planeDirectory = os.path.join("./temp", dirSpec)
		pyramidSearchPath = os.path.join(planeDirectory, "**/*.png")
		pyramidFiles = glob.iglob(pyramidSearchPath, recursive=True)

		# Iterate
		for imagePath in pyramidFiles:
			# Google structure inserts images representing blank tiles
			# Ignore them
			if os.path.split(imagePath)[-1] == "blank.png":
				continue
			dimensions = self.defsStore.getDefsBBox()
			self.renameFile(imagePath, zoomLevel, dimensions, basePath)

		# Clean up temporary files
		self.removeSubdirectories("./temp")
		os.rmdir("./temp")
		
	def padLeft(self, image, lowerX, scaleFactor):
		inverseScale = scaleFactor ** -1
		zoomCornerX = (lowerX // inverseScale) * inverseScale
		if zoomCornerX != lowerX:
			# The missing number of squares can then be calculated
			cornerPadX_squares = lowerX - zoomCornerX
			# Convert to pixels
			cornerPadX_px = cornerPadX_squares * GCS.squarePixelLength * scaleFactor
			# Attach padding to image
			leftPadding = pv.Image.black(cornerPadX_px, image.height).copy(interpretation="srgb")
			image = leftPadding.join(image, "horizontal")
		return image
	
	def padDown(self, image, lowerY, scaleFactor):
		inverseScale = scaleFactor ** -1
		zoomCornerY = (lowerY // inverseScale) * inverseScale
		if zoomCornerY != lowerY:
			# The missing number of squares can then be calculated
			cornerPadY_squares = lowerY - zoomCornerY
			# Convert to pixels
			cornerPadY_px = cornerPadY_squares * GCS.squarePixelLength * scaleFactor
			# Attach padding to image
			downPadding = pv.Image.black(image.width, cornerPadY_px).copy(interpretation="srgb")
			image = image.join(downPadding, "vertical")
		return image

	def padRight(self, image):
		overhangX_px = image.width % GCS.squarePixelLength
		if overhangX_px != 0:
			overhangX_square = overhangX_px / GCS.squarePixelLength
			missingX_square = (1 - overhangX_square)
			missingX_px = missingX_square * GCS.squarePixelLength
			rightPadding = pv.Image.black(missingX_px, image.height)
			image = image.join(rightPadding, "horizontal")
		return image
	
	def padUp(self, image):
		overhangZ_px = image.height % GCS.squarePixelLength
		if overhangZ_px != 0:
			overhangZ_square = overhangZ_px / GCS.squarePixelLength
			missingZ_square = (1 - overhangZ_square)
			missingZ_px = missingZ_square * GCS.squarePixelLength
			upPadding = pv.Image.black(image.width, missingZ_px)
			image = upPadding.join(image, "vertical")
		return image

	def stylePlane(self, image):
		# Plane styling pipeline
		image = brightnessAndContrast(image)
		image = grayscale(image)
		image = blur(image)
		return image

	def renameFile(self, filePath, zoom, defsDimensions, basePath):
		splitPath = os.path.normpath(filePath).split(os.sep)[-5:]
		planeNum = int(splitPath[0].split("_")[-1])
		zoom = int(splitPath[1])
		y = int(splitPath[-2])
		x = int(splitPath[-1].split(".")[0])
		
		# Scale factor is relevant for determining the correct positions
		scaleFactor = 2.0 ** zoom / 2.0 ** CONFIG.zoom.baselineZoomLevel

		# Calculate the height of the slice
		# Need to add one to get the coordinate of the top of the highest square
		# Then use ceiling on the scaling calculation to get the top left corner
		upperY = math.ceil((defsDimensions["upperZ"] + 1) / (scaleFactor ** -1))
		lowerY = defsDimensions["lowerZ"] // (scaleFactor ** -1)
		height = (upperY - lowerY)

		# Transform the image location within slicer frame to bottom left coordinates
		x_sliceSquare = x
		y_sliceSquare = height - y - 1

		# Calculate the coordinate of the bottom left of the slicer frame
		slicerXBL_square = defsDimensions["lowerX"] // (scaleFactor ** -1)
		slicerYBL_square = lowerY

		# Add the distance from Jagex reference to distance from slicer bottom left
		relX = slicerXBL_square + x_sliceSquare
		relY = slicerYBL_square + y_sliceSquare

		newFileName = f"{planeNum}_{int(relX)}_{int(relY)}.png"
		outPath = CONFIG.directory.outPath
		outPath = os.path.join(basePath, outPath, str(self.mapID), f"{zoom}")
		if not os.path.exists(outPath):
			os.makedirs(outPath)

		# If there is an old file in the way it should be replaced
		newPath = os.path.join(outPath, newFileName)
		if os.path.exists(newPath):
			os.remove(newPath)
		os.rename(filePath, newPath)

	def removeSubdirectories(self, topLevelDir):
		# Depth first search to find all directories and files
		dirsToRemove = glob.glob(os.path.join(topLevelDir, "**/"))
		dirsToRemove = [os.path.normpath(path) for path in dirsToRemove]
		filesToRemove = glob.glob(os.path.join(topLevelDir, "*.*"))
		filesToRemove = [os.path.normpath(path) for path in filesToRemove]
		for dir in dirsToRemove:
			# Empty subdirectories and delete
			self.removeSubdirectories(dir)
			os.rmdir(dir)
		# Remove files from this directory
		for file in filesToRemove:
			os.remove(file)

class MapIconManager:
	# Holds definitions for icons
	# Holds a square-coordinate indexable map, a list of all icons in the square
	def __init__(self, iconDefs: list[IconDefinition], basePath) -> None:
		# Sort the icon defs and save
		self.iconDefs = iconDefs

		# Manager loads its own icons for reference
		self.basePath = basePath
		
		# Filter out icons not in the definitions
		self._sortDefinitions()
		self._loadIconImages()
		self._processIconList()

	def _sortDefinitions(self):
		self.iconDefs.sort()

	def _loadIconImages(self):
		# Load all the icon images into referenceable memory
		self.iconIDtoImage = dict()
		iconImageDir = os.path.join(self.basePath, CONFIG.icon.iconPath)
		iconImagePaths = glob.iglob(os.path.join(iconImageDir, "*.png"))
		for iconImagePath in iconImagePaths:
			iconID = int(os.path.basename(iconImagePath).split(".")[0])
			iconImageContainer = IconImage(iconImagePath)
			self.iconIDtoImage[iconID] = iconImageContainer

	def _processIconList(self):
		
		pass
		

	def calculateOwnerTiles(self):
		# zoomLevelHasIcons = CONFIG.icon.zoomLevelHasIcons.items()
		# zoomLevelsWithIcons = {int(k):v for k,v in zoomLevelHasIcons if v}
		# for zoomLevel in zoomLevelsWithIcons:
		# 	for iconDef in self.iconDefs:
		# 		pass
		pass


# How much encapsulation?

# IconDefinition holds tileX, tileZ, plane, and spriteID (plus render index)
# - Expect to fetch this data
# - Encapsulates the unload from json
# - Custom repr
# IconImage holds the pyvips image and the source path
# IconData holds IconDefinition and IconImage

# MapManager holds all the map data and highest-level methods
# - There is a list of planes
# - Planes are mosaic managers containing squares
# - Squares can also be mosaics containing zones

# A squareData is defined by its squareDefinition, squareImage
# A zoneData is defined by its zoneDefinition, zoneImage
# There is no planeData, only planeManagers with squares


def buildMapID(mapID, basePath, squareDefsPath, zoneDefsPath, iconDefsPath):
	# Load definitions that create the mapID
	squareDefs = SquareDefinition.squareDefsFromJSON(squareDefsPath, basePath)
	zoneDefs = ZoneDefinition.zoneDefsFromJSON(zoneDefsPath, basePath)
	defsManager = MapDefsManager(squareDefs, zoneDefs)

	# Build the mapID
	mapBuilder = MapBuilder(defsManager, mapID)
	mapBuilder.renderImages(basePath)

	# Load icon definitions
	iconDefs = IconDefinition.iconDefsFromJSON(iconDefsPath)
	iconManager = MapIconManager(iconDefs, basePath)
	# print(iconDefs)

def actionRoutine(basePath):
	"""
	Generates all tiles for all mapIDs using the worldMapCompositeDefinitions 
	
	Loads definition files dumped from RuneLite, passing the information to
	classes to store the data. Using that information, the tile images are
	generated. Each generated image is then rescaled, styled, composited, 
	and sliced per config file settings. The resulting image directory from a
	dzsave operation is then restructured to match Jagex/Leaflet coordinates
	"""
	# Data paths
	squareDefsPath = CONFIG.mapid.squareDefsPath
	squareDefsPath = os.path.join(basePath, squareDefsPath)
	zoneDefsPath = CONFIG.mapid.zoneDefsPath
	zoneDefsPath = os.path.join(basePath, zoneDefsPath)

	iconDefsPath = CONFIG.icon.iconDefs
	iconDefsPath = os.path.join(basePath, iconDefsPath)
	# baseTilePath = os.path.join(basePath, "tiles/rendered/-1/2")
	# coordDataPath = os.path.join(basePath, "coordinateData.json")
	# configDataPath = os.path.join(basePath, "./scripts/mapBuilderConfig.json")

	# Count determines how many mapIDs are generated
	squareDefsCount = len(os.listdir(squareDefsPath))
	zoneDefsCount = len(os.listdir(zoneDefsPath))
	defsCount = min(squareDefsCount, zoneDefsCount)

	# Build the mapID
	# for mapID in range(defsCount):
	# 	prevTime = time.time()
	# 	print(f"MapID: {mapID}")
	# 	squareDefPath = os.path.join(squareDefsPath, f"mapSquareDefinitions_{mapID}.json")
	# 	zoneDefPath = os.path.join(zoneDefsPath, f"zoneDefinitions_{mapID}.json")
	# 	buildMapID(mapID, basePath, squareDefPath, zoneDefPath, iconDefsPath)
	# 	print(f"\tTime: {time.time()-prevTime}")

	mapID = 44
	squareDefsPath = os.path.join(squareDefsPath, f"mapSquareDefinitions_{mapID}.json")
	zoneDefsPath = os.path.join(zoneDefsPath, f"zoneDefinitions_{mapID}.json")
	buildMapID(mapID, basePath, squareDefsPath, zoneDefsPath, iconDefsPath)

if __name__ == "__main__":
	startTime = time.time()
	actionRoutine("osrs-wiki-maps/out/mapgen/versions/2024-05-29_a")
	print(f"MapID generation took {time.time()-startTime}s")