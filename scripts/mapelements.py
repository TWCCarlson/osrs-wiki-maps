from definitions import (SquareDefinition, ZoneDefinition, IconDefinition)
from images import MapImage, PlaneImage, SquareImage, ZoneImage, IconImage
from config import MapBuilderConfig, GlobalCoordinateDefinition
CONFIG = MapBuilderConfig()
GCS = GlobalCoordinateDefinition()

import os
import math

# Pyvips import is OS-dependent, use dispatcher file
from pyvips_import import pyvips as pv


class MapMosaic():
	def __init__(self, lowerX, upperX, lowerZ, upperZ, level) -> None:
		# Save the bbox
		self.bbox = {
			"lowerX": lowerX,
			"upperX": upperX,
			"lowerZ": lowerZ,
			"upperZ": upperZ,
		}

		# Preallocate the empty mosaic with passed dimensions
		self.mosaic = dict()
		for y in range(lowerZ, upperZ+1):
			for x in range(lowerX, upperX+1):
				self.mosaic[(x, y)] = None

		# Save the level
		self.level = level

		# Save dimensions
		self.width = upperX - lowerX + 1
		self.height = upperZ - lowerZ + 1

		# Image object
		self.imageContainer = None

	def checkIfCellEmpty(self, x, z) -> bool:
		return not bool(self.mosaic[(x, z)])
	
	def insertToCell(self, x, z, obj):
		self.mosaic[(x, z)] = obj

	def getCellContents(self, x, z):
		return self.mosaic[(x, z)]

	def render(self):
		# Render all items composing the mosaic
		item: MapSquare | MapSquareOfZones | MapZone
		for coords, item in self.mosaic.items():
			validTypes = (MapSquare, MapSquareOfZones, MapZone)
			if isinstance(item, validTypes):
				item.render()
			else:
				item = self.makeBlank()
				self.mosaic[coords] = item

		# Create the output list
		tileList = list()
		# Insertion order matters
		# Pyvips uses top left origin, while Jagex is bottom left
		# Therefore the y-ordering is descending
		for z in range(self.bbox["upperZ"], self.bbox["lowerZ"]-1, -1):
			for x in range(self.bbox["lowerX"], self.bbox["upperX"]+1):
				item = self.mosaic[(x, z)]
				tileList.append(item.getImage())

		# Now join them together to render the mosaic
		tiledImage = pv.Image.arrayjoin(tileList, across=self.width)
		self.imageContainer = PlaneImage(tiledImage)

	def makeBlank(self):
		# Overridden by subclasses, not intended to be called
		pass

	def getImage(self):
		return self.imageContainer.image


class MapPlane(MapMosaic):
	def __init__(self, lowerX, upperX, lowerZ, upperZ, level) -> None:
		super().__init__(lowerX, upperX, lowerZ, upperZ, level)

	def makeBlank(self):
		return MapSquare.makeBlank()
	

class MapSquareOfZones(MapMosaic):
	# Squares composed of an 8x8 arrangement of Zones
	def __init__(self, level) -> None:
		maxZoneIndex = GCS.squareZoneLength - 1
		super().__init__(0, maxZoneIndex, 0, maxZoneIndex, level)

	def makeBlank(self):
		return MapZone.makeBlank()

	def getImage(self):
		return self.imageContainer.image


class MapSquare():
	# Class which contains the definition and image of a square
	def __init__(self, definition, sourcePlane) -> None:
		self.definition = definition
		self.imageContainer = None

		# The source plane is a per-tile thing, so should be saved here
		# The definition covers the full range of planes
		self.sourceLevel = sourcePlane

	def render(self):
		# Construct the tile path from the source data
		self.definition: SquareDefinition
		sourceX, sourceY = self.definition.getSourceSquare()
		baseTileName = (f"{CONFIG.mapid.baseTilePath}/"
				  		f"{self.sourceLevel}_{sourceX}_{sourceY}.png")
		baseTilePath = os.path.join(self.definition.basePath, baseTileName)
		self.imageContainer = SquareImage(baseTilePath)
		self.imageContainer.render()

	def getImage(self):
		return self.imageContainer.image
	
	@classmethod
	def makeBlank(cls):
		newSquare = cls(None, 0)
		newSquare.imageContainer = SquareImage(None)
		newSquare.imageContainer.render()
		return newSquare

	def __repr__(self) -> str:
		repr = (f"MapSquare: \n\t{self.definition}\n")
		return repr
	

class MapZone(MapSquare):
	# Class which contains the definition and image of a zone
	def __init__(self, definition, sourcePlane) -> None:
		super().__init__(definition, sourcePlane)

	def render(self):
		# Extract the sub-section of the source image
		definition = self.definition # type: ZoneDefinition
		sourceSquareX, sourceSquareZ = definition.getSourceSquare()
		sourceZoneX, sourceZoneZ = definition.getSourceZone()
		baseTileName = (f"{CONFIG.mapid.baseTilePath}/"
				  		f"{self.sourceLevel}_{sourceSquareX}_{sourceSquareZ}.png")
		baseTilePath = os.path.join(definition.basePath, baseTileName)
		self.imageContainer = ZoneImage(baseTilePath, sourceZoneX, sourceZoneZ)
		self.imageContainer.render()

	@classmethod
	def makeBlank(cls):
		newZone = cls(None, 0)
		newZone.imageContainer = ZoneImage(None, 0, 0)
		newZone.imageContainer.render()
		return newZone

	def __repr__(self) -> str:
		repr = (f"MapZone: \n\t{self.definition}")
		return repr

class MapIcon():
	def __init__(self, definition: IconDefinition, targetPlane) -> None:
		# Load in the data
		self.definition = definition
		self.targetPlane = targetPlane
		self.imageContainer = None # don't set for now
		self.displayX_tile = None
		self.displayZ_tile = None
		
		self.tilePosition = dict()
		self.positionInTile = dict()
		self.overflowsInto = dict()

	def setImage(self, image: IconImage):
		self.imageContainer = image
	
	def setDisplayCoordinates(self, x, z):
		self.displayX_tile = x
		self.displayZ_tile = z
		self.calculateRenderPosition(x, z)

	def calculateRenderPosition(self, x_tile, z_tile):
		# Calculates the tile and position in the tile the icon should be
		# placed in at each relevant zoom level. Also determines if there is
		# any overflowing of the icon image to be handled.

		# Start with the owner display square coordinates

		zoomLevelsWithIcons = [z for z, i in 
						 	   CONFIG.icon.zoomLevelHasIcons.items() if i]
		for zoomLevel in zoomLevelsWithIcons:
			# Calculate the leaflet tile coordinates for this zoom level
			scaleFactor = 2.0**zoomLevel/2.0**CONFIG.zoom.baselineZoomLevel
			scaleTileX = math.floor((x_tile * scaleFactor) // GCS.squareTileLength)
			scaleTileZ = math.floor((z_tile * scaleFactor) // GCS.squareTileLength)
			self.tilePosition[zoomLevel] = (scaleTileX, scaleTileZ)

			# Calculate the relative position of the icon in the tile
			# Start from bottom left (Jagex) coordinate origin
			x_px = x_tile * GCS.tilePixelLength
			z_px = z_tile * GCS.tilePixelLength
			# Rescale and find piel coordinates relative to the tile
			x_px = x_px * scaleFactor % 256
			z_px = z_px * scaleFactor % 256
			# Adjust to top left (pyvips) coordinate origin
			z_px = 256 - z_px - 1
			self.positionInTile[zoomLevel] = (x_px, z_px)

			# Check if the icon overflows into other tiles
			overflowDirs = list()
			iconSize_px = CONFIG.icon.iconSize
			leftOverflow = x_px - (iconSize_px//2) < 0
			topOverflow = z_px - (iconSize_px//2) < 0
			rightOverflow = x_px + (iconSize_px//2) > GCS.squarePixelLength
			bottomOverflow = z_px + (iconSize_px//2) > GCS.squarePixelLength
			# Relative y-values are top left origin (-ve means the tile above)
			# But the in-game tiles are bottom left (+ve means the tile above)
			# So "top overflow" means y+1, "right overflow" means x+1
			if leftOverflow: overflowDirs.append((-1, 0))
			if rightOverflow: overflowDirs.append((1, 0))
			if topOverflow: overflowDirs.append((0, 1))
			if bottomOverflow: overflowDirs.append((0, -1)) 
			if leftOverflow and topOverflow: overflowDirs.append((-1, 1))
			if leftOverflow and bottomOverflow: overflowDirs.append((-1, -1))
			if rightOverflow and topOverflow: overflowDirs.append((1, 1))
			if rightOverflow and bottomOverflow: overflowDirs.append((1, -1))
			# Calculate the destination tile coordinates
			overflowTiles = list()
			for overflowDirection in overflowDirs:
				overflowTiles.append((overflowDirection[0]+scaleTileX, 
						 			  overflowDirection[1]+scaleTileZ))
			# Store the overflow tiles into another dict
			self.overflowsInto[zoomLevel] = overflowTiles

	def __repr__(self) -> str:
		repr = (f"MapIcon@{self.targetPlane}: {self.definition}")
		return repr