# Imports only for type hints
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from buildMapIDs import MapBuilder
	
# Necessary class imports
from definitions import (SquareDefinition, ZoneDefinition, IconDefinition)
from images import MapImage, PlaneImage, SquareImage, ZoneImage, IconImage
from mapelements import (MapPlane, MapSquare, MapZone, MapIcon, MapMosaic,
                        MapSquareOfZones)
from config import MapBuilderConfig, GlobalCoordinateDefinition
CONFIG = MapBuilderConfig()
GCS = GlobalCoordinateDefinition()

# Functional imports
import math
import os
import glob
from collections import defaultdict
from copy import deepcopy


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
		self.rangeImage()
		self.sortDefinitions()
		self.buildReferences(self.squareDefs, self.zoneDefs)
	
	def rangeImage(self) -> None:
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
	
	def sortDefinitions(self) -> None:
		self.squareDefs.sort()
		self.zoneDefs.sort()

	def buildReferences(self, squareDefs: list[SquareDefinition],
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
	
	def getBounds(self):
		lowerLeftBound = [
			(self.lowerSquareX - 1) * GCS.squareTileLength,
			(self.lowerSquareZ - 1) * GCS.squareTileLength
		]
		upperRightBound = [
			(self.upperSquareX + 2) * GCS.squareTileLength,
			(self.upperSquareZ + 2) * GCS.squareTileLength
		]
		return [lowerLeftBound, upperRightBound]
	
	def getCenter(self):
		center = [
			(self.lowerSquareX + self.upperSquareX + 1) * 32,
			(self.lowerSquareZ + self.upperSquareZ + 1) * 32
		]
		return center


class MapIconManager:
	# Holds definitions for icons
	# Holds a square-coordinate indexable map, a list of all icons in the square
	def __init__(self, iconDefs: list[IconDefinition], basePath) -> None:
		# Sort the icon defs and save
		self.iconDefs = iconDefs

		# Manager loads its own icons for reference
		self.basePath = basePath
		
		# Filter out icons not in the definitions
		self.sortDefinitions()
		self.loadIconImages()
		self.processIconList()

	def sortDefinitions(self):
		def iconSortKey(icon: IconDefinition) -> int:
			# Uses the same RuneLite hash/key to sort icons
			level = icon.plane
			x, z = icon.getTileRelativeToOwnerSquare()
			return (level << 28 | x << 14 | z) * -1

		self.iconDefs.sort(key=iconSortKey)

	def loadIconImages(self):
		# Load all the icon images into referenceable memory
		self.iconIDtoImage = dict()
		iconImageDir = os.path.join(self.basePath, CONFIG.icon.iconPath)
		iconImagePaths = glob.iglob(os.path.join(iconImageDir, "*.png"))
		for iconImagePath in iconImagePaths:
			iconID = int(os.path.basename(iconImagePath).split(".")[0])
			iconImageContainer = IconImage(iconImagePath)
			self.iconIDtoImage[iconID] = iconImageContainer

	def processIconList(self):
		# Store icons to be accessed via owner coordinates
		self.iconStore = defaultdict(lambda: # [plane]
						 defaultdict(lambda: # [square]
						 defaultdict(list))) # [zone]
		for iconDef in self.iconDefs:
			plane = iconDef.plane
			sqX, sqZ = iconDef.getOwnerSquare()
			znX, znZ = iconDef.getOwnerZone()
			self.iconStore[plane][(sqX, sqZ)][(znX, znZ)].append(iconDef)

	def getIconsInID(self, mapBuilder: 'MapBuilder'):
		# Return dict with plane numbers as keys, mapped to icons in plane
		renderedIcons = defaultdict(list)

		# Using the structure of the ID determined by the builder, find
		# all icons that should be represented in each defined map element
		for plane in range(mapBuilder.lowerPlane, mapBuilder.upperPlane+1):
			# For each plane, evaluate the elements in the plane
			targetPlane = mapBuilder.planes[plane] # type: MapPlane
			for square, element in targetPlane.mosaic.items():
				if isinstance(element, MapSquareOfZones):
					# Another layer of mosaic needs to be parsed
					for zone, subelem in element.mosaic.items():
						newIconList = self.getIconsInCell(plane, subelem, mapBuilder.mapID)
						renderedIcons[plane].extend(newIconList)
				elif isinstance(element, MapSquare):
					newIconList = self.getIconsInCell(plane, element, mapBuilder.mapID)
					renderedIcons[plane].extend(newIconList)
		return renderedIcons

	def getIconsInCell(self, plane, cellContent: MapSquare | MapSquareOfZones, mapID):
		# If there is no definition, we do not render anything
		cellDefinition = cellContent.definition
		icons = defaultdict(list)
		if not cellDefinition:
			return icons

		# Cover the whole plane range, finding all icons from the same region
		for defPlane in range(0, 4):
			sourceCoords = cellDefinition.getFullSource()
			iconsInCell = self.getIconsInDef(defPlane, *sourceCoords)
			for icon in iconsInCell:
				newIcon = self.createMapIcon(defPlane, icon, cellDefinition)
				icons[defPlane].append(newIcon)

		# Only return the list of icons that are rendered in this cell's plane
		outList = list()
		for planeNum, iconList in icons.items():
			# Some mapIDs have overrides
			mapIDOverride = CONFIG.icon.defsWithIconsFromOtherPlanes
			if mapID in mapIDOverride.keys() and planeNum in mapIDOverride[mapID][plane]:
				outList.extend(iconList)
			elif planeNum in CONFIG.icon.planeHasIconsFromPlanes[plane]:
				outList.extend(iconList)
		return outList

	def getIconsInDef(self, plane, squareX, squareZ, 
				   	  zoneX=None, zoneZ=None):
		# Search the iconStore for icons that fall within the square and zone
		# Not supplying zone coordinates means the whole square is checked
		iconList = list()

		# Access the datastructure for the specified square
		squareData = self.iconStore[plane][(squareX, squareZ)]
		if zoneX is None and zoneZ is None:
			# If no zone was specified, then flatten the data
			sqL = [icon for icons in squareData.values() for icon in icons]
			iconList.extend(sqL)
		else:
			# Otherwise, only append the icons in the zone
			iconList.extend(squareData[(zoneX, zoneZ)])
		return iconList

	def createMapIcon(self, planeNum, iconDefinition: IconDefinition, 
				   	  mapDefinition: SquareDefinition | ZoneDefinition):
		# Create the map element of the icon, with image and icondef loaded
		# Use the map definition to set the display coordinates

		# Create the MapIcon instance, based on the icon definition
		newIcon = MapIcon(iconDefinition, planeNum)

		# Set the icon's image, which was pre-loaded earlier
		spriteID = iconDefinition.spriteID
		iconSprite = self.iconIDtoImage[spriteID]
		newIcon.setImage(iconSprite)

		# Set the icon's display coordinates
		# Need to determine how the icon is being moved by the definition
		# This must be done relative to the lower left of the square,
		# or zone, if it is mentioned in the definition
		if isinstance(mapDefinition, ZoneDefinition):
			# For zones, find the zone-relative position of the icon
			znRelX, znRelZ = iconDefinition.getTileRelativeToOwnerZone()
			# Then find the base point of the display zone
			dsqX, dsqZ = mapDefinition.getDisplaySquare()
			dznX, dznZ = mapDefinition.getDisplayZone()
			baseX = dsqX * GCS.squareTileLength + dznX * GCS.zoneTileLength
			baseZ = dsqZ * GCS.squareTileLength + dznZ * GCS.zoneTileLength
			# Final location is the relative position added to the base point
			dX_tile = baseX + znRelX
			dZ_tile = baseZ + znRelZ
		else:
			# Squares are simpler, just get the square-relative coordinates
			sqRelX, sqRelZ = iconDefinition.getTileRelativeToOwnerSquare()
			# And add them to the base point of the display square
			dsqX, dsqZ = mapDefinition.getDisplaySquare()
			dX_tile = dsqX * GCS.squareTileLength + sqRelX
			dZ_tile = dsqZ * GCS.squareTileLength + sqRelZ
		# The baseline display coordinates can now be set
		newIcon.setDisplayCoordinates(dX_tile, dZ_tile)
		return newIcon
