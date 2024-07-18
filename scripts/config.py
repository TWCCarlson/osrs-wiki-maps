from dataclasses import dataclass
import json


class Singleton(type):
	_instances = {}
	def __call__(cls, *args, **kwargs):
		if cls not in cls._instances:
			# If there are no init arguments, ignore the call
			if not args and not kwargs:
				return None
			cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
		return cls._instances[cls]


class MapBuilderConfig(metaclass=Singleton):
	"""
	A singleton made available to the entire map builder workspace
	Using a metaclass ensures there will only ever be one instance
	"""
	@dataclass
	class CompositeConfig(metaclass=Singleton):
		transparencyColor: int | list
		transparencyTolerance: int | list
		brightnessFraction: float
		contrastFraction: float
		grayscaleFraction: float
		blurRadius: int
		sourcePath: str
		outPath: str

	@dataclass
	class ZoomConfig(metaclass=Singleton):
		zoomLevels: dict
		baselineZoomLevel: int
		kernels: dict
		sourcePath: str
		outPath: str

		def __post_init__(self):
			# Extract min and max zoom levels for ease of reference
			self.minZoom = self.zoomLevels["min"]
			self.maxZoom = self.zoomLevels["max"]

			# Adjust str keys to ints for ease of use
			self.kernels = {int(k):v for k,v in self.kernels.items()}

	@dataclass
	class IconConfig(metaclass=Singleton):
		mapIDDirectory: str
		iconPath: str
		iconDefs: str
		zoomLevelHasIcons: dict
		planePath: str
		outPath: str
		planeHasIconsFromPlanes: dict
		iconSize: int

		def __post_init__(self):
			# Adjust str keys to ints for ease of use
			self.zoomLevelHasIcons = {int(k):v for k,v in 
									  self.zoomLevelHasIcons.items()}
			self.planeHasIconsFromPlanes = {int(k):v for k,v in
								   	  		self.planeHasIconsFromPlanes.items()}

	@dataclass
	class TilerConfig(metaclass=Singleton):
		backgroundColor: int | list
		backgroundThreshold: int | list
		layerPath: str
		outPath: str
		baselineZoomLevel: int
		imagePath: str

	@dataclass
	class DirConfig(metaclass=Singleton):
		multiprocessingEnabled: bool
		dzPath: str
		outPath: str
		baselineZoomLevel: int

	@dataclass
	class MapIDConfig(metaclass=Singleton):
		baseTilePath: str
		mapIDoutPath: str
		squareDefsPath: str
		zoneDefsPath: str
		mapDefsPath: str
		userMapDefsPath: str
		basemapsPath: str

	def __init__(self, composite: CompositeConfig, zoom: ZoomConfig, 
				 tiler: TilerConfig, dir: DirConfig, 
				 icon: IconConfig, mapid: MapIDConfig) -> None:
		self.composite = composite
		self.zoom = zoom
		self.tiler = tiler
		self.directory = dir
		self.icon = icon
		self.mapid = mapid

	@classmethod
	def fromJSON(cls, jsonFilePath):
		with open(jsonFilePath) as jsonFile:
			jsonData = json.load(jsonFile) # type: dict

		compositeOpts = jsonData.get("COMPOSITE_OPTS")
		compositeConfig = cls.CompositeConfig(**compositeOpts)
		zoomOpts = jsonData.get("ZOOM_OPTS")
		zoomConfig = cls.ZoomConfig(**zoomOpts)
		tilerOpts = jsonData.get("TILER_OPTS")
		tilerConfig = cls.TilerConfig(**tilerOpts)
		dirOpts = jsonData.get("DIR_OPTS")
		dirConfig = cls.DirConfig(**dirOpts)
		iconOpts = jsonData.get("ICON_OPTS")
		iconConfig = cls.IconConfig(**iconOpts)
		mapidOpts = jsonData.get("MAPID_OPTS")
		mapidConfig = cls.MapIDConfig(**mapidOpts)

		new = cls(compositeConfig, zoomConfig, tilerConfig, 
				  dirConfig, iconConfig, mapidConfig)

		return new
	

# Alternative approach I'm not sure about
# def loadBuilderConfig(path):
#     with open(path) as jsonFile:
#         jsonData = json.load(jsonFile) # type: dict
	
#     compositeOpts = jsonData.get("COMPOSITE_OPTS")
#     for name, value in compositeOpts.items():
#         setattr(MapBuilderConfig.CompositeConfig, name, value)

#     zoomOpts = jsonData.get("ZOOM_OPTS")
#     for name, value in zoomOpts.items():
#         setattr(MapBuilderConfig.ZoomConfig, name, value)
	
#     tilerOpts = jsonData.get("TILER_OPTS")
#     for name, value in tilerOpts.items():
#         setattr(MapBuilderConfig.TilerConfig, name, value)
	
#     dirOpts = jsonData.get("DIR_OPTS")
#     for name, value in dirOpts.items():
#         setattr(MapBuilderConfig.DirConfig, name, value)
	
#     iconOpts = jsonData.get("ICON_OPTS")
#     for name, value in iconOpts.items():
#         setattr(MapBuilderConfig.IconConfig, name, value)
	
#     mapidOpts = jsonData.get("MAPID_OPTS")
#     for name, value in mapidOpts.items():
#         setattr(MapBuilderConfig.MapIDConfig, name, value)


@dataclass
class GlobalCoordinateDefinition(metaclass=Singleton):
	"""
	Holds reference values for the complete map source material
	"""
	maxX_square: int
	maxY_sqaure: int
	minX_square: int
	minY_square: int
	maxX_tile: int
	maxY_tile: int
	minX_tile: int
	minY_tile: int
	squareZoneLength: int
	squareTileLength: int
	squarePixelLength: int
	zoneTileLength: int
	zonePixelLength: int
	tilePixelLength: int

	@classmethod
	def fromJSON(cls, jsonFilePath):
		with open(jsonFilePath) as jsonFile:
			jsonData = json.load(jsonFile) # type: dict

		# Fetch all values
		maxX_square = jsonData.get("maxSquareX")
		maxY_sqaure = jsonData.get("maxSquareY")
		minX_square = jsonData.get("minSquareX")
		minY_square = jsonData.get("minSquareY")
		maxX_tile = jsonData.get("maxTileX")
		maxY_tile = jsonData.get("maxTileY")
		minX_tile = jsonData.get("minTileX")
		minY_tile = jsonData.get("minTileY")
		squareZoneLength = jsonData.get("squareZoneLength")
		squareTileLength = jsonData.get("squareTileLength")
		squarePixelLength = jsonData.get("squarePixelLength")
		zoneTileLength = jsonData.get("zoneTileLength")
		zonePixelLength = jsonData.get("zonePixelLength")
		tilePixelLength = jsonData.get("tilePixelLength")

		# Create the new instance
		newGCS = cls(maxX_square, maxY_sqaure, minX_square, minY_square,
			   		 maxX_tile, maxY_tile, minX_tile, minY_tile,
					 squareZoneLength, squareTileLength, squarePixelLength,
					 zoneTileLength, zonePixelLength,
					 tilePixelLength)
		return newGCS	