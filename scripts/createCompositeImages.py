import os.path
from platform import system
from collections import defaultdict
from glob import glob
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
	brightnessValue = ((brightnessFrac * 255) - 255) / 2
	# contrastValue = ((contrastFraction * 255) - 255) / 2
	# contrastCorrection = (259 * (contrastValue + 255)) / (255 * (259 - contrastValue))
	layerImage = contrastFrac * (layerImage - 127) + (127 + brightnessValue)

	# Grayscale
	if 0 < grayscaleFrac <= 1:
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


def createComposites(sourcePath, outPath, transparencyColor, transparencyTolerance, styleOptions):
	# Locate plane images
	planeImagePaths = [os.path.normpath(path) for path in glob(os.path.join(sourcePath, "*.png"))]
	# raise error if plane images not found in directory

	# Load images, ensuring the right order
	planeDict = defaultdict(pv.Image)
	for planeImagePath in planeImagePaths:
		imageName = os.path.splitext(os.path.basename(planeImagePath))[0]
		planeNum = int(imageName.split("_")[-1])
		planeImage = pv.Image.new_from_file(planeImagePath)
		planeDict[planeNum] = planeImage
	
	# Initialize with the base plane
	baseImage = planeDict[0]
	baseImage.write_to_file(os.path.join(outPath, f"plane_0.png"))

	# Stack the other layers on top of it
	for planeNum in range(0, len(planeImagePaths)):
		# Style the underlay plane
		styledBaseImage = styleLayer(baseImage, *styleOptions)
		if planeNum == 0:
			# There is nothing to overlay on the base plane
			continue

		# Get the overlay plane
		overlayImage = planeDict[planeNum]

		# Create a mask treating non-background pixels as 255 from the overlay
		mask = (abs(overlayImage - transparencyColor) > transparencyTolerance).bandor()

		# Insert overlay pixels where the mask is true, and base pixels where false
		styledCompositeImage = mask.ifthenelse(overlayImage, styledBaseImage)
		styledCompositeImage.write_to_file(os.path.join(outPath, f"plane_{planeNum}.png"))

		# Separately, merge the overlay with the not-styled underlay to become the underlay for the next plane
		baseImage = mask.ifthenelse(overlayImage, baseImage)


def actionRoutine(basePath):
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
	# Use default values found in mapBuilderConfig.py
	with open("./scripts/mapBuilderConfig.json") as configFile:
		configOpts = json.load(configFile)["COMPOSITE_OPTS"]
	
	transparencyColor = configOpts["transparencyColor"]
	transparencyTolerance = configOpts["transparencyTolerance"]
	brightNessFraction = configOpts["brightNessFraction"]
	contrastFraction = configOpts["contrastFraction"]
	grayscaleFraction = configOpts["grayscaleFraction"]
	blurRadius = configOpts["blurRadius"]
	sourcePath = configOpts["sourcePath"]
	outPath = configOpts["outPath"]

	sourcePath = os.path.join(basePath, sourcePath)
	outPath = os.path.join(basePath, outPath)
	if not os.path.exists(outPath):
		os.makedirs(outPath)
	underlayStyleOpts = [brightNessFraction, contrastFraction, grayscaleFraction, blurRadius]

	createComposites(sourcePath, outPath, transparencyColor, transparencyTolerance, underlayStyleOpts)