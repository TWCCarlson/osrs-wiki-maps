from dataclasses import dataclass, field
import json
from config import MapBuilderConfig, GlobalCoordinateDefinition
CONFIG = MapBuilderConfig()
GCS = GlobalCoordinateDefinition()


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
	def squareDefsFromJSON(cls, jsonFilePath, basePath):
		with open(jsonFilePath) as jsonFile:
			jsonData = json.load(jsonFile)

		# Return a list of all the new ZoneDefinitions
		zoneList = list()
		for data in jsonData:
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
			zoneList.append(newSquare)
		return zoneList
	
	def getSourceSquare(self) -> tuple:
		return (self.sourceSquareX, self.sourceSquareZ)

	def getDisplaySquare(self) -> tuple:
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
	def zoneDefsFromJSON(cls, jsonFilePath, basePath):
		with open(jsonFilePath) as jsonFile:
			jsonData = json.load(jsonFile)

		# Return a list of all the new ZoneDefinitions
		zoneList = list()
		for data in jsonData:
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

	# def __post_init__(self):
	# 	# Calculate the owning square and icon's relative position to it
	# 	self.x_square = self.x_tile // GCS.squareTileLength
	# 	self.z_square = self.z_tile // GCS.squareTileLength

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