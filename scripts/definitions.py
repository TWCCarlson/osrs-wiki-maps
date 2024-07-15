from config import MapBuilderConfig, GlobalCoordinateDefinition
CONFIG = MapBuilderConfig()
GCS = GlobalCoordinateDefinition()

from dataclasses import dataclass, field
import json


def loadMapDefinitions(mapID, mapDefs, basePath):
	# Reads the map definitions and extracts the square and zone definitions
	# for the supplied mapID, returning the list of definition objects
	mapIDDefs = mapDefs[mapID]
	squareDefsJSON = mapIDDefs.get("mapSquareDefinitions")
	zoneDefsJSON = mapIDDefs.get("zoneDefinitions")
	squareDefs = SquareDefinition.squareDefsFromJSON(squareDefsJSON, basePath)
	zoneDefs = ZoneDefinition.zoneDefsFromJSON(zoneDefsJSON, basePath)
	return squareDefs, zoneDefs


@dataclass(order=True)
class SquareDefinition:
	groupId: int
	sourceSquareX: int = field(compare=False)
	sourceSquareZ: int = field(compare=False)
	displaySquareX: int = field(compare=False)
	displaySquareZ: int = field(compare=False)
	minLevel: int = field(compare=False)
	levels: int = field(compare=False)
	fileId: int = field(compare=False)
	basePath: str = field(compare=False)
	# Post init vals
	lowerPlane: int = field(init=False, compare=False)
	upperPlane: int = field(init=False, compare=False)

	def __post_init__(self) -> None:
		# Calculate lower and upper planes for ease of reference
		self.lowerPlane = self.minLevel
		self.upperPlane = self.minLevel + self.levels - 1

	@classmethod
	def squareDefsFromJSON(cls, squareDefsList, basePath):
		# Parse the passed list, generating square definition objects
		squareList = list()
		# If there are no square definitions, skip 
		if not squareDefsList:
			return squareList
		
		for data in squareDefsList:
			# Get definition data
			minLevel = data.get("minLevel")
			levels = data.get("levels")
			sourceSquareX = data.get("sourceSquareX")
			sourceSquareZ = data.get("sourceSquareZ")
			displaySquareX = data.get("displaySquareX")
			displaySquareZ = data.get("displaySquareZ")
			groupID = data.get("groupId")
			fileID = data.get("fileId")

			# Create new instance
			newSquare = cls(groupID,
							sourceSquareX, sourceSquareZ, 
							displaySquareX, displaySquareZ,
							minLevel, levels,
							fileID, basePath
				 		)
			squareList.append(newSquare)
		return squareList
	
	@classmethod
	def spoofAllSquareDefs(cls, basePath):
		# Creates all definitions spanning the plane, where source = display
		squareList = list()
		# Always assumes all 4 levels are used
		# GroupID matches the level
		minLevel = 0
		levels = 4
		fileID = None
		groupID = 0
		for x in range(GCS.minX_square, GCS.maxX_square+1):
			for z in range(GCS.minY_square, GCS.maxY_sqaure+1):
				sourceSquareX = x
				sourceSquareZ = z
				displaySquareX = x
				displaySquareZ = z
				newSquare = cls(groupID,
								sourceSquareX, sourceSquareZ, 
								displaySquareX, displaySquareZ,
								minLevel, levels,
								fileID, basePath
				 			)
				squareList.append(newSquare)
		return squareList
	
	def getSourceSquare(self) -> tuple:
		return (self.sourceSquareX, self.sourceSquareZ)

	def getDisplaySquare(self) -> tuple:
		return (self.displaySquareX, self.displaySquareZ)
	
	def getFullSource(self) -> tuple:
		return (self.sourceSquareX, self.sourceSquareZ)
	
	def getFullDisplay(self) -> tuple:
		return (self.displaySquareX, self.displaySquareZ)
	
	def getPlaneRange(self) -> tuple:
		return (self.lowerPlane, self.upperPlane)

	def __repr__(self) -> str:
		repr = (f"SquareDef: Source[{self.sourceSquareX}, {self.sourceSquareZ}]"
				f"-> Display[{self.displaySquareX}, {self.displaySquareZ}]")
		return repr


@dataclass(order=True)
class ZoneDefinition(SquareDefinition):
	# Specifies a subset of a mapSquare, 32 x 32px
	sourceZoneX: int = field(compare=False)
	sourceZoneZ: int = field(compare=False)
	displayZoneX: int = field(compare=False)
	displayZoneZ: int = field(compare=False)

	@classmethod
	def zoneDefsFromJSON(cls, zoneDefsList, basePath):
		# Parse the passed list, generating zone definition objects
		zoneList = list()
		# If there are no zones, skip
		if not zoneDefsList:
			return zoneList
		
		for data in zoneDefsList:
			# Get definition data
			sourceZoneX = data.get("sourceZoneX")
			sourceZoneZ = data.get("sourceZoneZ")
			displayZoneX = data.get("displayZoneX")
			displayZoneZ = data.get("displayZoneZ")
			minLevel = data.get("minLevel")
			levels = data.get("levels")
			sourceSquareX = data.get("sourceSquareX")
			sourceSquareZ = data.get("sourceSquareZ")
			displaySquareX = data.get("displaySquareX")
			displaySquareZ = data.get("displaySquareZ")
			groupID = data.get("groupId")
			fileID = data.get("fileId")

			# Create new instance
			newZone = cls(groupID,
						  sourceSquareX, sourceSquareZ, 
						  displaySquareX, displaySquareZ,
						  minLevel, levels,
						  fileID, basePath,
				 		  sourceZoneX, sourceZoneZ,
						  displayZoneX, displayZoneZ
				 		)
			zoneList.append(newZone)
		return zoneList

	def getSourceZone(self) -> tuple:
		return (self.sourceZoneX, self.sourceZoneZ)

	def getDisplayZone(self) -> tuple:
		return (self.displayZoneX, self.displayZoneZ)
	
	def getFullSource(self) -> tuple:
		return (self.sourceSquareX, self.sourceSquareZ, 
		  		self.sourceZoneX, self.sourceZoneZ)
	
	def getFullDisplay(self) -> tuple:
		return (self.displaySquareX, self.displaySquareZ,
		  		self.displayZoneX, self.displayZoneZ)

	def __repr__(self) -> str:
		repr = (f"ZoneDef: Source[{self.sourceSquareX}, {self.sourceSquareZ}]"
				f"{self.sourceZoneX, self.sourceZoneZ} -> "
				f"Display[{self.displaySquareX}, {self.displaySquareZ}]"
				f"{self.displayZoneX, self.displayZoneZ}")
		return repr


@dataclass(order=True)
class IconDefinition:
	iconIndex: int
	x_tile: int = field(compare=False)
	z_tile: int = field(compare=False)
	plane: int = field(compare=False)
	spriteID: int = field(compare=False)
	# Post-init values
	x_square: int = field(init=False, compare=False)
	z_square: int = field(init=False, compare=False)
	x_zone: int = field(init=False, compare=False)
	z_zone: int = field(init=False, compare=False)

	def getOwnerSquare(self):
		# Return coordinates relative to the lower left of the square
		sqX = self.x_tile // GCS.squareTileLength
		sqZ = self.z_tile // GCS.squareTileLength
		return (sqX, sqZ)
	
	def getTileRelativeToOwnerSquare(self):
		relX = self.x_tile % GCS.squareTileLength
		relZ = self.z_tile % GCS.squareTileLength
		return (relX, relZ)
	
	def getOwnerZone(self):
		# Return coordinates relative to the lower left of the zone
		znX = self.x_tile % GCS.squareTileLength // GCS.zoneTileLength
		znZ = self.z_tile % GCS.squareTileLength // GCS.zoneTileLength
		return (znX, znZ)
	
	def getTileRelativeToOwnerZone(self):
		relX = self.x_tile % GCS.zoneTileLength
		relZ = self.z_tile % GCS.zoneTileLength
		return (relX, relZ)
	
	def getOwnerTile(self):
		# Return the tile coordinates of the icon
		return (self.x_tile, self.z_tile)

	@classmethod
	def iconDefsFromJSON(cls, jsonFilePath):
		with open(jsonFilePath) as jsonFile:
			jsonData = json.load(jsonFile)

		# Return a list of all the new IconDefinitions
		iconList = list()
		iconIndex = 0
		for data in jsonData:
			# Get definition data
			positionData = data.get("position")			
			x_tile = positionData.get("x")
			z_tile = positionData.get("y")
			plane = positionData.get("z")
			spriteID = data.get("spriteId")

			# Create new instance
			newIcon = cls(iconIndex, x_tile, z_tile, plane, spriteID)
			iconList.append(newIcon)
			iconIndex += 1
		return iconList

	def __repr__(self) -> str:
		repr = (f"IconDef: {self.spriteID}@"
		  		f"[{self.plane, self.x_tile, self.z_tile}]")
		return repr