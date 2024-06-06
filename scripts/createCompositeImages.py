import os.path
from platform import system
import math
import json

# Detect whether the script is being run on Windows or Linux
runnerOS = system()
if runnerOS == "Windows":
	# Pyvips on windows is finnicky
	# Windows binaries are required: https://pypi.org/project/pyvips/, https://www.libvips.org/install.html
	LIBVIPS_VERSION = "8.15"
	vipsbin = os.path.join(os.getcwd(), f"vipsbin/vips-dev-{LIBVIPS_VERSION}/bin")
	os.environ['PATH'] = os.pathsep.join((vipsbin, os.environ['PATH']))
import pyvips as pv


def styleLayer(layerImage, brightnessFrac, contrastFrac, grayscaleFrac, blurRadius):
	# Brightness and contrast
	# This is done via a linear equation out = contrast * in + brightness
	brightnessValue = ((brightnessFrac * 255) - 255) / 2
	layerImage = contrastFrac * (layerImage - 127) + (127 + brightnessValue)

	# Grayscale
	if 0 < grayscaleFrac <= 1:
		# Convert to .hsv, adjust the saturation band, and convert back to srgb
		layerImage = (layerImage.colourspace("hsv") * [1, (1-grayscaleFrac), 1]).colourspace("srgb")

	# Color Palette
	# Seems unpopular, but would be sepia, etc

	# Dropshadow
	# Seems unpopular, looks nice in some areas of the map

	# Blur
	# Preview the radius of this blur operation using:
	# print(pv.Image.gaussmat(sigma, min_ampl, precision="float", separable=True).rot90().numpy())
	# pyvips implementation skips the first term of the Gaussian: https://www.libvips.org/API/8.9/libvips-create.html#vips-gaussmat
	if blurRadius > 0:
		sigma = 1
		n = blurRadius + 1 
		nthGaussTerm = math.e ** ((-n**2)/(2 * (sigma**2)))
		layerImage = layerImage.gaussblur(sigma, min_ampl=nthGaussTerm, precision="float")

	return layerImage


def createComposites(planeNum, planePathDict):
	"""
		Intended to be called as part of the map tile generation automation
		Currently relies on the default values found in mapBuilderConfig.json
		
		05/29/24 Defaults
		
		- transparencyColor = 0
			- The color of pixels to be ignored in overlay images
		- transparencyTolerance = 0
			- The amount of difference allowed, per band, between a pixel's value and the transparency
			- A pixel is ignored if abs(overlayPixel - transparencyColor) > transparencyTolerance in all bands
		- brightNessFraction = 1.0
			- Brightness factor between 0.0 and 2.0, inclusive
			- Scaled such that a value of 1.0 has no impact, 0.0 results in black, 2.0 results in white
		- contrastFraction = 1.0
			- Contrast factor between 0.0 and 2.0, inclusive
			- Scaled such that a value of 1.0 has no impact, 0.0 results in all gray
		- grayscaleFraction = 0.0
			- Saturation factor between 0.0 and 1.0, right inclusive
			- Adjusts the saturation band of the image after conversion to hsv color model
			- 0.0 would have no effect, 1.0 is equivalent to conversion to black and white
		- blurRadius = 1
			- Radius in pixels of a Gaussian blur on the image
			- This is used to reverse-calculate the amplitude cutoff values of the blur assuming a sigma value of 1
			- A radius of zero means no blur takes place, large radii increase processing time
	"""
	# Use default config values found in mapBuilderConfig.py
	with open("./scripts/mapBuilderConfig.json") as configFile:
		configOpts = json.load(configFile)["COMPOSITE_OPTS"]
	
	transparencyColor = configOpts["transparencyColor"]
	transparencyTolerance = configOpts["transparencyTolerance"]
	brightNessFraction = configOpts["brightNessFraction"]
	contrastFraction = configOpts["contrastFraction"]
	grayscaleFraction = configOpts["grayscaleFraction"]
	blurRadius = configOpts["blurRadius"]
	underlayStyleOpts = [brightNessFraction, contrastFraction, grayscaleFraction, blurRadius]

	# For all planes beneath the planeNum, create a stacked composite
	# Load the base images
	baseImage = pv.Image.new_from_file(planePathDict[0])

	# Composite all the planes beneath this one
	if planeNum > 0:
		underlayPlanes = list()
		print(f"Merging 0-{planeNum}")
		for underlayID in range(0, planeNum):
			underlayPlanes.append(pv.Image.new_from_file(planePathDict[underlayID]))
		baseImage = createUnderlay(underlayPlanes, transparencyColor, transparencyTolerance, underlayStyleOpts)

		# Then style the result
		styledBaseImage = styleLayer(baseImage, *underlayStyleOpts)

		# Load in the next plane
		overlayImage = pv.Image.new_from_file(planePathDict[planeNum])

		# Create a mask treating non-background pixels as 255 from the overlay
		mask = (abs(overlayImage - transparencyColor) > transparencyTolerance).bandor()

		# Insert overlay pixels where the mask is true, and base pixels where false
		baseImage = mask.ifthenelse(overlayImage, styledBaseImage)

	return baseImage


def createUnderlay(underlayImages, transparencyColor, transparencyTolerance, underlayStyleOpts):
	# Creates an underlay image from the list of supplied images
	baseImage = underlayImages[0]
	if len(underlayImages) > 0:
		for image in underlayImages[1:]:
			mask = (abs(image - transparencyColor) > transparencyTolerance).bandor()
			baseImage = mask.ifthenelse(image, baseImage)
	return baseImage