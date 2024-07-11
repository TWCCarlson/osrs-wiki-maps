from config import MapBuilderConfig, GlobalCoordinateDefinition
# These are ignored when the singleton is created by buildWikiMaps.py
global VERSION, WORKING_DIR, GCS, CONFIG
GCS = GlobalCoordinateDefinition()
CONFIG = MapBuilderConfig()

from definitions import (SquareDefinition, ZoneDefinition, IconDefinition,
						 loadMapDefinitions)
from images import MapImage, PlaneImage, SquareImage, ZoneImage, IconImage
from mapelements import (MapPlane, MapSquare, MapZone, MapIcon, MapMosaic,
						 MapSquareOfZones)
from managers import MapDefsManager, MapIconManager

from collections import defaultdict
import math
import pprint
import os
import time
import json
import glob
import logging

### Pyvips import
# Windows binaries are required: 
# https://pypi.org/project/pyvips/
# https://www.libvips.org/install.html
LIBVIPS_VERSION = "8.15"
vipsbin = os.path.join(os.getcwd(), f"vipsbin/vips-dev-{LIBVIPS_VERSION}/bin")
os.environ['PATH'] = os.pathsep.join((vipsbin, os.environ['PATH']))
# os.environ['VIPS_PROFILE'] = "1"
# os.environ["VIPS_CONCURRENCY"] = "1"
# logging.basicConfig(level = logging.DEBUG)
import pyvips as pv


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
		self.loadDefinitions(defsStore.squareDefs, defsStore.zoneDefs)


	def loadDefinitions(self, squareDefs: list[SquareDefinition],
					 	zoneDefs: list[ZoneDefinition]):
		for sd in squareDefs:
			# Squares get defined for each source plane in the level range
			lowerPlane, upperPlane = sd.getPlaneRange()
			for planeNum in range(lowerPlane, upperPlane+1):
				self.loadSquareDefinition(sd, planeNum)

		for zd in zoneDefs:
			# Zones get defined for each source plane in the level range
			lowerPlane, upperPlane = zd.getPlaneRange()
			for planeNum in range(lowerPlane, upperPlane+1):
				self.loadZoneDefinition(zd, planeNum)

	def loadSquareDefinition(self, sqDef: SquareDefinition, sourcePlane):
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
		
	def loadZoneDefinition(self, zDef: ZoneDefinition, sourcePlane):
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

	def createMapTiles(self, basePath):
		# Pipeline for generating the map tiles specific to this mapID
		TEMP_DIR = "./temp-planes"
		os.mkdir(TEMP_DIR)
		for planeNum in range(self.lowerDisplayPlane, self.upperDisplayPlane+1):
			# Render the plane image from its components
			targetPlane = self.planes[planeNum]	# type: MapMosaic
			if self.mapID == -1:
				# The debug plane images already exist from the cache dump
				planePath = os.path.join(basePath, f"fullplanes/base/plane_{planeNum}.png")
				planeImage = pv.Image.new_from_file(planePath)
			else:
				planeImage = self.renderImages(targetPlane) # type: pv.Image
				planePath = os.path.join(TEMP_DIR, f"plane_{planeNum}.png")
				planeImage.write_to_file(planePath)
				planeImage = pv.Image.new_from_file(planePath)
			# Becuase of how process pipelines are handled, the preceding steps
			# will be repeated quite a lot (i.e. plane 3 will generate a new 
			# assembly of plane 0). It is better to use a single pipeline to 
			# generate the base images, followed by new pipelines which start
			# from this point.
			# Restart the pipeline from this point to save time

			# There is no need to composte the lowest plane
			if planeNum == self.lowerPlane:
				baseImage = planeImage
				compositeImage = planeImage
			elif planeNum > self.lowerPlane:
				baseImage, compositeImage = self.compositeImages(planeImage, baseImage)
			compositePath = os.path.join(TEMP_DIR, f"plane_{planeNum}_comp.png")
			compositeImage.write_to_file(compositePath)
			
			# Restart the pipeline from this point to save time
			compositeImage = pv.Image.new_from_file(compositePath)
			minZoom = CONFIG.zoom.minZoom
			maxZoom = CONFIG.zoom.maxZoom
			for zoomLevel in range(minZoom, maxZoom+1):
				lowerX = targetPlane.bbox["lowerX"]
				lowerZ = targetPlane.bbox["lowerZ"]
				zoomedImage = self.rescaleImages(compositeImage, zoomLevel,
									 			 lowerX, lowerZ)

				# The image can now be sliced
				self.tileImage(zoomedImage, planeNum, zoomLevel)
				
				# The output directory of the slicer needs restructuring
				self.restructureDirectory(planeNum, zoomLevel, basePath)

		# Clean up temporary files
		self.removeSubdirectories(TEMP_DIR)
		os.rmdir(TEMP_DIR)

	def renderImages(self, targetPlane: MapMosaic | str):
		# For each plane, render all relevant images into a complete plane
		if isinstance(targetPlane, MapMosaic):
			# MapMosaics are the OOP structure which have render methods
			targetPlane.render()
			image = targetPlane.getImage()
		elif isinstance(targetPlane, str):
			# Assume a str input is a filepath to load
			image = pv.Image.new_from_file(targetPlane)
		return image
	
	def compositeImages(self, image: pv.Image, baseImage: pv.Image):
		# Create the composite images for ecah plane, where lower planes
		# are stacked underneath upper planes
		# The lowest plane is the base image for stacking operations
		# For planes above 0, the finalized plane image will be a composite
		# Create the stacked underlay by masking the top level and pasting
		# mask = targetPlane.imageContainer.getMask()
		color = CONFIG.composite.transparencyColor
		tolerance = CONFIG.composite.transparencyTolerance
		mask = (abs(image - color) > tolerance).bandor()
		baseImage = mask.ifthenelse(image, baseImage)
		styledPlane = self.stylePlane(baseImage)
		compositeImage = mask.ifthenelse(image, styledPlane)
		return baseImage, compositeImage

	def rescaleImages(self, image: pv.Image, zoomLevel, lowerX, lowerZ):
		# Rescale the plane images
		baselineZoom = CONFIG.zoom.baselineZoomLevel

		# There is no need to rescale the baseline zoom image
		if zoomLevel == baselineZoom:
			return image
		
		# Calculate scale factor for this zoom level
		scaleFactor = 2.0 ** zoomLevel / 2.0 ** baselineZoom
		zoomedImage = self.resizeImage(image, zoomLevel, scaleFactor)

		# At each zoom level lower than baseline, the image need aligning
		if zoomLevel < CONFIG.zoom.baselineZoomLevel:
			# Pad the image to the lnearest ower left point via integer division
			zoomedImage = self.padLeft(zoomedImage, lowerX, scaleFactor)
			zoomedImage = self.padDown(zoomedImage, lowerZ, scaleFactor)

			# Grow the image up and right until it aligns with grid
			zoomedImage = self.padRight(zoomedImage)
			zoomedImage = self.padUp(zoomedImage)
		return zoomedImage

	def resizeImage(self, image, zoomLevel, scaleFactor):
		# Select the kernel for this zoom level (zooming in uses NN)
		kernels = CONFIG.zoom.kernels
		kernelStyle = kernels[zoomLevel]

		# Scale
		zoomedImage = image.resize(scaleFactor, kernel=kernelStyle)
		return zoomedImage

	def tileImage(self, image: pv.Image, planeNum, zoomLevel):
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
		# File names should match Jagex/Leaflet coordinates
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
		image = MapImage.brightnessAndContrast(image)
		image = MapImage.grayscale(image)
		image = MapImage.blur(image)
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

	def renderIcons(self, tileImagePath, iconList: dict[int, list[MapIcon]]):
		# Draws icons onto the rendered tiles from slicing
		# Requires calculating the scaing factor to place the icons
		# Reliant on the directory renaming scheme to choose the right tiles
		zoomLevelsWithIcons = [z for z,i in CONFIG.icon.zoomLevelHasIcons.items() if i]
		for zoomLevel in zoomLevelsWithIcons:
			# Get a list of all the tiles to update and the icons in them
			tilesWithIcons = defaultdict(lambda: defaultdict(list))
			for plane, icons in iconList.items():
				for icon in icons:
					# Ownership
					x, z = icon.tilePosition[zoomLevel]
					tilesWithIcons[plane][(x, z)].append(icon)
					# Overflow
					for overflowTile in icon.overflowsInto[zoomLevel]:
						ox, oz = overflowTile
						tilesWithIcons[plane][(ox, oz)].append(icon)
			
			# Iterate the list of tiles to modify or create images as necessary
			for plane, tiles in tilesWithIcons.items():
				for tile, icons in tiles.items():
					# If there are no icons, skip the tile entirely
					if not icons:
						continue
					# Determine the path of this tile
					imageName = f"{plane}_{tile[0]}_{tile[1]}.png"
					p = os.path.join(tileImagePath, str(zoomLevel), imageName)
					# Insert icons to the tile's image and save
					self.insertIcons(p, tile[0], tile[1], icons, zoomLevel)				

	def insertIcons(self, path, x, z, iconList: list[MapIcon], zoomLevel):
		# Draw icons onto the tile image
		# This is done by compositing the icons into one image, then using
		# a mask to paste the resulting image overtop the existing image
		iconLayer = self.createIconLayer(x, z, iconList, zoomLevel)
		
		# To replace the base image with the icon-implanted image, the old file
		# must be renamed, loaded, then deleted. The new image will be written
		# to the same namespace the old file. This is necessary because pyvips
		# needs the source image to remain on disk during its execution.
		basePath = os.path.dirname(path)
		swapperPath = os.path.basename(path).split(".")[0] + "-icon.png"
		randPath = os.path.join(basePath, swapperPath)
		# Mask the icon layer overtop the tile image
		layerMask = (iconLayer[3] == 255)
		if os.path.exists(path):
			# If the image exists already, load it after changing its name
			os.rename(path, randPath)
			tileImage = pv.Image.new_from_file(randPath)
		else:
			# If the image does not exist, create a new blank image
			tileImage = pv.Image.black(256, 256, bands=3)
			tileImage = tileImage.copy(interpretation="srgb")
		outImage = layerMask.ifthenelse(iconLayer[0:3], tileImage) # drop alpha
		# Save the resulting image to the directory
		outImage.write_to_file(path)
		# Remove the temporary file
		if os.path.exists(randPath):
			os.remove(randPath)

	def createIconLayer(self, x, z, iconList: list[MapIcon], zoomLevel):
		# Creates an overlay image. All icons in the list are drawn onto it
		iconLayer = pv.Image.black(256, 256, bands=4).copy(interpretation="srgb")
		for icon in iconList:
			# Fetch image, icon owner tile, and location in owner tile
			iconImage = icon.imageContainer.image
			iconX_tile, iconZ_tile = icon.tilePosition[zoomLevel]
			x_px, z_px = icon.positionInTile[zoomLevel]

			# Temporary layer for this icon only
			temp = pv.Image.black(256, 256, bands=4).copy(interpretation="srgb")

			# Find the draw location for the icon in this tile
			if iconX_tile==x and iconZ_tile==z:
				# If the tile being drawn is the same as the icons owner tile
				# The in tile location can just be used, adjusting to top left
				iconX_px = x_px - math.ceil(iconImage.width/2)
				iconZ_px = z_px - math.ceil(iconImage.height/2)
			else:
				# If the tile overflows into this tile, the offset which 
				# places the icon in the correct position outside this tile 
				# needs to be found
				offsetX = x - iconX_tile
				offsetZ = z - iconZ_tile
				# From the offset, calculate the correct pixel position
				iconX_px = x_px - (offsetX*256) - math.ceil(iconImage.width/2)
				# Recall that +ve z coordinates values indicate the top left
				# while +ve z pixels indicate the bottom left
				iconZ_px = z_px + (offsetZ*256) - math.ceil(iconImage.height/2)
			# Insert the icon image
			temp = temp.insert(iconImage, iconX_px, iconZ_px, expand=False)
			# Mask the temporary image overtop the base image
			mask = (temp[3] == 255)
			iconLayer = mask.ifthenelse(temp, iconLayer)
		return iconLayer
		

def buildMapID(mapID, basePath, squareDefsPath, zoneDefsPath,
			   iconManager: MapIconManager):
	print(f"BUILDING {mapID}")
	mapIDtime = time.time()
	# Load definitions that create the mapID
	if mapID == -1:
		squareDefs = squareDefsPath
		zoneDefs = zoneDefsPath
	else:
		squareDefs = SquareDefinition.squareDefsFromJSON(squareDefsPath, basePath)
		zoneDefs = ZoneDefinition.zoneDefsFromJSON(zoneDefsPath, basePath)
	defsManager = MapDefsManager(squareDefs, zoneDefs)

	# Build the mapID
	renderTime = time.time()
	mapBuilder = MapBuilder(defsManager, mapID)
	mapBuilder.createMapTiles(basePath)
	print(f"\tRendering Tiles took {time.time()-renderTime:.3f}")

	# Load icon definitions relevant to this mapID
	iconTime = time.time()
	iconList = iconManager.getIconsInID(mapBuilder)
	mapIDPath = os.path.join(basePath, CONFIG.icon.mapIDDirectory, str(mapID))
	mapBuilder.renderIcons(mapIDPath, iconList)
	print(f"\tInserting Icons took {time.time()-iconTime:.2f}")

	print(f"GENERATING {mapID} TOOK {time.time()-mapIDtime:.2f}")


def actionRoutine(basePath):
	"""
	Generates all tiles for all mapIDs using the worldMapCompositeDefinitions 
	
	Loads definition files dumped from RuneLite, passing the information to
	classes to store the data. Using that information, the tile images are
	generated. Each generated image is then rescaled, styled, composited, 
	and sliced per config file settings. The resulting image directory from a
	dzsave operation is then restructured to match Jagex/Leaflet coordinates,
	Finally, icon locations are calculated and their sprites are inserted to 
	the correct image files.
	"""
	# Data paths
	squareDefsPath = CONFIG.mapid.squareDefsPath
	squareDefsPath = os.path.join(basePath, squareDefsPath)
	zoneDefsPath = CONFIG.mapid.zoneDefsPath
	zoneDefsPath = os.path.join(basePath, zoneDefsPath)
	iconDefsPath = CONFIG.icon.iconDefs
	iconDefsPath = os.path.join(basePath, iconDefsPath)

	# Count determines how many mapIDs are generated
	squareDefsCount = len(os.listdir(squareDefsPath))
	zoneDefsCount = len(os.listdir(zoneDefsPath))
	defsCount = min(squareDefsCount, zoneDefsCount)

	# The icon manager should only be created once, as icons are reused in IDs
	# Load icon definitions
	iconDefs = IconDefinition.iconDefsFromJSON(iconDefsPath)
	iconManager = MapIconManager(iconDefs, basePath)

	# Building the debug (-1) mapID (contains all tiles, with icons)
	# This is created using spoofed definitions that render in-place
	# Therefore each spoof definition is made by iterating the square ranges
	debugSquareDefs = SquareDefinition.spoofAllSquareDefs(basePath)
	debugZoneDefs = list() # There are no zone definitions for this
	buildMapID(-1, basePath, debugSquareDefs, debugZoneDefs, iconManager)

	# Build the mapID
	for mapID in range(defsCount):
		squareDefPath = os.path.join(squareDefsPath, f"mapSquareDefinitions_{mapID}.json")
		zoneDefPath = os.path.join(zoneDefsPath, f"zoneDefinitions_{mapID}.json")
		buildMapID(mapID, basePath, squareDefPath, zoneDefPath, iconManager)

	# mapID = 4
	# squareDefsPath = os.path.join(squareDefsPath, f"mapSquareDefinitions_{mapID}.json")
	# zoneDefsPath = os.path.join(zoneDefsPath, f"zoneDefinitions_{mapID}.json")
	# buildMapID(mapID, basePath, squareDefsPath, zoneDefsPath, iconManager)

if __name__ == "__main__":
	startTime = time.time()
	VERSION = "2024-07-24_0_a"
	WORKING_DIR = f"./osrs-wiki-maps/out/mapgen/versions/{VERSION}"
	GCS = GlobalCoordinateDefinition.fromJSON(F"{WORKING_DIR}/coordinateData.json")
	CONFIG = MapBuilderConfig.fromJSON("./scripts/mapBuilderConfig.json")
	actionRoutine(f"osrs-wiki-maps/out/mapgen/versions/{VERSION}")
	print(f"MapID generation took {time.time()-startTime:.2f}s")