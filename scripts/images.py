from dataclasses import dataclass, field
import os
from config import MapBuilderConfig, GlobalCoordinateDefinition
CONFIG = MapBuilderConfig()
GCS = GlobalCoordinateDefinition()

### Pyvips import
# Windows binaries are required: 
# https://pypi.org/project/pyvips/
# https://www.libvips.org/install.html
LIBVIPS_VERSION = "8.15"
vipsbin = os.path.join(os.getcwd(), f"vipsbin/vips-dev-{LIBVIPS_VERSION}/bin")
os.environ['PATH'] = os.pathsep.join((vipsbin, os.environ['PATH']))
# os.environ['VIPS_PROFILE'] = "1"
import pyvips as pv


class MapImage():
	"""
	Base class for images used in the map creation process
	"""
	def __init__(self, sourcePath) -> None:
		self.sourcePath = str(sourcePath) # paths must be strings
		self.image = None

	def createBlankImage(self, width, height, bands):
		return pv.Image.black(width, height, 
							  bands=bands).copy(interpretation="srgb")
	
	def setImage(self, image):
		self.image = image

	def getMask(self):
		color = CONFIG.composite.transparencyColor
		tolerance = CONFIG.composite.transparencyTolerance
		return (abs(self.image - color) > tolerance).bandor()
	
	def overlayImage(self, baseImage):
		mask = self.getMask()
		return mask.ifthenelse(self.image, baseImage)
	
	def writeImageToFile(self, name):
		self.image.write_to_file(name)

	# Methods for general image processing go here


class PlaneImage(MapImage):
	# Plane images are used for processing composites and styling
	def __init__(self, image) -> None:
		super().__init__(None)
		self.image = image

	# def loadImage(self):
	#     # Plane images are assembled from sub images
	#     pass


class SquareImage(MapImage):
	def __init__(self, sourcePath) -> None:
		super().__init__(sourcePath)

	def render(self):
		# Load the image in from file
		px = GCS.squarePixelLength
		if os.path.exists(self.sourcePath):
			self.image = pv.Image.new_from_file(self.sourcePath)
		else:
			self.image = self.createBlankImage(px, px, 3)

		# Add any other image manipulations here

	def __repr__(self) -> str:
		return f"SquareImage: {self.image}"


class ZoneImage(MapImage):
	def __init__(self, sourcePath, x, z) -> None:
		super().__init__(sourcePath)
		self.sourceZoneX = x
		self.sourceZoneZ = z

	def render(self):
		# Load the source image from file and crop out the zone
		px = GCS.zonePixelLength
		zones = GCS.squareZoneLength
		if os.path.exists(self.sourcePath):
			sourceImage = pv.Image.new_from_file(self.sourcePath)
			# Convert coordinates from bottom left to top left
			x = (self.sourceZoneX) * px
			z = (zones - self.sourceZoneZ - 1) * px
			self.image = sourceImage.crop(x, z, px, px)
		else:
			self.image = self.createBlankImage(px, px, 3)
			
		# Add any other image manipulations here

	def __repr__(self) -> str:
		return f"ZoneImage: {self.image}"

class IconImage(MapImage):
	def __init__(self, sourcePath) -> None:
		super().__init__(sourcePath)
		# Load the image immediately for repeated referencing
		self.image = pv.Image.new_from_file(sourcePath)