from config import MapBuilderConfig, GlobalCoordinateDefinition
CONFIG = MapBuilderConfig()
GCS = GlobalCoordinateDefinition()

import os
import math

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
		return pv.Image.black(width, height, bands=bands).copy(interpretation="srgb")
	
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

	### Generic image processing
	@staticmethod
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

	@staticmethod
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

	@staticmethod
	def blur(image):
		# Preview the radius of this blur operation using:
		# print(pv.Image.gaussmat(sigma, min_ampl, precision="float", separable=True).rot90().numpy())
		# pyvips implementation skips the first term of the Gaussian: 
		# https://www.libvips.org/API/8.9/libvips-create.html#vips-gaussmat
		blurRadius = CONFIG.composite.blurRadius
		if blurRadius > 0:
			# This approach calculates the amplitude cutoff for passed radius
			sigma = 1
			n = blurRadius + 1
			nthGaussTerm = math.e ** (-(n**2)/(2 * (sigma**2)))
			return image.gaussblur(sigma, min_ampl=nthGaussTerm, precision="float")
		return image


class PlaneImage(MapImage):
	# Plane images are used for processing composites and styling
	def __init__(self, image) -> None:
		super().__init__(None)
		self.image = image


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

	def __repr__(self) -> str:
		return f"ZoneImage: {self.image}"

class IconImage(MapImage):
	def __init__(self, sourcePath) -> None:
		super().__init__(sourcePath)
		# Load the image immediately for repeated referencing
		self.image = pv.Image.new_from_file(sourcePath)